"""Windows-compatible local Showtanz video analyzer (showtanz-choreo 1.0.0)."""
import argparse
from collections import Counter
import math
from pathlib import Path
import struct
import sys
import tempfile

from analyzer.analysis import Quality, Timeline, DEFAULT_ZOOM_UNCERTAIN_PERCENT
from analyzer.export import export
from analyzer.pose import PoseEngine, pack_pose
from analyzer.video import frames, normalize, copy_prepared
from analyzer.validate import SPEC
from analyzer.selection import PersonSelector, Selection
from analyzer.runtime import check_cancel, notify


def analyze(source, output, model, *, title=None, backend='auto', max_fps=0,
            max_side=1280, aspect=9/16, overwrite=False, ffmpeg=None,
            zoom_max_uncertain_percent=DEFAULT_ZOOM_UNCERTAIN_PERCENT, single_person=False,
            target_point=None, observer=None, engine_factory=PoseEngine,
            cancel=None, progress=None, prepared_video=None):
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
    quality = Quality(zoom_max_uncertain_percent)
    if max_fps:
        quality.warn(f'Zeitliche Abtastung auf höchstens {max_fps:g} fps; kurze Bewegungen können fehlen. Zoom bleibt sicherheitshalber Ganzbild.')
        quality.safe = False
    quality.warn('3D ist eine Modellschätzung relativ zur Hüfte, keine vermessene Bühnenposition.')
    selector = PersonSelector(target_point=target_point) if single_person or target_point is not None else None
    selection_counts = Counter()
    extra_detection_frames = 0
    if single_person:
        quality.warn('Bestätigte Einpersonenaufnahme: heuristische Vordergrund-/Zeitverfolgung aktiv. '
                     'Zusatzdetektionen können Spiegelungen oder Fehlkennungen sein; Auswahl visuell prüfen.')
    if target_point is not None:
        quality.warn('Manuelle Startauswahl aktiv: Figur anhand des markierten Oberkörpers und zeitlicher Kontinuität verfolgen; Auswahl visuell prüfen.')
    with tempfile.TemporaryDirectory(prefix='.analysis-', dir=output.parent) as directory:
        work = Path(directory)
        payload = {name: work/name.replace('/', '_') for name in (
            'reference/video.mp4', 'reference/poses.bin', 'reference/timestamps.bin',
            'reference/zoom.json', 'reference/quality.json', 'assets/preview.jpg')}
        print('Video lokal importieren und H.264/AAC normalisieren …', file=sys.stderr)
        check_cancel(cancel)
        if prepared_video is None:
            info = normalize(source, payload['reference/video.mp4'], ffmpeg,cancel=cancel,progress=progress)
        else:
            info = copy_prepared(Path(prepared_video),payload['reference/video.mp4'],cancel=cancel,progress=progress)
        video_bytes = payload['reference/video.mp4'].stat().st_size
        timeline, count, last_end = Timeline(max_fps), 0, 0.
        engine = engine_factory(model, backend, quality.warn)
        iterator = frames(payload['reference/video.mp4'])
        try:
            with payload['reference/poses.bin'].open('wb') as poses, payload['reference/timestamps.bin'].open('wb') as times:
                for frame, time in iterator:
                    check_cancel(cancel)
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
                    raw_count = len(result.pose_landmarks)
                    decision = selector.select(result, time) if selector else Selection(
                        result, 0 if raw_count == 1 else None, raw_count,
                        'single' if raw_count == 1 else 'ambiguous' if raw_count > 1 else 'missing')
                    selection_counts[decision.status] += 1
                    extra_detection_frames += int(raw_count > 1)
                    data, missing, points = pack_pose(decision.result)
                    if observer is not None:
                        observer(time, result, decision)
                    poses.write(data)
                    times.write(struct.pack('<d', time))
                    quality.observe_pose(time, data, 1 if decision.index is not None else raw_count)
                    count += 1
                    if count==1 or count%10==0:
                        notify(progress,'analysis',min(1.,time/info['duration']),
                               f'{count} Bilder analysiert · {time:.1f} von {info["duration"]:.1f} Sekunden · {engine.backend}')
                    if count % 100 == 0:
                        print(f'{count} Analyseframes; Videoposition {time:.2f} s; {engine.backend}', file=sys.stderr)
        finally:
            iterator.close()
            engine.close()
        if not count:
            raise ValueError('Keine dekodierbaren Videoframes.')
        duration = max(info['duration'], last_end)
        check_cancel(cancel)
        notify(progress,'analysis',1.,'Videoanalyse abgeschlossen.')
        if selector is not None:
            quality.warn(f'Personenauswahl: {extra_detection_frames} Bilder mit Zusatzdetektionen; '
                         f'{selection_counts["ambiguous"]} mehrdeutig, '
                         f'{selection_counts["jump_rejected"]} Positionssprünge abgewiesen, '
                         f'{selection_counts["reacquired"]} Wiederaufnahmen nach Erkennungslücke.')
        zoom = quality.zoom(info['width'], info['height'], aspect)
        manifest = export(output, payload, title=title, duration=duration, count=count,
                          model=engine.identity, width=info['width'], height=info['height'],
                          zoom=zoom, audio=info['audio'], quality=quality.report(), overwrite=overwrite,
                          cancel=cancel,progress=progress)
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
    parser.add_argument('--zoom-max-uncertain-percent', type=float, default=DEFAULT_ZOOM_UNCERTAIN_PERCENT,
                        help='Maximaler Anteil unsicherer Analysebilder für festen Zoom (Standard: 30 Prozent)')
    parser.add_argument('--ffmpeg', type=Path, help='Eigene FFmpeg-Programmdatei statt gebündelter Version')
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--single-person', action='store_true',
                        help='Bestätigte Einpersonenaufnahme: Vordergrundfigur zeitlich verfolgen; Zusatzdetektionen prüfen')
    def target_value(text):
        try:
            values=tuple(float(v) for v in text.split(','))
            PersonSelector(target_point=values)
            return values
        except (ValueError,TypeError):
            raise argparse.ArgumentTypeError('Startmarkierung als X,Y mit zwei Werten zwischen 0 und 1 angeben.')
    parser.add_argument('--target-point',type=target_value,help='Oberkörper am Videoanfang markieren, normalisierte Koordinaten X,Y')
    args = parser.parse_args(argv)
    try:
        manifest, quality = analyze(args.video, args.output, args.model, title=args.title,
                                    backend=args.backend, max_fps=args.max_fps, max_side=args.max_side,
                                    aspect=args.aspect, overwrite=args.overwrite, ffmpeg=args.ffmpeg,
                                    zoom_max_uncertain_percent=args.zoom_max_uncertain_percent,
                                    single_person=args.single_person,target_point=args.target_point)
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
