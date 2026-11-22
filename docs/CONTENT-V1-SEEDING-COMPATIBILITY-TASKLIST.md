# Content v1 Manifest Seeding for v2 Sites

## Status

**Compatibility transport merged:** [PR #23](https://github.com/Floflis/ZirohNeth/pull/23) merged the initial manifest-only transport. [PR #24](https://github.com/Floflis/ZirohNeth/pull/24) is the separate implementation track for the Classic landing page, full-content preservation and two-file historical identity. Keep task checkboxes open until runtime tests and the evidence requirements in `AGENTS.md` are satisfied.

## Problem

A site migrated from a Bitcoin-addressed Content v1 identity to an Ethereum-addressed
Content v2 identity must remain understandable to unmodified ZeroNet Classic clients.
Those clients cannot parse the dual-signed migration envelope or follow an Ethereum
identity. Merely retaining the terminal v1 `content.json` does not provide a usable
migration experience: the classic client needs a normal `index.html` to render.

The historical Bitcoin identity therefore becomes a deliberately minimal, signed
migration landing page, while the complete site content is carried by the Ethereum v2
identity.

## Goal

When the owner authorizes migration with the Bitcoin private key, the migration
workflow must produce and publish exactly two files for the historical Bitcoin
identity:

1. the terminal Bitcoin-signed `content.json`, whose signed file list contains only
   `index.html`;
2. the generated `index.html` migration landing page, explaining that the site moved
   and linking to https://github.com/ZeroNetPlus/ZirohNeth.

The Bitcoin signature on `content.json` authenticates the HTML through its signed
SHA-512 digest and size. The migration envelope binds the terminal manifest to the
Ethereum destination. Every peer seeding the v2 site must also seed these two
historical v1 files under the old Bitcoin address. The complete original site content
must be retained under the v2 identity, not discarded when the v1 identity is reduced
to its landing page.

## Scope and compatibility boundaries

- Preserve the original Bitcoin identity/address and v1 signature verification rules.
- Preserve the Ethereum identity/address and EIP-712/BLAKE3 verification rules.
- The Bitcoin-signed terminal `content.json` must list exactly one required file:
  `index.html`. No original site assets or other files remain part of the historical
  Bitcoin version.
- Generate the landing page as part of migration. It must clearly state that the site
  has migrated and link to the ZirohNeth project at
  https://github.com/ZeroNetPlus/ZirohNeth.
- The Bitcoin signature authenticates the landing page indirectly but unambiguously:
  the signed manifest commits to its SHA-512 digest and byte size. The owner must
  authorize both the terminal manifest and its HTML payload in the same migration
  operation.
- Copy and verify the complete pre-migration site content into the Ethereum v2 site
  before replacing/removing any legacy files. Do not lose original assets during the
  v1-to-v2 transition.
- A v2 peer serving a migrated site must expose both terminal v1 files under the
  historical Bitcoin address. It must not expose the original v1 site's old assets
  under that address.
- Do not generate or fabricate migration proofs, or infer migration from shared content.
- Do not permit a v2 peer to sign or mutate a manifest on behalf of the historical
  Bitcoin identity.
- Legacy ZeroNet Classic clients need no migration-envelope support: they render the
  signed landing page as an ordinary v1 site. The link is informational; the classic
  client itself does not automatically navigate to the Ethereum site.
- Important limitation: the owner still possesses the Bitcoin private key and can use
  another v1 client to sign/publish a competing Bitcoin manifest. The protocol cannot
  revoke that key or prevent this. Such a post-migration signature can fork/conflict
  the historical v1 identity and undermine the migration view on both v1 and v2
  clients. Detect and report conflicting post-migration manifests; never silently
  overwrite the pinned migration checkpoint.
- The original ZeroNet network continues to seed ordinary v1 content. Explicit
  tracker/DHT withdrawal by the v2 alias is not a requirement: the historical address
  remains a v1 network concern, while v2 peers provide redundant availability for the
  signed migration landing page.

## Implementation snapshot (PR #23 / PR #24)

PR #23 merged the earlier compatibility-manifest transport design:
it stores and verifies the terminal v1 `content.json` and creates a historical
serving alias. It does **not yet implement** the newly required signed HTML landing
page, the two-file-only historical manifest, or preservation of all original content
under v2 while pruning the v1 identity. The PR must not be considered complete until
those runtime changes and their tests are added.

The intended new flow is:

1. Snapshot the complete original v1 manifest and its authorized file set.
2. Stage and verify all original site files into the Ethereum v2 site.
3. Generate the migration landing-page HTML and construct a terminal Bitcoin
   `content.json` whose only file entry is that HTML.
4. Embed the dual-signed migration proof, sign the terminal manifest with the
   Bitcoin key, and publish the two-file historical site.
5. Store and serve exactly those two files from every eligible v2 peer under the
   historical Bitcoin address.
6. On clients, recognize a post-migration competing Bitcoin manifest as a conflict
   with the pinned migration checkpoint. The key itself cannot be revoked.

**Seeding lifecycle:** the original ZeroNet Classic network continues to seed the v1
landing page normally. The v2 compatibility alias does not need a separate tracker/DHT
withdrawal mechanism for this design; its serving lifecycle follows the v2 parent.

**Evidence state:** the above is the target contract, not a claim that PR #23 already
implements it. Focused tests exist for the earlier manifest-only design, but the
updated landing-page, v1 pruning, full-content v2 preservation, conflict detection,
and classic-client rendering tests remain to be implemented and executed.

## Implementation tasklist

### V1 migration manifest discovery and validation

- [ ] **V1S-01** Locate and define the persisted representation and lifecycle of the terminal Bitcoin/v1 `content.json` associated with a migrated v2 site.
- [ ] **V1S-02** Validate the legacy Bitcoin signature, manifest version, migration proof, old/new identity binding, sequence and digest linkage before accepting the compatibility manifest.
- [ ] **V1S-03** Reject malformed, unsigned, conflicting, stale/non-terminal or unrelated v1 manifests; never replace the locally pinned terminal manifest with an unverified peer copy.
- [ ] **V1S-04** Make the verified terminal v1 manifest and its signed `index.html` persist across restart, site re-seeding, reindexing and cache eviction (unless an explicit safe retention policy removes them).

### Peer seeding and discovery

- [ ] **V1S-05** When a peer seeds a migrated v2 site, seed/serve exactly the terminal v1 `content.json` and signed migration `index.html` under the historical Bitcoin address, as well as the complete v2 site under Ethereum.
- [ ] **V1S-06** Advertise compatibility availability only after the v1 manifest has been verified and durably stored; avoid announcing a v1 address with no served manifest.
- [ ] **V1S-07** Ensure unmodified ZeroNet Classic clients can retrieve the terminal `content.json` and authenticated `index.html`, then render the migration landing page using unchanged v1 request framing and signature semantics.
- [ ] **V1S-08** Ensure v2 clients can discover and retrieve compatibility manifests from multiple peers; do not make the original migration publisher the sole availability dependency.
- [ ] **V1S-09** Reconcile peer availability, restart and reseed so the two-file historical landing page remains available while its v2 parent is seeded. Explicit tracker/DHT withdrawal is not required because the classic v1 network continues seeding the historical identity.
- [ ] **V1S-10** Avoid loops, address conflation or cross-site cache collisions between the Bitcoin historical identity and Ethereum destination identity.

### Visitor behavior and redirect contract

- [ ] **V1S-11** Define and implement redirect behavior for migration-aware ZirohNeth clients visiting the old Bitcoin address: validate the terminal migration proof and resolve to the Ethereum destination.
- [ ] **V1S-12** Preserve the historical site directory/address and expose an understandable migration state instead of silently rewriting identity or losing local data.
- [ ] **V1S-13** Verify the generated signed landing page renders in an unmodified ZeroNet Classic client and clearly presents the migration notice and ZirohNeth link. Classic clients do not need Ethereum proof support.
- [ ] **V1S-14** Define behavior when the v1 manifest is temporarily unavailable, peers disagree, a first-contact peer withholds the terminal manifest, or the visitor is offline. Fail safely and show the historical address rather than inventing a destination.

### Tests and evidence

- [ ] **V1S-15** Unit tests for validation, persistence, retrieval, seeding advertisement, historical-address routing and redirect resolution.
- [ ] **V1S-16** Regression tests proving ordinary v1 sites and ordinary v2 sites without a migration record retain their existing behavior.
- [ ] **V1S-17** Multi-peer integration test: a migrated site is seeded by multiple v2 peers; a visitor starting from the Bitcoin v1 address obtains the exact terminal signed manifest and resolves to the Ethereum destination.
- [ ] **V1S-18** Restart/reseed and peer-unavailability tests; simulate a post-migration competing Bitcoin-signed v1 manifest and verify conflict detection without silently replacing the pinned migration checkpoint.
- [ ] **V1S-19** Test classic-client rendering of the landing page separately from migration-aware ZirohNeth proof validation and Ethereum address resolution.
- [ ] **V1S-20** Record exact test commands, outcomes, environment/topology, PR URL and commit SHA for each completed task. Do not close checklist items without evidence.

## Acceptance criteria

1. A migrated v2 site with a valid terminal v1 migration manifest can be seeded by multiple v2 peers.
2. The old Bitcoin address serves exactly two files: the terminal Bitcoin-signed `content.json` and its authenticated migration `index.html`.
3. Migration-aware visitors using the old address can validate the proof and reach the Ethereum v2 identity.
4. Missing or conflicting compatibility data fails safely; unverified data is never advertised as seedable.
5. Existing non-migrated v1 and v2 sites remain unaffected.
6. An unmodified ZeroNet Classic client renders the signed migration landing page; it does not need to understand the Ethereum migration proof.
7. Every completed implementation task has linked PR/commit/test evidence.

## Related work

- Content v2 / Bitcoin-to-Ethereum migration: https://github.com/Floflis/ZirohNeth/pull/2
- Content v2 integrity remediation: https://github.com/Floflis/ZirohNeth/pull/8
- Content v2 hashfield namespace work: https://github.com/Floflis/ZirohNeth/pull/9

This tasklist complements the migration protocol; it does not replace or duplicate the migration proof, signing, or v2 identity implementation.
