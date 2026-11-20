# 🌈 Rust-native migration findings: ZirohNeth ↔ zeronet-rs

> **Audit date:** 20 November 2026  
> **Purpose:** identify the first ZirohNeth Python responsibilities that can be delegated to the native `Floflis/zeronet-rs` implementation.  
> **Status:** source audit and migration plan, not a claim of complete protocol parity.

## 🌈 Executive decision

The migration should begin with **AnnounceLocal / LAN peer discovery**, but the first engineering prerequisite is a stable, long-lived Python ↔ Rust process boundary.

The companion `zeronet-rs` change proposes a versioned JSON Lines bridge over the child process' standard input/output. It exposes the existing native LAN discovery functions without requiring PyO3, a Python ABI, a network control port, or one Rust process per operation.

See the bridge protocol proposal in [zeronet-rs/docs/PYTHON-BRIDGE.md](https://github.com/Floflis/zeronet-rs/blob/feat/python-jsonl-bridge/docs/PYTHON-BRIDGE.md).

The intended ownership model is:

- Rust owns native networking operations as they are migrated.
- Python keeps the existing application, plugin, UI, site lifecycle, and compatibility behavior until each responsibility has a tested native replacement.
- The Python host remains responsible for deciding which site addresses it serves and for validating discovered peers through its normal connection/handshake path.
- A Python module should not be commented out merely because a similarly named Rust module exists. Replace a responsibility only after behavior and compatibility tests pass.

## 🌈 Repositories and inspected baseline

| Project | Inspected baseline | Role |
|---|---|---|
| [Floflis/ZirohNeth](https://github.com/Floflis/ZirohNeth) | `main`, 20/11/2026 | Existing Python ZeroNet-derived client and application/plugin runtime |
| [Floflis/zeronet-rs](https://github.com/Floflis/zeronet-rs) | `main`, 20/11/2026 | Native Rust protocol implementation and migration destination |
| [zeronet-rs PR #3](https://github.com/Floflis/zeronet-rs/pull/3) | Open at audit time | Separate work on native `zero://` tracker interoperability |

The audit compares responsibilities and actual code paths, not repository descriptions or module names alone.

## 🌈 Top five migration candidates

The ranking favors native Rust coverage, functional isolation, and a manageable compatibility boundary. It is not a statement that every candidate is already a drop-in replacement.

| Rank | Python responsibility | ZirohNeth source | Rust implementation | Assessment |
|---:|---|---|---|---|
| **1** | LAN peer discovery | `plugins/AnnounceLocal/AnnounceLocalPlugin.py`, `plugins/AnnounceLocal/BroadcastServer.py` | `src/discovery/lan.rs` | Closest existing replacement; finish interoperability validation and bridge integration |
| **2** | Outgoing peer discovery, connection and handshake | `src/Peer/Peer.py`, `src/Connection/Connection.py` | `src/discovery/mod.rs`, `src/core/peer.rs`, `src/net/` | Native connection path exists, but handshake, transport and policy parity need work |
| **3** | BitTorrent HTTP/UDP tracker announce | `plugins/AnnounceBitTorrent/AnnounceBitTorrentPlugin.py` | `src/discovery/tracker/{http,udp,bencode}/` | Native baseline exists; compare edge cases, HTTPS, proxy behavior and malformed responses |
| **4** | Peer exchange (PEX) | `src/Peer/Peer.py` (`pex`) and announcer orchestration | `src/controllers/connections.rs`, `src/common.rs` | Partial; request/response behavior and hashfield support are not complete |
| **5** | Site content download, update and verification | `src/Site/Site.py`, `src/Content/ContentManager.py` | `src/io/site.rs`, `src/io/content.rs`, `src/controllers/sites.rs` | Broad native foundation exists, but important integrity and synchronization gaps remain |

### 🌈 1. AnnounceLocal: LAN discovery

Python responsibilities:
- Broadcast `discoverRequest` and handle `discoverResponse`.
- Request and exchange site lists.
- Cache known peers and associate peers with sites.
- Notify the existing site/worker layer when peers are discovered.

Rust already has a native core implementation in `src/discovery/lan.rs`. It encodes and decodes named MessagePack messages, uses UDP port `1544`, handles the four discovery/site-list message types, chunks site lists at 100 hashes per packet, maintains known peers and per-site peer associations, and exposes `start`, `set_local_sites`, and `discover`.

Relevant code:
- [Python AnnounceLocalPlugin.py](https://github.com/Floflis/ZirohNeth/blob/main/plugins/AnnounceLocal/AnnounceLocalPlugin.py)
- [Python BroadcastServer.py](https://github.com/Floflis/ZirohNeth/blob/main/plugins/AnnounceLocal/BroadcastServer.py)
- [Rust lan.rs](https://github.com/Floflis/zeronet-rs/blob/main/src/discovery/lan.rs)

**Remaining validation:** the Rust TODO and audit still call for real two-process interoperability tests, tests against Python peers, broadcast on each active IPv4 interface, multi-packet site-list cache reconciliation, and validation across Linux, Windows and Android. Unit fixtures alone do not prove network interoperability.

**Migration boundary:** Rust returns discovered `ip:port` candidates. ZirohNeth should continue to add them through its current peer/site code and perform the ordinary connection and handshake checks. Do not treat LAN discovery as peer authentication.

**Socket ownership:** Python and Rust both use UDP port `1544`. Do not run the Python AnnounceLocal listener and the Rust listener simultaneously. During the cutover, the bridge process must own the LAN socket; retain a deliberate startup fallback rather than starting both listeners.

### 🌈 2. Outgoing peer connections and handshake

Python's `Peer` and `Connection` classes combine peer selection, connection pooling, retries, TCP framing, MessagePack stream parsing, optional TLS, proxy/Tor behavior, handshake state, statistics, and plugin hooks.

The Rust project has:
- `Peer::connect` and `Peer::connect_async` in `src/core/peer.rs`;
- tracker and LAN discovery plus `Site::find_peers` in `src/discovery/mod.rs`;
- protocol request/response handling in `src/net/`;
- `ZeroConnection` framing and handshake support through its protocol dependencies.

This is a useful base for migrating **outgoing** connections. It is not yet a replacement for the whole Python connection subsystem. The Rust handshake builder currently uses fixed/default values for some advertised settings, and the Python client has additional transport policies such as certificate pinning, TLS fallback, SOCKS/Tor routing, per-site onion restrictions, connection reuse, and plugin hooks.

**Do not disable `src/Connection/ConnectionServer.py` or the Python inbound server yet.** The Rust `ConnectionController` exists, but the normal `main.rs` runtime path that starts it is still disabled behind an `else if false` branch. The standard runtime starts the site/WebSocket server instead.

Relevant code:
- [Python Peer.py](https://github.com/Floflis/ZirohNeth/blob/main/src/Peer/Peer.py)
- [Python Connection.py](https://github.com/Floflis/ZirohNeth/blob/main/src/Connection/Connection.py)
- [Python ConnectionServer.py](https://github.com/Floflis/ZirohNeth/blob/main/src/Connection/ConnectionServer.py)
- [Rust peer.rs](https://github.com/Floflis/zeronet-rs/blob/main/src/core/peer.rs)
- [Rust connections.rs](https://github.com/Floflis/zeronet-rs/blob/main/src/controllers/connections.rs)

### 🌈 3. BitTorrent HTTP/UDP trackers

Python's `AnnounceBitTorrentPlugin.py` implements UDP, HTTP and HTTPS announces, Bencode response parsing, proxy/Tor handling and configuration-based protocol restrictions.

Rust contains native tracker modules:
- `src/discovery/tracker/http.rs`
- `src/discovery/tracker/udp.rs`
- `src/discovery/tracker/bencode/`
- `src/discovery/tracker/mod.rs`

These are promising replacements for conventional BitTorrent tracker traffic, but not full Python parity. The current HTTP implementation is a raw TCP HTTP request, not an HTTPS/TLS transport. Proxy/Tor behavior and several timeout/response edge cases also need explicit compatibility tests. The UDP implementation should be hardened against malformed or unexpected packets before it is used as an untrusted network parser.

Keep Python tracker handling available for schemes and policies that the Rust implementation does not yet support.

Relevant code:
- [Python AnnounceBitTorrentPlugin.py](https://github.com/Floflis/ZirohNeth/blob/main/plugins/AnnounceBitTorrent/AnnounceBitTorrentPlugin.py)
- [Rust tracker modules](https://github.com/Floflis/zeronet-rs/tree/main/src/discovery/tracker)

### 🌈 4. Peer exchange (PEX)

Rust has an incoming `pex` request handler in `src/controllers/connections.rs`. It unpacks peer addresses, adds peers to a site's peer collection, and constructs a response. However:
- the response path still has a TODO to filter connectable peers;
- `get_hashfield` in the same controller remains unimplemented;
- the `sitePeerExchange` helper in `src/common.rs` currently connects to known peers and pings them; that is not by itself equivalent to Python's outbound `Peer.pex()` request flow.

Treat this as **partial PEX support**, not a reason to disable Python `Peer.pex()`.

Relevant code:
- [Python Peer.py](https://github.com/Floflis/ZirohNeth/blob/main/src/Peer/Peer.py)
- [Rust connections.rs](https://github.com/Floflis/zeronet-rs/blob/main/src/controllers/connections.rs)
- [Rust common.rs](https://github.com/Floflis/zeronet-rs/blob/main/src/common.rs)

### 🌈 5. Site content download and verification

The Rust project already contains content/site storage, file download, content parsing, signing and verification operations. This makes the area a viable later migration target, but the current implementation is not equivalent to ZirohNeth's mature Python content manager.

Concrete gaps observed in the Rust sources include:
- existing files can be accepted without a complete integrity check in the download path;
- download selection currently uses a single peer rather than a multi-peer recovery strategy;
- included/user content verification is incomplete;
- some update handling in the native connection controller is unfinished;
- the site download path contains TODOs around remote freshness and storage permissions.

Migrate in smaller units: root `content.json` acquisition and signature verification first, then referenced file integrity, then includes/user content and update semantics. Preserve the legacy SHA-512 and signature rules for legacy ZeroNet content; do not silently substitute newer digest formats.

Relevant code:
- [Python Site.py](https://github.com/Floflis/ZirohNeth/blob/main/src/Site/Site.py)
- [Python ContentManager.py](https://github.com/Floflis/ZirohNeth/blob/main/src/Content/ContentManager.py)
- [Rust io/site.rs](https://github.com/Floflis/zeronet-rs/blob/main/src/io/site.rs)
- [Rust io/content.rs](https://github.com/Floflis/zeronet-rs/blob/main/src/io/content.rs)

## 🌈 Components to keep in Python for now

### 🌈 `AnnounceZero` and `zero://`

`plugins/AnnounceZero/AnnounceZeroPlugin.py` implements a distinct ZeroNet tracker protocol. It is not the same as HTTP/UDP BitTorrent announce.

[zeronet-rs PR #3](https://github.com/Floflis/zeronet-rs/pull/3) is open at the time of this audit and adds a native `zero://` path. Its stated current limits include clear-TCP clearnet trackers, single-site announce, no Tor/certificate-pinned TLS transport, unsupported onion-signing challenges, and incomplete multi-site announce/delete and service-type reporting. Keep the Python plugin until the Rust work is merged and the missing behavior is addressed or intentionally excluded.

### 🌈 DHT

`src/DHT/DHTServer.py` uses `aiobtdht` and `aioudp`. No equivalent native DHT module was found in `zeronet-rs`. Tracker discovery and LAN discovery are not a replacement for this DHT behavior.

### 🌈 Announcer orchestration

`src/Site/SiteAnnouncer.py` owns timers, retry policy, tracker statistics, WebSocket notifications, DHT announcements, and PEX orchestration. It is an application-level coordinator, not simply a tracker implementation. Keep it until the native services expose equivalent events and the Python host has a deliberate replacement coordinator.

### 🌈 Incoming TCP fileserver

`src/Connection/ConnectionServer.py` and `src/File/FileRequest.py` serve incoming peers and dispatch ZeroNet commands. The native `ConnectionController` is not yet started by the normal runtime path. Do not comment out these Python files until native inbound serving, request coverage, file streaming, permissions, onion restrictions, and compatibility are implemented and tested.

### 🌈 Cryptography

`src/Crypt/ed25519.py` explicitly warns that its Python big-integer implementation is not safe for operations involving secret keys. This is a security concern and should be tracked separately. It is not a direct replacement candidate until the exact algorithms, formats, call sites, and compatibility behavior are mapped to maintained native cryptography. Do not assume the Rust ZeroNet signing APIs cover every ZirohNeth key type or legacy format.

## 🌈 Bridge contract and initial integration

The proposed bridge is a long-lived child process using JSON Lines over standard input/output:

- protocol marker: `zeronet-bridge`;
- protocol version: `1`;
- one request line produces one response line;
- each request carries an `id` for correlation;
- stdout is reserved for JSON responses; diagnostics remain on stderr.

Initial native methods:

| Method | Purpose |
|---|---|
| `system.ping` | Check that the Rust child is alive |
| `discovery.lan.configure` | Start LAN discovery with the Python host's peer ID, fileserver port, revision, and local site list |
| `discovery.lan.set_local_sites` | Update the list of sites advertised by the running Rust service |
| `discovery.lan.discover` | Return LAN peer candidates for one site |

The Python parent should keep one process for the fileserver lifetime. The bridge must receive the **existing Python peer ID and actual fileserver port**; a generated Rust peer ID or an unrelated random port would advertise the wrong endpoint. The LAN listener's UDP port is fixed at `1544`.

See the [bridge protocol and lifecycle documentation](https://github.com/Floflis/zeronet-rs/blob/feat/python-jsonl-bridge/docs/PYTHON-BRIDGE.md).

This first bridge does not expose tracker announce, outgoing peer connections, PEX, downloads, content verification, WebSocket commands, or plugin APIs. Add those operations incrementally only after their native contracts and tests are ready.

## 🌈 Recommended implementation sequence

1. **Merge and stabilize the JSONL bridge.** Test framing, request correlation, version rejection, malformed requests, process shutdown, and standard-output purity.
2. **Integrate native AnnounceLocal.** Start one Rust child, configure it with the Python peer ID/fileserver port/revision/sites, disable the Python UDP listener while Rust owns port 1544, and forward discovered candidates through the existing Python peer-add path.
3. **Migrate outgoing peer connections.** Match handshake fields, connection reuse, TLS/proxy/Tor policies, timeouts, and error semantics. Keep inbound Python serving.
4. **Migrate supported trackers and PEX.** Add cross-implementation fixtures and tracker-specific behavior tests; finish the separate `zero://` work before removing `AnnounceZero`.
5. **Migrate content operations.** Prove byte/signature/hash compatibility and full integrity verification before turning off Python download or content-management paths.

## 🌈 Acceptance criteria before commenting out a Python path

- The native operation covers the actual Python call sites, not only a subset of the class.
- Cross-implementation fixtures prove wire-format and data compatibility.
- Tests cover malformed messages, timeouts, transport errors, duplicate peers, and shutdown/restart behavior.
- The Python host still receives the events and state updates its UI, worker manager, and plugins expect.
- A tested fallback exists for platforms or runtime conditions where the native service cannot start.
- The relevant ZeroNet peer interoperability path has been exercised; unit tests alone are not enough.
- Rollback does not require deleting site data or changing legacy content formats.

