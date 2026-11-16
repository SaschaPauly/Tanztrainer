"""Generate original, synthetic CC0 media and a reproducible ZIP layout (FFmpeg required)."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import zipfile

from analyzer.validate import SCHEMA

ROOT = Path(__file__).resolve().parents[1]


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def create(output):
    with tempfile.TemporaryDirectory() as folder:
        video, preview = Path(folder)/'video.mp4', Path(folder)/'preview.jpg'
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'lavfi', '-i',
                        'color=c=blue:s=160x120:r=4', '-t', '1', '-an', '-c:v', 'libx264',
                        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(video)], check=True)
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(video),
                        '-frames:v', '1', '-threads', '1', str(preview)], check=True)
        # Anatomical left is image right for a front-facing synthetic person.
        xy = [(.5,.12),(.52,.11),(.54,.11),(.56,.11),(.48,.11),(.46,.11),(.44,.11),
              (.59,.13),(.41,.13),(.53,.16),(.47,.16),(.65,.25),(.35,.25),
              (.72,.4),(.28,.4),(.75,.55),(.25,.55),(.78,.57),(.22,.57),
              (.76,.59),(.24,.59),(.73,.57),(.27,.57),(.59,.53),(.41,.53),
              (.6,.7),(.4,.7),(.61,.87),(.39,.87),(.6,.89),(.4,.89),(.65,.92),(.35,.92)]
        poses = b''.join(struct.pack('<7f', x, y, (x-.5)*2, (y-.53)*2, 0, 1, 1)
                         for _ in range(4) for x,y in xy)
        zoom = {'mode':'fixed','x':.1,'y':0,'width':.8,'height':1,'targetAspectRatio':4/3}
        payload = {'reference/video.mp4':video.read_bytes(), 'assets/preview.jpg':preview.read_bytes(),
                   'reference/poses.bin':poses,'reference/timestamps.bin':struct.pack('<4d',0,.25,.5,.75),
                   'reference/zoom.json':encode(zoom),
                   'reference/quality.json':encode({'status':'complete','missingLandmarks':0,'warnings':['Synthetische Testdaten; keine Modellerkennung.']})}
        manifest = {'format':'showtanz-choreo','version':'1.0.0','title':'Synthetic standing skeleton (CC0)',
                    'durationSeconds':1,'frameCount':4,'model':{'name':'synthetic-fixture','version':'1.0.0'},
                    'video':{'width':160,'height':120},'coordinateSystem':SCHEMA['properties']['coordinateSystem']['const'],
                    'layout':SCHEMA['properties']['layout']['const'],'zoom':zoom,'audio':{'source':'none','offsetSeconds':0},
                    'files':{p:{'size':len(b),'sha256':hashlib.sha256(b).hexdigest()} for p,b in payload.items()}}
        payload['manifest.json'] = encode(manifest)
        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_STORED) as archive:
            for name,data in sorted(payload.items()):
                entry = zipfile.ZipInfo(name, (2026,1,1,0,0,0))
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry,data)


if __name__ == '__main__':
    create(ROOT/'tests/fixtures/synthetic.choreo')
