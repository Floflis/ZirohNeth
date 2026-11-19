# 🌈 RFC-0001: Native iroh transport for content.json v3

- **Project:** Floflis / ZirohNeth
- **Status:** Draft for architectural review
- **Created:** 2026-11-19
- **Target repository:** Floflis/ZirohNeth
- **Related repository:** Floflis/ZirohNeth-dashboard
- **Scope:** Architecture, protocol boundaries, compatibility, and migration plan
- **Implementation status:** Proposal only; this RFC does not implement the v3 transport

## 🌈 1. Abstract

This RFC proposes a three-generation architecture for ZirohNeth:

- **Content v1** remains the existing ZeroNet-compatible Bitcoin/SHA-512 implementation and continues to use the existing ZeroNet peer protocol and discovery behavior.
- **Content v2** remains the existing Ethereum EOA/EIP-712/BLAKE3 content format and continues to use the existing ZeroNet transport path. V2 is not retroactively moved to iroh.
- **Content v3** is the first content format whose native network transport is iroh. Its networking implementation should be written in Rust using the native iroh crates, rather than extending the Python/ZeroNet networking runtime.

This is an explicit version boundary: the ZeroNet-to-iroh transport replacement happens **only for content.json v3**. A v1 or v2 site must continue to use the legacy transport unless and until its owner explicitly performs a separately authenticated migration to v3. A v2 site must not be silently reinterpreted as a v3 site, and a failed v3 validation must never fall back to v2 or v1.

The goal is not merely to download and publish files through iroh. ZirohNeth must preserve the useful application semantics that made ZeroNet compelling: local browser access, site hosting by visitors, offline browsing, one-click cloning, signed user content, ZeroID-like identity, name resolution, permissions, optional files, social applications, and multi-user application data.

The proposed implementation keeps Python where it provides value to the existing application and legacy network, while placing the v3 network-critical path in native Rust. Rust is not proposed because Python is incapable of production use. It is proposed because the v3 transport is built directly on a Rust-native networking stack, and a product-critical asynchronous P2P runtime benefits from native type boundaries, ownership, memory safety, explicit concurrency, and a deployable runtime that does not require the legacy Python/gevent networking machinery.

## 🌈 2. Version contract: v1, v2, and v3

This version boundary is normative for the proposal.

| Content version | Identity and content | Transport | Compatibility promise |
|---|---|---|---|
| **v1** | Bitcoin identity, legacy signatures, SHA-512 | Existing ZeroNet Python peer protocol | Preserve current behavior |
| **v2** | Ethereum EOA, EIP-712, BLAKE3-256 | Existing ZeroNet Python peer protocol | Preserve current behavior |
| **v3** | Ethereum-based identity, versioned EIP-712 profile, BLAKE3-256 | Native iroh transport, implemented in Rust | New native protocol and application path |

### 2.1. V1 remains legacy ZeroNet

V1 retains its existing Bitcoin identity rules, legacy manifest interpretation, SHA-512 checks, tracker/DHT/PEX discovery, peer RPC, file-transfer scheduling, user-content behavior, and Tor integration as currently supported.

The v3 project must not remove a dependency from the shared application if the v1 runtime still needs it.

### 2.2. V2 remains ZeroNet-transported

V2 already introduces Ethereum identity and EIP-712/BLAKE3 manifest support, but that does not make it an iroh site. V2 continues to use the existing ZeroNet peer/network path.

This is intentional. V2 is a supported compatibility generation, not an unfinished transport migration and not an alias for v3.

No v2 manifest should gain an iroh transport merely because a newer client is installed. If the owner wants to move a v2 site to v3, that must be an explicit, authenticated format transition with a new v3 genesis/head record.

### 2.3. V3 is the transport replacement boundary

V3 is the first version that selects a native iroh network stack. This means:

- a v3 site is discovered and connected through the v3 discovery/provider model;
- v3 content transfer uses iroh streams and the selected blob/content protocol;
- v3 publishing announces signed v3 heads and provider availability through v3 mechanisms;
- v3 must not instantiate the legacy ZeroNet Peer object to perform network operations;
- v1 and v2 still use the legacy Python path.

### 2.4. Keep version axes independent

The content format version, transport ALPN version, identity scheme, signature scheme, digest algorithm, and application protocol version are different axes.

Do not infer transport version from content version. A manifest declares its content profile. An iroh ALPN selects a wire protocol. Their evolution must be independent.

## 🌈 3. Repository observations

The observations below are based on Floflis/ZirohNeth main as inspected on 2026-11-19. They describe the inspected code, not future branches.

### 3.1. Manifest signing and verification

Relevant file: **src/Content/ContentManager.py**

- The signing path selects Ethereum when the supplied private-key string has the explicit eth: prefix. Bare hexadecimal key strings retain their historical Bitcoin meaning.
- The current Ethereum signing path writes content_version = 2, hash_algorithm = blake3-256, identity_scheme, signature_scheme, sequence, and previous_update_digest.
- Ethereum v2 signing is explicitly restricted to the root content.json. Attempting to sign an included manifest raises SignError.
- Required v2 files must carry a BLAKE3 digest and may not also carry a SHA-512 field under the current verifier.
- Optional v2 files are more permissive: BLAKE3 is accepted, but legacy SHA-512 optional entries can also be accepted when they declare sha512-truncated-256.
- verifyFile has an EIP-712 path for v2, but non-root manifests still pass through verifyCert.
- verifyCertSign currently calls CryptBitcoin.verify. Certificate authorization therefore remains Bitcoin-specific even though the root manifest can use Ethereum.
- The v2 root update-chain check compares a new manifest with the locally stored predecessor. It returns unverified_first_contact when no predecessor is available.

**Consequences:** the existing v2 root can be authenticated with Ethereum, but the current signing/certificate model is not yet a complete Ethereum-native user-content path. V3 must define this path directly rather than assuming the current v2 root-signing implementation already solves it.

### 3.2. Ethereum signing module

Relevant file: **src/Crypt/CryptEthereum.py**

The module defines ethereum-eoa-secp256k1 as its identity scheme and ethereum-eip712-v1 as its signature scheme. It calculates BLAKE3-256 over an RFC 8785 canonicalized protected manifest, supports EIP-712 signing and recovery, and checks update continuity against a locally trusted predecessor.

The verifier correctly distinguishes first contact from locally continuous history: a valid signature authenticates the signer and manifest, but does not prove that the observed manifest is globally newest.

The current v2 root path enforces a single EOA signer. Multisig, threshold signing, delegated publisher keys, and a general certificate/capability model are not implemented by this module.

### 3.3. Bitcoin-to-Ethereum migration

Relevant file: **src/Crypt/CryptMigration.py**

The repository has dual-signature migration primitives. A migration record binds the old Bitcoin identity and new Ethereum identity, and the v2 migration payload uses BLAKE3 over canonical data. The code verifies a Bitcoin authorization and an Ethereum acceptance.

CheckpointStore persists a locally observed migration chain. Site blocks a historical Bitcoin identity from publishing new files or non-root manifests after migration, and SiteManager can resolve a legacy address to its Ethereum destination after validating the migration record and local checkpoint.

A local checkpoint prevents a client from silently accepting a different later migration after it has pinned one. It does not prove that all first-contact clients worldwide observed the same migration history. Global freshness, migration equivocation, and first-contact trust remain protocol questions.

### 3.4. Legacy peer networking

Relevant files:

- **src/Peer/Peer.py**
- **src/Peer/PeerHashfield.py**
- **src/Site/SiteAnnouncer.py**
- **src/Site/Site.py**
- **src/Worker/WorkerManager.py**

The legacy Peer abstraction is more than a socket wrapper. It owns a peer address, connection, reputation, response timing, hashfield state, failure counters, and transfer statistics.

