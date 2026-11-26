# 🌈 ZeroCompanies: Aragon OSx on Plasmium and decentralized organization infrastructure

> **Status:** architecture proposal and implementation roadmap  
> **Scope:** ZirohNeth / Floflis integration direction  
> **Non-goal of this document:** claiming that contracts have already been forked, deployed, audited, or that decentralized backend adapters are implemented.

## 🌈 Executive vision

**ZeroCompanies** is the organization and DAO layer of ZirohNeth: a place where communities, cooperatives, teams, projects, and commercial or non-commercial organizations can create an on-chain identity, govern shared resources, coordinate members, publish proposals, and manage treasuries.

The project should fork and adapt the **current Aragon OSx generation**, rather than revive Aragon 1 or build a new DAO framework from scratch.

The intended direction is:

- Fork and maintain the relevant Aragon OSx smart-contract code in the Floflis ecosystem.
- Deploy the adapted OSx protocol stack to **Plasmium**, the project's OP Stack chain.
- Integrate the Aragon application experience into ZirohNeth, with a branded and maintainable application fork.
- Make the frontend distributable through IPFS and discoverable through ZirohNeth/ENS-compatible naming.
- Replace assumptions about one always-on Aragon backend with interchangeable, independently operated indexing, API, storage, compute, and RPC providers.
- Keep smart contracts as the authoritative source of organization state and permissions.
- Preserve direct wallet-to-contract interaction so essential DAO administration does not depend on the official web application or any one backend.

This is an architectural direction, not a claim that every component is already available or decentralized.

## 🌈 Naming and product boundaries

| Name | Responsibility |
|---|---|
| **ZirohNeth** | The wider decentralized network, runtime, identity, discovery, storage and application ecosystem |
| **ZeroCompanies** | Organization discovery, creation, profiles and DAO experience |
| **ZeroMembers** | Member identity, membership and participation surfaces |
| **ZeroGovernance** | Proposals, voting, permissions and execution UX |
| **ZeroTreasury** | Treasury visibility, asset management and payment workflows |
| **Aragon OSx fork** | Smart-contract framework and plugin architecture underneath ZeroCompanies |

These are product/module boundaries. They do not require one smart contract per product name. Prefer Aragon's existing DAO and plugin model where it fits.

A ZeroCompany is an on-chain organization, not automatically a legally incorporated company. The UI and documentation must distinguish a DAO from a registered legal entity and must not imply that on-chain membership or token ownership creates legal status by itself.

## 🌈 Why Aragon OSx

Use the current OSx architecture, not legacy Aragon Client / Aragon 1.

OSx provides a deliberately small DAO core and a modular framework:

- DAO contract: organization identity, treasury, execution and permission state.
- Permission system: authorization over DAO and plugin actions.
- Plugins: optional governance, membership, treasury and other capabilities.
- Framework contracts: DAO and plugin factories/registries, plugin setup processor and related infrastructure.
- Versioned plugin repositories and installation/update lifecycle.

The fork should begin from the upstream OSx repository and a pinned, reviewed release/commit. Do not silently track a moving upstream branch in production.

Upstream references:
- https://github.com/aragon/osx
- https://docs.aragon.org/
- https://docs.aragon.org/deployment/protocol-factory
- https://docs.aragon.org/framework/plugins
- https://docs.aragon.org/core/dao

### 🌈 Fork strategy and upstream maintenance

Create Floflis-maintained repositories for the components that are actually needed. Candidate repository boundaries:

1. **OSx contracts fork**: fork of `aragon/osx`, including Solidity contracts, Foundry configuration, tests, deployment scripts and required submodules.
2. **Aragon App fork**: fork of `aragon/app`, adapted to ZirohNeth identity, Plasmium configuration, IPFS distribution and provider selection.
3. **App backend/indexer integration**: initially a separate adapter/integration layer. Fork `aragon/app-backend` only if code-level compatibility or product changes justify maintaining the fork.
4. **ZeroCompanies plugins**: separate plugin repositories or a clearly isolated package/workspace, depending on the upstream plugin template and deployment workflow.

Repository names are proposals, not existing repositories. Confirm naming, ownership, upstream license obligations and maintenance capacity before creating them.

Maintain an explicit upstream remote and record:
- upstream repository URL;
- pinned upstream release/tag and commit SHA;
- local patch set and rationale;
- license and notices;
- upgrade/rebase procedure;
- security advisories and audit history.

Do not remove upstream copyright, license notices, attribution or audit references. Audit the license of every forked repository and dependency independently before redistribution or deployment. The Aragon app backend repository currently identifies itself as AGPL-3.0; do not assume every Aragon component has the same license.

