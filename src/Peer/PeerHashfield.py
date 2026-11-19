import array
import base64
import struct
import time


class PeerHashfield(object):
    """Algorithm-aware availability hints with a legacy SHA-512 view.

    The legacy wire format remains an array of native-endian unsigned 16-bit
    values. Version 2 uses explicit algorithm namespaces and big-endian values.
    Hashfield entries are hints only; file integrity must still be verified.
    """

    VERSION = 2
    ALGORITHM_IDS = {
        "sha512": 0,
        "blake3": 1
    }
    ALGORITHM_ALIASES = {
        "sha512": "sha512",
        "sha512-truncated-256": "sha512",
        "blake3": "blake3",
        "blake3-256": "blake3"
    }

    __slots__ = ("fields", "storage", "time_changed")

    def __init__(self):
        self.fields = {
            "sha512": array.array("H"),
            "blake3": array.array("H")
        }
        # Keep the old attribute available for code that inspects legacy data.
        self.storage = self.fields["sha512"]
        self.time_changed = time.time()

    @classmethod
    def normalizeAlgorithm(cls, algorithm):
        try:
            return cls.ALGORITHM_ALIASES[algorithm]
        except (KeyError, TypeError):
            raise ValueError("Unsupported hashfield algorithm: %s" % algorithm)

    @classmethod
    def decodeHashId(cls, hash_id):
        """Decode a 32-bit namespaced ID; 16-bit IDs remain legacy SHA-512."""
        if not isinstance(hash_id, int) or hash_id < 0:
            raise ValueError("Hashfield ID must be a non-negative integer")

        algorithm_id = hash_id >> 16
        prefix = hash_id & 0xffff
        if algorithm_id == 0:
            return "sha512", prefix
        if algorithm_id == cls.ALGORITHM_IDS["blake3"]:
            return "blake3", prefix
        raise ValueError("Unknown hashfield algorithm namespace: %s" % algorithm_id)

    @classmethod
    def getHashId(cls, digest, algorithm="sha512"):
        """Return the first 16 digest bits, namespaced for non-legacy hashes."""
        algorithm = cls.normalizeAlgorithm(algorithm)
        if not isinstance(digest, str) or len(digest) < 4:
            raise ValueError("Digest must be a hexadecimal string of at least 4 characters")
        try:
            prefix = int(digest[:4], 16)
        except ValueError:
            raise ValueError("Digest prefix is not hexadecimal")

        return (cls.ALGORITHM_IDS[algorithm] << 16) | prefix

    def _field(self, algorithm="sha512"):
        return self.fields[self.normalizeAlgorithm(algorithm)]

    def appendHash(self, digest, algorithm="sha512"):
        hash_id = self.getHashId(digest, algorithm)
        return self.appendHashId(hash_id)

    def appendHashId(self, hash_id):
        algorithm, prefix = self.decodeHashId(hash_id)
        field = self.fields[algorithm]
        if prefix not in field:
            field.append(prefix)
            self.time_changed = time.time()
            return True
        return False

    def removeHash(self, digest, algorithm="sha512"):
        return self.removeHashId(self.getHashId(digest, algorithm))

    def removeHashId(self, hash_id):
        algorithm, prefix = self.decodeHashId(hash_id)
        field = self.fields[algorithm]
        if prefix in field:
            field.remove(prefix)
            self.time_changed = time.time()
            return True
        return False

    def hasHash(self, digest, algorithm="sha512"):
        return self.getHashId(digest, algorithm) in self

    def append(self, hash_id):
        """Legacy array-like API: append a raw SHA-512 16-bit prefix."""
        return self.appendHashId(hash_id)

    def remove(self, hash_id):
        """Legacy array-like API: remove a raw SHA-512 16-bit prefix."""
        return self.removeHashId(hash_id)

    def __contains__(self, hash_id):
        try:
            algorithm, prefix = self.decodeHashId(hash_id)
        except (TypeError, ValueError):
            return False
        return prefix in self.fields[algorithm]

    def __iter__(self):
        # Existing 16-bit SHA-512 IDs remain unchanged. BLAKE3 IDs occupy
        # the next 16-bit namespace, so the same prefix cannot alias SHA-512.
        for prefix in self.fields["sha512"]:
            yield prefix
        for prefix in self.fields["blake3"]:
            yield (self.ALGORITHM_IDS["blake3"] << 16) | prefix

    def __len__(self):
        return sum(len(field) for field in self.fields.values())

    def tobytes(self):
        """Return the legacy untyped projection understood by pre-v2 peers.

        Older clients held all digest prefixes in one bucket. Send the union
        of both algorithm namespaces so they can still discover BLAKE3 files.
        A v2 receiver ignores this projection in favor of the typed fields.
        """
        legacy = array.array("H")
        seen = set()
        for algorithm in ("sha512", "blake3"):
            for prefix in self.fields[algorithm]:
                if prefix not in seen:
                    legacy.append(prefix)
                    seen.add(prefix)
        return legacy.tobytes()

    def frombytes(self, hashfield_raw):
        """Append a legacy SHA-512-only representation."""
        self.fields["sha512"].frombytes(hashfield_raw)
        self.time_changed = time.time()

    def replaceFromBytes(self, hashfield_raw):
        """Replace the peer's legacy-only view and clear newer namespaces."""
        storage = array.array("H")
        storage.frombytes(hashfield_raw)
        self.fields = {
            "sha512": storage,
            "blake3": array.array("H")
        }
        self.storage = storage
        self.time_changed = time.time()

    @staticmethod
    def _encodeField(field):
        # Version 2 is network-order and deterministic across CPU architectures.
        return b"".join(struct.pack(">H", value) for value in sorted(field))

    @staticmethod
    def _decodeField(raw, algorithm):
        if not isinstance(raw, (bytes, bytearray)):
            raise ValueError("Hashfield %s must be bytes" % algorithm)
        if len(raw) % 2:
            raise ValueError("Hashfield %s has an incomplete 16-bit entry" % algorithm)

        storage = array.array("H")
        for offset in range(0, len(raw), 2):
            value = struct.unpack(">H", raw[offset:offset + 2])[0]
            if value not in storage:
                storage.append(value)
        return storage

    def toProtocolPayload(self):
        """Return v2 fields plus the SHA-512 field understood by legacy peers."""
        return {
            # Compatibility union for peers that do not understand v2.
            "hashfield_raw": self.tobytes(),
            "hashfield_version": self.VERSION,
            "hashfields": {
                algorithm: self._encodeField(field)
                for algorithm, field in self.fields.items()
            }
        }

    def replaceFromProtocol(self, payload):
        """Load v2 when explicitly versioned, otherwise decode the legacy field."""
        version = payload.get("hashfield_version")
        if version is None:
            if "hashfield_raw" not in payload:
                raise ValueError("Missing legacy hashfield payload")
            # Pre-v2 peers did not identify the algorithm. Some versions
            # used this same 16-bit table for both SHA-512 and BLAKE3.
            # Import it as an ambiguous compatibility hint in both buckets;
            # full digest verification remains mandatory after download.
            legacy = array.array("H")
            legacy.frombytes(payload["hashfield_raw"])
            self.fields = {
                "sha512": legacy,
                "blake3": array.array("H", legacy)
            }
            self.storage = self.fields["sha512"]
            self.time_changed = time.time()
            return False
        if version != self.VERSION:
            raise ValueError("Unsupported hashfield protocol version: %s" % version)

        hashfields = payload.get("hashfields")
        if not isinstance(hashfields, dict):
            raise ValueError("Version 2 hashfields must be a mapping")
        unknown_algorithms = set(hashfields) - set(self.ALGORITHM_IDS)
        if unknown_algorithms:
            raise ValueError("Unknown hashfield algorithms: %s" % sorted(unknown_algorithms))

        # Decode into temporary buckets before mutating current peer state.
        decoded = {}
        for algorithm in self.ALGORITHM_IDS:
            decoded[algorithm] = self._decodeField(hashfields.get(algorithm, b""), algorithm)

        self.fields = decoded
        self.storage = self.fields["sha512"]
        self.time_changed = time.time()
        return True

    def toCache(self):
        """Return a JSON-safe cache representation with an explicit version."""
        return {
            "version": self.VERSION,
            "hashfields": {
                algorithm: base64.b64encode(self._encodeField(field)).decode("ascii")
                for algorithm, field in self.fields.items()
            }
        }

    def replaceFromCache(self, cache):
        if not isinstance(cache, dict) or cache.get("version") != self.VERSION:
            raise ValueError("Unsupported hashfield cache version")
        hashfields = cache.get("hashfields")
        if not isinstance(hashfields, dict):
            raise ValueError("Hashfield cache fields must be a mapping")

        decoded = {}
        for algorithm in self.ALGORITHM_IDS:
            encoded = hashfields.get(algorithm, "")
            try:
                raw = base64.b64decode(encoded, validate=True)
            except Exception as err:
                raise ValueError("Invalid cached %s hashfield: %s" % (algorithm, err))
            decoded[algorithm] = self._decodeField(raw, algorithm)

        self.fields = decoded
        self.storage = self.fields["sha512"]
        self.time_changed = time.time()
