# ZeroNet plugin ecosystem: historical inventory

Status: research inventory, 2026-11-20.

This document records ZeroNet plugins and plugin-like extensions found during a historical ecosystem review. It is a research and compatibility reference for ZirohNeth, not a porting commitment and not evidence that every listed project is currently maintained or safe to run.

## Scope and classification

The inventory separates four different things:

1. **Core-distributed plugins**: directories shipped in the official ZeroNet core repository.
2. **Disabled/legacy core plugins**: code retained in the core tree under `disabled-*` directories.
3. **Independent community plugins**: separately maintained repositories that extend the ZeroNet client.
4. **Applications and roadmap ideas**: sites, services or proposals that are relevant historically but are not themselves confirmed client plugins.

A plugin directory, README or roadmap entry is not proof of current compatibility. Before porting anything, inspect its exact source revision, license, dependencies, security model and behavior.

## 1. Core-distributed plugins

Source: [HelloZeroNet/ZeroNet, plugins directory](https://github.com/HelloZeroNet/ZeroNet/tree/py3/plugins), branch `py3`.

The following 23 plugin directories were present in the inspected tree.

### Networking, discovery and peer state

| Plugin | Historical purpose |
|---|---|
| `AnnounceBitTorrent` | Peer discovery/announcement through BitTorrent trackers. |
| `AnnounceZero` | Peer announcement using ZeroNet's own announcement mechanism. |
| `AnnounceLocal` | Local-network peer discovery using UDP broadcast. |
| `AnnounceShare` | Sharing/distributing tracker information between clients. |
| `PeerDb` | Persisting peer information across client restarts. |

### Content, files and site management

| Plugin | Historical purpose |
|---|---|
| `Bigfile` | Support for large files and optional/partial file transfer. |
| `FilePack` | Transparent access to files stored in ZIP and TAR.GZ archives. |
| `MergerSite` | Combining content from multiple sites. |
| `OptionalManager` | Managing optional files: listing, pinning, downloading and removing them. |
| `ContentFilter` | Shared filtering/block lists for sites and users. |
| `Cors` | Configurable cross-origin resource sharing behavior. |
| `TranslateSite` | Translation support for site HTML and JavaScript resources. |
| `Newsfeed` | Following and retrieving feeds from other sites. |

### Cryptography and naming

| Plugin | Historical purpose |
|---|---|
| `CryptMessage` | Message encryption helpers, including ECIES/AES-related functionality. |
| `Zeroname` | Namecoin-based name resolution, including `.bit` names. |

### User interface, administration and diagnostics

| Plugin | Historical purpose |
|---|---|
| `Sidebar` | Sidebar and client-side administration/console UI. |
| `Stats` | Statistics and diagnostic pages. |
| `Benchmark` | Benchmarking facilities for selected client operations. |
| `Chart` | Graphical presentation of client/network statistics. |
| `Trayicon` | Operating-system system-tray integration. |
| `UiConfig` | Configuration management through the web UI. |
| `UiFileManager` | Web-based file browsing/management for site data. |
| `UiPluginManager` | UI and API for installing/managing third-party plugins. |

The descriptions above are functional summaries, not a claim that every feature is enabled in every ZeroNet release. Review the implementation and version history before relying on a specific behavior.

## 2. Disabled and legacy core plugins

The inspected core tree also contained these seven directories with a `disabled-` prefix:

| Directory | Historical purpose / area |
|---|---|
| `disabled-Bootstrapper` | Bootstrapper/tracker server functionality. |
| `disabled-Dnschain` | DNSChain-based name resolution. |
| `disabled-DonationMessage` | Donation messaging in the client UI. |
| `disabled-Multiuser` | Multi-user access to the web UI, using browser cookies/session handling. |
| `disabled-StemPort` | Tor control integration using Stem. |
| `disabled-UiPassword` | Password protection for the web UI. |
| `disabled-ZeronameLocal` | An alternative/local ZeroName resolver implementation. |

The `disabled-` prefix means the code was retained but not loaded as an ordinary enabled plugin in the inspected tree. It does not, by itself, establish why it was disabled, whether it worked in earlier releases, or whether it is safe to reactivate.

## 3. Other historical core plugin: Mute

The ZeroNet changelog/history records a **Mute** plugin/feature for muting users. It is not one of the 23 ordinary plugin directories in the inspected `py3/plugins` tree, so it is listed separately rather than counted as a currently present directory.

Source: [ZeroNet changelog](https://github.com/HelloZeroNet/ZeroNet/blob/py3/CHANGELOG.md).

## 4. Independent community plugins and extensions

These projects were found as separate repositories or independently distributed extensions. Their status labels describe the evidence found during this review, not a guarantee of current maintenance.

| Project | Historical purpose | Evidence / status |
|---|---|---|
| [Plugin-PeerMessage](https://github.com/HelloZeroNet/Plugin-PeerMessage) | Extends peer messaging/API behavior for real-time communication between clients. | Independent plugin repository. |
| [Plugin-BackgroundProcessing](https://github.com/HelloZeroNet/Plugin-BackgroundProcessing) | Background execution of site-provided Python code, intended to work independently of an open browser tab. | Independent plugin repository; requires a serious sandbox/security review. |
| [Plugin-Ark](https://github.com/purplesyringa/Plugin-Ark) | Adds Ark-related cryptographic support as an alternative signing/identity mechanism. | Independent plugin repository. |
| [Plugin-Gopher](https://github.com/purplesyringa/Plugin-Gopher) | Exposes ZeroNet content through the Gopher protocol. | Independent plugin repository. |
| [Plugin-Torrent](https://github.com/ZeroNetX/Plugin-Torrent) | Experimental integration of torrent/magnet downloads and media streaming with ZeroNet sites. | Repository describes the work as experimental/WIP; do not assume production readiness. |
| [Plugin-NameYo](https://github.com/ZeroNetX/Plugin-NameYo) | Name.YO domain/name resolution integration. | Independent plugin repository. |
| [zeronet-electrum-nmc-plugin](https://github.com/rllola/zeronet-electrum-nmc-plugin) | Namecoin `.bit` resolution through Electrum-NMC. | Independent repository; inspect its TODOs and dependencies before reuse. |
| [0net-NameTRUST-Resolver](https://github.com/rdp-studio/0net-NameTRUST-Resolver) | NameTRUST-based name-resolution integration. | Independent resolver project; exact runtime integration and maintenance status need further audit. |

### Related applications are not automatically plugins

The PeerMessage ecosystem also included or was associated with applications/services such as 0Play, Instant Messenger, StreamZ and zIRC. These should be catalogued as applications or services unless their own source proves they are installable ZeroNet client plugins.

Do not count a zite/site, chat application, game or streaming service as a plugin merely because it uses a plugin-provided API.

## 5. ZeroNet+ and proposed extensions

The archived [ZeroNetPlus application repository](https://github.com/ZeroNetPlus/ZeroNetPlus) and its [project website repository](https://github.com/ZeroNetPlus/ZeroNetPlus.github.io) documented additional ideas.

The ZeroNet+ roadmap included:

- Plugin Store.
- CDN integration.
- Addresscoin / `.www` naming.
- Video downloading.
- Live streaming.
- Installation of essential zites.
- Communication between the desktop application and plugins.
- Updates distributed through GitHub/P2P.
- Publishing to the DAT network.

The DAT publishing idea was also tracked in [ZeroNetPlus issue #46](https://github.com/ZeroNetPlus/ZeroNetPlus/issues/46).

**These are roadmap items, not verified shipped plugins.** The ZeroNet+ materials described an early-stage application and explicitly noted that its own plugin had not yet been developed. The DAT issue contains no implementation specification or code demonstrating a working ZeroNet-to-DAT bridge.

The ZeroNet+ Plugin Store proposal is nevertheless a useful product/UX predecessor for a ZirohNeth extension registry.

## 6. Historical plugin installation model

ZeroNet's `UiPluginManager` provided a user-facing plugin installation flow. A plugin could be distributed from a site, with a manifest such as `plugin_info.json` and Python implementation files.

The client exposed a request API used by site JavaScript, including the historical `pluginAddRequest` command. Installation required user confirmation.

Relevant source: [UiPluginManagerPlugin.py](https://github.com/HelloZeroNet/ZeroNet/blob/py3/plugins/UiPluginManager/UiPluginManagerPlugin.py).

### Security limitation

The historical Python plugin model must not be mistaken for a safe sandbox. Client-loaded Python plugins could run with the privileges of the ZeroNet process. Site JavaScript sandboxing did not automatically isolate native/client plugins.

A ZirohNeth plugin registry should therefore treat installation and execution as separate trust boundaries.

## 7. Implications for ZirohNeth

The historical ecosystem suggests four useful extension families. These are proposed ZirohNeth taxonomy labels, not existing implementation commitments.

| Proposed family | Historical references | Possible ZirohNeth scope |
|---|---|---|
| Network extensions | AnnounceLocal, AnnounceBitTorrent, PeerDb, Plugin-Torrent, Plugin-Gopher | Peer discovery, transports, protocol adapters and network bridges. |
| Storage/content extensions | Bigfile, FilePack, OptionalManager, MergerSite | Large-object handling, archive views, selective retrieval and content adapters. |
| Runtime/service extensions | PeerMessage, BackgroundProcessing, CryptMessage, Plugin-Ark | Messaging, background tasks, cryptographic providers and service APIs. |
| UI/application extensions | Sidebar, UiConfig, UiFileManager, UiPluginManager, Newsfeed | Administration, discovery, site tooling and user-facing integrations. |

### Recommended design constraints

1. **Versioned manifests:** define a stable plugin identifier, semantic version, API compatibility range, author, license, source location and cryptographic artifact digest.
2. **Declared capabilities:** require explicit permissions for filesystem access, network access, storage, identity/signing, background execution and administrative APIs.
3. **Isolation by default:** prefer WASM or separately sandboxed processes for untrusted extensions. Do not load third-party native code into the daemon process by default.
4. **Reproducible provenance:** record the source repository, immutable source revision, build inputs and artifact digest.
5. **Reviewable updates:** support signature verification, rollback and explicit trust decisions. A mutable Git branch or a site-hosted manifest alone is not a trust root.
6. **API stability:** expose versioned host APIs rather than allowing extensions to depend on private daemon internals.
7. **Resource controls:** define CPU, memory, disk, bandwidth and background-task limits.
8. **No implicit trust inheritance:** a trusted site must not automatically make every plugin it hosts trusted.

### Candidate audit order

The following are good first subjects for code-level study, not automatic porting targets:

1. **PeerMessage** — peer-to-peer messaging and event/API design.
2. **BackgroundProcessing** — background task lifecycle and isolation requirements.
3. **Bigfile** — large-file and partial-transfer behavior.
4. **Plugin-Torrent** — protocol interoperability and streaming behavior.
5. **FilePack** — archive-backed virtual file access.
6. **AnnounceLocal** — local peer discovery.
7. **Plugin-Ark** — pluggable cryptographic provider design.

For each candidate, record the exact upstream commit, license, dependencies, security boundaries, API surface, tests and a decision: port, adapt, replace, defer or reject.

## 8. Sources and audit boundaries

Primary sources:

- [HelloZeroNet/ZeroNet — core plugins](https://github.com/HelloZeroNet/ZeroNet/tree/py3/plugins)
- [HelloZeroNet/ZeroNet — changelog](https://github.com/HelloZeroNet/ZeroNet/blob/py3/CHANGELOG.md)
- [HelloZeroNet/ZeroNet — UiPluginManager](https://github.com/HelloZeroNet/ZeroNet/blob/py3/plugins/UiPluginManager/UiPluginManagerPlugin.py)
- [HelloZeroNet/Plugin-PeerMessage](https://github.com/HelloZeroNet/Plugin-PeerMessage)
- [HelloZeroNet/Plugin-BackgroundProcessing](https://github.com/HelloZeroNet/Plugin-BackgroundProcessing)
- [purplesyringa/Plugin-Ark](https://github.com/purplesyringa/Plugin-Ark)
- [purplesyringa/Plugin-Gopher](https://github.com/purplesyringa/Plugin-Gopher)
- [ZeroNetX/Plugin-Torrent](https://github.com/ZeroNetX/Plugin-Torrent)
- [ZeroNetX/Plugin-NameYo](https://github.com/ZeroNetX/Plugin-NameYo)
- [rllola/zeronet-electrum-nmc-plugin](https://github.com/rllola/zeronet-electrum-nmc-plugin)
- [rdp-studio/0net-NameTRUST-Resolver](https://github.com/rdp-studio/0net-NameTRUST-Resolver)
- [ZeroNetPlus/ZeroNetPlus](https://github.com/ZeroNetPlus/ZeroNetPlus)
- [ZeroNetPlus/ZeroNetPlus.github.io](https://github.com/ZeroNetPlus/ZeroNetPlus.github.io)
- [ZeroNetPlus issue #46: Publish to DAT network](https://github.com/ZeroNetPlus/ZeroNetPlus/issues/46)

This is a bounded repository/history review, not an exhaustive census of every plugin ever published on ZeroNet. Repositories may have been deleted, renamed, moved off GitHub or distributed only through ZeroNet sites. Historical descriptions should be revalidated against source before implementation.
