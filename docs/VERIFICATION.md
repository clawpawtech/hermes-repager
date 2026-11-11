# Verification receipt

## Public-release housekeeping (2026-11-11) - current

- **184 Python tests passed**, zero skips/failures/errors, with Chromium and public-network integrations enabled.
- **48 Node tests passed**, zero skips/failures, including actual browser UI/network/readability fixtures.
- Native plugin validator: **15 checks passed, zero warnings**. The pre-existing Docker-managed host-install sync warning is separate and the host installation was left unchanged.
- Dashboard rebuild is byte-identical to the checked-in bundle. Five additional packaging regressions check license/version consistency, documentation links, portable browser helpers, required workbench guards and accurate release status.
- Full private-development Git history was scanned with Gitleaks 8.30.1: seven commits, zero detected leaks. npm's production dependency audit reported zero known vulnerabilities. These are bounded scanner results, not proof of absence.
- Publication uses a clean-history copy with project-handle attribution only; the old development repository stays private. Historical milestone IDs below describe private execution evidence, not pins available in the new public history. Final public CI and the installable pin are obtained from the actual pushed clean-history commit.
- No new plugin-generation calls were needed for housekeeping. Earlier signed study records and video pixels are not rewritten by source-text sanitization; they remain private and require a fresh privacy review before sharing.

## Version 0.3 retained review trail (2026-11-11) - implementation acceptance

| Check | Actual result |
| --- | --- |
| Final Python, browser/public-network opt-ins | **179 passed; zero skips, failures or errors** |
| Final Node, actual Chromium opt-ins | **48 passed; zero skips or failures**, including historical image-versus-HTML selection |
| Clean source/dependency installation | npm ci/build and offline suites passed; browser opt-ins skipped explicitly and exercised separately |
| Native saved-review lifecycle | Retained reasons/receipt images, local revision, consent/focus/history and current authenticated handoff passed with inference disabled |
| Fresh GetFluid source-to-model stage | Actual capture, version-guarded approval, paid Codex proposal, no-inference local revision, stale-export refusal and 29 checks passed |
| Restarted continuation of that same checked study | Historical PNG dimensions and SHA-256 matched the signed archived receipt; exact current receipt remained intact; receipt-bound choice and authenticated report/ZIP succeeded, desktop/mobile/light/dark, no browser errors, no new capture/generation |
| Offline report and implementation packet | Authenticated report equals ZIP member, four canonical PNGs decode at desktop/mobile; no JS, external attempts or horizontal overflow; exact approved text/CTA and all 29 checks independently verified |
| Continuation clip | **16.80s**, H.264 Constrained Baseline level 3.1, 960 x 666, yuv420p, fast-start, full decode and embedded watch bytes match |

The fresh stage stopped after successful checking because its old assertion expected historical controls that are now intentionally unavailable. The next continuation exposed a second outdated assumption: inspecting a historical checked proposal opens its retained screenshot, not an unchecked HTML iframe. A live DOM probe established this before the assertion fix. The repaired continuation passed against the **same** saved review; capture and paid inference were not repeated. Its archived PNG is now checked by signed hash and dimensions, and a regression covers PNG inspection versus sandboxed HTML fallback. These are staged real runs, not one uninterrupted latency benchmark. Earlier failed recordings/logs remain separate.

Final study: `97a4b93174274f5f99c3aa502c487947`, checked revision **2**. HTML SHA-256 `70dbed5a0a9fdafc25f001c15e98435689956b7ff3d1958f168a832890f37f02`. ZIP **850052 bytes**, SHA-256 `8970c66d79c7e7452502a82cb780207752bc2fe5020560e86898a0135b8c9eef`. Revision 1 records actual `openai-codex / gpt-6.1-sol`; revision 2 is a local remix with null provider/model. The undecided choice is explicitly an automated test, not the project owner's/source-owner's preference.

