# repager plugin build contract

## Scope
Native Hermes plugin: public landing-page evidence -> one selected finding -> explicit preservation contract -> actual HTML/CSS section -> real browser checks -> export. Browser-first and mobile-friendly. No production deployment, automatic PRs, fake conversion metrics, paid service signup, or global Hermes configuration changes.

## Privacy and third-party rights
Public project attribution uses the project handle only. Do not add real names, identifying collaborator/upstream links or personal authorship narratives. Do not import application code from unrelated projects. The bundled project wordmark/favicon are owner-authorized; retain required font/dependency notices. Restricted decorative components are excluded.

## Branding
Use **repager** in lowercase in all user-facing product copy. Preserve environment-variable names, code identifiers, external URLs and captured source copy exactly.

## Engineering
- Plugin root plugin.yaml + __init__.py. Internal package repager/. Node browser worker in browser/. Dashboard manifest and static assets in dashboard/.
- Python tests: python3 -m unittest discover -s tests -v. Node worker tested through integration script. No live network/model in unit tests.
- Use only supported Hermes APIs. No monkeypatching, no credential file reads. Model through ctx.llm. Import/register must have zero network, model calls or filesystem initialization.
- Runtime state belongs to profile-scoped plugin data, never install tree. Development overrides require explicit paths.
- Captured source and generated content are untrusted. Trusted renderer escapes text, validates URL/colors/layout, allows no arbitrary JS/CSS/HTML. Preview has no scripts or network.
- Public network only for source capture. Browser is fresh/no saved login. Block private destinations, redirects/subrequests, service workers, downloads and unsafe protocols. Document residual DNS/OS isolation limits truthfully.
- Every finding references evidence. No verdict from link counts or treating decorative alt text as conformance failures.
- Revision verification is tied to SHA256 of exact artifact bytes; revision changes invalidate prior verification. No generic passed score or conversion uplift claims.
- Generated factual text defaults to verbatim source selections. Bounded layout/color/spacing choices; deterministic checks separately from human review.
- No sample substitution on live failure. Fixture mode explicitly labeled, never automatic fallback.
- Keep unrelated workspaces and live Hermes untouched. Do not commit secrets, browser binaries, node_modules, captured third-party data or run artifacts.

## Workstream ownership
Core implementer: repager/models.py, store.py, renderer.py, service.py and corresponding tests.
Browser implementer: browser/*, repager/browser.py, tests/test_browser.py and package.json/package-lock.json.
Canvas implementer: dashboard/manifest.json, dashboard/dist/*, dashboard/src/* only.
Parent: __init__.py, plugin.yaml, repager/runtime.py, dashboard/plugin_api.py, docs, scripts and integration.
No shared-file edits without parent coordination. Do not git commit/push from subagents; parent reviews and commits.
