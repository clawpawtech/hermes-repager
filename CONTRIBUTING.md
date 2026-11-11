# Contributing

Keep changes small and evidence-backed. For a larger change, open an issue describing the user problem and supported Hermes API before adding machinery. Contributions to the original code are accepted under the repository's MIT license; retain applicable third-party notices.

## Local checks

Use Python 3.11 or newer and Node 20 or newer:

```bash
python3 -m pip install -r requirements-dev.txt
npm ci --ignore-scripts --no-audit --no-fund
npm run build
python3 scripts/run_tests.py --receipt artifacts/python-tests.json
npm test
hermes plugins validate . --json
```

Prefer a disposable Python environment. Offline runs explicitly skip browser/public-network tests; [README](README.md) documents the separate opt-ins. Live model runs require additional consent and consume the operator's host quota. Never claim an offline fixture is a successful real capture.

## Invariants

- Supported Hermes APIs only; host-owned model transport and profile-scoped state.
- Closed trusted renderer, exact approved copy/CTA, revision/receipt-bound checks and explicit human decisions.
- No runtime source updates, credential-file reads, login bypasses or relaxed capture network policy.
- Do not commit credentials, runtime state, third-party captures, browser binaries, dependencies or run artifacts.
- Use project handles, not real names or identifying collaborator narratives, in public materials.
- Regenerate checked-in dashboard assets after source changes. Add a regression for behavioral fixes and describe remaining verification limits.

Report vulnerabilities through the [private security channel](SECURITY.md), not public reproduction details.
