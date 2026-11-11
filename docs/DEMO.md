# Demo and submission handoff

## The promise

“Website feedback is cheap. A controlled, inspectable change is harder. repager keeps the observed problem, the scope you approved, the exact artifact and its browser checks together.”

## Current 0.3 lifecycle recordings

The successful saved-review lifecycle run is in `artifacts/third-pass/native/`. The latest repaired continuation is in `native-fixed/`: **16.80 seconds**, no new capture or inference, signed historical PNG inspection, receipt-preserving scope cancel, receipt-bound automated choice, authenticated report/ZIP and mobile/theme checks. Its private watch page explicitly labels the resumed workflow. The fresh source-to-model/check stage and this restarted continuation are separate real runs; do not present the continuation clip as fresh URL-to-model generation or a full-flow latency measurement. Failed earlier assertions/recordings remain retained separately. Physical Android playback is still unverified.

## Historical 0.2 recording

The new real recording is **42.68 seconds** under `artifacts/top10-20261111/native-final/`. It demonstrates one actual Codex proposal, a **no-inference Editorial remix**, 29 named browser checks, an explicitly automated undecided test choice, and authenticated visual report/ZIP downloads. This is a materially different design-lab workflow from the older 48-second two-model-call baseline below. Report punctuation was normalized after recording and the final packet was re-downloaded/reverified; captured evidence, proposal and receipt stayed unchanged. The script's UI actions and JSON timeline are retained.

Afterward a new native process reopened the exact receipt and exported it with inference disabled, then restored the old design as a new unverified revision. The delivered packet remains the frozen checked revision 2, not the later restoration test state. Physical Android playback remains unverified; desktop/mobile-sized loopback player tests passed.

## Current demo target

**GetFluid (`https://getfluid.ai/`) is now the default recorded candidate.** It provides a real business audience and two meaningful hero actions. The recorded contract chooses **Book an Appointment** and preserves `https://calendly.com/trasy-getfluid/30min` exactly; WhatsApp remains an alternative selection, not an invented replacement or a claim that both CTAs are retained.

Its original visual design is already polished. Present this as **an optional, inspectable text-only layout alternative**, not a detected conversion defect, a replacement full site or proof of visual superiority. No business relationship, endorsement or customer authorization is implied by using the public site in a private test. Review rights/wording before public posting.

The previous branded GetFluid recording at `8b8e3a7` is **48 seconds**. It contains actual waits and two host model calls, not synthetic responses. Local evidence: `artifacts/brand-fluid/native-final/`. The initial failed recording is retained separately and is not delivered. Plausible remains the previous verified baseline and can be selected explicitly with `REPAGER_DEMO_TARGET=plausible`; `fluid` is the default. No live-target failure automatically switches to another site.

## Suggested 60-85 second demonstration (strictly under 90 seconds)

1. **Start inside native Hermes dashboard.** Show the repager tab, not a standalone website pretending to be a plugin.
2. **Capture a real public page.** Briefly show desktop/mobile evidence and the distinction between measured observations and optional layout hypotheses. No conversion score.
3. **Approve exact scope.** Expand preserved copy, explicitly choose a CTA and show its exact destination. Confirm both preservation boundaries.
4. **Generate through Hermes.** Show the real section and actual model/provider metadata. Explain that the model selects a bounded layout, not arbitrary executable HTML.
5. **Run browser checks.** Show named checks tied to the revision and exact hash, not a generic “AI approved” score.
6. **Revise once.** Show export becoming unavailable because the old receipt does not cover the new revision. Recheck, then download the handoff.
7. **Close on honest limits.** This is a text-only hero proposal, not an automatic production rebuild or guaranteed conversion improvement. Original site unchanged.

The automated native workflow records real actions and real waiting. Editing out waits is fine; do not represent edited footage as a measured end-to-end latency benchmark. Keep the raw recording and JSON timeline as evidence. Do not fabricate a successful result if a live site/model call fails.

## Release gates still requiring owner sign-off

