"""Desktop work sessions; validated, cancellable and independent of Qt widgets."""
from dataclasses import dataclass
import json
import mmap
import os
from pathlib import Path
import struct
import tempfile
import zipfile

from analyzer.cli import analyze
from analyzer.runtime import check_cancel, notify
from analyzer.validate import validate
from analyzer.video import normalize, inspect_video


def read_frame(video, seconds, *, cancel=None, progress=None):
    """Decode the exact recorded PTS for single stepping, including B frames.

    Native player seeks are millisecond-based and can skip several frames.
    This bounded background decoder keeps step/pose review exact instead.
    """
    import av
    check_cancel(cancel)
    notify(progress,'frame',None,'Einzelbild wird geladen …')
    with av.open(str(video)) as container:
        stream=container.streams.video[0];stream.codec_context.thread_count=2
        container.seek(max(0,int(seconds*av.time_base)),backward=True,any_frame=False)
        for frame in container.decode(stream):
            check_cancel(cancel)
            if frame.pts is None:continue
            timestamp=float(frame.pts*frame.time_base)
            if timestamp+1e-5<seconds:continue
            if abs(timestamp-seconds)>1e-5:
                raise ValueError('Zum gespeicherten Zeitpunkt wurde kein exaktes Videobild gefunden.')
            image=frame.to_image().convert('RGB')
            return dict(pixels=image.tobytes(),width=image.width,height=image.height,seconds=timestamp)
    raise ValueError('Videobild am gespeicherten Zeitpunkt fehlt.')


@dataclass
class PreparedInput:
    source: Path
    video: Path
    info: dict
    workspace: object

    def close(self):
        self.workspace.cleanup()


class PackageSession:
    """Memory-map binary data, retaining only one displayed pose at a time."""
    def __init__(self, package, manifest, quality, workspace, owner=None):
        self.package=Path(package)
        self.manifest,self.quality=manifest,quality
        self.workspace,self.owner=workspace,owner
        self.video=Path(workspace.name)/'video.mp4'
        self.files=[];self.maps=[]
        try:
            for name in ('poses.bin','timestamps.bin'):
                stream=(Path(workspace.name)/name).open('rb')
                self.files.append(stream)
                self.maps.append(mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ))
        except BaseException:
            self.close()
            raise

    @property
    def frame_count(self):return self.manifest['frameCount']

    def timestamp(self,index):
        return struct.unpack_from('<d',self.maps[1],index*8)[0]

    def frame_at(self,seconds):
        if seconds+1e-5<self.timestamp(0):return None
        lo,hi=0,self.frame_count-1
        while lo<hi:
            mid=(lo+hi+1)//2
            if self.timestamp(mid)<=seconds+1e-5:lo=mid
            else:hi=mid-1
        return lo

    def pose(self,index):
        return tuple(struct.iter_unpack('<7f',self.maps[0][index*924:(index+1)*924]))

    def close(self):
        for mapping in self.maps:mapping.close()
        self.maps=[]
        for stream in self.files:stream.close()
        self.files=[]
        # The GUI releases QMediaPlayer's source before cleanup. If a decoder
        # still holds the video briefly, this can be safely retried later.
        self.workspace.cleanup()
        if self.owner is not None:self.owner.cleanup()


def prepare_input(source, *, cancel=None, progress=None):
    source=Path(source).resolve()
    if not source.is_file():raise ValueError('Videodatei fehlt.')
    workspace=tempfile.TemporaryDirectory(prefix='showtanz-import-')
    try:
        video=Path(workspace.name)/'prepared.mp4'
        info=normalize(source,video,cancel=cancel,progress=progress)
        check_cancel(cancel)
        return PreparedInput(source,video,info,workspace)
    except BaseException:
        workspace.cleanup()
        raise


def open_package(package, *, owner=None, cancel=None, progress=None):
    check_cancel(cancel)
    notify(progress,'open',None,'Choreografie wird vollständig geprüft …')
    manifest=validate(package)
    check_cancel(cancel)
    workspace=tempfile.TemporaryDirectory(prefix='showtanz-preview-')
    try:
        with zipfile.ZipFile(package) as archive:
            quality=json.loads(archive.read('reference/quality.json'))
            for name,filename in (('reference/video.mp4','video.mp4'),('reference/poses.bin','poses.bin'),
                                  ('reference/timestamps.bin','timestamps.bin')):
                with archive.open(name) as source,(Path(workspace.name)/filename).open('wb') as target:
                    while block:=source.read(65536):
                        check_cancel(cancel)
                        target.write(block)
        check_cancel(cancel)
        # The portable validator checks ZIP/binary contracts, not codecs. Check
        # real media dimensions/limits before handing a package video to Qt.
        info=inspect_video(Path(workspace.name)/'video.mp4')
        if (info['width'],info['height'])!=(manifest['video']['width'],manifest['video']['height']):
            raise ValueError('Videogröße widerspricht den Paketmetadaten.')
        if info['codec']!='h264' or info['pixel_format']!='yuv420p' or abs(info['duration']-manifest['durationSeconds'])>.1:
            raise ValueError('Paketvideo entspricht nicht dem H.264-/Zeitformat.')
        check_cancel(cancel)
        session=PackageSession(package,manifest,quality,workspace,owner)
        notify(progress,'open',1.,'Choreografie bereit zur Prüfung.')
        return session
    except BaseException:
        workspace.cleanup()
        if owner is not None:owner.cleanup()
        raise


def analyze_prepared(prepared, model, *, title, single_person=False, target_point=None,
                     zoom_percent=30, backend='cpu', max_side=1280, max_fps=0,
                     aspect=9/16, cancel=None, progress=None):
    workspace=tempfile.TemporaryDirectory(prefix='showtanz-analysis-')
    try:
        package=Path(workspace.name)/'result.choreo'
        analyze(prepared.source,package,Path(model),title=title,single_person=single_person,
                target_point=target_point,zoom_max_uncertain_percent=zoom_percent,
                backend=backend,max_side=max_side,max_fps=max_fps,aspect=aspect,
                prepared_video=prepared.video,cancel=cancel,progress=progress)
        return open_package(package,owner=workspace,cancel=cancel,progress=progress)
    except BaseException:
        workspace.cleanup()
        raise


def save_package(package, output, *, overwrite=False, cancel=None, progress=None):
    package,output=Path(package).resolve(),Path(output).resolve()
    if package==output or output.suffix.lower()!='.choreo':
        raise ValueError('Bitte einen anderen Dateinamen mit Endung .choreo wählen.')
    if output.exists() and not overwrite:raise ValueError('Zieldatei existiert bereits.')
    if not output.parent.is_dir():raise ValueError('Ausgabeordner fehlt.')
    check_cancel(cancel)
    validate(package)
    size=package.stat().st_size;copied=0
    with tempfile.TemporaryDirectory(prefix='.choreo-save-',dir=output.parent) as directory:
        temporary=Path(directory)/'result.choreo'
        with package.open('rb') as source,temporary.open('wb') as target:
            while block:=source.read(65536):
                check_cancel(cancel)
                target.write(block);copied+=len(block)
                if copied%(1024*1024)<65536:
                    notify(progress,'save',copied/size,'Choreografie wird gespeichert …')
        check_cancel(cancel)
        validate(temporary)
        check_cancel(cancel)
        if overwrite:temporary.replace(output)
        elif os.name=='nt':temporary.rename(output)
        else:os.link(temporary,output)
    notify(progress,'save',1.,'Choreografie gespeichert.')
    return output
