# Implementation guide: versioned content manifests, BLAKE3 and Ethereum identities

**Status:** implementation plan only. No production code is implemented by this document.
**Target:** ZirohNeth
**Branch for this documentation PR:** `docs/iroh-rust-crypto-studies`

## Goals

This guide turns the architecture study into an ordered implementation path. Preserve legacy Bitcoin sites and legacy content verification while introducing explicitly versioned manifests, BLAKE3 content hashes and classical (pre-quantum) Ethereum EOA identities/signatures.

Do not introduce post-quantum cryptography in this work.

## Ground rules

- Treat a missing `content_version` as legacy v1.
- Never reinterpret or overwrite the legacy `sha512` field. The existing implementation is SHA-512 truncated to 256 bits, not full SHA-512 and not standardized SHA-512/256.
- Use a new, explicit field for BLAKE3, e.g. `blake3`, with `hash_algorithm: "blake3-256"` in v2.
- Keep legacy readers. New v2 writers must emit only the v2 schema they claim to support.
- Keep content integrity (file digest) separate from manifest authenticity (signature).
- Keep Bitcoin and Ethereum identity/signature implementations separate behind a typed identity interface.
- Never remove the `0x` prefix from Ethereum addresses.
- Do not silently accept an unknown version, hash algorithm, identity scheme or signature scheme.
- Do not add ERC-1271 smart-wallet validation to the first EOA implementation; it requires chain/RPC state and a separate policy.
- No implementation should be marked complete until tests and compatibility checks actually pass.

## 1. Start with repository reconnaissance

Inspect the current versions of:

- `src/Crypt/CryptHash.py`
- `src/Crypt/CryptBitcoin.py`
- `src/Content/ContentManager.py`
- `src/Site/Site.py`
- `src/Site/SiteManager.py`
- `src/Peer/PeerHashfield.py`
- `src/Site/SiteStorage.py`
- tests under `src/Test`
- dependency declarations and packaging/build scripts

The earlier audit used commit `dfb0e9ed390006cde9365354572120c62fcf6119` from the previous repository owner. Re-check every finding against the current `Floflis/ZirohNeth` default branch before coding. Do not assume paths, line numbers or behavior are unchanged.

Create baseline tests before refactoring. Capture known legacy hashes, signatures, address parsing, manifest serialization and hashfield behavior as golden vectors.

## 2. Define the v2 manifest contract

Suggested top-level fields:

```json
{
  "content_version": 2,
  "hash_algorithm": "blake3-256",
  "identity_scheme": "ethereum-eoa-secp256k1",
  "signature_scheme": "ethereum-eip712-v1"
}
```

This is a conceptual minimum, not a final complete schema. Define required fields, optional fields, types, canonicalization, error behavior and migration rules before implementation.

For each v2 file entry, add a distinct `blake3` digest field. Do not overload `sha512`. Decide whether size is mandatory and validate it before writing data to storage.

Unknown versions and algorithms must fail closed with a useful error. A legacy v1 manifest must continue through the exact legacy verification path.

## 3. Implement BLAKE3 without breaking legacy files

Where to work:

- `src/Crypt/CryptHash.py`: add a clearly named BLAKE3 function; do not change the meaning of `sha512sum()`.
- `src/Content/ContentManager.py`: dispatch file hashing and verification from manifest version/algorithm.
- `src/Peer/PeerHashfield.py`: audit how file hashes become 16-bit IDs. Prevent v1 and v2 digest namespaces from silently colliding or mixing; version or isolate the hashfield/cache representation if required.
- Tests: empty input, `abc`, binary data, chunked streaming, large files, corrupted files and legacy vectors.

Use BLAKE3-256 (32-byte output) as the initial v2 digest. BLAKE3 XOF can produce 64 bytes when explicitly requested, but that is not the same thing as BLAKE2b-512. Do not change digest length casually.

## 4. Add typed identity and Ethereum EOA support

Where to work:

- Add a separate module such as `src/Crypt/CryptEthereum.py`.
- Add or adapt an identity parser/dispatcher without making `CryptBitcoin.py` interpret Ethereum keys.
- `src/Site/SiteManager.py`: replace the Base58-only address assumption with explicit scheme-specific validation.
- `src/Site/Site.py`: replace generic character stripping with typed parsing and canonical normalization. Preserve the Ethereum `0x` prefix.
- Audit database keys, trackers, caches, URLs and peer discovery for assumptions that every address is Base58.

