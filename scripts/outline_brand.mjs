// Optional asset-authoring tool. Runtime/build do not load fonts or this dependency.
// Usage: REPAGER_BRAND_TOOLS=/path/to/node_modules node scripts/outline_brand.mjs 700.ttf 800.ttf output.svg
import {createRequire} from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
const require=createRequire(import.meta.url);
const opentype=require(process.env.REPAGER_BRAND_TOOLS?path.join(process.env.REPAGER_BRAND_TOOLS,'opentype.js'): 'opentype.js');
const [regularFile,accentFile,output]=process.argv.slice(2);
if(!output)throw Error('Explicit Manrope 700, Manrope 800 and new SVG output required');
const regular=opentype.loadSync(regularFile),accent=opentype.loadSync(accentFile);
const size=200,spacing=-.02*size,letters=[...'regager'];
let x=0,minY=Infinity,maxY=-Infinity;
const paths=letters.map((letter,i)=>{
 const font=i===2?accent:regular,glyph=font.charToGlyph(letter),outline=glyph.getPath(0,0,size),box=outline.getBoundingBox();
 minY=Math.min(minY,box.y1);maxY=Math.max(maxY,box.y2);
 const advance=glyph.advanceWidth*size/font.unitsPerEm;
 const transform=i===2?`translate(${(x+advance).toFixed(3)},0) scale(-1,1)`:`translate(${x.toFixed(3)},0)`;
 const result=`<g transform="${transform}"${i===2?' data-brand-letter="p" data-source-glyph="g" fill="#F7931A"':''}><path d="${outline.toPathData(3)}"/></g>`;
 const sameRun=i===0||(i>=3&&i<letters.length-1);
 x+=advance+spacing+(sameRun?font.getKerningValue(glyph,font.charToGlyph(letters[i+1]))*size/font.unitsPerEm:0);
 return result;
});
const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 ${(minY-2).toFixed(3)} ${(x-spacing+2).toFixed(3)} ${(maxY-minY+4).toFixed(3)}" role="img" aria-label="repager" fill="currentColor">\n${paths.join('\n')}\n</svg>\n`;
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,svg,{flag:'wx'});
console.log('Outlined live re + mirrored orange g + ager; no font required at runtime.');
