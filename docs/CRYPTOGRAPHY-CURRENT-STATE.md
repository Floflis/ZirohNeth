# Cryptography and content formats: current implementation

## Compatibility baseline

The original ZeroNet-compatible content format remains the compatibility baseline:

- A missing content_version is treated as legacy v1.
- The legacy sha512 field is SHA-512 truncated to 256 bits (32 bytes), not full SHA-512 and not standardized SHA-512/256.
- Legacy manifest signatures use the existing Bitcoin message-signature implementation in CryptBitcoin.
- Existing v1 manifests must continue to use the legacy verification path.

## New implementation in progress

The feature branch feat/content-v2-blake3-ethereum introduces the first implementation pieces for v2:

- CryptHash.blake3sum() computes the standard 32-byte BLAKE3 digest. It does not modify sha512sum().
- CryptEthereum provides Ethereum EOA address normalization, raw private-key address derivation, RFC 8785 canonical manifest hashing and EIP-712 signing/recovery.
- Ethereum addresses retain the 0x prefix and use EIP-55 checksums.
- Ethereum private keys use the explicit eth: prefix. Bare 64-character hexadecimal private keys retain their historical Bitcoin interpretation.
- ContentManager selects BLAKE3-256 and EIP-712 when explicitly signing with an eth: key, and dispatches file verification by the digest field present in the manifest.
- Ethereum v2 signing is currently limited to the root content.json manifest and one EOA signer. Ethereum sub-manifest signing, multisig and ERC-1271 are not implemented.

## Security and compatibility boundaries

- BLAKE3 file integrity and EIP-712 manifest authenticity are separate checks.
- v2 identifies its algorithms explicitly with content_version, hash_algorithm, identity_scheme and signature_scheme.
- Unknown v2 algorithms and schemes are rejected.
- The old Bitcoin signing and SHA-512-truncated-256 code paths are intentionally retained.
- Bitcoin-to-Ethereum migration proofs and anti-rollback checkpoints are not yet implemented. Creating a new Ethereum-identified site is not proof of ownership of an existing Bitcoin site.
- The compact peer hashfield still stores only 16-bit digest prefixes. Algorithm-aware namespacing remains a compatibility task.

## Verification status

The code and tests are being assembled on a feature branch. Do not treat this feature as release-ready until the full test suite, legacy compatibility tests and cross-platform checks pass.

See ToDo.md for remaining work.


## Tor policy note

Ethereum-addressed sites (0x identities) are excluded from per-site Tor hidden-service creation and onion-peer transport. This does not globally disable Tor or alter legacy Bitcoin/Base58 site behavior. The implementation is in TorManager, Site peer selection and ConnectionServer; automated regression tests remain pending.