- Peer.request sends command-oriented requests over the existing connection.
- File transfer uses getFile or streamFile.
- Publishing uses update.
- Availability uses getHashfield, findHashIds, and setHashfield.
- WorkerManager schedules download tasks against legacy peers, retries failed tasks, excludes failed peers, and can re-query providers for optional files.
- SiteAnnouncer announces through configured trackers, invokes the existing DHT announcer, and performs PEX by asking connected or recently seen peers for more peers.
- Tracker/DHT results feed Site.addPeer and then the legacy worker manager.

Replacing only Peer.request would retain the old peer model in task scheduling, publication, provider lookup, and site status. V3 needs a provider-oriented transfer scheduler and separate discovery path.

### 3.5. Hashfield

Relevant file: **src/Peer/PeerHashfield.py**

PeerHashfield has introduced algorithm namespaces for SHA-512 and BLAKE3 while retaining an untyped legacy projection for older peers. Its documentation correctly says that hashfield entries are availability hints and integrity must still be verified after download.

This is useful migration work, but it remains a prefix-based peer-availability structure. It is not a content-addressed provider directory, a full blob identity, or an iroh discovery protocol.

V3 must not treat a 16-bit prefix, an old hashfield entry, or a provider advertisement as proof that a provider has the requested full blob.

### 3.6. Site lifecycle and storage

Relevant files:

- **src/Site/Site.py**
- **src/Site/SiteManager.py**
- **src/Site/SiteStorage.py**
- **src/Content/ContentDbDict.py**
- **src/Db/Db.py**

Site owns a legacy peer dictionary and worker manager, creates a ContentManager, and manages local storage. Its download and publish paths use the legacy site/peer lifecycle. Site.clone copies files and included manifests, sets clone metadata, and re-signs manifests using the new site's key.

SiteStorage owns the on-disk site directory, file operations, validation/recovery, and the local SQLite cache/database lifecycle. Db uses SQLite and local transaction/commit management.

Replacing the transport must not imply replacing the local storage model. Locally verified files and the local SQL cache remain useful and should continue supporting offline access.

### 3.7. Name resolution

Relevant file: **src/Site/SiteManager.py**

In the inspected code, SiteManager.isDomain() and resolveDomain() return False. Domain resolution is not currently implemented in this core path.

This RFC does not describe ZeroName as a working feature that only needs a transport swap. It proposes a NameResolver interface and an Ethereum-compatible resolution design so ZeroName-like behavior can be implemented as a new application service.

### 3.8. Python dependencies and Rust integration

Relevant file: **requirements.txt**

The inspected dependency list includes gevent, msgpack, existing BitTorrent DHT/KRPC dependencies, BLAKE3, eth-account, and rfc8785. No root Cargo.toml was found in the inspected repository state.

The inspected root therefore does not currently contain an integrated Rust iroh runtime. V3 needs a deliberate Rust project/build boundary, runtime supervision, platform packaging, and IPC/API contract. It should not quietly add a Python wrapper around the old networking stack and call that native iroh.

### 3.9. Dashboard trust boundary

Relevant repository: **Floflis/ZirohNeth-dashboard**, README.md

The dashboard documentation already describes the right trust boundary: it presents verification and migration status supplied by the core and does not independently validate Bitcoin/EIP-712 signatures. It consumes fields such as content_verification_status and migration_state.

Keep that rule for v3. The browser UI must not infer cryptographic verification, migration validity, provider authenticity, or freshness from unverified manifest fields or peer-supplied labels.

## 🌈 4. Goals and non-goals

### 4.1. Goals

- Keep v1 and v2 semantics and their existing ZeroNet transport path operational.
- Make content v3 use a native iroh transport path implemented in Rust.
- Keep the browser gateway and user-facing site lifecycle stable where practical.
- Define independent interfaces for content verification, identity, transport, discovery, provider availability, storage, and application replication.
- Bind iroh endpoints to Ethereum site identities without conflating them.
- Support multiple endpoints/devices per site identity and endpoint rotation.
- Separate discovery, provider availability, content authenticity, and content authorization.
- Support BLAKE3-addressed required and optional content.
- Define Ethereum-native user certificates and included/user manifests.
- Preserve SiteClone, offline browsing, permissions, social applications, and multi-user application semantics.
- Define a safe and explicit v2-to-v3 transition.
- Measure performance, reliability, memory, resource use, and packaging rather than assuming Rust is automatically faster in every workload.

### 4.2. Non-goals

This RFC does not:

- Change the transport used by v1 or v2.
- Port the entire existing application to Rust in one step.
- Implement the iroh runtime or application protocol.
- Select a final wire serialization format.
- Define a production Ethereum contract for ZeroName or migration transparency.
- Claim Ethereum EOA identities provide anonymity.
- Claim iroh relays provide Tor-equivalent anonymity.
- Replace every social data type with a generic CRDT.
- Mandate iroh-docs as the database or user-content format.
- Replicate arbitrary SQL statements or SQLite files between peers.
- Make v1/v2 clients understand v3.
- Treat endpoint discovery or provider lookup as consensus.

## 🌈 5. Architectural decision: native Rust for the v3 network path

### 5.1. The recommendation

Implement the v3 network runtime and iroh application protocols in Rust. Use iroh as a Rust-native library, not as a Python process that shells out to a separate command for each network operation and not as a thin label over the existing ZeroNet Peer API.

The recommended transition architecture is:

- Python continues to host the existing v1/v2 compatibility runtime.
- A Rust v3 service owns the iroh Endpoint, protocol handlers, discovery/address lookup, provider index client, blob transfer, v3 head subscriptions, and v3 transfer scheduler.
- Python and Rust communicate through a versioned local IPC/API boundary for site lifecycle, browser-gateway integration, dashboard status, and migration coordination.
- V3-specific content and identity verification should move into Rust modules where doing so avoids divergent security implementations. The first milestone may call into the existing Python crypto implementation only through a documented temporary boundary, but it must not duplicate verification rules indefinitely.
- The boundary may shrink over time as more v3 responsibilities move into Rust. This is an incremental migration, not a requirement to rewrite the whole legacy application before shipping v3.

A direct Rust library embedding into Python can be reconsidered after the protocol and lifecycle contracts stabilize. The initial design should prefer a supervised sidecar/service because it provides process isolation and avoids coupling gevent, Python runtime lifetime, and iroh's asynchronous runtime in one address space.

### 5.2. Why native Rust is valuable for iroh

Iroh is a Rust-native networking stack. Implementing v3 in Rust allows ZirohNeth to use its native types, async APIs, connection lifecycle, QUIC streams, and protocol crates directly.

Expected advantages:

1. **Direct use of iroh APIs.** Endpoint, connection, stream, ALPN, discovery/address lookup, and blob protocol types can be composed without forcing them through a Python object model.
2. **Clear ownership of network resources.** Rust ownership and borrowing make endpoint, connection, stream, cancellation, and buffer lifetimes explicit. This is valuable in a long-running peer-to-peer process with many concurrent transfers.
3. **Memory safety in the critical path.** Safe Rust prevents broad classes of use-after-free and data-race bugs at compile time. It does not eliminate logic bugs, denial-of-service risks, unsafe-code defects, or protocol vulnerabilities, but it makes certain classes of memory/concurrency mistakes harder to introduce.
4. **Explicit concurrency and cancellation.** The runtime can structure concurrent peer sessions, streams, timeouts, backpressure, shutdown, and retry policy around Rust's async ecosystem rather than extending the existing gevent-oriented peer model.
5. **Typed protocol boundaries.** Message variants, protocol versions, identity states, authorization results, and error classes can be represented as enums and validated structures. This reduces the chance that an untrusted remote response becomes a loosely typed dictionary that leaks invalid state into the application.
6. **Fewer language-boundary conversions on the network path.** A native implementation avoids repeatedly converting binary payloads, stream chunks, endpoint identifiers, and error states between Rust and Python for every transfer.
7. **A more self-contained v3 runtime.** A packaged Rust service can ship as a platform-specific executable without requiring the user's Python environment, Python package resolver, or gevent runtime for v3 networking. It still has native platform dependencies and needs reproducible build and update practices.
8. **A cleaner security boundary.** The network parser, quotas, stream lifecycle, and transfer verification can be concentrated in a small, auditable Rust component with a narrow API to the larger legacy application.
9. **Potentially lower overhead under concurrency.** A native async implementation may reduce per-connection/per-task overhead and improve resource efficiency. This is a hypothesis to benchmark, not a guaranteed speedup. Network conditions, storage, cryptography, scheduler design, and implementation quality can dominate.
10. **A path away from accidental ZeroNet coupling.** V3 gets its own provider discovery, transport, transfer scheduler, and lifecycle instead of inheriting the assumptions embedded in Peer, SiteAnnouncer, hashfields, and WorkerManager.

