# Content v2: implementation reference

## Status

Content v2 and the Bitcoin-to-Ethereum dual-signed migration primitives are present in the core. Audit remediation is in progress. This guide describes the protocol boundary and current implementation behavior; it is **not** a release-readiness statement. Unit/integration tests, crash fault-injection, peer interoperability and cross-client browser validation remain outstanding.

## Version dispatch

- A manifest without `content_version` is legacy v1.
- v1 retains the original SHA-512-truncated-256 file digest in the `sha512` field and the original Bitcoin message-signature flow.
- v2 declares `content_version: 2`, `hash_algorithm: blake3-256`, `identity_scheme: ethereum-eoa-secp256k1` and `signature_scheme: ethereum-eip712-v1`.
- Unknown content versions, hash algorithms, identity schemes and signature schemes are rejected.

## File integrity

`CryptHash.blake3sum()` calculates the standard BLAKE3 256-bit digest. `CryptHash.sha512sum()` is intentionally unchanged.

New v2 required-file entries use the `blake3` field:

```json
{
  "files": {
    "index.html": {
      "blake3": "<64 lowercase hexadecimal characters>",
      "size": 1234
    }
  }
}
```

The algorithm is selected from the explicit digest field when verifying a file. Existing optional files that are not locally available during a v1-to-v2 signing operation may retain their `sha512` digest, tagged with `hash_algorithm: sha512-truncated-256`. New files hashed for v2 use BLAKE3.

The peer hashfield still stores only 16-bit digest prefixes and does not identify the digest algorithm. It is a compact availability hint, never an integrity check. Full file digests are verified before content is accepted. Algorithm-namespaced hashfield encoding and mixed-version peer compatibility remain open work.

## Ethereum identity and signatures

Ethereum identities use secp256k1 EOA keys. Addresses are normalized to EIP-55 form and retain the `0x` prefix.

To explicitly select Ethereum signing, pass a private key with the `eth:` prefix followed by a 32-byte hexadecimal key. A bare 64-character hexadecimal key is not reinterpreted and continues through the legacy Bitcoin key parser.

The v2 manifest declares:

- `content_version: 2`
- `hash_algorithm: blake3-256`
- `identity_scheme: ethereum-eoa-secp256k1`
- `signature_scheme: ethereum-eip712-v1`
- `sequence`: monotonically increasing update number
- `previous_update_digest`: BLAKE3-256 digest of the previous protected manifest

The protected manifest is serialized with RFC 8785 JSON Canonicalization Scheme. Signature fields are excluded from the protected digest to avoid circular signing. EIP-712 signs the site address, protected-manifest digest, content version, sequence and previous-update digest under the ZirohNeth domain.

When a client has a locally stored predecessor, it enforces the next sequence and exact previous-digest link. A first-contact client has no trusted predecessor: a valid signature authenticates the signer and manifest, but does **not** establish global freshness. The backend exposes this as `freshness_status: unverified_first_contact`. Independent witnesses, transparency or quorum policy are still required to improve first-contact freshness.

The first implementation supports signing only the root `content.json` manifest with one Ethereum EOA signer. Ethereum sub-manifest signing, multisig and ERC-1271 smart-wallet verification are not implemented.

## Bitcoin compatibility and migration boundary

Legacy Bitcoin sites continue to use the v1 verification path. `CryptBitcoin` has not been repurposed to parse Ethereum keys or signatures.

The migration is authorized by a Bitcoin signature and accepted by the destination Ethereum EOA over the same migration payload. The final Bitcoin root embeds the dual-signed proof and is locally checkpointed. The Ethereum v2 manifest also includes a signed migration relationship containing the source identity and BLAKE3 digest of the exact proof. A pre-existing destination is reusable only when that relationship matches and the v2 manifest verifies.

Migration copies only root-manifest files. Before re-signing, the staged copy is checked against the legacy SHA-512-truncated-256 digest and declared size. The import uses a sibling staging directory and a local journal bound to the source identity, destination identity, terminal legacy manifest digest and migration proof digest. A matching interrupted stage can be rebuilt/resumed; an unrelated or unrecognized destination is rejected. These paths still require fault-injection tests before being considered proven crash-safe.

New migrations use protocol v2, which explicitly signs the legacy-manifest digest algorithm (SHA-256), migration-payload digest algorithm (BLAKE3-256) and canonicalization (RFC 8785), with a version-2 EIP-712 domain. The verifier retains protocol-v1 support with its historical implicit SHA-256 semantics. Never reinterpret v1 fields in place.

Manifests containing `includes` or `user_contents` remain unsupported by the current migration workflow and are rejected during preflight. Do not flatten these structures: their signer and authorization boundaries need a separate migration design.

## Transport compatibility

Ethereum-addressed sites do not create per-site Tor hidden services and do not use Tor onion peers. The Tor manager returns no hidden-service address for an Ethereum site, site peer discovery skips onion peers for Ethereum identities, and the connection server rejects onion connections when a site context identifies an Ethereum address.

This is a per-site onion-transport restriction. It does not globally disable the Tor daemon or change Tor behavior for legacy Bitcoin/Base58 sites. Global Tor modes and tracker proxy behavior are separate client-wide settings. Automated clearnet, Tor-enabled and mixed-peer regression tests are still required.

## Tests and release criteria

The cryptographic tests include BLAKE3 known vectors, Ethereum address normalization, EIP-712 signature recovery and tamper detection. A clean Python 3.11 dependency install and source compilation pass in GitHub Actions. These checks do not replace the full test suite.

Before release:

- Run the complete project test suite and all v1 golden vectors.
- Add migration tests for tampered/missing files, unrelated destination, retry, crash at every phase and journal recovery.
- Test update-chain replay, rollback, sequence gaps, same-sequence forks and restart persistence.
- Test first-contact freshness/conflicting migration proofs and mixed-version peer hashfields.
- Add end-to-end browser-to-backend tests for Ethereum v2 navigation and migration lifecycle.
- Verify the supported Python and operating-system matrix.

Remaining work is tracked in `docs/ToDo.md`.
