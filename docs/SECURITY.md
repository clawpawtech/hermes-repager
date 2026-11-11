# Security and explicit limits

## Trust boundaries

- Plugin registration starts no browser, model request or data directory. Runtime is lazy and keyed by the active Hermes home. Tools and dashboard use the same service and profile-scoped state.
- The native dashboard supplies authentication/profile/trust scope. The standalone development app is loopback-only, requires a generated token, validates Host, rejects cross-origin changes and serves no credentials to JavaScript. Cookie auth is HttpOnly and SameSite=Strict. It is a development surface, not production remote hosting.
- Capture accepts public HTTP(S) URLs on standard ports, without userinfo or control/normalization bypasses. A loopback HTTP/CONNECT proxy resolves all addresses, rejects mixed/non-public DNS, then dials a numeric public address. Redirects and subresources use the same policy. Browser routing blocks unsafe schemes/methods, service workers, WebSockets, downloads and popups. QUIC/direct WebRTC egress is disabled.
- Preview contexts disable JavaScript at the browser level, block all resource requests, share no source profile/cookies and use a deny-all proxy. Verification measures actual rendered text, href, Tab-key focus, dimensions and network attempts. Deliberately hostile fixtures test the controls; they are not live customer evidence.
- The renderer consumes a closed schema, validates source references/palette, escapes text/attributes and emits trusted fixed CSS. Source text is explicitly untrusted model input, not instructions. No source scripts, arbitrary generated markup, remote packages or credentials reach the preview.
- A plugin-owned, owner-only local HMAC key signs captured metadata/source image hashes, immutable revision metadata and verification receipts. Screenshot and HTML bytes are rehashed before serving/export. The key is never exported or sent to a model. This protects local record/file integrity, not against a malicious owner controlling the host and key; exported HMACs are not public-key attestations.
- SHA-256 binds exact UTF-8 artifact bytes. Receipts also bind the latest revision and approval contract. Immutable check-specific screenshot names avoid overwriting old evidence. Reapproval or generation invalidates current verification. Export rechecks hashes and uses a controlled allowlist, rejecting symlink artifacts.
- Interrupted unrecorded revision files are quarantined before retry, without overwriting recorded revisions. Failed save acknowledgements never delete potentially committed HTML. Capture DNS resolution runs only inside the timed, killable worker/proxy.
- JSON writes are atomic and fsynced. Reentrant path-shared thread locks and advisory process locks cover mutations. Optimistic versions reject stale writes; corrupt records are not silently overwritten. Identity-first discovery retains recovery rows for unreadable/malformed records and head-only interrupted creation; a damaged head does not break healthy gallery rows.

## Current integrity and verification (introduced in 0.2, strengthened in 0.3)

Approval is now independently signed, not trusted just because a later revision is signed. A sealed current-record head and two-state before/after publication journal reject record-only editing and rollback while recovering failed-save/lost-acknowledgement cases. All retained revision metadata and HTML are rechecked before a handoff. This is **not an external monotonic anchor**: restoring both data/head/key from a full backup restores that backup, and the host owner holding the key is outside the guarantee.

Current decisions and handoffs require protocol 2 and all 29 exact check IDs. Legacy/incomplete receipts remain inspectable but are not current export authority. Computed contrast, exact observed DOM copy, CTA size and representative clipping/occlusion tests strengthen the old geometry checks; unsupported backdrops remain unknown and these do not establish full accessibility or universal perceptibility. Failed checks permit a reasoned reject/undecided choice, never prefer or implementation export; a labeled passive failure report remains available. New approval, revision or check invalidation clears current authority; independently sealed review events retain superseded receipts, images and reasons. Decisions bind the specific receipt signature. Old current evidence can migrate once, but already-discarded older history is not reconstructed. The 500-event cap precedes model/browser work. Stale approval requests must match the displayed record version, separately from the stable source scope hash. Human choices are not deployment permission.

Local remixes/restoration use the same immutable publisher, signed scope and stale revision/hash guards without inference. Manual unreadable colors are refused. Model text-color repairs use only declared neutral colors and are recorded explicitly. Reports escape captured data, validate complete PNGs and embed the exact hash-bound evidence; no scripts or external dependencies. Downloaded reports intentionally contain public captured text/screenshots and source URLs.

Inference requires the explicit auxiliary task provider/model and canonical empty fallback lanes; no main-model inheritance, known free/auto aliases, truthy/falsy type shortcuts or task fallback chain. Returned-route audit adds detection after dispatch, not a way to undo a call or verify a provider's billing/transport independently. The plugin never changes live configuration.

## Not an OS sandbox

Application controls are **not** a hardened browser-exploit containment boundary. Use a dedicated low-privilege container/VM with appropriate network/filesystem policy for hostile sites. Chromium OS sandboxing is on by default. The acceptance-test container could not launch it; those live tests explicitly opted out and disclose that fact. Never describe that opt-out as equivalent isolation.

HTTPS CONNECT tunnel contents are opaque to the proxy. WebSocket/unsafe-method restrictions depend on Chromium context controls inside TLS. Browser vulnerabilities, new transports or unsupported flags remain residual risks. This is not a multi-tenant public capture service.

New source captures retain the nearest semantic main/section container identity. The selected heading must itself be in the supported hero, and selected paragraphs/CTA must match that container. Legacy signed evidence without a container ID is retained as captured, not silently upgraded. Native and dashboard expensive operations share process-local admission; independent Hermes processes do not share a machine-wide semaphore.

Source rendering waits at most eight seconds for a supported, unobscured semantic heading/paragraph/CTA group before freezing CSS/collecting DOM. This avoids known client-render races, not arbitrary app completion. Timeout does not invent content or substitute a fixture; unsupported captures still fail visibly.

## Capture and product limits

Desktop/mobile are separate fresh navigations and can differ over time. Screenshot and DOM are sampled in the same viewport pass, not claimed atomically simultaneous. CSS animations/transitions are frozen. Blocked resources can change appearance. The collector bounds candidate inspection, visible elements, text lengths, palette size, proxy connections/bytes/time and input size; truncation is disclosed.

Only first-screen h1/h2/p/a content is supported. A narrow semantic hero is required for proposals. No OCR, full-page crawl, arbitrary SPA/framework support, login/captcha bypass or full-site clone. Captured whitespace is normalized; preservation refers to the selected snapshot text and CTA, not source HTML bytes or all page content.

Checks do not establish visual effectiveness, conversion uplift, SEO rank, full accessibility compliance, brand fidelity or production readiness. Vertical scrolling alone is not reported as a layout defect. Unknown results remain explicit; any failed or missing required check blocks handoff.

## Model consent and routing

Only host `ctx.llm.complete_structured` is used. repager never reads provider credential files or creates a provider client. Model-data consent is off by default. The URL, bounded public text and user brief go to the configured host provider after approval. The plugin's no-free preflight refuses configured free routes and auto/ambiguous primary routing. The isolated acceptance profile explicitly pinned openai-codex/gpt-6.1-sol with no fallback chain; no global routing was changed.

## Operations

Local capture data and exports have no automatic retention policy. Treat them as sensitive if the supplied URL or visible content is sensitive. Jobs are bounded and process-local, without an instant-cancellation claim. Do not expose the development server remotely. Long temporary-directory paths can exceed Chromium's Unix socket budget; use the trusted `browser_temp_dir` setting, not a global temp-directory workaround.
