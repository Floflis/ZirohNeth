"""Cross-signature Bitcoin -> Ethereum ownership migration primitives.

A migration is authorized by the legacy Bitcoin key and accepted by the
new Ethereum EOA. CheckpointStore persists a locally observed chain of
verified migration records; it is not, by itself, a global freshness oracle.
"""
import copy
import hashlib
import json
import os
import tempfile
import threading
from pathlib import Path

import blake3
import rfc8785
from eth_account import Account
from eth_account.messages import encode_typed_data

from Crypt import CryptBitcoin
from Crypt import CryptEthereum


PROTOCOL = "zirohneth-bitcoin-to-ethereum-v1"
ZERO_DIGEST = "0x" + ("00" * 32)
_DOMAIN = {"name": "ZirohNeth Migration", "version": "1"}
_TYPES = {
    "EIP712Domain": [
        {"name": "name", "type": "string"},
        {"name": "version", "type": "string"},
    ],
    "MigrationAcceptance": [
        {"name": "migrationDigest", "type": "bytes32"},
        {"name": "oldIdentity", "type": "string"},
        {"name": "newIdentity", "type": "address"},
        {"name": "migrationSequence", "type": "uint64"},
        {"name": "previousMigrationDigest", "type": "bytes32"},
    ],
}


class MigrationError(ValueError):
    """Raised when a migration proof or checkpoint is invalid."""


