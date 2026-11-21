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

- [ ] Fix mesh-helper test invocation/import context. The PR #15 workflow's mesh test step failed with an attempted-relative-import/no-known-parent-package ImportError while importing Config/util.Git. Use the supported package/module invocation or repair test bootstrap without changing production import semantics.
- [ ] Make mesh tests a required green CI check. Verify that the new tests actually execute, not merely that compileall succeeds.
- [ ] Separate IPv6 transport capability from listener capability. A detected route or usable outbound source address must not automatically add IPv6 to inbound FileServer services.
- [ ] Honor IPv4-only bind configuration. With fileserver-ip-type=ipv4, do not advertise IPv6 because a CJDNS/Yggdrasil route exists. Check active bound sockets before building tracker announcements.
- [ ] Make reachability evidence explicit. Do not set port_opened[ipv6] true solely because an IPv6 address is non-private or a mesh route exists. Align with Rust's ReachabilityEvidence concept: valid inbound ZeroNet v2 handshake on an active IPv6 listener, with bounded freshness.
- [ ] Add false-positive regression tests: route present/listener absent; IPv4-only listener plus mesh route; bind failure; stale evidence; route loss after a successful check.
- [ ] Fix IPv6 tracker URL parsing. Accept bracketed literals such as zero://[fc00::1234]:15441 and distinguish address colons from the port separator. Test malformed brackets, ports, DNS names and unbracketed input according to the URL grammar.
- [ ] Fix IPv6 sockaddr construction. Do not hard-code flowinfo=1 and scopeid=1 for every destination. Use default flow information for global/overlay addresses and a real interface scope only where required, notably link-local addresses. Add platform-aware tests.

## P1 - Dynamic interface and route lifecycle

- [ ] Introduce a network-state abstraction tracking IPv4/IPv6 addresses, routes, interface identity/index, overlay classification (CJDNS/Yggdrasil/other IPv6), and observation timestamp/source.
- [ ] Monitor runtime network changes: interface up/down, address add/remove, route add/remove/metric changes, and overlay daemon restart. Prefer native OS notifications; retain bounded polling fallback.
- [ ] Reconcile state instead of taking a startup snapshot. Recompute outbound family capability, listener eligibility, peer-route eligibility and announcement state after relevant changes.
- [ ] Handle overlay startup after ZirohNeth starts. Discover a newly available CJDNS/Yggdrasil route and activate the appropriate IPv6 path without requiring restart.
- [ ] Handle overlay shutdown and route loss. Stop advertising unreachable endpoints, invalidate stale route observations and avoid repeated attempts to peers no longer routable.
- [ ] Reconcile listeners safely. Bind/close IPv6 listeners as policy requires; do not tear down healthy IPv4 listeners during IPv6 transitions. Make listener changes atomic to the announcement layer.
- [ ] Reannounce after meaningful state transitions. Refresh trackers when active/reachable endpoints change, with debounce and rate limiting to prevent announce storms.
- [ ] Expire stale route observations and reachability evidence with explicit TTLs; expiration must trigger peer and announcement recalculation.
- [ ] Add lifecycle tests for route/interface add/remove, overlay restart, bind failure, duplicate notifications, rapid flapping and shutdown with active connections.

## P1 - Peer connection and tracker correctness

- [ ] Make peer endpoint parsing IPv6-safe end-to-end: tracker response, PEX decoding, normalization, persistence, logging and socket creation. Brackets are URL syntax, not part of the stored IP literal.
- [ ] Keep endpoint family and listener family consistent. Advertise inbound IPv6 only when the IPv6 listener is bound and the reachability policy is satisfied.
- [ ] Keep outbound and inbound capabilities separate. An outbound-only mesh route may allow connecting to peers without claiming inbound service.
- [ ] Preserve PEX compatibility, including peers_ipv6 and legacy peer formats. Verify older peers safely handle optional/unknown fields.
- [ ] Add route-aware peer selection. Avoid dialing CJDNS peers without a CJDNS route, and likewise for Yggdrasil; do not classify all IPv6 as overlay.
- [ ] Support dual-overlay nodes without conflating CJDNS and Yggdrasil route availability.
- [ ] Specify tracker announcement semantics: endpoint, observed inbound reachability, or both. Align code and tests with that contract.

## P2 - DHT and local discovery

- [ ] Design IPv6 DHT transport. The current Python DHT startup binds UDP to 0.0.0.0:12346 and uses IPv4 bootstrap assumptions. Define IPv6 sockets and bootstrap representation before implementation.
- [ ] Support mesh-reachable DHT peers. Verify node IDs and endpoint serialization represent IPv6 without lossy parsing or IPv4-only assumptions.
- [ ] Preserve IPv4 DHT behavior; IPv6 must not replace or regress the existing path.
- [ ] Evaluate IPv6 local discovery separately. The current LAN broadcast path uses AF_INET/SO_BROADCAST. Design IPv6 multicast with interface scope, group choice, hop limit, duplicate suppression and privacy controls.
- [ ] Do not equate multicast with overlay discovery. Link-local multicast is not automatically propagated across overlay nodes.

## P2 - Cross-platform and security validation

- [ ] Linux: test dual-stack/IPv6-only sockets, IPV6_V6ONLY, route notifications and overlay daemon lifecycle.
- [ ] Windows: test binding, IPv6 parsing, interface/route notifications and overlay client behavior.
- [ ] macOS: test dual-stack binding, route changes, scope handling and overlay lifecycle.
- [ ] Android where supported: document restrictions, background lifecycle, VPN/overlay routing and deployment mode.
- [ ] Audit proxy/Tor/bind modes. Socket monkey-patching and configurations disabling UDP or restricting bind addresses must not accidentally advertise mesh reachability.
- [ ] Review privacy: do not leak local interface addresses, overlay membership or unreachable endpoints through logs, trackers or diagnostics beyond protocol intent.
- [ ] Add two-node integration tests for CJDNS-to-CJDNS and Yggdrasil-to-Yggdrasil inbound/outbound handshakes, PEX and file transfer.
- [ ] Add mixed-network tests: IPv4 + public IPv6 + CJDNS; IPv4 + Yggdrasil; both overlays; inter-overlay only where an actual route exists.
- [ ] Test route changes during active transfers, including reconnect, retry/backoff, cancellation and tracker updates.

## P2 - Rust integration and parity

- [ ] Define a shared capability contract with zeronet-rs: outbound capability, listener state, reachability evidence, overlay classification and peer eligibility.
- [ ] Align Python reachability with Rust. A route probe must not mark an inbound service reachable.
- [ ] Expose dynamic network-state changes to the Rust bridge, or define Rust as the sole owner of route monitoring.
- [ ] Keep fallback behavior explicit. Python fallback must not double-bind or double-announce when Rust networking is enabled.
- [ ] Add parity fixtures: feed the same addresses/routes to Python and Rust and assert equivalent classification and endpoint eligibility.
- [ ] Update migration documentation with Python-owned, Rust-owned and shared responsibilities.

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
