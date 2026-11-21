# Quantum Doomsday: Legacy Content v1 Freeze and PQ Migration Plan

> **Status:** Design proposal / documentation only. No freeze, archival, signature migration, or PQ cryptography is implemented by this document.

## 1. Purpose and trigger

Define a conservative response for legacy Content v1 sites whose update authorization depends on Bitcoin-address/ECDSA-era cryptography, and a forward-looking path for Content v2+ identities and signatures.

“Quantum Doomsday” is a project shorthand for a cryptographic transition emergency, not a calendar date or a prediction that Bitcoin addresses have already been broken.

The emergency trigger must be based on a documented, credible assessment that cryptographically relevant quantum capability makes attacks against the relevant public-key signature scheme **imminent**, even if no practical attack against Bitcoin addresses has yet occurred. Trigger criteria, who can declare the state, review cadence, and emergency-release process must be specified and publicly documented before enabling this mode. Avoid relying on a single headline, speculative timeline, or unverified claim.

## 2. Legacy v1 update lockdown

At and after the declared trigger, ZirohNeth clients should **block acceptance of new updates to Content v1 sites by default**.

- Show a prominent warning explaining that the legacy authorization scheme is considered at imminent risk.
- Do not silently accept, download-and-apply, or publish an update as the normal path.
- Require a deliberate user action to proceed with a risky legacy update, with a clear second confirmation describing the consequence: the update may be forged or malicious and could replace locally trusted content.
- Remembering a user's choice must be explicit, scoped, revocable, and clearly surfaced. A blanket preference must not silently weaken protections for every site.
- Keep ordinary visiting/reading of already cached or locally archived v1 content distinct from authorizing updates. Reading a frozen snapshot does not require trusting future v1 signatures.
- Provide a safe way to cancel, inspect the current locally accepted version, and preserve backups before any opt-in update.
- Do not confuse a signature-valid legacy update with a quantum-safe update after the emergency trigger.

The warning/lockdown should be policy-driven and testable. Emergency status changes must be auditable, with an explicit policy version and source of the trigger assessment.

## 3. Freeze and archive current v1 sites

When the emergency trigger is declared, the client should be prepared to preserve the currently accepted state of v1 sites as an archival snapshot.

Proposed archival workflow:

1. Identify the locally accepted v1 site state at the freeze point. Record site address, accepted manifest/content identifier, timestamp, client version, and relevant verification outcome.
2. Preserve the original content.json and original site files as received. Do not modify the historical manifest or manufacture an owner signature.
3. Create an internal Pijul repository/archive for the frozen snapshot and its subsequent archival history. The internal archive is a local/peer retention format, not a replacement for the original site's authority or identity.
4. Preserve provenance: mark which files and metadata came from the original v1 site, which archival changes were created by the local node, and which signatures were actually verified. Never imply that an archival-node signature is the legacy site owner's signature.
5. Keep the frozen baseline read-only from the ordinary v1 update path. Later local annotations, fixes to archival metadata, or snapshotting operations must not mutate the baseline silently.
6. Retain the ability to export/reconstruct the original frozen snapshot and inspect its provenance.

### 3.1 Research item: importing a snapshot without the site-owner signature

The desired archive seed should not require a new signature from the original v1 site owner, because the owner may be unavailable and legacy owner signatures are precisely the trust mechanism being deprecated.

**This is an unresolved implementation investigation, not an assumed Pijul capability.** Research Pijul's change creation, author identity, signing/verification, import, unrecorded working-tree, and patch application semantics. Determine whether an archive node can create a repository from the snapshot using its own archival identity (or an appropriate unsigned/local-only import mechanism), while preserving the original v1 manifest/signature as evidence and making provenance unambiguous.

Do not disable Pijul verification globally, forge or impersonate the original owner, or claim that a Pij change is unsigned/PQ-safe until verified against Pij's actual behavior and version. Document the chosen mechanism, limitations, interoperability, and tests in a follow-up implementation contract.

## 4. Post-freeze snapshotting and retention

From the trigger onward, archival peers should snapshot the frozen v1 baseline and any explicitly authorized archival additions/metadata into Pijul history.

- Keep original frozen content recoverable; avoid destructive rewriting of the archive.
- Distinguish the original baseline from post-freeze archival commits/changes and from any user-authorized risky v1 update imported after warning.
- Snapshotting should be repeatable and content-verifiable; record digests and provenance for each import.
- A peer may seed archival data without representing itself as the historical site owner. Peer retention/availability is a separate property from publisher authorization.
- Document retention, replication, export, corruption detection, and recovery behavior. “Archived” must not be described as permanently available unless independent replicas and a retention mechanism actually provide that guarantee.

## 5. Quantum-safe signatures for v2 and later

Content v2 (Ethereum-address identity) and future versions must have a forward migration path to post-quantum signing and verification. Ethereum's current EOA/ECDSA signatures must not be described as PQ-safe, and anchoring a digest on Ethereum does not make that digest quantum-safe.

