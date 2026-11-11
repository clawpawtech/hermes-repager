'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');

test('solid contrast math: exact extremes, thresholds, unsupported alpha',async()=>{
  const {contrastRatio,opaqueRGB}=await import('../repager/browser/readability.mjs');
  assert.equal(contrastRatio('rgb(0, 0, 0)','rgb(255, 255, 255)'),21);
  assert.equal(contrastRatio('rgb(20,20,20)','rgb(20,20,20)'),1);
  assert.ok(contrastRatio('rgb(118,118,118)','rgb(255,255,255)')>=4.5);
  assert.ok(contrastRatio('rgb(119,119,119)','rgb(255,255,255)')<4.5);
  assert.equal(contrastRatio('rgba(0,0,0,0.5)','rgb(255,255,255)'),null);
  assert.equal(opaqueRGB('rgb(256,0,0)'),null);
  assert.equal(opaqueRGB('transparent'),null);
});

test('real local Chrome quality fixtures: exact DOM copy, contrast, target, clipping and walls',
  {skip:process.env.REPAGER_BROWSER_INTEGRATION!=='1',timeout:90000},async()=>{
    const fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path');
    const {createProxy}=await import('../repager/browser/proxy.mjs');
    const {createLauncher,verifyAction}=await import('../repager/browser/worker.mjs');
    const output=await fs.mkdtemp(path.join(os.tmpdir(),'rp-quality-'));
    const proxy=await createProxy({denyAll:true});
    const payload={timeout:60,output_dir:output,executable_path:process.env.REPAGER_CHROMIUM_PATH||undefined,allow_no_sandbox:process.env.REPAGER_ALLOW_NO_SANDBOX==='1',expected_cta:'https://example.com/keep/',expected_copy:{headline:'Exact headline',bodies:['First paragraph','Second paragraph'],cta_label:'Keep'}};
    const html=(css='',extra='',body='<h1 class="rp-head">Exact headline</h1><p class="rp-body">First paragraph</p><p class="rp-body">Second paragraph</p><a class="rp-cta-link" href="https://example.com/keep/">Keep</a>')=>`<!doctype html><meta name="viewport" content="width=device-width"><style>body{background:#fff;color:#111}a{display:inline-block;background:#111;color:#fff;padding:14px 24px;min-height:44px;box-sizing:border-box}${css}</style><body>${body}${extra}</body>`;
    let browser;
    try{
      browser=await createLauncher(payload,proxy);
      const verify=async(markup,overrides={})=>{
        const report=await verifyAction({...payload,html:markup,...overrides},browser,proxy);
        assert.equal(report.protocol,2);assert.equal(report.checks.length,29);
        assert.equal(new Set(report.checks.map(c=>c.id)).size,29);
        assert.equal(report.checks.find(c=>c.id==='preview-no-network').status,'pass');
        return Object.fromEntries(report.checks.map(c=>[c.id,c]));
      };
      const expect=(checks,suffix,status)=>{for(const name of ['desktop','mobile'])assert.equal(checks[`${name}-${suffix}`].status,status,`${name}-${suffix}: ${checks[`${name}-${suffix}`].detail}`);};
      let checks=await verify(html());
      for(const suffix of ['headline-copy','body-copy','cta-label','heading-contrast','body-contrast','cta-contrast','cta-target','cta-complete','keyboard-focusable'])expect(checks,suffix,'pass');
      checks=await verify(html(),{expected_copy:null});
      for(const suffix of ['headline-copy','body-copy','cta-label'])expect(checks,suffix,'unknown');
      checks=await verify(html(),{expected_copy:{headline:'Wrong',bodies:['Second paragraph','First paragraph'],cta_label:'Wrong'}});
      for(const suffix of ['headline-copy','body-copy','cta-label'])expect(checks,suffix,'fail');
      checks=await verify(html('.rp-head,.rp-body{color:#eee}a{background:#fff;color:#eee}'));
      for(const suffix of ['heading-contrast','body-contrast','cta-contrast'])expect(checks,suffix,'fail');
      checks=await verify(html('body{background:linear-gradient(white,black)}'));
      for(const suffix of ['heading-contrast','body-contrast','cta-contrast'])expect(checks,suffix,'unknown');
      checks=await verify(html('.rp-body{color:rgba(0,0,0,.5)}'));
      expect(checks,'body-contrast','unknown');
      checks=await verify(html('a{padding:0;min-height:0;font-size:10px}'));
      expect(checks,'cta-target','fail');
      checks=await verify(html('a{position:absolute;left:-5px;top:150px}'));
      expect(checks,'cta-complete','fail');
      checks=await verify(html('', '<div style="position:fixed;inset:0;background:white;z-index:99">Explicit opaque wall fixture</div>'));
      expect(checks,'cta-complete','fail');
      checks=await verify(html('', '', '<h1 class="rp-head">Exact headline</h1><p class="rp-body">First paragraph</p><p class="rp-body">Second paragraph</p><div style="width:50px;overflow:hidden"><a class="rp-cta-link" href="https://example.com/keep/">Keep</a></div>'));
      expect(checks,'cta-complete','fail');
      checks=await verify(html('.rp-head{display:none}'));
      expect(checks,'headline-copy','pass'); // DOM equality deliberately does not claim perceptibility.
      assert.equal(proxy.stats.dials,0);
    }finally{if(browser)await browser.close();await proxy.close();await fs.rm(output,{recursive:true,force:true});}
  });
