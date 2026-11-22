"""Compare Lite/Full/Heavy on identical frames and create an offline preview."""
import argparse
import csv
import json
import math
from pathlib import Path
import shutil
import struct
import tempfile
import time
import zipfile

from analyzer.cli import analyze
from analyzer.analysis import DEFAULT_ZOOM_UNCERTAIN_PERCENT
from analyzer.models import MODEL_NAMES, download_models, model_path
from analyzer.pose import PoseEngine
from analyzer.preview import write_preview
from analyzer.validate import validate

BODY_SEGMENTS = ((11,13),(13,15),(12,14),(14,16),(23,25),(25,27),(24,26),(26,28))


def diagnostic_frame(timestamp, result, decision):
    extras = []
    for index, pose in enumerate(result.pose_landmarks):
        if index == decision.index:
            continue
        points = []
        for point in pose:
            values = (point.x, point.y, getattr(point,'visibility',None), getattr(point,'presence',None))
            points.append(list(values) if all(isinstance(v,(int,float)) and math.isfinite(v) for v in values) else None)
        extras.append(points)
    return dict(timestamp=timestamp, selectedIndex=decision.index, candidates=decision.candidates,
                status=decision.status, extras=extras)


def pose_metrics(package, diagnostics):
    manifest = validate(package)
    if len(diagnostics) != manifest['frameCount']:
        raise ValueError('Diagnosezeitpunkte und Poseanzahl stimmen nicht überein.')
    uncertain = missing = missing_frames = body_usable = body_complete = 0
    frame_rows = []
    with zipfile.ZipFile(package) as archive, archive.open('reference/poses.bin') as poses, archive.open('reference/timestamps.bin') as times:
        for index in range(manifest['frameCount']):
            timestamp, = struct.unpack('<d', times.read(8))
            if timestamp != diagnostics[index]['timestamp']:
                raise ValueError('Diagnosezeitstempel stimmt nicht mit Pose überein.')
            points = list(struct.iter_unpack('<7f', poses.read(924)))
            absent = sum(math.isnan(p[0]) for p in points)
            low = sum(not math.isnan(p[0]) and min(p[5:])<.5 for p in points)
            reliable = lambda j: not math.isnan(points[j][0]) and min(points[j][5:])>=.65
            segments = sum(reliable(a) and reliable(b) for a,b in BODY_SEGMENTS)
            uncertain += int(absent>0 or low>0 or diagnostics[index]['selectedIndex'] is None)
            missing += absent
            missing_frames += int(absent>0)
            body_usable += int(segments>=6)
            body_complete += int(segments==8)
            frame_rows.append((index,timestamp,absent,low,segments))
        quality = json.loads(archive.read('reference/quality.json'))
    count = manifest['frameCount']
    return dict(frames=count, uncertainFrames=uncertain, uncertainPercent=uncertain/count*100,
                missingLandmarks=missing, framesWithMissing=missing_frames,
                usableBodyFrames=body_usable, usableBodyPercent=body_usable/count*100,
                completeBodyFrames=body_complete, completeBodyPercent=body_complete/count*100,
                extraDetectionFrames=sum(d['candidates']>1 for d in diagnostics),
                rejectedSelectionFrames=sum(d['selectedIndex'] is None for d in diagnostics),
                model=manifest['model'], zoom=manifest['zoom'], quality=quality), frame_rows