## 🌈 Plasmium deployment target

Plasmium is the intended home chain for the ZeroCompanies OSx deployment. It is the project's OP Stack chain, so treat it as an EVM chain but do not assume that every upstream Aragon deployment script, ENS dependency, address registry, explorer integration or RPC assumption works unchanged.

### 🌈 Required deployment inventory

The protocol deployment must account for the complete OSx framework, not just the DAO implementation:

- DAO implementation and required proxies/beacons/factories.
- DAO factory and DAO registry.
- Plugin repository factory and plugin registry.
- Plugin setup processor.
- Core plugin repositories and their setup contracts.
- Permission wiring and initial framework governance/management authority.
- ENS-compatible naming components or an explicitly selected alternative naming/registry strategy.
- Any required helper, resolver, registrar, token or external dependency used by the pinned OSx release.
- Deployment artifacts: addresses, ABIs, bytecode/build metadata and verified source references.

Use the upstream **Protocol Factory** deployment workflow as the starting point. The protocol factory exists to bring up the complete OSx framework on a new EVM chain, including core contracts, naming, Management DAO and core plugin repositories. Adapt and test that workflow for Plasmium instead of deploying a partial collection of contracts by hand.

Reference: https://docs.aragon.org/deployment/protocol-factory

### 🌈 Chain configuration

Add a single canonical Plasmium chain configuration consumed by the app, SDK, deployment tooling, indexers and tests. It should include, once confirmed from the actual chain configuration:

- chain ID;
- chain name and native currency;
- public and optional operator RPC URLs;
- WebSocket RPC URLs where supported;
- explorer URL and verification API details;
- finality / confirmation policy;
- contract deployment addresses and deployment block numbers;
- ENS or alternative naming configuration;
- supported wallet/network metadata.

**Do not invent or hardcode a chain ID, RPC URL, explorer URL, or contract address.** Obtain these from the actual Plasmium OP Stack deployment and publish them through reviewed configuration. Keep private operator endpoints and credentials out of source control.

### 🌈 Deployment safety

- Use deterministic, reproducible deployment scripts where possible.
- Separate local development, testnet/staging and production configuration.
- Dry-run and simulate every deployment/upgrade before broadcasting.
- Verify deployed source code and publish deployment manifests.
- Record transaction hashes, deployer/admin addresses, implementation addresses, proxy relationships and initialization parameters.
- Test all permission relationships after deployment.
- Use a documented multisig/governance process for production administration; do not leave a personal hot wallet as an undocumented permanent super-admin.
- Never deploy production contracts merely because a build succeeds.
- Require independent review and security testing before handling meaningful treasury assets.

## 🌈 Application architecture

The ZeroCompanies experience should reuse and adapt the current Aragon App and governance UI components where practical, while remaining a ZirohNeth-owned product surface.

The current Aragon App repository is a modern monorepo with a Next.js application and shared packages. The Aragon app backend is a separate service family that includes API, indexer and rates/admin services and documents a MongoDB dependency. This separation is useful: the UI, contracts and data services should not be treated as one indivisible server.

Upstream references:
- https://github.com/aragon/app
- https://github.com/aragon/app-backend

### 🌈 IPFS-first frontend distribution

Target a frontend release that can be built, content-addressed and served from IPFS:

- Build static assets and publish a versioned release to IPFS.
- Record and verify the resulting CID.
- Publish a signed release manifest containing the source commit, build metadata, CID and integrity hashes.
- Expose the selected release through a ZirohNeth/ENS-compatible name or content record.
- Keep older releases retrievable for rollback and independent verification.
- Allow users to pin, mirror or serve the frontend themselves.

The current Next.js app may rely on server-side rendering, route handlers, middleware, image optimization or runtime APIs. **Do not assume it can be deployed as a static IPFS site unchanged.** Audit every route and runtime dependency. Move server-dependent features behind explicit provider interfaces or replace them with browser-side/on-chain capabilities before enabling static export. No hidden dependency on a single Vercel deployment should remain in the core user journey.

Vercel may remain a convenient preview or optional mirror, but it must not be a protocol requirement.

### 🌈 Graceful degradation

The frontend should distinguish:
- **Core on-chain actions:** wallet + Plasmium RPC + contracts.
- **Enhanced indexed views:** indexer/query provider.
- **Optional enrichment:** token prices, avatars, metadata previews and analytics.
- **Publishing/discovery:** IPFS and ZirohNeth discovery mechanisms.

