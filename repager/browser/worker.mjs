// Independent private plugin worker; stdin/stdout JSON, never source diagnostics.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright';
import utils from './adapter-utils.js';
import {createProxy} from './proxy.mjs';
import {contrastRatio,measureReadability} from './readability.mjs';

const SIZES=[{name:'desktop',width:1440,height:900},{name:'mobile',width:390,height:844}];
const FREEZE='*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important;scroll-behavior:auto!important}';
const LIMITATIONS=[
  'Fresh contexts, no saved profile or source cookies. Application-level controls are not an OS security boundary.',
  'No conversion, performance, accessibility-conformance or semantic-preservation conclusion is made.'
];

export async function createLauncher(payload,proxy) {
  const executablePath=payload.executable_path || chromium.executablePath();
  if(!fs.existsSync(executablePath))throw Error('local-browser-unavailable');
  return chromium.launch({executablePath,headless:true,chromiumSandbox:payload.allow_no_sandbox!==true,
    timeout:Math.min(payload.timeout*1000,30000),proxy:{server:`http://localhost:${proxy.port}`,bypass:'<-loopback>'},
    args:['--disable-quic','--force-webrtc-ip-handling-policy=disable_non_proxied_udp',
      '--disable-features=WebRtcAllowInputVolumeAdjustment,WebTransport,DnsOverHttps',
      '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost','--disable-extensions','--disable-background-networking']});
}

export async function applyNetworkGuards(context,page,preview,record) {
  await context.routeWebSocket('**',ws=>{record.websockets++;ws.close();});
  await context.route('**',async route=>{
    const request=route.request();
    record.attempted++;
    if(preview){record.denied++;await route.abort();return;}
    try {
      if(!['GET','HEAD'].includes(request.method()))throw Error('method');
      if(request.isNavigationRequest() && request.frame().page()!==page)throw Error('popup');
      utils.parseHttpUrl(request.url());
      // DNS enforcement belongs to the proxy, not a vulnerable check/continue pair.
      await route.continue();
    } catch {record.denied++;await route.abort().catch(()=>{});}
  });
  context.on('page',popup=>{if(popup!==page)popup.close().catch(()=>{});});
  page.on('download',download=>download.cancel().catch(()=>{}));
  page.on('dialog',dialog=>dialog.dismiss().catch(()=>{}));
  page.on('framenavigated',frame=>{
    if(frame===page.mainFrame() && frame.url()!=='about:blank' && (preview || !utils.isValidHttpUrl(frame.url())))page.close().catch(()=>{});
  });
}

async function newPage(browser,size,preview,payload,record) {
  const context=await browser.newContext({viewport:{width:size.width,height:size.height},
    javaScriptEnabled:!preview,serviceWorkers:'block',acceptDownloads:false,bypassCSP:false,
    locale:'en-US',timezoneId:'UTC',reducedMotion:'reduce'});
  try {
    const page=await context.newPage();page.setDefaultTimeout(Math.min(payload.timeout*1000,20000));
    await applyNetworkGuards(context,page,preview,record);
    return {context,page};
  } catch(error){await context.close();throw error;}
}

async function screenshot(page,output,prefix,size) {
  const filename=`${prefix}-${size.name}.png`;
  const target=path.join(output,filename);
  if(fs.existsSync(target) && fs.lstatSync(target).isSymbolicLink())throw Error('unsafe-output');
  await page.screenshot({path:target,fullPage:false,animations:'disabled',timeout:20000});
  return filename;
}