### 5.3. What Rust does not automatically solve

Rust does not automatically provide:

- a complete ZeroNet replacement;
- a provider discovery protocol;
- a ZeroID or ZeroName service;
- correct authorization policy;
- protection against Sybil attacks or spam;
- globally fresh manifests;
- deterministic application conflict resolution;
- anonymity;
- compatibility with all existing Python plugins;
- portable builds for every platform without work.

The application protocol, identity bindings, security model, migration rules, and tests are still ZirohNeth responsibilities.

### 5.4. Python is still useful and can ship production software

This RFC does not assert that Python is unsuitable for serious products. Python is widely useful in production systems, including network services, automation, application backends, and AI systems. The recommendation is narrower: the v3 network-critical path should be implemented in the language of its native networking stack, while the existing Python application continues to serve the legacy generations and higher-level integration where it is effective.

Keep Python for:

- v1/v2 compatibility and existing ZeroNet behavior;
- legacy plugin execution that cannot be safely migrated immediately;
- high-level application orchestration during the transition;
- administrative commands and automation where startup/runtime constraints permit;
- fast experimentation, test harnesses, migration tooling, and protocol prototypes;
- dashboard/API integration until the Rust service contract is stable.

Do not keep Python in the v3 hot path solely because the old implementation uses Python.

### 5.5. Analogy: Python as the AI laboratory, Rust as the product engine

A useful analogy comes from AI development.

Python is excellent for trying an idea quickly: load a model, change a preprocessing step, test a prompt, compare an architecture, plot results, or wire together a training experiment. Its high-level syntax and ecosystem reduce the distance between a hypothesis and an experiment. That is why it is such a productive prototyping and orchestration language.

But the Python notebook is not automatically the finished inference engine. When a system becomes a product, the team must address bounded memory, predictable latency, concurrency, batching, cancellation, hardware utilization, crash behavior, deployment, observability, security boundaries, and long-term compatibility. Performance-critical AI operations commonly run in native kernels or runtimes such as C++, CUDA, or other compiled components, while Python remains the convenient control plane.

The analogy for ZirohNeth is:

- Python is the workbench where we can quickly explore protocol semantics, test migration ideas, generate fixtures, inspect state, and iterate on application workflows.
- Rust/iroh is the production networking engine that owns long-lived endpoints, untrusted network input, concurrent streams, transfer scheduling, and the v3 protocol boundary.

The workbench is valuable; the engine must be engineered for the operating conditions it will actually face.

The analogy is not a claim that Python cannot be deployed as a product or that every AI stack replaces Python. Some successful systems ship Python directly. The decision should be driven by the runtime's requirements and measured results, not by language fashion.

### 5.6. Sidecar vs native binding

**Recommended first implementation: supervised Rust sidecar.**

Advantages:

- process isolation between the legacy gevent application and iroh runtime;
- one Rust async runtime can own all v3 endpoints and streams;
- Rust crashes or panics are less likely to corrupt the Python process;
- Rust dependency upgrades do not require importing a large native extension into Python;
- easier independent testing of the v3 protocol;
- a clear migration boundary for the Python application.

Costs:

- a second process must be supervised, restarted, upgraded, and shut down cleanly;
- IPC schemas need versioning and validation;
- cross-process file ownership and locking must be defined;
- package builders must ship and verify the correct executable for each platform;
- logs, metrics, and tracing must be correlated across processes.

A PyO3 or other native binding can reduce IPC overhead and simplify some in-process calls, but it couples Python and Rust lifetimes, build systems, runtime initialization, exception conversion, and distribution. Revisit it only after stable interfaces and profiling show that IPC is a real bottleneck.

### 5.7. Local IPC contract

The sidecar should expose a small, versioned local API. It should not expose a generic arbitrary-command tunnel that recreates the old RPC protocol.

Initial operation families:

- **Runtime:** health, version, capabilities, shutdown.
- **Site:** register/unregister a v3 site profile, get local state.
- **Manifest:** publish signed head, request current head, subscribe to head changes.
- **Content:** fetch verified blob, publish/announce blob availability, cancel transfer.
- **Discovery:** resolve endpoint bindings, find candidate providers.
- **Identity:** validate endpoint binding and capability records; request verification state.
- **Events:** transfer progress, connection changes, provider changes, manifest conflicts, errors.

IPC requirements:

- authenticate local callers using OS permissions and an appropriate local transport;
- use a versioned request/response envelope;
- enforce message and payload limits;
- do not expose private keys through generic RPC;
- stream large blobs through a controlled file descriptor/handle or bounded streaming API rather than copying unbounded payloads into one message;
- make operations cancellable and idempotent where appropriate;
- report typed error codes;
- define startup readiness and crash-recovery behavior;
- support Windows named pipes and Unix-domain sockets, or document a platform-specific equivalent.

## 🌈 6. V3 manifest and cryptographic profile

### 6.1. V3 is a new signed content format

V3 must use content_version = 3. Do not use content_version = 2 with an extra transport field to signal an incompatible network protocol.

V3 may reuse the Ethereum EOA identity family and BLAKE3-256 file digest family introduced by v2, but the v3 manifest and signature profile must be explicitly versioned and domain-separated.

Proposed profile fields:

- content_version = 3;
- identity_scheme with an explicit supported Ethereum identity profile;
- signature_scheme naming the v3 EIP-712 domain/type profile;
- hash_algorithm = blake3-256;
- a monotonically increasing sequence;
- a previous v3 update digest;
- site address;
- file manifest and permission metadata;
- transport profile identifier indicating the supported v3 iroh application profile, if transport selection is part of the signed content contract.

Exact field names and canonicalization rules must be frozen by test vectors before implementation.

### 6.2. Do not change v2 verification semantics

V2 verification must remain as it is for v2 sites. Do not alter the v2 EIP-712 domain, hash interpretation, key-selection rules, or transport selection as a side effect of introducing v3.

V3 should use an explicitly distinct EIP-712 domain/type profile so signatures cannot be accidentally replayed across versions or other ZirohNeth application domains. Include network/chain context where relevant and define precisely which fields are signed. A change in signature scheme name alone is not domain separation; the typed data itself must bind the intended protocol/version/domain.

### 6.3. Manifest freshness

The current v2 verifier returns unverified_first_contact when there is no locally trusted predecessor. Preserve this honest distinction.

A first-contact client can validate syntax, declared schemes, the signer, signature, file metadata, paths, and permissions. It cannot prove from one signed manifest alone that no newer update exists or that the owner has not signed a competing history.

V3 needs:

- locally persisted accepted head digest and sequence;
- previous-head validation;
- same-sequence conflict detection;
- signed evidence retention for equivocation;
- explicit stale/fork/conflict states;
- a documented recovery process;
- optional transparency/checkpoint integration as a separately specified trust enhancement.

Do not equate a valid signature with a globally current manifest.

### 6.4. Content vs transport metadata

Keep dynamic network state out of the content manifest where possible.

Relay URLs, local IP addresses, endpoint addresses, provider lists, connection statistics, and provider expiry must not force a content manifest update every time a device changes network.

Use separately signed endpoint-binding and provider records. The manifest identifies the site and content; the network records tell clients where they may retrieve it.

## 🌈 7. V2-to-v3 transition and v1 migration

