"""Offline, synchronized skeleton preview; no server, CDN or network requests."""
import base64
import json
from pathlib import Path
import zipfile

from analyzer.validate import validate


def write_preview(output, variants, summary):
    models = []
    expected_times = None
    for name, package, diagnostics in variants:
        manifest = validate(package)
        if manifest['frameCount'] > 20000:
            raise ValueError('Vorschau auf 20000 Zeitpunkte begrenzt; --max-fps für längere Videos verwenden.')
        with zipfile.ZipFile(package) as archive:
            times = archive.read('reference/timestamps.bin')
            if expected_times is not None and times != expected_times:
                raise ValueError('Modellvergleich erfordert identische Analysezeitpunkte.')
            expected_times = times
            models.append(dict(name=name, manifest=manifest, diagnostics=diagnostics,
                               poses=base64.b64encode(archive.read('reference/poses.bin')).decode('ascii'),
                               times=base64.b64encode(times).decode('ascii')))
    payload = json.dumps(dict(models=models, summary=summary), ensure_ascii=True, allow_nan=False)
    payload = payload.replace('<', '\\u003c').replace('&', '\\u0026')
    controls = Path(__file__).with_name('preview_controls.js').read_text(encoding='utf-8')
    Path(output).write_text(HTML.replace('__CONTROLS__', controls).replace('__PAYLOAD__', payload), encoding='utf-8')