def _payload(record):
    """Return only the fields covered by both signatures."""
    fields = (
        "protocol", "old_identity", "new_identity",
        "final_legacy_manifest_digest", "final_legacy_sequence",
        "migration_sequence", "previous_migration_digest",
    )
    try:
        payload = {key: record[key] for key in fields}
    except (KeyError, TypeError) as err:
        raise MigrationError("Incomplete migration payload") from err
    if payload["protocol"] != PROTOCOL:
        raise MigrationError("Unsupported migration protocol")
    if not isinstance(payload["old_identity"], str) or not CryptBitcoin.isValidAddress(payload["old_identity"]):
        raise MigrationError("Invalid legacy Bitcoin identity")
    payload["new_identity"] = CryptEthereum.normalize_address(payload["new_identity"])
    for field in ("final_legacy_sequence", "migration_sequence"):
        value = payload[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise MigrationError("Invalid " + field)
    for field in ("final_legacy_manifest_digest", "previous_migration_digest"):
        value = payload[field]
        if not isinstance(value, str) or len(value) != 66 or not value.startswith("0x"):
            raise MigrationError("Invalid " + field)
        try:
            bytes.fromhex(value[2:])
        except ValueError as err:
            raise MigrationError("Invalid " + field) from err
        payload[field] = value.lower()
    return payload


def migration_digest(record):
    """BLAKE3-256 digest of the RFC 8785 canonical migration payload."""
    return blake3.blake3(rfc8785.dumps(_payload(record))).hexdigest()



def legacy_manifest_digest(manifest):
    """Digest the exact legacy Bitcoin-signed JSON representation.

    The body excludes signature fields and the embedded migration envelope
    to avoid a circular digest. The final ordinary Bitcoin content signature
    still covers the complete manifest, including the embedded envelope.
    """
    protected = copy.deepcopy(manifest)
    for field in ("sign", "signs", "migration"):
        protected.pop(field, None)
    serialized = json.dumps(protected, sort_keys=True)
    return "0x" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def verify_final_legacy_manifest(record, manifest):
    """Confirm the referenced final manifest is signed by the old Bitcoin key."""
    try:
        payload = _payload(record)
        if manifest.get("address", payload["old_identity"]) != payload["old_identity"]:
            return False
        if manifest.get("inner_path", "content.json") != "content.json":
            return False
        if int(manifest.get("content_version", 1)) != 1:
            return False
        if manifest.get("migration_protocol") != PROTOCOL:
            return False
        if manifest.get("migration_status") != "historical":
            return False
        if manifest.get("migration_target") != payload["new_identity"]:
            return False
        embedded_record = manifest.get("migration")
        if not isinstance(embedded_record, dict):
            return False
        if record_digest(embedded_record) != record_digest(record):
            return False
        legacy_sequence = manifest.get("sequence", manifest.get("modified"))
        if isinstance(legacy_sequence, bool) or not isinstance(legacy_sequence, int):
            return False
        if legacy_sequence != payload["final_legacy_sequence"]:
            return False
        signs = manifest.get("signs", {})
        signature = signs.get(payload["old_identity"])
        if not signature:
            return False
        protected = copy.deepcopy(manifest)
        for field in ("sign", "signs"):
            protected.pop(field, None)
        serialized = json.dumps(protected, sort_keys=True)
        return (
            legacy_manifest_digest(manifest) == payload["final_legacy_manifest_digest"]
            and CryptBitcoin.verify(serialized, payload["old_identity"], signature)
        )
    except Exception:
        return False


def _ethereum_message(payload, digest):
    previous = bytes.fromhex(payload["previous_migration_digest"][2:])
    return {
        "types": _TYPES,
        "primaryType": "MigrationAcceptance",
        "domain": _DOMAIN,
        "message": {
            "migrationDigest": bytes.fromhex(digest),
            "oldIdentity": payload["old_identity"],
            "newIdentity": payload["new_identity"],
            "migrationSequence": payload["migration_sequence"],
            "previousMigrationDigest": previous,
        },
    }


def sign_migration(payload, bitcoin_private_key, ethereum_private_key):
    """Create a dual-signed record. Private keys are never stored in the result."""
    payload = _payload(payload)
    old_address = CryptBitcoin.privatekeyToAddress(bitcoin_private_key)
    if old_address != payload["old_identity"]:
        raise MigrationError("Bitcoin key does not control old_identity")
    eth_key = ethereum_private_key[4:] if ethereum_private_key.startswith("eth:") else ethereum_private_key
    eth_key = eth_key[2:] if eth_key.startswith("0x") else eth_key
    try:
        eth_bytes = bytes.fromhex(eth_key)
        eth_address = Account.from_key(eth_bytes).address
    except Exception as err:
        raise MigrationError("Invalid Ethereum private key") from err
    if CryptEthereum.normalize_address(eth_address) != payload["new_identity"]:
        raise MigrationError("Ethereum key does not control new_identity")

    canonical = rfc8785.dumps(payload).decode("utf-8")
    digest = migration_digest(payload)
    btc_signature = CryptBitcoin.sign(canonical, bitcoin_private_key)
    typed = encode_typed_data(full_message=_ethereum_message(payload, digest))
    eth_signature = Account.sign_message(typed, private_key=eth_bytes).signature.hex()
    if not btc_signature:
        raise MigrationError("Legacy Bitcoin signer cannot produce a supported signature")
    return dict(payload, bitcoin_signature=btc_signature, ethereum_signature=eth_signature)


def verify_migration(record):
    """Verify both signatures and their binding to the exact same payload."""
    try:
        payload = _payload(record)
        digest = migration_digest(payload)
        canonical = rfc8785.dumps(payload).decode("utf-8")
        if not CryptBitcoin.verify(canonical, payload["old_identity"], record["bitcoin_signature"]):
            return False
        typed = encode_typed_data(full_message=_ethereum_message(payload, digest))
        recovered = Account.recover_message(typed, signature=record["ethereum_signature"])
        return CryptEthereum.normalize_address(recovered) == payload["new_identity"]
    except Exception:
        return False


def record_digest(record):
    """Digest the signed envelope, including both signatures."""
    envelope = dict(record)
    return blake3.blake3(rfc8785.dumps(envelope)).hexdigest()


class CheckpointStore:
    """Atomic local checkpoint ledger with explicit trust-on-first-checkpoint.

    Call trust_checkpoint() only after obtaining the checkpoint digest from
    an independently trusted source. append() then enforces a contiguous,
    hash-linked sequence and rejects replay/forks relative to local state.
    """
    _lock = threading.RLock()

    def __init__(self, path):
        self.path = Path(path)

    def _read(self):
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
        if not isinstance(data, list) or not data:
            raise MigrationError("Checkpoint store is corrupt")
        first = _payload(data[0])
        if not verify_migration(data[0]) or first["migration_sequence"] != 1 or first["previous_migration_digest"] != ZERO_DIGEST:
            raise MigrationError("Checkpoint trust anchor is invalid")
        previous = data[0]
        for record in data[1:]:
            payload = _payload(record)
            previous_payload = _payload(previous)
            if not verify_migration(record):
                raise MigrationError("Stored checkpoint signature is invalid")
            if payload["migration_sequence"] != previous_payload["migration_sequence"] + 1:
                raise MigrationError("Stored checkpoint sequence is broken")
            if payload["previous_migration_digest"] != "0x" + record_digest(previous):
                raise MigrationError("Stored checkpoint chain is broken")
            if payload["old_identity"] != previous_payload["old_identity"]:
                raise MigrationError("Stored checkpoint identity changed")
            previous = record
        return data

    def _write(self, records):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=self.path.name + ".", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(records, stream, sort_keys=True, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def trust_checkpoint(self, record, expected_record_digest):
        """Pin a checkpoint obtained out-of-band; never infer freshness locally."""
        if not verify_migration(record) or record_digest(record) != expected_record_digest:
            raise MigrationError("Checkpoint does not match the independently trusted digest")
        payload = _payload(record)
        if payload["migration_sequence"] != 1 or payload["previous_migration_digest"] != ZERO_DIGEST:
            raise MigrationError("Initial trusted checkpoint must start at sequence 1")
        with self._lock:
            records = self._read()
            if records:
                raise MigrationError("Checkpoint store is already initialized")
            self._write([record])

    def append(self, record):
        """Append the next verified checkpoint, rejecting gaps, forks and replay."""
        if not verify_migration(record):
            raise MigrationError("Invalid dual-signed migration record")
        payload = _payload(record)
        with self._lock:
            records = self._read()
            if not records:
                raise MigrationError("No trusted checkpoint; pin one before appending")
            previous = records[-1]
            previous_payload = _payload(previous)
            expected_sequence = previous_payload["migration_sequence"] + 1
            expected_digest = "0x" + record_digest(previous)
            if payload["migration_sequence"] != expected_sequence:
                raise MigrationError("Migration checkpoint sequence is not contiguous")
            if payload["previous_migration_digest"] != expected_digest:
                raise MigrationError("Migration checkpoint does not extend the trusted chain")
            if payload["old_identity"] != previous_payload["old_identity"]:
                raise MigrationError("Checkpoint chain changed legacy identity")
            self._write(records + [record])

    def latest(self):
        """Return the latest locally trusted record, or None."""
        with self._lock:
            records = self._read()
            return copy.deepcopy(records[-1]) if records else None

    def is_terminal(self, bitcoin_identity):
        """Whether this local ledger has a checkpoint terminating the identity."""
        latest = self.latest()
        return bool(latest and _payload(latest)["old_identity"] == bitcoin_identity)
