"""Export validated .choreo pose data for local inspection, without re-analysis."""
import argparse
from contextlib import closing
import csv
import json
import math
from pathlib import Path
import sqlite3
import struct
import tempfile
import zipfile

from analyzer.validate import SHARED, validate

POINT_COLUMNS = ['frameIndex', 'timestampSeconds', 'landmarkIndex', 'landmarkName',
                 'imageX', 'imageY', 'worldX', 'worldY', 'worldZ',
                 'visibility', 'presence', 'isMissing']
FRAME_COLUMNS = ['frameIndex', 'timestampSeconds', 'missingLandmarks',
                 'lowConfidenceLandmarks', 'borderLandmarks']


def csv_number(value):
    """German Excel CSV: decimal comma, missing coordinates are empty cells."""
    if value is None:
        return ''
    if isinstance(value, float):
        return repr(value).replace('.', ',')
    return value


def export_poses(package, output_directory):
    package, output = Path(package).resolve(), Path(output_directory).resolve()
    if output.exists():
        raise ValueError('Ausgabeordner existiert bereits. Einen neuen Ordnernamen wählen.')
    if not output.parent.is_dir():
        raise ValueError('Übergeordneter Ausgabeordner existiert nicht.')
    # Validate hashes, binary records and all paths before consuming any payload.
    manifest = validate(package)
    registry = json.loads((SHARED/'landmarks.json').read_text(encoding='utf-8'))['landmarks']
    names = [item['name'] for item in registry]
    summary = dict(frames=manifest['frameCount'], points=manifest['frameCount']*33,
                   missingLandmarks=0, framesWithMissing=0, framesWithLowConfidence=0,
                   framesWithBorderPoints=0)
    with tempfile.TemporaryDirectory(prefix='.pose-export-', dir=output.parent) as directory:
        work = Path(directory)
        with zipfile.ZipFile(package) as archive, \
                closing(sqlite3.connect(work/'haltungspunkte.sqlite')) as database, \
                (work/'haltungspunkte.csv').open('w', encoding='utf-8-sig', newline='') as point_file, \
                (work/'bilder.csv').open('w', encoding='utf-8-sig', newline='') as frame_file:
            quality = json.loads(archive.read('reference/quality.json'))
            database.executescript('''
                PRAGMA foreign_keys=ON;
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value_json TEXT NOT NULL);
                CREATE TABLE landmark_names (landmark_index INTEGER PRIMARY KEY, name TEXT NOT NULL);
                CREATE TABLE frames (frame_index INTEGER PRIMARY KEY, timestamp_seconds REAL NOT NULL UNIQUE,
                    missing_landmarks INTEGER NOT NULL, low_confidence_landmarks INTEGER NOT NULL,
                    border_landmarks INTEGER NOT NULL);
                CREATE TABLE landmarks (frame_index INTEGER NOT NULL REFERENCES frames(frame_index),
                    landmark_index INTEGER NOT NULL REFERENCES landmark_names(landmark_index),
                    image_x REAL, image_y REAL, world_x REAL, world_y REAL, world_z REAL,
                    visibility REAL NOT NULL, presence REAL NOT NULL, is_missing INTEGER NOT NULL,
                    PRIMARY KEY (frame_index, landmark_index));
                CREATE VIEW pose_points AS SELECT f.timestamp_seconds, n.name AS landmark_name, p.*
                    FROM landmarks p JOIN frames f USING(frame_index)
                    JOIN landmark_names n USING(landmark_index);
            ''')
            points_csv, frames_csv = csv.writer(point_file, delimiter=';'), csv.writer(frame_file, delimiter=';')
            points_csv.writerow(POINT_COLUMNS)
            frames_csv.writerow(FRAME_COLUMNS)
            with database, archive.open('reference/poses.bin') as poses, archive.open('reference/timestamps.bin') as timestamps:
                database.executemany('INSERT INTO landmark_names VALUES (?, ?)',
                                     [(item['index'], item['name']) for item in registry])
                for frame_index in range(manifest['frameCount']):
                    timestamp, = struct.unpack('<d', timestamps.read(8))
                    rows, missing, low, border = [], 0, 0, 0
                    for index, values in enumerate(struct.iter_unpack('<7f', poses.read(924))):
                        absent = math.isnan(values[0])
                        coordinates = (None,)*5 if absent else values[:5]
                        visibility, presence = values[5:]
                        missing += int(absent)
                        low += int(not absent and min(visibility, presence) < .5)
                        border += int(not absent and min(visibility, presence) >= .5 and
                                      (values[0] < .02 or values[0] > .98 or values[1] < .02 or values[1] > .98))
                        row = (frame_index, index, *coordinates, visibility, presence, int(absent))
                        rows.append(row)
                        points_csv.writerow([csv_number(v) for v in
                                             (frame_index, timestamp, index, names[index],
                                              *coordinates, visibility, presence, int(absent))])
                    frame = (frame_index, timestamp, missing, low, border)
                    frames_csv.writerow([csv_number(v) for v in frame])
                    database.execute('INSERT INTO frames VALUES (?, ?, ?, ?, ?)', frame)
                    database.executemany('INSERT INTO landmarks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', rows)
                    summary['missingLandmarks'] += missing
                    summary['framesWithMissing'] += int(missing > 0)
                    summary['framesWithLowConfidence'] += int(low > 0)
                    summary['framesWithBorderPoints'] += int(border > 0)
                report = dict(format='showtanz-pose-debug', version='1.0.0',
                              sourceManifest=manifest, quality=quality, summary=summary,
                              zoomIsFullFrame=all(manifest['zoom'][k] == v for k, v in
                                                  (('x',0), ('y',0), ('width',1), ('height',1))),
                              zoomAppliedToVideo=False)
                database.executemany('INSERT INTO metadata VALUES (?, ?)',
                                     [(key, json.dumps(value, ensure_ascii=False, allow_nan=False))
                                      for key, value in report.items()])
            (work/'bericht.json').write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2)+'\n', encoding='utf-8')
        (work/'LIESMICH.txt').write_text(
            'Haltungspunkte – separate Testausgabe\n\n'
            'haltungspunkte.csv: eine Zeile pro Zeitpunkt und Gelenk, 33 Zeilen pro Bild.\n'
            'bilder.csv: Fehlzahlen und Konfidenzprobleme pro Zeitpunkt.\n'
            'CSV: UTF-8 mit BOM, Semikolon, Dezimalkomma für deutsches Excel.\n'
            'haltungspunkte.sqlite: Tabellen frames, landmarks, landmark_names, metadata;\n'
            'Ansicht pose_points verbindet Gelenknamen und Videotimestamps.\n'
            'bericht.json: Metadaten, Zoom, Qualitätsbericht und Zusammenfassung.\n\n'
            'frameIndex und landmarkIndex beginnen bei 0. timestampSeconds bezieht sich\n'
            'auf das Paketvideo. imageX/Y: gesamtes ungespiegeltes Bild, Werte 0 bis 1.\n'
            'worldX/Y/Z: geschätzte Meter relativ zum Hüftmittelpunkt, keine Bühnenposition.\n'
            'visibility/presence: Modellwerte von 0 bis 1. isMissing=1: fehlender Punkt;\n'
            'Koordinaten leer in CSV bzw. NULL in SQLite, Konfidenzen 0.\n'
            'lowConfidenceLandmarks zählt vorhandene Punkte mit visibility oder presence <0,5.\n'
            'borderLandmarks zählt zuverlässige Punkte innerhalb von 2 % zum Bildrand.\n'
            'Fehlende Punkte werden bei diesen beiden Zählern nicht doppelt gezählt.\n\n'
            'Der Zoom ist eine feste Darstellungsinformation; das Paketvideo ist nicht\n'
            'zugeschnitten. Ganzbild ist der Sicherheitsfallback bei unsicheren Grenzen.\n'
            'Mehrpersonenerkennung lässt sich aus den gespeicherten Punkten allein nicht\n'
            'rekonstruieren; dazu stehen nur die Warnungen des Originalberichts bereit.\n'
            'Keine Interpolation, neue Modellerkennung oder Veränderung am Paket.\n', encoding='utf-8-sig')
        # Reserve a new destination exclusively; never overwrite an existing folder.
        output.mkdir()
        moved = []
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
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path, help='Vorhandene .choreo-Datei')
    parser.add_argument('output_directory', type=Path, help='Neuer Ordner für CSV, SQLite und Bericht')
    args = parser.parse_args(argv)
    try:
        report = export_poses(args.package, args.output_directory)
    except KeyboardInterrupt:
        parser.exit(130, 'Export abgebrochen.\n')
    except Exception as exc:
        parser.exit(1, f'Punktexport fehlgeschlagen: {exc}\n')
    print(f"Exportiert: {args.output_directory} ({report['summary']['frames']} Bilder, {report['summary']['points']} Gelenkpunkte)")


if __name__ == '__main__':
    main()
