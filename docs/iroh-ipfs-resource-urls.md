# 🌈 Iroh-first and optional IPFS resource URLs

> **Status:** architectural proposal / implementation plan. This document describes intended behavior, not functionality already available in the current ZeroNet Conservancy codebase.

## 1. Goal

Allow a ZirohNeth site to reference content stored on peer-to-peer networks other than the ZeroNet site network, without requiring the site itself to be hosted on those networks.

For example, a site hosted and signed as a normal ZeroNet site should be able to include:

```html
<img src="ipfs://bafy...">
<a href="iroh://<blob-hash>">Open a document</a>
```

The page remains a ZeroNet site. ZirohNeth resolves the external resource URL, retrieves its bytes from the corresponding network, and exposes the result to the browser's ordinary resource-loading pipeline.

The key distinction is **resource interoperability, not site migration**.

## 2. Design principles

1. **Iroh first:** Iroh is the native/default peer-to-peer resource network for ZirohNeth.
2. **IPFS optional:** IPFS support is an optional adapter/backend. A node that does not enable IPFS must still work normally with ZeroNet and Iroh resources.
3. **Protocol-neutral browser experience:** HTML authors use URLs in attributes such as `src`, `href`, `poster`, and CSS `url()`; the runtime handles resolution.
4. **No mandatory gateway dependency:** Prefer direct peer-to-peer retrieval through the enabled backend. Public HTTP gateways may be an explicit fallback policy, never a silent requirement.
5. **Integrity before use:** Verify content against the identifier's hash/CID before exposing it to the page.
6. **Graceful degradation:** Missing providers, disabled backends, unsupported schemes, or failed retrievals should produce ordinary resource errors, not crash the site or node.
7. **Explicit trust boundaries:** A ZeroNet site's signature authenticates that site's manifest and references. It does not automatically certify the publisher, safety, or availability of an external Iroh/IPFS object.

## 3. URL schemes and addressing

### 3.1 Iroh (default)

Proposed author-facing form:

```text
iroh://<iroh-blob-hash>
```

Iroh is the preferred native backend. The implementation should use the Iroh blob addressing and discovery APIs supported by the selected Iroh version, rather than inventing a parallel content-addressing format.

The exact URI grammar must be finalized against the Iroh APIs and addressing model selected during implementation. In particular, distinguish a content hash from a peer identity or endpoint: a blob identifier names content, while peer identifiers and discovery information help locate providers. Do not overload one field to mean both.

Potential future extension: define a versioned URI form if the selected Iroh API requires additional namespace or format information. Keep the simplest stable form as the default where possible.

### 3.2 IPFS (optional)

Proposed author-facing form:

```text
ipfs://<cid>
ipfs://<cid>/<path/inside/directory>
```

The CID identifies the IPFS object or DAG root. A path may select a file within a UnixFS/IPLD structure. The resolver must preserve path semantics and must not treat arbitrary path text as part of the CID.

IPFS support should be packaged or configured as an optional backend. If it is disabled, an `ipfs://` resource should fail clearly and predictably; it must not silently be fetched from an unrelated network.

### 3.3 Ordinary URLs remain ordinary

- Relative URLs continue to resolve against the ZeroNet site's own origin/base URL.
- `http://` and `https://` retain their normal behavior and applicable security policy.
- `data:` and `blob:` retain browser-defined behavior.
- Unknown schemes are rejected or left to explicitly registered handlers. Never reinterpret an unknown scheme as a filesystem path.

## 4. Resolution architecture

The intended flow is:

1. The browser requests a resource from a page, stylesheet, script, media element, or navigation link.
2. The ZirohNeth browser integration or local resource bridge detects a supported `iroh://` or `ipfs://` URL.
3. A scheme dispatcher selects the Iroh backend or the optional IPFS backend.
4. The backend resolves providers and retrieves the requested object using its native peer-to-peer protocol.
5. The runtime verifies the retrieved bytes against the requested content identifier and enforces configured size/resource limits.
6. The runtime determines a safe media type and returns the bytes through a browser-compatible response channel.
7. The browser renders or downloads the resource as it would any other resource.

