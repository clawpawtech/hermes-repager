const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const crypto=require('node:crypto');
const wordmark=fs.readFileSync('dashboard/brand/wordmark.svg','utf8');
const favicon=fs.readFileSync('dashboard/brand/favicon.svg','utf8');
const bundle=fs.readFileSync('dashboard/dist/index.js','utf8');
const brand=JSON.parse(bundle.match(/^const BRAND=(.+);$/m)[1]);
test('live wordmark treatment replaces p, not the later g, without a runtime font',()=>{
 const groups=[...wordmark.matchAll(/<g\b[^>]*>/g)].map(m=>m[0]);
 assert.equal(groups.length,7);assert.match(groups[2],/data-brand-letter="p"/);assert.match(groups[2],/data-source-glyph="g"/);assert.match(groups[2],/scale\(-1,1\)/);assert.match(groups[2],/#F7931A/);
 assert.ok(!groups[4].includes('scale(-1,1)'));assert.doesNotMatch(wordmark,/<(?:text|script|foreignObject|image)\b|\bhref\s*=/i);
 assert.equal(brand.wordmark,wordmark);assert.match(wordmark,/fill="currentColor"/);
});
test('bundled app icon and standalone favicon exactly preserve live source bytes',()=>{
 assert.equal(crypto.createHash('sha256').update(favicon).digest('hex'),'85a12292829fe3133d8f8fd80ba25947fa060257b5b0e6b4c159cb02654da328');
 const uri='data:image/svg+xml;base64,'+Buffer.from(favicon).toString('base64');
 assert.equal(brand.favicon,uri);assert.ok(fs.readFileSync('dashboard/index.html','utf8').includes(`href="${uri}"`));
});
test('branding stays plugin-owned, lowercase and built without external font resources',()=>{
 assert.equal(JSON.parse(fs.readFileSync('dashboard/manifest.json','utf8')).label,'repager');
 assert.match(bundle,/aria-label="repager - start a new review"/);
 assert.doesNotMatch(bundle,/fonts\.googleapis|fonts\.gstatic|document\.head\.(?:append|prepend)/);
 assert.ok(fs.existsSync('dashboard/brand/Manrope-OFL.txt'));
});
