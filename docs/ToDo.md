# ZirohNeth ToDo

This file tracks work that is not yet implemented or not yet verified. An item moves out of this list only after code, tests, compatibility checks and documentation are complete.

## Content protocol

- [ ] Complete the content v2 implementation and run the full test suite.
- [ ] Add golden compatibility tests proving that v1 manifests, legacy SHA-512-truncated-256 hashes and Bitcoin signatures remain unchanged.
- [ ] Define and test the v2 hashfield/cache compatibility policy. The current compact hashfield stores only 16-bit prefixes and does not encode the digest algorithm.
- [ ] Extend Ethereum EIP-712 signing beyond the root content.json manifest and define how included manifests/certificates are authorized.
- [ ] Add adversarial tests for unknown versions, unknown algorithms, malformed manifests, duplicate JSON keys, replay and rollback.
- [ ] Add a cross-implementation RFC 8785 + EIP-712 test corpus for Python and future Rust clients.

## Bitcoin → Ethereum migration

- [ ] Specify a migration proof that is authorized by the old Bitcoin key and accepted by the new Ethereum EOA.
- [ ] Bind the proof to the final legacy manifest digest, old Bitcoin identity, new Ethereum identity, protocol version and terminal sequence.
- [ ] Define verifiable checkpoints/discovery and anti-rollback behavior for fresh clients.
- [ ] Preserve legacy Bitcoin sites as readable historical identities. Never silently rewrite an old site address.
- [ ] Add migration fixtures and negative tests for missing, mismatched, replayed or superseded proofs.

## Ethereum extensions

- [ ] Add Ethereum post-quantum identity/signature support as a separately versioned future protocol. Do not silently replace secp256k1/EIP-712.
- [ ] Evaluate ERC-1271 smart-wallet verification with an explicit chain, RPC and block-state policy.
- [ ] Design Ethereum multisignature support; current v2 EOA path is single-signer only.
- [ ] Define key import/export UX and safe handling for encrypted/private-key material. Never log secrets.

## Content v3 and IPFS

- [ ] Design content.json v3 with IPFS CIDv1 using the BLAKE3 multihash code.
- [ ] Decide the CID codec, raw-leaves policy, chunker and UnixFS import parameters. A CID for a UnixFS DAG is not the same as a raw BLAKE3 file digest.
- [ ] Specify whether v3 stores both a direct BLAKE3 file digest and a CID, and how each is verified.
- [ ] Verify Kubo and library support for the selected BLAKE3 multihash code across supported versions.
- [ ] Add CIDv1 interoperability vectors and migration tests from v2.

## Release and maintenance

- [ ] Run unit/integration tests on supported Python versions and operating systems.
- [ ] Verify dependency versions, packaging, reproducible installs and licensing.
- [ ] Update user-facing documentation and protocol compatibility notes after implementation is verified.
