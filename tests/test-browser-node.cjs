'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const net = require('node:net');
const { once } = require('node:events');
const u = require('../repager/browser/adapter-utils.js');

test('public address classification includes IPv6 and rejects reserved/mapped', () => {
  for (const ip of ['8.8.8.8', '1.1.1.1', '2606:4700:4700::1111']) assert.equal(u.isPublicIp(ip), true, ip);
  for (const ip of ['127.0.0.1', '10.0.0.1', '172.16.0.1', '192.168.1.1', '169.254.1.1', '100.64.1.1', '0.0.0.0', '224.0.0.1', '240.1.1.1', '192.0.0.9', '192.0.2.1', '198.18.0.1', '198.51.100.1', '203.0.113.1', '::', '::1', 'fc00::1', 'fe80::1', 'ff02::1', '2001:db8::1', '::ffff:8.8.8.8', '2002:0808:0808::1', '2001::1']) assert.equal(u.isPublicIp(ip), false, ip);
});
test('strict URLs reject parser normalization and nonstandard ports', () => {
  for (const url of ['https://example.com/', 'http://8.8.8.8:80/a', 'https://[2606:4700::1111]/']) assert.equal(u.isValidHttpUrl(url), true, url);
  for (const url of ['http://127.1', 'http://0x08080808', 'http://134744072', 'http://010.0.0.1', 'http://example.com:443', 'https://example.com:80', 'https://example.com:444', 'https://user@example.com', 'https://@example.com', 'https://example.com\\@evil.com', 'https://example.com/%0afoo', 'https://example.com/\n', 'https:///example.com', 'file:///x']) assert.equal(u.isValidHttpUrl(url), false, url);
});
test('resolve all once; mixed addresses fail closed', async () => {
  let calls = 0;
  const dns = { lookup: async (host, opts) => { calls++; assert.equal(opts.all, true); return [{address:'8.8.8.8',family:4},{address:'::1',family:6}]; } };
  await assert.rejects(u.resolveHostToPublic('example.com', {dns}));
  assert.equal(calls, 1);
});
test('palette ignores transparent, uses measured colors, bounds unique entries', () => {
  assert.equal(u.normalizeHexColor('rgba(0, 0, 0, 0)'), null);
  assert.equal(u.normalizeHexColor('rgb(255, 0, 16)'), '#ff0010');
  assert.equal(u.normalizePalette(Array.from({length:30}, (_,i)=>`rgb(${i},0,0)`)).length, 16);
});

async function request(proxy, url, method='GET') {
  return new Promise((resolve,reject) => {
    const req=http.request({host:'127.0.0.1',port:proxy.port,path:url,method},res=>{res.resume();res.on('end',()=>resolve(res.statusCode));});
    req.on('error',reject); req.end();
  });
}
test('real proxy rejects private/mixed DNS without reaching localhost honeypot', async () => {
  const {createProxy} = await import('../repager/browser/proxy.mjs');
  let hits=0, connects=0;
  const honey=http.createServer((req,res)=>{hits++;res.end('secret');}); honey.listen(0,'127.0.0.1'); await once(honey,'listening');
  const proxy=await createProxy({dns:{lookup:async()=>[{address:'8.8.8.8',family:4},{address:'127.0.0.1',family:4}]},connect:()=>{connects++;return net.connect(honey.address().port,'127.0.0.1');}});
  try {
    assert.equal(await request(proxy,'http://example.com/'),403);
    assert.equal(await request(proxy,'http://127.0.0.1/'),403);
    assert.equal(await request(proxy,'http://example.com/','POST'),403);
    assert.equal(hits,0); assert.equal(connects,0);
  } finally {await proxy.close();await new Promise(r=>honey.close(r));}
});
test('HTTP and CONNECT proxy dial numeric pinned addresses, never hostname', async () => {
  const {createProxy} = await import('../repager/browser/proxy.mjs');
  let calls=0; const targets=[];
  const honey=http.createServer((req,res)=>res.end('ok')); honey.listen(0,'127.0.0.1'); await once(honey,'listening');
  const proxy=await createProxy({dns:{lookup:async()=>{calls++;return [{address:'8.8.8.8',family:4}];}},connect:options=>{targets.push(options);return net.connect(honey.address().port,'127.0.0.1');}});
  try {
    assert.equal(await request(proxy,'http://example.com/'),200);
    const client=net.connect(proxy.port,'127.0.0.1'); await once(client,'connect'); client.write('CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n');
    const [data]=await once(client,'data'); assert.match(data.toString(),/200 Connection Established/); client.destroy();
    assert.equal(calls,2); assert.deepEqual(targets.map(t=>[t.host,t.port]),[['8.8.8.8',80],['8.8.8.8',443]]);
  } finally {await proxy.close();await new Promise(r=>honey.close(r));}
});

