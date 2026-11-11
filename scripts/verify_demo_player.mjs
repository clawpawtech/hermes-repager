// Isolated authenticated loopback player test, NOT proof of Android hardware playback.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import http from 'node:http';
import crypto from 'node:crypto';
import path from 'node:path';
import {chromium} from 'playwright';
const directory=process.env.REPAGER_SCREENSHOT_DIR;
if(!directory)throw Error('Explicit REPAGER_SCREENSHOT_DIR required');
const content=await fs.readFile(path.join(directory,'watch.html'));
const token=crypto.randomBytes(32).toString('hex');
const server=http.createServer((req,res)=>{
 if(req.headers.authorization!==`Bearer ${token}`){res.writeHead(401,{'Cache-Control':'no-store'});res.end();return;}
 if(req.url!=='/watch'){res.writeHead(404);res.end();return;}
 res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store','Content-Security-Policy':'sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox','X-Content-Type-Options':'nosniff'});res.end(content);
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const url=`http://127.0.0.1:${server.address().port}/watch`;
let browser;
try{
 assert.equal((await fetch(url)).status,401,'Unauthenticated loopback test requests denied');
 browser=await chromium.launch({executablePath:process.env.REPAGER_CHROMIUM_PATH,chromiumSandbox:process.env.REPAGER_TEST_NO_SANDBOX!=='1'});
 const results=[];
 for(const viewport of [{width:1440,height:1000},{width:390,height:844}]){
  const context=await browser.newContext({viewport,extraHTTPHeaders:{Authorization:`Bearer ${token}`}});
  const page=await context.newPage();const external=[],errors=[];
  page.on('request',r=>{if(r.url().startsWith('http')&&r.url()!==url)external.push(r.url());});
  page.on('pageerror',e=>errors.push(e.message));
  assert.equal((await page.goto(url)).status(),200);
  const video=page.locator('video');
  await video.evaluate(v=>v.play());
  await page.waitForFunction(()=>document.querySelector('video').currentTime>1,null,{timeout:15000});
  await video.evaluate(v=>{v.currentTime=v.duration-2;});
  await page.waitForFunction(()=>{const v=document.querySelector('video');return v.currentTime>v.duration-3&&!v.seeking;},null,{timeout:10000});
  const media=await video.evaluate(v=>({width:v.videoWidth,height:v.videoHeight,duration:v.duration,readyState:v.readyState,error:v.error?.code||null,currentTime:v.currentTime,inline:v.playsInline}));
  assert.equal(media.error,null);assert.equal(media.inline,true);assert.deepEqual(external,[]);assert.deepEqual(errors,[]);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  results.push({viewport,media,external_requests:external,browser_errors:errors});
  await page.screenshot({path:path.join(directory,`player-${viewport.width}.png`),fullPage:true});
  await context.close();
 }
 const proof={auth_scope:'Ephemeral isolated loopback harness, not a live WebUI login',live_webui_authenticated_playback:'not tested: no vault login available',android_hardware_playback:'unverified',results};
 await fs.writeFile(path.join(directory,'player-proof.json'),JSON.stringify(proof,null,2));
 console.log(JSON.stringify(proof));
}finally{if(browser)await browser.close();await new Promise(r=>server.close(r));}
