"""Streaming, validated, atomic export of the unchanged version 1.0.0 schema."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import zipfile

from analyzer.validate import SCHEMA, SPEC, validate


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)+'\n', encoding='utf-8')


def export(output, payload, *, title, duration, count, model, width, height, zoom, audio, quality, overwrite=False, audio_offset=0):
    write_json(payload['reference/zoom.json'], zoom)
    write_json(payload['reference/quality.json'], quality)
    files = {}
    for name, path in payload.items():
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for block in iter(lambda: source.read(65536), b''):
                digest.update(block)
        files[name] = dict(size=path.stat().st_size, sha256=digest.hexdigest())
    manifest = dict(format='showtanz-choreo', version='1.0.0', title=title,
                    durationSeconds=duration, frameCount=count, model=model,
                    video=dict(width=width, height=height), zoom=zoom,
                    audio=dict(source='reference/video.mp4' if audio else 'none', offsetSeconds=audio_offset),
                    coordinateSystem=SCHEMA['properties']['coordinateSystem']['const'],
                    layout=SCHEMA['properties']['layout']['const'], files=files)
    if sum(f['size'] for f in files.values()) > SPEC['limits']['totalUncompressedBytes']:
        raise ValueError('Export überschreitet das Paketgrößenlimit.')
    # Same filesystem as destination; exceptions/cancellation leave no partial output.
    with tempfile.TemporaryDirectory(prefix='.choreo-', dir=output.parent) as directory:
        package = Path(directory)/'export.choreo'
        with zipfile.ZipFile(package, 'w', compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
            archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, allow_nan=False).encode('utf-8'))
            for name, path in payload.items():
                archive.write(path, name)
        validate(package)
        if overwrite:
            package.replace(output)
        else:
            # Windows rename fails atomically if another process created the target.
            # Hard-link provides the same no-clobber guarantee on POSIX as well.
            if os.name == 'nt':
                package.rename(output)
            else:
                os.link(package, output)
    return manifest
