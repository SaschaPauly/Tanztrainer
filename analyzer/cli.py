"""Windows-compatible local Showtanz video analyzer (showtanz-choreo 1.0.0)."""
import argparse
import math
from pathlib import Path
import struct
import sys
import tempfile

from analyzer.analysis import Quality, Timeline
from analyzer.export import export
from analyzer.pose import PoseEngine, pack_pose
from analyzer.video import frames, normalize
from analyzer.validate import SPEC


def analyze(source, output, model, *, title=None, backend='auto', max_fps=0,
            max_side=1280, aspect=9/16, overwrite=False, ffmpeg=None,
            engine_factory=PoseEngine):
    source, output, model = Path(source).resolve(), Path(output).resolve(), Path(model).resolve()
    if not source.is_file() or not model.is_file():
        raise ValueError('Video oder lokale MediaPipe-.task-Modelldatei fehlt.')
    if backend not in ('auto', 'cpu', 'gpu'):
        raise ValueError('Backend muss auto, cpu oder gpu sein.')
    if output in (source, model) or output.suffix.lower() != '.choreo':
        raise ValueError('Ausgabe muss eine separate .choreo-Datei sein.')
    if output.exists() and not overwrite:
        raise ValueError('Ausgabe existiert bereits. Anderen Namen oder --overwrite verwenden.')
    if not output.parent.is_dir():
        raise ValueError('Ausgabeordner existiert nicht.')
    title = source.stem if title is None else title
    if not title.strip() or len(title) > 200:
        raise ValueError('Titel muss 1–200 Zeichen enthalten.')
    if not math.isfinite(max_fps) or not 0 <= max_fps <= 240:
        raise ValueError('--max-fps muss 0 (alle Frames) oder >0 bis 240 sein.')
    if not 64 <= max_side <= 4096 or not math.isfinite(aspect) or not 0 < aspect <= 100:
        raise ValueError('Ungültige Analyseauflösung oder ungültiges Zielseitenverhältnis.')
    quality = Quality()
    if max_fps:
        quality.warn(f'Zeitliche Abtastung auf höchstens {max_fps:g} fps; kurze Bewegungen können fehlen. Zoom bleibt sicherheitshalber Ganzbild.')
        quality.safe = False
    quality.warn('3D ist eine Modellschätzung relativ zur Hüfte, keine vermessene Bühnenposition.')
    with tempfile.TemporaryDirectory(prefix='.analysis-', dir=output.parent) as directory:
        work = Path(directory)
        payload = {name: work/name.replace('/', '_') for name in (
            'reference/video.mp4', 'reference/poses.bin', 'reference/timestamps.bin',
            'reference/zoom.json', 'reference/quality.json', 'assets/preview.jpg')}
        print('Video lokal importieren und H.264/AAC normalisieren …', file=sys.stderr)
        info = normalize(source, payload['reference/video.mp4'], ffmpeg)
        video_bytes = payload['reference/video.mp4'].stat().st_size
        timeline, count, last_end = Timeline(max_fps), 0, 0.
        engine = engine_factory(model, backend, quality.warn)
        iterator = frames(payload['reference/video.mp4'])
        try:
            with payload['reference/poses.bin'].open('wb') as poses, payload['reference/timestamps.bin'].open('wb') as times:
                for frame, time in iterator:
                    if time is not None:
                        duration = getattr(frame, 'duration', 0) or 0
                        last_end = max(last_end, time + float(duration*frame.time_base))
                    if not timeline.accept(time):
                        continue
                    if count >= 1000000 or time > 14400:
                        raise ValueError('Analyse überschreitet das Frame-/Dauerlimit.')
                    if video_bytes + (count+1)*932 + 2*1024*1024 > SPEC['limits']['archiveBytes']:
                        raise ValueError('Video und Posen überschreiten das 1-GiB-Paketlimit.')
                    if (frame.width, frame.height) != (info['width'], info['height']):
                        raise ValueError('Wechselnde Videoauflösung wird nicht unterstützt.')
                    image = frame.to_image()
                    if count == 0:
                        preview = image.copy()
                        preview.thumbnail((640, 640))
                        preview.save(payload['assets/preview.jpg'], format='JPEG', quality=85)
                    image.thumbnail((max_side, max_side))
                    import numpy as np
                    result = engine.detect(np.asarray(image.convert('RGB')).copy(), timeline.model_ms)
                    data, missing, points = pack_pose(result)
                    poses.write(data)
                    times.write(struct.pack('<d', time))
                    quality.observe(time, missing, points, len(result.pose_landmarks))
                    count += 1
                    if count % 100 == 0:
                        print(f'{count} Analyseframes; Videoposition {time:.2f} s; {engine.backend}', file=sys.stderr)
        finally:
            iterator.close()
            engine.close()
        if not count:
            raise ValueError('Keine dekodierbaren Videoframes.')
        duration = max(info['duration'], last_end)
        zoom = quality.zoom(info['width'], info['height'], aspect)
        manifest = export(output, payload, title=title, duration=duration, count=count,
                          model=engine.identity, width=info['width'], height=info['height'],
                          zoom=zoom, audio=info['audio'], quality=quality.report(), overwrite=overwrite)
        return manifest, quality.report()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--model', type=Path, required=True, help='Lokales Pose-Landmarker-.task-Modell; kein automatischer Download')
    parser.add_argument('--title')
    parser.add_argument('--backend', choices=('auto', 'cpu', 'gpu'), default='auto', help='GPU wird geprüft; bei Fehlern CPU-Fallback')
    parser.add_argument('--max-fps', type=float, default=0, help='0: jeder Frame (Standard); sonst zeitliche Obergrenze')
    parser.add_argument('--max-side', type=int, default=1280, help='Maximale Bildkante nur für Inferenz')
    parser.add_argument('--aspect', type=float, default=9/16, help='Bevorzugtes Player-Breite/Höhe-Verhältnis')
    parser.add_argument('--ffmpeg', type=Path, help='Eigene FFmpeg-Programmdatei statt gebündelter Version')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args(argv)
    try:
        manifest, quality = analyze(args.video, args.output, args.model, title=args.title,
                                    backend=args.backend, max_fps=args.max_fps, max_side=args.max_side,
                                    aspect=args.aspect, overwrite=args.overwrite, ffmpeg=args.ffmpeg)
    except KeyboardInterrupt:
        parser.exit(130, 'Analyse abgebrochen; kein unvollständiger Export.\n')
    except Exception as exc:
        parser.exit(1, f'Analyse fehlgeschlagen: {exc}\n')
    print(f"Exportiert: {args.output} ({manifest['frameCount']} Frames; {quality['status']}; {quality['missingLandmarks']} fehlende Gelenke)")
    for warning in quality['warnings']:
        print(f'Warnung: {warning}')
    return 0


if __name__ == '__main__':
    main()
