# ZirohNeth Roadmap

> Status: planning document. A roadmap item is not evidence of implementation; completed work must be linked to a PR/commit and its test evidence.

## Direction

Maintain the existing ZeroNet Conservancy codebase while evolving ZirohNeth toward a decentralized web stack with modern peer-to-peer connectivity and verifiable integration boundaries. Preserve compatibility and make the transition incremental.

## Workstreams

### 1. Establish the current baseline
- [ ] Inventory the inherited ZeroNet/Conservancy modules, runtime assumptions, dependencies, and test coverage.
- [ ] Document the supported deployment platforms and known operational limitations.
- [ ] Define compatibility and regression tests for existing ZeroNet behavior.

### 2. Rust-native foundation
- [ ] Integrate the maintained Rust components through explicit, versioned interfaces.
- [ ] Keep the Python-facing application and Rust-native services separated by documented process/API contracts.
- [ ] Record ownership, lifecycle, error handling, and upgrade behavior for every native service.

### 3. Python runtime strategy
- [ ] Evaluate a dual-runtime model: CPython for compatibility and RustPython for eligible scripts.
- [ ] Define per-script runtime selection and a capability/compatibility manifest.
- [ ] Port or implement missing RustPython modules only when required by a concrete ZirohNeth workload.
- [ ] Keep CPython as the compatibility fallback until parity is demonstrated; do not silently change script runtimes.

### 4. Peer-to-peer networking
- [ ] Define the networking architecture and trust boundaries before replacing existing transports.
- [ ] Integrate and validate selected Rust-native networking components behind stable interfaces.
- [ ] Document peer discovery, connection lifecycle, persistence, and failure recovery.
- [ ] Keep optional transports and privacy layers explicit; do not introduce unrequested dependencies.

### 5. Web3 and decentralized coordination
- [ ] Specify which functions genuinely require blockchain coordination.
- [ ] Define threat models, key management, and trust assumptions before implementing on-chain components.
- [ ] Prototype integrations independently and document their operational costs and failure modes.

### 6. Release quality
- [ ] Add reproducible build and test workflows for supported targets.
- [ ] Track platform-specific compatibility separately instead of assuming all BSD, Linux, or alternative-OS targets share an architecture.
- [ ] Publish migration notes and a feature/status matrix for each release.

## Completion policy

A task is complete only when its implementation is merged, the relevant tests pass, and this roadmap links to the PR/commit and evidence. Keep unfinished work checked open; do not mark aspirational capabilities as shipped.