If an indexer, metadata gateway, price service or official API is unavailable, the application should explain which view is degraded and preserve direct access to essential on-chain actions.

## 🌈 Decentralized backend and provider architecture

Do not replace one mandatory centralized backend with another mandatory vendor. Introduce explicit provider interfaces and permit multiple independent implementations.

Suggested logical interfaces:

| Interface | Responsibility | Candidate implementations |
|---|---|---|
| `RpcProvider` | Read/write blockchain access | Multiple independent Plasmium RPC operators; self-hosted OP Stack nodes |
| `IndexerProvider` | DAO/plugin/proposal/event indexing | The Graph Network; independently operated Graph Nodes; direct RPC log scanner |
| `QueryProvider` | Normalized organization and governance queries | GraphQL/subgraph adapters; independently hosted APIs |
| `MetadataProvider` | DAO profile JSON, logos and documents | IPFS, ZirohNeth storage, user-operated gateways |
| `StorageProvider` | Durable content-addressed files | IPFS pinning providers, self-hosted Kubo or compatible nodes |
| `ComputeProvider` | Verifiable or outsourced compute | EigenCloud where appropriate; Cartesi for application-specific verifiable computation |
| `JobProvider` | Parallelizable/off-chain tasks | Golem providers or other worker networks |
| `PriceProvider` | Optional token-price data | Multiple independent sources, clearly marked as non-authoritative |

These are adapters, not a requirement to use every network. The first implementation should prioritize RPC, indexing, metadata and storage. Add distributed compute only for concrete workloads.

### 🌈 The Graph

The Graph is the leading candidate for decentralized DAO event indexing and query delivery.

- Define and version subgraphs for OSx DAO creation, plugin installation, permissions, proposals, votes, execution and relevant ZeroCompanies events.
- Deploy and test the subgraphs against Plasmium's actual chain configuration.
- Verify that the required chain is supported by the intended Graph Network/indexing deployment path before depending on it.
- Publish schema, mappings, deployment instructions and deterministic fixtures.
- Support independent Graph Node deployments and a direct-RPC fallback.
- Do not equate a successful GraphQL response with canonical truth: verify high-value actions against the Plasmium chain and handle reorgs/finality.

A decentralized indexer network still depends on RPC access, subgraph availability and query infrastructure. Preserve alternate query paths.

### 🌈 EigenCloud

Evaluate EigenCloud for workloads that benefit from verifiable or economically secured computation, rather than using it as a generic replacement for every API.

Potential future workloads:
- independently verifiable batch calculations;
- off-chain policy evaluation where the result can be checked;
- compute-heavy organization analytics;
- selected automation whose outputs are committed or attested on-chain.

Keep ordinary reads and simple application APIs out of this path unless there is a measurable reason.

### 🌈 Golem Network

Evaluate Golem for independent, parallelizable jobs:
- metadata processing;
- document/media transformations;
- optional analytics and batch reports;
- reproducible computation that does not require a continuously available authoritative API.

Do not assume a Golem task provider is a durable database, always-on API or trusted indexer. Define job inputs/outputs, timeouts, retries, result validation, persistence and provider failure handling at the application layer.

### 🌈 Cartesi

Evaluate Cartesi when a ZeroCompanies feature needs a Linux/RISC-V execution environment, application-specific rollup logic or verifiable off-chain computation.

It is not the default backend for the first release. A Cartesi integration would introduce its own deployment, data availability, dispute and operational model and should be justified by a specific feature.

### 🌈 Backend independence and failover

- Allow more than one provider for each critical read capability.
- Configure provider priority, health checks, timeouts, rate limits and retry policy.
- Detect stale indexers by comparing indexed block height/hash with independent RPC sources.
- Treat chain reorganizations and finality explicitly.
- Keep provider credentials local or in deployment secrets, never in browser bundles or committed configuration.
- Make provider selection user/operator configurable.
- Expose provider identity and freshness in diagnostics.
- Do not let an indexer or metadata provider authorize transactions. Wallet signatures and contract permissions remain authoritative.
- Never silently accept conflicting indexed state; surface disagreement and fall back to direct chain verification.

## 🌈 RPC is unavoidable, but a single RPC is not

Every indexer and frontend needs blockchain access. The objective is not to eliminate RPC; it is to avoid a single RPC operator becoming a control point.

Implement a `RpcProvider` abstraction with:
- multiple independently operated Plasmium endpoints;
- HTTP JSON-RPC and WebSocket support where available;
- chain ID validation at connection time;
- endpoint health and latency tracking;
- block-height and block-hash freshness checks;
- retry and failover rules appropriate to read versus write operations;
- configurable confirmation/finality depth;
- explicit handling for rate limits, timeouts and malformed responses.

