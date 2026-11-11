"""Authenticated API acceptance with explicit offline adapters; no live capture/model."""
import hashlib
import io
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from fastapi.testclient import TestClient
from repager.api import create_dev_app
from repager.runtime import Runtime
from test_core_service import FakeBrowser, FakeLLM, URL, approve_displayed

class LabAPITests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.llm = FakeLLM()
        self.runtime = Runtime(Path(tmp.name), FakeBrowser(), self.llm)
        self.addCleanup(self.runtime.close)
        token = 'explicit-unit-test-token-only-32-bytes'
        self.client = TestClient(create_dev_app(lambda: self.runtime, token=token))
        self.client.headers['Authorization'] = 'Bearer ' + token
        self.r = self.runtime.service.create_review(URL)
        self.rid = self.r['id']; self.base = '/api/plugins/repager/reviews/' + self.rid
        approve_displayed(self.runtime.service, self.rid, self.r['findings'][0]['id'])
        self.r = self.runtime.service.generate(self.rid)

    def finish(self, job):
        for _ in range(100):
            value = self.client.get('/api/plugins/repager/jobs/' + job['id']).json()['job']
            if value['state'] in ('completed', 'failed'): return value
            time.sleep(.01)
        self.fail('Offline operation did not finish')

    def remix_payload(self):
        rev = self.r['revisions'][-1]
        return {'base_revision': rev['number'], 'artifact_hash': rev['artifact_hash'], 'changes': {'layout': 'editorial'}}

    def test_new_routes_require_auth_and_refuse_cross_origin(self):
        self.client.headers.pop('Authorization')
        self.assertEqual(self.client.get('/api/plugins/repager/jobs').status_code, 401)
        self.assertEqual(self.client.get(self.base + '/report').status_code, 401)
        self.assertEqual(self.client.post(self.base + '/remix', json=self.remix_payload()).status_code, 401)
        self.client.headers['Authorization'] = 'Bearer explicit-unit-test-token-only-32-bytes'
        self.assertEqual(self.client.post(self.base + '/remix', json=self.remix_payload(), headers={'Origin': 'https://evil.example'}).status_code, 403)

    def test_local_remix_is_async_no_model_and_invalidates_export(self):
        self.runtime.service.verify(self.rid); self.llm.calls.clear()
        response = self.client.post(self.base + '/remix', json=self.remix_payload())
        self.assertEqual(response.status_code, 202, response.text)
        self.assertEqual(self.finish(response.json()['job'])['state'], 'completed')
        record = self.client.get(self.base).json()['review']
        self.assertEqual(record['revisions'][-1]['origin'], 'local-remix')
        self.assertEqual(self.llm.calls, [])
        self.assertEqual(self.client.get(self.base + '/export').status_code, 409)
        self.assertEqual(self.client.get(self.base + '/report').status_code, 409)
        self.assertTrue(self.client.get('/api/plugins/repager/jobs').json()['jobs'])

    def test_archived_preview_remains_authenticated_after_new_revision(self):
        r=self.runtime.service.verify(self.rid);receipt=r['verification'];name=receipt['viewports'][0]['screenshot']
        expected=self.runtime.service.read_artifact(self.rid,name)
        self.runtime.service.remix(self.rid,**self.remix_payload())
        response=self.client.get(self.base+'/artifacts/'+name)
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.content,expected)
        self.client.headers.pop('Authorization');self.assertEqual(self.client.get(self.base+'/artifacts/'+name).status_code,401)

    def test_failed_review_report_is_passive_and_zip_stays_blocked(self):
        self.runtime.service.browser.verify_report['checks'][0]['status']='fail';self.runtime.service.verify(self.rid)
        report=self.client.get(self.base+'/report');self.assertEqual(report.status_code,200,report.text)
        self.assertIn(b'Review only - failed checks',report.content);self.assertNotIn(b'<script',report.content)
        self.assertEqual(self.client.get(self.base+'/export').status_code,409)

    def test_approval_requires_strict_displayed_version_and_rejects_stale_post(self):
        scope=self.runtime.service.preview_scope(self.rid)
        body=dict(finding_id=self.r['findings'][0]['id'],cta_id=scope['default_cta_id'],scope_hash=scope['scope_hash'],preserve_copy=True,preserve_destination=True)
        self.assertEqual(self.client.post(self.base+'/approve',json=body).status_code,422)
        self.assertEqual(self.client.post(self.base+'/approve',json=dict(body,expected_version=True)).status_code,422)
        self.runtime.service.verify(self.rid)
        response=self.client.post(self.base+'/approve',json=dict(body,expected_version=scope['record_version']))
        self.assertEqual(response.status_code,409,response.text);self.assertIsNotNone(self.runtime.service.get_review(self.rid)['verification'])

    def test_remix_schema_rejects_copy_script_unknown_or_boolean_baseline(self):
        for payload in (dict(self.remix_payload(), changes={'headline_id': 'content-h'}),
                        dict(self.remix_payload(), changes={'css': 'display:none'}),
                        dict(self.remix_payload(), base_revision=True),
                        dict(self.remix_payload(), unexpected='no')):
            self.assertEqual(self.client.post(self.base + '/remix', json=payload).status_code, 422)

    def test_decision_report_and_zip_have_same_current_bytes_and_manifest(self):
        self.runtime.service.verify(self.rid)
        rev = self.r['revisions'][-1]
        body = {'verification_signature':self.runtime.service.get_review(self.rid)['verification']['signature'], 'revision': rev['number'], 'artifact_hash': rev['artifact_hash'], 'verdict': 'undecided',
                'reason': 'Automated acceptance test only; not a human or source-owner endorsement.'}
        response = self.client.post(self.base + '/decision', json=body)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['review']['decision']['verdict'], 'undecided')
        report = self.client.get(self.base + '/report')
        self.assertEqual(report.status_code, 200)
        self.assertIn('attachment;', report.headers['content-disposition'])
        self.assertEqual(report.headers['cache-control'], 'no-store')
        self.assertIn("default-src 'none'", report.headers['content-security-policy'])
        self.assertNotIn(b'<script', report.content)
        response = self.client.get(self.base + '/export')
        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            self.assertEqual(z.read('review.html'), report.content)
            sums = z.read('SHA256SUMS.txt').decode().splitlines()
            self.assertEqual(len(sums), len(z.namelist()) - 1)
            for line in sums:
                expected, name = line.split('  ', 1)
                self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(), expected)
        body['artifact_hash'] = '0' * 64
        self.assertEqual(self.client.post(self.base + '/decision', json=body).status_code, 409)