Current evidence is gitignored under `artifacts/third-pass/`: `python-fixed.json`, `node-fixed.log`, `validation-final.json`, clean install receipts, saved-review proof under `native/`, fresh-stage log under `native-fresh.log`, and the successful final `native-fixed/{verified.json,result.json,artifact-proof.json,report-browser-proof.json,handoff.zip,review.html,watch.html}`. Source and exact-commit CI identify the shipped tree. See [third-pass findings](THIRD_PASS.md) for the twelve implemented lifecycle/branding fixes and the explicit local-signature threat boundary.

Physical Android and authenticated live-WebUI playback, comprehensive accessibility, conversion/visual superiority and competition placement remain unverified. No public release/submission approval is implied.

## Version 0.2 design lab (2026-11-11) - historical

Baseline compared: `8b8e3a7d99199801d8d63ff4d7275b12fed90b12`; see [BENCHMARK.md](BENCHMARK.md). Source pin and remote CI are obtained from the actual shipped commit, not embedded self-referentially in that commit.

| Check | Actual result |
| --- | --- |
| Final full Python suite, browser and public-network opt-ins | **159 tests, zero skips/failures/errors** |
| Final full Node suite, actual Chrome opt-ins | **43 passed, zero skips/failures** |
| Clean source snapshot / npm ci / build | 3 exact-pinned packages installed; offline Python 159 run, 4 explicit live-test skips; Node 40 pass, 3 explicit browser skips |
| Native plugin validation on Hermes 0.23.1 | **15 checks passed, zero validator warnings**, ten declared/registered tools; host-compatible API |
| Real native GetFluid workflow | One actual host `openai-codex / gpt-6.1-sol` generation, then a local Editorial remix with null model/provider, exact approved text/CTA and stale-export refusal |
| Protocol-2 artifact | **29/29 checks passed**, exact exported copy/href, source/preview PNG dimensions and hashes independently checked, zero browser errors |
| Offline report | Authenticated report equals ZIP `review.html`; all four embedded PNGs match canonical ZIP bytes. Actual Chromium desktop/mobile rendering, scripts disabled, no external requests or horizontal overflow |
| Real native restart/restore | Saved receipt/signature and canonical evidence reopened in a new process. Authenticated export worked with model calls **disabled**. Historical restore produced revision 3, exactly reproduced revision 1 HTML, cleared current receipt/decision and blocked export pending fresh checks |
| Demo and player | **42.68s**, H.264 Constrained Baseline level 3.1, 960 x 666 encoded pixels, yuv420p, fast-start; full decode and exact embedded bytes pass. Authenticated loopback desktop/mobile play/seek passes |
| Isolation | The live Hermes configuration digest matches the pre-task baseline; only isolated test-home settings changed. No free fallback, public submission or unrelated-project edits |

Frozen delivered study: `386834ab65da4ff19f3e1f340c2011df`, revision **2**, HTML SHA-256 `719595402442d87f70f32b7264bd8ca520845945c022cb1ed48d6e6ac725d64a`. Its final local-remix metadata correctly has no model/provider; revision 1 records the actual Codex generation. Its explicit undecided choice is labeled **automated acceptance test only**, not the project owner's/source-owner's preference or endorsement.

Final ZIP: **859151 bytes**, SHA-256 `0ff12a0fb562827f7e78d6151370e1d9274e2f2ed7a27a05e2631af756854c57`. MP4: **1274265 bytes**, SHA-256 `793aa0da609db9abfd8312ee4b292527057a44190abe4f7bc10e2ac299ed99eb`. Following restart, only report punctuation and its checksums changed to satisfy the no-em-dash UI convention; record, receipt, proposal and PNG bytes remained identical. Both report and ZIP were re-downloaded and reverified. The later restore test intentionally left the isolated current study at unverified revision 3; it does not retroactively certify that revision or replace the frozen revision-2 packet.

Evidence is gitignored at `artifacts/top10-20261111/`, including `python-shipping.json`, `node-shipping.log`, `validation-final.json`, `clean-python.json`, `clean-node.log`, and `native-final/{verified.json,result.json,resume-proof.json,restored.json,artifact-proof.json,report-browser-proof.json,player-proof.json,handoff.zip,review.html,demo-android.mp4,watch.html}`. Raw reviewer transcripts stay outside the plugin install tree. Current release verifier requires protocol 2; use the corresponding older pinned script for historical 13-check runs below.

