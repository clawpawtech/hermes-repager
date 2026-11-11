// Exercise the ACTUAL Hermes dashboard SDK and embedded plugin, not the standalone shell.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {chromium} from 'playwright';
const base=process.env.REPAGER_NATIVE_URL||'http://127.0.0.1:9121';
const out=process.env.REPAGER_SCREENSHOT_DIR;
if(!out)throw Error('REPAGER_SCREENSHOT_DIR must be an explicit local artifact directory');
await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:process.env.REPAGER_CHROMIUM_PATH,headless:true,chromiumSandbox:process.env.REPAGER_TEST_NO_SANDBOX!=='1'});
try{
 const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
 const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/repager',{waitUntil:'networkidle'});
 await page.waitForFunction(()=>!!window.__HERMES_PLUGIN_SDK__,null,{timeout:30000});
 const health=await page.evaluate(async()=>{try{return {ok:true,result:await window.__HERMES_PLUGIN_SDK__.fetchJSON('/api/plugins/repager/health')}}catch(e){return {ok:false,error:e.message}}});
 const visible=await page.locator('repager-canvas').count();
 const report={native_url:base,health,canvas_present:visible>0,page_errors:errors};
 await fs.writeFile(path.join(out,'native-probe.json'),JSON.stringify(report,null,2));
 await page.screenshot({path:path.join(out,'native-dashboard.png'),fullPage:true});
 console.log(JSON.stringify(report));
 assert.ok(health.ok,'Actual host SDK can reach protected plugin health');
 assert.equal(visible,1,'Canvas is embedded in the actual native dashboard');
 const canvas=page.locator('repager-canvas');
 await canvas.getByRole('heading',{name:'Make one change. Keep the evidence.'}).waitFor();
 assert.deepEqual(errors,[],'No uncaught native/plugin browser errors');
 await context.close();
}finally{await browser.close();}
