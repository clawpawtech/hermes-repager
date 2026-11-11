"""Unit tests for repager.renderer: escaping, palette, layout, no external code."""

import unittest
from pathlib import Path
from typing import cast, Dict

import repager.models as m
from repager.renderer import render_section

PALETTE = ["#111111", "#f7931a", "#ffffff"]


def _source(title="Example", extra_viewports=(), elements=None, limitations=None):
    viewports = [{
        "name": "desktop", "width": 1440, "height": 900,
        "screenshot": "source-desktop.png", "overflow": False,
        "elements": elements or [{
            "id": "h0", "tag": "h1", "text": "Headline",
            "href": None,
            "rect": {"x": 0, "y": 0, "width": 100, "height": 20},
            "style": {"color": "#111111", "background_color": "#ffffff",
                      "font_size": "30px", "font_family": "system-ui"},
        }, {
            "id": "p1", "tag": "p", "text": "Body copy <b>keep</b>",
            "href": None,
            "rect": {"x": 0, "y": 25, "width": 400, "height": 20},
            "style": {"color": "#111111", "background_color": "#ffffff",
                      "font_size": "18px", "font_family": "system-ui"},
        }, {
            "id": "a1", "tag": "a", "text": "Book a review",
            "href": "https://example.com/start",
            "rect": {"x": 100, "y": 800, "width": 140, "height": 46},
            "style": {"color": "#f7931a", "background_color": "#ffffff",
                      "font_size": "17px", "font_family": "system-ui"},
        }],
    }] + list(extra_viewports)
    return {
        "url": "https://example.com/",
        "title": title,
        "captured_at": "2026-11-06T00:00:00+00:00",
        "viewports": viewports,
        "palette": PALETTE,
        "limitations": limitations or [],
    }


FULL_SPEC = {
    "headline_id": "h0", "body_ids": ["p1"], "cta_id": "a1",
    "layout": "stack", "alignment": "left", "spacing": "comfortable",
    "background": "#ffffff", "foreground": "#111111",
    "accent": "#f7931a", "button_text": "#000000",
    "evidence_ids": ["f1"],
}


