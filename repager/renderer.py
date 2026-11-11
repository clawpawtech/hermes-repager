"""Trusted text-only section renderer.

``render_section(spec, source) -> str`` turns a validated ``SectionSpec`` and a
validated ``SourceSnapshot`` into a standalone HTML document that:

* contains the exact captured copy (headline, bodies, CTA text + destination),
  never model-substituted text,
* carries a static CSP, inlines no fonts/images, runs no scripts, makes no
  network request,
* binds layout and theme only from the sanctioned set (source palette plus
  neutral black/white),
* keeps text sizes bounded and escapes every string,
* fails clean (:class:`ValueError`) when a suitable heading or CTA cannot be
  resolved from the source.

The document is deliberately text-only in the first release: it never relies on
images, embedded fonts, or executable markup, and it is the artifact the
browser verifier opens for overflow/CTA checks.
"""

from __future__ import annotations

import html as _html
import re
from typing import Dict, List, cast

from . import models

__all__ = ["render_section", "prepare_readable_section", "contrast_ratio"]

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_FORBIDDEN_HREF = ("javascript:", "mailto:", "vbscript:", "data:", "blob:")
#: Sanctioned layout/theme choices in the source spec (enforced by validation).
_SANCTIONED_LAYOUTS = ("stack", "split", "editorial", "spotlight")
_SANCTIONED_ALIGNMENTS = ("left", "center")
_SANCTIONED_SPACINGS = ("compact", "comfortable")
#: Bound text sizes (px) for headings, bodies and the CTA button.
_BOUND_HEADING_PX = 64
_BOUND_BODY_PX = 18
_BOUND_BUTTON_PX = 17
_BOUND_MAX_WIDTH = 1180

