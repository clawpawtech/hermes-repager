"""Real producer-schema -> real canvas boundary test. Browser/model are explicit offline adapters."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from repager.service import ReviewService
from repager.store import ReviewStore
from test_core_service import FakeBrowser, FakeLLM, _default_verify_report, URL, approve_displayed

class ClientContractTests(unittest.TestCase):
    def test_canvas_accepts_actual_validated_signed_protocol2_record(self):
        self.assertIsNotNone(shutil.which('node'), 'Node is required by this plugin and CI')
        checks = ('cta-destination', 'keyboard-focusable', 'horizontal-overflow', 'visible-content',
                  'vertical-extent', 'scripts-disabled', 'headline-copy', 'body-copy', 'cta-label',
                  'heading-contrast', 'body-contrast', 'cta-contrast', 'cta-target', 'cta-complete')
        report = _default_verify_report()
        report['protocol'] = 2
        report['checks'] = [{'id': 'preview-no-network', 'label': 'Unit-only sentinel', 'status': 'pass', 'detail': 'Synthetic adapter, not live browser evidence.'}]
        report['checks'] += [{'id': f'{vp}-{name}', 'label': name, 'status': 'pass', 'detail': 'Synthetic adapter, not live browser evidence.'}
                             for vp in ('desktop', 'mobile') for name in checks]
        with tempfile.TemporaryDirectory() as directory:
            service = ReviewService(ReviewStore(Path(directory)), FakeBrowser(verify_report=report), FakeLLM())
            r = service.create_review(URL)
            approve_displayed(service, r['id'], r['findings'][0]['id'])
            service.generate(r['id'])
            record = service.verify(r['id'])
            code = r"""
const fs=require('node:fs'),vm=require('node:vm'),classes={};
const context={window:{},HTMLElement:class{attachShadow(){this.shadowRoot={};}},customElements:{get:n=>classes[n],define:(n,c)=>classes[n]=c},URL,console};
vm.runInNewContext(fs.readFileSync('dashboard/src/canvas.js','utf8'),context);
const c=new classes['repager-canvas']();c.review=JSON.parse(fs.readFileSync(0,'utf8'));
console.log(JSON.stringify({recognized:c.currentReceipt()?.protocol,exportable:c.exportable()}));
"""
            result = json.loads(subprocess.check_output(['node', '-e', code], input=json.dumps(record).encode(), cwd=Path(__file__).resolve().parents[1]))
            self.assertEqual(result, {'recognized': 2, 'exportable': True})
