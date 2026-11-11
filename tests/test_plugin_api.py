"""API contract tests with EXPLICIT injected test doubles, never live evidence."""
import copy
import hashlib
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

try:
    from fastapi.testclient import TestClient
except ImportError:
    raise unittest.SkipTest("API tests require the declared FastAPI dependencies")

from repager.api import create_dev_app
from repager.runtime import Runtime, check_model_policy


def source():
    rect = {"x": 20, "y": 50, "width": 200, "height": 40}
    elements = [
        {"id": "desktop-h", "tag": "h1", "text": "Evidence, not promises", "href": None, "rect": rect, "style": {}},
        {"id": "desktop-p", "tag": "p", "text": "This is a labeled unit-test source.", "href": None, "rect": rect, "style": {}},
        {"id": "desktop-a", "tag": "a", "text": "Read the brief", "href": "https://example.com/start/", "rect": rect, "style": {}},
    ]
    return {"url": "https://example.com/", "title": "Unit test source", "captured_at": "2026-11-07T00:00:00+00:00", "viewports": [{"name": name, "width": width, "height": height, "screenshot": f"source-{name}.png", "overflow": False, "elements": copy.deepcopy(elements) if name == "desktop" else []} for name,width,height in [("desktop",1440,900),("mobile",390,844)]], "palette": ["#111111", "#ffffff"], "limitations": ["Synthetic unit fixture, not live evidence."]}


class TestBrowser:
    executable_path = None
    def capture(self, url, output_dir):
        record = source()
        for v in record["viewports"]:
            (Path(output_dir) / v["screenshot"]).write_bytes(__import__("synthetic_png").PNG)
        return record
    def verify(self, html, expected_cta, output_dir, **_kwargs):
        assert expected_cta == "https://example.com/start/"
        viewports=[]
        checks=[{"id":"preview-no-network","label":"Preview network policy","status":"pass","detail":"Unit test double only."}]
        for name,width,height in [("desktop",1440,900),("mobile",390,844)]:
            screenshot=f"preview-{name}.png"
            (Path(output_dir)/screenshot).write_bytes(__import__("synthetic_png").PNG)
            viewports.append({"name":name,"width":width,"height":height,"screenshot":screenshot,"overflow":False})
            for kind in ["cta-destination","keyboard-focusable","horizontal-overflow","visible-content","vertical-extent","scripts-disabled","headline-copy","body-copy","cta-label","heading-contrast","body-contrast","cta-contrast","cta-target","cta-complete"]:
                checks.append({"id":name+"-"+kind,"label":kind,"status":"pass","detail":"Unit test double only."})
        return {"protocol":2,"checked_at":"2026-11-07T00:00:00+00:00","checks":checks,"viewports":viewports,"limitations":["Injected test double; not browser evidence."]}


class TestLlm:
    def complete_structured(self, **kwargs):
        data={"layout":"stack","alignment":"left","spacing":"comfortable","background":"#ffffff","foreground":"#111111","accent":"#111111","button_text":"#ffffff","evidence_ids":[]}
        return SimpleNamespace(parsed=data, model="unit-test",provider="unit-test",usage=SimpleNamespace(input_tokens=0,output_tokens=0))


