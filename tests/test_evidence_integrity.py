"""Adversarial integrity regression; offline adapters are explicitly synthetic."""
import tempfile
import unittest
from pathlib import Path
from test_core_service import FakeBrowser, FakeLLM, URL, approve_displayed
from repager.store import ReviewStore
from repager.service import ReviewService, ServiceError

class EvidenceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=ReviewStore(Path(self.tmp.name))
        self.service=ReviewService(self.store,FakeBrowser(),FakeLLM())
        r=self.service.create_review(URL);self.rid=r['id'];self.finding=r['findings'][0]['id']
        approve_displayed(self.service,self.rid,self.finding)
        self.service.generate(self.rid)
        self.record=self.service.verify(self.rid)
    def test_preview_image_tamper_blocks_export(self):
        name=self.record['verification']['viewports'][0]['screenshot']
        (self.store.run_dir(self.rid)/name).write_bytes(b'altered image')
        with self.assertRaises(ServiceError):self.service.export(self.rid)
    def test_source_image_tamper_blocks_export(self):
        (self.store.run_dir(self.rid)/'source-desktop.png').write_bytes(b'altered original')
        with self.assertRaises(ServiceError):self.service.export(self.rid)
    def test_receipt_detail_tamper_blocks_export(self):
        record=self.store.get(self.rid);record['verification']['checks'][0]['detail']='invented receipt'
        self.store.save(record)
        with self.assertRaises(ServiceError):self.service.export(self.rid)
    def test_source_metadata_tamper_blocks_reapproval(self):
        record=self.store.get(self.rid);record['source']['title']='altered source'
        self.store.save(record)
        with self.assertRaises(ServiceError):approve_displayed(self.service,self.rid,self.finding)
    def test_bad_scope_hash_rejected(self):
        with self.assertRaises(ServiceError):approve_displayed(self.service,self.rid,self.finding,scope_hash='0'*64)
    def test_edited_revision_metadata_cannot_be_reverified(self):
        record=self.store.get(self.rid)
        assert record is not None
        record['revisions'][-1]['instruction']='forged model provenance'
        self.store.save(record)
        with self.assertRaises(ServiceError):self.service.verify(self.rid)
    def test_current_signed_artifacts_can_be_read(self):
        receipt=self.record['verification']
        self.assertEqual(len(receipt['signature']),64)
        for view in receipt['viewports']:
            self.assertTrue(self.service.read_artifact(self.rid,view['screenshot']))
