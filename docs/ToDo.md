# ZirohNeth ToDo

This file tracks work that is not yet implemented or not yet verified. An item moves out of this list only after code, tests, compatibility checks and documentation are complete.

## Content protocol

- [ ] Complete the content v2 implementation and run the full test suite.
- [ ] Add golden compatibility tests proving that v1 manifests, legacy SHA-512-truncated-256 hashes and Bitcoin signatures remain unchanged.
- [ ] Define and test the v2 hashfield/cache compatibility policy. The current compact hashfield stores only 16-bit prefixes and does not encode the digest algorithm.
- [ ] Extend Ethereum EIP-712 signing beyond the root content.json manifest and define how included manifests/certificates are authorized.
- [ ] Add adversarial tests for unknown versions, unknown algorithms, malformed manifests, duplicate JSON keys, replay and rollback.
- [ ] Add a cross-implementation RFC 8785 + EIP-712 test corpus for Python and future Rust clients.

## Bitcoin → Ethereum migration

- [x] Implement dual-signed migration proof primitives: legacy Bitcoin authorization plus EIP-712 Ethereum acceptance over the same migration payload.
- [x] Bind the proof to the final legacy manifest digest, old Bitcoin identity, new Ethereum identity, protocol version and terminal sequence; verify the legacy manifest signature and digest.
- [x] Implement an atomic local checkpoint ledger with explicit trust-anchor pinning, hash linkage, contiguous sequence checks and replay rejection.
- [x] Enforce the locally checkpointed final-manifest boundary in ContentManager verification.\n- [ ] Integrate migration lifecycle into SiteManager/UI: register the Ethereum site, retain the Bitcoin site as historical/read-only, and expose a safe migration workflow.
- [ ] Select and implement a network-wide checkpoint discovery backend (on-chain registry, transparency log or quorum) that can establish freshness for new clients; local storage alone cannot do this.
- [ ] Complete and test historical/read-only SiteManager/UI lifecycle. The workflow marks the old Site settings as historical, and the local ContentManager guard rejects non-terminal root manifests after pinning. Never silently rewrite an old site address.
- [ ] Run and expand migration tests for missing/mismatched signatures, final-manifest mismatch, replay, checkpoint forks, stale peers and checkpoint-source equivocation. Tests are added but not yet executed.

## Ethereum extensions

- [ ] Add Ethereum post-quantum identity/signature support as a separately versioned future protocol. Do not silently replace secp256k1/EIP-712.
- [ ] Evaluate ERC-1271 smart-wallet verification with an explicit chain, RPC and block-state policy.
- [ ] Design Ethereum multisignature support; current v2 EOA path is single-signer only.
- [ ] Define key import/export UX and safe handling for encrypted/private-key material. Never log secrets.

## Content v3 and IPFS

- [ ] Design content.json v3 with IPFS CIDv1 using the BLAKE3 multihash code.
- [ ] Decide the CID codec, raw-leaves policy, chunker and UnixFS import parameters. A CID for a UnixFS DAG is not the same as a raw BLAKE3 file digest.
- [ ] Specify whether v3 stores both a direct BLAKE3 file digest and a CID, and how each is verified.
- [ ] Verify Kubo and library support for the selected BLAKE3 multihash code across supported versions.
- [ ] Add CIDv1 interoperability vectors and migration tests from v2.

## Tor policy for Ethereum sites

- [ ] Add automated tests proving Ethereum-addressed sites never create hidden services, advertise onion endpoints, discover onion peers or connect to onion peers.
- [ ] Audit tracker proxying and global Tor modes to document precisely which traffic remains Tor-routed independently of per-site hidden-service policy.
- [ ] Verify legacy Bitcoin/Base58 sites retain their existing Tor behavior.

## Social identity and Sybil resistance

- [ ] Prototype an optional Human Passport integration without making a third-party score mandatory for reading, publishing or account ownership.
- [ ] Define a decentralized fallback based on portable credentials, local trust relationships and user-controlled attestations.
- [ ] Design privacy-preserving proof storage and selective disclosure; never publish raw Passport stamps or personal verification data in site content.
- [ ] Define appeal, recovery and false-positive handling before any score can limit posting or interaction.
- [ ] Evaluate API, on-chain and self-hosted verification paths, including provider outage and vendor lock-in behavior.

## ZeroNet ecosystem parity

- [ ] Audit ZeroHello and related ZeroNet/ZeroNet-Conservancy repositories against ZirohNeth; classify each feature as implemented, partially implemented, intentionally omitted or not yet reviewed.
- [ ] Decide whether ZeroHello is to be ported, redesigned as a native ZirohNeth portal, or kept as an external companion project.
- [ ] Review 0Me, 0dashboard, fid, znapi and the supporting Python networking/crypto repositories listed in docs/ECOSYSTEM-COMPATIBILITY.md.
- [ ] Keep the ecosystem inventory current when upstream sibling repositories receive relevant changes.

## Release and maintenance

- [ ] Run unit/integration tests on supported Python versions and operating systems.
- [ ] Verify dependency versions, packaging, reproducible installs and licensing.
- [ ] Update user-facing documentation and protocol compatibility notes after implementation is verified.
