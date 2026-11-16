"""Bounded, extraction-free showtanz-choreo 1.0.0 validation."""
import argparse
import zlib
import hashlib
import json
import math
from pathlib import Path
import stat
import struct
import zipfile

from jsonschema import Draft202012Validator

SHARED = Path(__file__).resolve().parents[1] / 'shared'
SPEC = json.loads((SHARED / 'validation-spec.json').read_text())
SCHEMA = json.loads((SHARED / 'choreography.schema.json').read_text())


class ValidationError(ValueError):
    """Invalid or unsafe choreography package."""


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def parse_json(data, name):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f'{name}: doppelter JSON-Schlüssel {key}')
            result[key] = value
        return result
    def finite_float(raw):
        value = float(raw)
        require(math.isfinite(value), f'{name}: JSON-Zahl muss endlich sein')
        return value
    try:
        return json.loads(data.decode('utf-8'), object_pairs_hook=unique, parse_float=finite_float,
                          parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValidationError(f'{name}: ungültiges UTF-8/JSON ({exc})') from exc


def validate(path, *, limits=None):
    """Return validated manifest. Limits may only be tightened by callers."""
    lim = dict(SPEC['limits'])
    if limits:
        for key, value in limits.items():
            require(key in lim and 0 < value <= lim[key], 'Limits dürfen nur verkleinert werden')
            lim[key] = value
    try:
        with open(path, 'rb') as source:
            source.seek(0, 2)
            require(source.tell() <= lim['archiveBytes'], 'ZIP überschreitet das Archiv-Größenlimit')
            length = source.tell()
            source.seek(max(0, length - 65557))
            tail = source.read(65557)
            marker = tail.rfind(b'PK\x05\x06')
            require(marker >= 0 and len(tail) >= marker + 22, 'ZIP: Endverzeichnis fehlt')
            _, disk, cd_disk, disk_count, count, cd_size, cd_offset, comment = struct.unpack_from('<4s4H2IH', tail, marker)
            require(marker + 22 + comment == len(tail), 'ZIP: ungültiges Ende')
            require(disk == cd_disk == 0 and disk_count == count and count <= lim['entries'], 'ZIP: Mehrteilarchive, ZIP64 oder zu viele Einträge')
            require(cd_size <= 65536 and cd_offset + cd_size == length - len(tail) + marker, 'ZIP: ungültiges oder zu großes Zentralverzeichnis; ZIP64 nicht erlaubt')
            source.seek(0)
            with zipfile.ZipFile(source) as archive:
                entries = archive.infolist()
                require(len(entries) <= lim['entries'], 'ZIP enthält zu viele Einträge')
                names = [entry.filename for entry in entries]
                require(len(names) == len(set(names)), 'ZIP enthält doppelte Pfade')
                require(set(names) == set(SPEC['files']), 'ZIP: fehlende Dateien oder unerlaubte Pfade')
                total = 0
                for entry in entries:
                    require(entry.orig_filename == entry.filename, 'ZIP-Pfad enthält NUL')
                    mode = entry.external_attr >> 16
                    require(stat.S_IFMT(mode) in (0, stat.S_IFREG), f'{entry.filename}: kein regulärer Dateieintrag')
                    require(not entry.flag_bits & 1, 'Verschlüsselte ZIP-Dateien sind nicht erlaubt')
                    require(entry.compress_type in SPEC['compressionMethods'], 'ZIP-Kompressionsverfahren nicht unterstützt')
                    require(0 < entry.file_size <= lim['entryBytes'], f'{entry.filename}: Dateigrößenlimit überschritten')
                    require(entry.file_size <= max(1, entry.compress_size) * lim['compressionRatio'], f'{entry.filename}: übermäßige Kompression')
                    if entry.filename.endswith('.json'):
                        require(entry.file_size <= lim['jsonBytes'], f'{entry.filename}: JSON-Größenlimit überschritten')
                    require(entry.extract_version <= 20, 'ZIP64 oder neuere ZIP-Erweiterungen nicht erlaubt')
                    total += entry.file_size
                require(total <= lim['totalUncompressedBytes'], 'ZIP überschreitet das entpackte Gesamtlimit')

                def chunks(name):
                    # Never extract. Count actual output, even if ZIP metadata lies.
                    with archive.open(name) as stream:
                        count = 0
                        while True:
                            block = stream.read(min(65536, lim['entryBytes'] - count + 1))
                            if not block:
                                break
                            count += len(block)
                            require(count <= min(lim['entryBytes'], archive.getinfo(name).file_size), f'{name}: tatsächliche Größe überschritten')
                            yield block
                        require(count == archive.getinfo(name).file_size, f'{name}: falsche ZIP-Größe')

                def read(name):
                    return b''.join(chunks(name))

                manifest = parse_json(read('manifest.json'), 'manifest.json')
                errors = sorted(Draft202012Validator(SCHEMA).iter_errors(manifest), key=lambda e: str(e.path))
                if errors:
                    err = errors[0]
                    raise ValidationError('manifest.json/' + '/'.join(map(str, err.path)) + ': ' + err.message)
                n = manifest['frameCount']
                require(archive.getinfo('reference/poses.bin').file_size == n * 924, 'poses.bin: erwartet 33 Gelenke × 7 Float32 je Frame (924 Byte)')
                require(archive.getinfo('reference/timestamps.bin').file_size == n * 8, 'timestamps.bin: erwartet einen Float64 je Frame')
                for name, metadata in manifest['files'].items():
                    require(metadata['size'] == archive.getinfo(name).file_size, f'{name}: Dateigröße stimmt nicht')
                    digest = hashlib.sha256()
                    for block in chunks(name):
                        digest.update(block)
                    require(digest.hexdigest() == metadata['sha256'], f'{name}: SHA-256-Prüfsumme stimmt nicht')
                zoom = parse_json(read('reference/zoom.json'), 'zoom.json')
                zoom_errors = list(Draft202012Validator(SCHEMA['properties']['zoom']).iter_errors(zoom))
                require(not zoom_errors, 'zoom.json: ungültige Zoomparameter/Datentypen')
                require(zoom == manifest['zoom'], 'zoom.json: stimmt nicht mit Manifest überein')
                require(zoom['x'] + zoom['width'] <= 1 and zoom['y'] + zoom['height'] <= 1, 'Zoom: Ausschnitt liegt außerhalb des Originalvideos')
                quality = parse_json(read('reference/quality.json'), 'quality.json')
                require(isinstance(quality, dict) and set(quality) == {'status', 'missingLandmarks', 'warnings'}, 'quality.json: ungültige Felder')
                require(quality['status'] in ('complete', 'partial'), 'quality.json: ungültiger Status')
                require(type(quality['missingLandmarks']) is int and 0 <= quality['missingLandmarks'] <= n * 33, 'quality.json: ungültige Anzahl fehlender Gelenke')
                require(isinstance(quality['warnings'], list) and len(quality['warnings']) <= 100 and all(isinstance(v, str) and len(v) <= 500 for v in quality['warnings']), 'quality.json: ungültige Warnungen')
                previous = -1.0
                # Stream binary validation with record alignment across chunk boundaries.
                def records(name, fmt):
                    pending = b''
                    size = struct.calcsize(fmt)
                    for block in chunks(name):
                        pending += block
                        end = len(pending) // size * size
                        yield from struct.iter_unpack(fmt, pending[:end])
                        pending = pending[end:]
                    require(not pending, f'{name}: unvollständiger Datensatz')
                for i, (timestamp,) in enumerate(records('reference/timestamps.bin', '<d')):
                    require(math.isfinite(timestamp) and previous < timestamp <= manifest['durationSeconds'], f'timestamps.bin: Frame {i}: Zeit muss endlich, nicht negativ und streng steigend innerhalb der Dauer sein')
                    require(timestamp >= 0, 'timestamps.bin: negative Zeit')
                    previous = timestamp
                missing = 0
                for i, values in enumerate(records('reference/poses.bin', '<7f')):
                    xyz, confidence = values[:5], values[5:]
                    require(all(math.isfinite(v) and 0 <= v <= 1 for v in confidence), f'poses.bin: Gelenk {i}: Visibility/Presence außerhalb [0,1]')
                    if any(math.isnan(v) for v in xyz):
                        require(all(math.isnan(v) for v in xyz) and confidence == (0.0, 0.0), f'poses.bin: Gelenk {i}: fehlende Werte müssen fünf NaN und zwei Nullen sein')
                        missing += 1
                    else:
                        require(all(math.isfinite(v) for v in xyz), f'poses.bin: Gelenk {i}: unendliche Koordinate')
                        require(all(0 <= v <= 1 for v in xyz[:2]), f'poses.bin: Gelenk {i}: Bildkoordinate außerhalb [0,1]')
                require(quality['missingLandmarks'] == missing and quality['status'] == ('partial' if missing else 'complete'), 'quality.json: Status/Fehlzahl widerspricht Skelettdaten')
                video_start = next(chunks('reference/video.mp4'))[:8]
                require(video_start[4:8] == b'ftyp', 'video.mp4: MP4-ftyp-Signatur fehlt')
                prefix, suffix = b'', b''
                for block in chunks('assets/preview.jpg'):
                    if not prefix:
                        prefix = block[:3]
                    suffix = (suffix + block)[-2:]
                require(prefix == b'\xff\xd8\xff' and suffix == b'\xff\xd9', 'preview.jpg: JPEG-Signatur fehlt')
                return manifest
    except ValidationError:
        raise
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError, NotImplementedError, EOFError, zlib.error, struct.error) as exc:
        raise ValidationError(f'ZIP nicht lesbar oder beschädigt: {exc}') from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    args = parser.parse_args()
    try:
        manifest = validate(args.package)
    except ValidationError as exc:
        parser.exit(1, f'Ungültiges .choreo-Paket: {exc}\n')
    print(f"Gültig: {manifest['title']} ({manifest['frameCount']} Frames)")


if __name__ == '__main__':
    main()
