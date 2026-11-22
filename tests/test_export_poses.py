"""Readable pose exports retain timestamps, values and explicit missing data."""
import csv
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from analyzer.export_poses import export_poses
from analyzer.pose import MISSING
from analyzer.validate import ValidationError

FIXTURE = Path(__file__).parent/'fixtures/synthetic.choreo'


class PoseExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.output = self.root/'Punkte ü test'

    def test_csv_sqlite_and_source_values_match(self):
        before = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        report = export_poses(FIXTURE, self.output)
        with zipfile.ZipFile(FIXTURE) as archive:
            points = list(struct.iter_unpack('<7f', archive.read('reference/poses.bin')))
            times = struct.unpack('<4d', archive.read('reference/timestamps.bin'))
        with (self.output/'haltungspunkte.csv').open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream, delimiter=';'))
        self.assertEqual(len(rows), 132)
        with closing(sqlite3.connect(self.output/'haltungspunkte.sqlite')) as db:
            stored = db.execute('SELECT image_x,image_y,world_x,world_y,world_z,visibility,presence FROM landmarks ORDER BY frame_index,landmark_index').fetchall()
            self.assertEqual(stored, points)
            self.assertEqual([t[0] for t in db.execute('SELECT timestamp_seconds FROM frames ORDER BY frame_index')], list(times))
            self.assertEqual(db.execute('SELECT count(*) FROM pose_points').fetchone()[0], 132)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        for i, row in enumerate(rows):
            self.assertEqual(float(row['timestampSeconds'].replace(',', '.')), times[i//33])
            for key, expected in zip(('imageX','imageY','worldX','worldY','worldZ','visibility','presence'), points[i]):
                self.assertEqual(float(row[key].replace(',', '.')), expected)
        self.assertEqual(report['summary']['points'], 132)
        self.assertFalse(report['zoomAppliedToVideo'])
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), before)

    def test_missing_coordinates_are_blank_and_null_not_zero(self):
        with zipfile.ZipFile(FIXTURE) as archive:
            data = {name: archive.read(name) for name in archive.namelist()}
        data['reference/poses.bin'] = MISSING+data['reference/poses.bin'][28:]
        data['reference/quality.json'] = json.dumps(dict(status='partial', missingLandmarks=1, warnings=[])).encode()
        manifest = json.loads(data['manifest.json'])
        for name, meta in manifest['files'].items():
            meta.update(size=len(data[name]), sha256=hashlib.sha256(data[name]).hexdigest())
        data['manifest.json'] = json.dumps(manifest).encode()
        source = self.root/'missing.choreo'
        with zipfile.ZipFile(source, 'w') as archive:
            for name, value in data.items():
                archive.writestr(name, value)
        report = export_poses(source, self.output)
        with closing(sqlite3.connect(self.output/'haltungspunkte.sqlite')) as db:
            self.assertEqual(db.execute('SELECT image_x,image_y,world_x,world_y,world_z,visibility,presence,is_missing FROM landmarks WHERE frame_index=0 AND landmark_index=0').fetchone(), (None,None,None,None,None,0.,0.,1))
        with (self.output/'haltungspunkte.csv').open(encoding='utf-8-sig', newline='') as stream:
            first = next(csv.DictReader(stream, delimiter=';'))
        self.assertEqual(first['imageX'], '')
        self.assertEqual(first['isMissing'], '1')
        self.assertEqual(report['summary']['missingLandmarks'], 1)
        self.assertEqual(report['summary']['framesWithMissing'], 1)

    def test_existing_folder_is_preserved(self):
        self.output.mkdir()
        sentinel = self.output/'existing.txt'
        sentinel.write_text('keep')
        with self.assertRaisesRegex(ValueError, 'existiert bereits'):
            export_poses(FIXTURE, self.output)
        self.assertEqual(sentinel.read_text(), 'keep')

    def test_invalid_package_creates_no_output(self):
        source = self.root/'broken.choreo'
        source.write_bytes(b'broken')
        with self.assertRaises(ValidationError):
            export_poses(source, self.output)
        self.assertFalse(self.output.exists())

    def test_cancel_during_writing_removes_temporary_output(self):
        with patch('analyzer.export_poses.csv_number', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                export_poses(FIXTURE, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob('.pose-export-*')), [])


if __name__ == '__main__':
    unittest.main()