Conceptual flow:

```text
ZeroNet HTML / CSS / JS
        |
        | src="iroh://..." or href="ipfs://..."
        v
ZirohNeth resource bridge
        |
        v
Scheme dispatcher
   |             |
   v             v
Iroh backend   IPFS backend (optional)
   |             |
   v             v
P2P retrieval  IPFS retrieval
   |             |
   +------v------+
          |
   hash / CID verification
          |
   MIME + policy checks
          |
   browser response
```

The current ZeroNet codebase is Python-based. The architecture should keep the browser-facing bridge narrow and define a backend interface so a future Rust-native Iroh implementation can replace or sit behind it without changing site-authored URLs.

## 5. Browser integration options

The implementation must choose and document one supported integration path:

- **Local HTTP resource bridge:** rewrite or intercept supported URLs and serve verified bytes from a local ZirohNeth endpoint. This is likely the most compatible initial path for existing browsers.
- **Browser-native protocol handler:** register custom schemes only where the browser/runtime supports secure, controllable protocol handlers.
- **Controlled browser engine integration:** use a browser engine's request interception/resource loader when ZirohNeth ships or controls the browser runtime.

Do not assume that a normal web page can make arbitrary browsers load `ipfs://` or `iroh://` directly. Browsers generally do not understand these schemes by default. A bridge or registered protocol handler is required.

For a first implementation, favor the least invasive mechanism that works with the project's supported browsers. Avoid modifying every HTML file on disk. If rewriting is necessary, it should happen in the response/request layer and preserve the original signed site content.

## 6. HTML and CSS coverage

The goal is to support resource-bearing locations consistently, not just `<img>`.

Initial coverage should include:

- HTML: `img[src]`, `source[src]`, `video[src]`, `audio[src]`, `video[poster]`, `track[src]`, `object[data]`, and navigational `a[href]`.
- Stylesheets: `url(...)` in CSS, including backgrounds and fonts.
- Modern markup: `srcset` and `imagesrcset`, with each candidate resolved independently.
- Script-initiated requests: `fetch()` and XHR only if the browser bridge can support them without weakening origin and CORS protections.

The initial milestone may limit support to passive resources and navigational links. Document any unsupported contexts instead of pretending all URL-bearing attributes work automatically.

## 7. HTTP semantics exposed to the browser

The bridge should provide browser-compatible responses, including where practical:

- Correct `Content-Type` based on verified metadata or safe sniffing policy.
- `Content-Length` when known.
- `ETag` or an equivalent stable validator derived from the content identifier.
- `Cache-Control` consistent with immutable content addressing.
- Byte-range responses for media playback and large files, if supported by the backend.
- Clear status mapping for not-found, unavailable, disabled backend, invalid identifier, integrity failure, and policy rejection.

A content-addressed object is immutable by identifier. Cache entries can therefore be keyed by normalized scheme + identifier + path (for IPFS directory paths), while respecting storage quotas and user deletion controls.

## 8. Security and privacy

External P2P resources are untrusted input, even when referenced by a signed ZeroNet site.

Required safeguards:

- Verify the full content identifier before returning content to the browser.
- Enforce maximum download size, decompression limits, timeouts, concurrency limits, and per-site resource budgets.
- Reject malformed identifiers and path traversal attempts.
- Normalize and validate IPFS paths; never map them directly to local filesystem paths.
- Apply browser origin isolation and CORS rules. Do not grant an external resource the ZeroNet site's origin merely because the site referenced it.
- Apply Content Security Policy (CSP) and mixed-content rules consistently. Define whether custom schemes are mapped to a dedicated opaque/local origin.
- Prevent redirects from escaping the selected backend or silently switching protocols.
- Do not leak the user's IP address or peer identity to arbitrary sites without a clear network/privacy policy and user configuration.
- Make public gateway fallback opt-in and visible. A gateway can observe requested CIDs and the user's network address.
- Treat MIME types as untrusted; use safe download behavior for ambiguous or executable content.
- Keep external resource retrieval separate from ZeroNet site signing and update authorization.