Failures are retained, not relabeled: the first current native attempt used an old screen-title selector and stopped before capture/inference; restart testing first ran before server readiness and then used an outdated Restore label. Selectors/readiness were corrected, followed by the passing actual run. The first clean offline run caught stale punctuation expectations after the UI text normalization; expectations were updated, then clean and full suites passed again.

**Still unverified:** physical Android hardware/PWA playback, authenticated live-WebUI playback, novice first-use usability, visual/conversion superiority, full-site remediation, comprehensive accessibility and contest ranking. The portable report is an evidence document, not production approval. The release permissions in effect for this historical run have since changed; see the current [submission checklist](SUBMISSION.md).

## Historical results below - not current totals


## Branding and GetFluid follow-up (2026-11-10)

- Reused the explicitly authorized live repager wordmark treatment and byte-identical favicon; no source application code was imported. See [BRANDING.md](BRANDING.md) and the bundled font notice.
- **123 Python tests, zero skips/failures/errors; 18 Node tests, zero skips/failures**, with live browser opt-in. Plugin validator: **15 passed, zero warnings**, on native Hermes v0.23.1.
- The first native GetFluid recording failed before inference: DOM evidence was sampled before client rendering, although the later screenshot contained the hero. A deliberately delayed local browser fixture reproduced the defect (red); bounded visible-heading readiness fixed it (green). No target-specific source substitution or network-policy weakening. A readiness timeout still preserves actual unsupported evidence; this is not universal app-readiness proof.
- After the fix, **three independent guarded GetFluid captures** succeeded with the same supported headline/body and two CTA candidates. No measured overflow defect was found; the finding remains an optional layout hypothesis.
- Actual full native GetFluid workflow completed: two `openai-codex / gpt-6.1-sol` revisions, exact approved booking link, missing approval/stale-export refusal, revision history, canonical preview, checks and authenticated ZIP. All **13 artifact checks passed**, zero browser errors. Host route/fallback isolation remained explicit; no live configuration change.
- New review: `cbba0a989aa6408db20d1f3c6a42b714`, revision 2. HTML SHA-256 `aa116c6b0013516e39890769e16fd39849e7a52f5cab8613ef3b635b166c6237`. ZIP **438692 bytes**, SHA-256 `493212f18b44202077ad533d7f55ec0a5bb6221dd85cfa2ec2010aa4f51da732`.
- New real demo: **48 seconds**, H.264 Constrained Baseline level 3.1, 960 x 666 encoded pixels, yuv420p, fast-start. Full decode and desktop/mobile-sized player seeking passed; embedded watch bytes match the MP4. Physical Android playback is still unverified.
- Native branding smoke test: four real renders at 1440/390px and light/dark themes, loaded exact app icon, correct p-position/orange glyph, no horizontal overflow or browser errors. No inference used for this smoke test.
- Local evidence: `artifacts/brand-fluid/{preflight.json,stability.json,python-tests.json,plugin-validation.json,branding/,native-final/}`. Failed attempt remains separately under `native/`, never substituted for the passing recording.
- New current-session private attachments were hash-checked after copying. Unauthenticated MP4/watch requests return **401**. Original recordings and delivery names remain intact.

## Previous critical-review pass (2026-11-10)

See [SELF_REVIEW.md](SELF_REVIEW.md) for prioritized findings, fixes and remaining product/release limitations. Historical evidence below is retained, not substituted for this rerun.