test('proxy denies WebSocket upgrades and bounded request exhaustion', async () => {
  const {createProxy}=await import('../repager/browser/proxy.mjs');
  let dials=0;
  const proxy=await createProxy({maxRequests:1,dns:{lookup:async()=>[{address:'127.0.0.1',family:4}]},connect:()=>{dials++;throw Error('must not dial');}});
  try {
    assert.equal(await request(proxy,'http://public.test/'),403);
    assert.equal(await request(proxy,'http://public.test/'),403);
    const client=net.connect(proxy.port,'127.0.0.1');await once(client,'connect');
    client.write('GET http://public.test/ HTTP/1.1\r\nHost: public.test\r\nConnection: Upgrade\r\nUpgrade: websocket\r\n\r\n');
    const [data]=await once(client,'data');assert.match(data.toString(),/403 Forbidden/);client.destroy();
    assert.equal(dials,0);
  }finally{await proxy.close();}
});

test('real Chrome source guards: redirects, subresources, WebSockets, POST, popups and viewport capture',
  {skip:process.env.REPAGER_BROWSER_INTEGRATION!=='1',timeout:90000},async()=>{
    const fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path');
    const {createProxy}=await import('../repager/browser/proxy.mjs');
    const {createLauncher,applyNetworkGuards,captureAction}=await import('../repager/browser/worker.mjs');
    let hits=0;
    const honey=http.createServer((req,res)=>{hits++;res.end('PRIVATE');});honey.listen(0,'127.0.0.1');await once(honey,'listening');
    const blocked=`http://127.0.0.1:${honey.address().port}/secret`;
    const upstream=http.createServer((req,res)=>{
      if(req.url==='/redirect'){res.writeHead(302,{location:blocked});res.end();return;}
      res.setHeader('content-type','text/html');
      if(req.url==='/delayed'){
        res.end('<!doctype html><title>Explicit delayed-render test fixture</title><nav><h2>Early navigation shell</h2><p>Not hero copy</p><a href="https://example.com/nav">Menu</a></nav><main id="app"></main><script>setTimeout(()=>{document.getElementById("app").innerHTML=\'<h1>Delayed hydrated hero</h1><p>Actual late DOM content</p><a href="https://example.com/keep/">Keep</a>\'},900)</script>');return;
      }
      if(req.url==='/wall'){
        res.end('<!doctype html><title>Explicit opaque-wall fixture</title><main><h1>Covered hero</h1><p>Covered paragraph</p><a href="https://example.com/keep/">Covered CTA</a></main><div style="position:fixed;inset:0;z-index:999;background:white"><p>Consent wall remains</p></div>');return;
      }
      if(req.url==='/overflow'){
        res.end('<!doctype html><main><h1>Overflow fixture</h1><p>Actual paragraph</p><a href="https://example.com/keep/">Keep</a><p style="width:2000px">Wide actual content</p></main>');return;
      }
      res.end(`<!doctype html><meta name="viewport" content="width=device-width"><title>Controlled source fixture</title>
        <style>body{background:rgb(12,34,56);color:rgb(255,255,255)}@media(max-width:500px){body{background:rgb(65,43,21)}}</style>
        <nav><a href="https://example.com/nav">Navigation</a></nav><main><h1>Source fixture</h1><p>Real rendered content</p>
        <a href="mailto:someone@example.com">Email</a><a href="https://example.com/keep/">Keep</a>
        <img src="${blocked}"><img src="http://mixed.test/secret"><iframe src="http://public.test/redirect"></iframe></main>
        <script>window.sourceScriptRan=true;fetch('${blocked}');fetch('http://public.test/post',{method:'POST'});new WebSocket('ws://127.0.0.1:${honey.address().port}/');window.open('${blocked}');navigator.serviceWorker.register('/sw.js').catch(()=>{});</script>`);
    });upstream.listen(0,'127.0.0.1');await once(upstream,'listening');
    const pins=[];
    const proxy=await createProxy({dns:{lookup:async host=>host==='mixed.test'?[{address:'8.8.8.8',family:4},{address:'::1',family:6}]:[{address:'8.8.8.8',family:4}]},
      connect:options=>{pins.push(options);assert.equal(options.host,'8.8.8.8');return net.connect(upstream.address().port,'127.0.0.1');}});
    const output=await fs.mkdtemp(path.join(os.tmpdir(),'repager-node-'));
    const payload={url:'http://public.test/',output_dir:output,timeout:20,executable_path:process.env.REPAGER_CHROMIUM_PATH||undefined,allow_no_sandbox:process.env.REPAGER_ALLOW_NO_SANDBOX==='1'};
    let browser;
    try {
      browser=await createLauncher(payload,proxy);
      const context=await browser.newContext({serviceWorkers:'block'}),page=await context.newPage(),record={attempted:0,denied:0,websockets:0};
      await applyNetworkGuards(context,page,false,record);
      await page.goto(payload.url,{waitUntil:'load'});
      assert.equal(await page.evaluate(()=>window.sourceScriptRan),true);
      await page.waitForTimeout(150);
      assert.ok(record.denied>=3);assert.equal(record.websockets,1);assert.equal(context.pages().length,1);
      assert.equal(context.serviceWorkers().length,0);
      await assert.rejects(page.goto('http://public.test/redirect'));
      await context.close();
      const source=await captureAction(payload,browser);
      assert.ok(source.palette.includes('#0c2238'));assert.ok(source.palette.includes('#412b15'));
      for(const view of source.viewports){
        const png=await fs.readFile(path.join(output,view.screenshot));
        assert.equal(png.readUInt32BE(16),view.width);assert.equal(png.readUInt32BE(20),view.height);
        assert.equal(view.overflow,false);
        assert.equal(view.elements.find(e=>e.text==='Email').href,null);
        assert.equal(view.elements.find(e=>e.text==='Navigation').region,'nav');
        const heading=view.elements.find(e=>e.tag==='h1');
        assert.ok(heading.container_id,'Real collector preserves semantic container identity');
        assert.equal(heading.container_id,view.elements.find(e=>e.text==='Keep').container_id);
      }
      assert.equal(hits,0,'private localhost honeypot must never receive requests');
      assert.ok(pins.length>0);assert.ok(proxy.stats.denied>0,'mixed DNS must reach proxy and be denied');
      const delayedOutput=path.join(output,'delayed');await fs.mkdir(delayedOutput);
      const delayed=await captureAction({...payload,url:'http://public.test/delayed',output_dir:delayedOutput},browser);
      for(const view of delayed.viewports)assert.ok(view.elements.some(e=>e.tag==='h1'&&e.text==='Delayed hydrated hero'),'Capture waits for actual client-rendered content, not just DOMContentLoaded');
      const wallOutput=path.join(output,'wall');await fs.mkdir(wallOutput);
      const wall=await captureAction({...payload,url:'http://public.test/wall',output_dir:wallOutput},browser);
      for(const view of wall.viewports){
        assert.ok(!view.elements.some(e=>e.text.startsWith('Covered')),'Opaque wall must not offer covered source evidence');
        assert.ok(view.elements.some(e=>e.text==='Consent wall remains'),'Timeout preserves actual wall snapshot');
      }
      const overflowOutput=path.join(output,'overflow');await fs.mkdir(overflowOutput);
      const overflow=await captureAction({...payload,url:'http://public.test/overflow',output_dir:overflowOutput},browser);
      for(const view of overflow.viewports){
        assert.equal(view.overflow,true);
        assert.ok(view.overflow_elements.length<=12);
        const item=view.overflow_elements.find(e=>e.text==='Wide actual content');
        assert.ok(item.in_hero);assert.equal(item.tag,'p');assert.ok(item.rect.width>view.width);
      }
      for(const view of delayed.viewports)assert.equal('overflow_elements' in view,false,'Absent optional evidence must not inject defaults');
    }finally{
      if(browser)await browser.close();await proxy.close();
      await new Promise(r=>upstream.close(r));await new Promise(r=>honey.close(r));await fs.rm(output,{recursive:true,force:true});
    }
  });