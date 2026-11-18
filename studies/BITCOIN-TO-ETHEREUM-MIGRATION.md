# Bitcoin → Ethereum site migration study

> **Status:** dual-signature primitives, final-manifest verification, a local checkpoint ledger, and a two-phase orchestration API are implemented. A concrete global registry adapter, Ethereum site importer/registration implementation, and UI lifecycle remain incomplete.
>
> **Scope:** preserve existing Bitcoin-addressed sites while allowing their owners to migrate to an Ethereum EOA identity without an unauthenticated takeover or silent rollback.

## Current implementation boundary

The content v2 branch already contains initial BLAKE3-256 hashing, Ethereum EOA address parsing and EIP-712 manifest signatures. Those implemented areas are documented in docs/CRYPTOGRAPHY-CURRENT-STATE.md and docs/architecture/CONTENT-V2-IMPLEMENTATION-GUIDE.md.

The implementation now provides dual-signature migration records, verification of the referenced final legacy manifest, a hash-linked local checkpoint ledger, and `src/Crypt/MigrationWorkflow.py` for preparing the terminal Bitcoin manifest and orchestrating publish → independent read-back → local pin → Ethereum-registration callback. The workflow refuses to proceed if the registry read-back differs from the signed record. The registration callback is intentionally injected and is not yet a built-in SiteManager importer. Ethereum post-quantum signatures and IPFS CIDv1/BLAKE3 content v3 are tracked separately in docs/ToDo.md.

## Migration requirements

1. The old Bitcoin key must authorize the migration.
2. The new Ethereum EOA must explicitly accept the migration.
3. Both proofs must bind the exact same migration payload.
4. The payload must identify the old Bitcoin site, new Ethereum site, final legacy manifest digest, final legacy sequence/version, protocol identifier and migration sequence.
5. A migration must be terminal for the old identity in clients that recognize its checkpoint.
6. The old site remains readable as historical content. Its identity record must not be silently overwritten.
7. A fresh client must have a way to discover the newest trusted checkpoint. A manifest alone cannot prove that a peer is not withholding a newer migration record.

## Cross-signature proposal

A migration payload should contain at least:

- protocol: zirohneth-bitcoin-to-ethereum-v1
- old_identity: the exact legacy Bitcoin address
- new_identity: the normalized EIP-55 Ethereum EOA address
- final_legacy_manifest_digest: digest of the final v1 manifest using the exact legacy canonicalization and hash/signature rules
- final_legacy_sequence: the final monotonic sequence, if the legacy format has one; otherwise a separately specified terminal timestamp/checkpoint
- migration_sequence: monotonic migration number
- previous_migration_digest: zero digest for the first migration or the previous migration record digest
- created_at: informational timestamp, not the anti-rollback authority

Implemented in `src/Crypt/CryptMigration.py`: the old Bitcoin key signs the RFC 8785 canonical migration payload using the existing recoverable Bitcoin message-signature format. The new Ethereum key signs acceptance using EIP-712 typed data that includes the BLAKE3-256 payload digest and the identity/sequence linkage. Verification recovers both signers and rejects either missing or invalid signature. The final legacy manifest commitment uses SHA-256 over the legacy `json.dumps(sort_keys=True)` protected manifest representation, and `verify_final_legacy_manifest()` verifies its original Bitcoin signature as well as the digest. `signers_sign` remains in the protected legacy body because the legacy signer-policy attestation was part of the signed body.

Do not reuse the old content v2 EIP-712 signature as proof of Bitcoin ownership. Do not accept a migration containing only the new Ethereum signature.

## Terminal checkpoint and anti-rollback

A signed migration manifest cannot guarantee global freezing by itself. A malicious peer can still serve a client an older signed Bitcoin manifest if that client has never seen the migration.

The implemented `CheckpointStore` is a local, atomic, hash-linked ledger. It rejects appends without a pinned trust anchor, non-contiguous sequence numbers, replay, and a previous-digest mismatch. The first checkpoint must be pinned with `trust_checkpoint(record, expected_record_digest)` using a digest obtained out-of-band. This protects a client after it has pinned a checkpoint, but it does **not** prove that a fresh client was given the newest checkpoint. A robust network-wide policy must define how clients discover and compare terminal checkpoints. Candidate mechanisms include:

- a verifiable append-only checkpoint log;
- an on-chain registry or contract with explicit update/freeze semantics;
- a quorum or independently sourced checkpoint set with a documented trust model.

No concrete registry adapter is selected yet. The workflow requires `publish_checkpoint(record)` and `lookup_checkpoint(old_identity)` callbacks; this is an integration seam, not a network-wide registry implementation. The chosen mechanism must specify freshness, quorum, equivocation handling, chain reorganization policy if on-chain, and behavior when the checkpoint source is unavailable. A timeout or RPC failure must never be interpreted as proof that no migration exists.

Existing legacy clients cannot enforce a protocol they do not implement. The migration guarantee therefore applies only to clients that support this migration protocol and its checkpoint policy.

## Expected client behavior

- Verify the legacy final manifest with the original Bitcoin verification path.
- Verify the old-key migration authorization.
- Verify the new-key EIP-712 acceptance.
- Verify that the new identity and final legacy digest match the payload.
- Persist the terminal checkpoint and reject subsequent updates to the old identity. The local ledger primitive and ContentManager terminal-manifest guard exist. SiteManager/UI historical-mode integration remains incomplete.
- Keep the old site readable in historical/read-only mode.
- Display the new Ethereum identity and a verifiable link between old and new identities.
- Reject missing, mismatched, replayed, stale or superseded proofs.

## Required adversarial tests

- Old Bitcoin signature missing or invalid.
- New Ethereum acceptance signature missing or invalid.
- Old/new signatures bind different payloads.
- Wrong old Bitcoin address or new Ethereum address.
- Final manifest digest mismatch.
- Replayed migration sequence or previous-digest mismatch.
- Peer serves a pre-migration manifest after the client has stored the terminal checkpoint.
- Fresh client is given an older checkpoint while a newer checkpoint exists.
- Checkpoint source is unavailable, inconsistent or equivocating.
- A malicious third party attempts to migrate a site without the old key.

## Workflow API and safety boundaries\n\n`prepare_migration(site, bitcoin_private_key, ethereum_private_key)` builds a final Bitcoin root manifest with explicit historical/target metadata and returns it with a dual-signed record. It refuses sites with `includes` or `user_contents`, because their submanifest signer lifecycle is not migrated yet. `commit_migration(...)` persists the final root manifest, publishes the record through an injected registry adapter, reads it back independently, pins the verified checkpoint locally, marks the old Site object as historical, and finally invokes an injected Ethereum-site registration callback. The callback must be idempotent: a retry after successful publication may invoke it again.\n\nThe orchestration API does not itself choose a chain, deploy a registry, copy site data, or implement Ethereum SiteManager registration. It is therefore not yet a turnkey migration command. The old site remains on disk and keeps its Bitcoin address.\n\n## Remaining work

See docs/ToDo.md for implementation tasks. No global freeze, ownership transfer or rollback protection should be claimed until the checkpoint discovery policy is implemented and adversarial tests pass.
\n\nThe current test additions cover signature binding, legacy signer-policy attestation, checkpoint sequencing, registry read-back ordering and retry behavior. They have not been executed in this environment.\n