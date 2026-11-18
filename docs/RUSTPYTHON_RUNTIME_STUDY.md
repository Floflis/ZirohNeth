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
