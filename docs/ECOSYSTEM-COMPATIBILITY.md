# ZeroNet ecosystem compatibility inventory

Status: initial repository-level audit, 2026-11-18. This is a comparison inventory, not a claim that every upstream feature has been fully audited or ported.

## Scope and method

Compared the ZirohNeth repository tree with the public zeronet-conservancy/zeronet-conservancy tree and inspected public repository metadata for related projects. The Conservancy core repository is a fork of HelloZeroNet/ZeroNet; the current ZirohNeth tree contains the recognizable ZeroNet core layout and many of the same plugin directories.

This inventory records project-level gaps and likely parity targets. A matching directory name is not proof of matching implementation, behavior or upstream revision. Each component still needs a code-level diff and tests before being marked fully synchronized.

## ZeroHello

- Upstream: https://github.com/HelloZeroNet/ZeroHello
- Purpose: ZeroNet homepage / portal.
- ZirohNeth status: no ZeroHello project or equivalent standalone portal was found in the ZirohNeth repository tree during this audit.
- Decision needed: port the site, redesign it as a native ZirohNeth discovery/start page, or explicitly maintain it as an external companion. Do not silently assume the old portal is compatible with Ethereum identities or content v2.

## Related repositories in the ZeroNet-Conservancy ecosystem

| Repository | Upstream relationship / purpose | Initial ZirohNeth status |
|---|---|---|
| https://github.com/zeronet-conservancy/zeronet-conservancy | Core client fork of HelloZeroNet/ZeroNet | Core tree and plugin families are present; exact upstream parity is not established |
| https://github.com/zeronet-conservancy/0me | Microblogging platform; fork of HelloZeroNet/ZeroMe | No standalone 0Me application found in the ZirohNeth tree |
| https://github.com/zeronet-conservancy/0dashboard | Dashboard; fork of ZeroHello | No standalone dashboard found in the ZirohNeth tree |
| https://github.com/zeronet-conservancy/fid | New UI for ZeroNet-Conservancy | No separate FID application found in the ZirohNeth tree |
| https://github.com/zeronet-conservancy/znapi | JavaScript / TypeScript wrapper for the 0net API; described upstream as WIP | No standalone znapi package found in the ZirohNeth tree |
| https://github.com/zeronet-conservancy/is-v0.8-ready-yet | Tracks Conservancy v0.8 readiness | External project tracker; not a runtime component |
| https://github.com/zeronet-conservancy/aiobtdht | Async BitTorrent DHT support library | Dependency / networking compatibility review required |
| https://github.com/zeronet-conservancy/aioudp | Async UDP support library | Dependency / networking compatibility review required |
| https://github.com/zeronet-conservancy/aiokrpc | Async KRPC support library | Dependency / networking compatibility review required |
| https://github.com/zeronet-conservancy/pymerkletools | Merkle tooling library | Evaluate relevance to content integrity / future protocol work |
| https://github.com/zeronet-conservancy/rzhs0 | Archived repository | Archived; inspect only if a concrete dependency or feature reference is found |

Repository metadata at audit time:
- zeronet-conservancy/zeronet-conservancy: default branch main; fork of HelloZeroNet/ZeroNet.
- 0me: default branch master; fork of HelloZeroNet/ZeroMe.
- 0dashboard: default branch master; fork of HelloZeroNet/ZeroHello.
- fid and znapi: default branch main.
- The Conservancy core tree includes plugin families such as AnnounceBitTorrent, AnnounceLocal, AnnounceShare, AnnounceZero, Benchmark, Bigfile, Chart, ContentFilter, Cors, CryptMessage, FilePack, MergerSite, Newsfeed, OptionalManager, PeerDb, Sidebar, Stats, TranslateSite, Trayicon, UiConfig, UiFileManager, UiPluginManager and Zeroname. ZirohNeth's current tree contains these same broad plugin families, including several disabled plugins. This is directory-level evidence only; compare implementation commits and behavior before declaring parity.

## Immediate follow-up checklist

- [ ] Identify the exact ZirohNeth commit corresponding to the Conservancy core base and calculate a file-level diff against the selected upstream branch.
- [ ] Audit every plugin listed above for upstream changes, compatibility and security relevance.
- [ ] Audit ZeroHello and 0dashboard assets, APIs, site manifests and UX before choosing port / redesign / external companion.
- [ ] Audit 0Me as a social product reference, especially user content manifests, moderation, identity and migration assumptions.
- [ ] Review FID and znapi as possible UI and API integration layers, not automatically as code to vendor.
- [ ] Review aiobtdht, aioudp, aiokrpc and pymerkletools for dependency value, license, maintenance and protocol fit.
- [ ] Track each adopted change with upstream URL, source commit, local commit and tests.
- [ ] Mark intentionally omitted features with rationale so they are not rediscovered as accidental omissions.

## Compatibility policy

Do not copy upstream code blindly. For each candidate update, record:
1. upstream repository and exact commit;
2. affected files and behavior;
3. whether ZirohNeth has an equivalent;
4. required changes for Ethereum identities, BLAKE3/content v2 and the Tor policy;
5. tests and migration impact;
6. decision: port, adapt, replace, defer or reject.

The audit should be refreshed whenever the Conservancy core or a sibling project receives a relevant update.
