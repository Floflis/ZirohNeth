# CJDNS and Yggdrasil support: implementation task list

Status: planning and verification backlog  
Scope: ZirohNeth Python client and networking integration with zeronet-rs  
Related work: ZirohNeth PR #15 (IPv6 route detection); zeronet-rs PR #8 (dual-stack listeners and handshake-derived reachability).

This is a task list, not a claim that these items are implemented. Keep each item open until code, tests and runtime evidence support closing it.

## Goals and invariants

- Treat CJDNS and Yggdrasil as IPv6 transports/overlays, not separate ZeroNet wire protocols.
- Preserve IPv4, public IPv6, existing trackers and existing ZeroNet peers.
- Distinguish outbound IPv6 capability, active inbound IPv6 listener, and verified inbound reachability.
- A local route, interface address, UDP route probe or successful bind is not proof that a remote peer can reach the TCP listener.
- Re-evaluate network state when interfaces/routes change at runtime.
- Advertise only endpoints backed by an active listener and the agreed reachability policy.
- Keep Python and Rust semantics aligned during migration; retain Python fallback until Rust parity is demonstrated.

## P0 - Correctness and CI blockers

- [ ] **ZN-001** Fix mesh-helper test invocation/import context. The PR #15 workflow's mesh test step failed with an attempted-relative-import/no-known-parent-package ImportError while importing Config/util.Git. Use the supported package/module invocation or repair test bootstrap without changing production import semantics.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-002** Make mesh tests a required green CI check. Verify that the new tests actually execute, not merely that compileall succeeds.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-003** Separate IPv6 transport capability from listener capability. A detected route or usable outbound source address must not automatically add IPv6 to inbound FileServer services.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-004** Honor IPv4-only bind configuration. With fileserver-ip-type=ipv4, do not advertise IPv6 because a CJDNS/Yggdrasil route exists. Check active bound sockets before building tracker announcements.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-005** Make reachability evidence explicit. Do not set port_opened[ipv6] true solely because an IPv6 address is non-private or a mesh route exists. Align with Rust's ReachabilityEvidence concept: valid inbound ZeroNet v2 handshake on an active IPv6 listener, with bounded freshness.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-006** Add false-positive regression tests: route present/listener absent; IPv4-only listener plus mesh route; bind failure; stale evidence; route loss after a successful check.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-007** Fix IPv6 tracker URL parsing. Accept bracketed literals such as zero://[fc00::1234]:15441 and distinguish address colons from the port separator. Test malformed brackets, ports, DNS names and unbracketed input according to the URL grammar.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-008** Fix IPv6 sockaddr construction. Do not hard-code flowinfo=1 and scopeid=1 for every destination. Use default flow information for global/overlay addresses and a real interface scope only where required, notably link-local addresses. Add platform-aware tests.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_

## P1 - Dynamic interface and route lifecycle

- [ ] **ZN-009** Introduce a network-state abstraction tracking IPv4/IPv6 addresses, routes, interface identity/index, overlay classification (CJDNS/Yggdrasil/other IPv6), and observation timestamp/source.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-010** Monitor runtime network changes: interface up/down, address add/remove, route add/remove/metric changes, and overlay daemon restart. Prefer native OS notifications; retain bounded polling fallback.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-011** Reconcile state instead of taking a startup snapshot. Recompute outbound family capability, listener eligibility, peer-route eligibility and announcement state after relevant changes.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-012** Handle overlay startup after ZirohNeth starts. Discover a newly available CJDNS/Yggdrasil route and activate the appropriate IPv6 path without requiring restart.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-013** Handle overlay shutdown and route loss. Stop advertising unreachable endpoints, invalidate stale route observations and avoid repeated attempts to peers no longer routable.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-014** Reconcile listeners safely. Bind/close IPv6 listeners as policy requires; do not tear down healthy IPv4 listeners during IPv6 transitions. Make listener changes atomic to the announcement layer.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-015** Reannounce after meaningful state transitions. Refresh trackers when active/reachable endpoints change, with debounce and rate limiting to prevent announce storms.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-016** Expire stale route observations and reachability evidence with explicit TTLs; expiration must trigger peer and announcement recalculation.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-017** Add lifecycle tests for route/interface add/remove, overlay restart, bind failure, duplicate notifications, rapid flapping and shutdown with active connections.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_

## P1 - Peer connection and tracker correctness

- [ ] **ZN-018** Make peer endpoint parsing IPv6-safe end-to-end: tracker response, PEX decoding, normalization, persistence, logging and socket creation. Brackets are URL syntax, not part of the stored IP literal.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-019** Keep endpoint family and listener family consistent. Advertise inbound IPv6 only when the IPv6 listener is bound and the reachability policy is satisfied.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-020** Keep outbound and inbound capabilities separate. An outbound-only mesh route may allow connecting to peers without claiming inbound service.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-021** Preserve PEX compatibility, including peers_ipv6 and legacy peer formats. Verify older peers safely handle optional/unknown fields.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-022** Add route-aware peer selection. Avoid dialing CJDNS peers without a CJDNS route, and likewise for Yggdrasil; do not classify all IPv6 as overlay.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-023** Support dual-overlay nodes without conflating CJDNS and Yggdrasil route availability.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-024** Specify tracker announcement semantics: endpoint, observed inbound reachability, or both. Align code and tests with that contract.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_

