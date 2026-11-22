"""Explicit download of Google's versioned Pose Landmarker model bundles."""
import argparse
from pathlib import Path
import tempfile
from urllib.request import urlopen
import zipfile
from analyzer.runtime import check_cancel, notify

MODEL_NAMES = ('lite', 'full', 'heavy')


def model_path(directory, name):
    if name not in MODEL_NAMES:
        raise ValueError('Unbekanntes Modell.')
    return Path(directory)/f'pose_landmarker_{name}.task'


def download_models(directory, names=MODEL_NAMES, *, cancel=None, progress=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name in names:
        check_cancel(cancel)
        target = model_path(directory, name)
        if target.is_file():
            if not zipfile.is_zipfile(target):
                raise ValueError(f'Modelldatei beschädigt: {target}')
            print(f'Modell vorhanden: {name}', flush=True)
            continue
        url = f'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_{name}/float16/1/pose_landmarker_{name}.task'
        print(f'Lade offizielles Google-Modell: {name}', flush=True)
        with tempfile.TemporaryDirectory(prefix='.model-', dir=directory) as temporary:
            path = Path(temporary)/'model.task'
            size = 0
            with urlopen(url, timeout=60) as response, path.open('wb') as output:
                while block := response.read(1024*1024):
                    check_cancel(cancel)
                    size += len(block)
                    if size > 100*1024*1024:
                        raise ValueError('Modelldownload überschreitet 100 MiB.')
                    output.write(block)
                    notify(progress,'download',None,f'Google-Modell {name}: {size/1024/1024:.1f} MiB geladen …')
            if not zipfile.is_zipfile(path):
                raise ValueError(f'Ungültiges Modellbundle: {name}')
            if target.exists():
                raise FileExistsError(target)
            check_cancel(cancel)
            path.rename(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    try:
        download_models(args.directory)
    except Exception as exc:
        parser.exit(1, f'Modelldownload fehlgeschlagen: {exc}\n')


if __name__ == '__main__':
    main()
