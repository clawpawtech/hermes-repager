# repager for Hermes

**Keep the message. Explore the presentation.**

An evidence-bound hero design lab for designers and developers who need a reasoned alternative, not another unconstrained website generator. Capture a real public page, approve the exact words and CTA, explore four trusted design directions, check the actual output in Chromium, and hand someone a visual review they can open offline. **The original website is never changed.**

**Version 0.3.0 · MIT-licensed source · Community plugin.** Catalog admission and hackathon submission are separate, pending steps, not endorsements. Branding is the explicitly authorized repager wordmark and original favicon, bundled offline. GetFluid is an independent demo of a controlled layout alternative, not a client endorsement or a claim that its already-polished site needed fixing.

[![CI](https://github.com/clawpawtech/hermes-repager/actions/workflows/ci.yml/badge.svg)](https://github.com/clawpawtech/hermes-repager/actions/workflows/ci.yml)

[Third-pass fixes](docs/THIRD_PASS.md) · [Competitive review](docs/BENCHMARK.md) · [Verification](docs/VERIFICATION.md) · [Security](docs/SECURITY.md) · [Interfaces](docs/INTERFACES.md) · [Release gates](docs/SUBMISSION.md)

**Verified locally:** 184 Python tests and 48 Node tests pass with browser integrations enabled and zero skips; native plugin validation passes all 15 checks. Public CI runs the offline suites on Python 3.11/3.12/3.14 and deliberately skips live-browser tests. The earlier real URL-to-model workflow and its restarted continuation are documented separately, not presented as one uninterrupted benchmark. Physical Android playback remains unverified.

## One section. A deliberate choice.

1. **Observe.** Supply a public URL, audience and intended action. Get real desktop **1440 × 900** and mobile **390 × 844** captures and bounded DOM evidence. No model call during capture.
2. **Approve the message.** Inspect the visible headline, selected paragraphs, supported CTA choices and exact destination. Approval is signed and bound to that source and scope, and rejects a stale displayed record version. Page instructions cannot become approval.
3. **Ask for a direction.** The host-owned `ctx.llm` chooses a constrained layout and measured palette, never writes factual copy or arbitrary HTML/CSS/JavaScript. A deterministic readability guard records any necessary text-color repairs.
4. **Adjust without inference.** Choose **Stack**, **Split**, **Editorial** or **Spotlight**, alignment, spacing and source-palette colors. Apply saves a new immutable revision. Direct controls and historical restore make **no model call**; restore creates a new revision, never resurrects an old receipt.
5. **Check the bytes.** Current protocol 2 runs **29 named Chromium checks** across both viewports: approved DOM copy, CTA label/destination, text contrast, target size, clipping/first-screen CTA completeness, keyboard focusability, overflow, script and network controls. Unknown results remain unknown, not passes. This is not complete accessibility or conversion proof.
6. **Decide.** Record prefer, reject or undecided with a reason for the exact checked artifact. Failed checks permit rejection or uncertainty and a labeled passive review report, not preference or implementation export. Earlier check runs and reasons remain in the signed review trail after new revisions or failed rechecks. A recorded choice is not deployment permission or source-owner consent.
7. **Hand off.** Download a self-contained **visual HTML report**, or a ZIP containing it, the proposal, real screenshots, checks, metadata, limitations and file checksums. Stale, edited, incomplete, legacy or failing receipts cannot authorize an implementation handoff. A compact candidate ledger retains earlier observations and choices; historical images remain inspectable locally, while the packet embeds only its current four images.

The native canvas includes real source-region highlights, canonical-size sandboxed inspection, property differences, read-only history, explicit scope editing, phone-first mobile evidence and a single Original/Proposal comparison. Reload reconnects to an active backend job before reading a potentially locked gallery. No fake percentages, sample-success fallbacks or automatic preference scores.

## Deliberately bounded

- **Text-only first-screen hero studies**, not complete site redesigns, deployed fixes or integration-ready framework patches.
- A visible, unobscured `h1`/`h2`, paragraph and navigable HTTP(S) CTA inside the same supported semantic main/section container, outside header/navigation and before the next heading.
- Desktop is the canonical copy source. Mobile is independently captured and checked; missing mobile text matches are not fabricated.
- Four authored layouts, fixed responsive CSS and captured palette plus black/white. No model-authored CSS/HTML, source imagery, external fonts, scripts or third-party components in proposals. Editorial uses platform serif fonts, so typography can vary across operating systems.
- Root overflow and candidate rectangles are observations, **not proven causes**. A passing standalone proposal does not establish that the original site's overflow was repaired.
- Public pages only. Login, CAPTCHAs, blocking consent walls, missing semantic markup and late content outside the bounded readiness window fail visibly. No bypass or source substitution.
- POSIX file locking; native Windows and physical Android-device playback have not been verified.

## Install from source

Requires **Hermes ≥0.22.5**, Python ≥3.11, Node ≥20, the declared FastAPI/Pydantic dependencies and a provisioned compatible Chromium. Python 3.11/3.12/3.14 are the CI targets. Runtime browser dependencies are exact-pinned; no new dependencies were added for the design lab or report.

There is no catalog entry yet; install by repository, not the bare catalog name `repager`. Review the source first. In an interactive terminal, Hermes asks separately about the declared Python and Node dependencies:

```bash
hermes plugins install clawpawtech/hermes-repager
```

Enable `repager` if you did not enable it during installation. For a reviewed immutable revision, the installer also accepts `--ref` followed by its full 40-character commit SHA. A future catalog entry must pin such a SHA.

For headless/agent-managed setup, `--yes-deps` consents to **Python** dependencies only; it does not answer the separate Node prompt. If Node installation was skipped, run the following inside the installed plugin directory (normally `${HERMES_HOME:-$HOME/.hermes}/plugins/repager`):

```bash
npm ci --ignore-scripts --no-audit --no-fund
```

This installs Playwright's driver and the IP parser, **not Chromium**. Provision a trusted compatible browser separately and set `chromium_path`, or deliberately install the pinned Playwright browser from that same directory with `npx playwright install chromium`. Required OS libraries remain the operator's responsibility. Nothing downloads a browser or calls a model at import/register time.

After configuration, run `hermes repager --doctor`, start `hermes dashboard`, and open the **repager** tab. Configure model access before using **Generate**; capture and local browser diagnostics do not need a model call.

## Configuration and consent

Enable `repager` through Hermes' plugin controls. Plugin settings:

| Setting | Default | Meaning |
| --- | --- | --- |
| `chromium_path` | empty | Trusted provisioned browser path, or Playwright's installed standard browser |
| `allow_model_calls` | false | Consent to send public captured text, URL and the brief to the host model |
| `allow_no_sandbox` | false | Explicit OS-sandbox opt-out for a dedicated isolated container only |
| `browser_temp_dir` | empty | Optional short trusted absolute scratch path, at most 50 bytes, for Chromium sockets |

Inference requires **both an explicit provider and model** in the plugin-owned `auxiliary.repager_layout` task, its `fallback_chain: []`, global `fallback_providers: []` and disabled legacy `fallback_model: {}` or `null`. Known free/router aliases, automatic routes, malformed fallback values and main-model inheritance are refused before dispatch. Returned attribution is checked as an additional audit; it cannot undo an already-completed call. Provider billing and a host owner replacing transport are not independently knowable from a model identifier. Our acceptance profile uses **Codex only, with no fallbacks**.

See the non-secret [settings example](docs/SETTINGS.example.yaml). Merge deliberately; **do not overwrite your live Hermes configuration**. The plugin never edits routing, reads provider credentials or signs into a separate service.

**Browser-first:** native `hermes dashboard` discovers the prebuilt canvas and protected plugin API. JSON and binary downloads use the supported host SDK. This is not the third-party Hermes WebUI or the separate native Desktop SDK. An agent can perform setup; end users need not operate a terminal to use the canvas.

**Chat-first:** the bundled workbench skill guides the same **ten** tools: `repager_capture`, `repager_list`, `repager_get`, `repager_scope`, `repager_approve`, `repager_generate`, `repager_remix`, `repager_verify`, `repager_decide`, `repager_export`.

The registered `hermes repager` command also provides a token-authenticated **127.0.0.1-only development** canvas. Do not publish or port-forward it as production hosting. `hermes repager --doctor` reports non-secret browser configuration.

## Development and evidence

Use a disposable Python environment rather than changing your live Hermes environment. Install the test requirements before running the suites:

```bash
python3 -m pip install -r requirements-dev.txt
npm ci --ignore-scripts --no-audit --no-fund
npm run build
python3 scripts/run_tests.py --receipt artifacts/python-tests.json
npm test
hermes plugins validate . --json
```

Offline tests use explicitly labeled injected adapters, never runtime fallbacks or claimed live evidence. A producer-to-canvas schema regression passes an actual service-produced signed record to the real canvas, rather than duplicating its receipt schema in a frontend mock.

Live tests need explicit opt-ins and provisioned Chrome:

```bash
REPAGER_BROWSER_INTEGRATION=1 REPAGER_ALLOW_NO_SANDBOX=1 \
  REPAGER_CHROMIUM_PATH=/your/trusted/chromium REPAGER_TEST_NO_SANDBOX=1 npm test
REPAGER_BROWSER_INTEGRATION=1 REPAGER_PUBLIC_INTEGRATION=1 \
  REPAGER_CHROMIUM_PATH=/your/trusted/chromium REPAGER_ALLOW_NO_SANDBOX=1 \
  python3 scripts/run_tests.py --receipt artifacts/live-tests.json
```

Sandbox opt-outs above are **only for an appropriately isolated container**; default launch retains Chromium sandboxing. Public-network tests have a separate opt-in. See [verification](docs/VERIFICATION.md) for actual execution, skipped-test disclosure, clean-install checks, native workflow and artifact/player proof. `scripts/verify_native_workflow.mjs` separately requires `REPAGER_ALLOW_LIVE_MODEL=1`; its current path uses one real host-model generation followed by a no-inference local remix and authenticated handoff.

## State, integrity and privacy

State lives under `<HERMES_HOME>/plugin-data/repager/reviews/`. Capture identity is saved before navigation, so interruption does not erase the attempted review. Saved reviews survive process restart; job history does not. Two expensive operations per process, one per review, are shared across chat and dashboard. The 50-revision and 500-review-event limits are enforced before further inference/browser work or publication. Exact approved copy is preflighted across all bounded designs against the shared 128 KiB escaped UTF-8 HTML limit; words are never silently dropped to fit. No instantaneous cancellation or automatic retention policy is claimed.

Local HMACs bind source evidence, approval, revisions, decisions and receipts. An independently sealed current head detects record-only editing and rollback; a two-state publication journal resolves failed-save versus lost-acknowledgement recovery. History metadata and all retained HTML artifacts are checked before handoff. **This is local integrity, not external attestation:** a host owner with the key, or a full filesystem rollback including its head/key, is outside that boundary.

Captures, normalized public text, proposals, choices and source URLs are retained until the operator removes them. Do not supply private/signed URLs or URLs carrying secrets. Reports intentionally include their captured evidence. There is no telemetry, external storage, deployment, service signup or automatic repository PR. Inference consumes the operator's host quota.

## License and release status

The original plugin code is released under the [MIT License](LICENSE). [Third-party notices](THIRD_PARTY_NOTICES.md) retain dependency/font and asset terms; MIT does not confer third-party trademark or captured-site rights. The package's `private: true` prevents accidental npm publishing, not public source use. Public source and licensing are owner-approved; catalog PR, public demo/X post and competition form remain separate actions tracked in [the submission checklist](docs/SUBMISSION.md). No competition placement is guaranteed. See [contributing](CONTRIBUTING.md) and [private security reporting](SECURITY.md).
