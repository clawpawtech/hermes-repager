# Plugin branding

The bundled project wordmark and favicon are owner-authorized. Required font notices are retained; see [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). No unrelated application code is included.

## Exact treatment

The live wordmark is **`re` + mirrored orange Manrope `g` + `ager`**. The 9-like character replaces the p-position. It is not a literal 9 and is not the later g in plain `repager`.

- Normal glyphs: Manrope 700; mirrored accent glyph: Manrope 800.
- Tracking: -0.02em. Accent: #F7931A.
- `dashboard/brand/wordmark.svg` contains actual font outlines, not a hand-drawn approximation. `currentColor` supplies readable light/dark ink. No font is required to display it.
- `dashboard/brand/favicon.svg` is byte-identical to the live public favicon. Its original Arial-based mirrored g is intentionally retained.
- Manrope's OFL notice is included alongside the assets. Font sources and authoring versions are recorded in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

`npm run build` embeds both assets in the self-contained native canvas bundle and the icon in the standalone workbench HTML. The private watch-page packager embeds the same assets. There are no runtime branding/font requests.

The app icon is used inside the plugin header. The standalone/plugin-owned pages use it as their favicon. **The shared Hermes shell's global favicon and built-in Lucide sidebar icon are not overridden.** Branding does not rewrite the third-party source page, generated client section, host configuration or another workspace.

The header wordmark is an accessible new-review button and cannot reset the workbench during a running job. Mobile layout and light/dark contrast were checked in actual Chromium at 390px and 1440px; this is not physical-phone verification.

## Rebuilding outlines (optional authoring step)

The checked-in SVG is sufficient for normal builds. To regenerate, provision `opentype.js@1.3.4` in a separate tooling prefix, download the exact static Manrope 700 and 800 files recorded in THIRD_PARTY_NOTICES.md, and run:

```bash
REPAGER_BRAND_TOOLS=/path/to/tooling/node_modules \
  node scripts/outline_brand.mjs Manrope-700.ttf Manrope-800.ttf new-wordmark.svg
```

The output must be a new file. Compare its third glyph, transforms, palette and notice before replacing the trusted asset. Never reuse an old brand kit without checking glyph placement against the live wordmark.

## Evidence

- Three offline branding regressions bind the bundle/favicon bytes and p-position.
- `scripts/verify_brand_ui.mjs` checks actual native render, loaded icon, orange glyph, no horizontal overflow and both themes at desktop/mobile widths, without inference.
- Local screenshots/receipts: `artifacts/brand-fluid/branding/` (gitignored).
