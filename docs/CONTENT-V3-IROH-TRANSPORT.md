# ZirohNeth Content v3 Iroh transport

This first runtime slice implements the v3 transport boundary without changing
v1/v2 behavior.

## Version routing

- v1 and v2 root manifests and files continue through the existing ZeroNet
  peer/file-transfer pipeline.
- A v3 root content.json is bootstrapped and signature-verified through
  ZeroNet. The exact manifest bytes are then fetched by BLAKE3 hash from its
  signed Iroh provider list as an additional serving path. The ZeroNet file
  server refuses ordinary v3 file requests but continues serving content.json.
- After the v3 root manifest is verified, all non-content.json required and
  optional files are fetched only through Iroh. The legacy Worker/Peer path is
  never used for those files.
- An Iroh error is a download failure. There is no ZeroNet fallback.
- V3 included/user manifests and v2-to-v3 conversion are not enabled in this
  slice. A local v2 head cannot be replaced by v3 without a separately
  authenticated VersionTransition. V3 root manifests with includes are also
  rejected until the included-manifest transport and authorization model is ready.

## V3 provider metadata

The signed root manifest contains a top-level iroh object with a providers
array. Each provider is an Iroh NodeAddr represented by node_id, relay_url
(nullable), and direct_addresses (an array). Example:

    {
      "content_version": 3,
      "hash_algorithm": "blake3-256",
      "identity_scheme": "ethereum-eoa-secp256k1",
      "signature_scheme": "ethereum-eip712-v3",
      "iroh": {
        "providers": [{
          "node_id": "<64-hex-character Iroh endpoint id>",
          "relay_url": "https://relay.example/",
          "direct_addresses": ["192.0.2.10:11204"]
        }]
      }
    }

The same provider set serves the exact content.json blob and the
BLAKE3-addressed files in the manifest. Provider count is limited to 16;
each address list is limited to 32 entries. Provider hints are covered by the
v3 EIP-712 signature.

The Iroh sidecar uses the version-pinned iroh-blobs 0.35.0 protocol and its
BLAKE3-verified blob transfer. Python independently checks the received bytes
against the signed manifest's flat BLAKE3-256 digest and declared size before
writing them into the site directory.

## Local publishing

When an existing v3 root manifest is signed with its Ethereum owner key,
ZirohNeth obtains its local Iroh endpoint address and places it in the signed
provider list. After writing the signed manifest, it imports all present
required/optional files and the exact root content.json into its persistent
local Iroh blob store. ZeroNet publication remains unchanged and continues to
publish the root manifest.

## Required runtime

Build/install zirohneth-iroh-bridge from the companion
Floflis/zeronet-rs/iroh-bridge crate and make it available on PATH.
Alternatively set ZIROHNETH_IROH_BRIDGE to its executable path. The bridge
stores its Iroh endpoint key and blob data under the configured ZirohNeth data
directory. The endpoint key is never exposed to Python or the manifest.

## Security and current limits

- Iroh's verified blob protocol is not treated as publisher authorization.
  Ethereum EIP-712 v3 still authenticates the manifest and provider hints.
- Python verifies BLAKE3 and size before promoting downloaded data.
- The bridge restricts source and destination paths to the application data
  directory and caps JSONL requests at 64 KiB.
- Iroh provider availability/discovery is currently explicit in the signed
  manifest. A separate dynamic provider index, signed endpoint-binding
  records, multi-provider mirror announcements and address refresh protocol
  remain future work.
- The current bridge uses standard iroh-blobs transfers, not a custom
  ZirohNeth ALPN protocol.
