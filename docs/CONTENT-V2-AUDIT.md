# Content v2 security and compatibility audit

**Status:** static audit findings, not a test report  
**Scope:** Bitcoin-to-Ethereum identity migration, Ethereum/v2 site access, BLAKE3 integrity, update-chain validation  
**Audited revision:** `main` at the time of review (2026-11-19)  
**Related design material:** `docs/architecture/CONTENT-V2-IMPLEMENTATION-GUIDE.md`, `docs/CRYPTOGRAPHY-CURRENT-STATE.md`, and the migration implementation under `src/Crypt/`

This document records implementation risks found during a source review. Severity describes potential impact, not exploitability demonstrated by a runtime test. No test suite, live migration, multi-peer synchronization, or cross-client interoperability test was run as part of this audit.

## Executive summary

The v2 direction is coherent: retain the Bitcoin legacy verifier, introduce an Ethereum EOA identity, authenticate manifests with EIP-712, canonicalize JSON with RFC 8785, and use BLAKE3 for v2 content digests. The main risks are at the boundaries between those systems:

1. Legacy file bytes must be authenticated **before** they are copied and re-signed under the new identity.
2. Migration must be crash-safe and must not silently reuse an unrelated pre-existing Ethereum site.
3. Signed update-chain fields must be checked against trusted local state, not merely included in a signature.
4. Peer availability hints must distinguish digest algorithms.
5. A new client cannot infer global freshness from a valid signature alone.
6. The dependency declaration must be valid for installation.

## Findings

### C2-01. Legacy file contents are copied without first validating each file against the signed legacy manifest

**Severity:** Critical  
**Area:** migration integrity  
**Relevant code:** `src/Crypt/MigrationWorkflow.py`, especially `_copy_manifest_files()` and `_register_ethereum_site()`

The migration workflow copies files selected by the legacy manifest, then creates/signs the Ethereum v2 manifest using BLAKE3 over the copied files. The copy stage does not first establish that each copied file's bytes match the legacy manifest's SHA-512-truncated digest.

An altered local file could therefore be copied and then receive a fresh Ethereum signature and BLAKE3 digest. The new manifest would authenticate the altered bytes, even though those bytes were not the content authorized by the old Bitcoin identity.

**Recommendation**
- Before copying, verify every present required file against its legacy manifest digest using the exact legacy algorithm and encoding.
- Fail closed on a mismatch.
- Define explicit behavior for absent optional files; do not silently treat a required missing file as valid.
- Only after successful legacy verification should the workflow compute BLAKE3 and create the v2 manifest.
- Add a test that tampers with a legacy file immediately before migration and asserts that migration aborts without publishing a v2 site.

### C2-02. Migration can leave a partial destination that the same workflow cannot resume

**Severity:** Critical  
**Area:** crash consistency and recovery  
**Relevant code:** `src/Crypt/MigrationWorkflow.py`, destination creation/copy and registration flow

The workflow populates the destination before the final v2 manifest is registered. If the process stops after copying files but before writing a valid v2 manifest, a retry may encounter a non-empty destination without a valid manifest and abort. This conflicts with the intended idempotent/retryable behavior.

**Recommendation**
- Perform migration in a dedicated staging directory.
- Persist a small migration journal with source identity, destination identity, legacy manifest digest, and completed phase.
- Verify all staged files and signatures before promotion.
- Promote atomically where the filesystem permits it; otherwise use a recoverable rename/marker protocol.
- On restart, either resume a matching staging operation or safely discard it. Never overwrite an unrelated destination.
- Add fault-injection tests at every phase boundary.

### C2-03. A pre-existing Ethereum destination can be reused without proving that it belongs to this migration

**Severity:** High  
**Area:** identity binding  
**Relevant code:** `src/Crypt/MigrationWorkflow.py`, `_register_ethereum_site()`

The existing-destination path checks for a valid v2 manifest and expected Ethereum identity, but does not establish that the destination manifest is cryptographically linked to the Bitcoin source and this migration proof. A valid, unrelated site at the destination could be reused.

