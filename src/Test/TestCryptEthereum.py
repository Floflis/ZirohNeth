import io

import pytest
from eth_account import Account

from Crypt import CryptEthereum, CryptHash


def test_legacy_sha512_truncation_remains_unchanged():
    # The old sha512 field is SHA-512 truncated to its first 32 bytes.
    assert CryptHash.sha512sum(io.BytesIO(b"")).lower() == (
        "cf83e1357eefb8bdf1542850d66d8007"
        "d620e4050b5715dc83f4a921d36ce9ce"
    )


def test_blake3_256_known_vectors():
    assert CryptHash.blake3sum(io.BytesIO(b"")).lower() == (
        "af1349b9f5f9a1a6a0404dea36dcc949"
        "9bcb25c9adc112b7cc9a93cae41f3262"
    )
    assert CryptHash.blake3sum(io.BytesIO(b"abc")).lower() == (
        "6437b3ac38465133ffb63b75273a8db5"
        "48c558465d79db03fd359c6cd5bd9d85"
    )


def test_ethereum_eip55_normalization():
    account = Account.create()
    normalized = CryptEthereum.normalize_address(account.address.lower())
    uppercase = CryptEthereum.normalize_address("0x" + account.address[2:].upper())
    assert normalized == account.address
    assert uppercase == account.address


def test_ethereum_rejects_invalid_mixed_case_checksum():
    with pytest.raises(ValueError):
        CryptEthereum.normalize_address("0x" + "aA" * 20)


def test_eip712_manifest_signature_and_tamper_detection():
    account = Account.create()
    private_key = "eth:" + account.key.hex()
    manifest = {
        "content_version": 2,
        "hash_algorithm": "blake3-256",
        "identity_scheme": CryptEthereum.IDENTITY_SCHEME,
        "signature_scheme": CryptEthereum.SIGNATURE_SCHEME,
        "address": account.address,
        "sequence": 1,
        "previous_update_digest": CryptEthereum.ZERO_DIGEST,
        "modified": 1794960000,
        "files": {"index.html": {"blake3": "00" * 32, "size": 0}},
    }

    signature = CryptEthereum.sign_manifest(manifest, private_key)
    assert signature.startswith("0x")
    assert CryptEthereum.verify_manifest(manifest, signature, account.address)

    tampered = dict(manifest)
    tampered["modified"] += 1
    assert not CryptEthereum.verify_manifest(tampered, signature, account.address)


def test_ethereum_private_key_requires_explicit_prefix():
    account = Account.create()
    assert CryptEthereum.private_key_to_address("eth:" + account.key.hex()) == account.address



def _chain_manifest(sequence=1, previous=CryptEthereum.ZERO_DIGEST, title="site", address=None):
    account = Account.create() if address is None else None
    return {
        "content_version": 2,
        "hash_algorithm": "blake3-256",
        "identity_scheme": CryptEthereum.IDENTITY_SCHEME,
        "signature_scheme": CryptEthereum.SIGNATURE_SCHEME,
        "address": address or account.address,
        "sequence": sequence,
        "previous_update_digest": previous,
        "modified": 1794960000 + sequence,
        "title": title,
        "files": {},
    }


def test_update_chain_accepts_next_sequence_and_exact_previous_digest():
    first = _chain_manifest()
    digest = "0x" + CryptEthereum.manifest_digest(first).hex()
    second = _chain_manifest(sequence=2, previous=digest, title="updated", address=first["address"])
    assert CryptEthereum.verify_update_chain(first, second) == "locally_continuous"


def test_update_chain_rejects_replay_rollback_and_sequence_gap():
    first = _chain_manifest()
    digest = "0x" + CryptEthereum.manifest_digest(first).hex()
    replay = _chain_manifest(sequence=1, previous=digest, title="replay", address=first["address"])
    rollback = _chain_manifest(sequence=0, previous=digest, title="rollback", address=first["address"])
    gap = _chain_manifest(sequence=3, previous=digest, title="gap", address=first["address"])
    for changed in (replay, rollback, gap):
        with pytest.raises(ValueError):
            CryptEthereum.verify_update_chain(first, changed)


def test_update_chain_rejects_wrong_predecessor_digest():
    first = _chain_manifest()
    second = _chain_manifest(sequence=2, previous="0x" + ("11" * 32), title="fork", address=first["address"])
    with pytest.raises(ValueError, match="does not extend"):
        CryptEthereum.verify_update_chain(first, second)


def test_update_chain_marks_first_contact_and_accepts_idempotent_recheck():
    first = _chain_manifest()
    assert CryptEthereum.verify_update_chain(None, first) == "unverified_first_contact"
    assert CryptEthereum.verify_update_chain(first, first) == "locally_continuous"


def test_v3_eip712_signature_uses_a_separate_domain_and_primary_type():
    account = Account.create()
    manifest = {
        "content_version": 3,
        "hash_algorithm": "blake3-256",
        "identity_scheme": CryptEthereum.IDENTITY_SCHEME,
        "signature_scheme": CryptEthereum.V3_SIGNATURE_SCHEME,
        "address": account.address,
        "sequence": 1,
        "previous_update_digest": CryptEthereum.ZERO_DIGEST,
        "modified": 1794960000,
        "files": {},
        "iroh": {
            "providers": [
                {"node_id": "a" * 64, "relay_url": None, "direct_addresses": []}
            ]
        },
    }

    signature = CryptEthereum.sign_manifest(manifest, "eth:" + account.key.hex())
    assert CryptEthereum.verify_manifest(manifest, signature, account.address)

    replay = dict(manifest)
    replay["content_version"] = 2
    replay["signature_scheme"] = CryptEthereum.SIGNATURE_SCHEME
    assert not CryptEthereum.verify_manifest(replay, signature, account.address)


def test_v3_signature_rejects_the_v2_signature_scheme():
    account = Account.create()
    manifest = {
        "content_version": 3,
        "hash_algorithm": "blake3-256",
        "identity_scheme": CryptEthereum.IDENTITY_SCHEME,
        "signature_scheme": CryptEthereum.SIGNATURE_SCHEME,
        "address": account.address,
        "sequence": 1,
        "previous_update_digest": CryptEthereum.ZERO_DIGEST,
        "modified": 1794960000,
        "files": {},
    }
    with pytest.raises(ValueError, match="Signature scheme"):
        CryptEthereum.sign_manifest(manifest, "eth:" + account.key.hex())
