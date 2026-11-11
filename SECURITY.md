# Security policy

This is a pre-1.0 community plugin. Security fixes target the current 0.3 series; older snapshots should not be used as the latest supported build. There is no response-time or production-security guarantee.

## Report privately

Use [GitHub private vulnerability reporting](https://github.com/clawpawtech/hermes-repager/security/advisories/new).

Keep secrets, signed URLs, captured personal information and exploit details out of public issues. If private reporting is unavailable, open a minimal issue requesting a private contact channel without sensitive details.

Include the plugin commit, Hermes/Python/Node/Chromium versions, operating system, whether sandbox opt-out was used, and a minimal reproduction with secrets removed. Synthetic reproductions are preferred to captured personal data.

## Boundaries

Read the [detailed security model](docs/SECURITY.md) before enabling capture/model calls. Public-page capture is not an OS-level browser-exploit sandbox. Keep Chromium sandboxing on; opt out only with separate appropriate container/VM isolation. Generated previews disable scripts/network; local signatures are integrity controls, not external attestations.
