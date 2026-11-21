# ZirohNeth Content v3 Roadmap

> Status: design proposal. This document records intended architecture and implementation order. It does not claim that planned components are implemented.

## 1. Goals and responsibility boundaries

Content v3 replaces publishing a conventional site directory as a self-contained snapshot with publishing a Pijul-backed history plus a manifest of immutable content objects.

- **Pijul:** logical site history, changes, dependencies, channels and checkout.
- **BLAKE3-256:** content addressing and integrity for external files and transport objects.
- **Iroh:** peer-to-peer transport and optional per-object pinning/availability.
- **Signed checkpoints:** publication sequence, history linkage, authorization policy and independent authenticity verification.
- **Ethereum and Zond:** optional authorization coordination and/or checkpoint anchoring backends. Neither is required to understand or reconstruct the content format.

The working directory is the materialized site root, not the authoritative publication unit. Publishing records Pijul changes and a manifest that references external objects.

## 2. Publication model and file classes

A v3 site consists of:
1. A Pijul repository containing logical history and ordinary, reasonably sized files.
2. A versioned manifest mapping site-relative paths to external content objects.
3. Immutable external objects addressed by BLAKE3-256.
4. Signed publication checkpoints binding site identity, publication sequence, previous checkpoint, Pijul state/change set, manifest and authorization policy.

| Class | In Pijul history | External object | Behavior |
|---|---:|---:|---|
| Ordinary files | Yes | No, by default | Versioned normally |
| Bigfiles | No | Yes | Retrieved when required or requested |
| Optional files | No | Yes | Retrieved on demand, subject to client/site policy |

The exact size threshold and classification rules remain open. Classification must be deterministic or explicitly recorded; clients must not silently disagree about whether a path is external.

### 2.1 External object manifest

Each external entry should include:
- normalized site-relative path;
- BLAKE3-256 digest of exact object bytes;
- byte length;
- media type (advisory, not a trust decision);
- class: bigfile or optional;
- optional retrieval/availability hints.

The digest identifies bytes, not availability. A missing object is an availability failure, not proof that the manifest is invalid. Downloaded bytes must be verified before being exposed to the site.

Pinning is a per-object availability/storage commitment. Pin state is not part of immutable content identity. The protocol should support independent peers pinning the same object and report observed availability without inventing guarantees.

## 3. Pijul history and append-only publication

Pijul represents logical changes and reconstructs the site tree. Its change graph is not necessarily a linear Git-style commit sequence: independent changes can have dependencies and may be applied in different valid orders.

The v3 publication layer therefore defines its own monotonically increasing publication sequence. Each accepted checkpoint binds:
- stable site identifier;
- publication sequence number;
- previous accepted checkpoint digest;
- Pijul channel/state reference and exact newly announced changes/dependencies;
- manifest digest;
- authorization-policy version/digest;
- signatures and algorithm identifiers.

A peer that accepted a checkpoint must reject later announcements that silently rewrite or omit accepted history. A publisher may remove a path from the current tree through a legitimate deletion, but that does not erase earlier publication records or historical object references retained by peers.

### 3.1 Storage limitation

Pijul's change model does not make a local repository directory physically undeletable. An owner controls their own storage and can remove local data. Append-only behavior is enforced by receiving peers and independent archival/retention replicas, not by claiming the owner's disk is immutable.

Peers retain accepted checkpoints and the changes/objects required by their configured retention policy. A new peer can reconstruct old history only to the extent that peers still provide the required changes and objects.

### 3.2 Do not conflate identifiers

Keep distinct:
- native Pijul change identifiers;
- Pijul's native version/state identifier;
- BLAKE3 digest of a serialized transport object or external file;
- v3 publication checkpoint digest.

They serve different purposes. BLAKE3-256 identifies content and verifies bytes; it is not a digital signature and does not authenticate a publisher.

Pijul's native version identifier has separate cryptographic assumptions, including an elliptic-curve-based component in the documented construction. Preserve native identifiers for Pijul operation, but do not treat them alone as a post-quantum authenticity proof. Bind them into an independently signed v3 checkpoint.

