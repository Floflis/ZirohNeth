"""Ethereum EOA identity and EIP-712 manifest signatures for ZirohNeth.

This module is deliberately separate from CryptBitcoin. Bitcoin message
signatures remain available for legacy content manifests.
"""
import copy

import blake3
import rfc8785
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import is_address, is_checksum_address, to_checksum_address


IDENTITY_SCHEME = "ethereum-eoa-secp256k1"
SIGNATURE_SCHEME = "ethereum-eip712-v1"
V3_SIGNATURE_SCHEME = "ethereum-eip712-v3"
CONTENT_VERSION = 2
ZERO_DIGEST = "0x" + ("00" * 32)

_TYPED_DATA_TYPES = {
    "EIP712Domain": [
        {"name": "name", "type": "string"},
        {"name": "version", "type": "string"},
    ],
    "SiteUpdate": [
        {"name": "siteAddress", "type": "address"},
        {"name": "contentDigest", "type": "bytes32"},
        {"name": "contentVersion", "type": "uint32"},
        {"name": "sequence", "type": "uint64"},
        {"name": "previousUpdateDigest", "type": "bytes32"},
    ],
}

# V3 uses a distinct EIP-712 primary type and domain version. This prevents
# signatures from being replayed between the legacy v2 and native-Iroh v3
# content profiles while keeping the v2 encoding byte-for-byte unchanged.
_TYPED_DATA_TYPES_V3 = {
    "EIP712Domain": [
        {"name": "name", "type": "string"},
        {"name": "version", "type": "string"},
    ],
    "SiteUpdateV3": [
        {"name": "siteAddress", "type": "address"},
        {"name": "contentDigest", "type": "bytes32"},
        {"name": "contentVersion", "type": "uint32"},
        {"name": "sequence", "type": "uint64"},
        {"name": "previousUpdateDigest", "type": "bytes32"},
    ],
}


def normalize_address(address):
    """Validate an Ethereum address and return its EIP-55 representation."""
    if not isinstance(address, str) or not address.startswith("0x") or not is_address(address):
        raise ValueError("Invalid Ethereum address")
    body = address[2:]
    if body != body.lower() and body != body.upper() and not is_checksum_address(address):
        raise ValueError("Invalid EIP-55 checksum")
    return to_checksum_address(address)


def private_key_to_address(private_key):
    """Derive an EOA address from a raw 32-byte hex private key."""
    key = private_key[4:] if private_key.startswith("eth:") else private_key
    key = key[2:] if key.startswith("0x") else key
    if len(key) != 64:
        raise ValueError("Ethereum private key must contain exactly 32 bytes")
    try:
        bytes.fromhex(key)
    except ValueError as err:
        raise ValueError("Ethereum private key must be hexadecimal") from err
    return Account.from_key(bytes.fromhex(key)).address


def _protected_manifest(content):
    """Copy the manifest and remove signature fields to avoid circular signing."""
    protected = copy.deepcopy(content)
    for field in ("sign", "signs", "signers_sign"):
        protected.pop(field, None)
    return protected


def manifest_digest(content):
    """Return BLAKE3-256 of the RFC 8785 canonical protected manifest."""
    canonical = rfc8785.dumps(_protected_manifest(content))
    return blake3.blake3(canonical).digest()


def verify_update_chain(previous, current):
    """Validate a v2 manifest against the locally trusted predecessor.

    Returns an explicit freshness status. First contact can authenticate a
    signature but cannot establish that the manifest is globally newest.
    """
    if previous is None:
        return "unverified_first_contact"

    previous_digest = manifest_digest(previous)
    current_digest = manifest_digest(current)
    if previous_digest == current_digest:
        # Idempotent verification of the same locally stored manifest.
        return "locally_continuous"

    previous_sequence = previous.get("sequence", 0)
    current_sequence = current.get("sequence")
    if (
        isinstance(previous_sequence, bool)
        or not isinstance(previous_sequence, int)
        or isinstance(current_sequence, bool)
        or not isinstance(current_sequence, int)
    ):
        raise ValueError("Invalid Ethereum update sequence")
    if current_sequence != previous_sequence + 1:
        raise ValueError("Ethereum update sequence is not the next local sequence")

    expected_previous = "0x" + previous_digest.hex()
    supplied_previous = current.get("previous_update_digest")
    if not isinstance(supplied_previous, str) or supplied_previous.lower() != expected_previous:
        raise ValueError("Ethereum update does not extend the locally trusted manifest")

    return "locally_continuous"


def _typed_message(content):
    address = normalize_address(content["address"])
    previous = content.get("previous_update_digest", ZERO_DIGEST)
    if isinstance(previous, str):
        previous = bytes.fromhex(previous[2:] if previous.startswith("0x") else previous)
    if len(previous) != 32:
        raise ValueError("previous_update_digest must be 32 bytes")

    content_version = int(content.get("content_version", 2))
    if content_version == 2:
        types = _TYPED_DATA_TYPES
        primary_type = "SiteUpdate"
        domain_version = "1"
    elif content_version == 3:
        types = _TYPED_DATA_TYPES_V3
        primary_type = "SiteUpdateV3"
        domain_version = "3"
    else:
        raise ValueError("Unsupported Ethereum content version: %s" % content_version)

    return {
        "types": types,
        "primaryType": primary_type,
        "domain": {"name": "ZirohNeth", "version": domain_version},
        "message": {
            "siteAddress": address,
            "contentDigest": manifest_digest(content),
            "contentVersion": content_version,
            "sequence": int(content["sequence"]),
            "previousUpdateDigest": previous,
        },
    }


def sign_manifest(content, private_key):
    """Sign a versioned Ethereum manifest using its EIP-712 profile."""
    content_version = int(content.get("content_version", 2))
    expected_scheme = SIGNATURE_SCHEME if content_version == 2 else V3_SIGNATURE_SCHEME
    if content.get("signature_scheme") != expected_scheme:
        raise ValueError("Signature scheme does not match Ethereum content version")
    key = private_key[4:] if private_key.startswith("eth:") else private_key
    key = key[2:] if key.startswith("0x") else key
    signer = Account.from_key(bytes.fromhex(key)).address
    if normalize_address(signer) != normalize_address(content["address"]):
        raise ValueError("Ethereum private key does not match manifest address")
    typed_data = encode_typed_data(full_message=_typed_message(content))
    signed = Account.sign_message(typed_data, private_key=bytes.fromhex(key))
    return "0x" + signed.signature.hex().removeprefix("0x")


def verify_manifest(content, signature, expected_address):
    """Verify a versioned Ethereum manifest and ensure its signer is expected."""
    try:
        content_version = int(content.get("content_version", 2))
        expected_scheme = SIGNATURE_SCHEME if content_version == 2 else V3_SIGNATURE_SCHEME
        if content.get("signature_scheme") != expected_scheme:
            return False
        typed_data = encode_typed_data(full_message=_typed_message(content))
        recovered = Account.recover_message(typed_data, signature=signature)
        return normalize_address(recovered) == normalize_address(expected_address)
    except Exception:
        return False