HTML = r'''<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; media-src 'self' file:; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'">
<title>Showtanz – Modellvergleich</title>
<style>
:root{color-scheme:dark;font:16px system-ui,sans-serif;background:#101722;color:#edf2f8}body{margin:0;padding:24px;max-width:1600px;margin-inline:auto}
h1{font-size:1.7rem;margin:0 0 8px}p{line-height:1.5}.muted{color:#bac6d9}button,select,input{font:inherit}button,select{background:#25354b;border:1px solid #657993;color:inherit;border-radius:8px;padding:8px 12px;cursor:pointer}button:hover{background:#354d6e}
.controls{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:16px;background:#1b2739;border-radius:12px;margin-block:16px}.controls label{display:flex;align-items:center;gap:6px}#seek{flex:1;min-width:180px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.card{background:#1b2739;border-radius:12px;overflow:hidden}.card h2,.card p{margin:12px}.card h2{font-size:1.2rem}.card canvas{display:block;width:100%;height:auto;background:#000}.status{min-height:4em;font-size:.9rem;white-space:pre-line}table{border-collapse:collapse;width:100%;margin-block:20px}th,td{text-align:left;padding:10px;border-bottom:1px solid #38475c}th{color:#bac6d9}.legend{display:flex;gap:18px;flex-wrap:wrap}.green{color:#4ff0a4}.amber{color:#ffd05e}.red{color:#ff6577}#error{color:#ff8996}summary{cursor:pointer;font-weight:600}details{padding:12px;background:#1b2739;border-radius:10px;margin-top:16px}li{margin-block:6px}
.grid.single{grid-template-columns:minmax(0,1fr);max-width:1100px;margin-inline:auto}
.grid.single canvas{max-height:75vh;object-fit:contain}
@media(max-width:900px){.grid{grid-template-columns:1fr}body{padding:12px}table{font-size:.85rem}th,td{padding:7px}}
</style></head><body>
<h1>Skelettvorschau und Modellvergleich</h1>
<p class="muted">Alle Modelle zeigen denselben Videozeitpunkt. Die Farben kennzeichnen Modellkonfidenz; sie sind keine gemessene Fehlerwahrscheinlichkeit.</p>
<p id="scope"></p><p id="error" role="alert"></p>
<video id="source" src="reference.mp4" preload="metadata" playsinline hidden></video>
<div class="controls">
<button id="play" type="button">Abspielen</button><button id="back" type="button" aria-label="Ein Analysebild zurück">◀ Bild</button><button id="next" type="button">Bild ▶</button>
<input id="seek" type="range" min="0" max="1" step="any" value="0" aria-label="Videoposition"><output id="clock">0,00 s</output>
<label><input id="audio" type="checkbox">Ton</label>
<label><input id="extras" type="checkbox" checked>Zusatzdetektionen</label>
<label><input id="numbers" type="checkbox">Punktnummern</label>
<label><input id="crop" type="checkbox">Festen Zoom anwenden</label></div>
<p><label for="view">Darstellung: </label><select id="view"><option value="all">Alle Modelle vergleichen</option><option value="lite">Lite groß anzeigen</option><option value="full">Full groß anzeigen</option><option value="heavy">Heavy groß anzeigen</option></select></p>
<p class="legend"><span class="green">● Sicher: ab 0,65</span><span class="amber">● Eingeschränkt: 0,50–0,65</span><span class="red">● Unsicher: unter 0,50</span><span class="muted">Grau: zusätzliche Erkennung</span></p>
<div id="cards" class="grid"></div>
<table><thead><tr><th>Modell</th><th>Unsichere Bilder (33 Punkte)</th><th>Mind. 6/8 Arm-/Beinabschnitte</th><th>Fehlende Punkte</th><th>Laufzeit</th></tr></thead><tbody id="metrics"></tbody></table>
<p class="muted">Die Abdeckung betrifft ausschließlich die Referenzpose. Eine vollständige Trainingsbewertung erfordert zusätzlich sichere Kamerapunkte. Weniger Warnungen beweisen keine höhere tatsächliche Genauigkeit.</p>
<details><summary>Zoom, Auswahl und Grenzen</summary><ul><li>Die weiße Umrandung kennzeichnet die ausgewählte Figur. Bei mehrdeutiger Auswahl wird keine Figur als Referenz übernommen.</li><li>Graue Figuren sind zusätzliche Modellhypothesen. Ob sie Spiegelungen oder Fehlkennungen darstellen, muss visuell geprüft werden.</li><li>Türkis zeigt den festen Zoomrahmen. „Festen Zoom anwenden“ stellt dessen Ausschnitt mit gegebenenfalls schwarzen Balken dar.</li><li>Fehlende Punkte werden nicht erfunden oder interpoliert. Bei Stichproben bleibt die letzte Pose nur zur Vorschau bis zum nächsten analysierten Zeitpunkt sichtbar.</li><li>Diese lokale Vorschau lädt keine externen Inhalte und verändert die bestehende Trainingsanwendung nicht.</li></ul></details>
<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
'use strict';
__CONTROLS__
const data=JSON.parse(document.getElementById('payload').textContent),video=document.getElementById('source');
const $=id=>document.getElementById(id),links=[[0,1],[1,2],[2,3],[3,7],[0,4],[4,5],[5,6],[6,8],[9,10],[11,12],[11,13],[13,15],[15,17],[15,19],[15,21],[17,19],[12,14],[14,16],[16,18],[16,20],[16,22],[18,20],[11,23],[12,24],[23,24],[23,25],[25,27],[27,29],[29,31],[27,31],[24,26],[26,28],[28,30],[30,32],[28,32]];
function bytes(value){const s=atob(value),b=new Uint8Array(s.length);for(let i=0;i<s.length;i++)b[i]=s.charCodeAt(i);return new DataView(b.buffer)}
const models=data.models.map(m=>({...m,values:bytes(m.poses),timestamps:bytes(m.times)}));
const count=models[0].manifest.frameCount,time=i=>models[0].timestamps.getFloat64(i*8,true),fmt=n=>n.toLocaleString('de-DE',{maximumFractionDigits:2});
video.muted=true;
$('scope').textContent=data.summary.maxFps===0?'Vollständige Analyse aller Videobilder.':`Stichprobenvergleich: höchstens ${data.summary.maxFps} Analysebilder pro Sekunde. Prozentwerte beziehen sich auf diese Stichprobe.`;
if(Number.isFinite(data.summary.zoomMaxUncertainPercent))$('scope').textContent+=` Zoomtoleranz: ${data.summary.zoomMaxUncertainPercent} %; Zeitgrenze gilt für Rumpf-/Zuordnungslücken.`;
for(const m of models){
 const card=document.createElement('section');card.className='card';const h=document.createElement('h2');h.textContent=m.name.toUpperCase();const canvas=document.createElement('canvas');canvas.width=640;canvas.height=360;canvas.setAttribute('aria-label',`Skelettvorschau ${m.name}`);const status=document.createElement('p');status.className='status';card.append(h,canvas,status);$('cards').append(card);m.canvas=canvas;m.status=status;m.card=card;
 const row=document.createElement('tr'),stats=data.summary.models[m.name];for(const text of [m.name.toUpperCase(),fmt(stats.uncertainPercent)+' %',fmt(stats.usableBodyPercent)+' %',String(stats.missingLandmarks),fmt(stats.elapsedSeconds)+' s']){const cell=document.createElement('td');cell.textContent=text;row.append(cell)}$('metrics').append(row);
}
const indexAt=t=>findPoseIndex(count,time,t);
function color(c){return c>=.65?'#4ff0a4':c>=.5?'#ffd05e':'#ff6577'}
function draw(){
 if(video.readyState<2)return;const index=indexAt(video.currentTime);$('seek').value=video.currentTime;$('clock').textContent=fmt(video.currentTime)+' s · Pose '+fmt(time(index))+' s';
 for(const m of models){const canvas=m.canvas,z=m.manifest.zoom,W=m.manifest.video.width,H=m.manifest.video.height,zoom=$('crop').checked;
  if(m.card.hidden)continue;const wantedW=$('view').value==='all'?640:1280;if(canvas.width!==wantedW)canvas.width=wantedW;
  const wantedH=Math.max(180,Math.min(2048,zoom?Math.round(wantedW/z.targetAspectRatio):Math.round(wantedW*H/W)));if(canvas.height!==wantedH)canvas.height=wantedH;
  const ctx=canvas.getContext('2d'),sx=zoom?z.x*W:0,sy=zoom?z.y*H:0,sw=zoom?z.width*W:W,sh=zoom?z.height*H:H,scale=Math.min(canvas.width/sw,canvas.height/sh),ox=(canvas.width-sw*scale)/2,oy=(canvas.height-sh*scale)/2;
  ctx.fillStyle='#000';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(video,sx,sy,sw,sh,ox,oy,sw*scale,sh*scale);ctx.save();ctx.beginPath();ctx.rect(ox,oy,sw*scale,sh*scale);ctx.clip();
  const project=p=>[(p[0]*W-sx)*scale+ox,(p[1]*H-sy)*scale+oy];
  function skeleton(points,ghost=false){
   ctx.lineWidth=ghost?1.3:2.5;ctx.globalAlpha=ghost ? .7 : 1;
   for(const [a,b] of links){const p=points[a],q=points[b];if(!p||!q||!Number.isFinite(p[0])||!Number.isFinite(q[0]))continue;const A=project(p),B=project(q);ctx.strokeStyle=ghost?'#c3cad6':color(Math.min(p[2],p[3],q[2],q[3]));ctx.beginPath();ctx.moveTo(...A);ctx.lineTo(...B);ctx.stroke()}
   if(!ghost)for(let j=0;j<points.length;j++){const p=points[j];if(!p||!Number.isFinite(p[0]))continue;const P=project(p);ctx.fillStyle=color(Math.min(p[2],p[3]));ctx.beginPath();ctx.arc(...P,3.5,0,Math.PI*2);ctx.fill();if($('numbers').checked){ctx.font='11px system-ui';ctx.fillStyle='#fff';ctx.fillText(String(j),P[0]+5,P[1]-4)}}
   ctx.globalAlpha=1;
  }
  const diagnostic=m.diagnostics[index]||{},points=[];let missing=0,low=0;
  for(let j=0;j<33;j++){const off=(index*231+j*7)*4,p=[m.values.getFloat32(off,true),m.values.getFloat32(off+4,true),m.values.getFloat32(off+20,true),m.values.getFloat32(off+24,true)];if(!Number.isFinite(p[0])){missing++;points.push(null)}else{if(Math.min(p[2],p[3])<.5)low++;points.push(p)}}
  if($('extras').checked)for(const ghost of diagnostic.extras||[])skeleton(ghost,true);skeleton(points);
  const known=points.filter(Boolean);if(diagnostic.selectedIndex!==null&&known.length){const xs=known.map(p=>p[0]),ys=known.map(p=>p[1]),a=project([Math.min(...xs),Math.min(...ys)]),b=project([Math.max(...xs),Math.max(...ys)]);ctx.strokeStyle='#fff';ctx.lineWidth=1;ctx.strokeRect(a[0]-5,a[1]-5,b[0]-a[0]+10,b[1]-a[1]+10)}
  if(!zoom){const a=project([z.x,z.y]);ctx.strokeStyle='#4cddff';ctx.lineWidth=2;ctx.strokeRect(a[0]+1,a[1]+1,z.width*W*scale-2,z.height*H*scale-2)}ctx.restore();
  const labels={initial:'Vordergrund gewählt',tracked:'Figur verfolgt',reacquired:'Nach Lücke neu gewählt – prüfen',ambiguous:'Auswahl mehrdeutig',jump_rejected:'Positionssprung abgewiesen',missing:'Keine sichere Figur',single:'Eine Figur erkannt'};
  m.status.textContent=`Fehlend: ${missing}/33 · Unter 0,50: ${low}/33\n${labels[diagnostic.status]||'Gespeicherte Pose'} · Erkennungen: ${diagnostic.candidates??'?'} · Auswahl: ${diagnostic.selectedIndex===null?'keine':(diagnostic.selectedIndex??0)+1}`;
 }
}
$('play').onclick=async()=>{try{if(video.paused)await video.play();else video.pause()}catch(e){$('error').textContent='Wiedergabe nicht möglich: '+e.message}};
video.onplay=()=>$('play').textContent='Pause';video.onpause=()=>$('play').textContent='Abspielen';
function step(delta){video.pause();const i=Math.max(0,Math.min(count-1,indexAt(video.currentTime)+delta));video.currentTime=time(i)}
$('back').onclick=()=>step(-1);$('next').onclick=()=>step(1);$('seek').oninput=()=>{video.currentTime=Number($('seek').value)};
$('audio').onchange=()=>video.muted=!$('audio').checked;for(const id of ['extras','numbers','crop'])$(id).onchange=draw;
$('view').onchange=()=>{const selected=$('view').value;$('cards').classList.toggle('single',selected!=='all');for(const m of models)m.card.hidden=selected!=='all'&&m.name!==selected;draw()};
bindMediaMetadata(video,$('seek'),draw);
video.onseeked=draw;video.onloadeddata=draw;video.onerror=()=>$('error').textContent='reference.mp4 nicht lesbar. Alle Vergleichsdateien im selben Ordner belassen und die HTML-Datei in Chrome oder Edge öffnen.';
let lastPaint=-1;function loop(){if(!video.paused&&video.currentTime!==lastPaint){lastPaint=video.currentTime;draw()}requestAnimationFrame(loop)}requestAnimationFrame(loop);
if(data.summary.previewView&&models.some(m=>m.name===data.summary.previewView)){$('view').value=data.summary.previewView;$('view').onchange()}
if(data.summary.previewApplyZoom){$('crop').checked=true;draw()}
window.previewReady=true;
</script></body></html>'''
