/* Local portable-package contract. Shared by the worker and Node conformance tests. */
(function(root){
'use strict';
const MIB=1024*1024;
const BROWSER_LIMITS={archiveBytes:64*MIB,entryBytes:64*MIB,totalUncompressedBytes:96*MIB,jsonBytes:MIB,entries:7,compressionRatio:100};
function requireValue(ok,message){if(!ok)throw Error(message)}
function equal(a,b){if(a===b)return true;if(!a||!b||typeof a!=='object'||typeof b!=='object')return false;const keys=Object.keys(a);return keys.length===Object.keys(b).length&&keys.every(k=>Object.hasOwn(b,k)&&equal(a[k],b[k]))}
function strictJSON(bytes,name){
 requireValue(!(bytes[0]===239&&bytes[1]===187&&bytes[2]===191),name+': UTF-8-BOM nicht erlaubt');
 let text;try{text=new TextDecoder('utf-8',{fatal:true}).decode(bytes)}catch{throw Error(name+': ungültiges UTF-8/JSON')}let i=0,tokens=0;
 const fail=message=>{throw Error(name+': ungültiges JSON ('+message+')')};
 const whitespace=()=>{while(/[\x20\t\r\n]/.test(text[i]??'!'))i++};
 function string(){const start=i++;while(i<text.length){const c=text[i++];if(c==='"')return JSON.parse(text.slice(start,i));if(c==='\\')i++;}fail('Zeichenkette')}
 function value(depth){
  if(depth>64||++tokens>200000)fail('Parserlimit');whitespace();const c=text[i];
  if(c==='"')return string();
  if(c==='{'){
   i++;const object=Object.create(null);whitespace();if(text[i]==='}'){i++;return object}
   while(true){whitespace();if(text[i]!=='"')fail('Objektschlüssel');const key=string();if(Object.hasOwn(object,key))fail('doppelter Schlüssel '+key);whitespace();if(text[i++]!==':')fail('Doppelpunkt');object[key]=value(depth+1);whitespace();const end=text[i++];if(end==='}')return object;if(end!==',')fail('Objektende')}
  }
  if(c==='['){i++;const array=[];whitespace();if(text[i]===']'){i++;return array}while(true){array.push(value(depth+1));whitespace();const end=text[i++];if(end===']')return array;if(end!==',')fail('Arrayende')}}
  for(const [word,result]of [['true',true],['false',false],['null',null]])if(text.startsWith(word,i)){i+=word.length;return result}
  const number=text.slice(i).match(/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/);
  if(!number)fail('Wert');i+=number[0].length;const result=Number(number[0]);if(!Number.isFinite(result))fail('nichtendliche Zahl');return result;
 }
 const result=value(0);whitespace();if(i!==text.length)fail('zusätzlicher Inhalt');return result;
}
// The checked-in schema uses this finite subset of Draft 2020-12. Unknown
// keywords fail closed, so a future contract cannot silently bypass validation.
function schemaCheck(value,schema,path='manifest.json'){
 const allowed=new Set(['$schema','$id','title','type','const','enum','required','properties','additionalProperties','minimum','maximum','exclusiveMinimum','minLength','maxLength','pattern']);
 for(const key of Object.keys(schema))requireValue(allowed.has(key),'Nicht unterstützte Schemaregel: '+key);
 const fail=message=>requireValue(false,path+': '+message);
 if(Object.hasOwn(schema,'const')&&!equal(value,schema.const))fail('unerwarteter Formatwert');
 if(schema.enum&&!schema.enum.some(v=>equal(value,v)))fail('unzulässiger Wert');
 if(schema.type){const valid=schema.type==='object'?value!==null&&typeof value==='object'&&!Array.isArray(value):schema.type==='integer'?Number.isInteger(value):typeof value===schema.type;if(!valid)fail('ungültige Datentypen')}
 if(typeof value==='number'){
  if(!Number.isFinite(value))fail('Zahl muss endlich sein');
  if(schema.minimum!==undefined&&value<schema.minimum||schema.maximum!==undefined&&value>schema.maximum||schema.exclusiveMinimum!==undefined&&value<=schema.exclusiveMinimum)fail('Zahl außerhalb des Limits');
 }
 if(typeof value==='string'){
  const length=Array.from(value).length;
  if(schema.minLength!==undefined&&length<schema.minLength||schema.maxLength!==undefined&&length>schema.maxLength||schema.pattern&&!new RegExp(schema.pattern).test(value))fail('ungültiger Text');
 }
 if(schema.properties){for(const key of schema.required??[])if(!Object.hasOwn(value,key))fail('Feld fehlt: '+key);for(const key of Object.keys(value)){if(!Object.hasOwn(schema.properties,key)){if(schema.additionalProperties===false)fail('unerlaubtes Feld: '+key)}else schemaCheck(value[key],schema.properties[key],path+'/'+key)}}
}
const crcTable=Uint32Array.from({length:256},(_,n)=>{for(let i=0;i<8;i++)n=n&1?0xedb88320^(n>>>1):n>>>1;return n>>>0});
function crcUpdate(crc,bytes){for(const byte of bytes)crc=crcTable[(crc^byte)&255]^(crc>>>8);return crc>>>0}
const view=bytes=>new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
async function bytesAt(file,start,length){requireValue(start>=0&&length>=0&&start+length<=file.size,'ZIP: abgeschnittener Bereich');return new Uint8Array(await file.slice(start,start+length).arrayBuffer())}
function extras(bytes){const d=view(bytes);for(let i=0;i<bytes.length;){requireValue(i+4<=bytes.length,'ZIP: ungültige Zusatzfelder');const id=d.getUint16(i,true),size=d.getUint16(i+2,true);requireValue(id!==1&&i+4+size<=bytes.length,'ZIP64 oder ungültiges Zusatzfeld');i+=4+size}}
async function zipDirectory(file,spec,limits){
 requireValue(file.size>0&&file.size<=limits.archiveBytes,'Paket überschreitet das Browserlimit von '+Math.round(limits.archiveBytes/MIB)+' MiB');
 const tail=await bytesAt(file,Math.max(0,file.size-65557),Math.min(file.size,65557));const t=view(tail);let marker=-1;
 for(let i=tail.length-22;i>=0;i--)if(t.getUint32(i,true)===0x06054b50){marker=i;break}
 requireValue(marker>=0,'ZIP: Endverzeichnis fehlt');const end=marker,cdSize=t.getUint32(end+12,true),cdStart=t.getUint32(end+16,true),count=t.getUint16(end+10,true);
 requireValue(end+22+t.getUint16(end+20,true)===tail.length,'ZIP: ungültiges Ende');
 requireValue(t.getUint16(end+4,true)===0&&t.getUint16(end+6,true)===0&&t.getUint16(end+8,true)===count&&count===spec.files.length&&count<=limits.entries,'ZIP: Mehrteilarchiv, ZIP64 oder falsche Einträge/Pfade');
 requireValue(cdSize<=65536&&cdStart+cdSize===file.size-tail.length+marker,'ZIP: Zentralverzeichnis ungültig oder ZIP64');
 const bytes=await bytesAt(file,cdStart,cdSize),d=view(bytes),entries=new Map();let offset=0,total=0;
 for(let index=0;index<count;index++){
  requireValue(offset+46<=bytes.length&&d.getUint32(offset,true)===0x02014b50,'ZIP: ungültiger Zentraleintrag');
  const version=d.getUint16(offset+6,true),flags=d.getUint16(offset+8,true),method=d.getUint16(offset+10,true),crc=d.getUint32(offset+16,true),compressed=d.getUint32(offset+20,true),size=d.getUint32(offset+24,true),nl=d.getUint16(offset+28,true),el=d.getUint16(offset+30,true),cl=d.getUint16(offset+32,true),disk=d.getUint16(offset+34,true),attr=d.getUint32(offset+38,true),local=d.getUint32(offset+42,true);
  requireValue(offset+46+nl+el+cl<=bytes.length,'ZIP: abgeschnittener Dateiname');
  const name=new TextDecoder('utf-8',{fatal:true}).decode(bytes.subarray(offset+46,offset+46+nl));
  requireValue(spec.files.includes(name)&&!entries.has(name),'ZIP: fehlende Dateien, doppelte oder unerlaubte Pfade');
  requireValue(version<=20&&disk===0,'ZIP64/neue ZIP-Version nicht unterstützt');
  requireValue(!(flags&1),'ZIP: Verschlüsselte Dateien nicht erlaubt');requireValue(!(flags&~0x808),'ZIP: nicht unterstützte Flags');
  const mode=(attr>>>16)&0xf000;requireValue((mode===0||mode===0x8000)&&!(attr&16),'ZIP: kein regulärer Dateieintrag');
  requireValue(spec.compressionMethods.includes(method),'ZIP: Kompressionsverfahren nicht unterstützt');
  requireValue(size>0&&size<=limits.entryBytes,'ZIP: Dateigrößenlimit überschritten');requireValue(size<=Math.max(1,compressed)*limits.compressionRatio,'ZIP: übermäßige Kompression');
  if(name.endsWith('.json'))requireValue(size<=limits.jsonBytes,name+': JSON-Größenlimit überschritten');
  extras(bytes.subarray(offset+46+nl,offset+46+nl+el));total+=size;
  entries.set(name,{name,flags,method,crc,compressed,size,local});offset+=46+nl+el+cl;
 }
 requireValue(offset===bytes.length&&total<=limits.totalUncompressedBytes,'ZIP: Gesamtlimit oder Zentralverzeichnis ungültig');
 const ranges=[];
 for(const entry of entries.values()){
  const header=await bytesAt(file,entry.local,30),h=view(header);
  requireValue(h.getUint32(0,true)===0x04034b50&&h.getUint16(4,true)<=20&&h.getUint16(6,true)===entry.flags&&h.getUint16(8,true)===entry.method,'ZIP: lokaler Header widersprüchlich');
  const nl=h.getUint16(26,true),el=h.getUint16(28,true),names=await bytesAt(file,entry.local+30,nl+el);
  requireValue(new TextDecoder('utf-8',{fatal:true}).decode(names.subarray(0,nl))===entry.name,'ZIP beschädigt: lokale und zentrale Pfade widersprechen sich');extras(names.subarray(nl));
  for(const [position,expected]of [[14,entry.crc],[18,entry.compressed],[22,entry.size]])requireValue(h.getUint32(position,true)===expected||!!(entry.flags&8)&&h.getUint32(position,true)===0,'ZIP: lokale Größe/CRC widersprüchlich');
  entry.start=entry.local+30+nl+el;let end=entry.start+entry.compressed;requireValue(end<=cdStart,'ZIP: Nutzdaten überlappen Zentralverzeichnis');
  if(entry.flags&8){const raw=await bytesAt(file,end,Math.min(16,cdStart-end)),descriptor=view(raw),skip=raw.length>=4&&descriptor.getUint32(0,true)===0x08074b50?4:0;requireValue(raw.length>=skip+12&&descriptor.getUint32(skip,true)===entry.crc&&descriptor.getUint32(skip+4,true)===entry.compressed&&descriptor.getUint32(skip+8,true)===entry.size,'ZIP: ungültiger Datendeskriptor');end+=skip+12}
  ranges.push([entry.local,end]);
 }
 ranges.sort((a,b)=>a[0]-b[0]);for(let i=1;i<ranges.length;i++)requireValue(ranges[i][0]>=ranges[i-1][1],'ZIP: überlappende Einträge');
 return entries;
}
async function readEntry(file,entry){
 let stream=file.slice(entry.start,entry.start+entry.compressed).stream();
 if(entry.method===8){try{stream=stream.pipeThrough(new DecompressionStream('deflate-raw'))}catch{throw Error('Dieser Browser unterstützt DEFLATE-Import nicht. Aktuelles Chrome/Edge verwenden oder unkomprimiertes Analyzer-Paket exportieren.')}}
 const reader=stream.getReader(),output=new Uint8Array(entry.size);let count=0,crc=0xffffffff;
 try{while(true){const {done,value}=await reader.read();if(done)break;requireValue(count+value.length<=entry.size,entry.name+': tatsächliche Größe überschritten');output.set(value,count);count+=value.length;crc=crcUpdate(crc,value)}}finally{await reader.cancel().catch(()=>{});reader.releaseLock()}
 requireValue(count===entry.size&&(crc^0xffffffff)>>>0===entry.crc,entry.name+': ZIP-Größe/CRC beschädigt');return output;
}
async function validate(file,{schema,spec,limits={},onProgress=()=>{}}){
 const lim={...BROWSER_LIMITS};for(const [k,v]of Object.entries(limits)){requireValue(k in lim&&v>0&&v<=lim[k],'Browserlimits dürfen nur verkleinert werden');lim[k]=v}
 requireValue(!!globalThis.crypto?.subtle,'Sichere Paketprüfung benötigt HTTPS oder localhost (Web Crypto).');
 const entries=await zipDirectory(file,spec,lim);onProgress('Paketstruktur geprüft.');
 const manifest=strictJSON(await readEntry(file,entries.get('manifest.json')),'manifest.json');schemaCheck(manifest,schema);
 const n=manifest.frameCount;requireValue(entries.get('reference/poses.bin').size===n*924&&entries.get('reference/timestamps.bin').size===n*8,'Binärlänge: 33 Gelenke × 7 Float32 und ein Float64 pro Bild erwartet');
 const payload=Object.create(null);
 for(const [name,meta]of Object.entries(manifest.files)){
  const entry=entries.get(name);requireValue(entry.size===meta.size,name+': Dateigröße stimmt nicht');const bytes=await readEntry(file,entry);
  const digest=await crypto.subtle.digest('SHA-256',bytes),hex=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');requireValue(hex===meta.sha256,name+': SHA-256-Prüfsumme stimmt nicht');payload[name]=bytes;onProgress(name+' geprüft.');
 }
 const zoom=strictJSON(payload['reference/zoom.json'],'zoom.json');schemaCheck(zoom,schema.properties.zoom,'zoom.json');requireValue(equal(zoom,manifest.zoom)&&zoom.x+zoom.width<=1&&zoom.y+zoom.height<=1,'Zoom widerspricht Manifest oder liegt außerhalb des Videos');
 const quality=strictJSON(payload['reference/quality.json'],'quality.json');
 requireValue(quality&&equal(Object.keys(quality).sort(),['missingLandmarks','status','warnings'])&&['complete','partial'].includes(quality.status)&&Number.isInteger(quality.missingLandmarks)&&quality.missingLandmarks>=0&&quality.missingLandmarks<=n*33&&Array.isArray(quality.warnings)&&quality.warnings.length<=100&&quality.warnings.every(s=>typeof s==='string'&&Array.from(s).length<=500),'quality.json: ungültige Felder');
 const poses=payload['reference/poses.bin'],times=payload['reference/timestamps.bin'],pv=view(poses),tv=view(times);let previous=-1,missing=0;
 for(let f=0;f<n;f++){
  const t=tv.getFloat64(f*8,true);requireValue(Number.isFinite(t)&&t>=0&&t>previous&&t<=manifest.durationSeconds,'timestamps.bin: ungültiger/nichtmonotoner Zeitpunkt');previous=t;
  for(let j=0;j<33;j++){
   const base=(f*33+j)*28,values=Array.from({length:7},(_,k)=>pv.getFloat32(base+k*4,true));
   requireValue(values.slice(5).every(v=>Number.isFinite(v)&&v>=0&&v<=1),'poses.bin: ungültige Konfidenz');
   if(values.slice(0,5).some(Number.isNaN)){requireValue(values.slice(0,5).every(Number.isNaN)&&values[5]===0&&values[6]===0,'poses.bin: inkonsistente fehlende Werte');missing++}
   else requireValue(values.slice(0,5).every(Number.isFinite)&&values.slice(0,2).every(v=>v>=0&&v<=1),'poses.bin: ungültige Koordinaten');
  }
 }
 requireValue(quality.missingLandmarks===missing&&quality.status===(missing?'partial':'complete'),'quality.json: Fehlzahl/Status widerspricht Haltungspunkten');
 const video=payload['reference/video.mp4'],preview=payload['assets/preview.jpg'];requireValue(video.length>=8&&String.fromCharCode(...video.subarray(4,8))==='ftyp','video.mp4: MP4-Signatur fehlt');requireValue(preview[0]===255&&preview[1]===216&&preview[2]===255&&preview.at(-2)===255&&preview.at(-1)===217,'preview.jpg: JPEG-Signatur fehlt');
 return {manifest,quality,video:new Blob([video],{type:'video/mp4'}),poses:poses.buffer,timestamps:times.buffer};
}
const api={BROWSER_LIMITS,strictJSON,schemaCheck,validate,crcUpdate,equal};root.ChoreoCore=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
