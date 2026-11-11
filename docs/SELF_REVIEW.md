# Critical self-review and improvements

Historical first review, not the current feature inventory or permission state. Current 0.3 fixes are in [THIRD_PASS.md](THIRD_PASS.md); current evidence is in [VERIFICATION.md](VERIFICATION.md). The two-layout, 13-check and no-restore descriptions below apply only to the original milestone, superseded by four layouts, 29 checks and restore-as-new-revision. The original CTA-consent behavior was also superseded by fresh confirmations on every CTA change/approval attempt. Public-source permission is now approved; see [SUBMISSION.md](SUBMISSION.md) for the remaining gates.

Reviewed 2026-11-10. This is a private development assessment, not a competition result or production-readiness claim.

## Prioritized findings and dispositions

| Priority | Finding | Implemented response | Evidence |
| --- | --- | --- | --- |
| P1 | Chat tools bypassed the dashboard's two-job admission limit. | Capture/generate/verify share runtime admission across both entry points, including synchronous errors and per-review slots. This is process-local, not a machine-wide quota. | Offline concurrency and slot-release regressions. |
| P1 | A 51st revision consumed inference and published a doomed artifact before storage rejected it. | Reject under the review lock before inference, orphan handling or publication. | Regression asserts no model call or r51 file. |
| P1 | An unrelated content heading could bind another semantic section's paragraphs/CTA. | Require a hero-region heading; new captures retain semantic container IDs and restrict selections to that container. | Service regressions and actual Chromium collector assertion. Legacy signed captures without container IDs are not silently rewritten. |
| P1 | Unchecked previews rendered at column width, then changed layout when replaced by canonical checked screenshots. Desktop comparisons were unreadably small. | Canonical-size scaled previews and full-size isolated inspection for source/proposal; revision selection is read-only. | Actual native dashboard asserts 1440px iframe viewport, sandbox, dialog close, historical verify/export refusal. |
| P1 | A transient polling error abandoned recovery; a failed terminal review reload could lose the job ID. | Keep existing job identity and admission UI until exact review/scope reload succeeds; retry resumes the job, not just gallery refresh. | Node state/control-flow regressions. Restart recovery remains reopen-saved-review, not a durable job queue. |
| P1 | Approved single-finding reviews could not change CTA. Changing CTA erased consent checkboxes. | Explicit scope editor/cancel, destination-only update, fresh approval invalidates checks; layout drafts reset across reviews. | Node regressions and native UI scope/checkbox checks. |
| P2 | Proposal hierarchy was a fixed 30px text specimen and result appeared after the whole workflow. | Bounded responsive 34-64px headings, paragraph measure, semantic hero, focus treatment; result-first workspace, compact navigation, mobile Original/Proposal switch. | Real desktop/mobile screenshots, full native acceptance, exact exported copy check. |
| P1 delivery | Old Android demo failure was not actually diagnosed. | Inspect real access logs, auth/session/file-serving implementation and encoding; current-session inline media, baseline MP4, private self-contained watch page, explicit download. | Old client requests logged 200/206; current unauthenticated requests 401; decoded baseline fast-start MP4 and isolated authenticated playback/seeking. Actual Android confirmation remains required. |

## Product judgment

The useful distinction is **a controlled hero-layout decision with a portable evidence chain**, not an AI conversion audit. It now makes that decision substantially easier to inspect. Nevertheless generation still selects from two trusted layouts and bounded controls. That limits creativity and site fidelity; verification machinery does not turn it into a general design engine. Do not pitch it as one.

Whole-page overflow findings do not identify the responsible element. A passing isolated proposal does not prove the source page was repaired. Capture is canonical only at the recorded first screens; unsupported semantic structure is rejected rather than reconstructed.

## Review method and coverage

- Parent inspected actual screenshots and rendered/native artifacts, reviewed code and compared official current Hermes integration documentation.
- Two independent read-only workers used task-local `openai-codex / gpt-6.1-sol`, asserted empty fallback chains before dispatch, and completed on that route. No global model routing changes.
- Installed Impeccable context/detector scripts were missing; both invocations failed with module-not-found. No automated design-detector score is claimed. Visual/browser evidence and source review were used instead.
- Re-ran unit, real Chromium network/preview, native SDK, immutable artifact and clean Node-install checks. Restarted the actual isolated native process, reopened the saved review/receipt and downloaded a handoff whose entries were byte-identical. No model call was used for restart recovery. Prior approval/hash/orphan/DNS regression tests remain in the full suite.
- Supported live proposal path: plausible.io. example.com and IANA exercise capture/unsupported boundaries in live tests; they are not invented customer successes. Source fixture tests are explicitly labeled and never runtime fallbacks.
- No additional high-severity exploit was established. That is not proof of absence. Application-level network controls are not browser-exploit containment. Container tests explicitly opt out of Chromium OS sandboxing.

## Remaining boundaries

1. Real Android/PWA playback awaits the owner's five-second inline-player check. No authenticated live-WebUI playback retest was possible from the automation browser: no saved vault login and secure prompt unavailable. No login bypass was attempted.
2. Desktop screenshot comparisons still scale down; use full-size inspection for readable desktop text. Mobile uses one comparison panel. Native host telemetry/header layout remains outside this plugin's ownership.
3. Historical revisions can be inspected, not promoted/restored as current. Regenerating invalidates current checks. No full-site design, Windows verification, universal page support, instant cancellation or durable queue.
4. The 13 checks do not include comprehensive contrast/a11y coverage, SEO, conversion, source-overflow-cause attribution or production readiness. Brand/typeface fidelity and glyph coverage need human review.
5. Browser provisioning remains explicit and platform-dependent. The live Hermes installation reported its venv out of sync with uv.lock; plugin validation still passed. This task did not repair or upgrade the live host.
6. Public visibility, redistribution licensing/collaborator permission, catalog PR, public X demo and competition form remain owner decisions. No publication or submission performed.
