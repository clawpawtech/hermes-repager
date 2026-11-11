"""Approval must name the inspected proposal and explicitly select its CTA."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_core_service import FakeBrowser, FakeLLM, URL
from repager.service import ReviewService, ServiceError
from repager.store import ReviewStore
from repager.runtime import register_plugin


class ApprovalBindingTests(unittest.TestCase):
    def setUp(self):
        directory=tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.service=ReviewService(ReviewStore(Path(directory.name)),FakeBrowser(),FakeLLM())
        record=self.service.create_review(URL)
        self.rid=record['id']; self.finding=record['findings'][0]['id']
        self.scope=self.service.preview_scope(self.rid)

    def test_missing_empty_or_wrong_binding_is_rejected_without_mutation(self):
        good={'cta_id':self.scope['default_cta_id'],'scope_hash':self.scope['scope_hash']}
        for bad in [{}, {'cta_id':good['cta_id']}, {'scope_hash':good['scope_hash']},
                    dict(good,cta_id=None),dict(good,cta_id=''),
                    dict(good,scope_hash=None),dict(good,scope_hash=''),dict(good,scope_hash='0'*64)]:
            with self.subTest(binding=bad):
                with self.assertRaises((TypeError,ValueError,ServiceError)):
                    self.service.approve(self.rid,self.finding,**bad)
                self.assertIsNone(self.service.get_review(self.rid)['contract'])

    def test_explicit_non_default_candidate_is_preserved(self):
        chosen=self.scope['cta_candidates'][1]
        record=self.service.approve(self.rid,self.finding,scope_hash=self.scope['scope_hash'],cta_id=chosen['id'],expected_version=self.scope['record_version'])
        self.assertEqual(record['contract']['cta_id'],chosen['id'])
        self.assertEqual(record['contract']['cta_destination'],chosen['destination'])

    def test_native_schema_requires_scope_and_cta(self):
        class Context:
            def __init__(self):self.tools={}
            def register_tool(self,**kwargs):self.tools[kwargs['name']]=kwargs
            def register_auxiliary_task(self,*args,**kwargs):pass
            def register_cli_command(self,*args,**kwargs):pass
            def register_skill(self,*args,**kwargs):pass
            def on_unload(self,*args,**kwargs):pass
        ctx=Context()
        with patch('repager.runtime.bind_context'):
            register_plugin(ctx)
        required=ctx.tools['repager_approve']['schema']['parameters']['required']
        self.assertIn('cta_id',required)
        self.assertIn('scope_hash',required)
