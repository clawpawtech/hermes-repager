// Synthetic contracts only: no network, model calls, or live-success claims.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('dashboard/src/canvas.js','utf8');
const signature='a'.repeat(64);
function review(){
 const contract={signature,finding_id:'f',headline_id:'h',body_ids:['b'],cta_id:'c',cta_text:'Go',cta_destination:'https://example.com/go',approved_at:'2026-01-01'};
 const section={headline_id:'h',body_ids:['b'],cta_id:'c',layout:'stack',alignment:'left',spacing:'comfortable',background:'#ffffff',foreground:'#000000',accent:'#000000',button_text:'#ffffff'};
 return {id:'r',status:'verified',source:{title:'Synthetic source',url:'https://example.com',palette:['#123456'],limitations:[],viewports:[{name:'desktop',width:1440,height:900,screenshot:'d.png'},{name:'mobile',width:390,height:844,screenshot:'m.png'}]},findings:[{id:'f',title:'Readable finding title',kind:'judgment',evidence_ids:[]}],contract,revisions:[{number:1,signature,artifact_hash:'b'.repeat(64),contract_hash:'c'.repeat(64),contract_snapshot:structuredClone(contract),section,html_file:'r1.html'}],verification:{revision:1,signature,artifact_hash:'b'.repeat(64),contract_hash:'c'.repeat(64),protocol:2,checks:Array.from({length:29},(_,i)=>({id:'check-'+i,status:i===28?'unknown':'pass',label:'Synthetic check',detail:'Test observation'})),viewports:[],limitations:[]}};
}
function scope(){return {headline:{text:'Exact heading'},bodies:[{text:'Exact body'}],cta_candidates:[{id:'c',text:'Go',destination:'https://example.com/go'}],default_cta_id:'c',scope_hash:'scope'};}
function canvas(extra={}){
 const classes={};const context={window:{},HTMLElement:class{attachShadow(){this.shadowRoot={};}},customElements:{get:n=>classes[n],define:(n,c)=>classes[n]=c},URL,console,...extra};
 vm.runInNewContext(source,context);const c=new classes['repager-canvas']();c.render=()=>{};c.review=review();c.scope=scope();c.selected='f';return c;
}
const action=(name,more={})=>({target:{closest:selector=>selector==='[data-action]'?{disabled:false,dataset:{action:name,...more}}:null}});

