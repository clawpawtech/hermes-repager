// Actual downloaded report, not a fixture. Scripts disabled; external requests denied.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright';
const out=process.env.REPAGER_SCREENSHOT_DIR;if(!out)throw Error('Explicit output directory required');
const url=pathToFileURL(path.resolve(out,'review.html')).href;
const browser=await chromium.launch({executablePath:process.env.REPAGER_CHROMIUM_PATH,chromiumSandbox:process.env.REPAGER_TEST_NO_SANDBOX!=='1'});
try{
 const results=[];
 for(const viewport of [{width:1440,height:1000},{width:390,height:844}]){
  const context=await browser.newContext({viewport,javaScriptEnabled:false});
  const page=await context.newPage(),attempts=[],errors=[];
  await page.route('**/*',route=>{if(route.request().url()===url)return route.continue();attempts.push(route.request().url());return route.abort();});
  page.on('pageerror',e=>errors.push(e.message));await page.goto(url);
  const images=await page.locator('img').evaluateAll(a=>a.map(i=>({complete:i.complete,width:i.naturalWidth,height:i.naturalHeight})));
  assert.equal(images.length,4);assert.ok(images.every(i=>i.complete&&i.width>0&&i.height>0));
  const body=await page.locator('body').innerText();assert.match(body,/Finance, transformed by AI/);assert.match(body,/undecided/i);assert.match(body,/Automated acceptance (test|exercise)/);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  assert.deepEqual(attempts,[]);assert.deepEqual(errors,[]);
  await page.screenshot({path:path.join(out,`report-${viewport.width}.png`),fullPage:true});
  results.push({viewport,images,external_attempts:attempts,errors,horizontal_overflow:false,scripts_disabled:true});await context.close();
 }
 await fs.writeFile(path.join(out,'report-browser-proof.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results));
}finally{await browser.close();}
