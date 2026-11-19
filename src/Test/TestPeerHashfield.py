from Peer.PeerHashfield import PeerHashfield


def test_hashfield_algorithm_namespaces():
    field = PeerHashfield()
    sha512_id = field.getHashId("AABB", "sha512")
    blake3_id = field.getHashId("AABB", "blake3")

    # Equal 16-bit prefixes must not alias across digest algorithms.
    assert sha512_id == 0xAABB
    assert blake3_id == 0x1AABB
    assert field.appendHash("AABB", "sha512")
    assert field.appendHash("AABB", "blake3")
    assert field.appendHash("CAFE", "blake3")
    cafe_blake3_id = field.getHashId("CAFE", "blake3")
    assert len(field) == 3
    assert sha512_id in field
    assert blake3_id in field

    payload = field.toProtocolPayload()
    assert payload["hashfield_version"] == 2
    assert payload["hashfields"]["sha512"] == bytes.fromhex("aabb")
    assert payload["hashfields"]["blake3"] == bytes.fromhex("aabbcafe")

    # A v2 peer restores both buckets without endian ambiguity.
    restored = PeerHashfield()
    assert restored.replaceFromProtocol(payload)
    assert sha512_id in restored
    assert blake3_id in restored
    assert cafe_blake3_id in restored

    # An unversioned legacy table is ambiguous, so it populates both buckets.
    legacy = PeerHashfield()
    assert not legacy.replaceFromProtocol({"hashfield_raw": payload["hashfield_raw"]})
    assert sha512_id in legacy
    assert blake3_id in legacy
    assert cafe_blake3_id in legacy
    assert field.getHashId("CAFE", "sha512") in legacy

    # Raw legacy cache bytes are equally ambiguous.
    legacy_cache = PeerHashfield()
    legacy_cache.replaceFromBytes(payload["hashfield_raw"])
    assert sha512_id in legacy_cache
    assert blake3_id in legacy_cache
    assert cafe_blake3_id in legacy_cache
    assert field.getHashId("CAFE", "sha512") in legacy_cache

    # The persisted cache keeps both algorithm namespaces.
    cached = PeerHashfield()
    cached.replaceFromCache(restored.toCache())
    assert sha512_id in cached
    assert blake3_id in cached
    assert cafe_blake3_id in cached

    # Unknown explicit versions must not silently downgrade to v1.
    try:
        cached.replaceFromProtocol({
            "hashfield_version": 3,
            "hashfield_raw": payload["hashfield_raw"]
        })
    except ValueError:
        pass
    else:
        assert False, "Unknown hashfield versions must be rejected"

    # Truncated network-order entries are rejected.
    try:
        cached.replaceFromProtocol({
            "hashfield_version": 2,
            "hashfield_raw": payload["hashfield_raw"],
            "hashfields": {"sha512": b"\\xaa", "blake3": b""}
        })
    except ValueError:
        pass
    else:
        assert False, "Malformed v2 hashfields must be rejected"

    # Explicit unknown algorithm names must not be silently ignored.
    try:
        cached.replaceFromProtocol({
            "hashfield_version": 2,
            "hashfield_raw": payload["hashfield_raw"],
            "hashfields": {"sha512": b"", "blake3": b"", "sha3": b""}
        })
    except ValueError:
        pass
    else:
        assert False, "Unknown hashfield algorithms must be rejected"
