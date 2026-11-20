# 🌈 ENS .eth name resolution roadmap

## 🌈 Status and scope

**Status:** planning document. This roadmap does not claim that ENS resolution is implemented.

This work adapts the ZirohNeth client to consume `.eth` mappings published by the companion ZeroName service. It must preserve the existing `.bit` path and use the Ethereum identity model already defined by ZirohNeth Content v2.

A `.eth` name resolves to an Ethereum `0x` site identity. It does not resolve to an IPFS CID, IPFS gateway, or ENS content hash.

The companion server-side roadmap is maintained in [Floflis/ZeroName](https://github.com/Floflis/ZeroName/blob/master/docs/ETH-NAME-RESOLUTION-ROADMAP.md).

## 🌈 Goals

1. Preserve existing Namecoin-backed `.bit` resolution.
2. Recognize published `.eth` records from ZeroName.
3. Resolve a valid `.eth` name to its published Ethereum `0x` address.
4. Validate the published record's status, expiration, and verification metadata before use.
5. Refuse expired, malformed, conflicting, or unverifiable records.
6. Keep cache entries bounded by the published validity policy.
7. Verify that the resolved destination is handled through the existing ZirohNeth Ethereum identity and Content v2 path.

## 🌈 Coordinated PR sequence

### PR 1. Audit the existing `.bit` integration

- Locate the current ZeroName plugin, Namecoin mapping lookup, cache, and client routing behavior.
- Document the existing `.bit` registry shape and compatibility expectations.
- Identify shared code paths that must not change when adding `.eth`.
- Add or identify regression tests before modifying the resolver.

**Acceptance:** current `.bit` lookup and routing remain unchanged.

### PR 2. Add `.eth` recognition and address resolution

- Recognize ENS `.eth` names separately from `.bit` names.
- Consume the published ZeroName mapping; do not independently guess or derive an address from the name.
- Normalize and validate the returned Ethereum address using the existing Ethereum address utilities.
- Route the result through the existing ZirohNeth site identity path, preserving the `0x` prefix and EIP-55 normalization.
- Reject malformed names, malformed addresses, unsupported record versions, and ambiguous results.

**Acceptance:** a valid published mapping resolves to the exact Ethereum site identity; `.bit` routing remains compatible.

### PR 3. Consume published validity and verification metadata

- Parse the explicit status and expiration fields defined by the shared ZeroName registry contract.
- Reject records marked expired, pending, rejected, or unverifiable.
- Enforce the expiration boundary locally using a trusted clock policy.
- Treat missing or malformed expiration metadata as unverifiable, not as non-expiring.
- Keep last-verification metadata visible to diagnostics and logs.
- Do not treat an old cached address as valid after its published expiration.

**Acceptance:** expired and unverifiable entries never reach site routing.

### PR 4. Cache policy and refresh behavior

- Bound positive cache lifetime by the published expiration and verification policy.
- Invalidate cached results when the ZeroName registry revision changes.
- Do not let a local cache extend a name's validity beyond its authoritative expiration.
- Distinguish a cache hit from a fresh registry result in diagnostics.
- Define conservative behavior when the registry is unavailable: previously verified data may only be used if the agreed policy explicitly permits it and its validity window remains provable; otherwise fail closed.
- Do not add a local Ethereum node or an independent continuous ENS watcher.

**Acceptance:** cache expiry, registry updates, stale data, and offline behavior are covered by tests.

### PR 5. Integrate with Ethereum Content v2 site identity

- Pass the resolved `0x` destination to the existing Ethereum site identity and Content v2 verification flow.
- Keep EIP-712 signature validation and BLAKE3 content integrity checks in their existing layers.
- Do not treat a syntactically valid address as proof that a usable or authentic site exists.
- Preserve the distinction between name resolution and site-manifest authentication.

**Acceptance:** resolving a name selects the destination identity; the normal Content v2 verification still decides whether the site's manifest and content are authentic.

### PR 6. Security, expiration, cache, and compatibility tests

- Active, expired, pending, rejected, and unverifiable record cases.
- Exact expiration boundary and missing/malformed expiry.
- Address changes after a registry refresh.
- Conflicting or duplicate records.
- Stale cache, registry revision change, and offline behavior.
- Malformed Ethereum addresses and unsupported record versions.
- `.bit` regression tests.
- End-to-end resolution followed by Content v2 identity/signature verification.

**Acceptance:** no expired or unverifiable `.eth` record is routed; `.bit` behavior remains compatible; site authentication remains independent of name resolution.

## 🌈 Shared ZeroName record contract

The exact schema is owned jointly with ZeroName and must be finalized after auditing its existing registry consumers. The following fields are conceptual, not a committed schema:

- Normalized ENS name.
- Ethereum `0x` destination address.
- Explicit status.
- Authoritative expiration timestamp.
- Last verification timestamp and source.
- Verified Ethereum block number/hash, where applicable.
- Registry/publication revision.

The client must fail closed when required validity fields are absent or inconsistent. A valid EIP-55 address alone does not establish that an ENS registration is active.

## 🌈 Security boundaries

- ZeroName is responsible for on-demand ENS verification and signed publication.
- ZirohNeth consumes the published mapping and enforces the published validity policy.
- ZirohNeth must not trust user-submitted form data or ENS Data cache directly.
- The ENS destination address is not the same thing as the registrar owner/controller.
- Expiration must be enforced before routing, even if an old resolver response or cache still contains an address.
- Name resolution does not replace Content v2 EIP-712 signature verification or file-integrity checks.
- No IPFS fallback, local Ethereum node, or background ENS watcher is part of this roadmap.

## 🌈 Delivery rule

The two repositories must agree on the record schema, status vocabulary, expiry semantics, and cache policy before implementation is considered complete. Keep implementation changes in focused PRs, with tests and explicit documentation for unsupported cases.
