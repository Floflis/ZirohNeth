# OS and architecture portability study

**Status:** research and test plan. This document complements `RUSTPYTHON_RUNTIME_STUDY.md`; it does not replace it and does not claim that RustPython, CPython, or the complete application currently supports every target below.

## 1. The portability question has multiple layers

A Python application can be portable at one layer and blocked at another:

1. **Operating system port:** the OS supports the CPU architecture.
2. **Interpreter:** CPython or RustPython can be built and run on that OS/architecture.
3. **Standard library:** the modules used by the application work there.
4. **Third-party packages:** pure-Python wheels, platform wheels, or source builds are available.
5. **Native extensions:** C/C++/Rust extensions compile and link against the selected interpreter ABI.
6. **Application behavior:** sockets, TLS, subprocesses, filesystem semantics, crypto, permissions and startup work.
7. **Distribution:** a reproducible environment or executable can be installed on a clean device.

A successful interpreter build is not proof of application portability.

## 2. Target inventory

| OS / environment | CPU architectures to investigate | Python strategy | Main validation |
|---|---|---|---|
| Linux | x86-64, AArch64, ARMv7, RISC-V 64 | CPython baseline; RustPython experiment | Full requirements install and tests |
| Android / Termux | AArch64, ARMv7, x86-64 | Termux CPython first; RustPython only as separate prototype | Run directly on device, inspect native wheels |
| macOS | x86-64, AArch64 | CPython universal/architecture-specific builds | Native dependency installation and network tests |
| Windows | x86-64, ARM64, legacy x86 where dependencies permit | CPython official builds; ARM64 native validation | Native wheels, subprocesses, path and socket behavior |
| FreeBSD | amd64, AArch64, ARMv7, RISC-V 64 where OS ports exist | Native CPython package/build; source builds | Native package availability and BSD API behavior |
| OpenBSD | amd64, ARM64, ARMv7, RISC-V 64 where supported by the OS | Native package/build | OpenBSD-specific networking, sandbox and crypto behavior |
| NetBSD | amd64, ARM, RISC-V 64 and other maintained ports | Native package/build | Package availability and ABI compatibility |
| DragonFly BSD | x86-64 | Native package/build | Native dependencies and filesystem/socket behavior |
| RedoxOS | x86-64, AArch64, i586, RISC-V 64 are OS/Rust target research directions | Interpreter feasibility study first | libc/POSIX surface, process model, TLS and native extensions |

The OS architecture list is not a promise that CPython or every Python package supports that architecture. Record interpreter availability and package availability separately.

## 3. CPython and RustPython are different compatibility bets

### CPython

CPython is the compatibility baseline because most third-party Python packages target its C API and ABI. It still does not guarantee wheels for every OS/architecture. On BSD, Android, Redox and less common CPU ports, source builds and package patches may be required.

### RustPython

RustPython's Rust implementation may make interpreter ports attractive, but it does not automatically provide:
- Complete CPython C-API compatibility.
- Binary compatibility with CPython extension modules.
- A complete standard library for every target.
- Wheels for packages that ship native code.
- Equivalent behavior for all platform-specific Python modules.

Treat RustPython as a separately tested interpreter implementation. Do not infer that compiling RustPython for RISC-V or Redox makes ZirohNeth's dependency stack portable there.

### Hybrid path

The least disruptive migration path is to keep CPython as the baseline while evaluating Rust modules or services for platform-sensitive components. PyO3 can help with incremental native modules where CPython remains available, but it introduces its own interpreter ABI and target-build constraints.

## 4. Dependency audit

For every direct and transitive requirement, maintain a record with:

| Field | Required evidence |
|---|---|
| Package/version | Exact pinned version |
| Pure Python? | Source inspection or package metadata |
| Native extension? | Wheel tags, build metadata, import result |
| C library dependencies | Required headers, linker libraries and minimum versions |
| Interpreter compatibility | CPython versions and RustPython test status |
| OS/architecture availability | Published wheel or reproducible source build |
| Runtime behavior | Relevant ZirohNeth integration tests |
| Result | Pass / Partial / Blocked / Not tested |

Prioritize dependencies used by networking, cryptography, serialization, storage, DNS, HTTP/TLS, subprocesses and event loops. A package import is not a sufficient compatibility test.

## 5. CI and runtime strategy

- Linux x86-64 is the baseline hosted CI environment.
- Use native ARM64 Linux runners for ARM64 runtime tests; use cross-compilation for ARMv7 and RISC-V only as an earlier evidence level.
- macOS Intel and Apple Silicon should be separate architecture lanes.
- Windows x64 and ARM64 should use native runners for release validation.
- Android requires Termux/device tests in addition to NDK or wheel-build checks.
- BSD and Redox need dedicated VMs, emulators or self-hosted hardware. A Linux runner cannot prove native BSD/Redox behavior.
- RISC-V runtime validation should use QEMU or native hardware and record the exact OS image and CPU model.
- Keep dependency-install, syntax, unit, integration, runtime and packaging results separate.

## 6. Required evidence labels

- **I0 — OS port identified:** OS and architecture are maintained by the OS project.
- **I1 — interpreter available:** exact interpreter version builds and starts.
- **I2 — dependency install:** all required dependencies install from wheels or reproducible source builds.
- **I3 — application tests:** ZirohNeth's relevant tests pass.
- **I4 — runtime validation:** network, crypto, storage and process behavior pass on native hardware or a documented VM.
- **I5 — distribution:** a clean installation works without developer tools.

Never report a target as supported if only I0 or I1 has been demonstrated.

## 7. Recommended sequence

1. Inventory the actual requirements and imports, including optional modules.
2. Establish CPython baselines on Linux x86-64, Linux ARM64, macOS and Windows.
3. Add Termux ARM64 testing on real Android hardware.
4. Evaluate ARMv7 and RISC-V Linux with source-build and QEMU lanes.
5. Evaluate FreeBSD and NetBSD before OpenBSD/DragonFly.
6. Treat Redox as an OS porting research project: establish interpreter, libc, process, filesystem and socket prerequisites before attempting the whole app.
7. Run RustPython compatibility tests against real ZirohNeth modules and dependencies without replacing the production interpreter.
8. Publish a platform as supported only after I5 evidence.

## 8. Relationship to the existing RustPython study

Keep `RUSTPYTHON_RUNTIME_STUDY.md` as the interpreter/runtime evaluation. This document broadens the question to the complete OS × architecture × interpreter × package ecosystem. Update both documents when a concrete test changes the evidence level; do not duplicate or silently rewrite the earlier conclusions.