For writes, do not blindly broadcast a transaction to many providers and imply that this creates multiple independent executions. Use a selected endpoint, track the transaction hash, and verify inclusion and finality through independent read endpoints. Wallets may supply their own RPC, subject to chain ID and endpoint validation.

The app should support user-provided RPC URLs and self-hosted nodes. Public endpoints are convenience options, not trust anchors.

## 🌈 Data and authority model

Use the following source-of-truth hierarchy:

1. **Plasmium smart contracts:** DAO ownership, permissions, treasury balances, plugin installation and executed governance state.
2. **Signed/content-addressed metadata:** human-readable organization profiles, documents, logos and release manifests.
3. **Indexers:** derived, rebuildable query projections of on-chain events.
4. **Caches and analytics:** disposable performance/enrichment data.

An indexer database must never become the only copy of DAO state. It should be possible to rebuild its projection from chain history, subject to available archive/log access and the documented starting block.

Use EIP-4824-compatible DAO metadata where supported by the pinned OSx version, and keep the metadata document retrievable independently of the official app. Confirm exact on-chain metadata behavior and URI handling against the pinned contract implementation.

## 🌈 ZeroCompanies product capabilities

Initial product capabilities should include:

- Create a ZeroCompany/DAO on Plasmium.
- Choose an initial governance model and install the required plugin(s).
- Set organization name, description, avatar and external/content-addressed links.
- Discover organizations through indexed and peer-distributed catalogues.
- View members, installed plugins, proposals, votes, execution history and treasury.
- Connect a wallet and interact directly with contracts.
- Publish and retrieve metadata through IPFS-compatible providers.
- Display the chain and provider currently being used.

Future capabilities may include:
- ZeroMembers identity and membership profiles.
- ZeroGovernance UX and additional governance plugins.
- ZeroTreasury payments, budgeting and asset management.
- ZirohNeth-native discovery and notifications.
- Optional confidential voting or other advanced governance, only after evaluating the exact cryptographic and contract requirements.

Do not imply that every capability is supplied by OSx out of the box. Membership, voting and treasury workflows depend on installed plugins and their permissions.

## 🌈 ZirohNeth integration

ZeroCompanies should be an application and protocol capability inside ZirohNeth, not an isolated centralized SaaS.

Integration points:
- ZirohNeth identity and wallet discovery.
- ENS-compatible or ZirohNeth-native organization naming.
- IPFS content addressing and publication.
- Peer discovery for organization profiles and signed release manifests.
- Local caching and offline access to previously retrieved metadata.
- Optional P2P notifications and activity feeds.
- Native/browser app integration without requiring the official hosted Aragon frontend.

Keep the boundaries clean: ZirohNeth handles network/runtime concerns; OSx handles DAO permissions and execution; ZeroCompanies presents the organization experience.

## 🌈 Security, trust and legal requirements

- Treat every RPC, indexer, gateway, worker, metadata URI and provider response as untrusted input.
- Validate chain IDs, contract addresses, ABI versions and deployment manifests.
- Verify metadata hashes/CIDs and signed release manifests.
- Sanitize user-generated names, descriptions, links, SVGs and media before rendering.
- Apply origin isolation and restrictive browser security policies to externally hosted content.
- Do not expose private keys, API secrets or operator credentials in frontend bundles.
- Use explicit permission reviews for every plugin and setup contract.
- Test upgrade and uninstall flows, permission revocation, malicious plugin behavior and reentrancy-sensitive execution paths.
- Obtain independent audits for the fork's modifications and custom plugins; upstream audits do not automatically cover local changes or a new chain deployment.
- Clearly disclose RPC/indexer/provider trust assumptions.
- Distinguish a DAO from a legally incorporated entity and provide jurisdiction-specific legal review before presenting regulated financial or corporate functionality.

## 🌈 Phased implementation roadmap

### Phase 0 — Upstream and chain audit
- Pin the current OSx release and commit.
- Audit upstream licenses, dependencies, deployment scripts and security reports.
- Inspect Plasmium chain ID, RPC, explorer, finality and OP Stack configuration.
- Identify ENS/naming requirements and all external contract dependencies.
- Audit current Aragon App routes for static/IPFS compatibility.
- Audit the current app-backend/indexer and its database/API assumptions.

**Exit criteria:** reviewed source baseline, license inventory, Plasmium deployment checklist and documented gaps.