### 7.1. V2-to-v3 is explicit

A v2 site remains a v2 site on the legacy transport until its owner chooses to publish a v3 transition.

The transition must bind:

- the existing v2 site identity;
- the exact last accepted v2 manifest digest and sequence;
- the v3 content profile;
- the new v3 genesis manifest digest;
- the intended site identity (same Ethereum identity or explicitly rotated identity);
- the authorization to make v3 the active publication generation;
- a transition sequence/identifier and timestamp for audit purposes.

If the Ethereum owner identity is unchanged, the same owner key may authorize the transition, but the signature still needs a v3-specific domain and an explicit reference to the final v2 head. If ownership changes, require authorization from the old owner and acceptance by the new owner, with a precise recovery policy.

A transition record is not proof that every client globally observed the same state. First-contact trust and equivocation still need an explicit solution.

### 7.2. Do not reuse Bitcoin migration rules blindly

The existing CryptMigration code addresses Bitcoin-to-Ethereum identity handoff. A v2-to-v3 transition usually changes content/transport generation while retaining the Ethereum identity family. Do not overload the Bitcoin migration record or pretend that a format upgrade is the same as an ownership migration.

Define a distinct VersionTransition record. It can reuse proven canonicalization/signature utilities, but it needs its own schema, domain separation, sequencing, and tests.

### 7.3. Preserve v1-to-v2/v3 historical identity behavior

Do not weaken the existing Bitcoin-to-Ethereum terminal migration rule. A historical Bitcoin identity must not regain publication authority after its accepted terminal migration.

If a migrated site later moves from v2 to v3, the client should validate the Bitcoin migration first, resolve the accepted Ethereum identity, then validate the distinct v2-to-v3 version transition. The historical Bitcoin identity, current Ethereum identity, and iroh endpoint IDs remain different entities.

### 7.4. No implicit v2-to-v3 conversion

The client must not rewrite v2 content into v3 merely by opening it. No automatic background conversion, key reinterpretation, transport substitution, or destructive cache migration is allowed.

The owner must explicitly sign/publish the transition. Clients should retain the last verified v2 state for rollback/audit and show a clear generation transition.

## 🌈 8. Iroh integration

### 8.1. Native Rust runtime

The v3 Rust service owns the iroh endpoint and the application protocol handlers. Use one managed endpoint per running service initially, and multiplex the supported v3 protocols above it. Multiple sites can share the endpoint runtime; site ownership and authorization remain site-scoped.

Iroh provides encrypted peer connectivity, endpoint identity, QUIC connections, and streams. ZirohNeth defines the site/application protocol carried over those connections.

Upstream references:
- https://docs.rs/iroh/latest/iroh/
- https://docs.rs/iroh/latest/iroh/endpoint/struct.Endpoint.html

### 8.2. ALPN

Define a ZirohNeth-owned ALPN namespace, initially proposed as:

~~~text
zirohneth/site-transport/1
~~~

This is the first revision of the v3 transport wire protocol. It is not the content manifest version. A future transport revision can evolve independently while the v3 content profile remains supported.

Do not reuse iroh-blobs, iroh-gossip, or iroh-docs ALPN identifiers for ZirohNeth application messages. If the service also hosts standard iroh protocols, register those under their own documented protocol identifiers and enforce the intended authorization boundary.

### 8.3. Message envelope

The ZirohNeth application protocol needs a bounded, versioned message envelope containing at minimum:

- wire protocol version;
- message type;
- request/correlation ID where request-response semantics apply;
- site/content scope;
- payload length and resource budget;
- typed payload;
- explicit status/error code.

Choose a serialization format after comparing schema evolution, canonical encoding, fuzzability, platform support, and Rust/Python interoperability. Use deterministic encoding for signed/hashed data. Ordinary JSON serialization is not a wire canonicalization rule.

The first message family should be deliberately small:

- HELLO / NEGOTIATE;
- IDENTIFY / AUTHORIZE;
- RESOLVE_HEAD;
- ANNOUNCE_HEAD;
- SUBSCRIBE_HEAD;
- DISCOVER_PROVIDERS;
- GET_MANIFEST;
- GET_BLOB / GET_BLOB_RANGE;
- ANNOUNCE_PROVIDER;
- CANCEL;
- CLOSE.

These names are illustrative. They do not imply that an implementation exists.

### 8.4. Endpoint identity is not site identity

An Ethereum site address identifies the site owner under the v2/v3 identity family. An iroh EndpointId identifies a transport endpoint/key. They are not interchangeable.

One Ethereum site identity may be served by the owner's desktop, laptop, mobile device, community mirror, authorized hosting operator, or multiple independent replicas.

An endpoint must prove possession of its iroh endpoint key during connection establishment. Separately, it must present a valid site/endpoint binding signed by the site owner or an authorized delegate.

Proposed logical binding fields:

~~~json
{
  "record_version": 1,
  "site_address": "0x...",
  "endpoint_id": "<canonical iroh EndpointId>",
  "alpn": "zirohneth/site-transport/1",
  "capabilities": ["manifest-read", "blob-read"],
  "issued_at": 0,
  "expires_at": 0,
  "binding_sequence": 1,
  "previous_binding_digest": "0x...",
  "signature_scheme": "v3 EIP-712 profile",
  "signature": "0x..."
}
~~~

This is an illustrative schema, not a committed wire format.

The signed binding must include endpoint ID, site address, ALPN, capability scope, validity interval, sequence, prior-binding reference, and appropriate protocol/network domain separation.

Endpoint bindings are independently publishable and rotatable. Changing a relay URL or local IP address must not require changing the site content manifest. Endpoint rotation must not change the site identity.

Delegated mirrors need scoped capabilities. A mirror authorized to serve blobs must not thereby gain permission to publish a new root manifest.

### 8.5. Key separation

Do not reuse the Ethereum site-owner private key as the iroh endpoint secret key.

Use separate keys for:

- Ethereum site ownership and manifest authorization;
- iroh endpoint identity;
- per-user identity and signing;
- delegated publishing/service capabilities;
- application encryption and private messaging.

Site-owner key rotation needs an authenticated transition or recovery mechanism. Endpoint key rotation should require a new signed endpoint binding unless the endpoint also holds a delegated application capability.

Private keys must never be serialized into manifests, discovery records, provider advertisements, logs, diagnostic responses, or generic IPC payloads.

### 8.6. Direct connections, relays, and privacy

Support direct IPv4/IPv6 paths where available and relay-assisted connectivity where needed. Expose connection mode and failure reasons as diagnostics, not as trust decisions.

A relay carries traffic; it does not authenticate site ownership, validate content, or decide which peer is authorized to publish.

The v3 threat model must document that encrypted transport is not anonymity. Endpoint metadata, relay observations, timing, IP addresses, and discovery lookups can reveal information. V1 Tor behavior remains unchanged. V3 must not claim Tor-equivalent anonymity without a separately designed and tested privacy transport.

## 🌈 9. Discovery and provider availability

Discovery must answer two separate questions:

1. **How do I dial this endpoint?** Address lookup resolves an iroh EndpointId into relay/direct addressing information.
2. **Which endpoints may have this site manifest or blob?** ZirohNeth provider discovery maps a site/content identifier to candidate endpoints.

Do not collapse these questions into one DHT key or assume that endpoint discovery finds content providers automatically.

### 9.1. Endpoint address lookup

Define a pluggable address-lookup interface. Candidate mechanisms include static/bootstrap records, DNS/PKARR-backed discovery, a DHT discovery provider, local-network discovery, self-hosted discovery services, cached signed endpoint bindings, and invitation/ticket-based initial contacts.

The inspected current iroh documentation describes several address lookup implementations, including DNS/PKARR, local swarm discovery, and DHT discovery. The public number0 DNS/PKARR service can be a convenient default, but it must remain an optional provider rather than a hidden mandatory central dependency.

Document the exact defaults and trust assumptions. A self-hosted installation must be able to configure alternative address lookup and relay infrastructure.