export async function captureAction(payload,browser) {
  utils.parseHttpUrl(payload.url);
  const viewports=[],colors=[],record={attempted:0,denied:0,websockets:0};
  let title='',truncated=false;
  for(const size of SIZES) {
    const {context,page}=await newPage(browser,size,false,payload,record);
    try {
      const response=await page.goto(payload.url,{waitUntil:'domcontentloaded',timeout:Math.min(payload.timeout*1000,30000)});
      if(!response || !response.ok())throw Error('capture-navigation-failed');
      utils.parseHttpUrl(page.url());
      // DOMContentLoaded can precede an SPA's first render. Wait boundedly for
      // supported hero content before freezing CSS or collecting evidence.
      // Timeout preserves the actual unsupported snapshot; it never inserts text.
      try {
        await page.waitForFunction(()=>{
          const visible=el=>{
            const r=el.getBoundingClientRect();
            if(!el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})||r.width<=0||r.height<=0)return false;
            const l=Math.max(0,r.left),t=Math.max(0,r.top),right=Math.min(innerWidth,r.right),bottom=Math.min(innerHeight,r.bottom);
            if(right<=l||bottom<=t)return false;
            return [0.15,0.5,0.85].some(x=>[0.15,0.5,0.85].some(y=>{
              const hit=document.elementFromPoint(l+(right-l)*x,t+(bottom-t)*y);
              return hit&&(hit===el||el.contains(hit));
            }));
          };
          const nodes=document.querySelectorAll('main h1,main h2,section h1,section h2,[role="main"] h1,[role="main"] h2');
          let peerBudget=5000;
          for(let i=0;i<Math.min(nodes.length,5000);i++){
            const el=nodes[i],container=el.closest('main,section,[role="main"]');
            if(el.closest('nav,header,[role="navigation"]')||!el.innerText.trim()||!visible(el))continue;
            let paragraph=false,cta=false;
            const peers=container.querySelectorAll('p,a[href]');
            for(let j=0;j<peers.length&&peerBudget>0;j++,peerBudget--){
              const peer=peers[j];
              if(peer.closest('main,section,[role="main"]')!==container||peer.closest('nav,header,[role="navigation"]')||!peer.innerText.trim()||!visible(peer))continue;
              if(peer.tagName==='P')paragraph=true;
              if(peer.tagName==='A')try{const u=new URL(peer.href);if(['http:','https:'].includes(u.protocol)&&!u.username&&!u.password)cta=true;}catch{}
              if(paragraph&&cta)return true;
            }
          }
          return false;
        },null,{timeout:Math.min(payload.timeout*1000,8000)});
      }catch(error){if(error.name!=='TimeoutError')throw error;}
      await page.evaluate(css=>{const style=document.createElement('style');style.textContent=css;document.head.appendChild(style);},FREEZE);
      await page.waitForTimeout(300);
      const measured=await page.evaluate(({name,width,height})=>{
        const elements=[],overflowElements=[],containers=new Map();let truncated=false;
        // Query results and inspection budget are bounded, not just final output.
        const candidates=document.querySelectorAll('h1,h2,p,a');
        if(candidates.length>5000)truncated=true;
        for(let i=0;i<Math.min(candidates.length,5000);i++) {
          const el=candidates[i],r=el.getBoundingClientRect(),s=getComputedStyle(el);
          if(r.width<=0 || r.height<=0 || r.bottom<=0 || r.top>=height || r.right<=0 || r.left>=width || !el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}))continue;
          const l=Math.max(0,r.left),t=Math.max(0,r.top),right=Math.min(width,r.right),bottom=Math.min(height,r.bottom);
          if(![0.15,0.5,0.85].some(x=>[0.15,0.5,0.85].some(y=>{
            const hit=document.elementFromPoint(l+(right-l)*x,t+(bottom-t)*y);
            return hit&&(hit===el||el.contains(hit));
          })))continue;
          const full=el.innerText.trim().replace(/\s+/g,' ');
          if(!full)continue;
          if(overflowElements.length<12&&(r.left<0||r.right>width))overflowElements.push({
            id:`${name}-overflow-${overflowElements.length}`,tag:el.tagName.toLowerCase(),text:full.slice(0,400),
            rect:{x:r.x,y:r.y,width:r.width,height:r.height},in_hero:!el.closest('nav,header,[role="navigation"]')&&!!el.closest('main,section,[role="main"]')});
          if(elements.length>=300){truncated=true;break;}
          if(full.length>4000)truncated=true;
          let href=null;
          if(el.tagName==='A' && el.hasAttribute('href')) {
            try {const u=new URL(el.getAttribute('href'),document.baseURI);if(['http:','https:'].includes(u.protocol)&&!u.username&&!u.password&&u.href.length<=2048)href=u.href;}catch{}
          }
          const container=el.closest('main,section,[role="main"]');
          if(container&&!containers.has(container))containers.set(container,`${name}-container-${containers.size}`);
          elements.push({id:`${name}-${elements.length}`,tag:el.tagName.toLowerCase(),text:full.slice(0,4000),href,
            ...(container?{container_id:containers.get(container)}:{}),
            region:el.closest('nav,header,[role="navigation"]')?'nav':el.closest('main,section,[role="main"]')?'hero':'content',
            rect:{x:r.x,y:r.y,width:r.width,height:r.height},
            style:{color:s.color,background_color:s.backgroundColor,font_size:s.fontSize,font_family:s.fontFamily.slice(0,300)}});
        }
        return {elements,truncated,overflowElements,background:getComputedStyle(document.body).backgroundColor,
          overflow:Math.max(document.documentElement.scrollWidth,document.body.scrollWidth)>width};
      },size);
      // Validate unsupported URLs independently; mailto/js links become null, not capture failure.
      for(const el of measured.elements)if(el.href&&!utils.isValidHttpUrl(el.href))el.href=null;
      colors.push(measured.background,...measured.elements.flatMap(el=>[el.style.background_color,el.style.color]));
      truncated ||= measured.truncated;
      title ||= (await page.title()).slice(0,4000);
      const filename=await screenshot(page,payload.output_dir,'source',size);
      viewports.push({...size,screenshot:filename,overflow:measured.overflow,elements:measured.elements,
        ...(measured.overflowElements.length?{overflow_elements:measured.overflowElements}:{})});
    } finally {await context.close();}
  }
  const limitations=[...LIMITATIONS,
    'First viewport only: h1/h2/p/a, maximum 300 visible elements and 4000 characters per element; at most 5000 candidates inspected. No full-page audit.',
    'Optional overflow elements are at most 12 visible first-screen text-element candidates, not proven causes or repairs. No diagnostic mutation or scrolling is performed.',
    'Waits at most 8 seconds for a first-screen semantic hero heading, paragraph and navigable CTA outside navigation before freezing CSS. Timeout retains the actual snapshot. Bounded representative hit tests exclude covered evidence but do not prove comprehensive interactability. Scripts remain enabled; separate viewport navigations may differ.',
    'Source traffic uses bounded public-only pinned proxy connections; denied resources may alter appearance. HTTPS tunnel contents are opaque; WebSockets are blocked at browser context.',
    `Source guard denied ${record.denied} requests and ${record.websockets} WebSockets.`];
  if(truncated)limitations.push('Capture bounds were reached: text/elements were omitted or truncated; do not treat selections as complete source copy.');
  return {url:payload.url,title,captured_at:new Date().toISOString(),viewports,palette:utils.normalizePalette(colors),limitations};
}