### Phase 1 — OSx fork and Plasmium protocol deployment
- Create the Floflis OSx fork.
- Preserve upstream history and notices.
- Adapt deployment configuration and Protocol Factory workflow.
- Deploy to local OP Stack devnet and Plasmium test environment first.
- Publish verified artifacts and a machine-readable deployment manifest.
- Test DAO creation, core plugins, permission wiring, proposal lifecycle and treasury execution.

**Exit criteria:** reproducible test deployment and passing integration tests. No production treasury use yet.

### Phase 2 — ZeroCompanies application
- Fork/adapt the current Aragon App.
- Add Plasmium chain configuration and wallet/network UX.
- Brand the organization experience as ZeroCompanies.
- Implement organization creation, discovery and core governance views.
- Add direct contract interaction paths.
- Document any upstream components intentionally not forked.

**Exit criteria:** users can create and administer a test DAO without relying on a single proprietary backend.

### Phase 3 — IPFS frontend distribution
- Remove or isolate runtime features that prevent static distribution.
- Build static assets and publish to IPFS.
- Sign and publish release manifests with source commit and CID.
- Add independent pinning/mirroring and rollback documentation.
- Keep conventional hosting optional.

**Exit criteria:** a clean browser can load a verified release through an IPFS gateway or local node, and core wallet interactions work.

### Phase 4 — Decentralized indexing and RPC
- Define OSx/ZeroCompanies subgraphs.
- Validate The Graph Network support for Plasmium; operate independent Graph Nodes as needed.
- Add direct RPC log-scanning fallback.
- Implement multi-provider RPC selection and freshness checks.
- Make indexed data rebuildable and expose provider diagnostics.

**Exit criteria:** DAO discovery and governance history continue to work when one indexer or RPC provider is unavailable.

### Phase 5 — Distributed services and native integration
- Add IPFS/ZirohNeth metadata providers.
- Evaluate EigenCloud, Golem and Cartesi against specific workloads.
- Integrate ZirohNeth identity, discovery, local cache and notifications.
- Add ZeroMembers, ZeroGovernance and ZeroTreasury capabilities incrementally.

**Exit criteria:** each distributed service has a documented failure model, validation method and independent fallback.

### Phase 6 — Production readiness
- Complete independent contract and application security reviews.
- Verify deployment manifests and published frontend builds.
- Exercise provider outages, stale indexers, reorgs and malicious metadata.
- Document governance/admin recovery and upgrade procedures.
- Publish operational runbooks and user-facing trust disclosures.

**Exit criteria:** production launch approved only after security, operational and governance checks pass.

## 🌈 Initial acceptance criteria for this architecture PR

- [ ] The ZeroCompanies name and product scope are documented.
- [ ] The current Aragon OSx generation is the selected contract foundation; Aragon 1 is not the target.
- [ ] Fork boundaries and upstream maintenance policy are documented.
- [ ] Plasmium is the target deployment chain, with unknown chain parameters explicitly left for verification.
- [ ] The Protocol Factory workflow is identified for full-stack deployment.
- [ ] The app is planned for IPFS distribution without assuming the current Next.js app is already static-compatible.
- [ ] RPC, indexing, metadata, storage and compute have separate provider interfaces.
- [ ] The Graph, EigenCloud, Golem and Cartesi have distinct, non-interchangeable roles.
- [ ] Direct wallet-to-contract access remains possible without the official app backend.
- [ ] Smart contracts are authoritative; indexers are rebuildable projections.
- [ ] Security, licensing, legal and production-readiness requirements are explicit.
- [ ] This PR is understood as architecture/documentation only, not an implementation or deployment claim.

## 🌈 Upstream references

- Aragon OSx contracts: https://github.com/aragon/osx
- Aragon App: https://github.com/aragon/app
- Aragon App backend: https://github.com/aragon/app-backend
- Aragon OSx developer documentation: https://docs.aragon.org/
- Protocol Factory: https://docs.aragon.org/deployment/protocol-factory
- DAO core: https://docs.aragon.org/core/dao
- Plugin model: https://docs.aragon.org/framework/plugins
- The Graph: https://thegraph.com/docs/
- EigenCloud: https://docs.eigencloud.xyz/
- Golem Network: https://docs.golem.network/
- Cartesi: https://docs.cartesi.io/
- IPFS: https://docs.ipfs.tech/
- OP Stack: https://docs.optimism.io/

---

**Architecture principle:** ZeroCompanies must remain usable and governable through the contracts even if the official ZirohNeth frontend, one RPC operator, one indexer, one IPFS gateway or one compute provider disappears.