Reference: https://docs.rs/iroh-net/latest/iroh_net/discovery/index.html

### 9.2. Provider index

Create a v3 ProviderIndex mapping full content identifiers to candidate providers.

A provider record should include:

- complete content digest and algorithm, not a 16-bit prefix;
- site and content scope;
- endpoint ID;
- a verifiable site/endpoint binding reference;
- capabilities such as manifest-read, full-blob, range-read, or optional content;
- observed/advertised time and expiry;
- source of the observation;
- optional reputation/quality data explicitly marked non-authoritative.

Provider results are hints. A provider can lie, disappear, or return corrupt content. The requester verifies the full digest and size against the signed manifest.

Use expiry, deduplication, quotas, rate limits, and bounded result counts. Do not allow arbitrary peers to inject unlimited provider records.

### 9.3. Gossip

iroh-gossip may be useful for ephemeral update notices, invalidation hints, and topic-scoped announcements. It is not a durable content store and is not a substitute for endpoint bootstrap. Joining a topic requires an initial peer contact obtained through another mechanism.

Gossip payloads may carry bounded hints such as site identity, new manifest digest, sequence, and signature/binding references. Receiving gossip must not mark a manifest verified or overwrite local state. The client fetches the manifest independently and applies signature, authorization, and update-history checks.

Do not use gossip message order as the authoritative order of site updates.

Reference: https://docs.rs/iroh-gossip/latest/iroh_gossip/

### 9.4. Replace PEX semantics, not only the message name

V1 PEX exchanges IP/port peers through the existing peer protocol. V3 should exchange signed endpoint references or provider hints with expiry and capability scope.

An endpoint announcement must not be treated as a trusted site identity merely because it arrived over an encrypted connection. The announced endpoint still needs a valid site binding or application authorization.

## 🌈 10. Blob transfer and BLAKE3

### 10.1. Evaluate iroh-blobs

iroh-blobs is a strong candidate for v3 blob transfer because its protocol uses BLAKE3-verified streaming and supports complete blobs, ranges, and collections of blobs.

However, its documented protocol does not provide provider discovery and does not aim to support arbitrary hash algorithms. ZirohNeth must supply provider discovery and retain its own manifest/permission model.

Reference: https://docs.rs/iroh-blobs/latest/iroh_blobs/protocol/

**Version caution:** the currently surfaced docs.rs page for the latest iroh-blobs release warns that the latest line is not yet considered production quality and recommends an older stable line for production use. Do not cargo-add latest blindly. Select a mutually compatible, reviewed set of iroh crate versions, pin them, test them, and record the rationale in the implementation's Cargo manifest/lockfile.

### 10.2. Verify exact digest compatibility

The current v2 manifest records a flat BLAKE3-256 file digest. Before using iroh-blobs as the v3 storage/transfer backend, add test vectors proving that the byte identity used by the manifest matches the blob identity expected by the selected iroh-blobs release.

Do not assume that every internal Bao/chunk/tree representation is interchangeable with a flat BLAKE3 digest merely because both use BLAKE3. Define exact bytes, digest length, encoding, and conversion rules.

Required cross-language tests:

- empty file;
- one-byte file;
- small file;
- file crossing a BLAKE3 chunk boundary;
- file crossing the blob chunk-group boundary;
- large file;
- range transfer followed by full reconstruction;
- corrupt and truncated streams;
- identical bytes imported by Python and Rust implementations.

The Rust implementation should become the authoritative v3 implementation after independent test vectors establish compatibility. Do not maintain two drifting interpretations.

### 10.3. Optional files

The inspected v2 verifier currently accepts legacy SHA-512 optional-file metadata when it declares sha512-truncated-256. This is a v2 compatibility behavior, not a native v3 blob identity.

For v3:

- new required and optional files should use BLAKE3-256;
- v3 must not silently accept legacy SHA-512 metadata unless an explicit, versioned compatibility rule is approved;
- v2 SHA-512 optional content remains handled by the v2 verifier and legacy transport;
- before importing old bytes into a v3 BLAKE3 blob store, re-hash the actual bytes and publish an authorized v3 manifest entry;
- never relabel a SHA-512 digest as BLAKE3;
- provider availability hints never replace full digest verification.

### 10.4. Collections and file paths

Collections can reduce round trips for groups of small files, but a collection is a transport/storage optimization. The signed v3 manifest remains the authority for file paths, sizes, optional status, and ownership.

Never let provider-supplied collection order or paths define filesystem layout. Resolve each manifest-relative path under a trusted site root; write to temporary storage; verify digest and size; then atomically promote the verified file.

## 🌈 11. ZeroID-like identity and Ethereum-native certificates

### 11.1. Current blocker

The v2 root manifest can use EIP-712, but the inspected certificate verifier still uses Bitcoin message verification. The v2 signing function also refuses included manifests. This prevents a complete Ethereum-native user-content authorization path.

V3 must not reproduce this limitation.

### 11.2. Separate identity concepts

Define:

- **Site owner identity:** Ethereum identity authorized to publish the root site manifest.
- **User identity:** a user's Ethereum identity or another explicitly supported, separately versioned identity scheme.
- **Certificate issuer:** site owner or delegated authority that grants a scoped right to publish user content.
- **Transport endpoint identity:** iroh endpoint key used for network connectivity.
- **Application name/profile:** human-readable label resolved through the name system; not itself a cryptographic key.

A username such as alice@site is a label/claim. It is not proof of ownership until an authorized certificate or signed profile record binds it to an identity.

### 11.3. V3 certificate/capability record

Define a versioned certificate format signed using the v3 EIP-712 profile or another explicitly declared identity scheme.

At minimum, bind:

- certificate version;
- subject identity;
- issuer identity;
- user/authentication type;
- username/profile claim;
- site identity and relevant network context;
- allowed content path or namespace;
- capabilities such as profile-write, comment-write, follow-write;
- validity interval;
- serial/nonce;
- revocation reference or issuer sequence;
- signature scheme and signature.

Legacy cert_user_id may remain a presentation/lookup field for v1/v2 compatibility, but it must not be the sole v3 authorization evidence.

The v3 verifier must validate subject, issuer, path, capability, site scope, signature, validity, and revocation. A certificate for data/users/<user>/... must never authorize publishing the root site manifest.

### 11.4. Included and user manifests

V3 must support signed included/user manifests from the beginning.

Proposed flow:

1. The root manifest declares permitted user/content namespaces and accepted issuer/capability rules.
2. A user signs their own content manifest with their user identity.
3. The certificate/capability binds that user to the site and permitted path.
4. The included manifest binds its path, site, author, sequence, predecessor, and content digest.
5. The client verifies user authorship and site authorization independently.
6. File data is validated against its declared BLAKE3 digest.

Do not make the site owner's EOA sign every user's post. That would collapse user authorship into owner approval and undermine multi-user publishing.

### 11.5. ZeroID-like application behavior

Preserve the expected operations:

- create/select a user identity;
- publish a profile;
- request/renew a site certificate;
- authenticate to a site;
- revoke or replace an identity/certificate;
- display verified identity and authorization status.

The user-facing semantics may remain familiar, but the v3 security format must be Ethereum-native and transport-independent.

## 🌈 12. ZeroName-like name resolution

The inspected core has no functioning domain resolver: SiteManager.isDomain() and resolveDomain() are stubs returning False.

V3 needs a separately defined NameResolver service before claiming ZeroName parity.

A resolver record should bind normalized name, target site identity, namespace/chain context, owner identity, sequence/version, expiry/renewal policy, previous-record digest where applicable, and signature/registry proof.

The resolver must define normalization, Unicode/confusable handling, uniqueness/collisions, ownership transfer, expiry/renewal, revocation/recovery, caching/TTL, conflicting records, and offline behavior.

Candidate backends include a ZirohNeth signed-record registry, an Ethereum contract, ENS integration, or pluggable resolvers. These are different trust/cost models, not interchangeable defaults.

