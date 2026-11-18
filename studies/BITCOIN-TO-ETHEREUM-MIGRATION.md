# Bitcoin → Ethereum site migration study

> **Status:** design research only. The migration protocol is not implemented.
>
> **Scope:** preserve existing Bitcoin-addressed sites while allowing their owners to migrate to an Ethereum EOA identity without an unauthenticated takeover or silent rollback.

## Current implementation boundary

The content v2 branch already contains initial BLAKE3-256 hashing, Ethereum EOA address parsing and EIP-712 manifest signatures. Those implemented areas are documented in docs/CRYPTOGRAPHY-CURRENT-STATE.md and docs/architecture/CONTENT-V2-IMPLEMENTATION-GUIDE.md.

This study retains only the still-unimplemented Bitcoin-to-Ethereum ownership transfer and anti-rollback design. Ethereum post-quantum signatures and IPFS CIDv1/BLAKE3 content v3 are tracked separately in docs/ToDo.md.

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

The old Bitcoin key signs the canonical migration payload using the existing legacy Bitcoin message-signature format. The new Ethereum key signs acceptance using the EIP-712 domain and typed data. Both signatures must be independently verified and must bind the exact same payload digest.

Do not reuse the old content v2 EIP-712 signature as proof of Bitcoin ownership. Do not accept a migration containing only the new Ethereum signature.

## Terminal checkpoint and anti-rollback

A signed migration manifest cannot guarantee global freezing by itself. A malicious peer can still serve a client an older signed Bitcoin manifest if that client has never seen the migration.

A robust policy must define how clients discover and compare terminal checkpoints. Candidate mechanisms include:

- a verifiable append-only checkpoint log;
- an on-chain registry or contract with explicit update/freeze semantics;
- a quorum or independently sourced checkpoint set with a documented trust model.

The chosen mechanism must specify freshness, quorum, equivocation handling, chain reorganization policy if on-chain, and behavior when the checkpoint source is unavailable. A timeout or RPC failure must never be interpreted as proof that no migration exists.

Existing legacy clients cannot enforce a protocol they do not implement. The migration guarantee therefore applies only to clients that support this migration protocol and its checkpoint policy.

## Expected client behavior

- Verify the legacy final manifest with the original Bitcoin verification path.
- Verify the old-key migration authorization.
- Verify the new-key EIP-712 acceptance.
- Verify that the new identity and final legacy digest match the payload.
- Persist the terminal checkpoint and reject subsequent updates to the old identity.
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

## Remaining work

See docs/ToDo.md for implementation tasks. No global freeze, ownership transfer or rollback protection should be claimed until the checkpoint discovery policy is implemented and adversarial tests pass.
