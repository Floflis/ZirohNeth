# Content filtering, blocklists and migration inheritance

**Status:** design study; no runtime implementation is claimed by this document.  
**Date:** 2026-11-21  
**Scope:** historical ZeroNet behavior, shared-blocklist limitations, and a proposed ZirohNeth policy for carrying a user's v1 blocks across a verified v1 → v2 migration.

## 1. Executive summary

ZeroNet did not solve abusive or illegal publishing by making the peer-to-peer network globally censorable. It gave each client controls for deciding which sites and users it would display, retain or redistribute. The original client added the ContentFilter plugin in ZeroNet 0.6.3 (2018-06-26), explicitly advertising shared site and user blocklists.

The historical design is useful precedent, but it is not a complete trust-and-safety system:

- A site block is a local client decision, not deletion from the network.
- Shared lists are opt-in inputs to a user's local policy, not a network-wide authority.
- SHA-256 of a site address can represent a blocklist key, but it is not a content-matching system and does not make a known-format address secret.
- The historical public catalog proves that several lists were published or advertised. It does not prove that their sites, peers, maintainers or entries remain active or accurate today.
- A protocol migration must not silently bypass a user's existing filters. ZirohNeth should inherit a v1 block onto its corresponding v2 identity when the user has enabled the list containing that v1 identity.

**Core proposed rule:** if an enabled blocklist blocks a v1 site identity, ZirohNeth must also block the v2 site identity that is cryptographically proven to be its migration successor. This is a client-side policy inheritance rule. It does not globally delete either identity or force other users to adopt the same list.

## 2. Historical ZeroNet behavior

### 2.1 ContentFilter introduction

The official ZeroNet changelog for version 0.6.3, dated 2018-06-26, lists a new ContentFilter plugin that supports shared site and user blocklists.

Primary references:

- [ZeroNet releases: v0.6.3](https://github.com/HelloZeroNet/ZeroNet/releases/tag/v0.6.3)
- [ZeroNet ContentFilterPlugin.py](https://github.com/HelloZeroNet/ZeroNet/blob/master/plugins/ContentFilter/ContentFilterPlugin.py)
- [ZeroNet ContentFilterStorage.py](https://github.com/HelloZeroNet/ZeroNet/blob/master/plugins/ContentFilter/ContentFilterStorage.py)

The plugin has three principal data groups in its local filters.json:

| Key | Meaning |
|---|---|
| siteblocks | Site addresses blocked by this client |
| mutes | User/authentication addresses whose content should be muted |
| includes | Shared filter files the user has explicitly included |

The storage implementation also migrates the old site_blacklist key to siteblocks, and the old mutes.json file to filters.json.

### 2.2 Local blocks and shared includes

A site block records a site address, timestamp and optional reason. The plugin exposes add, remove and list operations, with administrative permission checks for those management operations.

Shared filters are not automatically trusted merely because they exist on the network. A user adds an include by specifying a ZeroNet site address and an inner path. The client loads the referenced JSON and merges its siteblocks and mutes entries into the effective included-filter sets. The UI asks for confirmation when a non-admin user adds a shared filter, showing the number of site and user entries.

The local include record retains the source site address, inner path, description and date added. When the included file is updated, the plugin rebuilds the merged sets. Removing an include removes its contribution from the effective policy; local entries remain separate.

This creates a useful separation:

1. A publisher can maintain a list.
2. A user can choose whether to subscribe to it.
3. The client combines selected lists with local rules.
4. The user can remove the subscription or override local decisions.

A shared list therefore has influence only because the user opted into it. It is not a global consensus mechanism.

### 2.3 How site blocking was applied

The original plugin checks the requested site address and, if it is blocked, renders a local blocklisted page instead of the requested site. The blocklisted page is a client response; it does not remove the site from peers or from other users' storage.

The source also contains an important implementation nuance: the request wrapper first checks whether the site is already present in the local site manager. If it is, the wrapper delegates to the normal request path before evaluating the blocklist. This means the historical code should not be described as a universal, all-path access-control boundary. A modern implementation should enforce the effective policy consistently at navigation, lookup, serving, pinning, downloading and redistribution boundaries, with explicit exceptions only where required for safe metadata resolution.

### 2.4 User muting

The plugin separately supports muting authentication addresses. Its storage code scans paths for user-address components and suppresses files associated with muted users. This is conceptually different from blocking a whole site: a site may contain content from many users, while a mute targets one contributor identity.

ZirohNeth should preserve this distinction. Site blocks, user mutes, peer abuse controls and file-level safety matching are different policy dimensions and must not be conflated.

## 3. Address hashes are not content hashes

The original ContentFilter code also checks a SHA-256 representation of the requested site address. In the historical implementation, the key is formed as:

~~~text
"0x" + SHA256(site_address).hexdigest()
~~~

The plugin checks both the plain address and this prefixed digest against the site-block set. The source uses the address bytes as input (the code was written for the Python 2-era runtime).

This is an address-obfuscation / alternate-key mechanism, not a scanner for the bytes hosted by a site.

| Identifier | What it identifies | What it does not prove |
|---|---|---|
| Site-address SHA-256 | A known site address, represented as a digest | That the site's files are illegal or harmful |
| File digest | A particular byte sequence | That every re-encoding or modified copy is the same file |
| Perceptual/content-matching hash | Similarity to a known media item, depending on the scheme | Legal status, context or identity of the publisher |
| Migration proof | An authenticated relationship between old and new site identities | That either site is safe or should be trusted |

Hashing an address does not guarantee secrecy. Public addresses are enumerable and their format is known, so candidate addresses can be hashed and compared. A hash-only list can still be reverse-matched by someone who knows or enumerates the address space.

Do not describe the historical ZeroNet mechanism as a known-illegal-content hash database. The inspected plugin code implements site-address blocks and user mutes, not a perceptual media-matching service.

For any future file-level matching system, ZirohNeth would need a separate specification covering authorized databases, privacy, false positives, jurisdiction, appeal, access controls and the danger of turning match identifiers into a discovery index. This study does not propose publishing raw illegal material, samples, URLs or a browsable catalog.

## 4. Historical public blocklist catalog

The community-maintained [Awesome ZeroNet catalog](https://github.com/zolagonano/awesome-zeronet#block-lists) lists the following historical entries:

| Name in catalog | Advertised purpose | ZeroNet address |
|---|---|---|
| Privact blocklist | Sites with external files | 18zoKfKYPnVBuHtKpK1mhAuVsWXV72obA1 |
| Kaffie's Spamlist | Spam / user mute-ban list | 1CufK1ZtvekbFXEpSyKT2gDjf9jnqW8KwG |
| Pornography blocklist | Pornography category | 13CgSQeywg2ius5pjXVCk7dKUCRkz5xvW3 |
| NoMiner blocklist | Sites reported to contain miners | 1NominErMMEodukCTKD5NN6HqgmtsG4Z8U |
| 0net-preview blocklist | Proxy-specific blocklist | 16soWyYc1kTobaevbN25FJjWL2qf9PWvFG |

These are catalog entries, not endorsements. In particular:

- A pornography category is not equivalent to criminal content. Legal adult material and abusive material must not be treated as the same category.
- A list may be incomplete, outdated, abandoned, compromised or inaccurate.
- The catalog's existence does not establish that an address currently resolves, has serving peers, or publishes fresh signed updates.
- The purpose labels above are transcribed from the community catalog and have not been independently validated against each list's current contents.

### 4.1 Are any lists still maintained?

As of this study date (2026-11-21), the available evidence establishes the historical catalog entries but does **not** establish that any of the five lists is currently and regularly maintained. A recently crawled copy of the catalog is not proof that the underlying ZeroNet zite is alive or that its entries are current.

Therefore ZirohNeth should not ship these addresses as trusted defaults. They may be retained as historical research references only. If a user chooses to import a list, the client should display its current availability, publisher identity (if verifiable), last successful update, signature status and declared purpose without implying that those fields establish correctness.

## 5. Why blocklists can become discovery indexes

A plain-text blocklist can unintentionally advertise the very destinations it intends to suppress. Anyone who reads it may obtain a ready-made list of addresses. Hashing addresses can reduce casual exposure, but it is not a reliable secrecy boundary when candidate addresses are enumerable.

The more important control is to separate policy evaluation from discovery:

- The UI should show that a policy matched, its source list and a safe reason/category.
- It should not render blocked destinations as clickable suggestions or expose a browseable directory of blocked sites.
- Diagnostic exports should be opt-in and redact addresses by default.
- A list's publisher should not gain the ability to make a client fetch every blocked site.
- Importing a list should not automatically visit or download all listed destinations.

A blocklist is a set of policy inputs, not a recommendation feed.

## 6. Proposed ZirohNeth model

### 6.1 Policy layers

Keep policy sources distinct and composable:

1. **LocalBlocklist:** private rules created by the user.
2. **CommunityBlocklists:** explicitly enabled, independently signed lists.
3. **UserMutes:** contributor-level filtering, distinct from site-level blocking.
4. **PeerAbuseControls:** rate limits, request quotas, storage controls and anti-flood mechanisms.
5. **OptionalContentMatching:** a separately governed future capability, not an extension of site-address hashing.

Each rule should retain provenance: source list, publisher/signature identity, source revision or content digest, timestamp, category, reason code and expiry/review metadata where available. A list update must not silently erase local rules or local overrides.

### 6.2 Mandatory v1 → v2 block inheritance for enabled lists

**Requirement:** if a user has enabled a blocklist and that list blocks a v1 site identity, the corresponding v2 site identity must also be blocked for that user.

This prevents a site from escaping the user's existing choice merely by migrating from its legacy Bitcoin-addressed v1 identity to its Ethereum-addressed v2 identity.

The relationship must be established by the project's authenticated migration mechanism, not by name similarity, operator claims, DNS, matching page titles or an unverified redirect.

The current migration design records a dual-signed migration proof in the terminal v1 root manifest and verifies the relationship between the old Bitcoin identity and the new Ethereum identity. The filtering design should consume that verified relationship.

#### Required evaluation

Given:

- an enabled list L;
- a v1 identity A1;
- a v2 identity A2;
- a cryptographically verified migration relation M(A1, A2);

the effective decision is:

~~~text
blocked(A2) =
    directly_blocked(A2)
    OR exists A1:
         verified_migration(A1, A2)
         AND blocked_by_any_enabled_list(A1)
~~~

This is additive: a direct v2 block remains effective even when no v1 predecessor is known. A v1 block is inherited only across a verified migration edge.

#### Resolution and privacy requirements

- Do not fetch the full v2 site to determine whether its v1 predecessor is blocked.
- Prefer a small, authenticated migration-proof envelope available from the v2 root manifest or an independently retrievable proof record. The current v1-terminal-manifest proof remains authoritative; mirroring its digest/reference into v2 is a design option that needs protocol review.
- If the client only knows the v2 address and has no verified migration proof, it must not guess the predecessor. It may perform a narrowly scoped metadata/proof lookup, subject to network privacy policy, but must not download or render the site body first.
- Cache verified lineage locally, bound to the proof digest and protocol version. Invalidate or re-evaluate the cache if the verified migration checkpoint changes or conflicts.
- Apply inherited blocking before normal content download, rendering, pinning or redistribution.
- Show a neutral explanation such as: “Blocked because a v1 identity for this site is present in a blocklist you enabled.” Do not expose the blocked v1 address in public UI by default.
- Keep the user's list selection local. Do not broadcast which lists the user has enabled.
- Removing or disabling the source list should remove only the inherited contribution from that list. A separate local/direct v2 block must remain.
- If multiple enabled lists block the same v1 identity, retain all matching provenance records so removing one list does not accidentally unblock a site still blocked by another.
- If a v2 identity has multiple verified legacy predecessors, evaluate every predecessor. Any predecessor blocked by an enabled list makes the v2 identity blocked.
- If migration history forms a chain, evaluate the verified ancestry graph, with cycle detection and bounded traversal. A block on any verified ancestor should inherit to the successor unless the user explicitly disables that inheritance policy.
- A migration proof must never be treated as a safety endorsement. It proves identity continuity, not legitimacy.

### 6.3 Policy precedence and user control

Recommended precedence:

1. Security-critical client protections cannot be disabled by a site or list publisher.
2. A block from any enabled community list contributes a block.
3. Local blocks contribute independently.
4. A user's explicit override may override a community-list contribution only if the product deliberately supports that choice and makes the consequences clear. It must not silently erase the underlying list entry.
5. A direct local block should require an explicit local removal; disabling an unrelated list must not remove it.

The UI should make it clear whether a block is direct, inherited from a v1 predecessor, or contributed by one or more enabled lists.

### 6.4 Compatibility

- Existing v1 addresses and historical blocklist entries must remain interpretable.
- Accept the original plain address and the legacy 0x + SHA-256(address) representation when importing compatible historical lists.
- Do not reinterpret an address digest as a file digest.
- Keep v1 blocklist compatibility separate from v2's identity encoding and content digest algorithms.
- Never make legacy clients understand v2 migration proofs by changing the v1 protocol. Newer clients enforce the inherited policy locally.
- A v1-only client cannot be expected to recognize or block a v2 successor it does not understand.

## 7. Threats and failure cases to test

| Case | Expected behavior |
|---|---|
| Enabled list blocks v1; valid proof links v1 → v2 | Block v2 before normal content retrieval |
| Enabled list blocks v1; proof is missing | Do not infer lineage; resolve only bounded authenticated metadata or explain that inheritance cannot yet be established |
| Proof signature or binding is invalid | Reject the relation; never use it to inherit a block |
| v2 address is directly blocked | Block it regardless of migration metadata |
| Two enabled lists block the same v1 | Preserve both provenance records |
| One list is removed but another still blocks v1 | v2 remains blocked |
| List update removes the v1 entry | Recompute inherited decisions; retain any independent local/direct v2 block |
| Multiple verified v1 ancestors lead to one v2 | Any blocked verified ancestor contributes a block |
| Malicious site claims an unrelated v1 predecessor | Reject unless the migration proof verifies against the protocol's trust and checkpoint rules |
| User opens a blocked site already cached locally | Block consistently; cached presence must not bypass policy |
| Peer asks this client to serve blocked content | Apply the documented local serving/redistribution policy consistently |
| List contains malformed or hostile entries | Reject invalid schema; bound parsing, sizes and update work |
| List is stale, unsigned or publisher key changed | Surface trust/update status; do not silently treat it as freshly verified |

## 8. Implementation work still required

This document is a study and design proposal, not an implementation. Before coding:

- Audit the current ZirohNeth ContentFilter fork against the exact upstream source and current branch.
- Decide the signed list format, canonicalization, publisher-key rotation and revocation rules.
- Define whether a v2 manifest embeds the migration-proof envelope or a content-addressed reference to it.
- Define a bounded, privacy-preserving way to resolve lineage when a v2 site is visited first.
- Centralize the effective block decision so UI, API, cache, download, pinning and serving paths cannot disagree.
- Add tests for direct blocks, inherited blocks, list removal/update, multiple lists, multiple ancestors, invalid proofs, stale checkpoints and already-cached sites.
- Verify behavior for both Python legacy clients and future Rust-native clients without silently changing v1 wire formats.

## 9. Sources

1. [HelloZeroNet/ZeroNet v0.6.3 release notes](https://github.com/HelloZeroNet/ZeroNet/releases/tag/v0.6.3) — introduction of ContentFilter.
2. [ContentFilterPlugin.py](https://github.com/HelloZeroNet/ZeroNet/blob/master/plugins/ContentFilter/ContentFilterPlugin.py) — site blocks, user mutes, shared include actions, request wrapper and address SHA-256 check.
3. [ContentFilterStorage.py](https://github.com/HelloZeroNet/ZeroNet/blob/master/plugins/ContentFilter/ContentFilterStorage.py) — local storage, include merging, mute handling and block lookup.
4. [Awesome ZeroNet: Block lists](https://github.com/zolagonano/awesome-zeronet#block-lists) — historical community catalog and advertised purposes.
5. [ZeroNet FAQ](https://www.zeronet.io/docs/faq/) — the original project's explanation that users control what they host and can stop hosting a suspicious site.
6. [ZirohNeth Content v2 migration ToDo](ToDo.md#bitcoin--ethereum-migration) — current project checklist describing the dual-signed migration proof and its embedding in the terminal v1 manifest.

---

**Decision captured:** ZirohNeth should preserve user-selected v1 blocklist decisions across a cryptographically verified v1 → v2 migration. This is local policy continuity, not network-wide censorship.