**Recommendation**
- Require a signed migration relationship in the destination manifest, including the normalized legacy address and digest of the terminal legacy manifest/proof.
- Verify the relationship before treating an existing destination as an idempotent completion.
- If the destination is valid but unrelated, stop and require an explicit conflict-resolution workflow. Do not silently merge or reuse it.
- Test both a matching already-completed migration and an unrelated valid v2 destination.

### C2-04. Signed update-chain fields are not fully enforced against trusted state

**Severity:** High  
**Area:** anti-rollback and fork detection  
**Relevant code:** `src/Crypt/CryptEthereum.py`, `src/Content/ContentManager.py`

The EIP-712 payload includes fields such as `sequence` and `previous_update_digest`. However, the reviewed content-verification path does not appear to enforce a complete continuity rule against a trusted local checkpoint. In particular, signature validity alone does not prove that a manifest is the newest manifest or that it extends the previously trusted manifest.

The existing `modified` comparison is not a substitute for a monotonic, digest-linked update chain.

**Recommendation**
- Persist a trusted v2 checkpoint per site: sequence, manifest digest, and identity.
- For a normal update, require the expected next sequence and an exact `previous_update_digest` match.
- Reject sequence rollback, unexplained gaps, and conflicting branches unless an explicit recovery procedure is invoked.
- Define first-contact behavior for clients with no checkpoint. A signature proves authorization, not freshness.
- Add tests for replay, skipped sequence, same-sequence fork, rollback, and valid sequential update.

### C2-05. First-contact clients cannot establish global freshness from the signed manifest alone

**Severity:** High  
**Area:** discovery and freshness

A client that has never seen a site has no trusted previous digest against which to compare a validly signed manifest. A peer can potentially serve an older, still-valid signed manifest. A local checkpoint protects a client after it has observed a state, but does not by itself solve first-contact freshness.

Two distinct migration proofs signed by the old key for different destinations are also a conflict that local first-seen-wins state cannot resolve globally.

**Recommendation**
- Document the first-contact trust model and its limitations.
- Consider independent freshness witnesses, transparency/logging, quorum-based observations, or another explicit conflict-resolution mechanism.
- Surface an honest UI state such as “signature valid; freshness not independently established” where appropriate.
- Define how clients report and recover from conflicting signed migration proofs.

### C2-06. Peer hashfield does not namespace availability hints by digest algorithm

**Severity:** High  
**Area:** peer discovery and transfer efficiency  
**Relevant code:** `src/Peer/PeerHashfield.py`

The hashfield stores a short prefix (16 bits) without carrying the digest algorithm/version namespace. SHA-512-derived and BLAKE3-derived prefixes can collide. This can make a peer appear to have a file when it only has a file whose digest under another algorithm shares the prefix.

Full digest verification should still reject incorrect bytes, so this is primarily a false-positive availability and transfer-efficiency problem, not proof that the hashfield alone accepts corrupted content.

**Recommendation**
- Namespace hashfield entries by algorithm/version, or introduce an explicitly versioned hashfield encoding.
- Preserve legacy decoding for old peers during a defined compatibility period.
- Treat hashfield matches only as availability hints, never as integrity proof.
- Add cross-algorithm collision and mixed-version peer tests.

### C2-07. Migration digest fields should identify their hash algorithm explicitly

**Severity:** Medium  
**Area:** protocol clarity and cross-language interoperability  
**Relevant code:** `src/Crypt/CryptMigration.py` and migration manifest schema

The migration flow uses different algorithms for different objects (including SHA-256 for a legacy-manifest body digest and BLAKE3 for v2 content). The algorithm choice may be defined implicitly by the current implementation, but a digest field without an explicit algorithm identifier is easy for future implementations to misinterpret.

