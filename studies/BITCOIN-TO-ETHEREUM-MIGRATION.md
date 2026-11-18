# Bitcoin → Ethereum site migration

> **Status:** the migration proof is embedded in the terminal Bitcoin `content.json`; SiteManager can discover and resolve the Ethereum destination from that signed manifest. Local anti-rollback pinning and a first file-import workflow are implemented. Tests have been added but not executed.

## Protocol flow

1. A client visits the legacy Bitcoin address and obtains its root `content.json`.
2. The final Bitcoin manifest contains a `migration` object with the old identity, new Ethereum identity, final legacy body digest/sequence, protocol identifier, migration sequence, previous-record digest, Bitcoin authorization signature and Ethereum EIP-712 acceptance signature.
3. The ordinary Bitcoin root-manifest signature also covers the embedded migration object. This protects the complete on-site redirect record.
4. The client verifies the outer Bitcoin signature, the Bitcoin migration authorization, the Ethereum acceptance signature, and the binding between the proof and final manifest.
5. The client pins the verified proof locally. SiteManager resolves future visits to the old Bitcoin address to the new Ethereum address.
6. The old Bitcoin site directory and address remain intact as historical material. The new Ethereum site receives the authorized files and a freshly generated v2/BLAKE3 root manifest signed by the Ethereum key.

There is no separate public registry, contract, chain selection or peer-supplied redirect service in this design. The Bitcoin site's own signed root manifest is the discovery record.

## Signature and digest construction

The migration record uses protocol `zirohneth-bitcoin-to-ethereum-v1` and is signed by both keys:

- The Bitcoin key signs the canonical migration payload, authorizing the transfer away from the old identity.
- The Ethereum EOA signs EIP-712 acceptance of the same payload digest, old identity, new identity, migration sequence and previous-record digest.
- The record is embedded in the final Bitcoin `content.json`.
- The normal Bitcoin content signature is recalculated after embedding, so it covers the migration object too.

To avoid a circular digest, `final_legacy_manifest_digest` commits to the legacy manifest body excluding `sign`, `signs`, and the embedded `migration` envelope. The ordinary Bitcoin content signature covers the migration envelope and all other manifest fields. The proof verifier checks both the body digest and the complete outer signature.

## Implementation

- `src/Crypt/CryptMigration.py`: dual signatures, final-manifest verification and atomic local checkpoint ledger.
- `src/Crypt/MigrationWorkflow.py`: prepares the embedded proof, publishes the terminal Bitcoin manifest, pins the checkpoint, copies authorized files to the Ethereum site and signs/publishes the new v2 root manifest.
- `src/Content/ContentManager.py`: pins a valid embedded migration proof when first observed, rejects a later Bitcoin root manifest that conflicts with the pinned terminal proof, and blocks new signatures under a historical identity.
- `src/Site/SiteManager.py`: verifies the locally stored Bitcoin root manifest, restores historical mode when loading an already migrated site, and resolves the legacy address to its Ethereum destination. `Site.publish()` allows only re-advertising the exact terminal root manifest. The old site data is not renamed or deleted.

The workflow refuses roots with `includes` or `user_contents` because their signer lifecycle has not been migrated. It also refuses to overwrite an unrelated existing Ethereum destination.

## Freshness and security boundary

A dual-signed manifest proves that the Bitcoin owner authorized the transfer and the Ethereum owner accepted it. It does not prove that a peer is showing a fresh copy.

A client that has already observed and pinned the final manifest rejects rollback to a different Bitcoin root. A fresh client can still be shown an older, validly signed pre-migration manifest by a peer that withholds the final one. Without an independent freshness source, this cannot be solved cryptographically by the manifest alone. This protocol intentionally accepts that boundary rather than adding an unrelated public registry.

Legacy clients that do not implement this migration protocol will not follow the Ethereum destination. The guarantee applies to compatible clients.

## Remaining work

- Run all migration and content compatibility tests.
- Add adversarial tests for stale-peer withholding, manifest rollback, malformed embedded records and conflicting destination sites.
- Complete UI/CLI migration initiation and recovery behavior.
- Audit file-copy semantics for all supported platforms and optional files.
- Define how included/user manifests are migrated before lifting the current restriction.
- Verify the historical site is read-only in every publishing/editing UI path.

Do not claim global freshness against a malicious peer or compatibility with legacy clients.
