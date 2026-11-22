"""Local codec normalization and bounded sequential decoding using actual PTS."""
import subprocess

MAX_BYTES = 900 * 1024 * 1024  # leave room for binary data and ZIP headers
MAX_PIXELS = 4096 * 2160


def inspect_video(path):
    import av
    with av.open(str(path)) as container:
        if not container.streams.video:
            raise ValueError('Datei enthält keine Videospur.')
        stream = container.streams.video[0]
        if stream.sample_aspect_ratio not in (None, 1):
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


def normalize(source, destination, ffmpeg=None):
    """Preserve relative VFR timing and A/V offsets, physically apply orientation."""
    if ffmpeg is None:
        from imageio_ffmpeg import get_ffmpeg_exe
        ffmpeg = get_ffmpeg_exe()
    original = inspect_video(source)
    command = [str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
               '-threads', '2', '-copyts', '-start_at_zero', '-i', str(source),
               '-map', '0:v:0', '-map', '0:a:0?', '-map_metadata', '-1', '-map_chapters', '-1',
               '-c:v', 'libx264', '-threads', '2', '-preset', 'fast', '-crf', '20',
               '-vf', 'scale=in_range=auto:out_range=tv', '-color_range', 'tv',
               '-pix_fmt', 'yuv420p', '-fps_mode', 'passthrough',
               '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart',
               '-fs', str(MAX_BYTES + 1), str(destination)]
    # Use a disk-backed log rather than retaining arbitrary stderr in memory.
    log = destination.with_suffix('.log')
    with log.open('w+b') as errors:
        try:
            completed = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=errors,
                                       timeout=14400, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except subprocess.TimeoutExpired as exc:
            raise ValueError('FFmpeg-Zeitlimit überschritten; kein Export.') from exc
        if completed.returncode:
            errors.seek(max(0, errors.tell()-3000))
            raise ValueError('FFmpeg-Import fehlgeschlagen: '+errors.read().decode('utf-8', errors='replace'))
    if destination.stat().st_size > MAX_BYTES:
        raise ValueError('Normalisiertes Video überschreitet 900 MiB; kein gekürzter Export.')
    info = inspect_video(destination)
    if abs(info['duration'] - original['duration']) > .1:
        raise ValueError('Import hat die Videodauer verändert; kein gekürzter/verlängerter Export.')
    if info['codec'] != 'h264' or info['pixel_format'] != 'yuv420p':
        raise ValueError('Import entspricht nicht H.264/yuv420p.')
    return info


def frames(path):
    import av
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        stream.codec_context.thread_count = 2
        for frame in container.decode(stream):
            time = float(frame.pts * frame.time_base) if frame.pts is not None else None
            yield frame, time