export async function verifyAction(payload,browser,proxy) {
  if(typeof payload.html!=='string'||!payload.html||Buffer.byteLength(payload.html)>utils.MAX_HTML_BYTES)throw Error('invalid-html');
  utils.parseHttpUrl(payload.expected_cta);
  const viewports=[],checks=[],record={attempted:0,denied:0,websockets:0};
  const add=(name,id,label,status,detail)=>checks.push({id:`${name}-${id}`,label,status,detail});
  for(const size of SIZES) {
    const {context,page}=await newPage(browser,size,true,payload,record);
    try {
      // Real execution probe, not an init-script override. evaluate remains available to the trusted driver.
      await page.setContent('<script>window.__repagerScriptProbe=1</script><p>Probe</p>',{waitUntil:'load'});
      const probe=await page.evaluate(()=>window.__repagerScriptProbe===undefined);
      await page.setContent(payload.html,{waitUntil:'load'});
      await page.evaluate(css=>{const style=document.createElement('style');style.textContent=css;document.head.appendChild(style);},FREEZE);
      const quality=await page.evaluate(measureReadability);
      const expected=payload.expected_copy;
      const copyValid=expected&&typeof expected.headline==='string'&&Array.isArray(expected.bodies)&&expected.bodies.every(v=>typeof v==='string')&&typeof expected.cta_label==='string';
      for(const [id,label,actual,wanted] of [
        ['headline-copy','Headline DOM textContent exact',quality.headline,expected?.headline],
        ['body-copy','Ordered .rp-body DOM textContent exact',quality.bodies,expected?.bodies],
        ['cta-label','CTA DOM textContent exact',quality.ctaLabel,expected?.cta_label]]){
        add(size.name,id,label,!copyValid?'unknown':JSON.stringify(actual)===JSON.stringify(wanted)?'pass':'fail',!copyValid?'No valid expected copy supplied.':'Exact DOM text comparison only; not proof of perceptibility.');
      }
      for(const [id,label,pairs,threshold] of [
        ['heading-contrast','Heading computed solid-color contrast ≥ 3',quality.headingColors,3],
        ['body-contrast','Body computed solid-color contrast ≥ 4.5',quality.bodyColors,4.5],
        ['cta-contrast','CTA computed solid-color contrast ≥ 4.5',quality.ctaColors,4.5]]){
        const ratios=pairs.map(p=>p?contrastRatio(p.foreground,p.background):null);
        const status=!ratios.length?'fail':ratios.some(r=>r!==null&&r<threshold)?'fail':ratios.some(r=>r===null)?'unknown':'pass';
        add(size.name,id,label,status,ratios.length?`Computed ratios: ${ratios.map(r=>r===null?'unknown (unsupported transparency/image/effect backdrop)':r.toFixed(3)).join(', ')}.`:'Required renderer DOM element missing.');
      }
      add(size.name,'cta-target','CTA comfortable target policy: 44 × 44 CSS px',quality.target?'pass':'fail','Measured anchor bounding box; a product comfort policy, not a full WCAG target-size claim.');
      add(size.name,'cta-complete','CTA fully in viewport with bounded hit testing',quality.complete?'pass':'fail','First-screen bounds, ancestor clipping and nine representative hit points; not comprehensive clickability.');
      const measured=await page.evaluate(expected=>{
        const visible=el=>{const r=el.getBoundingClientRect();return el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})&&r.width>0&&r.height>0&&r.bottom>0&&r.right>0&&r.top<innerHeight&&r.left<innerWidth;};
        const anchors=[...document.querySelectorAll('a[href]')];
        const cta=anchors.findIndex(el=>el.href===expected&&visible(el));
        const root=document.documentElement,body=document.body;
        return {cta,focusableCount:document.querySelectorAll('a[href],button,input,select,textarea,[tabindex]').length,
          text:(body?.innerText||'').trim().length,
          scrollWidth:Math.max(root.scrollWidth,body?.scrollWidth||0),scrollHeight:Math.max(root.scrollHeight,body?.scrollHeight||0),
          hostileSentinel:window.__repagerHostile===undefined};
      },payload.expected_cta);
      const {name,width,height}=size;
      add(name,'cta-destination','Exact visible CTA destination',measured.cta>=0?'pass':'fail',measured.cta>=0?'Visible anchor href equals expected URL exactly (including trailing slash).':'No visible anchor with the exact expected URL.');
      let focused=false;
      if(measured.cta>=0) {
        for(let i=0;i<Math.min(measured.focusableCount+2,302);i++) {
          await page.keyboard.press('Tab');
          focused=await page.evaluate(index=>document.activeElement===document.querySelectorAll('a[href]')[index],measured.cta);
          if(focused)break;
        }
      }
      add(name,'keyboard-focusable','CTA reachable by real Tab key',focused?'pass':measured.focusableCount>300?'unknown':'fail',focused?'Tab key moved activeElement onto the exact visible CTA.':'CTA not reached within bounded Tab traversal (maximum 302 presses).');
      add(name,'horizontal-overflow','No horizontal overflow',measured.scrollWidth>width?'fail':'pass',`Rendered scrollWidth ${measured.scrollWidth}px; viewport ${width}px.`);
      add(name,'vertical-extent','Vertical content extent',measured.scrollHeight>height?'unknown':'pass',`Rendered height ${measured.scrollHeight}px; viewport ${height}px. Tall content is not a horizontal overflow or performance fault.`);
      add(name,'visible-content','Rendered text present',measured.text>0?'pass':'fail',`Rendered body innerText: ${measured.text} characters (not HTML source text).`);
      add(name,'scripts-disabled','Inline scripts cannot execute',probe&&measured.hostileSentinel?'pass':'fail','javaScriptEnabled:false; inline execution probe and hostile sentinel inspected via trusted evaluate.');
      await page.evaluate(()=>scrollTo(0,0));
      viewports.push({...size,screenshot:await screenshot(page,payload.output_dir,'preview',size),overflow:measured.scrollWidth>width});
    } finally {await context.close();}
  }
  checks.push({id:'preview-no-network',label:'Preview resource requests denied',status:record.attempted===record.denied&&proxy.stats.dials===0?'pass':'fail',
    detail:`${record.attempted} attempted resource requests, ${record.denied} denied; ${record.websockets} WebSockets closed; ${proxy.stats.dials} outbound proxy connections.`,attempted_requests:record.attempted,denied_requests:record.denied});
  return {protocol:2,checked_at:new Date().toISOString(),checks,viewports,limitations:[...LIMITATIONS,
    'Preview JavaScript disabled, all network denied, service workers blocked, downloads canceled, popups closed. No source cookies.',
    'DOM text equality is not proof of perceptibility. Contrast supports opaque solid computed colors only. Bounded geometry/hit tests and Tab focus are not complete accessibility, clickability or conversion verification.',
    'First-screen screenshots only. Tab traversal bounded to 302 presses; tall sections require human review. Text-only rendered checks do not prove accessibility or conversion quality.',
    ...(payload.allow_no_sandbox?['Trusted no-sandbox opt-in active: Chromium OS sandbox disabled. Use separate OS isolation for untrusted sites.']:[])]};
}