## P2 - DHT and local discovery

- [ ] **ZN-025** Design IPv6 DHT transport. The current Python DHT startup binds UDP to 0.0.0.0:12346 and uses IPv4 bootstrap assumptions. Define IPv6 sockets and bootstrap representation before implementation.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-026** Support mesh-reachable DHT peers. Verify node IDs and endpoint serialization represent IPv6 without lossy parsing or IPv4-only assumptions.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-027** Preserve IPv4 DHT behavior; IPv6 must not replace or regress the existing path.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-028** Evaluate IPv6 local discovery separately. The current LAN broadcast path uses AF_INET/SO_BROADCAST. Design IPv6 multicast with interface scope, group choice, hop limit, duplicate suppression and privacy controls.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-029** Do not equate multicast with overlay discovery. Link-local multicast is not automatically propagated across overlay nodes.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_

## P2 - Cross-platform and security validation

- [ ] **ZN-030** Linux: test dual-stack/IPv6-only sockets, IPV6_V6ONLY, route notifications and overlay daemon lifecycle.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-031** Windows: test binding, IPv6 parsing, interface/route notifications and overlay client behavior.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-032** macOS: test dual-stack binding, route changes, scope handling and overlay lifecycle.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-033** Android where supported: document restrictions, background lifecycle, VPN/overlay routing and deployment mode.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-034** Audit proxy/Tor/bind modes. Socket monkey-patching and configurations disabling UDP or restricting bind addresses must not accidentally advertise mesh reachability.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-035** Review privacy: do not leak local interface addresses, overlay membership or unreachable endpoints through logs, trackers or diagnostics beyond protocol intent.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-036** Add two-node integration tests for CJDNS-to-CJDNS and Yggdrasil-to-Yggdrasil inbound/outbound handshakes, PEX and file transfer.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-037** Add mixed-network tests: IPv4 + public IPv6 + CJDNS; IPv4 + Yggdrasil; both overlays; inter-overlay only where an actual route exists.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-038** Test route changes during active transfers, including reconnect, retry/backoff, cancellation and tracker updates.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_

## P2 - Rust integration and parity

- [ ] **ZN-039** Define a shared capability contract with zeronet-rs: outbound capability, listener state, reachability evidence, overlay classification and peer eligibility.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-040** Align Python reachability with Rust. A route probe must not mark an inbound service reachable.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-041** Expose dynamic network-state changes to the Rust bridge, or define Rust as the sole owner of route monitoring.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-042** Keep fallback behavior explicit. Python fallback must not double-bind or double-announce when Rust networking is enabled.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-043** Add parity fixtures: feed the same addresses/routes to Python and Rust and assert equivalent classification and endpoint eligibility.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_
- [ ] **ZN-044** Update migration documentation with Python-owned, Rust-owned and shared responsibilities.
  - Evidence when closed: PR: _pending_ · Commit: _pending_ · Tests: _pending_ · Runtime/topology: _pending or N/A with reason_

## Acceptance criteria

CJDNS/Yggdrasil support in ZirohNeth is not complete until:
1. Runtime route/interface changes are detected.
2. Listener state is reconciled without breaking the other address family.
3. Tracker announcements reflect active, policy-approved reachability, not route presence alone.
4. IPv6 peer parsing, PEX and outbound selection work as specified.
5. DHT/local-discovery gaps are implemented or explicitly scoped out of the peer-transport milestone.
6. CI executes and passes mesh tests.
7. Two-node integration tests pass on supported overlays/platforms.
8. Python/Rust capability semantics are documented and tested for parity.

## Evidence and close-out rules

For each completed item, record implementation PR/commit, exact test command/result, OS, overlay and topology. Do not close a task based only on code inspection or successful bind. Real interoperability requires a two-node test or a clearly labelled equivalent harness.


## Implementation contract: traceable task closure

Every checkbox has a stable ID. A checkbox may be changed to `[x]` only in the same change that supplies its evidence line immediately below it. The evidence line must contain:

- **PR:** the implementation pull request URL or number (not this documentation PR).
- **Commit:** the full commit SHA that contains the implementation or test.
- **Tests:** exact command(s), result, and CI run URL or equivalent reproducible output.
- **Runtime/topology:** OS, overlay (CJDNS/Yggdrasil), node count and relevant interface/route setup for runtime or interoperability claims; write `N/A` with a reason for tasks that are genuinely unit/CI-only.

A PR link without a commit is insufficient; a commit without test evidence is insufficient. For multi-PR work, list every required PR/commit. Keep the checkbox open while any evidence field is pending. Do not infer completion from code presence, a successful bind, prefix classification, or an unexecuted test command.

### Evidence record template

```text
PR: https://github.com/Floflis/<repo>/pull/<number>
Commit: <full SHA>
Tests: <exact command> — PASS/FAIL; <CI run URL or reproducible output>
Runtime/topology: <OS + overlay + node count + relevant route/interface details, or N/A + reason>
```

This contract is intentionally documentation-only. It does not mark any implementation task complete or alter the status of prior implementation PRs.