def compare_models(source, output_directory, models_directory, *, single_person=False,
                   backend='cpu', max_fps=0, max_side=1280,
                   zoom_max_uncertain_percent=DEFAULT_ZOOM_UNCERTAIN_PERCENT, engine_factory=PoseEngine):
    source, output = Path(source).resolve(), Path(output_directory).resolve()
    if output.exists():
        raise ValueError('Vergleichsordner existiert bereits. Einen neuen Namen wählen.')
    if not output.parent.is_dir():
        raise ValueError('Übergeordneter Ausgabeordner existiert nicht.')
    paths = {name:model_path(models_directory,name).resolve() for name in MODEL_NAMES}
    for path in paths.values():
        if not path.is_file():
            raise ValueError(f'Modell fehlt: {path}; Modelle vorher ausdrücklich herunterladen.')
    summary = dict(format='showtanz-model-comparison',version='1.0.0',maxFps=max_fps,
                   maxSide=max_side,singlePerson=single_person,requestedBackend=backend,
                   zoomMaxUncertainPercent=zoom_max_uncertain_percent,
                   limitations='Konfidenz und Abdeckung sind keine gemessene Genauigkeit. '
                   'Personenauswahl ist heuristisch; Zusatzdetektionen können Spiegelungen oder Fehlkennungen sein.', models={})
    with tempfile.TemporaryDirectory(prefix='.comparison-', dir=output.parent) as directory:
        work = Path(directory)
        variants, frame_tables = [], {}
        for name, path in paths.items():
            print(f'Analyse mit {name.upper()} …', flush=True)
            diagnostics, created = [], []
            def observe(timestamp, result, decision):
                if len(diagnostics)>=20000:
                    raise ValueError('Vergleich auf 20000 Zeitpunkte begrenzt; --max-fps reduzieren.')
                diagnostics.append(diagnostic_frame(timestamp,result,decision))
            def factory(*args):
                engine = engine_factory(*args)
                created.append(engine)
                return engine
            started = time.perf_counter()
            package = work/f'{name}.choreo'
            analyze(source, package, path, backend=backend, max_fps=max_fps,
                    max_side=max_side, single_person=single_person, observer=observe,
                    zoom_max_uncertain_percent=zoom_max_uncertain_percent,engine_factory=factory)
            elapsed = time.perf_counter()-started
            metrics, frame_tables[name] = pose_metrics(package,diagnostics)
            metrics.update(elapsedSeconds=elapsed,backendAtEnd=created[0].backend)
            summary['models'][name] = metrics
            variants.append((name,package,diagnostics))
            print(f'{name.upper()}: {metrics["uncertainPercent"]:.2f} % unsichere Bilder; '
                  f'{metrics["usableBodyPercent"]:.2f} % mit mindestens 6/8 sicheren Körperabschnitten.',flush=True)
        # Preview validates equal time arrays before publishing any comparison files.
        write_preview(work/'vergleich.html',variants,summary)
        with zipfile.ZipFile(variants[0][1]) as archive, archive.open('reference/video.mp4') as video, (work/'reference.mp4').open('wb') as target:
            shutil.copyfileobj(video,target,65536)
        (work/'vergleich.json').write_text(json.dumps(summary,ensure_ascii=False,allow_nan=False,indent=2)+'\n',encoding='utf-8')
        with (work/'bildervergleich.csv').open('w',encoding='utf-8-sig',newline='') as target:
            writer = csv.writer(target,delimiter=';')
            writer.writerow(['model','frameIndex','timestampSeconds','missingLandmarks','lowConfidenceLandmarks',
                             'reliableBodySegments','rawDetections','selectedIndex','selectionStatus'])
            from analyzer.export_poses import csv_number
            for name,_,diagnostics in variants:
                for frame,diagnostic in zip(frame_tables[name],diagnostics):
                    writer.writerow([csv_number(v) for v in (name,*frame,diagnostic['candidates'],diagnostic['selectedIndex'],diagnostic['status'])])
        output.mkdir()
        moved=[]
        try:
            for path in work.iterdir():
                destination = output/path.name
                path.rename(destination)
                moved.append(destination)
        except BaseException:
            for path in moved:
                path.unlink()
            output.rmdir()
            raise
    return summary


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video',type=Path)
    parser.add_argument('output_directory',type=Path)
    parser.add_argument('--models-dir',type=Path,default=Path('models'))
    parser.add_argument('--single-person',action='store_true',help='Bestätigte Einpersonenaufnahme mit möglicher Spiegelung')
    parser.add_argument('--backend',choices=('cpu','auto','gpu'),default='cpu')
    parser.add_argument('--max-fps',type=float,default=0,help='0: alle Frames, sonst identische zeitliche Abtastung je Modell')
    parser.add_argument('--max-side',type=int,default=1280)
    parser.add_argument('--zoom-max-uncertain-percent',type=float,default=DEFAULT_ZOOM_UNCERTAIN_PERCENT)
    parser.add_argument('--download-models',action='store_true',help='Offizielle Modelle ausdrücklich von Google laden')
    args=parser.parse_args(argv)
    try:
        if args.download_models:
            download_models(args.models_dir)
        compare_models(args.video,args.output_directory,args.models_dir,single_person=args.single_person,
                       backend=args.backend,max_fps=args.max_fps,max_side=args.max_side,
                       zoom_max_uncertain_percent=args.zoom_max_uncertain_percent)
    except KeyboardInterrupt:
        parser.exit(130,'Modellvergleich abgebrochen.\n')
    except Exception as exc:
        parser.exit(1,f'Modellvergleich fehlgeschlagen: {exc}\n')
    print(f'Fertig: {args.output_directory/"vergleich.html"}')


if __name__=='__main__':
    main()
