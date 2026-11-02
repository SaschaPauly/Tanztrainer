/* Static reference-video framing. No camera access and no network requests. */
'use strict';
const VideoZoom = (() => {
  const VERSION = 'zoom-v1-mediapipe-lite-0.10.21';
  const CACHE = 'tanztrainer.zoom.results';
  const required = [0,7,8,...Array.from({length:22},(_,i)=>i+11)];
  const clamp = (v,a,b) => Math.max(a,Math.min(b,v));
  function validBox(b) {
    return b && ['x','y','w','h'].every(k=>Number.isFinite(b[k])) &&
      b.x>=0 && b.y>=0 && b.w>0 && b.h>0 && b.x+b.w<=1.000001 && b.y+b.h<=1.000001;
  }
  function poseBox(p) {
    // Missing hands/feet or implausible coordinates invalidate the entire analysis,
    // rather than silently discarding a potentially important extremum.
    if (!p || required.some(i=>!p[i] || (p[i].visibility??0)<.65 || (p[i].presence??1)<.65 ||
        !Number.isFinite(p[i].x) || !Number.isFinite(p[i].y) ||
        p[i].x<0 || p[i].x>1 || p[i].y<0 || p[i].y>1)) return null;
    const xs=required.map(i=>p[i].x), ys=required.map(i=>p[i].y);
    const x=Math.min(...xs), y=Math.min(...ys), w=Math.max(...xs)-x, h=Math.max(...ys)-y;
    if(h<.15 || w<.025 || h>.98) return null;
    const torso=Math.hypot(p[11].x-p[23].x,p[11].y-p[23].y);
    if(torso<.025 || torso>h*.8) return null;
    return {x,y,w,h};
  }
  function union(a,b) {
    if(!a)return {...b};
    const x=Math.min(a.x,b.x),y=Math.min(a.y,b.y);
    return {x,y,w:Math.max(a.x+a.w,b.x+b.w)-x,h:Math.max(a.y+a.h,b.y+b.h)-y};
  }
  function padded(b) {
    // 5% image reserve on every side; extra crown allowance above face landmarks.
    const x=Math.max(0,b.x-.05), y=Math.max(0,b.y-.05-b.h*.08);
    return {x,y,w:Math.min(1,b.x+b.w+.05)-x,h:Math.min(1,b.y+b.h+.05)-y};
  }
  function moved(a,b) {
    return Math.max(Math.abs(a.x-b.x),Math.abs(a.y-b.y),
      Math.abs(a.x+a.w-b.x-b.w),Math.abs(a.y+a.h-b.y-b.h))>.035;
  }
  function framing(b,sw,sh,vw,vh) {
    if(!validBox(b)||![sw,sh,vw,vh].every(n=>Number.isFinite(n)&&n>0))return null;
    // Expand the union to viewport aspect ratio when source bounds permit.
    // Otherwise contain it with letterboxing; never cover/cut the union.
    let w=b.w*sw,h=b.h*sh;
    const ratio=vw/vh;
    if(w/h<ratio)w=Math.min(sw,h*ratio);else h=Math.min(sh,w/ratio);
    const x=clamp((b.x+b.w/2)*sw-w/2,0,sw-w);
    const y=clamp((b.y+b.h/2)*sh-h/2,0,sh-h);
    const scale=Math.min(vw/w,vh/h), base=Math.min(vw/sw,vh/sh);
    return {x,y,w,h,scale,zoom:scale/base,dx:(vw-w*scale)/2-x*scale,dy:(vh-h*scale)/2-y*scale};
  }
  function waitEvent(video,event,signal,action) {
    return new Promise((resolve,reject)=>{
      const done=()=>{cleanup();resolve();};
      const fail=()=>{cleanup();reject(Error('Videobild nicht verfügbar'));};
      const abort=()=>{cleanup();reject(new DOMException('Abgebrochen','AbortError'));};
      const timer=setTimeout(fail,8000);
      function cleanup(){clearTimeout(timer);video.removeEventListener(event,done);video.removeEventListener('error',fail);signal.removeEventListener('abort',abort);}
      video.addEventListener(event,done,{once:true});video.addEventListener('error',fail,{once:true});signal.addEventListener('abort',abort,{once:true});
      if(signal.aborted){abort();return;}try{action();}catch(e){cleanup();reject(e);}
    });
  }
  const check=signal=>{if(signal.aborted)throw new DOMException('Abgebrochen','AbortError');};
  async function fingerprint(file,signal) {
    // Hash every byte in bounded chunks. No entire-video ArrayBuffer in memory.
    const hashes=[];
    for(let offset=0;offset<file.size;offset+=4*1024*1024){
      check(signal);
      const chunk=await file.slice(offset,offset+4*1024*1024).arrayBuffer();
      hashes.push(new Uint8Array(await crypto.subtle.digest('SHA-256',chunk)));
    }
    check(signal);
    const bytes=new Uint8Array(hashes.length*32);hashes.forEach((h,i)=>bytes.set(h,i*32));
    return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
  }
  function readCache(key){try{const list=JSON.parse(localStorage.getItem(CACHE)||'[]');const hit=list.find(e=>e.key===key);return hit&&(hit.box===null||validBox(hit.box))?hit:undefined;}catch{return undefined;}}
  function writeCache(key,box){try{let list=JSON.parse(localStorage.getItem(CACHE)||'[]');if(!Array.isArray(list))list=[];list=[{key,box},...list.filter(e=>e.key!==key)].slice(0,20);localStorage.setItem(CACHE,JSON.stringify(list));}catch{/* Storage disabled/full: current session still works. */}}
  async function analyze({file,crop,detect,signal,onProgress=()=>{}}) {
    let video,source;
    try {
      const hash=await fingerprint(file,signal),key=VERSION+':'+crop+':'+file.size+':'+hash;
      const cached=readCache(key);if(cached)return {box:cached.box,cached:true};
      video=document.createElement('video');video.muted=true;video.playsInline=true;video.preload='auto';source=URL.createObjectURL(file);
      await waitEvent(video,'loadeddata',signal,()=>{video.src=source;video.load();});
      const duration=video.duration;
      // Never analyze just the beginning of a long/unknown video.
      if(!Number.isFinite(duration)||duration<=0||duration>300)throw Error('Videodauer außerhalb des Analysebereichs (maximal 5 Minuten)');
      const right=crop==='right',sx=right?video.videoWidth/2:0,sw=video.videoWidth-sx;
      const canvas=document.createElement('canvas'),k=Math.min(1,384/Math.max(sw,video.videoHeight));
      canvas.width=Math.max(1,Math.round(sw*k));canvas.height=Math.max(1,Math.round(video.videoHeight*k));
      const ctx=canvas.getContext('2d');let bounds=null,count=0;
      const sample=async t=>{
        check(signal);if(++count>1800)throw Error('Analysegrenze erreicht');
        if(Math.abs(video.currentTime-t)>.001||video.readyState<2)await waitEvent(video,'seeked',signal,()=>{video.currentTime=t;});
        check(signal);ctx.drawImage(video,sx,0,sw,video.videoHeight,0,0,canvas.width,canvas.height);
        const b=poseBox(detect(canvas));if(!b){writeCache(key,null);throw Error('Person nicht durchgehend vollständig und sicher erkannt');}
        bounds=union(bounds,b);onProgress(Math.min(99,Math.round(t/duration*100)));
        await new Promise(r=>setTimeout(r,0));return b;
      };
      let previous=await sample(0),last=0;
      const end=Math.max(0,duration-.001);
      for(let t=Math.min(.5,end);t>last;t=Math.min(t+.5,end)){
        const current=await sample(t);
        if(moved(previous,current))for(let q=last+.125;q<t-.01;q+=.125)await sample(q);
        previous=current;last=t;
      }
      check(signal);const box=padded(bounds);writeCache(key,box);return {box,cached:false,samples:count};
    } finally {if(video){video.pause();video.removeAttribute('src');video.load();}if(source)URL.revokeObjectURL(source);}
  }
  return {validBox,poseBox,union,padded,moved,framing,analyze,fingerprint,readCache,writeCache};
})();
if(typeof module!=='undefined')module.exports=VideoZoom;
