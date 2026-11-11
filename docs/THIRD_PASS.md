# Third-pass review: repager 0.3

The second release had good current-artifact guards but incomplete lifecycle coverage. A fresh backend review, a separate product/workflow review, parent adversarial probes, native browser exercise and an independent fix review found the gaps below. All model reviewers were explicitly pinned to paid `openai-codex / gpt-6.1-sol` with empty fallbacks. Offline adapters and intercepted UI fixtures are not live website/model evidence.

## What changed and why

| Finding | Root cause | Implemented correction |
| --- | --- | --- |
| Earlier check runs and choice reasons disappeared | Current authority and historical existence were the same mutable fields | Individually sealed, sequence-bound `review_events`; exact original receipt/decision payloads survive revision, reapproval, failed recheck and later choice changes |
| A choice could bind unseen same-revision checks | Revision/hash stayed unchanged when another client rechecked | Decision requests must provide the displayed `verification_signature`, compared under the record lock; stale choices are refused |
| A stale approval could clear newer approved work | Source scope hash did not represent review-state freshness | Required strict `expected_version`, separate from stable source-scope hash; compare under lock before mutation |
| Damaged reviews disappeared or broke the gallery | Discovery depended on successfully parsing JSON; head read I/O escaped per-review handling | Identity-first discovery, minimal recovery rows without unauthenticated source fields, bounded head-read errors and discoverable interrupted initial publication |
| Removing the head and version marker enabled modern-to-legacy downgrade | Legacy inspection depended on a removable record flag alone | Signed modern approvals/revision markers/events independently require an authenticated head; genuine pre-head records retain legacy inspection/reapproval behavior |
| Accepted exact copy could exceed the verifier budget after escaping | Character counts did not represent HTML UTF-8 bytes | Shared 128 KiB byte budget; render every bounded layout/alignment/spacing combination before approval/inference; no silent truncation |
| Historical artifact appeared beside a different current approval | Scope editor always displayed current contract | Inspected revision displays its own snapshot; current approval is labeled separately; cross-contract property comparisons explicitly say scope changed |
| Cancellation or failure reused preservation confirmations | Form preservation did not distinguish incidental rerender from a new attempt | Keep confirmations across theme/view changes, clear them on cancel, success, finding/CTA changes and every failed POST/readback attempt |
| Failing candidates could not be shared for discussion | Report and executable handoff used one permission gate | Passive, authenticated review-only failure report with prominent warning; failed implementation ZIP and preference remain refused |
| Keyboard actions lost focus | Whole-shadow-root rendering restored only form fields | Restore stable action identities and named revision selector focus; exercise Enter, Space and subsequent control interactions in Chromium |
| Desktop saved gallery could become inaccessible | Changing summary counts lost disclosure state; closed native details remained hidden despite descendant CSS | Stable disclosure identity and enforced desktop-open state; actual changing-count browser regression |
| Product name was inconsistently capitalized | Display prose spread across errors, metadata, help, docs and media labels | Lowercase **repager** throughout, plus a regression audit; preserve identifiers, environment variables, URLs and captured source case |

## Review trail and handoff semantics

- New check results and choices append authenticated events. New choices bind review, revision, artifact, contract and the exact displayed receipt signature.
- Current verification/choice are still invalidated on relevant changes. Historical events cannot authorize export, preference or checking an old artifact.
- Historical images remain protected by the same authenticated API and hash checks. Previous check-run images can be opened read-only, including after an unsuccessful recheck.
- The passive report includes a compact candidate ledger and retained event reasons/check summaries. It embeds only the current four source/preview images; older images remain in local protected storage. The ZIP is a current implementation packet, not a complete historical archive.
- Existing sealed current evidence is imported once when first superseded. Evidence already erased by older code cannot be reconstructed, and migration does not invent it.
- Fifty revisions and five hundred review events are explicit per-review limits. Capacity is checked before model/browser work, preserving the last good evidence on refusal.
- Local signatures are not independent attestations. Restoring the complete record/head/key backup restores that snapshot; a host owner controlling the key remains outside the guarantee.

## Verification approach

New failing regressions were exercised before the corresponding fixes. Coverage now includes retention/restart, failed rechecks, old PNG tamper, pre-trail migration, event-cap preflight, head-marker stripping, same-revision receipt races, stale approval POSTs, malformed/head-only recovery, HTML escaping expansion, review-only failed reports, archived authenticated PNGs and actual keyboard/consent/gallery behavior.

The new native acceptance script, `scripts/verify_review_trail.mjs`, resumes the existing real GetFluid capture with inference disabled. It exercises fresh actual Chromium checks, an explicitly labeled automated choice, a deterministic local revision, historical image hashes and reasons, current checking, authenticated report/ZIP downloads, desktop/mobile themes and focus. It neither recaptures the site nor repeats paid generation. Automated acceptance choices are not the owner's preference or source-owner endorsement.

Final test counts, native artifacts and remaining device limits are recorded in [verification](VERIFICATION.md). The earlier real URL-to-model workflow remains evidence for initial generation; the new run proves the additional lifecycle behavior. Historical failed acceptance attempts are retained separately, not substituted as successful runs. The later fresh source-to-model stage also passed capture/approval/generation/remix/checks; its historical-control assertions were outdated. The final repaired continuation inspects retained historical PNGs by dimensions and signed SHA-256, rather than assuming they are HTML frames, and completed choice/report/ZIP/mobile/theme acceptance with zero new model calls.

## Why this matters

The differentiation is now inspectable design reasoning across alternatives, not simply safe generation of one current artifact. This still does not establish visual superiority, conversion improvement, full accessibility, a production-ready integration patch or a competition placement. Public release, license, catalog and submission remain owner-gated.