A name resolves to a site identity. Endpoint address lookup and provider discovery then find where the site can be reached. Do not make endpoint discovery the name service.

## 🌈 13. Social applications and user-content replication

### 13.1. Preserve application semantics

V1 social applications can rely on per-user content, included manifests, user_contents, cert_signers, and existing site permissions. V3 should preserve the semantic separation between site-owned content and user-authored content while replacing Bitcoin-bound certificate verification.

Social records should be signed by their author and authorized by site policy. Transport providers only carry data.

### 13.2. Suggested record classes

- **Profile:** author-owned signed state with an explicit update sequence.
- **Comment/post:** immutable signed record, optionally indexed by a site/application feed.
- **Follow/unfollow:** signed state transition or append-only event, with deterministic materialization.
- **Reaction:** signed event referencing a content digest.
- **Moderation action:** signed by an explicitly authorized moderator with scope and expiry.
- **Private message:** encrypted payload with recipient/key-management metadata; transport encryption alone is not end-to-end application encryption.

The application must specify ordering and deletion semantics. A mutable profile may use a per-author sequence chain. An append-only comment stream may use immutable event IDs. A follow list may be a signed state snapshot or signed event set. Do not impose one generic conflict rule on every data type.

### 13.3. Evaluate iroh-docs without confusing it with ZeroNet manifests

iroh-docs is a candidate for selected multi-writer application data. Its replicas contain entries identified by namespace, author, and key. Entry values refer to a 32-byte BLAKE3 hash of the content data plus size/timestamp metadata; the content body itself is stored/transferred separately. Entries are signed with a namespace secret and author key, and replicas synchronize using range-based set reconciliation.

Those semantics are not identical to a ZeroNet site manifest tree.

A particularly important security detail: an iroh-docs NamespaceSecret is a write capability. Do not hand the namespace secret to every user merely because the site supports multi-user content. Define the mapping from Ethereum identity/capabilities to iroh-docs authors and namespace permissions.

If evaluated for social/shared application data:

- bind the namespace to a site/application using an authenticated capability record;
- use separate author keys or a rigorously specified Ethereum-to-author mapping;
- define delegation and revocation;
- define deletion/tombstones and conflict handling;
- define retention and storage quotas;
- ensure a namespace capability cannot publish the site root manifest;
- keep the signed site manifest as authority for static site files.

References:
- https://docs.rs/iroh-docs/latest/iroh_docs/
- https://docs.rs/iroh-docs/latest/iroh_docs/struct.NamespaceSecret.html

## 🌈 14. SQL and multi-user synchronization

The current SQLite database should remain a local query/index/cache/materialized-view layer. Do not replicate SQLite database files or arbitrary SQL statements between untrusted peers.

For v3 multi-user writes, define an authenticated application operation log containing:

- operation ID;
- site/application scope;
- author identity;
- authorization capability;
- logical sequence or causal metadata;
- operation type and schema version;
- references to immutable BLAKE3 payload blobs;
- signature;
- deterministic conflict/reconciliation rule.

The receiver validates authorization and signature before applying an operation to the local materialized view.

Specify commutativity, concurrent updates, merge/reject rules, deletion/tombstones, replay/idempotency, quotas, rate limits, schema migration, and recovery after partial synchronization.

A comment append can be immutable events. A profile update can be last-writer-by-author-sequence. A permission change must not be treated as an eventually consistent text field. Application semantics determine the replication model.

iroh-docs may be suitable for an append/event-oriented data set after these semantics are defined. It is not a reason to replicate the legacy SQL database wholesale.

## 🌈 15. SiteClone semantics in v3

The current Site.clone is built around local file copying, clone metadata (cloned_from and clone_root), and re-signing copied manifests. The Ethereum signing restriction to the root manifest creates a concrete gap for clones containing included manifests.

V3 SiteClone must preserve the expected behavior:

1. User selects a source site and permitted clone root.
2. Client verifies the source root manifest and every included manifest/file it copies.
3. Client creates or imports a new site-owner identity for the clone.
4. Client copies or references verified content and creates a new v3 root manifest.
5. The new root manifest records provenance: source site identity, source manifest digest, and clone root.
6. Included manifests are either copied as immutable source-owned content and referenced without claiming ownership, or re-authored/re-signed by the clone owner or authorized users under the clone's rules.
7. The clone receives independent update history, permissions, endpoint bindings, and provider records.
8. The original site's content and identity remain unchanged.

Do not silently reuse the source owner's private key. Do not treat cloned_from as proof by itself; verify the source manifest digest and provenance record.

The current Bitcoin-specific address_index behavior must not be reused as an Ethereum key derivation rule. Clone key creation belongs to explicit wallet/key-management APIs.

Sharing immutable blobs between original and clone is desirable, but storage deduplication must not grant write authority over the original site.

## 🌈 16. Browser gateway and offline operation

Keep the local HTTP gateway concept. Browsers should not need to speak iroh directly.

~~~text
Browser
  |
  v
Local HTTP Gateway
  |
  v
Site Manager / Version Router
  |
  +-------------------------+--------------------------+
  |                         |                          |
  v                         v                          v
V1 ZeroNet/Python      V2 ZeroNet/Python         V3 Rust/iroh
  |                         |                          |
  +-------------------------+--------------------------+
                            |
                            v
           Shared Verified Storage / Local Cache
                            |
                            v
                         Browser
~~~

For an offline v3 site:

- serve locally verified files;
- expose the last known manifest verification/freshness state;
- do not queue implicit publication unless the user requested it;
- distinguish missing content from corrupt content and unavailable providers;
- resume provider discovery/transfer when connectivity returns.

The dashboard may display transport and verification diagnostics, but must not decide that a peer or manifest is trustworthy by reading an unverified transport, identity_scheme, or verified field from remote JSON.

Recommended dashboard diagnostics include connection mode, endpoint ID (with privacy controls), candidate/active provider counts, blob availability, transfer state, manifest verification, freshness, and conflict state. These are display data from the core, not security authorities.

## 🌈 17. Runtime, packaging, and platform strategy

A native Rust runtime is valuable only if it can be delivered and maintained reliably.

### 17.1. Build and dependency discipline

- Create a dedicated Rust workspace/crate for the v3 service.
- Pin a mutually compatible iroh crate set.
- Commit Cargo.lock for the application/service.
- Do not blindly track latest versions for production.
- Record the selected crate versions and why they were chosen.
- Add dependency auditing and license review.
- Use reproducible build practices where practical.
- Keep the IPC/API schema versioned independently of the Rust binary version.

### 17.2. Platform matrix

The project must explicitly test and package:

- Linux x86_64 and aarch64;
- Windows x86_64 and aarch64 where supported;
- macOS arm64 and x86_64 where supported;
- Android/Termux if this remains a supported runtime target.

Android/Termux is not a trivial checkbox. Rust target support, NDK/toolchain selection, native dependencies, filesystem permissions, background execution, battery constraints, and packaging must be tested. Do not promise parity until the v3 service runs, reconnects, transfers, and survives restarts on the target device.

### 17.3. Logs and observability

The Rust service should emit structured logs and metrics for:

- endpoint lifecycle;
- direct/relay connection state;
- discovery source and lookup outcomes;
- provider candidate counts;
- transfer progress and verification outcomes;
- manifest sequence/head conflicts;
- certificate/capability failures;
- IPC requests and errors;
- restart/recovery state.

Do not log private keys, secret namespace capabilities, private message plaintext, or sensitive user payloads. Correlate Python and Rust logs with request/site/transfer IDs while avoiding unnecessary user identity disclosure.

### 17.4. Performance claims require benchmarks

Do not claim that Rust/i roh automatically makes ZirohNeth faster. Benchmark v1/v2 Python behavior and v3 native behavior under equivalent conditions where comparison is meaningful.

Measure:

