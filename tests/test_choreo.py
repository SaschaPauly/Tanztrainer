"""Package contract and hostile-input regression cases; no external media."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

from analyzer.validate import validate, ValidationError, SCHEMA
from jsonschema import Draft202012Validator

FIXTURE = Path(__file__).parent/'fixtures/synthetic.choreo'


class ChoreoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'test.choreo'
        with zipfile.ZipFile(FIXTURE) as archive:
            self.data = {n:archive.read(n) for n in archive.namelist()}
        self.manifest = json.loads(self.data['manifest.json'])

    def write(self, *, hashes=True, compression=zipfile.ZIP_STORED):
        if hashes:
            for name, meta in self.manifest['files'].items():
                if name in self.data:
                    meta.update(size=len(self.data[name]),sha256=hashlib.sha256(self.data[name]).hexdigest())
        self.data['manifest.json'] = json.dumps(self.manifest).encode()
        with zipfile.ZipFile(self.path,'w',compression=compression) as archive:
            for name, data in self.data.items():
                archive.writestr(name,data)
        return self.path

    def reject(self, pattern, **kwargs):
        with self.assertRaisesRegex(ValidationError,pattern):
            validate(self.write(**kwargs))

    def test_valid(self):
        self.assertEqual(validate(FIXTURE)['frameCount'],4)

    def test_schema_itself(self):
        Draft202012Validator.check_schema(SCHEMA)

    def test_corrupt_zip(self):
        self.path.write_bytes(b'not zip')
        with self.assertRaisesRegex(ValidationError,'ZIP'):
            validate(self.path)

    def test_missing(self):
        del self.data['assets/preview.jpg']
        self.reject('fehlende Dateien')

    def test_checksum(self):
        self.manifest['files']['assets/preview.jpg']['sha256'] = '0'*64
        self.reject('SHA-256',hashes=False)

    def test_version(self):
        self.manifest['version'] = '2.0.0'
        self.reject('version')

    def test_landmark_count(self):
        self.manifest['layout']['landmarks'] = 32
        self.reject('layout')

    def test_pose_length(self):
        self.data['reference/poses.bin'] = self.data['reference/poses.bin'][:-28]
        self.reject('33 Gelenke')

    def test_timestamps(self):
        for values in [(0,.25,.25,.75),(-.1,.25,.5,.75),(0,.25,.5,2),(0,.25,float('nan'),.75),(0,.25,float('inf'),.75)]:
            with self.subTest(values=values):
                self.data['reference/timestamps.bin'] = struct.pack('<4d',*values)
                self.reject('Zeit|negative')

    def test_timestamp_length(self):
        self.data['reference/timestamps.bin'] = b'x'
        self.reject('Float64')

    def test_zoom(self):
        for key,value in [('width',0),('x',.9),('targetAspectRatio',0)]:
            with self.subTest(key=key):
                zoom = copy.deepcopy(json.loads(self.data['reference/zoom.json']))
                zoom[key] = value
                self.manifest['zoom'] = zoom
                self.reject('zoom|Zoom')

    def test_zoom_mismatch(self):
        self.manifest['zoom']['x'] = 0
        self.reject('stimmt nicht mit Manifest')

    def test_zoom_json_types(self):
        # Python equality treats False == 0; the separate schema must reject it.
        zoom = dict(self.manifest['zoom'])
        zoom['y'] = False
        self.data['reference/zoom.json'] = json.dumps(zoom).encode()
        self.reject('Datentypen')

    def test_paths(self):
        for path in ['../video.mp4','/video.mp4','reference\\video.mp4','C:/video.mp4','reference/../video.mp4']:
            with self.subTest(path=path):
                self.data[path] = self.data.pop('reference/video.mp4')
                self.reject('Pfade')
                self.data['reference/video.mp4'] = self.data.pop(path)

    def test_compression_bomb(self):
        self.data['reference/video.mp4'] = b'0'*200000
        self.reject('Kompression',compression=zipfile.ZIP_DEFLATED)

    def test_limits(self):
        path = self.write()
        for limits in [{'archiveBytes':10},{'entryBytes':100},{'totalUncompressedBytes':5000},{'jsonBytes':10},{'entries':2}]:
            with self.subTest(limits=limits), self.assertRaises(ValidationError):
                validate(path,limits=limits)

    def test_declared_oversize(self):
        data = bytearray(FIXTURE.read_bytes())
        offset = data.index(b'PK\x01\x02')
        struct.pack_into('<I',data,offset+24,1073741825)
        self.path.write_bytes(data)
        with self.assertRaisesRegex(ValidationError,'größenlimit'):
            validate(self.path)

    def test_duplicate(self):
        self.write()
        with self.assertWarns(UserWarning):
            with zipfile.ZipFile(self.path,'a') as archive:
                archive.writestr('manifest.json',b'{}')
        with self.assertRaisesRegex(ValidationError,'Einträge|Pfade'):
            validate(self.path)

    def test_symlink(self):
        self.write()
        with zipfile.ZipFile(self.path,'w') as archive:
            for name,data in self.data.items():
                info = zipfile.ZipInfo(name)
                info.external_attr = 0o120777 << 16
                archive.writestr(info,data)
        with self.assertRaisesRegex(ValidationError,'regulärer'):
            validate(self.path)

    def test_missing_values_and_quality(self):
        self.data['reference/poses.bin'] = struct.pack('<7f',*[float('nan')]*5,0,0)+self.data['reference/poses.bin'][28:]
        self.reject('quality.json')
        self.data['reference/quality.json'] = json.dumps({'status':'partial','missingLandmarks':1,'warnings':[]}).encode()
        validate(self.write())

    def test_invalid_pose(self):
        for pose in [(2,.5,0,0,0,1,1),(.5,.5,0,0,float('inf'),1,1),(.5,.5,0,0,0,-1,1),(float('nan'),.5,0,0,0,0,0)]:
            self.data['reference/poses.bin'] = struct.pack('<7f',*pose)+self.data['reference/poses.bin'][28:]
            self.reject('poses.bin')

    def test_json_duplicate_and_nonfinite(self):
        for raw in [b'{"x":0,"x":1}',b'{"x":NaN}',b'{"x":1e309}',b'\xff']:
            self.data['reference/zoom.json'] = raw
            self.reject('JSON')

    def test_landmark_registry(self):
        registry = json.loads((Path(__file__).parents[1]/'shared/landmarks.json').read_text())
        self.assertEqual([p['index'] for p in registry['landmarks']], list(range(33)))
        self.assertEqual(len({p['name'] for p in registry['landmarks']}), 33)
        self.assertEqual(registry['landmarks'][23]['name'], 'left_hip')
        self.assertEqual(SCHEMA['properties']['layout']['const']['bytesPerFrame'], 33*7*4)

    def test_crc_corruption(self):
        data = bytearray(FIXTURE.read_bytes())
        with zipfile.ZipFile(FIXTURE) as archive:
            info = archive.getinfo('assets/preview.jpg')
            offset = info.header_offset
        name_len, extra_len = struct.unpack_from('<HH',data,offset+26)
        data[offset+30+name_len+extra_len+10] ^= 1
        self.path.write_bytes(data)
        with self.assertRaisesRegex(ValidationError,'beschädigt'):
            validate(self.path)

    def test_local_path_mismatch(self):
        data = bytearray(FIXTURE.read_bytes())
        data[30] ^= 1  # first local filename; central directory remains intact
        self.path.write_bytes(data)
        with self.assertRaisesRegex(ValidationError,'beschädigt'):
            validate(self.path)

    def test_encrypted_flag(self):
        data = bytearray(FIXTURE.read_bytes())
        offset = data.index(b'PK\x01\x02')
        struct.pack_into('<H',data,offset+8,1)
        self.path.write_bytes(data)
        with self.assertRaisesRegex(ValidationError,'Verschlüsselte'):
            validate(self.path)

    def test_unsupported_compression(self):
        self.reject('Kompressionsverfahren',compression=zipfile.ZIP_BZIP2)

    def test_zip64_version(self):
        data = bytearray(FIXTURE.read_bytes())
        offset = data.index(b'PK\x01\x02')
        struct.pack_into('<H',data,offset+6,45)
        self.path.write_bytes(data)
        with self.assertRaisesRegex(ValidationError,'ZIP64'):
            validate(self.path)

    def test_media_signatures(self):
        for name in ['reference/video.mp4','assets/preview.jpg']:
            original = self.data[name]
            self.data[name] = b'garbage'
            self.reject('Signatur')
            self.data[name] = original

    def test_deflated_valid(self):
        validate(self.write(compression=zipfile.ZIP_DEFLATED))


if __name__ == '__main__':
    unittest.main()
