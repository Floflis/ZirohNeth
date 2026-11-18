# Content v2: implementation reference

## Status

Content v2 support is being introduced on the feature branch feat/content-v2-blake3-ethereum. This document describes the code currently present in that branch. It is not a release-readiness statement: integration tests, legacy compatibility checks and cross-platform validation remain outstanding.

## Version dispatch

- A manifest without content_version is legacy v1.
- v1 retains the original SHA-512-truncated-256 file digest in the sha512 field and the original Bitcoin message-signature flow.
- v2 declares content_version: 2, hash_algorithm: blake3-256, identity_scheme: ethereum-eoa-secp256k1 and signature_scheme: ethereum-eip712-v1.
- Unknown content versions, hash algorithms, identity schemes and signature schemes are rejected.

## File integrity

CryptHash.blake3sum() calculates the standard BLAKE3 256-bit digest. CryptHash.sha512sum() is intentionally unchanged.

New v2 required-file entries use the blake3 field:

{
  "files": {
    "index.html": {
      "blake3": "<64 lowercase hexadecimal characters>",
      "size": 1234
    }
  }
}

The algorithm is selected from the explicit digest field when verifying a file. Existing optional files that are not locally available during a v1-to-v2 signing operation may retain their sha512 digest, tagged with hash_algorithm: sha512-truncated-256. New files hashed for v2 use BLAKE3.

The peer hashfield still stores only 16-bit digest prefixes. This is a compact availability hint, not an integrity check. The full file digest is always verified before content is accepted. Algorithm-aware hashfield namespacing remains a follow-up task.

## Ethereum identity and signatures

Ethereum identities use secp256k1 EOA keys. Addresses are normalized to EIP-55 form and retain the 0x prefix.

To explicitly select Ethereum signing, pass a private key with the eth: prefix followed by a 32-byte hexadecimal key. A bare 64-character hexadecimal key is not reinterpreted and continues through the legacy Bitcoin key parser.

The v2 manifest declares:

- content_version: 2
- hash_algorithm: blake3-256
- identity_scheme: ethereum-eoa-secp256k1
- signature_scheme: ethereum-eip712-v1
- sequence: monotonically increasing update number
- previous_update_digest: BLAKE3-256 digest of the previous protected manifest, or 32 zero bytes for the first update

The protected manifest is serialized with RFC 8785 JSON Canonicalization Scheme. Signature fields are excluded from the protected digest to avoid circular signing. EIP-712 signs the site address, protected-manifest digest, content version, sequence and previous-update digest under the ZirohNeth domain.

The first implementation supports signing only the root content.json manifest with one Ethereum EOA signer. Ethereum sub-manifest signing, multisig and ERC-1271 smart-wallet verification are not implemented.

## Bitcoin compatibility and migration boundary

Legacy Bitcoin sites continue to use the v1 verification path. CryptBitcoin has not been repurposed to parse Ethereum keys or signatures.

This implementation does not yet prove ownership transfer from a Bitcoin site to an Ethereum identity. A new Ethereum site address is not, by itself, evidence that the owner of a legacy Bitcoin site authorized the move. A dual-signed migration proof, terminal legacy checkpoint and anti-rollback discovery policy are tracked in docs/ToDo.md.

## Tests and release criteria

TestCryptEthereum.py contains BLAKE3 known vectors, Ethereum address normalization, EIP-712 signature recovery and tamper-detection tests. These tests have been added but have not yet been executed in this environment.

Before release:
- Run the complete project test suite.
- Verify all v1 golden vectors and legacy Bitcoin signatures.
- Add end-to-end tests for v2 signing and file verification.
- Test malformed manifests, unknown algorithms, replay and rollback.
- Verify supported Python versions, operating systems and dependency installation.

Remaining work is tracked in docs/ToDo.md.


## Tor policy for Ethereum-addressed sites

Ethereum-addressed sites (0x identities) do not create per-site Tor hidden services and do not use Tor onion peers. The Tor manager returns no hidden-service address for an Ethereum site, site peer discovery skips onion peers for Ethereum identities, and the connection server rejects onion connections when a site context identifies an Ethereum address.

This is a per-site onion-transport restriction. It does not globally disable the Tor daemon or change Tor behavior for legacy Bitcoin/Base58 sites. Global Tor modes and tracker proxy behavior are separate client-wide settings and remain subject to the follow-up audit in docs/ToDo.md. Automated regression tests are still required.