| Check | Actual latest result |
| --- | --- |
| Full Python suite with explicit live Chromium opt-in | **123 tests, 0 failures, 0 errors, 0 skips** |
| Full Node suite with real Chromium network guards and canvas regressions | **15 passed, 0 skipped** |
| Native plugin validation | **15 checks passed, 0 validator warnings** |
| Clean Node dependency snapshot | `npm ci --ignore-scripts` installed 3 packages; offline tests passed with the live test intentionally not opted in |
| Actual native dashboard acceptance | Real Plausible capture, exact scope/CTA approval, two `ctx.llm` generations, stale-export refusal, fresh checks, authenticated SDK ZIP download |
| New native UI assertions | Canonical unchecked iframe width; full-size sandboxed history inspection; historical verify/export disabled; scope editor/cancel; CTA checkbox preservation; mobile Original/Proposal switch |
| Native process restart | Saved review and exact receipt reopened in a new native process; authenticated re-export succeeded with every ZIP entry byte-identical; no new model call |
| Final exported artifact | **13 browser checks passed**, exact source copy/CTA and PNG dimensions/hashes independently checked against ZIP |
| Demo | Real recording, **36.84s**, 960 x 666 encoded pixels, H.264 Constrained Baseline level 3.1, yuv420p, fast-start, full decode successful |
| Player harness | Playback and seek successful at 1440px and 390px browser widths with ephemeral loopback authentication and no external requests. **Not actual Android-device proof or a live-WebUI authenticated playback test.** |

Final recorded review `a7737cb8081d43049ea769b8dc9355e2`, revision 2. Both revisions recorded `openai-codex / gpt-6.1-sol`; isolated profile fallback chains were empty. Two independent review workers also asserted this route with empty fallbacks. No free/trial inference route or global routing change was used.

- HTML SHA-256: `1121960b6234ceb1cb8ba2135f82224349abe50dddb9c326ff3f75e11bcc3f22`
- ZIP: 365744 bytes; SHA-256 `6618f003332517849b5d61fce0264a3e5b6949049f4664310511b8bc9cbeb5bc`
- MP4: 1230280 bytes; SHA-256 `e687e943da9212633e30c5be69b5ef481d7010e809d1f8e5478842f2817843cd`
- Durable local evidence: `artifacts/review-20261110/`, especially `final-native/{result.json,verified.json,artifact-proof.json,player-proof.json,handoff.zip,native-workflow.webm,demo-android.mp4,watch.html}`. Runtime/capture files remain gitignored.
- Reproduction: `python scripts/verify_release_artifacts.py artifacts/review-20261110/final-native`. Player test: set the explicit artifact directory/browser/sandbox diagnostic environment and run `node scripts/verify_demo_player.mjs`. The harness binds an ephemeral **authenticated loopback-only** endpoint, then stops it.
- Host warning: this Docker-managed Hermes installation reported its venv out of sync with uv.lock. The plugin validator itself passed with no warnings. No host repair/upgrade was attempted.

Android delivery investigation and verification boundaries are documented in [DEMO.md](DEMO.md). Public release gates remain closed.

## Historical baseline

