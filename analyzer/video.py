"""Local codec normalization and bounded sequential decoding using actual PTS."""
import subprocess
import time

from analyzer.runtime import check_cancel, notify

MAX_BYTES = 900 * 1024 * 1024  # leave room for binary data and ZIP headers
MAX_PIXELS = 4096 * 2160


def inspect_video(path):
    import av
    with av.open(str(path)) as container:
        if not container.streams.video:
            raise ValueError('Datei enthält keine Videospur.')
        stream = container.streams.video[0]
        # FFmpeg/PyAV use 0/1 as well as None for unspecified SAR.
        # Unspecified SAR is displayed as square pixels; it is not anamorphic.
        if stream.sample_aspect_ratio not in (None, 0, 1):
            raise ValueError('Nichtquadratische Videopixel werden ohne Geometrieänderung nicht unterstützt.')
        if not (0 < stream.width <= 16384 and 0 < stream.height <= 16384
                and stream.width*stream.height <= MAX_PIXELS):
            raise ValueError('Video überschreitet das Decoderlimit (maximal 4096 × 2160 Pixel insgesamt).')
        duration = float(container.duration / av.time_base) if container.duration else 0
        if not 0 < duration <= 14400:
            raise ValueError('Videodauer fehlt oder liegt außerhalb 0–14400 s.')
        return dict(width=stream.width, height=stream.height, duration=duration,
                    audio=bool(container.streams.audio), codec=stream.codec_context.name,
                    pixel_format=stream.codec_context.format.name if stream.codec_context.format else None)


def normalize(source, destination, ffmpeg=None, *, cancel=None, progress=None):
    """Preserve relative VFR timing and A/V offsets, physically apply orientation."""
    if ffmpeg is None:
        from imageio_ffmpeg import get_ffmpeg_exe
        ffmpeg = get_ffmpeg_exe()
    check_cancel(cancel)
    original = inspect_video(source)
    notify(progress,'import',None,'Video wird lokal für die Analyse vorbereitet …')
    command = [str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
               '-threads', '2', '-copyts', '-start_at_zero', '-i', str(source),
               '-map', '0:v:0', '-map', '0:a:0?', '-map_metadata', '-1', '-map_chapters', '-1',
               '-c:v', 'libx264', '-threads', '2', '-preset', 'fast', '-crf', '20',
               '-vf', 'scale=in_range=auto:out_range=tv,setsar=1', '-color_range', 'tv',
               '-pix_fmt', 'yuv420p', '-fps_mode', 'passthrough', '-enc_time_base:v', 'demux',
               '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart',
               '-fs', str(MAX_BYTES + 1), str(destination)]
    # Use a disk-backed log rather than retaining arbitrary stderr in memory.
    log = destination.with_suffix('.log')
    with log.open('w+b') as errors:
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=errors,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        started=time.monotonic()
        try:
            while process.poll() is None:
                check_cancel(cancel)
                if time.monotonic()-started>14400:
                    raise ValueError('FFmpeg-Zeitlimit überschritten; kein Export.')
                try:process.wait(timeout=.15)
                except subprocess.TimeoutExpired:pass
        except BaseException:
            if process.poll() is None:process.kill()
            process.wait()
            raise
        check_cancel(cancel)
        if process.returncode:
            errors.seek(max(0, errors.tell()-3000))
            raise ValueError('FFmpeg-Import fehlgeschlagen: '+errors.read().decode('utf-8', errors='replace'))
    if destination.stat().st_size > MAX_BYTES:
        raise ValueError('Normalisiertes Video überschreitet 900 MiB; kein gekürzter Export.')
    info = inspect_video(destination)
    if abs(info['duration'] - original['duration']) > .1:
        raise ValueError('Import hat die Videodauer verändert; kein gekürzter/verlängerter Export.')
    if info['codec'] != 'h264' or info['pixel_format'] != 'yuv420p':
        raise ValueError('Import entspricht nicht H.264/yuv420p.')
    notify(progress,'import',1.,'Videoimport abgeschlossen.')
    return info


def copy_prepared(source, destination, *, cancel=None, progress=None):
    """Reuse a GUI-normalized video without another lossy encode."""
    import av
    check_cancel(cancel)
    info=inspect_video(source)
    if source.stat().st_size>MAX_BYTES or info['codec']!='h264' or info['pixel_format']!='yuv420p':
        raise ValueError('Vorbereitetes Video entspricht nicht dem Analyseformat.')
    with av.open(str(source)) as container:
        stream=container.streams.video[0]
        if len(container.streams.video)!=1 or len(container.streams.audio)>1 or stream.sample_aspect_ratio!=1:
            raise ValueError('Vorbereitetes Video enthält unerwartete Spuren oder Pixelgeometrie.')
        if container.streams.audio and container.streams.audio[0].codec_context.name!='aac':
            raise ValueError('Vorbereitete Tonspur entspricht nicht AAC.')
        first=next(container.decode(stream),None)
        if first is None or first.rotation!=0:
            raise ValueError('Vorbereitetes Video ist leer oder nicht physisch aufrecht.')
    notify(progress,'import',None,'Vorbereitetes Video wird ohne neue Kodierung übernommen …')
    with source.open('rb') as src,destination.open('wb') as target:
        while block:=src.read(65536):
            check_cancel(cancel)
            target.write(block)
    return info


def frames(path):
    import av
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        stream.codec_context.thread_count = 2
        for frame in container.decode(stream):
            time = float(frame.pts * frame.time_base) if frame.pts is not None else None
            yield frame, time