- CPU per concurrent peer/stream;
- resident memory at idle and under load;
- throughput for small and large blobs;
- time to first byte;
- end-to-end verified transfer time;
- connection establishment and reconnection;
- CPU for hashing/signature verification;
- cancellation/shutdown latency;
- queue depth/backpressure;
- behavior under slow, malicious, and disappearing providers.

The purpose is to validate resource efficiency and stability, not to create a misleading language shootout. Different transports and protocol semantics must be called out in results.

## 🌈 18. Security and abuse considerations

### 18.1. Identity confusion

**Risk:** equating an Ethereum site address with an iroh EndpointId permits endpoint substitution and incorrect trust assumptions.

**Mitigation:** endpoint key possession, signed endpoint bindings, scope-limited capabilities, expiry, sequence, and revocation.

### 18.2. Provider poisoning

**Risk:** a malicious peer advertises a file it does not have or returns incorrect content.

**Mitigation:** provider hints only; full digest and size verification; temporary files; atomic promotion after validation; failure accounting; bounded retries.

### 18.3. First-contact stale heads

**Risk:** a peer serves an old but correctly signed manifest to a client with no local checkpoint.

**Mitigation:** expose unverified_first_contact; choose an explicit optional transparency/checkpoint strategy; never label first contact globally latest.

### 18.4. Equivocation

**Risk:** owner signs different heads at the same sequence or conflicting predecessor.

**Mitigation:** preserve signed evidence, detect conflicting heads, persist local checkpoints, surface conflict state, and define owner-signed recovery.

### 18.5. Discovery poisoning and Sybil attacks

**Risk:** discovery returns only attacker-controlled endpoints or floods the client with fake providers.

**Mitigation:** multiple discovery providers, signed bindings, endpoint-diversity policies, quotas, rate limits, expiry, and safe fallback behavior. Reputation is only a hint.

### 18.6. Relay and metadata privacy

**Risk:** relays/discovery providers observe timing, addressing metadata, and traffic patterns even when payloads are encrypted.

**Mitigation:** minimize lookup disclosure, separate site/user identity from endpoint identity, allow self-hosted discovery/relays, document metadata exposure, and do not claim Tor-equivalent anonymity.

### 18.7. Certificate abuse

**Risk:** over-broad certificates allow users to write root manifests or another user's data.

**Mitigation:** path-scoped capabilities, site/application scope, explicit issuer policy, expiry, revocation, and negative authorization tests.

### 18.8. Multi-user conflicts

**Risk:** concurrent edits or replayed operations corrupt a materialized SQL/application view.

**Mitigation:** immutable operation IDs, signature/capability checks, deterministic application-specific reconciliation, idempotency, and recovery from verified operations.

### 18.9. Resource exhaustion

**Risk:** peers request huge blobs, many streams, expensive signatures, deep manifests, or unbounded discovery.

**Mitigation:** bounded message/blob sizes, bounded concurrency, quotas, timeouts, backpressure, rate limiting, cancellation, and limits on manifest nesting/path counts.

### 18.10. Filesystem safety

**Risk:** untrusted manifest paths or collection metadata escape the site directory or overwrite unrelated files.

**Mitigation:** strengthen relative-path validation; resolve paths under a trusted root; write temporary files; verify digest/size; atomically promote only after verification.

### 18.11. Key compromise and revocation

**Risk:** compromised site/user keys issue valid malicious signatures.

**Mitigation:** key-rotation records, recovery policy, issuer revocation, scoped delegates, audit evidence, and UI distinction between historical/current identities. Endpoint rotation must not silently rotate site ownership.

### 18.12. Rust/FFI/IPC and supply chain

**Risk:** a Rust sidecar, native binding, or larger dependency graph expands the build and update attack surface.

**Mitigation:** pin dependencies, commit Cargo.lock, audit unsafe/FFI surfaces, validate sidecar version/capabilities, restrict IPC permissions, fuzz protocol parsers, and test package/update signatures.

Rust memory safety is not protocol security. The parser, authorization checks, resource limits, and application semantics still require adversarial tests.

## 🌈 19. Testing and acceptance criteria

### 19.1. Version isolation

- v2-capable client continues to read and publish v1 through the existing legacy path.
- v2 sites continue to use the existing ZeroNet transport path.
- v3 sites use the native Rust/iroh path.
- invalid v3 never falls back to v2/v1.
- unknown content or transport versions fail closed.
- legacy eth: key selection and bare-key v1 behavior remain unchanged.
- opening a v2 site does not silently upgrade or re-route it to iroh.

### 19.2. V3 manifest/signature

- canonicalization creates deterministic cross-language digest vectors;
- EIP-712 signatures verify across independent implementations;
- invalid signer, wrong site address, changed protected field, wrong signature profile, and wrong network/domain context are rejected;
- included/user manifest signing works under scoped user capabilities;
- invalid/expired/revoked certificates are rejected;
- a user certificate cannot publish the site root;
- same-sequence conflicting manifests are detected;
- first contact is explicitly freshness-unverified.

### 19.3. Endpoint/discovery

- endpoint proves possession of the iroh key;
- endpoint binding verifies against the correct site identity;
- expired, revoked, wrong-site, wrong-ALPN, and over-scoped endpoint records are rejected;
- multiple endpoints may be bound to one site identity;
- endpoint rotation does not change content identity;
- discovery outage does not corrupt local site state;
- bogus provider hints do not bypass digest verification;
- self-hosted/configurable address lookup works;
- no single discovery provider is silently required by the protocol.

### 19.4. Blob transfer

- Python and Rust BLAKE3 vectors match;
- iroh blob identity conversion is exact;
- range and full transfers reconstruct identical bytes;
- corrupt/truncated streams are rejected;
- optional files preserve explicitly declared digest algorithms;
- v2 SHA-512 optional content is not silently relabeled as BLAKE3;
- content is not promoted to verified storage until digest and size checks pass;
- concurrent transfers obey quotas/backpressure and cancel cleanly.

### 19.5. Runtime and packaging

- sidecar starts, reports readiness, and shuts down cleanly;
- Python can recover from sidecar restart without corrupting site state;
- IPC rejects unauthorized local callers and oversized messages;
- version mismatch is handled explicitly;
- Linux/Windows/macOS build matrix is tested;
- Android/Termux is tested separately before claiming support;
- logs correlate requests without leaking secrets;
- performance/resource benchmarks are reproducible.

### 19.6. Application behavior

- ZeroID-style profiles and certificates work for v3.
- ZeroName resolution has explicit ownership and collision behavior.
- social profiles/posts/comments/follows preserve authorship and authorization.
- private messaging uses application-level encryption.
- SiteClone creates an independently owned clone and preserves source provenance.
- SQLite can be rebuilt from verified application data.
- multi-user concurrent operations converge according to documented application rules.
- offline browsing works for locally available verified content.
- dashboard labels derive from core verification states, never from untrusted remote claims.

### 19.7. Transition and migration

- a v2-to-v3 transition binds the exact final v2 manifest digest and sequence;
- invalid or mismatched transition signatures fail;
- v2 remains readable after v3 publication;
- clients detect conflicting transition/head records;
- no automatic conversion occurs on open;
- existing Bitcoin-to-Ethereum migration behavior remains intact;
- historical Bitcoin identities cannot publish after terminal migration;
- first-contact migration/transition status is not presented as globally proven.

## 🌈 20. Implementation sequence

Each phase should be independently reviewable and must not change v1/v2 semantics.

### Phase A — Freeze the version and compatibility contracts

- Confirm that iroh transport is v3-only.
- Document v1/v2 manifest and migration test vectors.
- Define v3 manifest fields and signature domain separation.
- Define the v2-to-v3 VersionTransition record.
- Add tests proving v2 does not activate iroh.

### Phase B — Rust service foundation

- Create the Rust workspace/service.
- Pin a compatible iroh crate set.
- Establish endpoint lifecycle and service supervision.
- Define versioned local IPC.
- Implement structured logs, metrics, cancellation, and health checks.
- Add a platform build matrix before implementing all application features.

