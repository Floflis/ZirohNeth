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
    assert normalized == account.address


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