class TestApi(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.rt=Runtime(self.tmp.name,TestBrowser(),TestLlm())
        self.token="test-only-token-not-a-real-credential-123"
        self.app=create_dev_app(lambda:self.rt,token=self.token)
        self.client=TestClient(self.app)
        self.client.headers["Authorization"]="Bearer "+self.token
    def tearDown(self):
        self.client.close()
        self.rt.close()
        self.tmp.cleanup()
    def done(self, response):
        self.assertEqual(response.status_code,202,response.text)
        jid=response.json()["job"]["id"]
        limit=time.monotonic()+3
        while time.monotonic()<limit:
            job=self.client.get("/api/plugins/repager/jobs/"+jid).json()["job"]
            if job["state"] in {"completed","failed"}:
                self.assertEqual(job["state"],"completed",job)
                return self.client.get("/api/plugins/repager/reviews/"+job["review_id"]).json()["review"]
            time.sleep(.005)
        self.fail("Unit job did not finish within bounded timeout")
    def capture(self):
        return self.done(self.client.post("/api/plugins/repager/reviews",json={"url":"https://example.com/","audience":"testers","goal":"inspect"}))
    def test_development_requires_auth_and_host(self):
        with TestClient(self.app) as other:
            self.assertEqual(other.get("/api/plugins/repager/health").status_code,401)
            self.assertEqual(other.post("/dev/login",json={"token":"wrong"}).status_code,401)
            self.assertEqual(other.post("/dev/login",json={"token":self.token}).status_code,204)
            self.assertEqual(other.get("/api/plugins/repager/health").status_code,200)
            self.assertEqual(other.get("/",headers={"Host":"attacker.test"}).status_code,403)
    def test_cross_origin_and_schema_validation(self):
        url="/api/plugins/repager/reviews"
        self.assertEqual(self.client.post(url,json={"url":"https://example.com"},headers={"Origin":"https://attacker.test"}).status_code,403)
        self.assertEqual(self.client.post(url,content="url=x",headers={"Content-Type":"text/plain"}).status_code,415)
        self.assertEqual(self.client.post(url,json={"url":"https://example.com","model":"free"}).status_code,422)
    def test_approval_requires_both_displayed_scope_and_cta(self):
        record=self.capture();base="/api/plugins/repager/reviews/"+record['id']
        scope=self.client.get(base+'/scope').json()['scope']
        good={'finding_id':record['findings'][0]['id'],'preserve_copy':True,'preserve_destination':True,
              'cta_id':scope['default_cta_id'],'scope_hash':scope['scope_hash'],'expected_version':scope['record_version']}
        for missing in ['cta_id','scope_hash','expected_version']:
            payload={k:v for k,v in good.items() if k != missing}
            self.assertEqual(self.client.post(base+'/approve',json=payload).status_code,422)
        self.assertEqual(self.client.post(base+'/approve',json=dict(good,scope_hash='0'*64)).status_code,409)
        self.assertIsNone(self.client.get(base).json()['review']['contract'])

    def test_full_http_contract(self):
        record=self.capture(); rid=record["id"]; base="/api/plugins/repager/reviews/"+rid
        self.assertEqual(record["audience"],"testers")
        scope=self.client.get(base+"/scope").json()["scope"]
        self.assertEqual(scope["headline"]["text"],"Evidence, not promises")
        self.assertEqual(scope["cta_candidates"][0]["destination"],"https://example.com/start/")
        self.assertEqual(self.client.get("/api/plugins/repager/reviews").json()["reviews"][0]["id"],rid)
        self.assertEqual(self.client.get(base+"/export").status_code,409)
        response=self.client.post(base+"/approve",json={"finding_id":record["findings"][0]["id"],"cta_id":scope["default_cta_id"],"scope_hash":scope["scope_hash"],"expected_version":scope["record_version"],"preserve_copy":True,"preserve_destination":True})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()["review"]["contract"]["cta_destination"],"https://example.com/start/")
        generated=self.done(self.client.post(base+"/generate",json={"instruction":"Keep the exact copy"}))
        self.assertEqual(generated["status"],"generated")
        artifact=self.client.get(base+"/artifacts/"+generated["revisions"][-1]["html_file"])
        self.assertEqual(artifact.status_code,200,artifact.text)
        self.assertIn("sandbox",artifact.headers["content-security-policy"])
        self.assertEqual(artifact.headers["cache-control"],"no-store")
        self.assertEqual(hashlib.sha256(artifact.content).hexdigest(),generated["revisions"][-1]["artifact_hash"])
        verified=self.done(self.client.post(base+"/verify",json={}))
        self.assertIsNotNone(verified["verification"])
        exported=self.client.get(base+"/export")
        self.assertEqual(exported.status_code,200,exported.text if exported.status_code!=200 else "")
        self.assertEqual(exported.headers["content-type"],"application/zip")
        self.done(self.client.post(base+"/generate",json={}))
        self.assertEqual(self.client.get(base+"/export").status_code,409)
    def test_artifact_manifest_and_id_boundary(self):
        r=self.capture(); base="/api/plugins/repager/reviews/"+r["id"]
        self.assertEqual(self.client.get(base+"/artifacts/secret.json").status_code,400)
        self.assertEqual(self.client.get("/api/plugins/repager/reviews/not-an-id").status_code,400)
        self.assertEqual(self.client.get("/api/plugins/repager/jobs/missing").status_code,404)


class TestModelPolicy(unittest.TestCase):
    def test_no_free_main_or_fallback(self):
        base={"model":{"provider":"openai-codex","default":"paid-model"},"auxiliary":{"repager_layout":{"provider":"openai-codex","model":"paid-model","fallback_chain":[]}}}
        self.assertEqual(check_model_policy(base)["provider"],"openai-codex")
        for cfg in [{"model":{"provider":"nous","default":"x:free"}},dict(base,fallback_providers=[{"provider":"nous","model":"x:free"}]),dict(base,auxiliary={"repager_layout":{"provider":"nous","model":"x:free"}})]:
            with self.assertRaises(ServiceError):
                check_model_policy(cfg)

from repager.service import ServiceError
