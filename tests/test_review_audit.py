"""Signed audit events retain superseded evidence, never current export authority."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from repager.service import ReviewService, ServiceError
from repager.store import ReviewStore
from repager import integrity
from test_core_service import FakeBrowser, FakeLLM, URL, approve_displayed

class ReviewAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=ReviewStore(Path(self.tmp.name));self.browser=FakeBrowser();self.llm=FakeLLM()
        self.s=ReviewService(self.store,self.browser,self.llm)
        r=self.s.create_review(URL);self.rid=r['id'];approve_displayed(self.s,self.rid,r['findings'][0]['id'])
        self.s.generate(self.rid)

    def choose(self,verdict='prefer',reason='Explicit synthetic review choice, not a real preference.'):
        rev=self.s.get_review(self.rid)['revisions'][-1]
        return self.s.decide(self.rid,revision=rev['number'],artifact_hash=rev['artifact_hash'],verdict=verdict,reason=reason,verification_signature=self.s.get_review(self.rid)['verification']['signature'])

    def test_checks_and_reasons_survive_revision_and_restart_without_becoming_current(self):
        r=self.s.verify(self.rid);receipt=copy.deepcopy(r['verification']);r=self.choose();decision=copy.deepcopy(r['decision'])
        r=self.s.remix(self.rid,base_revision=1,artifact_hash=r['revisions'][0]['artifact_hash'],changes={'layout':'editorial'})
        self.assertIsNone(r['verification']);self.assertIsNone(r['decision'])
        events=r['review_events'];self.assertEqual([e['kind'] for e in events],['verification','decision'])
        self.assertEqual(events[0]['payload'],receipt);self.assertEqual(events[1]['payload'],decision)
        self.assertEqual(decision['verification_signature'],receipt['signature'])
        for e in events: integrity.validate(self.store.root,e)
        again=ReviewService(ReviewStore(self.store.root),self.browser,self.llm).get_review(self.rid)
        self.assertEqual(again['review_events'],events)
        with self.assertRaises(ServiceError):self.s.export(self.rid)

    def test_recheck_and_changed_choice_retain_original_events(self):
        self.s.verify(self.rid);first=self.choose('reject','Synthetic: this direction is too dense.')
        self.choose('undecided','Synthetic: revisit the spacing before choosing.')
        r=self.s.verify(self.rid)
        self.assertIsNone(r['decision'])
        self.assertEqual([e['kind'] for e in r['review_events']],['verification','decision','decision','verification'])
        self.assertEqual(r['review_events'][1]['payload'],first['decision'])

    def test_failed_recheck_keeps_historical_choice_and_image(self):
        r=self.s.verify(self.rid);name=r['verification']['viewports'][0]['screenshot'];image=self.s.read_artifact(self.rid,name)
        self.choose('reject','Synthetic prior choice survives browser failure.');self.browser.verify_exc=RuntimeError('Explicit synthetic browser outage')
        with self.assertRaises(ServiceError):self.s.verify(self.rid)
        r=self.s.get_review(self.rid);self.assertIsNone(r['verification']);self.assertIsNone(r['decision'])
        self.assertEqual(r['review_events'][1]['payload']['reason'],'Synthetic prior choice survives browser failure.')
        self.assertEqual(self.s.read_artifact(self.rid,name),image)
        with self.assertRaises(ServiceError):self.s.export(self.rid)

    def test_pretrail_current_receipt_migrates_without_invented_prior_history(self):
        self.s.verify(self.rid);r=self.choose();receipt=copy.deepcopy(r['verification']);choice=copy.deepcopy(r['decision'])
        # Explicit trusted fixture constructing the shipped pre-trail record shape.
        del r['review_events'];self.s._save(r)
        r=self.s.remix(self.rid,base_revision=1,artifact_hash=r['revisions'][0]['artifact_hash'],changes={'layout':'editorial'})
        self.assertEqual([e['payload'] for e in r['review_events']],[receipt,choice])

    def test_old_screenshot_tamper_blocks_handoff_without_laundering_history(self):
        r=self.s.verify(self.rid);name=r['verification']['viewports'][0]['screenshot']
        self.s.remix(self.rid,base_revision=1,artifact_hash=r['revisions'][0]['artifact_hash'],changes={'layout':'editorial'})
        self.s.verify(self.rid);(self.store.run_dir(self.rid)/name).write_bytes(b'Explicit synthetic tamper')
        with self.assertRaises(ServiceError):self.s.read_artifact(self.rid,name)
        with self.assertRaises(ServiceError):self.s.export(self.rid)

    def test_event_cap_refuses_model_and_browser_work_without_erasing_evidence(self):
        r=self.s.verify(self.rid);template=copy.deepcopy(r['review_events'][0]);events=[]
        for index in range(500):
            e=copy.deepcopy(template);e['sequence']=index+1;e['payload']['checked_at']=f'2026-01-01T00:00:00.{index:06d}+00:00'
            e['payload']['signature']=integrity.sign(self.store.root,e['payload']);e['signature']=integrity.sign(self.store.root,e);events.append(e)
        r['review_events']=events;r['verification']=events[-1]['payload'];r=self.s._save(r)
        self.llm.calls.clear();self.browser.calls.clear()
        for operation in (self.s.generate,self.s.verify):
            with self.assertRaisesRegex(ServiceError,'500 review events'):operation(self.rid)
        self.assertEqual(self.llm.calls,[]);self.assertEqual(self.browser.calls,[])
        after=self.s.get_review(self.rid);self.assertEqual(after['version'],r['version']);self.assertIsNotNone(after['verification'])

    def test_modern_seals_cannot_be_downgraded_by_deleting_head_and_marker(self):
        self.s.verify(self.rid)
        path=self.store.run_dir(self.rid)/f'{self.rid}.json';r=json.loads(path.read_text());r.pop('integrity_version')
        path.write_text(json.dumps(r));(path.parent/'.head.json').unlink()
        with self.assertRaises(ServiceError):self.s.get_review(self.rid)

    def test_same_revision_recheck_rejects_choice_against_unseen_receipt(self):
        seen=self.s.verify(self.rid);receipt=seen['verification'];rev=seen['revisions'][-1]
        current=self.s.verify(self.rid);self.assertNotEqual(receipt['signature'],current['verification']['signature'])
        with self.assertRaisesRegex(ServiceError,'Checks changed'):
            self.s.decide(self.rid,revision=rev['number'],artifact_hash=rev['artifact_hash'],verification_signature=receipt['signature'],verdict='undecided',reason='Synthetic reason composed against old checks.')
        after=self.s.get_review(self.rid);self.assertEqual(after['version'],current['version']);self.assertIsNone(after.get('decision'))

    def test_reapproval_does_not_erase_previous_scope_history(self):
        self.s.verify(self.rid);old=self.choose();scope=self.s.preview_scope(self.rid)
        r=self.s.approve(self.rid,old['findings'][0]['id'],cta_id=scope['default_cta_id'],scope_hash=scope['scope_hash'],expected_version=scope['record_version'])
        self.assertEqual(len(r['review_events']),2);self.assertIsNone(r['decision']);self.assertIsNone(r['verification'])

    def test_payload_edit_is_rejected_by_head_and_individual_event_seal(self):
        self.s.verify(self.rid);self.choose()
        path=self.store.run_dir(self.rid)/f'{self.rid}.json';raw=json.loads(path.read_text())
        raw['review_events'][1]['payload']['reason']='forged';path.write_text(json.dumps(raw))
        with self.assertRaises(ServiceError):self.s.get_review(self.rid)

    def test_report_preserves_prior_reason_but_not_as_current_endorsement(self):
        r=self.s.verify(self.rid);self.choose('reject','Synthetic historical reason: too dense.')
        self.s.remix(self.rid,base_revision=1,artifact_hash=r['revisions'][0]['artifact_hash'],changes={'layout':'editorial'})
        self.s.verify(self.rid);report=self.s.report(self.rid).decode()
        self.assertIn('Synthetic historical reason: too dense.',report)
        self.assertIn('Historical review trail',report)
        self.assertIn('Not current export authority',report)