Design requirements:

- Introduce explicit, versioned signature-suite identifiers and key encodings. Algorithm choice must be part of the signed domain/manifest/checkpoint data.
- Evaluate standardized post-quantum digital-signature schemes, initially including **ML-DSA (FIPS 204)**, for site-update authorization and checkpoint signatures. Review library maturity, implementation safety, test vectors, performance, signature/key sizes, interoperability, and audit status before selecting a production profile.
- Consider hybrid transition signatures (classical plus PQ) only with a clearly specified verification policy, domain separation, and downgrade prevention. Do not assume a hybrid is secure merely because two signatures are present.
- Define PQ key registration, authorization binding to existing v2 site identity, key rotation, recovery, revocation, and historical verification. A migration must not permit an attacker with a compromised legacy key to unilaterally install a new PQ key after the emergency trigger.
- Support explicit algorithm agility, but fail closed for unknown, deprecated, or disallowed signature suites. Do not silently fall back to v1/ECDSA authorization.
- Keep the content hash/addressing layer separate from signature authentication. Hashes prove byte integrity against a known digest, not publisher authority.
- Treat Ethereum/PQ transition work as its own adapter/roadmap: investigate protocol-level PQ account/signature changes and any smart-contract verification or alternative authorization mechanisms; verify their real deployment status and constraints before depending on them. Do not promise native Ethereum PQ signatures based on speculative roadmap statements.

## 6. Migration and user experience

- Explain which sites are legacy v1, which are frozen locally, and which use a PQ-capable signature profile.
- Provide a clear, user-visible trust state for historical owner signatures, archival-node provenance, current authorization policy, and PQ verification.
- Preserve legacy site identifiers and content for navigation/compatibility; a freeze is an update-policy change, not automatic identity destruction or a forced redirect.
- Offer a documented export and recovery path for frozen sites and archive repositories.
- Keep user opt-in to risky legacy updates separate from migration/archival consent.

## 7. Proposed implementation work items

These are planning tasks; no runtime behavior is implied.

- [ ] **QD-01** Define the emergency trigger, evidence sources, declaration authority, public notice, and review/rollback governance.
- [ ] **QD-02** Implement default v1 update lockdown with warning UX, deliberate per-site risk confirmation, cancel path, and safe backup.
- [ ] **QD-03** Specify the frozen-v1 snapshot format and provenance metadata, preserving original manifest/signature/files.
- [ ] **QD-04** Investigate Pijul archive seeding without the original site-owner signature; publish a technical decision and test proof-of-concept before choosing a mechanism.
- [ ] **QD-05** Implement archive import and Pijul snapshot history with clearly separated original baseline, local archival identity, and subsequent changes.
- [ ] **QD-06** Define archival retention/replication, verification, export, and recovery contracts.
- [ ] **QD-07** Evaluate ML-DSA and candidate hybrid profiles for v2+ update authorization, including key migration, policy, rotation, revocation, and interoperability.
- [ ] **QD-08** Audit Ethereum/PQ transition assumptions and document feasible adapters/verification paths based on deployed and testable capabilities.
- [ ] **QD-09** Add adversarial tests for forged v1 updates, consent bypass, rollback, downgrade, signature-suite confusion, archive provenance, and damaged snapshots.

## 8. Acceptance and safety criteria

1. In emergency mode, v1 updates are blocked by default and cannot be accepted without explicit user risk confirmation.
2. A normal update path, background updater, peer sync, or UI shortcut cannot bypass the lockdown.
3. User consent is specific and revocable; the client displays the risk before accepting a legacy update.
4. Frozen snapshots preserve the original manifest and signatures without impersonating the site owner.
5. Archival Pijul history clearly distinguishes original site content/provenance from changes made by archive maintainers.
6. The archive seed mechanism is proven against the supported Pijul version, not inferred from documentation or assumed behavior.
7. PQ-capable v2+ updates verify their declared signature suites and authorization policy; unknown/disallowed suites and silent downgrade are rejected.
8. PQ key migration cannot be authorized solely by a legacy key after the emergency state unless a separately reviewed recovery policy explicitly allows it.
9. Content hashes, signature verification, archive provenance, and chain anchoring are described as separate security properties.
10. Read-only access to previously accepted/cached v1 content remains distinct from trust in future updates.

## 9. Related design documents

- [Content v3 architecture and roadmap](CONTENT-V3-ROADMAP.md): Pijul-backed history, signed checkpoints, PQ checkpoint profile, and optional Ethereum/Zond adapters.
- [Content v1 manifest seeding for v2 sites](V1-MANIFEST-SEEDING-V2.md): compatibility seeding of the verified terminal legacy manifest for migrated sites.

This document focuses on legacy v1 update lockdown and emergency archival. Content v3 checkpoint PQ signatures and Ethereum/Zond backend integration remain complementary, separate workstreams.