## 4. Peer synchronization

Proposed client flow:
1. Resolve and obtain the latest available signed site checkpoint.
2. Verify signatures, site identity, policy version and linkage to the locally accepted checkpoint.
3. Determine missing Pijul changes and dependencies.
4. Fetch required change objects through the selected transport, including Iroh where integrated.
5. Verify transport-object integrity and Pijul change identity before importing/applying.
6. Fetch and verify the manifest.
7. Materialize the Pijul working tree using checkout.
8. Fetch required external objects and verify BLAKE3-256 before use.
9. Fetch optional objects only when requested or required by loading policy.
10. Serve the materialized site and optionally provide objects to other peers.

Iroh integration is new work. Do not assume existing Pijul clone/pull automatically uses Iroh. Prefer transferring required changes and dependencies as explicit objects and reconstructing/updating the local Pijul repository. Do not treat the entire repository metadata directory as an opaque blob unless a separately specified interoperable snapshot format is designed.

A BLAKE3 digest for a serialized transport object is distinct from the native Pijul change identifier. Both may be checked for their respective purposes.

## 5. Mandatory client-side Publication Gate

Publishing clients must run a mandatory local Publication Gate before publication data is recorded, signed, announced or uploaded.

It must inspect both:
- files entering Pijul history; and
- external files to be uploaded to Iroh or referenced by the manifest.

Minimum policy categories:
- detect likely credentials, private keys, tokens and configured secret patterns;
- reject explicitly excluded/private paths and file classes;
- apply configured content and size rules;
- validate normalized paths and manifest consistency;
- scan external objects before upload and verify their digest/size against the manifest;
- fail closed when a required scanner or mandatory validation step cannot run.

The gate should provide actionable diagnostics. Any permitted override must be explicit and auditable locally and must not bypass protocol invariants.

### 5.1 Security boundary

A client-side gate protects users of compliant publishing clients against accidental publication. It cannot prove that a malicious or modified publisher ran the gate. Receiving peers may therefore apply independent admission/scanning policies before serving or pinning content. Peer-side rejection is defense in depth, not a substitute for the publisher-side gate.

No scanner can perfectly identify every secret or private datum. The protocol must support explicit exclusions and user-defined policy, and warn that published content may be replicated and retained by other peers.

The gate cannot retroactively delete data already distributed. Removing a path from a later site version does not revoke copies already received by peers.

## 6. Signed checkpoints and post-quantum authorization

Every v3 publication checkpoint must be independently verifiable without relying solely on Pijul's native version identifier or a blockchain transaction.

The signed checkpoint should bind a canonical encoding of:
- protocol/checkpoint format version;
- site identifier;
- publication sequence and previous checkpoint digest;
- Pijul channel/state reference and announced change set;
- manifest digest;
- authorization-policy digest/version;
- signature algorithm identifiers and signer key identifiers.

A post-quantum signature path is required. ML-DSA-87 is a candidate for the initial profile, subject to implementation review, library maturity, test vectors, key encoding, canonical serialization and interoperability tests. Algorithm agility must be explicit; clients reject unknown or disallowed algorithms rather than silently downgrade.

BLAKE3-256 remains the content hash. It is not the PQ signature mechanism.

### 6.1 Multisignature policy

Define an algorithm-neutral SiteOwnershipPolicy with:
- M-of-N threshold;
- signer identifiers and public-key material/references;
- permitted signature algorithms;
- key activation, rotation and revocation rules;
- policy version and previous-policy linkage;
- rules for authorizing policy changes.

A collection of independent ML-DSA signatures can be the initial M-of-N design. Do not describe this as a threshold or aggregated ML-DSA signature scheme.

Key rotation must preserve verification of historical checkpoints. A new policy must be authorized under the currently accepted policy, and each checkpoint must retain the policy version that authorized it.

## 7. Ethereum and Zond

Ethereum and Zond are optional backends for authorization coordination and/or anchoring checkpoint digests. Core content format and peer synchronization must remain usable without either chain.

