# Hashfield v2 protocol

**Status:** implementation draft on `feat/hashfield-v2-algorithm-namespace`  
**Scope:** peer availability hints for SHA-512 legacy content and BLAKE3 content  
**Protocol version:** 2

## Goals

Hashfields tell a peer which optional-file digest prefixes a node may have. They are discovery hints only. They do not prove that a peer has a file or that downloaded bytes are valid; the requesting client must still verify the complete digest and file size against the site's signed manifest.

Hashfield v2 separates digest algorithms while retaining a compatibility projection for pre-v2 peers. It also makes the v2 prefix encoding independent of host endianness.

## Algorithm namespaces

Each algorithm has an explicit 16-bit namespace identifier:

| Algorithm | Namespace ID | Internal hash ID |
| --- | ---: | --- |
| SHA-512 legacy | 0 | `prefix16` |
| BLAKE3-256 | 1 | `0x10000 | prefix16` |

`prefix16` is the integer represented by the first four hexadecimal digest characters. A hash ID is therefore:

```text
hash_id = (algorithm_id << 16) | prefix16
```

This preserves the old SHA-512 integer IDs exactly. The BLAKE3 namespace is disjoint, so identical prefixes such as `AABB` produce SHA-512 ID `0x00AABB` and BLAKE3 ID `0x01AABB`.

The currently supported manifest algorithm aliases are `sha512` / `sha512-truncated-256` and `blake3` / `blake3-256`. New algorithm IDs must be assigned through a future protocol revision. Implementations must reject unknown namespaces rather than silently interpreting them as SHA-512.

## Version 2 wire payload

The `getHashfield` response and `setHashfield` request carry:

```python
{
    "hashfield_version": 2,
    "hashfields": {
        "sha512": b"...",  # sorted uint16 prefixes, network byte order
        "blake3": b"...",  # sorted uint16 prefixes, network byte order
    },
    "hashfield_raw": b"...",  # legacy compatibility union
}
```

Each entry in a typed field is an unsigned 16-bit integer encoded big-endian. Entries are sorted and deduplicated. An empty algorithm field is encoded as empty bytes. The maximum field size is 65,536 entries (131,072 bytes).

The compatibility field `hashfield_raw` is the deduplicated union of prefixes from both algorithm buckets, encoded in the original host-native `array('H')` format. It exists so an old client can continue to discover both SHA-512 and BLAKE3 content using its single untyped table. A v2 client must prefer `hashfields` and must not infer typed algorithm membership from `hashfield_raw` when a valid v2 marker is present.

Unknown explicit protocol versions and unknown algorithm names are rejected. Missing `hashfield_version` means the sender is using the legacy format; it does not mean “best effort v2”.

## Find-hash lookup

A v2 `findHashIds` request includes `hashfield_version: 2` and uses namespaced integer IDs. The response includes `hashfield_version: 2`; returned keys remain namespaced.

A legacy request omits `hashfield_version` and contains only 16-bit prefixes. A v2 server expands each requested prefix to both SHA-512 and BLAKE3 namespaces, searches both, then projects the result back to the original untyped prefix key. It omits the response version marker so the legacy response semantics remain explicit.

A v2 client querying a legacy server sends both each BLAKE3 namespaced ID and its raw 16-bit prefix. When the response has no version marker, the client treats a matching raw prefix as an ambiguous availability hint for the requested BLAKE3 ID as well as SHA-512. When a response is explicitly v2, raw keys are only SHA-512 and BLAKE3 results must arrive under their namespaced IDs.

## Compatibility behavior

| Sender | Receiver | Behavior |
| --- | --- | --- |
| v2 | v2 | Separate SHA-512 and BLAKE3 buckets; version 2 marker |
| v2 | legacy | Legacy `hashfield_raw` union is consumed; v2 fields are ignored |
| legacy | v2 | Untagged prefixes are treated as ambiguous hints in both buckets |
| legacy lookup | v2 server | Server searches both namespaces and projects matches to raw prefixes |
| v2 lookup | legacy server | Client also queries raw BLAKE3 prefixes and treats unversioned matches as ambiguous hints |

Pre-v2 peers did not label the algorithm associated with a prefix. In releases where SHA-512 and BLAKE3 entries were stored in the same table, a legacy table cannot be losslessly split after the fact. V2 clients therefore import a legacy peer's prefixes into both namespaces as *ambiguous hints*. This can create false-positive availability results, but must never bypass full digest verification after download.

Likewise, an old local cache cannot safely be partitioned by algorithm. On upgrade, the client discards the unversioned cache and rebuilds its hashfield from locally present optional files after verifying them against the manifest. New caches persist a versioned, per-algorithm representation and also retain the untyped compatibility projection for downgrade support.

## Integrity and security rules

- A hashfield match is not proof of possession. Always verify the complete digest and file size after downloading.
- Never use a 16-bit prefix as an integrity check, authorization decision, or content identity.
- Never reinterpret an explicitly versioned unknown payload as legacy.
- Reject malformed odd-length byte fields, fields larger than the namespace capacity, unknown algorithm names, and unsupported protocol versions.
- Legacy prefixes are inherently ambiguous. Keep that ambiguity visible in code and diagnostics; do not label them as verified SHA-512 or BLAKE3 possession.
- V2 typed fields use network byte order. The legacy field remains host-native solely for compatibility with existing peers.

## Cache format

New local caches persist:

```python
{
    "version": 2,
    "hashfields": {
        "sha512": "<base64 of sorted big-endian uint16 values>",
        "blake3": "<base64 of sorted big-endian uint16 values>",
    },
}
```

The site settings cache retains the old `hashfield` entry as a legacy untyped union and adds `hashfield_v2` for algorithm-aware restoration.

## Test coverage

The peer tests cover:

- equal 16-bit prefixes in SHA-512 and BLAKE3 remain distinct in v2;
- v2 encoding/decoding and persisted cache round trips;
- old unversioned payloads remain usable as ambiguous availability hints;
- the legacy projection contains prefixes from both algorithm buckets;
- unknown versions and malformed v2 fields are rejected;
- v2 lookups preserve algorithm identity;
- old-style raw-prefix lookups can still discover BLAKE3 entries through a v2 server.

The repository's full test suite and cross-version integration matrix must still be run before release. A static code change or passing unit test is not evidence of interoperability with every deployed legacy peer revision.