**Recommendation**
- Add a protocol-defined algorithm identifier for each migration digest field, for example `final_legacy_manifest_digest_algorithm: "sha256"`.
- Specify byte encoding, canonicalization, truncation (if any), and domain separation for every digest.
- Keep existing v1/v2 behavior immutable; introduce schema changes through an explicit versioned migration format rather than silently changing field meaning.

### C2-08. Dependency declarations in requirements.txt appear malformed

**Severity:** Blocker for reproducible installation  
**Area:** packaging  
**Relevant file:** `requirements.txt`

The final dependency declaration was observed as a single line containing literal escaped `\\n` sequences between package specifications, rather than separate newline-delimited requirements. This can cause pip to parse the line as an invalid requirement instead of installing the intended packages.

**Recommendation**
- Put each package requirement on its own physical line.
- Validate with a clean environment using `python -m pip install -r requirements.txt`.
- Add a packaging/CI check so this does not recur.

Expected layout:

```text
blake3>=0.4.1
eth-account>=0.11.0
rfc8785>=0.1.4
```

Confirm the exact dependency pins and supported Python versions before release.

### C2-09. Migration currently excludes manifests using includes/user_contents

**Severity:** Medium  
**Area:** migration coverage  
**Relevant code:** `src/Crypt/MigrationWorkflow.py`, migration preflight

The migration preflight rejects legacy manifests containing `includes` or `user_contents`. This is a defensible fail-closed limitation, but it means migration does not cover all site layouts, especially layouts that rely on included or user-specific content.

**Recommendation**
- Keep the rejection explicit and explain it to the user before signing or copying anything.
- Document which site classes are currently migratable.
- Design a separate migration plan for included/user content, including ownership, authorization, and destination mapping. Do not flatten these structures without preserving their trust boundaries.

### C2-10. Ethereum site transport restrictions need explicit compatibility documentation

**Severity:** Medium  
**Area:** connectivity  
**Relevant code:** `src/Connection/ConnectionServer.py` and site/peer transport policy

The reviewed policy rejects onion peers for Ethereum-addressed sites. This may be an intentional transport restriction, but it narrows connectivity for users who depend on Tor-only peers or environments. It should not be confused with a limitation of Ethereum identity itself.

**Recommendation**
- Document exactly which transports are permitted for Ethereum sites and why.
- Distinguish global Tor availability from per-site onion-peer restrictions.
- Test expected behavior for clearnet, Tor-enabled clients, and mixed peer sets.
- If the restriction is temporary, make that status and migration path explicit.

## Ethereum/v2 access review

The basic address path appears to be wired through the dashboard URL helper, the backend request route, and `SiteManager` address normalization/validation. This is a positive result, but it is not proof of end-to-end site access.

The current identity scheme is EOA/secp256k1-oriented and does not provide ERC-1271 smart-contract-wallet or multisig signature verification. That is a supported-scope limitation, not necessarily a defect, provided it is documented.

Before release, test the full route from a browser URL through request routing, site lookup, manifest verification, file serving, and peer discovery using both legacy Bitcoin and Ethereum v2 sites.

## Recommended remediation order

1. Fix the malformed dependency file and validate clean installation.
2. Verify legacy file bytes before migration.
3. Make migration staged, recoverable, and conflict-safe.
4. Bind existing Ethereum destinations to the exact source migration proof.
5. Enforce sequence and previous-digest continuity against trusted checkpoints.
6. Define first-contact freshness and migration-fork handling.
7. Version/namespace peer hashfields by digest algorithm.
8. Document unsupported migration layouts and transport restrictions.
9. Add cross-version and multi-client integration tests.

## Validation still required

This is a static source audit. The following remain unverified:
- Unit and integration test execution.
- Actual Bitcoin-to-Ethereum migration on a disposable site.
- Crash recovery at each migration phase.
- Multi-client replay, rollback, and fork behavior.
- Mixed legacy/v2 peer hashfield interoperability.
- Browser-to-backend access to real Ethereum v2 sites.
- Clean dependency installation and supported Python-version matrix.

Do not interpret this document as a claim that these scenarios have already been reproduced at runtime.
