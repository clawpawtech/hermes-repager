"""Unit tests for repager.models: shapes, validation and JSON schemas."""

import unittest

import repager.models as m


class TestValidateSource(unittest.TestCase):
    def test_fractional_negative_dom_rectangles_and_browser_limits(self):
        from test_core_service import _source
        source = _source(title='t' * 4000)
        element = source['viewports'][0]['elements'][0]
        element['rect'] = {'x': -0.5, 'y': 12.25, 'width': 100.125, 'height': 30.5}
        element['style']['font_family'] = 'f' * 300
        self.assertEqual(m.validate_source(source)['viewports'][0]['elements'][0]['rect'], element['rect'])
        for invalid in (float('nan'), float('inf'), True):
            element['rect']['width'] = invalid
            with self.assertRaises(ValueError):
                m.validate_source(source)

    def test_preview_minimal_shape_and_check_metadata(self):
        from test_core_service import _default_verify_report
        report = _default_verify_report()
        report.update(revision=1, artifact_hash='a' * 64)
        report['checks'][0]['attempted_requests'] = 2
        report['checks'][0]['denied_requests'] = 2
        out = m.validate_verification(report)
        self.assertEqual(out['viewports'], report['viewports'])
        self.assertEqual(out['checks'], report['checks'])

    def _snapshot(self, **kw):
        base = {
            "url": "https://example.com/",
            "title": "Example",
            "captured_at": "2026-11-06T00:00:00+00:00",
            "viewports": [],
            "palette": ["#111111", "#f7931a", "#ffffff"],
            "limitations": [],
        }
        base.update(kw)
        return base

    def test_valid(self):
        src = self._snapshot(viewports=[{
            "name": "desktop", "width": 1440, "height": 900,
            "screenshot": "source-desktop.png", "overflow": False,
            "elements": [{
                "id": "h0", "tag": "h1", "text": "Headline",
                "href": None, "rect": {"x": 0, "y": 0, "width": 100, "height": 20},
                "style": {"color": "#111111", "background_color": "#ffffff",
                          "font_size": "30px", "font_family": "system-ui"},
            }],
        }])
        out = m.validate_source(src)
        self.assertEqual(out["url"], "https://example.com/")
        self.assertEqual(len(out["viewports"]), 1)
        self.assertEqual(out["viewports"][0]["elements"][0]["tag"], "h1")

    def test_url_must_be_absolute(self):
        with self.assertRaises(ValueError):
            m.validate_source(self._snapshot(url="example.com"))

    def test_viewport_name_and_basename_screenshot(self):
        with self.assertRaises(ValueError):
            m.validate_source(self._snapshot(viewports=[{
                "name": "tablet", "width": 1000, "height": 800,
                "screenshot": "../source-desktop.png", "overflow": False,
                "elements": [],
            }]))

    def test_element_tag_and_href_constraints(self):
        with self.assertRaises(ValueError):
            m.validate_source(self._snapshot(viewports=[{
                "name": "desktop", "width": 1440, "height": 900,
                "screenshot": "source-desktop.png", "overflow": False,
                "elements": [{
                    "id": "a0", "tag": "custom-tag", "text": "x",
                    "href": "javascript:alert(1)", "rect": {"x": 0, "y": 0, "width": 1, "height": 1},
                    "style": {},
                }],
            }]))

    def test_palette_and_limitations(self):
        src = self._snapshot(palette=["#deadbeef"], limitations=["too long " * 40])
        with self.assertRaises(ValueError):
            m.validate_source(src)


class TestValidateFinding(unittest.TestCase):
    def test_valid(self):
        f = m.validate_finding({"id": "f1", "title": "x", "observation": "y",
                                "recommendation": "z", "evidence_ids": ["e1"],
                                "kind": "measurement"})
        self.assertEqual(f["kind"], "measurement")

    def test_bad_kind(self):
        with self.assertRaises(ValueError):
            m.validate_finding({"id": "f1", "title": "x", "observation": "y",
                                "recommendation": "z", "evidence_ids": [], "kind": "opinion"})


