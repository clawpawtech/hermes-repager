# Implemented interfaces, version 0.3

JSON uses snake_case, UTC timestamps and UUID-hex review IDs. The server is authoritative; UI signature-shape checks are not cryptographic validation. Optional legacy metadata is preserved without injecting defaults into signed objects.

## Browser

`BrowserAdapter(executable_path=None, timeout=90, allow_no_sandbox=False, temp_dir=None)`

- `capture(url, output_dir)` returns source metadata, two fixed viewport screenshots, bounded elements, measured palette and limitations. Elements retain optional region/container identity. The bounded readiness predicate needs a supported heading, paragraph and navigable CTA outside navigation/header; representative hit tests exclude fully covered evidence. No consent/login bypass. Readiness timeout retains the real unsupported snapshot.
- Viewports may include up to 12 `overflow_elements`: candidate rectangles, text, tag and `in_hero`, not causal proof or a production fix.
- `verify(html, expected_cta_url, output_dir, *, expected_copy=None)` returns `protocol: 2`, 29 checks, two screenshots and limitations. `expected_copy` contains `headline`, ordered `bodies`, and `cta_label`; absent expectations yield unknown copy checks, not invented matches.
- Protocol 2 retains the original 13 checks and adds, per viewport: `headline-copy`, `body-copy`, `cta-label`, `heading-contrast`, `body-contrast`, `cta-contrast`, `cta-target`, `cta-complete`. All exact IDs are required centrally. Contrast uses computed opaque colors, not source-code inspection; unsupported backdrops are unknown. Target policy is 44 × 44, not a blanket accessibility certification.
- No network/script/credential environment in proposal contexts; bounded JSON stdin/stdout, independent URL and HTML-byte limits, no sample fallback or automatic browser installation.

## State and integrity

`ReviewStore(root)` retains POSIX reentrant/advisory locks and optimistic versions. `RecordJournal` wraps service create/save/read with an independently HMAC-sealed `.head.json`. A pending head binds both legitimate before/after states; under the same record lock, recovery selects the state actually published. It detects record-only editing and rollback, not a host owner or restoration of a full snapshot including its head/key. `updated_at` is store-owned cosmetic metadata outside the head digest; source/check/approval timestamps remain bound inside their signed objects.

Capture records a `capturing` identity before navigation. Interrupted work remains discoverable, not declared completed. Job history is process-local; a restart does not resume an interrupted browser/model operation automatically. Saved evidence survives.

`ReviewService`:

- `create_review(url,audience='',goal='')`; unsupported and failed attempts retain an explicit reason.
- `get_review(id)`, `list_reviews()` authenticate head and history metadata. A damaged saved review is flagged for recovery, not shown as trusted evidence. Gallery reads can wait on a busy record; the UI queries jobs first so reconnection does not wait for that gallery lock.
- `preview_scope(id)` exposes exact heading/body/CTA selections, optional real `anchors` per viewport, a stable hash of the complete displayed source scope and `record_version` for optimistic approval. Missing mobile matches are not manufactured.
- `approve(id,finding_id,*,cta_id,scope_hash,expected_version,preserve_copy=True,preserve_destination=True)` signs review/source/scope identity, exact IDs, CTA text/destination and time. Both preservation flags and the exact displayed integer record version are mandatory. Stale approval is a conflict, not an implicit refresh. Unsigned legacy approvals require explicit reapproval. Every operation revalidates the signed scope against current captured evidence.
- `generate(id,instruction='')` uses host structured output only. Four sanctioned layouts: stack, split, editorial, spotlight. Model-selected unreadable text colors are deterministically changed only to approved neutral black/white, with signed `safety_adjustments`; invalid out-of-palette values are not laundered. Manual rendering remains strict. Provider/model attribution is recorded.
- `remix(id,*,base_revision,artifact_hash,changes,from_revision=None)` creates a new immutable revision without inference. `changes` permits only layout, alignment, spacing, background, foreground, accent and button_text. Empty changes are legal only for an explicit historical restoration. Current baseline/hash, same approval, historical integrity and no-op guards apply. Source IDs/copy/destination are not editable. Local revisions record `origin: local-remix`, null model/provider and their `parent_revision`.
- `verify(id)` invalidates receipt/choice first, checks exact current bytes/contract and all required protocol-2 measurements, then signs revision/hash/source/contract plus immutable screenshot hashes. A failed check is distinct from execution failure and from unknown.
- `decide(id,*,revision,artifact_hash,verdict,reason,verification_signature)` signs an explicit prefer/reject/undecided choice and nonempty reason. Requires the exact current checked artifact and the displayed receipt signature, so a same-revision recheck cannot silently bind an unseen result. Failed checks allow reject/undecided only. No deployment permission or source-owner endorsement is implied. New approval, revision or checking invalidation clears current authority, not historical existence. Signed `review_events` retain immutable check/decision payloads; each new choice binds its exact receipt signature. Old current evidence imports once when first changed; previously erased evidence cannot be reconstructed.
- `report(id)` returns self-contained passive HTML for a current protocol-2 receipt, including a prominently labeled review-only failure packet. Failed checks still block implementation ZIPs. No filesystem/network/model operations occur in its pure renderer.
- `export(id)` revalidates head, all historical metadata/HTML, source, approval, current artifact, receipt and optional decision. ZIP contains `index.html`, `review.html`, `review.json`, `verification.json`, four controlled PNGs, `README.txt`, `unknowns.txt` and `SHA256SUMS.txt`. Checksums establish file consistency, not independent attestation. Legacy receipts remain inspectable but cannot authorize a current handoff.

