# Content v1 Manifest Seeding for v2 Sites

## Status

**Implementation in review:** [PR #23](https://github.com/Floflis/ZirohNeth/pull/23) adds the first runtime implementation and focused tests. The PR is still a draft and its tests have not yet been executed. All task checkboxes remain open until the evidence requirements in `AGENTS.md` are met.

## Problem

A site migrated from a Bitcoin-addressed Content v1 identity to an Ethereum-addressed Content v2 identity may still be visited through its original Bitcoin address. The migration protocol in the Content v2 workstream advertises the Ethereum destination in the terminal, signed v1 `content.json`, but the new v2 site/peers must reliably retain and serve that legacy manifest to visitors using the old address.

This is a compatibility-seeding requirement, distinct from the migration proof and from v2 manifest signing.

## Goal

When a v2 site is seeded by a peer, the seeding peer must also make the site's authorized terminal v1 compatibility manifest available for the original Bitcoin address, where such a migration manifest exists. This lets v1-address visitors retrieve the migration metadata instead of depending on a single migration publisher.

## Scope and compatibility boundaries

- Preserve the original Bitcoin identity/address and its signature verification rules for v1.
- Preserve the Ethereum identity/address and EIP-712/BLAKE3 verification rules for v2.
- The v1 manifest must be the exact, verified terminal migration manifest authorized by the Bitcoin identity, not a reconstructed, unsigned, or arbitrary older manifest.
- Do not generate or fabricate migration proofs, or infer a migration merely from an Ethereum site sharing content.
- Do not permit a v2 peer to sign or mutate a manifest on behalf of the historical Bitcoin identity.
- Legacy clients cannot parse the v2 migration envelope. A client-side redirect requires a compatible migration-aware client; a site-level redirect/shim is a separate UX compatibility mechanism and must be evaluated explicitly.
- If no valid terminal v1 migration manifest is available, normal v2 seeding continues and no v1 migration data is advertised.

## Implementation snapshot (PR #23)

The current implementation stores the exact terminal Bitcoin-signed v1 manifest at
`migration/legacy-content.json` inside the Ethereum v2 site. The signed v2 root carries
a descriptor binding the two identities, the manifest digest, the compatibility path,
and the digest of the dual-signed migration proof. The file must be a required BLAKE3
entry in the v2 root; an ignore rule that excludes it makes migration fail.

A peer registers a historical Bitcoin-address serving alias only after it verifies
the v2 EIP-712 root, the compatibility file's BLAKE3 digest and size, the terminal v1
manifest and Bitcoin signature, the dual-signed migration record, and the local
migration checkpoint. The alias stores and serves the terminal v1 root, follows the
Ethereum site's serving state, and is announced only after verification and durable
persistence. Migration-aware clients can then use the existing old-address resolver.

**Compatibility boundary:** this serves the terminal v1 `content.json` under the old
address, allowing an updated client to validate the migration and resolve to Ethereum.
An unmodified legacy client can retrieve that file but does not understand the migration
envelope and will not automatically redirect. A signed site-level shim is not part of
this implementation.

**Evidence state:** focused unit tests have been added and a PR-triggered workflow has
been added, but no test result is claimed yet. Multi-node, restart/reseed, and separate
legacy-client integration evidence is still pending. Therefore no checkbox below is
closed by PR #23.

## Implementation tasklist

### V1 migration manifest discovery and validation

- [ ] **V1S-01** Locate and define the persisted representation and lifecycle of the terminal Bitcoin/v1 `content.json` associated with a migrated v2 site.
- [ ] **V1S-02** Validate the legacy Bitcoin signature, manifest version, migration proof, old/new identity binding, sequence and digest linkage before accepting the compatibility manifest.
- [ ] **V1S-03** Reject malformed, unsigned, conflicting, stale/non-terminal or unrelated v1 manifests; never replace the locally pinned terminal manifest with an unverified peer copy.
- [ ] **V1S-04** Make the verified terminal v1 manifest persist across restart, site re-seeding, reindexing and cache eviction (unless an explicit safe retention policy removes it).

### Peer seeding and discovery

- [ ] **V1S-05** When a peer seeds a migrated v2 site, seed/serve the verified terminal v1 `content.json` under the historical Bitcoin address as well as the v2 manifest under the Ethereum address.
- [ ] **V1S-06** Advertise compatibility availability only after the v1 manifest has been verified and durably stored; avoid announcing a v1 address with no served manifest.
- [ ] **V1S-07** Ensure legacy v1 requests can retrieve the terminal compatibility manifest from v2 seeders without changing legacy request framing or signature semantics.
- [ ] **V1S-08** Ensure v2 clients can discover and retrieve compatibility manifests from multiple peers; do not make the original migration publisher the sole availability dependency.
- [ ] **V1S-09** Reconcile peer availability, seed lifecycle, shutdown/restart and manifest updates so compatibility availability is withdrawn or refreshed accurately.
- [ ] **V1S-10** Avoid loops, address conflation or cross-site cache collisions between the Bitcoin historical identity and Ethereum destination identity.

### Visitor behavior and redirect contract

- [ ] **V1S-11** Define and implement redirect behavior for migration-aware ZirohNeth clients visiting the old Bitcoin address: validate the terminal migration proof and resolve to the Ethereum destination.
- [ ] **V1S-12** Preserve the historical site directory/address and expose an understandable migration state instead of silently rewriting identity or losing local data.
- [ ] **V1S-13** Investigate whether legacy clients can be supported through a signed site-level redirect/shim. Document limitations and do not claim old clients understand the v2 migration envelope.
- [ ] **V1S-14** Define behavior when the v1 manifest is temporarily unavailable, peers disagree, a first-contact peer withholds the terminal manifest, or the visitor is offline. Fail safely and show the historical address rather than inventing a destination.

### Tests and evidence

- [ ] **V1S-15** Unit tests for validation, persistence, retrieval, seeding advertisement, historical-address routing and redirect resolution.
- [ ] **V1S-16** Regression tests proving ordinary v1 sites and ordinary v2 sites without a migration record retain their existing behavior.
- [ ] **V1S-17** Multi-peer integration test: a migrated site is seeded by multiple v2 peers; a visitor starting from the Bitcoin v1 address obtains the exact terminal signed manifest and resolves to the Ethereum destination.
- [ ] **V1S-18** Restart/reseed and peer-unavailability tests; test conflicting/older valid v1 manifests and verify they cannot overwrite the pinned terminal manifest.
- [ ] **V1S-19** Test legacy client behavior separately from migration-aware client behavior; document any site-level shim as a distinct compatibility result.
- [ ] **V1S-20** Record exact test commands, outcomes, environment/topology, PR URL and commit SHA for each completed task. Do not close checklist items without evidence.

## Acceptance criteria

1. A migrated v2 site with a valid terminal v1 migration manifest can be seeded by multiple v2 peers.
2. The old Bitcoin address remains resolvable to the exact authorized terminal v1 manifest, with unchanged v1 verification.
3. Migration-aware visitors using the old address can validate the proof and reach the Ethereum v2 identity.
4. Missing or conflicting compatibility data fails safely; unverified data is never advertised as seedable.
5. Existing non-migrated v1 and v2 sites remain unaffected.
6. Legacy-client redirect limitations are explicitly tested and documented rather than assumed.
7. Every completed implementation task has linked PR/commit/test evidence.

## Related work

- Content v2 / Bitcoin-to-Ethereum migration: https://github.com/Floflis/ZirohNeth/pull/2
- Content v2 integrity remediation: https://github.com/Floflis/ZirohNeth/pull/8
- Content v2 hashfield namespace work: https://github.com/Floflis/ZirohNeth/pull/9

This tasklist complements the migration protocol; it does not replace or duplicate the migration proof, signing, or v2 identity implementation.
