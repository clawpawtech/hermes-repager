// Trusted, bounded measurements; no source HTML/CSS/JS is evaluated here.
export function opaqueRGB(value) {
  const m=/^rgba?\(\s*([\d.]+)[, ]+([\d.]+)[, ]+([\d.]+)(?:\s*[,/]\s*([\d.]+))?\s*\)$/.exec(value);
  if(!m || (m[4]!==undefined && Number(m[4])!==1))return null;
  const rgb=m.slice(1,4).map(Number);
  return rgb.every(v=>Number.isFinite(v)&&v>=0&&v<=255)?rgb:null;
}
export function contrastRatio(foreground,background) {
  const a=opaqueRGB(foreground),b=opaqueRGB(background);
  if(!a||!b)return null;
  const luminance=rgb=>rgb.map(v=>{v/=255;return v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4;}).reduce((s,v,i)=>s+v*[0.2126,0.7152,0.0722][i],0);
  const x=luminance(a),y=luminance(b);
  return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05);
}

// All browser helpers are nested so Playwright serialization has no closure dependencies.
export function measureReadability() {
  const head=[...document.querySelectorAll('.rp-head')];
  const bodies=[...document.querySelectorAll('.rp-body')];
  const links=[...document.querySelectorAll('.rp-cta-link')];
  const cta=links.length===1?links[0]:null;
  const colors=el=>{
    const foreground=getComputedStyle(el).color;
    let background=null;
    for(let node=el;node;node=node.parentElement){
      const s=getComputedStyle(node);
      if(Number(s.opacity)!==1 || s.filter!=='none' || s.backdropFilter!=='none' || s.mixBlendMode!=='normal' || s.backgroundImage!=='none')return null;
      if(background===null && !/^rgba\(.*[,/]\s*0\s*\)$/.test(s.backgroundColor))background=s.backgroundColor;
    }
    return background?{foreground,background}:null;
  };
  let complete=false,target=false;
  if(cta){
    const r=cta.getBoundingClientRect();
    target=r.width>=44&&r.height>=44;
    complete=cta.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})&&r.width>0&&r.height>0&&r.left>=0&&r.top>=0&&r.right<=innerWidth&&r.bottom<=innerHeight;
    // Reject geometric clipping by scroll/clip containers, even when the samples miss it.
    for(let n=cta.parentElement;n&&complete;n=n.parentElement){
      const s=getComputedStyle(n),b=n.getBoundingClientRect();
      if(s.clipPath!=='none'||s.maskImage!=='none'||s.clip!=='auto')complete=false;
      if(/hidden|clip|auto|scroll/.test(s.overflowX)&&(r.left<b.left+n.clientLeft||r.right>b.left+n.clientLeft+n.clientWidth))complete=false;
      if(/hidden|clip|auto|scroll/.test(s.overflowY)&&(r.top<b.top+n.clientTop||r.bottom>b.top+n.clientTop+n.clientHeight))complete=false;
    }
    if(getComputedStyle(cta).clipPath!=='none')complete=false;
    for(const fx of [0.05,0.5,0.95])for(const fy of [0.05,0.5,0.95]){
      const hit=document.elementFromPoint(r.left+r.width*fx,r.top+r.height*fy);
      if(!hit || !(hit===cta||cta.contains(hit)))complete=false;
    }
  }
  return {headline:head.length===1?head[0].textContent:null,bodies:bodies.map(el=>el.textContent),ctaLabel:cta?.textContent??null,
    headingColors:head.map(colors),bodyColors:bodies.map(colors),ctaColors:links.map(colors),target,complete};
}