A signed `content.json` proves the site's authorized publisher referenced a URL. It does not prove that the external object is benign.

## 9. Discovery, availability, and fallback

The resolver should distinguish:

- **Object identity:** the hash or CID requested.
- **Provider discovery:** how peers that can serve the object are found.
- **Transport:** how bytes are transferred from a provider.
- **Fallback:** whether another configured source may be tried.

Iroh should use its native discovery and transport facilities. IPFS should use its own compatible discovery and retrieval stack. Do not assume that Iroh peers and IPFS providers are interchangeable.

Suggested policy:

1. Try the selected native backend.
2. Retry according to bounded timeout/backoff policy.
3. If configured, try additional peers/providers for the same backend.
4. If the user explicitly enabled an HTTP gateway fallback, try an approved gateway and still verify the returned content.
5. Otherwise return a clear unavailable-resource response.

Never convert an Iroh identifier into an IPFS CID or vice versa unless a separately specified, verified mapping mechanism exists.

## 10. Configuration and user experience

Suggested configuration surface:

- Iroh resource support: enabled by default.
- IPFS resource support: optional, disabled unless installed/enabled.
- HTTP gateway fallback: disabled by default; configurable per backend.
- Cache location and quota: configurable.
- Maximum object size and request timeout: configurable.
- Per-site permissions: allow, block, or ask before retrieving external resources, especially for large downloads or privacy-sensitive transports.

The UI should make it possible to inspect a resource's scheme, identifier, retrieval source, verification result, and cache status. Errors should identify whether the backend is disabled, no provider was found, retrieval timed out, or integrity verification failed.

## 11. Suggested implementation milestones

### M0 - Technical validation

- Select and pin the Iroh APIs/version and confirm the canonical blob identifier format.
- Select an IPFS implementation strategy that can remain optional.
- Prototype browser interception for `img[src]` and `a[href]` without changing signed site files.
- Validate behavior in every browser/runtime the project intends to support.

### M1 - Iroh passive resources

- Implement the resource bridge and Iroh backend.
- Support `iroh://` for images and basic downloadable files.
- Verify identifiers before serving bytes.
- Add bounded caching, timeouts, and useful diagnostics.

### M2 - Navigation and broader markup

- Support `a[href]`, CSS `url()`, media resources, and responsive image candidates.
- Add byte-range support where feasible.
- Document browser-specific limitations.

### M3 - Optional IPFS backend

- Add IPFS behind the same backend interface.
- Support `ipfs://<cid>` and directory paths.
- Ensure builds/installations without IPFS dependencies remain functional.
- Add explicit gateway fallback configuration, disabled by default.

### M4 - Policy, permissions, and hardening

- Add per-site permissions, quotas, privacy controls, and resource inspection.
- Test malformed identifiers, malicious content, path traversal, oversized objects, provider failures, and gateway fallback.
- Document operational and privacy trade-offs.

## 12. Acceptance criteria

- A ZeroNet-hosted page can load an image addressed by `iroh://...` without being hosted on Iroh.
- A ZeroNet-hosted page can load an image addressed by `ipfs://...` when the optional IPFS backend is enabled.
- Disabling IPFS does not break ZeroNet or Iroh functionality.
- The original signed ZeroNet site files are not modified merely to resolve external resources.
- Retrieved bytes are verified against the requested identifier before delivery.
- Resource failure does not crash the node or page.
- Browser origin, CSP, CORS, and privacy boundaries are documented and tested.
- The implementation clearly distinguishes planned behavior from supported behavior in each release.

## 13. Open design questions

- Which Iroh release/API and canonical blob-address format will be pinned?
- Should the first bridge be a local HTTP endpoint, browser-engine interception, or a combination?
- What origin should bridged resources receive in the browser security model?
- Which browser engines are in the initial support matrix?
- Should IPFS be a separate optional process, an optional library dependency, or a plugin?
- Which gateway providers, if any, may be configured, and how will their privacy implications be shown?
- Should sites be able to declare expected MIME types or resource size limits in their signed manifest?

These questions should be resolved during M0 before implementation is considered complete.
