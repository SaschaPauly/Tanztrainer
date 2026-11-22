"""Recompute fixed zoom from validated stored poses; no model inference."""
import argparse
import json
import math
from pathlib import Path
import shutil
import struct
import tempfile
import zipfile

from analyzer.analysis import Quality, DEFAULT_ZOOM_UNCERTAIN_PERCENT
from analyzer.export import export
from analyzer.validate import validate
from analyzer.video import frames, inspect_video


def complete_frame_coverage(video, timestamps):
    """Prove that every decoded frame has a corresponding pose timestamp."""
    iterator = frames(video)
    try:
        with timestamps.open('rb') as source:
            for _, timestamp in iterator:
                raw = source.read(8)
                if len(raw) != 8 or timestamp is None or not math.isfinite(timestamp):
                    return False
                stored, = struct.unpack('<d', raw)
                if abs(timestamp-stored) > 1e-6:
                    return False
            return not source.read(1)
    finally:
        iterator.close()


def recompute_zoom(package, output, *, zoom_max_uncertain_percent=DEFAULT_ZOOM_UNCERTAIN_PERCENT, overwrite=False):
    package, output = Path(package).resolve(), Path(output).resolve()
    if output == package or output.suffix.lower() != '.choreo':
        raise ValueError('Ausgabe muss eine separate .choreo-Datei sein.')
    if output.exists() and not overwrite:
        raise ValueError('Ausgabe existiert bereits.')
    if not output.parent.is_dir():
        raise ValueError('Ausgabeordner existiert nicht.')
    quality = Quality(zoom_max_uncertain_percent)
    manifest = validate(package)
    with tempfile.TemporaryDirectory(prefix='.rezoom-', dir=output.parent) as directory:
        work = Path(directory)
        payload = {name:work/name.replace('/','_') for name in manifest['files']}
        # Only validated, allowlisted payloads are copied to generated flat paths.
        with zipfile.ZipFile(package) as archive:
            old_quality = json.loads(archive.read('reference/quality.json'))
            for name,path in payload.items():
                with archive.open(name) as source, path.open('wb') as target:
                    shutil.copyfileobj(source,target,65536)
        for warning in old_quality['warnings']:
            if not warning.startswith('Zoom'):
                quality.warn(warning)
        media = inspect_video(payload['reference/video.mp4'])
        if ((media['width'],media['height']) != (manifest['video']['width'],manifest['video']['height'])
                or media['codec']!='h264' or media['pixel_format']!='yuv420p'):
            raise ValueError('Paketvideo entspricht nicht den angegebenen Abmessungen oder H.264/yuv420p.')
        covered = complete_frame_coverage(payload['reference/video.mp4'],payload['reference/timestamps.bin'])
        sampling_declared = any(w.startswith('Zeitliche Abtastung') for w in old_quality['warnings'])
        if sampling_declared or not covered:
            quality.safe = False
            quality.warn('Zeitliche Abtastung oder abweichende Videozeitpunkte erkannt; Zoom bleibt Ganzbild.')
        with payload['reference/poses.bin'].open('rb') as poses, payload['reference/timestamps.bin'].open('rb') as times:
            for _ in range(manifest['frameCount']):
                timestamp, = struct.unpack('<d',times.read(8))
                # Unassigned/ambiguous original detections are already fully
                # missing in v1 and therefore fail the torso test conservatively.
                quality.observe_pose(timestamp,poses.read(924))
        zoom = quality.zoom(manifest['video']['width'],manifest['video']['height'],manifest['zoom']['targetAspectRatio'])
        report = quality.report()
        report['warnings'] = list(dict.fromkeys(report['warnings']))
        result = export(output,payload,title=manifest['title'],duration=manifest['durationSeconds'],
                        count=manifest['frameCount'],model=manifest['model'],
                        width=manifest['video']['width'],height=manifest['video']['height'],
                        zoom=zoom,audio=manifest['audio']['source']!='none',
                        audio_offset=manifest['audio']['offsetSeconds'],quality=report,overwrite=overwrite)
    return result,report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--zoom-max-uncertain-percent',type=float,default=DEFAULT_ZOOM_UNCERTAIN_PERCENT)
    parser.add_argument('--overwrite',action='store_true')
    args=parser.parse_args(argv)
    try:
        manifest,report=recompute_zoom(args.package,args.output,
                                      zoom_max_uncertain_percent=args.zoom_max_uncertain_percent,
                                      overwrite=args.overwrite)
    except KeyboardInterrupt:
        parser.exit(130,'Zoomneuberechnung abgebrochen.\n')
    except Exception as exc:
        parser.exit(1,f'Zoomneuberechnung fehlgeschlagen: {exc}\n')
    print(f'Exportiert: {args.output}; fester Ausschnitt {manifest["zoom"]}')
    for warning in report['warnings']:
        print(f'Warnung: {warning}')


if __name__=='__main__':
    main()
