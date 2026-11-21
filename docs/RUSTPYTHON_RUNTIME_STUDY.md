# 🌈 RustPython as a Potential ZirohNeth Runtime

**Research snapshot:** 2026-11-18  
**Status:** Architectural study only. No runtime replacement or compatibility claim is made by this document.

## 🌈 Executive summary

[**RustPython**](https://github.com/RustPython/RustPython) is the closest match to the idea of a Python interpreter implemented in Rust. Unlike CPython, which is implemented primarily in C, RustPython aims to provide a Python 3 environment written entirely in Rust. It can be built as a native application, embedded in Rust applications, and compiled to WebAssembly.

That makes it an attractive candidate for a future ZirohNeth engine that could target Linux and Windows from a shared Rust codebase. However, **RustPython should not currently be treated as a drop-in replacement for CPython**. Its own project documentation warns that it is still in development, is not production-ready for fault-intolerant use, and has incomplete standard-library coverage. Its compatibility with CPython's native extension ecosystem is also a major concern.

**Recommendation:** keep the existing Python runtime working for now; prototype RustPython in an isolated branch or experimental launcher; measure compatibility against ZirohNeth's actual imports, tests, networking behavior, cryptographic operations, and plugins before making an adoption decision.

## 🌈 What exactly are we evaluating?

### RustPython: a Python interpreter implemented in Rust

RustPython is an independent Python interpreter, not CPython wrapped in Rust. Its goals include a full Python 3 environment, a clean implementation, embedding into Rust applications, and WebAssembly support.

Potential benefits for ZirohNeth:

- A Rust-native implementation that fits a Rust-centered architecture.
- A possible path toward distributing a controlled runtime alongside the application.
- Native Linux and Windows build targets, subject to dependency and platform testing.
- An embedding model that could let a Rust application expose Python as a scripting or extension language.
- A possible future WebAssembly path for constrained or browser-oriented use cases.

Important limitations:

- The project explicitly describes itself as being in development and not production-ready.
- Standard-library coverage is incomplete; the project's own documentation has warned that only around half of the standard library is supported.
- CPython C-extension compatibility must not be assumed.
- Python package installation does not guarantee that a package's native components will work under RustPython.
- Compatibility, performance, memory use, startup behavior, and Windows packaging must be measured with ZirohNeth's workload.

Sources: [RustPython repository](https://github.com/RustPython/RustPython), [RustPython project site](https://rustpython.github.io/).

### PyO3: Rust integration, not a Rust-written Python interpreter

[PyO3](https://pyo3.rs/) is a different option. It provides Rust bindings for Python, allowing Rust applications to embed and interact with supported Python interpreters, and allowing Rust code to be exposed as Python extension modules.

PyO3 can be useful if ZirohNeth wants to move performance-sensitive or security-sensitive components to Rust while preserving CPython compatibility for existing Python code. But PyO3 does **not** replace CPython with an interpreter written in Rust. The embedded interpreter remains the selected Python distribution, and deployment must account for its shared or static runtime libraries.

Sources: [PyO3 user guide](https://pyo3.rs/), [PyO3 embedding and distribution](https://pyo3.rs/main/building-and-distribution.html).

## 🌈 Current ZirohNeth compatibility surface

The repository is not a small collection of pure-Python scripts. Its current dependency list includes networking, concurrency, cryptography, serialization, database, and WebSocket components.

Examples found in the current `requirements.txt` include:

| Dependency | Why it matters to the runtime study |
|---|---|
| `gevent` | Core concurrency and cooperative I/O behavior; native/runtime integration must be checked. |
| `asyncio-gevent` | Bridges two concurrency models and is a particularly important compatibility test. |
| `gevent-ws` | WebSocket functionality tied to the gevent ecosystem. |
| `coincurve` | Cryptographic functionality with native components. |
| `blake3` | Hashing dependency whose available wheel/native implementation must be verified. |
| `fastbencode` | Serialization dependency; verify whether the installed implementation relies on CPython extensions. |
| `aio-btdht` and `aio-krpc-server` | Network discovery and DHT-related behavior that must be tested end to end. |
| `msgpack`, `rsa`, `requests`, `PySocks` | Serialization, cryptography, HTTP, and proxy functionality. |

The list is taken from the repository's current `requirements.txt`; it is not a claim that every dependency is incompatible with RustPython. Each package needs an individual import, installation, and runtime test.

The existing launcher also checks for Python 3.8+ and recommends Python 3.11+, while the codebase uses standard-library modules and runtime behaviors that must be inventoried before selecting another interpreter.

Sources: [ZirohNeth requirements.txt](../requirements.txt), [ZirohNeth zeronet.py](../zeronet.py).

## 🌈 Linux and Windows viability

RustPython is a Rust project and can be compiled for multiple targets, making Linux and Windows plausible targets for an experimental runtime. That does not automatically mean that the complete ZirohNeth application is portable under it.

The real portability test is the complete application stack:

1. Build the interpreter for each target architecture and operating system.
2. Run the same Python compatibility suite on Linux and Windows.
3. Verify imports and behavior for every required dependency.
4. Test native libraries, filesystem paths, sockets, TLS, proxies, and cryptographic operations.
5. Test startup, shutdown, restart, logging, configuration, and data-directory handling.
6. Produce repeatable distributable builds and test them on clean machines without a developer toolchain installed.

Windows deserves particular attention because native extension availability, compiler requirements, filesystem behavior, and packaging can differ from Linux.

## 🌈 Recommended evaluation plan

### Phase 1: establish a baseline

- Record the currently supported Python versions and operating systems.
- Capture the existing test suite and representative startup/networking scenarios.
- Inventory direct and transitive dependencies.
- Identify packages that import CPython C extensions or depend on CPython-specific APIs.
- Record baseline startup time, memory use, and representative workload performance.

### Phase 2: build an isolated RustPython prototype

- Build or obtain a pinned RustPython revision.
- Run small, dependency-free project modules first.
- Test standard-library imports used by the application.
- Test argument parsing, configuration, logging, filesystem access, sockets, and cryptographic primitives.
- Keep this prototype separate from the default launcher. Do not change the production runtime yet.

### Phase 3: dependency compatibility matrix

For every direct dependency, record:

- Can it be installed or otherwise made available?
- Does it import successfully?
- Does it use a CPython C extension?
- Do its unit tests pass?
- Does its real ZirohNeth integration scenario pass?
- Is the behavior equivalent on Linux and Windows?

Classify each result as **Pass**, **Partial**, **Blocked**, or **Not tested**. A successful import alone is not a compatibility pass.

### Phase 4: compare architecture options

Evaluate three paths using the same application tests:

1. **RustPython-first:** use RustPython as the interpreter, if the dependency and standard-library gaps are resolved.
2. **CPython + Rust core:** retain CPython initially and progressively move suitable subsystems to Rust, using PyO3 where appropriate.
3. **Gradual hybrid:** keep the current application operational while introducing isolated Rust services or modules, then revisit the interpreter decision with evidence.

### Phase 5: adoption gate

Do not replace the current interpreter until all critical dependencies and application workflows pass on both Linux and Windows, packaging is reproducible, and performance and memory use are acceptable. Any missing functionality must be documented rather than silently worked around.

## 🌈 Preliminary recommendation

RustPython is a compelling long-term research candidate for ZirohNeth because it aligns with the ambition of a Rust-native, cross-platform engine. Its embedding and WebAssembly directions are especially interesting for a network that may eventually need multiple execution environments.

However, the current dependency stack makes an immediate interpreter swap too risky. In particular, gevent-based concurrency and native cryptographic or serialization packages could block a direct migration.

A pragmatic path is to **separate the future Rust engine from the current Python application**, prototype RustPython against real modules, and consider PyO3 for incremental Rust integration where CPython compatibility is still needed. This preserves a working baseline while allowing the architecture to evolve.

**Decision for now: investigate and prototype RustPython; do not make it the default runtime until the compatibility gate is passed.**

## 🌈 References

- [RustPython source repository](https://github.com/RustPython/RustPython)
- [RustPython project site and status](https://rustpython.github.io/)
- [RustPython documentation](https://rustpython.github.io/docs/)
- [PyO3 documentation](https://pyo3.rs/)
- [PyO3 embedding and distribution guide](https://pyo3.rs/main/building-and-distribution.html)
- [Python documentation: extending and embedding CPython](https://docs.python.org/3/extending/)


---

# 🌈 Architecture Addendum: Dual Runtimes, RustPython Lab, and Distribution

**Updated:** 2026-11-21  
**Status:** Proposed architecture and experimental roadmap. This addendum does not claim that dual-runtime execution, RustPython compatibility, or packaged builds have been implemented or tested.

## 🌈 Architectural decision under evaluation

ZirohNeth may support **CPython and RustPython side by side** during a gradual migration.

- **CPython** remains the compatibility runtime for the existing application and packages that require CPython-specific behavior or native extensions.
- **RustPython** becomes an integrated, experimental runtime for modules that pass the project's compatibility tests.
- **Rust-native services** progressively take responsibility for suitable networking, cryptography, serialization, storage, and other core functions.

The long-term goal is not to keep two interpreters forever. It is to make migration incremental, evidence-based, and reversible without blocking current ZirohNeth functionality.

### Runtime assignment is not automatically one process per Python file

A module cannot safely be moved to another interpreter merely because it is a separate `.py` file. Python modules often share objects, import state, global variables, plugin registries, exception classes, callbacks, and assumptions about the same interpreter.

Runtime selection must therefore happen at a **defined execution boundary**:

1. A standalone script or command.
2. A self-contained worker/service.
3. A package or plugin group whose imports and state remain inside one interpreter.
4. A module exposed through an explicit, versioned service interface.

Modules that exchange Python objects or rely on shared interpreter state must remain in the same runtime until that coupling is removed or replaced by a defined protocol.

### Preferred first implementation: separate worker processes

Start with a Rust supervisor/launcher that can start and manage:

- A CPython worker using the pinned, bundled CPython distribution.
- A RustPython worker using the RustPython VM embedded in a Rust executable, or a separately packaged RustPython executable during early experiments.
- Rust-native services where a stable interface has been defined.

Use explicit IPC between workers. Suitable initial transports include local sockets or standard input/output with framed messages. JSON is a simple first protocol; MessagePack may be considered after interoperability and schema requirements are established.

Define message envelopes with at least:

- Protocol version.
- Request/correlation ID.
- Service or operation name.
- Typed payload.
- Structured success or error response.

Do not pass live Python objects, interpreter pointers, or implicit shared-memory assumptions between CPython and RustPython. Convert data at the boundary.

Process separation improves dependency and crash isolation, but it is **not by itself a security sandbox**. If untrusted plugins or scripts are ever executed, apply explicit OS-level permissions, filesystem/network restrictions, resource limits, and a threat model.

Embedding both interpreters in one process can be evaluated later. It introduces additional lifecycle, linking, allocator, global-state, and native-library concerns; it should not be the first milestone.

## 🌈 Runtime manifest

Introduce a manifest to declare the intended runtime and entry point for each independently executable unit. The following is an illustrative format, not a file that has already been added:

```toml
[modules.bencode]
runtime = "rustpython"
entrypoint = "src.lib.bencode_open"

[modules.diff]
runtime = "rustpython"
entrypoint = "src.util.Diff"

[modules.safe_re]
runtime = "rustpython"
entrypoint = "src.util.SafeRe"

[modules.query_json]
runtime = "rustpython"
entrypoint = "src.util.QueryJson"

[modules.rate_limit]
runtime = "cpython"
entrypoint = "src.util.RateLimit"

[modules.legacy_plugins]
runtime = "cpython"
entrypoint = "src.Plugin.PluginManager"
```

The manifest must eventually support dependency constraints, runtime version, working directory, environment requirements, health checks, restart policy, and IPC contract version. Runtime assignment must be validated against the import/dependency graph; it must not silently split tightly coupled modules across interpreters.

## 🌈 First RustPython experiments in the current codebase

Begin with small, deterministic modules. The paths below are **candidates for inspection and testing**, not compatibility claims. Before assigning any module to RustPython, record its complete import graph, Python-version assumptions, filesystem/network effects, and transitive dependencies.

| Priority | Candidate | Initial test surface | Main caveat |
|---:|---|---|---|
| 1 | `src/lib/bencode_open/__init__.py` | Encode/decode integers, byte strings, lists, dictionaries, malformed and truncated inputs, round-trip behavior | Verify exact Bencode semantics and edge cases against the project's current implementation |
| 2 | `src/util/Diff.py` | Import, text diff behavior, insert/delete/replace cases | Check `io` and `difflib` behavior |
| 3 | `src/util/SafeRe.py` | Regex compilation, matching, caching, invalid patterns | Verify `re` semantics and any security/time-complexity expectations |
| 4 | `src/util/Flag.py` | Class/decorator behavior and collection semantics | Check `collections` behavior and import-time assumptions |
| 5 | `src/util/QueryJson.py` | JSON parsing/query behavior and controlled filesystem fixtures | Exercise `json`, path handling, traversal, and permissions |
| 6 | `src/Crypt/CryptHash.py` | Standard-library hash algorithms, base64, random bytes, path handling | Test optional/native hashing backends separately; do not assume BLAKE3 compatibility |

### Defer until the runtime boundary and dependencies are understood

- `src/util/RateLimit.py`: currently tied to gevent-related scheduling and concurrency.
- `src/Content/ContentManager.py`: integration-heavy content lifecycle and concurrency behavior.
- `plugins/Cors/CorsPlugin.py`: plugin and gevent integration.
- `src/Plugin/PluginManager.py`: dynamic imports, `sys.modules`, reload, class composition, and shared plugin state.
- `src/main.py`: startup ordering and gevent monkey patching affect the process as a whole.

A successful import is not a pass. A candidate is compatible only after its behavior and integration contract have been tested.

## 🌈 Differential compatibility testing

Create a reusable test harness that runs the same test vectors in separate CPython and RustPython processes and compares normalized results.

For each candidate, test:

1. Import and initialization.
2. Public API shape and expected exceptions.
3. Deterministic outputs against shared fixtures.
4. Edge cases, malformed inputs, and boundary conditions.
5. Filesystem and platform behavior where relevant.
6. Integration with its actual ZirohNeth callers.
7. Linux and Windows behavior.
8. Repeatability across clean builds and pinned runtime versions.

Classify each module/dependency as:

- `PASS`: required behavior and integration tests pass on the supported targets.
- `PARTIAL`: some behavior works, but known gaps remain.
- `BLOCKED`: a required capability currently prevents migration.
- `UNVERIFIED`: insufficient tests or evidence.

Record runtime version, OS/architecture, test command, commit SHA, and evidence for every status. Do not promote a module based on an import-only smoke test.

## 🌈 RustPython fork and AI-assisted compatibility work

A maintained Floflis fork may be created when the first concrete compatibility gap requires a change in RustPython itself. Possible repository name: `Floflis/RustPython-ZirohNeth`. Confirm naming and repository setup before creating it.

Fork maintenance requirements:

- Track a pinned upstream RustPython revision and document the upstream base commit.
- Keep Floflis patches small, topic-scoped, and independently reviewable.
- Prefer upstream contributions for generally useful fixes; keep ZirohNeth-specific integration in separate patches.
- Document every compatibility behavior and its intended CPython reference behavior.
- Add regression tests alongside each implementation.
- Maintain a changelog and an upstream synchronization procedure.
- Never silently claim complete CPython compatibility.

AI-assisted implementation is appropriate for investigating gaps, drafting implementations, generating test cases, and porting well-specified behavior. It does not replace review or conformance testing.

Choose the implementation layer deliberately:

- Pure-Python standard-library behavior may be implemented in Python when that is the simplest compatible solution.
- VM, interpreter, or standard-library integration gaps may require Rust changes in RustPython.
- Platform-specific capabilities may require Rust/native backends.
- CPython C-API compatibility must be treated as a separate, substantial project; it must not be implied by implementing a similarly named Python module.

For every AI-assisted change, require a reproducible test, source/reference behavior, platform coverage where applicable, and a traceable commit/PR.

## 🌈 Shipping RustPython with ZirohNeth

The intended user experience is that Linux and Windows users receive a ZirohNeth distribution that contains its required runtimes. Users should not need to install Rust, Cargo, or a separate RustPython package merely to run the application.

### Preferred distribution path

**Initial experiment:**
- Build a small Rust launcher/worker that embeds a pinned RustPython VM.
- Keep Python source modules and required standard-library resources in a clearly versioned application layout.
- Alternatively, package a separate RustPython worker executable while the embedding API and startup design are being validated.

**Later distribution:**
- Embed/freeze the standard library where supported and appropriate.
- Register ZirohNeth's Rust-native modules through the supported RustPython embedding/module APIs.
- Produce reproducible, signed or checksum-verified Linux and Windows artifacts.
- Keep CPython in a separate, pinned portable runtime directory for legacy modules until it is no longer needed.

Illustrative package layout (not an implemented layout):

```text
ZirohNeth/
├── bin/
│   └── zeroneth
├── runtime/
│   └── cpython/              # temporary compatibility runtime
├── python/
│   └── Lib/                  # resources if not frozen into the binary
├── plugins/
├── config/
└── data/
```

Windows may use `zeroneth.exe`; Linux may use an ELF executable. Exact runtime files and shared-library requirements must be established by clean-machine packaging tests, not assumed from the build host.

### Linux and Windows build matrix

At minimum, validate:
- Linux x86_64.
- Linux aarch64.
- Windows x86_64.

Additional targets such as Linux musl, Windows ARM64, and other architectures should be added when supported by the RustPython dependency graph and ZirohNeth's native dependencies. Do not describe a target as supported until its CI build and runtime tests pass.

For each target:
- Build from a pinned Rust toolchain and dependency lockfile.
- Run RustPython conformance and ZirohNeth module tests.
- Verify TLS, sockets, filesystem paths, process management, and native module loading as applicable.
- Test on a clean machine without Rust/Cargo or a system Python installation.
- Inspect dynamic-library dependencies and licensing notices.
- Verify upgrade, rollback, logs, configuration, and data-directory behavior.

CPython packaging is a separate concern: use a pinned portable/embeddable distribution appropriate to each OS and verify its native dependencies. Do not assume that a CPython package built for one OS or architecture can be reused on another.

## 🌈 Proposed implementation roadmap

### Phase 0 — Baseline and inventory
- [ ] Record the current default branch commit and existing runtime behavior.
- [ ] Inventory direct and transitive imports for the six initial candidates.
- [ ] Capture CPython reference outputs and existing test coverage.
- [ ] Record supported OS/architecture targets and current CI coverage.

### Phase 1 — RustPython Lab
- [ ] Add an isolated RustPython launcher/worker prototype.
- [ ] Pin the RustPython revision and Rust toolchain.
- [ ] Run a minimal interpreter smoke test on Linux and Windows.
- [ ] Execute the first candidate module tests without changing the default runtime.
- [ ] Publish logs and test evidence.

### Phase 2 — Dual-runtime supervisor
- [ ] Define a versioned IPC envelope and error model.
- [ ] Implement worker startup, shutdown, health checks, and structured logs.
- [ ] Add a runtime manifest and validate module dependency boundaries.
- [ ] Demonstrate one CPython worker and one RustPython worker in the same ZirohNeth session.
- [ ] Test worker crash/restart and graceful application shutdown.

### Phase 3 — Compatibility fork
- [ ] Create a Floflis RustPython fork only when concrete patches are ready to maintain.
- [ ] Establish upstream tracking and synchronization documentation.
- [ ] Add differential CPython/RustPython tests.
- [ ] Implement missing capabilities one issue/PR at a time.
- [ ] Keep CPython as the fallback for every unverified module.

### Phase 4 — Native migration and packaging
- [ ] Evaluate Rust replacements for gevent-dependent and native-extension-heavy components.
- [ ] Move suitable services behind stable interfaces.
- [ ] Integrate RustPython into the ZirohNeth launcher.
- [ ] Bundle the pinned CPython compatibility runtime where still required.
- [ ] Add clean-machine Linux and Windows packaging tests.

### Phase 5 — Adoption gate
- [ ] All migrated modules pass differential and integration tests.
- [ ] Critical application workflows pass on every declared supported target.
- [ ] Runtime selection and fallback behavior are documented and tested.
- [ ] Distribution is reproducible and does not require a developer toolchain.
- [ ] Performance, memory, startup, and operational behavior meet project-defined thresholds.

Only after these gates should the project consider changing the default runtime or removing CPython.

## 🌈 Current status and non-goals

This addendum is a plan, not an implementation report. It does not claim that:
- CPython and RustPython are already orchestrated together.
- Any listed module has passed RustPython compatibility tests.
- A Floflis RustPython fork has been created.
- Linux or Windows packaged artifacts exist.
- RustPython is production-ready for all ZirohNeth workloads.

The immediate deliverable is an isolated, measurable RustPython Lab while preserving the working CPython baseline.
