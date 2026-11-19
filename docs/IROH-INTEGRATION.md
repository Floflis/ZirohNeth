# Iroh integration

## Why a bridge instead of invoking `iroh` directly?

Iroh is primarily a Rust library/API for authenticated QUIC connections,
NAT traversal, and relay fallback. It is not a generic daemon exposing a
standard RPC endpoint that a Python application can safely assume exists.
The upstream project recommends using the Rust library directly; other
languages can use the separately maintained FFI project.

ZirohNeth is Python today, so the intended boundary is a small, separately
versioned Rust bridge built against a pinned Iroh release. The bridge will own
Iroh endpoints and expose a narrow, versioned IPC contract to Python.

## Current implementation

- `iroh_mode=disabled` is the default and performs no process discovery.
- `iroh_mode=external` only resolves and validates a dedicated
  `iroh-bridge` executable.
- The manager does not execute the bridge yet. It fails closed until the
  IPC contract, protocol version negotiation, identity handling, and Rust
  implementation are reviewed and tested.
- The generic upstream `iroh` executable is not treated as a compatible
  bridge.
- No binaries are downloaded or installed automatically.

## Planned bridge contract

The Rust sidecar should use a versioned JSON-lines control channel over
stdin/stdout (or a platform-native local socket), keep diagnostics on stderr,
and expose explicit operations for endpoint identity, peer dialing, blob
transfer, and shutdown. The transport protocol must use a dedicated ALPN.
The bridge must never expose private keys through the control channel.

## Architecture boundary

Iroh provides connectivity and authenticated QUIC transport. Content
addressing and synchronization should be layered separately, for example
with iroh-blobs or iroh-docs where their semantics fit. Do not assume that
Iroh itself is an IPFS-compatible content-addressed network.

## Security and release requirements

Before managed installation is enabled:

1. Pin an upstream Iroh release and Rust toolchain.
2. Publish per-platform artifacts with SHA-256 checksums and verified
   signatures/provenance.
3. Restrict bridge IPC to the local user and validate protocol versions.
4. Keep private identity material in the bridge's protected data directory.
5. Test upgrade, rollback, crash recovery, and process ownership.