- **Ethereum:** may provide conventional smart-contract multisig and checkpoint anchoring. Existing account/signature infrastructure must not be represented as post-quantum merely because a checkpoint digest is anchored on-chain.
- **Zond (QRL 2.0):** investigate post-quantum account/signature and EVM-compatible capabilities for a PQ authorization adapter. Verify target network, protocol version, supported verification paths, deployment status, costs and audit status before depending on it.

A blockchain anchor proves that a digest was recorded under that chain's consensus rules. It does not replace client-side verification of required checkpoint signatures and policy.

## 8. PR implementation roadmap

This is a proposed decomposition. Each PR adds tests and documentation for its own contract and must not claim future stages are implemented.

| PR | Scope | Expected result |
|---|---|---|
| V3-01 | Manifest format and BLAKE3 object references | Versioned canonical manifest; path rules; ordinary/bigfile/optional classification; digest and size validation |
| V3-02 | Pijul publication history and append-only checkpoints | Pijul changes/dependencies mapped to publication sequence; previous-checkpoint linkage; peer-side rollback/fork detection |
| V3-03 | Pijul/Iroh transport and peer synchronization | Explicit change/object transfer, verification, import/apply, checkout and offline catch-up |
| V3-04 | Bigfiles, optional files and per-object pinning | Individual object retrieval, on-demand optional assets, pin/unpin and replica/availability reporting |
| V3-05 | Client-side Publication Gate | Mandatory pre-publication scanning and validation for Pijul files and external objects; fail-closed behavior |
| V3-06 | PQ Signed Checkpoints | Canonical checkpoint encoding, ML-DSA profile, key identifiers, verification, policy versioning and rotation |
| V3-07 | Ethereum and Zond adapters | Optional anchoring/authorization integrations behind backend interfaces, tested independently |
| V3-08 | Migration and adversarial testing | Legacy-site migration, compatibility strategy, recovery, rollback/fork, tampering, missing-object and malicious-publisher tests |

## 9. Acceptance criteria

1. A fresh peer reconstructs a site from available Pijul changes, dependencies, checkpoints and manifest.
2. A peer catches up after being offline without losing previously accepted history.
3. Removing a path from the current tree does not erase historical records already retained by peers.
4. A peer rejects a checkpoint that rewrites, skips or forks its accepted chain without an explicitly authorized recovery procedure.
5. Altered external bytes fail BLAKE3 verification and are never exposed as the referenced object.
6. Missing optional objects do not prevent unrelated content from being materialized.
7. Missing required objects produce a clear availability error.
8. Pinning is per object; availability reporting does not claim unobserved replicas.
9. Publication is blocked when mandatory client-side validation fails or cannot run.
10. A modified publisher bypassing its local gate is not assumed safe; peer-side policy can independently reject or quarantine content.
11. Invalid, unknown, insufficient or disallowed signatures block checkpoint acceptance.
12. Key rotation preserves historical verification and cannot silently rewrite prior authorization.
13. Ethereum/Zond outages do not make the core content format or local verification unusable.
14. Migration preserves the legacy site as a recoverable source until the migrated v3 site is verified.

## 10. Non-goals and open questions

Not guaranteed by the initial design:
- permanent availability of every historical object;
- perfect detection of every secret or harmful payload;
- retroactive deletion of data already replicated to peers;
- Ethereum or Zond availability for ordinary synchronization;
- replacement of Pijul's native change identifiers or redesign of its internal cryptography;
- use of Iroh transport identity as the site's publication authority.

Questions for V3-01/V3-02:
- canonical manifest encoding and version negotiation;
- external-file threshold and deterministic classification rules;
- checkpoint digest encoding and domain separation;
- retention/archival policy for changes, manifests and objects;
- fork resolution and authorized recovery after conflicting checkpoints;
- single-writer versus multisig/delegated publication sequence;
- Iroh APIs and object-size limits for the selected implementation;
- secret-scanner baseline, exclusions and override policy;
- exact ML-DSA library/profile and Zond network/version for the adapter.

---

**Implementation discipline:** document unsupported capabilities as planned work. Do not simulate Iroh integration, PQ verification, multisig, permanent retention or blockchain anchoring before they exist and have tests.