Verified 2026-11-10T08:26:01.992045+00:00. Local checks below are actual executions, not agent self-reports or fixture substitutions. External CI is tracked separately at [GitHub Actions](https://github.com/clawpawtech/hermes-repager/actions/workflows/ci.yml).

## Automated checks

| Check | Observed result |
| --- | --- |
| Python full suite, including explicit live Chromium tests | 116 tests, 0 failures, 0 errors, 0 skips |
| Node full suite, including real Chromium network guards | 8 tests passed, 0 skipped |
| Hermes plugin validation | 15 checks passed, 0 warnings; native plugin-host compatible |
| Clean dependency installation | `npm ci --ignore-scripts` installed 3 packages in a separate clean snapshot; offline Node tests passed with the one live test deliberately not opted in |
| Source/distributed canvas | Rebuilt self-contained IIFE; syntax checked; no remote frontend dependencies |

Reproduce the Python receipt with `python scripts/run_tests.py --receipt artifacts/final/python-tests.json`. Enable `REPAGER_BROWSER_INTEGRATION=1` and the documented trusted browser configuration to run live browser checks. Container tests explicitly used the no-sandbox opt-out; this is disclosed, not represented as OS isolation.

## Real native-dashboard acceptance

The actual native `hermes dashboard` ran in an **isolated test home** on loopback port 9121, without modifying the user's normal profile. The UI used the actual host `SDK.fetchJSON` and `SDK.authedFetch`, including authenticated binary ZIP download. No static token or host credential was copied into the plugin UI.

The recorded workflow:

1. Captured **https://plausible.io/** in real desktop/mobile browser sessions.
2. Inspected server-derived exact copy and CTA choices; missing approval scope/CTA was rejected.
3. Approved the selected CTA and matching scope hash.
4. Generated revision 1 through host `ctx.llm` using **openai-codex / gpt-6.1-sol**.
5. Browser-checked the exact revision.
6. Generated a real second revision through the same non-free host model.
7. Confirmed the old receipt was cleared, the download button disabled and server-side export refused.
8. Rechecked revision 2 and downloaded its real handoff through the native SDK.
9. Verified desktop 1440px and mobile 390px UI layout, actual mobile image widths, light/dark theme and zero browser JavaScript errors.

Final review: `faf1440106a7499ba91101f9be24e45f`, revision **2**. Both revisions record `openai-codex / gpt-6.1-sol`; configured fallback chains were empty. Final receipt contains **13 browser checks, 0 failures**. These are narrow observable checks, not a whole-site visual-effectiveness or accessibility verdict.

- Exact HTML SHA-256: `f82b6a5f951bb278a7df54d325a9598894502e0e4a12fc0342345a44813913af`
- Handoff ZIP: **340890 bytes**
- ZIP SHA-256: `8763565461f7db2eafb6a4ab5f605101c3c2fe24c0b49a36f7343cd85af3a527`
- Original and proposal PNGs independently decoded at **1440 × 900** and **390 × 844**.
- The ZIP contains exact HTML, review/receipt metadata, source/preview PNGs, handoff notes and limitations. It does **not** contain the local HMAC key.

## Local artifacts, deliberately not committed

Under `artifacts/final/native/`:

- `handoff.zip`, `verified.json`, `result.json`, `artifact-proof.json`.
- `native-start.png`, `native-approval.png`, `native-verified-desktop.png`, `native-verified-mobile.png`, `native-verified-mobile-dark.png`.
- `demo.mp4`: H.264, 1440 × 1000, 37.4 seconds, 2,043,571 bytes. A straightforward transcode of the actual raw recording, no fabricated footage.
- `native-workflow.webm`: **37.400000 seconds**, **7348630 bytes**, actual recorded browser actions including real waits. This is one run, not a latency benchmark.

`artifacts/` is gitignored because it contains captured third-party material and runtime data. These files remain in the local workspace, outside the 24-hour scratch-pruning directory. Nothing was publicly deployed or submitted.

## Independent-review findings resolved

- **Optional approval identity:** now required service keyword arguments, required HTTP fields and required native tool schema. Missing, empty, wrong and null binding tests reject without mutating the contract.
- **Mutable screenshots/receipts:** signed source/revision/receipt metadata and exact byte hashes are checked before serving/export. Tests cover edited originals, previews, metadata, receipts, HTML, stale contracts and stale revision replay. Local-key integrity is not a public-key attestation or a defense against a malicious host owner.
- **Interrupted revision publication:** unrecorded next-revision files are preserved in quarantine before retry. Errors after an already-committed record never delete its HTML. Restart/lost-ack tests reproduce both cases.
- **Unbounded DNS preflight:** capture performs syntax-only parent validation; DNS resolution/address pinning occur inside the timed, killable worker/proxy. The regression test forbids parent-side resolution.

## Remaining release boundaries

This is a private, text-only semantic-hero milestone. Arbitrary-site/full-page redesign, Windows support, public multi-tenant hosting, automatic retention/cancellation and production deployment are not claimed. The readiness field `browser_ready` currently positively identifies an explicitly configured browser path; standard Playwright cache discovery can still work when that field is false. Public licensing/visibility, catalog admission, demo publication and submission require separate owner sign-off.
