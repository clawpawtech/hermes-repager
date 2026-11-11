"""Fresh third-pass regressions with explicitly offline adapters."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from repager.service import ReviewService,ServiceError
from repager.store import ReviewStore
from test_core_service import FakeBrowser,FakeLLM,URL,approve_displayed,_source,_element

class ThirdPassTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=ReviewStore(Path(self.tmp.name));self.llm=FakeLLM();self.browser=FakeBrowser()
        self.s=ReviewService(self.store,self.browser,self.llm)
        self.r=self.s.create_review(URL);self.rid=self.r['id']

    def test_damaged_json_stays_visible_beside_healthy_review(self):
        other=self.s.create_review(URL);p=self.store.run_dir(self.rid)/f'{self.rid}.json';p.write_text('{broken')
        rows=self.s.list_reviews();self.assertEqual({r['id'] for r in rows},{self.rid,other['id']})
        damaged=next(r for r in rows if r['id']==self.rid)
        self.assertTrue(damaged['recovery_required']);self.assertIsNone(damaged['source']);self.assertIn('Recovery',damaged['error'])

    def test_unreadable_head_is_per_review_not_global_gallery_failure(self):
        other=self.s.create_review(URL);p=self.store.run_dir(self.rid)/'.head.json';p.unlink();p.mkdir()
        rows=self.s.list_reviews();self.assertEqual(len(rows),2)
        damaged=next(r for r in rows if r['id']==self.rid);self.assertTrue(damaged['recovery_required'])
        self.assertEqual(next(r for r in rows if r['id']==other['id'])['status'],'reviewed')

    def test_interrupted_initial_publication_is_discoverable(self):
        with patch.object(self.store,'create',side_effect=OSError('explicit simulated write failure')):
            with self.assertRaises(OSError):self.s.create_review(URL)
        rows=self.s.list_reviews();self.assertEqual(len(rows),2)
        self.assertTrue(any(r.get('recovery_required') for r in rows))

    def test_stale_approval_cannot_clear_newer_checked_decision(self):
        scope=self.s.preview_scope(self.rid)
        approve_displayed(self.s,self.rid,self.r['findings'][0]['id'],cta_id='a2')
        self.s.generate(self.rid);r=self.s.verify(self.rid);rev=r['revisions'][-1]
        checked=self.s.decide(self.rid,revision=rev['number'],artifact_hash=rev['artifact_hash'],verdict='undecided',reason='Synthetic newer decision.',verification_signature=r['verification']['signature'])
        with self.assertRaises(ServiceError):
            self.s.approve(self.rid,self.r['findings'][0]['id'],cta_id='a0',scope_hash=scope['scope_hash'],expected_version=self.r['version'])
        after=self.s.get_review(self.rid)
        self.assertEqual(after['version'],checked['version']);self.assertEqual(after['decision'],checked['decision'])

    def test_escaped_copy_budget_refuses_approval_before_inference(self):
        source=_source();elements=source['viewports'][0]['elements']
        elements[2:3]=[_element(f'p{i}','p','&'*4000) for i in range(8)]
        s=ReviewService(self.store,FakeBrowser(snapshot=source),self.llm);r=s.create_review(URL)
        with self.assertRaisesRegex((ValueError,ServiceError),'128 KiB'):
            approve_displayed(s,r['id'],r['findings'][0]['id'])
        self.assertEqual(self.llm.calls,[]);self.assertIsNone(s.get_review(r['id'])['contract'])
