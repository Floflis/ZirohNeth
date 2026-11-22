# CoffeeScript-to-TypeScript migration plan

## Objective

Plan a gradual migration of official ZeroNet ecosystem websites and their documentation from CoffeeScript to TypeScript. This document is planning and inventory only: it does **not** convert code, change runtime behavior, or declare a migration complete.

## Principles

- Preserve existing UI, behavior, protocol/API contracts, site identity, and supported browsers unless a separately reviewed change explicitly changes them.
- Migrate in small, reviewable steps; avoid mixing redesigns, dependency upgrades, and unrelated cleanup into conversion PRs.
- TypeScript should be checked with strictness progressively enabled and should avoid `any` where practical.
- Keep source files authoritative; generated JavaScript and bundles remain generated artifacts and must not be hand-edited unless the repository's build process explicitly requires it.
- Preserve reproducible builds and document the compiler/build tool versions.
- Track each site/repository separately and record evidence: inventory, build command, tests, compatibility checks, and review.
- Do not assume a repository is under the Floflis organization merely because it is an upstream official ZeroNet project.

## Preliminary site / project inventory

The following are known official ZeroNet sites/projects to audit. Repository ownership, current status, and CoffeeScript presence are deliberately distinguished.

| Site/project | Repository / source | Initial finding | Status |
|---|---|---|---|
| ZeroHello (ZeroNet homepage/dashboard) | [Floflis/ZirohNeth-dashboard](https://github.com/Floflis/ZirohNeth-dashboard) | CoffeeScript sources confirmed in `js/`, `js/lib/`, `js/utils/`, page modules. This is the primary confirmed migration target. | Confirmed source inventory; audit/build setup pending |
| ZeroName | [Floflis/ZeroName](https://github.com/Floflis/ZeroName) | CoffeeScript confirmed: `js/ZeroName.coffee`, `js/lib/ZeroFrame.coffee`. | Confirmed source inventory; audit pending |
| ZeroID | [Floflis/ZeroID](https://github.com/Floflis/ZeroID) | CoffeeScript confirmed in `js/`, `js/lib/`, and `js/utils/`. | Confirmed source inventory; audit pending |
| ZeroMail | Upstream project: [HelloZeroNet/ZeroMail](https://github.com/HelloZeroNet/ZeroMail) | Official project/site candidate; no Floflis repository mirror was located during this initial search. CoffeeScript status not yet verified. | Needs repository and source audit |
| ZeroMe | Upstream project: [HelloZeroNet/ZeroMe](https://github.com/HelloZeroNet/ZeroMe) | Official project/site candidate; no Floflis repository mirror was located during this initial search. CoffeeScript status not yet verified. | Needs repository and source audit |
| ZeroTalk | Upstream project: [HelloZeroNet/ZeroTalk](https://github.com/HelloZeroNet/ZeroTalk) | Official site/project candidate; upstream repository is reported as CoffeeScript, but Floflis mirror and current branch inventory are not yet verified. | Needs repository and source audit |
| ZeroBlog | Upstream project: [HelloZeroNet/ZeroBlog](https://github.com/HelloZeroNet/ZeroBlog) | Official demo site candidate; current source language and Floflis mirror not yet verified. | Needs repository and source audit |
| ZeroChat | Upstream tutorial/site project | Official tutorial example/site candidate; source and ownership need verification. | Needs repository and source audit |
| zeronet.io / documentation website | Upstream documentation/website repositories | Official web and documentation surface; inventory source, scripts, code snippets, and build pipeline. | Needs repository and source audit |

This list is an initial known-project list, not a complete census of official or historically official sites. The inventory phase should search organization repositories, upstream HelloZeroNet repositories, site source manifests, and references in the client/docs; include other official sites discovered (e.g., admin tools, demos, or supporting sites) and exclude community sites unless explicitly adopted as official.

## Migration phases

### Phase 0 — Discovery and baseline

- [ ] Identify the canonical repository, owner, maintained branch, deployment/source-of-truth, and status for every official site.
- [ ] Enumerate all CoffeeScript (`.coffee`, `.litcoffee`) sources, compiler/build scripts, generated JS, templates, styles, and documentation snippets.
- [ ] Record CoffeeScript/compiler versions, build commands, browser support, runtime dependencies, and current test/CI coverage.
- [ ] Establish baseline screenshots or behavioral checks for key user journeys where practical.
- [ ] Record unresolved ownership, missing repositories, archived sites, and abandoned projects without silently dropping them from scope.

### Phase 1 — TypeScript architecture and conversion rules

- [ ] Choose a TypeScript version and compatible build approach per repository; prefer a minimal change to existing build systems initially.
- [ ] Define module strategy, target/runtime compatibility, source maps, declaration generation policy, and generated-file handling.
- [ ] Specify typing patterns for ZeroFrame/websocket APIs, site APIs, message payloads, callbacks, event handlers, and legacy globals.
- [ ] Establish strictness baseline, lint/format policy, and how temporary typing gaps are tracked (localized and documented, not blanket suppressions).
- [ ] Document CoffeeScript-to-TypeScript mapping rules and conversion pitfalls; use automated conversion only as a starting point followed by manual review.

### Phase 2 — Pilot: ZeroHello / dashboard

- [ ] Audit the confirmed CoffeeScript files and dependency graph in `Floflis/ZirohNeth-dashboard`.
- [ ] Select a small leaf module as the pilot; convert it and compare generated output/build and behavior.
- [ ] Validate API interactions, async behavior, event binding, DOM behavior, and UI parity.
- [ ] Use pilot findings to refine migration rules and review checklist before expanding.

### Phase 3 — Site-by-site conversion

- [ ] Convert modules in dependency-aware, small batches.
- [ ] Keep each batch buildable and reviewable; avoid mixing redesign or unrelated refactors.
- [ ] Update imports/references, compiler/build configuration, and CI checks as needed.
- [ ] Add or improve tests for typed interfaces and user-visible behavior.
- [ ] Repeat for ZeroName, ZeroID, and each additional confirmed official site after repository/source verification.

### Phase 4 — Documentation and snippets

- [ ] Search official documentation, READMEs, tutorials, templates, and code examples for CoffeeScript.
- [ ] Convert maintained examples to TypeScript and label historical examples that intentionally remain unchanged.
- [ ] Update setup, development, contribution, and build instructions.
- [ ] Cross-link migration progress and per-site source inventories.

### Phase 5 — Validation and completion

- [ ] Type-check and build in clean environments using documented commands.
- [ ] Run tests and CI, plus browser/runtime compatibility checks appropriate to each site.
- [ ] Verify key UI workflows and ZeroNet API/site interactions; compare baseline behavior.
- [ ] Confirm generated bundles are reproducible and no accidental source/bundle drift remains.
- [ ] Review accessibility and error handling for regressions introduced by conversion.
- [ ] Record remaining CoffeeScript files and explicitly justify any deferred/archived cases.
- [ ] Mark a site complete only after its evidence and review checklist are satisfied.

## Tracking template

For every site/repository, record:

- Repository and canonical upstream; owner and maintained branch
- Site identity/address and deployment/source-of-truth
- CoffeeScript files and related generated artifacts
- Build tooling/compiler versions and baseline build command
- Baseline tests/CI and important UI/API workflows
- Migration PR(s), converted file list, and remaining CoffeeScript
- Type-check/build/test commands and outcomes
- Compatibility/behavior review evidence
- Deferred items, blockers, and completion date/reviewer

## Initial progress

- [x] Confirmed `Floflis/ZirohNeth-dashboard` has CoffeeScript source files.
- [x] Confirmed `Floflis/ZeroName` has CoffeeScript source files.
- [x] Confirmed `Floflis/ZeroID` has CoffeeScript source files.
- [ ] Complete the official-site/repository census.
- [ ] Audit build systems and current behavior for the confirmed targets.
- [ ] Select and execute the ZeroHello/dashboard pilot.
- [ ] Begin remaining conversions after pilot review.

## Explicitly out of scope for this planning PR

- Actual CoffeeScript-to-TypeScript code conversion.
- Site redesign, feature changes, protocol/API changes, or unrelated dependency upgrades.
- Removing historical CoffeeScript sources before converted output and behavior are validated.
- Treating an upstream project as a Floflis-maintained repository without verifying ownership and maintenance status.
