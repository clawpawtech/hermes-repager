"""Explicit offline adapters: tests of invariants, never live browser evidence."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from repager import integrity
from repager.renderer import render_section
from repager.service import ReviewService, ServiceError
from repager.store import ReviewStore
from test_core_service import FakeBrowser, FakeLLM, URL, approve_displayed


class DesignLabTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = ReviewStore(Path(self.tmp.name))
        self.llm = FakeLLM()
        self.service = ReviewService(self.store, FakeBrowser(), self.llm)
        self.record = self.service.create_review(URL, 'designers', 'book a review')
        self.rid = self.record['id']
        approve_displayed(self.service, self.rid, self.record['findings'][0]['id'])

    def generated(self):
        return self.service.generate(self.rid)

    def raw(self):
        return self.store.run_dir(self.rid) / f'{self.rid}.json'

    def corrupt(self, mutate):
        record = json.loads(self.raw().read_text())
        mutate(record)
        self.raw().write_text(json.dumps(record))

    def test_approval_is_signed_and_binds_displayed_ids(self):
        record = self.service.get_review(self.rid)
        integrity.validate(self.store.root, record['contract'])
        self.corrupt(lambda r: r['contract'].update(headline_id='content-h', body_ids=['content-p']))
        with self.assertRaises(ServiceError):
            self.service.generate(self.rid)
        self.assertEqual(self.llm.calls, [])

    def test_old_history_metadata_tamper_is_not_laundered_in_current_export(self):
        self.generated()
        self.generated()
        self.service.verify(self.rid)
        self.corrupt(lambda r: r['revisions'][0].update(provider='forged-provider'))
        with self.assertRaises(ServiceError):
            self.service.export(self.rid)

    def test_signed_old_record_replay_is_rejected_by_independent_head(self):
        self.generated()
        self.service.verify(self.rid)
        old = self.raw().read_bytes()
        self.generated()
        self.raw().write_bytes(old)
        with self.assertRaises(ServiceError):
            self.service.export(self.rid)

    def test_remix_preserves_content_without_model_and_requires_new_checks(self):
        r = self.generated()
        r = self.service.verify(self.rid)
        old = copy.deepcopy(r['revisions'][-1])
        self.llm.calls.clear()
        r = self.service.remix(self.rid, base_revision=old['number'], artifact_hash=old['artifact_hash'], changes={'layout': 'editorial'})
        new = r['revisions'][-1]
        self.assertEqual(new['origin'], 'local-remix')
        self.assertEqual(new['parent_revision'], old['number'])
        self.assertIsNone(new['model'])
        self.assertEqual(self.llm.calls, [])
        self.assertIsNone(r['verification'])
        self.assertNotEqual(new['artifact_hash'], old['artifact_hash'])
        self.assertEqual(new['contract_hash'], old['contract_hash'])
        for key in ('headline_id', 'body_ids', 'cta_id'):
            self.assertEqual(new['section'][key], old['section'][key])
        with self.assertRaises(ServiceError):
            self.service.export(self.rid)

    def test_remix_rejects_stale_baseline_content_and_unknown_css(self):
        r = self.generated()['revisions'][-1]
        for changes in ({'headline_id': 'content-h'}, {'css': 'display:none'}, {}, {'layout': 'fake'}):
            with self.subTest(changes=changes), self.assertRaises((ServiceError, ValueError)):
                self.service.remix(self.rid, base_revision=r['number'], artifact_hash=r['artifact_hash'], changes=changes)
        with self.assertRaises(ServiceError):
            self.service.remix(self.rid, base_revision=50, artifact_hash=r['artifact_hash'], changes={'layout': 'spotlight'})
        with self.assertRaises(ServiceError):
            self.service.remix(self.rid, base_revision=r['number'], artifact_hash='0' * 64, changes={'layout': 'spotlight'})

    def test_restore_is_new_revision_not_reused_receipt(self):
        first = self.generated()['revisions'][-1]
        current = self.service.remix(self.rid, base_revision=1, artifact_hash=first['artifact_hash'], changes={'layout': 'split'})['revisions'][-1]
        r = self.service.remix(self.rid, base_revision=2, artifact_hash=current['artifact_hash'], from_revision=1, changes={})
        self.assertEqual(r['revisions'][-1]['number'], 3)
        self.assertEqual(r['revisions'][-1]['parent_revision'], 1)
        self.assertEqual(r['revisions'][-1]['section'], first['section'])
        self.assertIsNone(r['verification'])

    def test_decision_is_bound_to_current_checked_artifact_and_invalidated(self):
        r = self.generated()
        rev = r['revisions'][-1]
        kwargs = dict(verification_signature='0'*64, revision=rev['number'], artifact_hash=rev['artifact_hash'], verdict='prefer', reason='Explicit automated acceptance choice, not user endorsement.')
        with self.assertRaises(ServiceError):
            self.service.decide(self.rid, **kwargs)
        kwargs['verification_signature'] = self.service.verify(self.rid)['verification']['signature']
        r = self.service.decide(self.rid, **kwargs)
        integrity.validate(self.store.root, r['decision'])
        self.assertEqual(r['decision']['artifact_hash'], rev['artifact_hash'])
        with self.assertRaises(ServiceError):
            self.service.decide(self.rid, **dict(kwargs, artifact_hash='0' * 64))
        for bad in (dict(kwargs, reason=''), dict(kwargs, verdict='deploy')):
            with self.assertRaises(ValueError):
                self.service.decide(self.rid, **bad)
        r = self.service.remix(self.rid, base_revision=rev['number'], artifact_hash=rev['artifact_hash'], changes={'layout': 'spotlight'})
        self.assertIsNone(r.get('decision'))

    def test_four_layouts_are_distinct_and_keep_exact_copy(self):
        r = self.generated()
        source, spec = r['source'], r['revisions'][-1]['section']
        outputs = []
        for layout in ('stack', 'split', 'editorial', 'spotlight'):
            html = render_section(dict(spec, layout=layout), source)
            self.assertIn('Body copy &lt;b&gt;keep&lt;/b&gt;', html)
            self.assertIn('href="https://example.com/start"', html)
            self.assertNotIn('rp-note', html)
            self.assertNotIn('<script', html)
            outputs.append(html)
        self.assertEqual(len(set(outputs)), 4)

    def test_unreadable_manual_palette_is_rejected(self):
        r = self.generated()
        bad = dict(r['revisions'][-1]['section'], background='#ffffff', foreground='#ffffff', accent='#ffffff', button_text='#ffffff')
        with self.assertRaisesRegex(ValueError, 'contrast'):
            render_section(bad, r['source'])

    def test_model_color_repair_is_recorded_and_still_palette_bound(self):
        self.llm.result.update(background='#ffffff', foreground='#ffffff', accent='#ffffff', button_text='#ffffff')
        r = self.generated()
        rev = r['revisions'][-1]
        self.assertTrue(rev['safety_adjustments'])
        self.assertIn(rev['section']['foreground'], ('#000000', '#ffffff'))
        self.assertNotEqual(rev['section']['background'], rev['section']['foreground'])
        self.assertNotEqual(rev['section']['accent'], rev['section']['button_text'])
        integrity.validate(self.store.root, rev)

    def test_reject_checked_failure_without_permitting_prefer_or_export(self):
        r = self.generated()
        self.service.browser.verify_report['checks'][1]['status'] = 'fail'
        self.service.verify(self.rid)
        rev = r['revisions'][-1]
        args = dict(verification_signature=self.service.get_review(self.rid)['verification']['signature'], revision=rev['number'], artifact_hash=rev['artifact_hash'], reason='Explicit automated rejection test, not a real user preference.')
        with self.assertRaises(ServiceError):
            self.service.decide(self.rid, verdict='prefer', **args)
        record = self.service.decide(self.rid, verdict='reject', **args)
        self.assertEqual(record['decision']['verdict'], 'reject')
        with self.assertRaises(ServiceError): self.service.export(self.rid)
        self.assertIn(b'Review only - failed checks', self.service.report(self.rid))

    def test_legacy_or_incomplete_new_adapter_receipt_is_not_signed_as_current_proof(self):
        self.generated()
        report = self.service.browser.verify_report
        report.pop('protocol')
        with self.assertRaisesRegex(ServiceError, 'Legacy'):
            self.service.verify(self.rid)
        self.assertIsNone(self.service.get_review(self.rid)['verification'])
        report['protocol'] = 2
        report['checks'] = [c for c in report['checks'] if c['id'] != 'desktop-cta-contrast']
        with self.assertRaisesRegex(ServiceError, 'missing required'):
            self.service.verify(self.rid)

    def test_pending_head_recovers_lost_save_acknowledgement(self):
        real_save = self.store.save
        def lost_ack(record):
            real_save(record)
            raise OSError('explicit simulated lost acknowledgement')
        with patch.object(self.store, 'save', side_effect=lost_ack):
            with self.assertRaises(OSError):
                self.generated()
        recovered = self.service.get_review(self.rid)
        self.assertEqual(len(recovered['revisions']), 1)
        self.service.verify(self.rid)
        self.assertTrue(self.service.export(self.rid).is_file())

    def test_failed_record_save_retains_prior_head_and_good_receipt(self):
        self.generated()
        before = self.service.verify(self.rid)
        with patch.object(self.store, 'save', side_effect=OSError('explicit simulated failure before save')):
            with self.assertRaises(OSError):
                self.generated()
        after = self.service.get_review(self.rid)
        self.assertEqual(after['verification'], before['verification'])
        self.assertTrue(self.service.export(self.rid).is_file())


if __name__ == '__main__':
    unittest.main()