class TestValidateSectionSpec(unittest.TestCase):
    def _spec(self, **kw):
        base = {"headline_id": "h1", "body_ids": ["p1"], "cta_id": "a1",
                "layout": "stack", "alignment": "left", "spacing": "comfortable",
                "background": "#ffffff", "foreground": "#111111",
                "accent": "#f7931a", "button_text": "#ffffff", "evidence_ids": []}
        base.update(kw)
        return base

    def test_valid_full(self):
        out = m.validate_section_spec(self._spec())
        self.assertEqual(out["layout"], "stack")

    def test_invalid_layout_and_source_independent_colors(self):
        with self.assertRaises(ValueError):
            m.validate_section_spec(self._spec(layout="grid"))
        self.assertEqual(m.validate_section_spec(self._spec(accent='#ff0000'))['accent'], '#ff0000')
        with self.assertRaises(ValueError):
            m.validate_section_spec(self._spec(css='body{display:none}'))

    def test_missing_required_keys(self):
        partial = {k: v for k, v in self._spec().items() if k != "cta_id"}
        with self.assertRaises(ValueError):
            m.validate_section_spec(partial)

    def test_partial_model_output(self):
        partial = {"layout": "split", "alignment": "left", "spacing": "compact",
                   "background": "#000000", "foreground": "#ffffff",
                   "accent": "#f7931a", "button_text": "#ffffff",
                   "evidence_ids": ["f1"]}
        out = m.validate_section_spec(partial, allow_partial=True)
        self.assertEqual(out["layout"], "split")
        self.assertEqual(set(out.keys()), {"layout", "alignment", "spacing",
                                           "background", "foreground", "accent",
                                           "button_text", "evidence_ids"})

    def test_model_schema_authorization(self):
        schema = m.SECTION_SPEC_MODEL_SCHEMA
        self.assertEqual(schema["additionalProperties"], False)
        self.assertIn("button_text", schema["properties"])
        self.assertNotIn("cta_id", schema["properties"])


class TestValidateReview(unittest.TestCase):
    def _record(self, **kw):
        base = {
            "id": "0" * 32,
            "status": "reviewed",
            "created_at": "2026-11-06T00:00:00+00:00",
            "updated_at": "2026-11-06T00:00:00+00:00",
            "audience": "testers",
            "goal": "convert",
            "source": None,
            "findings": [],
            "contract": None,
            "revisions": [],
            "verification": None,
            "error": None,
        }
        base.update(kw)
        return base

    def test_valid_minimal(self):
        record = self._record()
        out = m.validate_review(record)
        self.assertEqual(out["status"], "reviewed")

    def test_bad_id_and_status(self):
        with self.assertRaises(ValueError):
            m.validate_review(self._record(id="nope", status="reviewed"))
        with self.assertRaises(ValueError):
            m.validate_review(self._record(id="0" * 31, status="reviewed"))
        with self.assertRaises(ValueError):
            m.validate_review(self._record(status="done"))

    def test_contract_and_revisions(self):
        record = self._record(contract={
            "finding_id": "f1", "preserve_copy": True,
            "preserve_destination": True, "approved_at": "2026-11-06T00:00:00+00:00",
            "cta_id": "a1",
        }, revisions=[{"number": 1, "created_at": "t", "artifact_hash": "a" * 64,
                       "html_file": "x.html", "section": TestValidateSectionSpec()._spec(), "instruction": ""}])
        out = m.validate_review(record)
        self.assertEqual(out["revisions"][0]["number"], 1)

    def test_failed_without_source(self):
        record = self._record(status="failed", source=None, error="capture failed")
        out = m.validate_review(record)
        self.assertIsNone(out["source"])
        self.assertIsNotNone(out["error"])


class TestSchemasStructure(unittest.TestCase):
    def test_full_schema_required_fields(self):
        schema = m.SECTION_SPEC_FULL_SCHEMA
        self.assertEqual(sorted(schema["required"]), sorted([
            "headline_id", "body_ids", "cta_id", "layout", "alignment", "spacing",
            "background", "foreground", "accent", "button_text",
        ]))

    def test_validation_error_message_content(self):
        with self.assertRaises(ValueError) as ctx:
            m.validate_section_spec({"layout": "stack"})
        self.assertIn("required", str(ctx.exception))
