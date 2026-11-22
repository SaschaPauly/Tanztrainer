"""MediaPipe Tasks adapter and strict conversion to the existing binary contract."""
import hashlib
import math
import struct
from importlib.metadata import version

MISSING = struct.pack('<5I2f', *([0x7fc00000] * 5), 0, 0)


def pack_pose(result):
    """Return bytes, missing count, and reliable image points; never invent confidence."""
    image, world = result.pose_landmarks, result.pose_world_landmarks
    if len(image) != 1 or len(world) != 1 or len(image[0]) != 33 or len(world[0]) != 33:
        return MISSING * 33, 33, []
    chunks, points, missing = [], [], 0
    # Explicitly re-center the estimated world pose on the hip midpoint.
    hips = world[0][23:25]
    center = [(getattr(hips[0], k) + getattr(hips[1], k)) / 2 for k in ('x', 'y', 'z')]
    for i, w in zip(image[0], world[0]):
        values = [i.x, i.y, w.x-center[0], w.y-center[1], w.z-center[2],
                  getattr(i, 'visibility', None), getattr(i, 'presence', None)]
        valid = all(isinstance(v, (int, float)) and math.isfinite(v) for v in values)
        valid = valid and all(0 <= values[k] <= 1 for k in (0, 1, 5, 6))
        try:
            record = struct.pack('<7f', *values) if valid else MISSING
            valid = valid and all(math.isfinite(v) for v in struct.unpack('<7f', record))
        except (OverflowError, struct.error):
            valid = False
        if not valid:
            chunks.append(MISSING)
            missing += 1
        else:
            chunks.append(record)
            if min(values[5:]) >= .5:
                points.append((values[0], values[1]))
    return b''.join(chunks), missing, points


class PoseEngine:
    """Try GPU where available, retry CPU on initialization or inference failure."""
    def __init__(self, model, backend, warn):
        import mediapipe as mp
        self.mp, self.model, self.warn = mp, str(model), warn
        self.backend = 'CPU' if backend == 'cpu' else 'GPU'
        hasher = hashlib.sha256()
        with model.open('rb') as stream:
            for block in iter(lambda: stream.read(65536), b''):
                hasher.update(block)
        digest = hasher.hexdigest()
        self.identity = {'name': 'MediaPipe Pose Landmarker 33',
                         'version': f'{version("mediapipe")};sha256:{digest}'}
        self.task = None
        try:
            self.task = self._create()
        except Exception:
            if self.backend == 'CPU':
                raise
            self._fallback()

    def _create(self):
        base = self.mp.tasks.BaseOptions
        vision = self.mp.tasks.vision
        return vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
            base_options=base(model_asset_path=self.model, delegate=getattr(base.Delegate, self.backend)),
            running_mode=vision.RunningMode.VIDEO, num_poses=2,
            output_segmentation_masks=False))

    def _fallback(self):
        self.warn('GPU nicht verfügbar/fehlgeschlagen; Analyse wird auf CPU fortgesetzt.')
        if self.task is not None:
            self.task.close()
        self.backend = 'CPU'
        self.task = self._create()

    def detect(self, rgb, milliseconds):
        image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
        try:
            return self.task.detect_for_video(image, milliseconds)
        except Exception:
            if self.backend == 'CPU':
                raise
            self._fallback()
            return self.task.detect_for_video(image, milliseconds)

    def close(self):
        if self.task is not None:
            self.task.close()
