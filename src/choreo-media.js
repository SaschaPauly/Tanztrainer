/* Bounded MP4 sample-description checks before browser decoder access. */
(function(root){
'use strict';
function check(ok,message){if(!ok)throw Error('Paketvideo: '+message)}
const tag=(d,p)=>String.fromCharCode(...new Uint8Array(d.buffer,d.byteOffset+p,4));
function boxes(d,start,end){const result=[];for(let p=start;p<end;){check(p+8<=end&&result.length<4096,'ungültige/zu viele MP4-Boxen');let size=d.getUint32(p);const type=tag(d,p+4);let header=8;if(size===1){check(p+16<=end,'abgeschnittene MP4-Box');size=d.getUint32(p+8)*4294967296+d.getUint32(p+12);header=16}if(size===0)size=end-p;check(Number.isSafeInteger(size)&&size>=header&&p+size<=end,'ungültige MP4-Boxgröße');result.push({type,start:p,data:p+header,end:p+size});p+=size}return result}
function one(list,type){const found=list.filter(b=>b.type===type);check(found.length===1,'MP4-Box fehlt/mehrfach: '+type);return found[0]}
function children(d,b){return boxes(d,b.data,b.end)}
function videoConfig(d,entry){
 check(['avc1','avc3'].includes(entry.type)&&entry.end>=entry.start+86,'H.264/AVC erwartet');
 const parts=boxes(d,entry.start+86,entry.end),config=one(parts,'avcC');check(config.end-config.data>=8,'AVC-Konfiguration fehlt');
 const pixelAspect=parts.filter(b=>b.type==='pasp');check(pixelAspect.length<=1,'mehrdeutige Pixelgeometrie');
 if(pixelAspect.length){const p=pixelAspect[0];check(p.end-p.data===8&&d.getUint32(p.data)>0&&d.getUint32(p.data)===d.getUint32(p.data+4),'quadratische Videopixel erwartet')}
 const p=config.data;check(d.getUint8(p)===1&&(d.getUint8(p+5)&31)>=1,'AVC-SPS fehlt');
 const length=d.getUint16(p+6);check(length>=5&&p+8+length<=config.end,'ungültige AVC-SPS');
 const raw=new Uint8Array(d.buffer,d.byteOffset+p+8,length);check((raw[0]&31)===7,'ungültige AVC-SPS');
 const bytes=[];let zeros=0;for(let i=1;i<raw.length;i++){if(zeros>=2&&raw[i]===3){zeros=0;continue}bytes.push(raw[i]);zeros=raw[i]===0?zeros+1:0}
 let bit=0;function bits(n){check(bit+n<=bytes.length*8,'abgeschnittene SPS');let v=0;while(n--)v=v*2+((bytes[bit>>3]>>(7-(bit++&7)))&1);return v}
 function ue(){let n=0;while(bits(1)===0){check(++n<=30,'ungültige SPS-Zahl')}return 2**n-1+bits(n)}
 const profile=bits(8);bits(16);ue();check(profile===d.getUint8(p+1)&&[66,77,88,100].includes(profile),'8-Bit-H.264 erwartet');
 if(profile===100)check(ue()===1&&ue()===0&&ue()===0,'H.264 mit 8 Bit und 4:2:0 erwartet');
 return [d.getUint16(entry.start+32),d.getUint16(entry.start+34)];
}
function audioConfig(d,entry){
 check(entry.type==='mp4a'&&entry.end>=entry.start+36&&d.getUint16(entry.start+16)===0,'AAC-Audiospur erwartet');
 const config=one(boxes(d,entry.start+36,entry.end),'esds');let p=config.data+4;
 function descriptor(type){check(p+2<=config.end&&d.getUint8(p++)===type,'ungültige AAC-Konfiguration');let size=0,b,count=0;do{check(p<config.end&&count++<4,'ungültige AAC-Deskriptorlänge');b=d.getUint8(p++);size=size*128+(b&127)}while(b&128);check(p+size<=config.end,'abgeschnittener AAC-Deskriptor');return p+size}
 descriptor(3);check(p+3<=config.end,'AAC-ES fehlt');p+=2;const flags=d.getUint8(p++);
 if(flags&128)p+=2;if(flags&64){check(p<config.end,'AAC-URL fehlt');p+=1+d.getUint8(p)}if(flags&32)p+=2;
 descriptor(4);check(p<config.end&&d.getUint8(p)===0x40,'MPEG-4-AAC erwartet');
}
async function inspect(blob,manifest){
 let p=0,count=0,moov=null;
 while(p<blob.size){check(++count<=4096&&p+8<=blob.size,'ungültige MP4-Struktur');const bytes=new Uint8Array(await blob.slice(p,p+16).arrayBuffer()),d=new DataView(bytes.buffer);let size=d.getUint32(0),header=8;if(size===1){check(bytes.length===16,'abgeschnittener MP4-Header');size=d.getUint32(8)*4294967296+d.getUint32(12);header=16}if(size===0)size=blob.size-p;check(Number.isSafeInteger(size)&&size>=header&&p+size<=blob.size,'ungültige MP4-Größe');if(tag(d,4)==='moov'){check(!moov&&size<=8*1024*1024,'MP4-Metadaten fehlen/zu groß/mehrfach');moov=await blob.slice(p+header,p+size).arrayBuffer()}p+=size}
 check(moov,'MP4-Metadaten fehlen');const d=new DataView(moov),tracks=boxes(d,0,d.byteLength).filter(b=>b.type==='trak');let video=0,audio=0;
 for(const track of tracks){
  const parts=children(d,track),media=one(parts,'mdia'),mdia=children(d,media),handler=one(mdia,'hdlr');check(handler.data+12<=handler.end,'Tracktyp fehlt');const type=tag(d,handler.data+8);check(['vide','soun'].includes(type),'unerwartete MP4-Spur');
  const stbl=one(children(d,one(mdia,'minf')),'stbl'),stsd=one(children(d,stbl),'stsd');check(stsd.data+8<=stsd.end&&d.getUint32(stsd.data)===0&&d.getUint32(stsd.data+4)===1,'ungültige Samplebeschreibung');const samples=boxes(d,stsd.data+8,stsd.end);check(samples.length===1,'mehrere Samplebeschreibungen');
  if(type==='vide'){
   video++;const dims=videoConfig(d,samples[0]);check(dims[0]===manifest.video.width&&dims[1]===manifest.video.height,'Videogröße widerspricht Manifest');
   const tkhd=one(parts,'tkhd'),version=d.getUint8(tkhd.data);check(version===0||version===1,'Trackversion unbekannt');const matrix=tkhd.data+(version===1?52:40);check(matrix+44<=tkhd.end,'Trackgeometrie fehlt');const expected=[65536,0,0,0,65536,0,0,0,1073741824];check(expected.every((v,i)=>d.getInt32(matrix+i*4)===v),'Video muss physisch aufrecht und ungespiegelt sein');
  }else{audio++;audioConfig(d,samples[0])}
 }
 check(video===1&&audio<=1&&(manifest.audio.source==='none'||audio===1),'Video-/Audiospuren widersprechen Paket');
 check(manifest.video.width*manifest.video.height<=4096*2160,'Videogeometrie überschreitet das Browser-Decoderlimit');
}
const api={inspect};root.ChoreoMedia=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