For EOA:
- curve: secp256k1;
- address derivation: last 20 bytes of Keccak-256 over the uncompressed public key without the `0x04` prefix;
- canonical address: `0x` plus 40 hexadecimal characters; EIP-55 checksum for display/validation;
- key input: use an explicit prefix such as `eth:` in any shared key dispatcher so a bare 64-character hex string is not accidentally reinterpreted as Ethereum;
- never log private keys, seeds or signatures containing secrets.

Use a maintained Ethereum library for EIP-712 encoding/signing/recovery. Do not hand-roll Keccak or typed-data encoding.

## 5. Specify and sign the v2 manifest

Before implementing, decide the exact typed-data schema, domain, chain ID policy, sequence/replay rules and previous-digest behavior.

Canonicalize the protected manifest deterministically. The earlier study recommends RFC 8785 JCS as the JSON canonicalization basis. Define exactly which signature fields are excluded before computing the signed digest, so no circular signature dependency exists.

Use a versioned signature identifier. Keep the legacy Bitcoin message-signature verification untouched. Verify that the recovered Ethereum signer matches the manifest's declared site identity.

Reject:
- modified protected fields;
- wrong domain or protocol version;
- signer/address mismatch;
- duplicate or stale sequence numbers;
- wrong previous digest;
- malformed or unsupported signature schemes.

Note: an earlier study discussed EIP-191 and EIP-712 in different contexts. The implementation must settle one normative scheme for v2 before code. The recommended direction in the detailed identity study is EIP-712 for typed manifest updates; do not mix EIP-191 and EIP-712 identifiers.

## 6. Migration from legacy Bitcoin identity

Treat migration as a separate, later milestone.

A migration proof should bind:
- old Bitcoin identity;
- final legacy manifest digest and sequence;
- new Ethereum identity;
- proof signed by the old key;
- acceptance proof signed by the new key;
- protocol/version and terminal update policy.

Keep the old site readable as historical content. Do not overwrite its identity record. A terminal migration marker stored only in a manifest cannot guarantee that a fresh client will know about a later migration if it is served an older manifest. A verifiable checkpoint/discovery policy is required to prevent rollback for new clients.

Do not claim global freezing until that checkpoint mechanism exists and is tested.

## 7. Defer smart wallets

ERC-1271 verification is not equivalent to offline EOA recovery. It requires a selected chain, RPC/provider, block-state policy, reorg handling and failure behavior. Keep the first implementation EOA-only unless a separate design explicitly adds ERC-1271.

## 8. Suggested implementation sequence

1. Re-audit current default branch and write baseline compatibility tests.
2. Specify and review the v2 manifest schema and version dispatch.
3. Add BLAKE3 primitive and test vectors.
4. Add v2 file hash read/write/verification.
5. isolate hashfield/cache namespaces by algorithm/version.
6. Add typed identity parsing and Ethereum EOA address validation.
7. Add Ethereum EIP-712 manifest signing and verification.
8. Add adversarial tests for replay, rollback, wrong signer and malformed data.
9. Design and implement Bitcoin-to-Ethereum migration proofs/checkpoints.
10. Consider ERC-1271 only as a separate feature.

Each step should be a small commit with tests and a clear rollback path.

## 9. Dependencies to evaluate

The earlier study suggests these Python packages for evaluation:

- `blake3`
- `eth-account`
- `eth-utils`
- `rfc8785`
- `web3.py` only if/when ERC-1271 RPC validation is implemented

Verify current versions, supported Python versions, platform wheels, licensing and reproducible installation before adding dependencies. Do not add all of them preemptively.

## 10. Acceptance checklist

- [ ] Legacy v1 manifests still verify byte-for-byte and signature-for-signature.
- [ ] V2 manifests reject unsupported versions and algorithms.
- [ ] BLAKE3-256 vectors pass in all supported environments.
- [ ] File verification chooses the algorithm declared by the manifest.
- [ ] Hashfield/cache cannot silently mix v1 and v2 digest namespaces.
- [ ] Ethereum addresses preserve `0x` and normalize consistently.
- [ ] Ethereum signer recovery matches the declared site identity.
- [ ] EIP-712 domain, sequence and replay rules are tested.
- [ ] Bitcoin legacy verification remains unchanged.
- [ ] No private key material appears in logs or error messages.
- [ ] Documentation describes compatibility boundaries and upgrade behavior.
- [ ] Tests run on the actual supported operating systems and architectures.

## Related studies

- [Iroh in parallel with ZeroNet](IROH-PARALLEL-ZERONET.md)
- [Rust migration audit](RUST-MIGRATION-AUDIT.md)
- [BLAKE3 and Ethereum identity migration study](BLAKE3-ETHEREUM-IDENTITY-MIGRATION.md)

These documents are design/audit material. They are not proof that any feature described in them has been implemented.
