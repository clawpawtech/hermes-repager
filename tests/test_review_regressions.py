"""Concrete review regressions, explicit offline doubles only."""
import copy
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from repager.runtime import Runtime, register_plugin
from repager.service import ReviewService, ServiceError
from repager.store import ReviewStore
from test_core_service import FakeBrowser, FakeLLM, URL, _source, _element, approve_displayed

class ReviewRegressions(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)

    def test_revision_cap_refuses_before_model_or_publication(self):
        llm=FakeLLM();service=ReviewService(ReviewStore(self.root),FakeBrowser(),llm)
        r=service.create_review(URL);rid=r['id'];approve_displayed(service,rid,r['findings'][0]['id'])
        # Real service publication with explicit FakeLLM: preserve signatures,
        # journal and artifacts rather than fabricating unsigned history.
        for _ in range(50):
            service.generate(rid)
        llm.calls.clear()
        with self.assertRaisesRegex(ServiceError,'50 revisions'):
            service.generate(rid)
        self.assertEqual(llm.calls,[])
        self.assertFalse((service.store.run_dir(rid)/f'{rid}-r51.html').exists())

    def test_content_heading_cannot_bind_other_section_cta(self):
        src=_source();elems=src['viewports'][0]['elements']
        elems[1]['region']='content'
        service=ReviewService(ReviewStore(self.root),FakeBrowser(src),FakeLLM())
        r=service.create_review(URL)
        self.assertEqual(r['status'],'failed')
        self.assertIn('heading',r['error'])

    def test_distinct_semantic_containers_cannot_be_joined(self):
        src=_source();elems=src['viewports'][0]['elements']
        for e in elems:e['container_id']='desktop-container-2'
        elems[1]['container_id']='desktop-container-1'
        service=ReviewService(ReviewStore(self.root),FakeBrowser(src),FakeLLM())
        r=service.create_review(URL)
        self.assertEqual(r['status'],'failed')
        self.assertIn('CTA',r['error'])

    def test_native_sync_passes_review_id_and_releases_failed_slots(self):
        rt=Runtime(self.root,FakeBrowser(),FakeLLM());self.addCleanup(rt.close)
        def failing(review_id):
            self.assertEqual(review_id,'review-id')
            raise ServiceError('explicit test failure')
        with self.assertRaisesRegex(ServiceError,'explicit test failure'):
            rt.run_sync(failing,admission_review_id='review-id',review_id='review-id')
        self.assertEqual(rt._active,set())
        result=rt.run_sync(lambda review_id:{'id':review_id},admission_review_id='review-id',review_id='review-id')
        self.assertEqual(result,{'id':'review-id'})

    def test_native_and_dashboard_share_capacity(self):
        class Context:
            def __init__(self):self.tools={}
            def register_tool(self,**kw):self.tools[kw['name']]=kw
            def __getattr__(self,name):return lambda *a,**k:None
        rt=Runtime(self.root,FakeBrowser(),FakeLLM());self.addCleanup(rt.close)
        ctx=Context()
        with patch('repager.runtime.bind_context'):register_plugin(ctx)
        entered=threading.Event();release=threading.Event()
        def blocked():
            entered.set();release.wait(3);return {'id':'offline-job'}
        rt.submit(blocked)
        self.assertTrue(entered.wait(2))
        try:
            def capture(**kwargs):
                release.wait(3);return {'id':'native-offline'}
            with patch.object(rt.service,'create_review',side_effect=capture),patch('repager.runtime.get_runtime',return_value=rt):
                with ThreadPoolExecutor(max_workers=1) as pool:
                    first=pool.submit(ctx.tools['repager_capture']['handler'],{'url':URL})
                    import time
                    deadline=time.monotonic()+2
                    while len(rt._active)<2 and time.monotonic()<deadline:time.sleep(.005)
                    try:
                        result=json.loads(ctx.tools['repager_capture']['handler']({'url':URL}))
                        self.assertIn('Two repager jobs',result.get('error',''))
                    finally:release.set();first.result(3)
        finally:release.set()

if __name__=='__main__':unittest.main()
