# Optional IPFS/Kubo integration

IPFS support is opt-in. The initial adapter defines three modes:

- `disabled` (default): do not probe, connect, or launch Kubo.
- `external`: use a user-installed Kubo daemon, RPC restricted to localhost.
- `managed`: reserved for a future installer that downloads a pinned Kubo release,
  verifies a SHA-256 manifest, and stores it in the user's application-data directory.

## Security requirements for managed mode

Managed downloads must be disabled until all supported OS/architecture artifacts
have release-pinned SHA-256 values from an authenticated upstream release source.
Never execute an artifact when its checksum is absent or mismatched. Extract
archives into a temporary directory, validate expected paths, then atomically
move into the application data directory. Never put downloaded binaries in the
repository or application source tree.

Kubo RPC must be bound to loopback only (127.0.0.1 / ::1). Do not configure
public RPC addresses or expose port 5001 to the LAN/WAN.

## Python client

The RPC client (`aioipfs`) should be an optional dependency added only when
IPFS functionality is enabled. It is a client for Kubo, not a P2P node itself.