- Confirm upstream collaborator/publication permission and select the new plugin's redistribution license.
- Authorize changing this independent private repository to public; do not change the upstream private repo.
- Pin the final **full 40-character commit SHA** for a catalog PR. A private build or branch name is not a catalog submission.
- Recheck current official submission instructions, then prepare the catalog PR and demo post tagging @NousResearch.
- Supply both public links through the official submission form. Do not report “submitted” without a verifiable result.

No public visibility change, catalog PR, social post or form submission is authorized by local acceptance alone.

## Current deadline, rechecked from the official announcement

[Nous Research's official announcement](https://x.com/NousResearch/status/2118094256438936062) is dated November 4, 2026 and says submissions close **November 11 at 5 PM EST**. That is **2026-11-11 22:00 UTC / November 12 at 06:00 Singapore time**. At the 2026-11-10 09:12 UTC check, 36 hours 47 minutes remained. Recalculate from the live clock before release rather than copying that duration.

Entry requires a public catalog PR, an X working-demo video tagging @NousResearch, and both links in the [official form](https://form.typeform.com/to/FwJLvOln). The demo must be **under 90 seconds**, not 90-100 seconds. Maintainer-started catalog checks are separate from this repository's own CI. No placement is promised.

## Android delivery investigation

- The old raw-file URL returned 401 without a WebUI login, with no automatic redirect to the login page. Opening a raw link in a different browser/PWA context is therefore not portable authentication.
- However, the real server access log recorded **200 and 206** for the old MP4 at 08:40:56 and 08:58:31 UTC, before the user reported failure. Missing authentication is **not established as the original cause**. No device/OS/user-agent attribution is inferred from those log entries.
- `/api/file/raw` resolves only the authorized profile's selected session workspace or that session's attachment inbox. The earlier file was in the old session inbox. New copies are in the current session inbox, not an unrelated workspace.
- Source review confirms `.mp4` maps to `video/mp4`, normal viewing uses inline disposition, `download=1` forces attachment, and valid ranges receive 206 with Content-Range/Accept-Ranges. These are implementation checks plus observed status logs, not a fresh authenticated response-header capture from a physical Android device.
- Original video was H.264 High level 4.0 at 1440 x 1000. This is not proven incompatible with the phone. The new real recording is additionally delivered as 960 x 666 H.264 Constrained Baseline level 3.1, yuv420p, fast-start, no audio. Full decode, seeking and exact embedded bytes were verified.
- A self-contained `watch.html` embeds the real MP4 in a native-controls `playsinline` player. It has no scripts or external requests, so once the authenticated HTML loads, playback does not depend on another authenticated media request or range fetch. It is not a public/static deployment and must remain behind the existing file endpoint login.
- Current-session MP4, watch page and ZIP copies were byte-hash checked after writing, owner-only, and did not change auth policy. The chat uses a native `MEDIA:` player plus separate authenticated watch/download links. Do not put tokens in links.
- The automation browser had no saved vault login and the secure prompt was unavailable. No live WebUI login bypass, session-cookie minting or credential extraction was attempted. The player test instead uses a clearly labeled ephemeral authenticated loopback harness with the same sandbox CSP, then stops it.
- **Unverified:** actual Android hardware/PWA playback. Ask the reviewer only to tap the inline player and confirm that the picture advances for five seconds; if not, distinguish login/error from a black player. Mobile emulation and desktop decode do not close this gate.

Local files: `artifacts/review-20261110/final-native/`. Delivery manifest: `artifacts/review-20261110/delivery.json`. They are deliberately not committed.

To package another existing real MP4 without publishing it:

```bash
python scripts/package_demo.py path/to/real-recording.mp4 path/to/new-watch.html
```

The command refuses an existing output and never records, fabricates, authenticates, transcodes or starts a server. Provision/transcode the actual recording separately. Use `scripts/verify_release_artifacts.py` and `scripts/verify_demo_player.mjs` for the documented artifact and isolated-browser checks.
