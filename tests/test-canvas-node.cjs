// Browser tests for canvas interaction contracts. Test doubles are explicitly synthetic.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
function canvas(){
 const classes={};
 const context={window:{},HTMLElement:class {attachShadow(){this.shadowRoot={};}},customElements:{get:n=>classes[n],define:(n,c)=>classes[n]=c},URL,console};
 vm.runInNewContext(fs.readFileSync('dashboard/src/canvas.js','utf8'),context);
 return new classes['repager-canvas']();
}
test('finding selection follows change events, including keyboard interaction',async()=>{
 const c=canvas();c.render=()=>{};
 c.change({target:{name:'finding',dataset:{finding:'f-keyboard'}}});
 assert.equal(c.selected,'f-keyboard');
});
test('revision inspection is read-only and cannot reuse latest receipt',()=>{
 const c=canvas();c.review={revisions:[{number:1,artifact_hash:'a'},{number:2,artifact_hash:'b'}],verification:{revision:2,artifact_hash:'b',checks:[{status:'pass'}]}};
 c.inspectedRevision=1;
 assert.equal(c.inspected().number,1);
 assert.equal(c.exportable(),false);
 c.inspectedRevision=null;
 assert.equal(c.inspected().number,2);
 assert.equal(c.exportable(),true);
});
test('changing CTA does not rerender and erase approval checkboxes',()=>{
 const c=canvas();let renders=0;c.render=()=>renders++;
 const destination={textContent:''};c.shadowRoot={querySelector:()=>destination};
 c.scope={cta_candidates:[{id:'second',destination:'https://example.com/second'}]};
 c.change({target:{name:'cta_id',value:'second'}});
 assert.equal(c.selectedCTA,'second');assert.equal(destination.textContent,'https://example.com/second');assert.equal(renders,0);
});
test('retry connection resumes the existing job rather than only refreshing the gallery',async()=>{
 const c=canvas();c.isConnected=true;c.jobId='ongoing';c.busy='Working';c.render=()=>{};
 c.json=async()=>{throw Error('Network unavailable');};
 await c.poll();assert.equal(c.jobId,'ongoing');assert.equal(c.busy,'Working');
 let polls=0;c.poll=async()=>polls++;c.refresh=async()=>{throw Error('Gallery refresh cannot recover a job');};
 await c.click({target:{closest:selector=>selector==='[data-action]'?{disabled:false,dataset:{action:'refresh'}}:null}});
 assert.equal(polls,1);
});
test('completed job remains recoverable if loading its saved review fails',async()=>{
 const c=canvas();c.isConnected=true;c.jobId='finished';c.busy='Working';c.render=()=>{};c.refresh=async()=>{};
 let fail=true;c.json=async path=>{if(path.startsWith('/jobs/'))return {job:{state:'completed',review_id:'saved'}};if(fail)throw Error('Network unavailable');return {review:{id:'saved',findings:[],revisions:[]}};};
 await c.poll();assert.equal(c.jobId,'finished');assert.equal(c.busy,'Working');
 fail=false;await c.poll();assert.equal(c.jobId,null);assert.equal(c.busy,'');assert.equal(c.review.id,'saved');assert.equal(c.error,'');
});
test('an approved single finding can reopen explicit scope approval',()=>{
 const c=canvas();c.scope={cta_candidates:[{id:'cta',text:'Go',destination:'https://example.com/'}],headline:{text:'Heading'},bodies:[]};
 c.selected='f';c.selectedCTA='cta';c.editScope=true;c.viewTabs=()=>'';
 const r={source:{title:'Test',url:'https://example.com',captured_at:'',viewports:[{name:'desktop',width:1440,height:900,screenshot:'source-desktop.png'}],limitations:[]},findings:[{id:'f',kind:'judgment',title:'Explore',evidence_ids:[]}],contract:{finding_id:'f',cta_text:'Go',cta_destination:'https://example.com/'},revisions:[]};
 assert.match(c.reviewBody(r,null,null),/data-form="approve"/);
});
test('latest check receipt must bind the current contract',()=>{
 const c=canvas();c.review={contract:{approved_at:'new'},revisions:[{number:1,artifact_hash:'a',contract_hash:'old'}],verification:{revision:1,artifact_hash:'a',contract_hash:'different',checks:[{status:'pass'}]}};
 assert.equal(c.exportable(),false);
});
