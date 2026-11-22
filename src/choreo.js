/* Browser session and original-timeline pose adapter; no external libraries. */
(function(root){
'use strict';
const MAX_POSE_AGE=.2;
class Reference{
 constructor(result){Object.assign(this,result);this.poseView=new DataView(result.poses);this.timeView=new DataView(result.timestamps)}
 timestamp(index){return this.timeView.getFloat64(index*8,true)}
 frameAt(seconds){if(!Number.isFinite(seconds)||seconds<0||seconds>this.manifest.durationSeconds||seconds+1e-6<this.timestamp(0))return null;let lo=0,hi=this.manifest.frameCount-1;while(lo<hi){const mid=(lo+hi+1)>>1;if(this.timestamp(mid)<=seconds+1e-6)lo=mid;else hi=mid-1}return seconds-this.timestamp(lo)<=MAX_POSE_AGE+1e-6?lo:null}
 poseAt(seconds){const index=this.frameAt(seconds);if(index===null)return null;return Array.from({length:33},(_,j)=>{const offset=(index*33+j)*28,v=this.poseView,x=v.getFloat32(offset,true),y=v.getFloat32(offset+4,true);if(Number.isNaN(x))return null;const visibility=v.getFloat32(offset+20,true),presence=v.getFloat32(offset+24,true);return {x,y,visibility:Math.min(visibility,presence),presence,world:{x:v.getFloat32(offset+8,true),y:v.getFloat32(offset+12,true),z:v.getFloat32(offset+16,true)}}})}
 close(){if(this.url)URL.revokeObjectURL(this.url);this.url=null;this.poses=null;this.timestamps=null;this.poseView=null;this.timeView=null;this.video=null}
}
async function open(file,{signal,onProgress=()=>{}}={}){
 if(!globalThis.Worker||!globalThis.crypto?.subtle)throw Error('Paketimport benötigt Web Worker und Web Crypto. Aktuelles Chrome/Edge über HTTPS oder localhost verwenden.');
 if(file.size>64*1024*1024)throw Error('Paket überschreitet das Browserlimit von 64 MiB. Ein kleineres Video im PC-Analyzer vorbereiten.');
 const abort=()=>new DOMException('Paketimport abgebrochen.','AbortError');
 const result=await new Promise((resolve,reject)=>{
  if(signal?.aborted){reject(abort());return}
  const worker=new Worker('./src/choreo-worker.js');let done=false;
  const stop=()=>{if(done)return;done=true;worker.onmessage=null;worker.onerror=null;worker.terminate();signal?.removeEventListener('abort',cancel)};
  const cancel=()=>{stop();reject(abort())};signal?.addEventListener('abort',cancel,{once:true});
  worker.onmessage=({data})=>{if(data.progress){onProgress(data.progress);return}stop();if(data.error)reject(Error(data.error));else resolve(data.result)};
  worker.onerror=()=>{stop();reject(Error('Paketprüfung im Hintergrund konnte nicht gestartet/abgeschlossen werden. Seite über HTTPS oder localhost öffnen.'))};try{worker.postMessage({file})}catch(error){stop();reject(error)}
 });
 const reference=new Reference(result),probe=document.createElement('video');reference.url=URL.createObjectURL(result.video);probe.muted=true;probe.playsInline=true;probe.preload='auto';
 try{
  await new Promise((resolve,reject)=>{
   const finish=error=>{clearTimeout(timer);signal?.removeEventListener('abort',cancel);probe.onloadeddata=null;probe.onerror=null;error?reject(error):resolve()};
   const cancel=()=>finish(abort()),timer=setTimeout(()=>finish(Error('Paketvideo konnte nicht rechtzeitig dekodiert werden.')),15000);
   probe.onloadeddata=()=>{const m=result.manifest;if(probe.videoWidth!==m.video.width||probe.videoHeight!==m.video.height||!Number.isFinite(probe.duration)||Math.abs(probe.duration-m.durationSeconds)>.1)finish(Error('Dekodierte Videogeometrie/Dauer widerspricht dem Paket.'));else finish()};
   probe.onerror=()=>finish(Error('H.264/AAC-Paketvideo wird von diesem Browser nicht dekodiert.'));
   signal?.addEventListener('abort',cancel,{once:true});if(signal?.aborted){cancel();return}probe.src=reference.url;probe.load();
  });
  return reference;
 }catch(error){reference.close();throw error}
 finally{probe.removeAttribute('src');probe.load()}
}
const api={Reference,open,MAX_POSE_AGE};root.Choreo=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