test('reconnection is not blocked behind a locked gallery request',async()=>{
 const c=canvas();c.isConnected=true;c.jobId=null;const calls=[];
 c.json=async p=>{calls.push(p);if(p==='/jobs')return {jobs:[{id:'busy-model',state:'running'}]};throw Error('A gallery read would block on the model-held record');};
 c.poll=async()=>{calls.push('poll');};await c.refresh();
 assert.deepEqual(calls,['/jobs','poll']);assert.equal(c.jobId,'busy-model');assert.equal(c.connecting,false);
});
test('checked failures permit a rejection choice but never prefer or export',()=>{
 const c=canvas();c.review.verification.checks[0].status='fail';
 assert.equal(c.canDecide(),true);assert.equal(c.exportable(),false);
 assert.match(c.decisionForm(),/value="prefer" disabled/);
});
test('mobile starts in canonical mobile view without changing desktop default',()=>{
 assert.equal(canvas().view,'desktop');assert.equal(canvas({matchMedia:()=>({matches:true})}).view,'mobile');
});
test('remix submits only changed trusted properties with current optimistic guards',async()=>{
 const c=canvas();let call;c.startJob=async(...args)=>{call=args;};
 await c.remix({layout:'editorial',background:'#ffffff',headline_id:'malicious',html:'<script>'});
 assert.equal(call[0],'/reviews/r/remix');assert.deepEqual(JSON.parse(JSON.stringify(call[1])),{base_revision:1,artifact_hash:c.latest().artifact_hash,changes:{layout:'editorial'}});
 assert.equal(Object.hasOwn(call[1],'from_revision'),false);
});
test('no-op remix does not create an operation',async()=>{
 const c=canvas();c.startJob=async()=>assert.fail('No operation expected');await c.remix({layout:'stack'});assert.match(c.error,/different design property/);
});
test('restoration creates a new guarded revision, never posts historical base guards',async()=>{
 const c=canvas();const prior=structuredClone(c.latest());c.review.revisions.push({...structuredClone(prior),number:2,artifact_hash:'d'.repeat(64)});c.inspectedRevision=1;
 let body;c.startJob=async(path,payload)=>{assert.equal(path,'/reviews/r/remix');body=payload;};await c.click(action('restore'));
 assert.deepEqual(JSON.parse(JSON.stringify(body)),{base_revision:2,artifact_hash:'d'.repeat(64),changes:{},from_revision:1});
 c.review.revisions[0].contract_snapshot.signature='e'.repeat(64);body=null;await c.click(action('restore'));assert.equal(body,null);
});
test('receipt requires current approval snapshot and expected signature metadata',()=>{
 const c=canvas();assert.ok(c.currentReceipt());assert.equal(c.exportable(),true);
 c.review.contract.approved_at='changed';assert.equal(c.currentReceipt(),null);
 c.latest().contract_snapshot=structuredClone(c.review.contract);assert.ok(c.currentReceipt());
 for(const target of [c.review.contract,c.latest(),c.review.verification]){const old=target.signature;delete target.signature;assert.equal(c.currentReceipt(),null);target.signature=old;}
 c.review.verification.artifact_hash='stale';assert.equal(c.currentReceipt(),null);
});
test('old protocol, incomplete or duplicate checks, failed checks and history block handoff',()=>{
 const c=canvas();c.review.verification.protocol=1;assert.equal(c.exportable(),false);c.review.verification.protocol=2;
 c.review.verification.checks[0].status='fail';assert.equal(c.exportable(),false);c.review.verification.checks[0].status='pass';
 c.review.verification.checks[1].id='check-0';assert.equal(c.exportable(),false);c.review.verification.checks[1].id='check-1';
 c.review.verification.checks.pop();assert.equal(c.exportable(),false);
});
test('unknown counts remain explicit alongside pass and fail',()=>{
 const c=canvas();assert.match(c.checkResults(c.review.verification),/28 pass · 0 fail · 1 unknown · protocol 2/);
});
test('readable property diff is bound to parent_revision and escapes data',()=>{
 const c=canvas();const next={...structuredClone(c.latest()),number:3,parent_revision:1,section:{...c.latest().section,layout:'spotlight',foreground:'<unsafe>'}};
 assert.match(c.propertyDiff(next),/Changes from revision 1/);assert.match(c.propertyDiff(next),/Layout<\/strong>: stack → spotlight/);assert.match(c.propertyDiff(next),/&lt;unsafe&gt;/);
});
test('controls expose exactly seven presentation fields, approval text starts open',()=>{
 const c=canvas();const html=c.designControls(c.latest());assert.deepEqual([...html.matchAll(/select name="([^"]+)"/g)].map(m=>m[1]),['layout','alignment','spacing','background','foreground','accent','button_text']);
 for(const layout of ['stack','split','editorial','spotlight'])assert.ok(html.includes(`value="${layout}"`));
 assert.match(c.approvalForm(),/<details open>/);assert.match(c.reviewBody(c.review,c.latest(),c.currentReceipt()),/Readable finding title/);
});
test('generated review includes only one whole-source image and sandboxed canonical preview',()=>{
 const c=canvas();const body=c.reviewBody(c.review,c.latest(),c.currentReceipt());assert.equal([...body.matchAll(/data-artifact="d.png"/g)].length,1);assert.match(body,/sandbox="" width="1440" height="900"/);
 c.view='mobile';assert.match(c.reviewBody(c.review,c.latest(),c.currentReceipt()),/sandbox="" width="390" height="844"/);
});
test('anchor highlights use only real viewport rectangles, never fabricate missing mobile matches',()=>{
 const c=canvas();const vp=c.review.source.viewports[0];c.scope.anchors={desktop:[{tag:'h1',text:'Exact heading',rect:{x:144,y:90,width:720,height:90}},{rect:{x:'bad',y:0,width:1,height:1}}],mobile:[]};
 assert.match(c.anchorHighlights(vp),/left:10%;top:10%;width:50%;height:10%/);assert.equal([...c.anchorHighlights(vp).matchAll(/class="anchor"/g)].length,1);assert.equal(c.anchorHighlights(c.review.source.viewports[1]),'');
});
test('mount refresh reconnects active backend job and never starts a duplicate',async()=>{
 const c=canvas();c.isConnected=true;let polls=0;c.json=async path=>path==='/reviews'?{reviews:[]}:path==='/health'?{}:{jobs:[{id:'active',state:'running',review_id:'r'}]};c.poll=async()=>polls++;await c.refresh();assert.equal(c.jobId,'active');assert.equal(c.connecting,false);assert.equal(polls,1);
});
test('absent process-local jobs leave saved reviews available',async()=>{
 const c=canvas();c.isConnected=true;c.json=async path=>path==='/reviews'?{reviews:[{id:'saved'}]}:path==='/jobs'?{jobs:[]}:{};await c.refresh();assert.equal(c.reviews[0].id,'saved');assert.equal(c.jobId,null);assert.equal(c.busy,'');
});
test('connection errors are distinct from unsupported-source errors',async()=>{
 const c=canvas();c.json=async()=>{throw Error('Offline');};await c.refresh();assert.match(c.error,/Connection unavailable/);assert.match(c.reviewBody({source:null,error:'Unsupported source'},null,null),/Source capture did not complete/);
});
test('URL eligibility updates in place without rerender or premature capture claim',()=>{
 const c=canvas();let renders=0;c.render=()=>renders++;const note={};c.shadowRoot={querySelector:()=>note};c.input({target:{name:'url',value:'javascript:alert(1)'}});assert.match(note.textContent,/HTTP\(S\)/);assert.equal(renders,0);assert.match(c.eligibility('https://example.com'),/not guaranteed/);
});
test('in-memory form preservation keeps consent and draft values but never password fields',()=>{
 const c=canvas();const elements=[{name:'preserve_copy',type:'checkbox',checked:true},{name:'cta_id',value:'c'},{name:'token',type:'password',value:'not-retained'}];const form={dataset:{form:'approve'},elements};c.formReview='r';c.formRevision=1;c.shadowRoot={querySelectorAll:()=>[form]};c.rememberForms();elements[0].checked=false;c.restoreForms();assert.equal(elements[0].checked,true);assert.equal(Object.hasOwn(c.formState.approve,'token'),false);
});
test('new revision resets remix and decision drafts rather than overriding new artifact properties',()=>{
 const c=canvas();c.formReview='r';c.formRevision=0;c.formState={remix:{layout:'split'},decision:{reason:'stale'},approve:{preserve_copy:true}};c.rememberForms();assert.equal(c.formState.remix,undefined);assert.equal(c.formState.decision,undefined);assert.equal(c.formState.approve.preserve_copy,true);
});
test('legacy optional metadata is not injected or mutated by rendering',()=>{
 const c=canvas();delete c.latest().origin;delete c.latest().parent_revision;delete c.latest().safety_adjustments;const before=JSON.stringify(c.review);c.reviewBody(c.review,c.latest(),c.currentReceipt());assert.equal(JSON.stringify(c.review),before);
});

test('decision submission guards exact artifact, then reads back persisted choice',async()=>{
 const c=canvas({FormData:class{constructor(form){return new Map(Object.entries(form.values));}}});const calls=[];
 c.json=async(path,body)=>{calls.push({path,body});return {review:{...c.review,decision:{revision:1,artifact_hash:c.latest().artifact_hash,verdict:'prefer',reason:'Clear hierarchy'}}};};
 const form={dataset:{form:'decision'},values:{verdict:'prefer',reason:' Clear hierarchy '}};await c.submit({target:{closest:()=>form},preventDefault(){}});
 assert.equal(calls.length,2);assert.equal(calls[0].path,'/reviews/r/decision');assert.deepEqual(JSON.parse(JSON.stringify(calls[0].body)),{revision:1,artifact_hash:'b'.repeat(64),verification_signature:signature,verdict:'prefer',reason:'Clear hierarchy'});assert.equal(calls[1].path,'/reviews/r');assert.match(c.decisionForm(),/Current choice: <strong>prefer/);
 c.review.verification.checks[0].status='fail';calls.length=0;await c.submit({target:{closest:()=>form},preventDefault(){}});assert.equal(calls.length,0);
});
test('visual report download uses authenticated SDK binary rather than public artifact URLs',async()=>{
 const calls=[],anchor={click(){calls.push('download');}};let sdkPath;
 const c=canvas({window:{__HERMES_PLUGIN_SDK__:{authedFetch:async path=>{sdkPath=path;return {ok:true,blob:async()=>new Blob(['<p>Report</p>'])};}}},Blob,document:{createElement:()=>anchor},URL:{createObjectURL:()=> 'blob:synthetic',revokeObjectURL(){}},setTimeout:()=>{}});
 await c.click(action('report'));assert.equal(sdkPath,'/api/plugins/repager/reviews/r/report');assert.equal(anchor.download,'repager-r-report.html');assert.deepEqual(calls,['download']);
});

test('failed approval or readback clears confirmations before any retry',async()=>{
 for(const failAt of [1,2]){
  const c=canvas({FormData:class{constructor(form){return Object.entries(form.values);}}});c.review.version=7;
  const fields=[{name:'preserve_copy',checked:true},{name:'preserve_destination',checked:true}];c.shadowRoot.querySelectorAll=()=>fields;c.formState.approve={preserve_copy:true,preserve_destination:true};let count=0,posted;
  c.json=async(path,body)=>{count++;if(body)posted=body;if(count===failAt)throw Error(failAt===1?'409 stale approval':'Readback failed');return {review:c.review};};
  const form={dataset:{form:'approve'},values:{cta_id:'c',preserve_copy:'on',preserve_destination:'on'}};
  await c.submit({target:{closest:()=>form},preventDefault(){}});
  assert.equal(posted.expected_version,7);assert.equal(posted.preserve_copy,true);assert.equal(posted.preserve_destination,true);
  assert.equal(c.formState.approve.preserve_copy,false);assert.equal(c.formState.approve.preserve_destination,false);assert.ok(fields.every(el=>!el.checked));assert.equal(c.busy,'');
 }
});

test('archived check images and reasons remain read-only and escaped' ,()=>{
 const c=canvas(),prior=structuredClone(c.latest());
 const receipt=structuredClone(c.review.verification);receipt.viewports=[{name:'desktop',screenshot:'archived.png'}];
 c.review.review_events=[{signature,sequence:1,kind:'verification',payload:receipt},{signature,sequence:2,kind:'decision',payload:{revision:1,verdict:'reject',reason:'<script>synthetic</script>',recorded_at:'2026-01-01'}}];
 c.review.revisions.push({...structuredClone(prior),number:2,artifact_hash:'d'.repeat(64)});c.review.verification=null;c.inspectedRevision=1;
 assert.equal(c.archivedReceipt(prior).revision,1);assert.equal(c.exportable(),false);assert.equal(c.reportable(),false);assert.equal(c.canDecide(),false);
 const body=c.reviewBody(c.review,c.latest(),null);assert.match(body,/Archived checked proposal/);assert.match(body,/&lt;script&gt;synthetic/);assert.doesNotMatch(body,/<script>/);
});
test('historical inspection selects signed captured pixels, falling back to isolated HTML only without a receipt',()=>{
 const c=canvas(),prior=structuredClone(c.latest()),receipt=structuredClone(c.review.verification);
 receipt.viewports=[{name:'desktop',screenshot:'archived-desktop.png'}];
 c.review.review_events=[{signature,sequence:1,kind:'verification',payload:receipt}];
 c.review.revisions.push({...structuredClone(prior),number:2,artifact_hash:'d'.repeat(64)});c.review.verification=null;c.inspectedRevision=1;
 let body=c.reviewBody(c.review,c.latest(),null);
 assert.match(body,/data-file="archived-desktop.png" data-title="Inspect proposal" data-html="false"/);
 assert.doesNotMatch(body,/<iframe/);
 c.review.review_events=[];body=c.reviewBody(c.review,c.latest(),null);
 assert.match(body,/data-file="r1.html" data-title="Inspect proposal" data-html="true"/);
 assert.match(body,/<iframe[^>]+sandbox="" width="1440" height="900"/);
});

test('historical scope and changed-scope diffs never substitute current approval',()=>{
 const c=canvas(),prior=structuredClone(c.latest());prior.contract_snapshot.cta_text='Earlier approved action';c.review.revisions[0]=prior;
 const next={...structuredClone(prior),number:2,contract_hash:'f'.repeat(64),parent_revision:1};c.review.revisions.push(next);c.inspectedRevision=1;c.review.contract.cta_text='Different current action';
 const body=c.reviewBody(c.review,next,null);assert.match(body,/Earlier approved action/);assert.match(body,/Current approval - for future revisions/);assert.match(c.propertyDiff(next),/Scope changed/);assert.doesNotMatch(c.propertyDiff(next),/same approved source/);
});
test('failed current candidate allows review-only report but not implementation ZIP',async()=>{
 const c=canvas();c.review.verification.checks[0].status='fail';let downloaded=[];c.download=async kind=>downloaded.push(kind);
 assert.equal(c.reportable(),true);assert.equal(c.exportable(),false);await c.click(action('report'));await c.click(action('export'));assert.deepEqual(downloaded,['report']);
});

test('real browser: consent, focus and local remix survive viewport/theme interactions' ,async t=>{
 const {chromium}=require('playwright');
 if(!process.env.REPAGER_CHROMIUM_PATH&&!fs.existsSync(chromium.executablePath())){t.skip('Set REPAGER_CHROMIUM_PATH to an installed browser for UI regression coverage');return;}
 const browser=await chromium.launch({headless:true,executablePath:process.env.REPAGER_CHROMIUM_PATH});
 try{const page=await browser.newPage({viewport:{width:390,height:844}});const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.setContent('<repager-canvas></repager-canvas>');
  await page.evaluate(({record,selectedScope})=>{
   window.testCalls=[];window.__HERMES_PLUGIN_SDK__={fetchJSON:async(path,opts={})=>{window.testCalls.push({path,opts});if(path.endsWith('/jobs'))return {jobs:[]};if(path.endsWith('/health'))return {};if(path.endsWith('/reviews'))return {reviews:[]};if(path.endsWith('/remix'))return {job:{id:'job'}};if(path.endsWith('/jobs/job'))return {job:{state:'running',review_id:'r'}};throw Error('Unexpected synthetic endpoint '+path);},authedFetch:async()=>new Response('<!doctype html><p>Synthetic artifact</p>',{headers:{'Content-Type':'text/html'}})};
   window.testRecord=record;window.testScope=selectedScope;
  },{record:review(),selectedScope:scope()});
  // localStorage requires an origin; this is a synthetic route, never a real network request.
  await page.route('https://canvas.invalid/**',route=>route.fulfill({contentType:'text/html',body:'<repager-canvas></repager-canvas>'}));
  // Preserve the fixture globals across navigation by reinitializing at that origin.
  const init=await page.evaluate(()=>({record:window.testRecord,scope:window.testScope}));
  await page.goto('https://canvas.invalid/');
  await page.evaluate(({record,scope})=>{window.testCalls=[];window.__HERMES_PLUGIN_SDK__={fetchJSON:async(path,opts={})=>{window.testCalls.push({path,opts});if(path.endsWith('/jobs'))return {jobs:[]};if(path.endsWith('/health'))return {};if(path.endsWith('/reviews'))return {reviews:[]};if(path.endsWith('/remix'))return {job:{id:'job'}};if(path.endsWith('/jobs/job'))return {job:{state:'running',review_id:'r'}};throw Error('Unexpected synthetic endpoint '+path);},authedFetch:async()=>new Response('<!doctype html><p>Synthetic artifact</p>')};window.testRecord=record;window.testScope=scope;},init);
  await page.addScriptTag({content:source});await page.evaluate(()=>{const c=document.querySelector('repager-canvas');c.review=window.testRecord;c.scope=window.testScope;c.selected='f';c.editScope=true;c.render();});
  const root=page.locator('repager-canvas');await root.locator('[name=preserve_copy]').check();await root.locator('[name=preserve_destination]').check();
  await root.locator('[data-action=viewport][data-view=desktop]').click();assert.equal(await root.locator('[name=preserve_copy]').isChecked(),true);
  await root.locator('[data-action=theme]').click();assert.equal(await root.locator('[name=preserve_destination]').isChecked(),true);
  await root.locator('[data-action=theme]').focus();await page.keyboard.press('Enter');
  assert.equal(await page.evaluate(()=>document.querySelector('repager-canvas').shadowRoot.activeElement?.dataset.action),'theme');
  await root.locator('[data-action=viewport][data-view=mobile]').focus();await page.keyboard.press('Space');
  assert.equal(await page.evaluate(()=>document.querySelector('repager-canvas').shadowRoot.activeElement?.dataset.view),'mobile');
  await root.locator('[data-action=comparison][data-side=proposal]').focus();await page.keyboard.press('Enter');
  assert.equal(await page.evaluate(()=>document.querySelector('repager-canvas').shadowRoot.activeElement?.dataset.side),'proposal');
  await root.locator('[name=revision]').focus();await page.evaluate(()=>document.querySelector('repager-canvas').render());
  assert.equal(await page.evaluate(()=>document.querySelector('repager-canvas').shadowRoot.activeElement?.name),'revision');
  await root.locator('[data-action=edit-scope]').click();await root.locator('[data-action=edit-scope]').click();
  assert.equal(await root.locator('[name=preserve_copy]').isChecked(),false);assert.equal(await root.locator('[name=preserve_destination]').isChecked(),false);
  await root.locator('[name=preserve_copy]').check();await root.locator('[name=preserve_destination]').check();
  await page.evaluate(()=>{const c=document.querySelector('repager-canvas');c.selectedCTA='different';c.change({target:{name:'cta_id',value:'c'}});});
  assert.equal(await root.locator('[name=preserve_copy]').isChecked(),false);assert.equal(await root.locator('[name=preserve_destination]').isChecked(),false);
  await root.locator('[data-action=edit-scope]').click();
  await root.locator('summary').filter({hasText:'AI-assisted alternative'}).click();
  await root.locator('[name=instruction]').fill('Keep the current copy');
  await page.evaluate(()=>{const c=document.querySelector('repager-canvas');const field=c.shadowRoot.querySelector('[name=instruction]');field.focus();field.setSelectionRange(5,9);c.render();});
  assert.deepEqual(await page.evaluate(()=>{const root=document.querySelector('repager-canvas').shadowRoot;return [root.activeElement.name,root.activeElement.selectionStart,root.activeElement.selectionEnd];}),['instruction',5,9]);
  assert.equal(await root.locator('[name=instruction]').inputValue(),'Keep the current copy');
  assert.equal(await root.locator('.saved').getAttribute('open'),null);
  await page.setViewportSize({width:1440,height:1000});
  await page.evaluate(()=>{const c=document.querySelector('repager-canvas');c.reviews=[{id:'recovered',status:'reviewed',source:{title:'Synthetic saved review'}}];c.render();});
  assert.equal(await root.locator('.saved').evaluate(el=>el.open),true);assert.equal(await root.locator('button.run[data-id=recovered]').isVisible(),true);
  await page.evaluate(()=>{const c=document.querySelector('repager-canvas');c.reviews.push({id:'second',status:'reviewed',source:{title:'Second synthetic saved review'}});c.render();});
  assert.equal(await root.locator('button.run[data-id=recovered]').isVisible(),true);
  await root.locator('form[data-form=remix] [name=layout]').selectOption('spotlight');
  await root.locator('form[data-form=remix] button').click();const posted=await page.evaluate(()=>window.testCalls.find(c=>c.path.endsWith('/remix')));assert.equal(JSON.parse(posted.opts.body).changes.layout,'spotlight');assert.equal(errors.length,0,errors.join('\n'));
 }finally{await browser.close();}
});