class TestRenderStack(unittest.TestCase):
    def test_escapes_cta_text_in_both_layouts(self):
        src = _source()
        src['viewports'][0]['elements'][2]['text'] = '<img src=x onerror=alert(1)> & "Go"'
        for layout in ('stack', 'split'):
            html = render_section(dict(FULL_SPEC, layout=layout), src)
            self.assertIn('&lt;img src=x onerror=alert(1)&gt; &amp; &quot;Go&quot;', html)
            self.assertNotIn('<img', html)

    def test_validates_content_tags_and_desktop_ids(self):
        for key, value in (('headline_id', 'p1'), ('body_ids', ['h0']), ('body_ids', ['p1', 'p1'])):
            with self.assertRaises(ValueError):
                render_section(dict(FULL_SPEC, **{key: value}), _source())

    def test_responsive_css_and_inline_csp(self):
        html = render_section(dict(FULL_SPEC, layout='split'), _source())
        self.assertIn('@media(max-width:700px)', html)
        self.assertIn('grid-template-columns:minmax(0,1fr)', html)
        self.assertIn("style-src 'unsafe-inline'", html)
        self.assertIn("default-src 'none'", html)
        compact = render_section(dict(FULL_SPEC, spacing='compact'), _source())
        self.assertNotEqual(html, compact)

    def test_source_palette_not_hardcoded_orange(self):
        src = _source()
        src['palette'] = ['#123456', '#111111']
        html = render_section(dict(FULL_SPEC, accent='#123456', button_text='#ffffff'), src)
        self.assertIn('--rp-accent:#123456', html)
        with self.assertRaises(ValueError):
            render_section(FULL_SPEC, src)

    def test_source_copy_is_not_trimmed(self):
        src = _source()
        src['viewports'][0]['elements'][1]['text'] = '  exact body \n'
        html = render_section(FULL_SPEC, src)
        self.assertIn('>  exact body \n</p>', html)

    def test_full_standalone_document(self):
        html = render_section(FULL_SPEC, _source())
        self.assertIn("<!doctype html>", html)
        self.assertIn("Proposed section", html)
        self.assertIn("Headline", html)
        self.assertIn("Book a review", html)
        self.assertIn("https://example.com/start", html)
        self.assertIn('Body copy &lt;b&gt;keep&lt;/b&gt;', html)
        self.assertNotIn("first release", html)  # Disclosures belong in the report, not approved proposal copy.

    def test_escapes_inline_script_text(self):
        src = _source()
        src['viewports'][0]['elements'][1]['text'] = '</script><script>alert(1)</script>'
        html = render_section(FULL_SPEC, src)
        self.assertIn('&lt;/script&gt;', html)
        self.assertNotIn('<script>alert', html)

    def test_rejects_source_without_heading(self):
        src = _source(elements=[{
            "id": "p1", "tag": "p", "text": '</script><script>alert(1)</script>',
            "href": None, "rect": {"x": 0, "y": 0, "width": 10, "height": 10},
            "style": {},
        }, {
            "id": "a1", "tag": "a", "text": "Go",
            "href": "https://example.com/start", "rect": {"x": 0, "y": 0, "width": 10, "height": 10},
            "style": {},
        }])
        with self.assertRaises(ValueError):
            render_section(FULL_SPEC, src)

    def test_escapes_attribute_quotes(self):
        src = _source()
        src['viewports'][0]['elements'][2]['href'] = 'https://example.com/start"onmouseover="alert(1)'
        html = render_section(FULL_SPEC, src)
        self.assertIn("&quot;onmouseover=", html)
        self.assertNotIn('onmouseover="alert', html)

    def test_rejects_javascript_href(self):
        src = _source(elements=[{
            "id": "a1", "tag": "a", "text": "Go",
            "href": "javascript:alert(1)", "rect": {"x": 0, "y": 0, "width": 10, "height": 10},
            "style": {},
        }])
        with self.assertRaises(ValueError):
            render_section(FULL_SPEC, src)

    def test_rejects_out_of_palette_color(self):
        spec = dict(FULL_SPEC, accent="#ff0000")
        with self.assertRaises(ValueError):
            render_section(cast(Dict[str, object], spec), _source())

    def test_rejects_non_a_cta(self):
        src = _source(elements=[{
            "id": "a1", "tag": "button", "text": "Go",
            "href": "https://example.com/start", "rect": {"x": 0, "y": 0, "width": 10, "height": 10},
            "style": {},
        }])
        with self.assertRaises(ValueError):
            render_section(FULL_SPEC, src)

    def test_rejects_missing_heading(self):
        src = _source(elements=[{
            "id": "p1", "tag": "p", "text": "Body", "href": None,
            "rect": {"x": 0, "y": 0, "width": 10, "height": 10}, "style": {},
        }, {
            "id": "a1", "tag": "a", "text": "Go",
            "href": "https://example.com/start", "rect": {"x": 0, "y": 0, "width": 10, "height": 10},
            "style": {},
        }])
        with self.assertRaises(ValueError):
            render_section(FULL_SPEC, src)

    def test_rejects_missing_cta(self):
        spec = dict(FULL_SPEC, cta_id="nope")
        src = _source()
        with self.assertRaises(ValueError):
            render_section(cast(Dict[str, object], spec), src)

    def test_bound_font_sizes(self):
        html = render_section(FULL_SPEC, _source())
        self.assertIn("font-size:clamp(34px,4.5vw,64px)", html)
        self.assertIn("font-size:18px", html)
        self.assertIn("font-size:17px", html)

    def test_no_external_resources(self):
        html = render_section(FULL_SPEC, _source())
        self.assertNotIn("<script", html)
        self.assertNotIn("<link", html)
        self.assertNotIn("<iframe", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("url(", html)

    def test_stack_layout_classes(self):
        html = render_section(FULL_SPEC, _source())
        self.assertIn("rp-layout-stack", html)

    def test_split_layout_classes(self):
        spec = dict(FULL_SPEC, layout="split", alignment="left")
        html = render_section(spec, _source())
        self.assertIn("rp-layout-split", html)
        self.assertIn("rp-head", html)
        self.assertIn("rp-plot", html)

    def test_alignment_center(self):
        spec = dict(FULL_SPEC, alignment="center")
        html = render_section(spec, _source())
        self.assertIn("text-align:center", html)

    def test_static_csp(self):
        html = render_section(FULL_SPEC, _source())
        self.assertIn("Content-Security-Policy", html)
        self.assertIn("script-src 'none'", html)
        self.assertIn("connect-src 'none'", html)

    def test_viewport_preference(self):
        """Elements are resolved from desktop viewports first."""
        src = _source(extra_viewports=[{
            "name": "mobile", "width": 390, "height": 844,
            "screenshot": "source-mobile.png", "overflow": False,
            "elements": [{
                "id": "mobile-h0", "tag": "h1", "text": "MOBILE HEADLINE",
                "href": None, "rect": {"x": 0, "y": 0, "width": 10, "height": 10},
                "style": {},
            }, {
                "id": "mobile-a1", "tag": "a", "text": "MOBILE GO",
                "href": "https://example.com/mobile-start", "rect": {"x": 0, "y": 0, "width": 10, "height": 10},
                "style": {},
            }],
        }])
        html = render_section(FULL_SPEC, src)
        self.assertIn("Headline", html)          # desktop wins
        self.assertNotIn("MOBILE HEADLINE", html)
        self.assertIn("https://example.com/start", html)  # desktop CTA wins
