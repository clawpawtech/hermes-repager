// Real native brand rendering smoke test. No model calls or live host settings.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {chromium} from 'playwright';
const out=process.env.REPAGER_SCREENSHOT_DIR;
if(!out)throw Error('Explicit artifact directory required');
await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:process.env.REPAGER_CHROMIUM_PATH,chromiumSandbox:process.env.REPAGER_TEST_NO_SANDBOX!=='1'});
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto((process.env.REPAGER_NATIVE_URL||'http://127.0.0.1:9121')+'/repager');
 // This declines an optional prompt in the isolated test profile only.
 const decline=page.getByRole('button',{name:'No thanks',exact:true});
 if(await decline.count()&&await decline.isVisible())await decline.click();
 const canvas=page.locator('repager-canvas');
 await canvas.getByRole('heading',{name:'Make one change. Keep the evidence.'}).waitFor();
 const results=[];
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:width===390?844:1000});
  for(const theme of ['light','dark']){
   if(await canvas.getAttribute('theme')!==theme)await canvas.getByRole('button',{name:theme==='dark'?'Dark theme':'Light theme',exact:true}).click();
   const rendered=await canvas.locator('header').evaluate(header=>{
    const mark=header.querySelector('.brand-wordmark svg'),accent=mark.querySelector('[data-brand-letter="p"]'),icon=header.querySelector('.brand-icon');
    return {viewport:innerWidth,header:header.getBoundingClientRect().toJSON(),mark:mark.getBoundingClientRect().toJSON(),icon_loaded:icon.complete&&icon.naturalWidth>0,accent:getComputedStyle(accent).fill,label:mark.getAttribute('aria-label')};
   });
   assert.equal(rendered.label,'repager');assert.equal(rendered.icon_loaded,true);assert.equal(rendered.accent,'rgb(247, 147, 26)');
   assert.ok(rendered.mark.x>=0&&rendered.mark.right<=width);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   await canvas.locator('header').screenshot({path:path.join(out,`brand-${width}-${theme}.png`)});
   results.push({width,theme,...rendered});
  }
 }
 assert.deepEqual(errors,[]);
 await fs.writeFile(path.join(out,'brand-ui-proof.json'),JSON.stringify({results,browser_errors:errors,android_hardware:'unverified',model_calls:0},null,2));
 console.log(JSON.stringify({renders:results.length,viewports:[1440,390],themes:['light','dark'],browser_errors:errors,model_calls:0}));
}finally{await browser.close();}