#: Colours the model may choose, in addition to the source palette.
_NEUTRALS = {"#000000", "#ffffff"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _allowed_colors(source: Dict[str, object]) -> frozenset:
    palette = source.get("palette") or []
    return frozenset({str(c).lower() for c in palette}) | _NEUTRALS


def _esc(value: str) -> str:
    return _html.escape(str(value), quote=True)


def _relative_luminance(hex_color: str) -> float:
    """Relative luminance per WCAG 2.1 (``#RRGGBB``, case-insensitive)."""
    hex_color = hex_color.lstrip("#")
    parts = [int(hex_color[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def _lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (part for part in parts)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast_ratio(first: str, second: str) -> float:
    light, dark = sorted((_relative_luminance(first), _relative_luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def prepare_readable_section(spec, source):
    """Repair only model-selected text colors, explicitly recording each repair.

    Direct/manual rendering remains strict. Neutral black/white are already in
    the sanctioned palette; factual copy and destinations are never changed.
    """
    cleaned = models.validate_section_spec(spec)
    _validated(cleaned, source)  # Never launder out-of-palette model values.
    adjustments = []
    for text, background in (('foreground', 'background'), ('button_text', 'accent')):
        ratio = contrast_ratio(cleaned[text], cleaned[background])
        if ratio < 4.5:
            previous = cleaned[text]
            cleaned[text] = max(('#000000', '#ffffff'), key=lambda color: contrast_ratio(color, cleaned[background]))
            adjustments.append(f'Readability guard changed {text} from {previous} to {cleaned[text]}: requested contrast {ratio:.3f}:1 was below 4.5:1.')
    return cleaned, adjustments


def _resolve(source: Dict[str, object], wanted_ids: List[str]) -> List[Dict[str, object]]:
    """Resolve elements by id, desktop viewports first."""
    found: Dict[str, Dict[str, object]] = {}
    for vp in source.get("viewports") or []:
        if vp.get('name') != 'desktop':
            continue
        for elem in vp.get("elements") or []:
            eid = elem.get("id")
            if eid:
                found[eid] = elem
    missing = [eid for eid in wanted_ids if eid not in found]
    if missing:
        raise ValueError(f"section content unavailable in snapshot: {', '.join(missing)}")
    return [found[eid] for eid in wanted_ids]


def _validated(spec: Dict[str, object], source: Dict[str, object]) -> Dict[str, object]:
    """Validate spec values against the source palette; returns the extracted fields."""
    if not isinstance(spec, dict):
        raise ValueError("section spec must be an object")
    if not isinstance(source, dict):
        raise ValueError("source snapshot must be an object")
    allowed = _allowed_colors(source)

    headline_id = str(spec.get("headline_id"))
    body_ids = [str(b) for b in (spec.get("body_ids") or [])]
    cta_id = str(spec.get("cta_id"))
    layout = str(spec.get("layout"))
    alignment = str(spec.get("alignment"))
    spacing = str(spec.get("spacing"))
    background = str(spec.get("background"))
    foreground = str(spec.get("foreground"))
    accent = str(spec.get("accent"))
    button_text = str(spec.get("button_text"))

    if layout not in _SANCTIONED_LAYOUTS:
        raise ValueError(f"section.layout is not one of {sorted(_SANCTIONED_LAYOUTS)}")
    if alignment not in _SANCTIONED_ALIGNMENTS:
        raise ValueError(f"section.alignment is not one of {sorted(_SANCTIONED_ALIGNMENTS)}")
    if spacing not in _SANCTIONED_SPACINGS:
        raise ValueError(f"section.spacing is not one of {sorted(_SANCTIONED_SPACINGS)}")

    for name, value in (("background", background), ("foreground", foreground),
                        ("accent", accent), ("button_text", button_text)):
        if not _HEX.match(value) or value.lower() not in allowed:
            raise ValueError(
                f"section.{name} #{value} is not in the source palette plus neutral black/white"
            )

    return {
        "headline_id": headline_id,
        "body_ids": body_ids,
        "cta_id": cta_id,
        "layout": layout,
        "alignment": alignment,
        "spacing": spacing,
        "background": background,
        "foreground": foreground,
        "accent": accent,
        "button_text": button_text,
    }


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------
def render_section(spec: Dict[str, object], source: Dict[str, object]) -> str:
    """Render a validated section spec against the captured source snapshot."""
    spec = models.validate_section_spec(spec)
    source = models.validate_source(source)
    fields = _validated(spec, source)
    headline_id = fields["headline_id"]
    body_ids = cast(List[str], fields["body_ids"])
    cta_id = fields["cta_id"]
    layout = fields["layout"]
    alignment = fields["alignment"]
    background = fields["background"]
    foreground = fields["foreground"]
    accent = fields["accent"]
    button_text = fields["button_text"]

    # --- resolve exact captured text ------------------------------------
    headline = _resolve(source, [cast(str, headline_id)])
    bodies = _resolve(source, cast(List[str], body_ids))
    cta = _resolve(source, [cast(str, cta_id)])
    if headline[0].get('tag') not in ('h1', 'h2') or not headline[0].get('text'):
        raise ValueError('headline must be a captured h1/h2')
    if any(b.get('tag') != 'p' or not b.get('text') for b in bodies):
        raise ValueError('body must contain captured paragraphs only')
    if len(set(body_ids)) != len(body_ids):
        raise ValueError('duplicate body ids')
    if cta[0].get("tag") != "a":
        raise ValueError(f"cta {cta_id!r} is not a navigable <a> element in the source")
    cta_text = str(cta[0].get("text") or "")
    cta_href = str(cta[0].get("href") or "")
    if not cta_text.strip():
        raise ValueError(f"cta {cta_id!r} has no visible text in the source")
    if not cta_href.startswith(("http://", "https://")):
        raise ValueError(f"cta {cta_id!r} has no usable destination in the source")
    if any(cta_href.lower().startswith(p) for p in _FORBIDDEN_HREF):
        raise ValueError(f"cta {cta_id!r} destination is not navigable (blocked scheme)")

    for label, text_color, surface in (('body/background', foreground, background), ('CTA text/background', button_text, accent)):
        ratio = contrast_ratio(cast(str, text_color), cast(str, surface))
        if ratio < 4.5:
            raise ValueError(f'{label} contrast {ratio:.3f}:1 is below 4.5:1; choose a readable palette combination')
    effective_button_text = button_text
    cta_text = _esc(cta_text)

    # --- scoped styles only; model-authored CSS is never emitted ----------
    def scoped_styles() -> str:
        return (
            f":root {{ --rp-bg:{background}; --rp-ink:{foreground}; "
            f"--rp-accent:{accent}; --rp-btn-text:{effective_button_text}; }}"
            f"*{{box-sizing:border-box}}"
            f"body{{background:var(--rp-bg);color:var(--rp-ink);"
            f"font-family:system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"
            f"margin:0;padding:24px;line-height:1.6}}"
            f".rp-section{{max-width:{_BOUND_MAX_WIDTH}px;margin:0 auto;overflow-wrap:anywhere;min-width:0}}"
            f".rp-section>*{{min-width:0}}"
            f".rp-section{{padding:{'24px' if fields['spacing'] == 'compact' else '64px'} 0}}"
            f".rp-section h1,.rp-section h2{{font-size:clamp(34px,4.5vw,{_BOUND_HEADING_PX}px);"
            f"max-width:22ch;line-height:1.08;font-weight:750;letter-spacing:-0.035em;"
            f"margin:0 0 0.6em;text-align:{alignment};text-wrap:balance;}}"
            f".rp-section .rp-body{{font-size:{_BOUND_BODY_PX}px;max-width:65ch;margin:0 0 0.9em;text-align:{alignment};}}"
            f"{'.rp-section .rp-head,.rp-section .rp-body{margin-inline:auto}' if alignment == 'center' else ''}"
            f".rp-section .rp-cta{{text-align:{alignment};margin-top:1em}}"
            f"a.rp-cta-link{{display:inline-block;Background:var(--rp-accent);color:var(--rp-btn-text);"
            f"padding:12px 20px;border-radius:8px;text-decoration:none;font-size:{_BOUND_BUTTON_PX}px;"
            f"font-weight:700;min-height:44px;min-width:44px;border:1px solid var(--rp-ink)}}"
            f"a:focus-visible{{outline:3px solid var(--rp-ink);outline-offset:4px}}"
            f".rp-layout-split{{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:48px;align-items:center}}"
            f"@media(max-width:700px){{.rp-layout-split{{grid-template-columns:minmax(0,1fr);gap:16px}}body{{padding:16px}}}}"
            f".rp-layout-center{{text-align:center}}"
            f".rp-layout-editorial{{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:64px;align-items:end;border-top:1px solid currentColor;padding-top:40px}}"
            f".rp-layout-editorial .rp-head{{font-family:ui-serif,Georgia,'Times New Roman',serif;font-size:clamp(38px,6vw,88px);font-weight:500;max-width:16ch;letter-spacing:-.035em;line-height:1.02;margin-bottom:0}}"
            f".rp-layout-spotlight{{border:1px solid currentColor;border-radius:24px;padding:clamp(28px,6vw,80px);margin-top:24px}}"
            f".rp-layout-spotlight .rp-head{{font-size:clamp(38px,6vw,84px);max-width:20ch}}"
            f".rp-layout-split .rp-plot{{border:1px solid currentColor;border-radius:16px;padding:clamp(24px,3vw,40px)}}"
            f"@media(max-width:700px){{.rp-layout-editorial{{grid-template-columns:minmax(0,1fr);gap:28px}}.rp-layout-spotlight{{padding:28px 20px;border-radius:16px;margin-top:8px}}.rp-layout-split .rp-plot{{padding:24px}}}}"
        )

    css = scoped_styles()

    # --- markup ----------------------------------------------------------
    def field(elem: Dict[str, object]) -> str:
        return _esc(str(elem.get("text") or ""))

    if layout in ("split", "editorial"):
        head = f'<h1 class="rp-head">{field(headline[0])}</h1>'
        plot = "".join(f'<p class="rp-body">{field(b)}</p>' for b in bodies)
        cta_block = (
            f'<p class="rp-cta"><a class="rp-cta-link" href="{_esc(cta_href)}">{cta_text}</a></p>'
        )
        wrapper = f'<section class="rp-section rp-layout-{layout}">{head}<div class="rp-plot">{plot}{cta_block}</div></section>'
    else:
        parts = [f'<h1 class="rp-head">{field(headline[0])}</h1>']
        parts.extend(f'<p class="rp-body">{field(b)}</p>' for b in bodies)
        parts.append(
            f'<p class="rp-cta"><a class="rp-cta-link" href="{_esc(cta_href)}">{cta_text}</a></p>'
        )
        wrapper = f'<section class="rp-section rp-layout-{layout}">{"".join(parts)}</section>'

    csp = (
        "default-src 'none'; style-src 'unsafe-inline'; script-src 'none'; object-src 'none'; "
        "frame-ancestors 'none'; connect-src 'none'; "
        "img-src 'none'; base-uri 'none'; form-action 'none';"
    )

    doc = (
        "<!doctype html>"
        '<html lang="en">'
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<meta http-equiv="Content-Security-Policy" content="{csp}">'
        f'<title>Proposed section - {_esc(str(source.get("title") or "repager proposal"))}</title>'
        f"<style>{css}</style>"
        "</head>"
        "<body>"
        f"<main>{wrapper}</main>"
        "</body>"
        "</html>"
    )
    return doc
