"""Offline regressions for crash publication and resolver timeout boundaries."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_core_service import FakeBrowser, FakeLLM, URL, approve_displayed
from repager.browser import BrowserAdapter
from repager.service import ReviewService
from repager.store import ReviewStore, atomic_write

class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);self.store=ReviewStore(self.root)
        self.service=ReviewService(self.store,FakeBrowser(),FakeLLM())
        r=self.service.create_review(URL);self.rid=r['id']
        approve_displayed(self.service,self.rid,r['findings'][0]['id'])

    def test_restart_recovers_published_but_unrecorded_revision(self):
        def crash_after_publication(path,data,**kwargs):
            atomic_write(path,data,**kwargs)
            raise OSError('simulated crash after file publication')
        with patch('repager.service.atomic_write',side_effect=crash_after_publication):
            with self.assertRaises(OSError):self.service.generate(self.rid)
        filename=self.store.run_dir(self.rid)/f'{self.rid}-r1.html'
        published=filename.read_bytes()
        record=self.store.get(self.rid)
        assert record is not None
        self.assertEqual(record['revisions'],[])
        restarted=ReviewService(ReviewStore(self.root),FakeBrowser(),FakeLLM())
        result=restarted.generate(self.rid)
        self.assertEqual(result['revisions'][-1]['number'],1)
        orphans=list(filename.parent.glob('.orphan-*.html'))
        self.assertEqual(len(orphans),1)
        self.assertEqual(orphans[0].read_bytes(),published)
        restarted.verify(self.rid)
        self.assertTrue(restarted.export(self.rid).is_file())

    def test_record_committed_then_save_error_never_deletes_recorded_html(self):
        save=self.store.save
        def lost_ack(record):
            save(record)
            raise OSError('simulated acknowledgement loss after record publication')
        with patch.object(self.store,'save',side_effect=lost_ack):
            with self.assertRaises(OSError):self.service.generate(self.rid)
        record=self.store.get(self.rid)
        assert record is not None
        filename=self.store.run_dir(self.rid)/record['revisions'][-1]['html_file']
        self.assertTrue(filename.is_file(),'Never remove a possibly committed artifact during rollback')
        self.service.verify(self.rid)

    def test_capture_never_resolves_before_the_timed_worker(self):
        adapter=BrowserAdapter(timeout=1)
        with patch('repager.browser.socket.getaddrinfo',side_effect=AssertionError('unbounded resolver called')) as resolver:
            with patch.object(adapter,'_spawn_worker',return_value={'explicit_unit_result':True}) as worker:
                result=adapter.capture(URL,self.root/'capture')
                self.assertEqual(result,{'explicit_unit_result':True})
                worker.assert_called_once()
            resolver.assert_not_called()
