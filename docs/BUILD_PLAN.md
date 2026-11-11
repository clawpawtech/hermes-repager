# First working release plan

Historical initial plan, not the current feature inventory or permission state. Current 0.3 behavior, evidence and release checklist are documented in [README](../README.md), [THIRD_PASS.md](THIRD_PASS.md), [VERIFICATION.md](VERIFICATION.md) and [SUBMISSION.md](SUBMISSION.md). References to private-only work and closed gates below describe that initial milestone, not the current owner-approved public source release.

## Product acceptance
1. Start with real public URL, audience and goal through a native tool or browser canvas.
2. Collect the same rendered state for screenshot and bounded DOM evidence at desktop/mobile sizes; persist artifacts and evidence IDs.
3. Select one supported finding, approve preservation constraints (verbatim factual content, primary CTA destination, source palette default), generate a schema-constrained section through the host model.
4. Trusted renderer emits standalone no-script/no-network HTML. Persist immutable revisions and hashes.
5. Browser opens exact output in fresh context and measures render, overflow, CTA focusability/destination, screenshots and applicable foreground/background contrast. Unknown stays unknown. No source-page-vs-section performance comparison.
6. Show actual before/proposed, named results and preserved content in browser canvas. Changes invalidate previous verification.
7. Export exact HTML, rationale, screenshots and checks with human review limitations. Original site unchanged.

## Implementation phases
A. Private independent repo and provenance established. GitHub API privacy/non-fork and remote main verified before the critical-review implementation pass.
B. Agreed backend/worker/UI contract; implement core and browser independently, prove real browser route before expanding UI.
C. Native Hermes registration and dashboard router, browser-first canvas using public SDK plus standalone authenticated dev harness.
D. Spec review then code-quality/security review, fix important issues and rerun tests.
E. Real end-to-end capture + host-model generation + rendering. Retain raw run evidence locally, not synthetic output. Fresh install/doctor/validate. Push private repo and read back commit/visibility.

## Non-goals
No full-page cloning, production changes, arbitrary repository patches, monitoring, unrestricted generated code, autonomous purchases, invented claims, desktop-only dependencies or modification of the user's WebUI.

## Critical-review implementation pass

Completed the focused fixes and real acceptance described in [SELF_REVIEW.md](SELF_REVIEW.md) and [VERIFICATION.md](VERIFICATION.md). Scope remains one text-only semantic hero. Current Android delivery is private/current-session and byte-checked; actual-device playback awaits the owner. Public release/submission gates remain closed.

## Release honesty
This milestone is an installable vertical slice, not a declaration of hackathon readiness. Document remaining supported-platform/browser boundaries and judge-facing polish. No publication, catalog PR or social posting until separately approved.