### Phase C — Identity and authorization

- Define v3 identity-provider interfaces.
- Implement Ethereum endpoint bindings.
- Implement certificate/capability format and verification.
- Add user/included-manifest signing.
- Add key rotation, revocation, expiry, and scope tests.

### Phase D — V3 transport and discovery

- Define ALPN and message envelope.
- Implement endpoint address lookup abstraction.
- Implement provider index/client and anti-spam limits.
- Implement direct/relay connection management.
- Implement provider-oriented transfer scheduling.
- Add gossip only for non-authoritative update hints where useful.

### Phase E — Manifest and blobs

- Implement v3 manifest parsing/signing/verification.
- Verify exact BLAKE3 compatibility with chosen blob crate/version.
- Implement manifest retrieval and update subscriptions.
- Implement complete/range blob transfer and atomic promotion.
- Implement local checkpoints, equivocation detection, and offline cache behavior.

### Phase F — Applications

- Adapt ZeroID-like profile/certificate workflows.
- Implement ZeroName via a separately approved resolver backend.
- Port SiteClone semantics and included manifests.
- Define social operation models.
- Add multi-user synchronization for authenticated application operations.
- Evaluate iroh-docs only for data types whose semantics fit its replica model.

### Phase G — Dashboard and v3 rollout

- Expose typed verification, freshness, endpoint, provider, and transfer states.
- Preserve v1/v2 UI behavior.
- Add end-to-end tests across all three content generations.
- Test upgrades, restart recovery, and v2-to-v3 transition.
- Document privacy and infrastructure assumptions before public release.

## 🌈 21. Open decisions

Resolve these before production rollout:

1. **Rust integration:** sidecar with versioned local IPC versus PyO3/native binding. The initial recommendation is a sidecar.
2. **Platform support:** exact Linux, Windows, macOS, and Android/Termux support matrix.
3. **Discovery defaults:** which address lookup providers ship enabled, how they can be replaced, and provider diversity requirements.
4. **Provider index:** record format, lookup privacy, DHT keying, expiry, anti-spam, and whether gossip carries only head hints.
5. **Blob identity:** exact compatibility between current Python flat BLAKE3 manifest hashes and selected iroh-blobs version.
6. **Crate release policy:** which mutually compatible iroh/iroh-blobs/iroh-gossip/iroh-docs releases are suitable for production; pin and document them.
7. **V3 certificate model:** EIP-712 schema, scopes, delegation, revocation, expiry, and user key recovery.
8. **ZeroName backend:** signed P2P registry, Ethereum contract, ENS integration, or pluggable resolver.
9. **Social data model:** per-application event/CRDT strategy and deletion semantics.
10. **SQL synchronization:** authenticated operations and materialized views, not raw SQLite replication.
11. **Global freshness:** trust-on-first-use, transparency log, optional on-chain checkpoints, or another explicit model.
12. **Multisig:** whether v3 root/included manifests need multisig or delegated publishing in the first release.
13. **Privacy/anonymity:** what v3 promises beyond encrypted transport and whether another privacy transport is required.
14. **Wire serialization:** deterministic binary format, schema evolution, and fuzzing strategy.
15. **Endpoint key custody:** persistent versus ephemeral identities, backup, rotation, and recovery.
16. **Python/Rust ownership:** which application logic stays in Python long-term and which v3 security decisions must have one authoritative Rust implementation.

These decisions do not block the version separation. They must not be silently resolved by implementation convenience.

## 🌈 22. Decision summary

| Question | Recommendation |
|---|---|
| Does iroh replace v1 transport? | No |
| Does iroh replace v2 transport? | No |
| Which generation introduces native iroh? | Content v3 only |
| Should v2 sites be silently upgraded? | Never |
| Should v3 networking use the Python ZeroNet Peer runtime? | No |
| Should v3 network runtime be Rust-native? | Yes |
| Should all application code be rewritten in Rust immediately? | No |
| Initial Python/Rust boundary | Supervised Rust sidecar with versioned local IPC |
| Is Rust guaranteed faster? | No; benchmark the actual workload |
| Is Python production-capable? | Yes; retain it where it fits |
| Is iroh EndpointId the Ethereum site identity? | Never |
| Is provider discovery proof of content? | No |
| Is iroh-gossip durable site state? | No |
| Is iroh-docs a drop-in ZeroNet manifest replacement? | No |
| Should SQLite files/arbitrary SQL be replicated? | No |
| Is Ethereum-native ZeroID/certification required for v3 parity? | Yes |
| Is ZeroName implemented in the inspected core? | No; current resolver methods are stubs |
| Does encrypted iroh transport provide Tor anonymity? | No |
| May v3 validation fall back to v2/v1? | Never |

## 🌈 23. Upstream references

Iroh APIs and crate release maturity evolve. These links describe the upstream concepts reviewed for this RFC; implementation must select and pin actual compatible releases rather than relying on latest.

- Iroh crate and endpoint API: https://docs.rs/iroh/latest/iroh/
- Iroh endpoint structure: https://docs.rs/iroh/latest/iroh/endpoint/struct.Endpoint.html
- Iroh discovery/address lookup model: https://docs.rs/iroh-net/latest/iroh_net/discovery/index.html
- Iroh blobs protocol, BLAKE3 verified streams, ranges, collections, and discovery non-goal: https://docs.rs/iroh-blobs/latest/iroh_blobs/protocol/
- Iroh blobs crate and release maturity notice: https://docs.rs/iroh-blobs/latest/iroh_blobs/
- Iroh gossip: https://docs.rs/iroh-gossip/latest/iroh_gossip/
- Iroh docs replica model: https://docs.rs/iroh-docs/latest/iroh_docs/
- Iroh docs namespace write capability: https://docs.rs/iroh-docs/latest/iroh_docs/struct.NamespaceSecret.html
- RFC 8785 JSON Canonicalization Scheme: https://www.rfc-editor.org/rfc/rfc8785
- Rust ownership and borrowing: https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html
- Rust fearlessness/concurrency concepts: https://doc.rust-lang.org/book/ch16-00-concurrency.html

## 🌈 24. Repository files reviewed

Core files:

- src/Content/ContentManager.py
- src/Crypt/CryptEthereum.py
- src/Crypt/CryptMigration.py
- src/Peer/Peer.py
- src/Peer/PeerHashfield.py
- src/Site/Site.py
- src/Site/SiteAnnouncer.py
- src/Site/SiteManager.py
- src/Site/SiteStorage.py
- src/Worker/WorkerManager.py
- src/Db/Db.py
- requirements.txt
- README.md

Related dashboard file:

- Floflis/ZirohNeth-dashboard/README.md

## 🌈 25. Review checklist

- [ ] Confirm iroh transport is v3-only.
- [ ] Confirm v1 and v2 retain their current ZeroNet transport.
- [ ] Confirm the explicit v2-to-v3 transition and no automatic migration.
- [ ] Confirm endpoint identity and Ethereum site identity remain separate.
- [ ] Confirm Rust sidecar and IPC direction.
- [ ] Confirm the v3 manifest/signature profile and domain separation.
- [ ] Confirm included/user-manifest and ZeroID certificate semantics.
- [ ] Confirm ZeroName resolver direction.
- [ ] Confirm endpoint discovery/provider-index separation.
- [ ] Confirm BLAKE3/iroh-blobs digest test requirements.
- [ ] Confirm social and SQL replication boundaries.
- [ ] Confirm SiteClone provenance and independent ownership.
- [ ] Confirm first-contact freshness and equivocation policy.
- [ ] Confirm Android/Termux and desktop packaging strategy.
- [ ] Confirm the benchmark plan and performance claims.
- [ ] Add implementation milestones only after the relevant contracts are approved.

---

**End of RFC-0001.**

This is an architectural proposal, not an implementation report. It intentionally makes no claim that the v3 iroh transport, Rust service, Ethereum-native certificates, ZeroName resolver, or application replication mechanisms are implemented.