export async function run(payload) {
  if(!payload||!['capture','verify'].includes(payload.action)||!Number.isInteger(payload.timeout)||payload.timeout<=0||typeof payload.output_dir!=='string'||!path.isAbsolute(payload.output_dir))throw Error('invalid-payload');
  if(payload.action==='capture')utils.parseHttpUrl(payload.url);
  if(payload.allow_no_sandbox!==undefined&&typeof payload.allow_no_sandbox!=='boolean')throw Error('invalid-sandbox-option');
  await fs.promises.mkdir(payload.output_dir,{recursive:true});
  const proxy=await createProxy({denyAll:payload.action==='verify',lifetimeMs:payload.timeout*1000});
  let browser;
  try {
    browser=await createLauncher(payload,proxy);
    const result=payload.action==='capture'?await captureAction(payload,browser):await verifyAction(payload,browser,proxy);
    if(payload.action==='capture'&&payload.allow_no_sandbox)result.limitations.push('Trusted no-sandbox opt-in active: Chromium OS sandbox disabled; separate OS isolation required for hostile pages.');
    if(Buffer.byteLength(JSON.stringify(result))>8*1024*1024)throw Error('output-budget');
    return result;
  } finally {try {if(browser)await browser.close();}finally{await proxy.close();}}
}

if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href) {
  try {
    const chunks=[];let bytes=0;
    for await(const chunk of process.stdin){bytes+=chunk.length;if(bytes>1024*1024)throw Error('input-budget');chunks.push(chunk);}
    const result=await run(JSON.parse(Buffer.concat(chunks).toString('utf8')));
    process.stdout.write(JSON.stringify(result)+'\n');
  } catch {
    process.stderr.write('browser-worker-failed: validation, local browser, or guarded navigation unavailable\n');
    process.exitCode=1;
  }
}