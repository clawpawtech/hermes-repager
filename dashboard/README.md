# repager canvas

Native Hermes web dashboard only: `manifest.json` declares a tab, `dist/index.js` registers through `window.__HERMES_PLUGINS__`, and `plugin_api.py` exposes the protected API router. The wrapper uses the host's React, not a second bundled copy. JSON uses `SDK.fetchJSON`; screenshots/downloads use `SDK.authedFetch`.

`npm run build` copies the self-contained IIFE source deterministically. The checked-in prebuilt bundle needs no runtime build or remote asset/CDN. Shadow DOM scopes styles; light/dark, mobile, named check states and failure recovery are built in. All captured text is escaped. Proposed HTML is in an empty-sandbox iframe until real browser screenshots exist; API artifact responses add a sandbox CSP and no-store headers.

The standalone `index.html` is served by the **authenticated loopback development app**, not a raw file server. Native `hermes repager` has the real host context; see the root README. There is no third-party WebUI embedding or Desktop SDK integration claim.