Both inference and local revisions stop at 50 before further inference/publication; review events stop at 500 before new model/browser work. Capture-selected copy is rendered across all bounded layout/alignment/spacing combinations before approval/inference, against the shared 128 KiB escaped UTF-8 budget. Failed generation preserves prior good state; a possibly committed artifact is never removed after a lost acknowledgement.

## Native tools

`repager_capture`, `repager_list`, `repager_get`, `repager_scope`, `repager_approve`, `repager_generate`, `repager_remix`, `repager_verify`, `repager_decide`, `repager_export`.

Chat and dashboard share the runtime and two-operation/per-review admission. Human approval and preference must never be inferred by the agent. Tools return JSON/error strings. The bundled workbench skill and `hermes repager` command remain registered through supported public surfaces.

## Protected HTTP prefix `/api/plugins/repager`

| Route | Payload/result |
| --- | --- |
| GET `/health` | Configuration readiness, not quota or live success proof |
| GET `/reviews`, `/reviews/{id}`, `/reviews/{id}/scope` | Saved records/exact scope |
| POST `/reviews` | `{url,audience,goal}` → 202 `{job}` |
| POST `/reviews/{id}/approve` | finding, exact scope/CTA, `expected_version`, both preservation flags → `{review}` |
| POST `/reviews/{id}/generate` | `{instruction?}` → 202 `{job}` |
| POST `/reviews/{id}/remix` | `{base_revision,artifact_hash,changes,from_revision?}` → 202 `{job}` |
| POST `/reviews/{id}/verify` | `{}` → 202 `{job}` |
| POST `/reviews/{id}/decision` | `{revision,artifact_hash,verification_signature,verdict,reason}` → `{review}` |
| GET `/jobs`, `/jobs/{id}` | Profile-scoped process-local job list/state |
| GET `/reviews/{id}/artifacts/{basename}` | Manifest-bound PNG/HTML, sandbox CSP, no-store |
| GET `/reviews/{id}/report` | Authenticated HTML attachment or explicit refusal |
| GET `/reviews/{id}/export` | Authenticated ZIP or explicit refusal |

Inputs reject unknown keys, boolean revision numbers, non-boolean approval flags, cross-origin mutations and non-JSON/oversized bodies. Native host authentication/profile scoping remains host-owned. The standalone development app adds loopback Host validation and HttpOnly-cookie/Bearer authentication; it is not a remote production server.

## Canvas

Self-contained, plugin-owned shadow root and host-React wrapper. Exact scope precedes approval; bounded controls never write a contract locally. Canonical 1440/390 iframe dimensions, sandboxed full-size inspection, source-rectangle overlays, parent-property differences, read-only historical checks/export, new-revision restoration, explicit choice and report download. Mobile begins with mobile evidence and a single Original/Proposal area. Required scope copy is open by default; consent/drafts/focus survive incidental view/theme renders, while every approval attempt (including POST/readback failure), cancel/success/finding/CTA changes clear preservation confirmations. Historical proposals show their own approval snapshot and explicit scope-change warnings; action/revision keyboard focus survives rerendering. The desktop saved gallery remains open when counts change. Recovery rows expose identity and error only, not damaged source data. Fresh mounts query active jobs before potentially locked gallery reads, and never restart work to reconnect. All binary downloads use the supported host SDK.
