# ZirohNeth ToDo

This file tracks work that is not yet implemented or not yet verified. An item moves out of this list only after code, tests, compatibility checks and documentation are complete.

## Content v2 audit remediation (2026-11-19)

Code changes have been started for legacy-file pre-verification, staged migration recovery, destination-to-proof binding, local update-chain continuity, and backend verification-state reporting. These remain open until automated tests and runtime validation pass.

- [ ] Add tampered legacy-file and missing-required/optional-file tests for migration pre-verification.
- [ ] Add crash/fault-injection tests before copy, during copy, before promotion, after promotion, during signing and after publish; verify journal-bound resume and safe conflict rejection.
- [ ] Add tests proving an unrelated but valid Ethereum destination cannot be reused, while an exact proof-bound destination is idempotent.
- [ ] Add v2 update-chain tests for valid sequential updates, replay, rollback, skipped sequence, same-sequence fork and restart persistence.
- [ ] Define first-contact freshness witnesses or quorum/transparency policy. A valid signature alone does not prove freshness; current clients must surface this limitation.
- [ ] Version peer hashfield encoding with digest-algorithm namespaces while preserving legacy peer interoperability. Do not reinterpret the existing 16-bit wire format.
- [x] Add migration protocol v2 with explicit SHA-256 legacy digest, BLAKE3-256 payload digest, RFC 8785 canonicalization and a version-2 EIP-712 domain; retain the v1 verifier without changing v1 semantics.
- [ ] Add v1/v2 migration golden vectors and cross-implementation signature/digest tests.
- [x] Validate clean-environment pip install -r requirements.txt and compileall on Python 3.11 (GitHub Actions runs 1 and 2 passed).
- [ ] Verify the full supported-Python version matrix; only Python 3.11 is covered by the current dependency workflow.
- [ ] Keep includes/user_contents migration fail-closed; document preflight behavior and design a trust-preserving migration format before supporting them.
- [ ] Add automated transport tests for per-site onion restrictions.
- [x] Document Ethereum per-site onion restrictions separately from global Tor and tracker proxy behavior in the Content v2 implementation guide.
- [ ] Add browser-to-backend tests for direct Ethereum navigation, listing, reload, internal links, invalid manifests and peer/transport failures.
- [ ] Execute the complete unit/integration suite and record actual results before declaring Content v2 release-ready.

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
- [x] Enforce the locally checkpointed final-manifest boundary in ContentManager verification.
- [x] Embed the dual-signed migration proof in the terminal Bitcoin content.json so the old site itself advertises its Ethereum destination.
- [x] Resolve a visited Bitcoin address to its Ethereum destination after verifying the embedded proof; preserve the old address and site directory as historical data.
- [x] Pin the first verified migration proof locally and reject a conflicting/rolled-back Bitcoin root manifest.
- [x] Add a migration workflow that copies authorized root-manifest files to a new Ethereum site, signs a v2/BLAKE3 root manifest and publishes it.
- [ ] Add a user-facing CLI/UI to initiate migration, display verification state and recover safely from interrupted steps.
- [x] Enforce backend historical mode: block new signatures under the old identity and allow only re-advertising its exact terminal root manifest.
- [ ] Complete and test historical/read-only UI lifecycle, including clear redirect messaging and preventing edit controls from being offered for the old identity.
- [ ] Add stale-peer withholding, rollback, conflicting destination, malformed proof and file-copy adversarial tests. Tests are added but not yet executed.
- [ ] Migrate included/user manifests and their signer lifecycle before lifting the current restriction.
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
