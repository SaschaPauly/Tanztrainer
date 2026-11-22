"""Phase 2 contract, VFR media and failure-path regressions; no network required."""
import math
from pathlib import Path
import struct
import subprocess
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import zipfile

from analyzer.analysis import Quality, Timeline
from analyzer.cli import analyze, main
from analyzer.pose import MISSING, PoseEngine, pack_pose
from analyzer.validate import validate
from analyzer.video import frames, normalize

FIXTURE = Path(__file__).parent/'fixtures/synthetic.choreo'


def pose():
    return NS(pose_landmarks=[[NS(x=.3+(j % 2)*.4, y=.2+j*.015, visibility=1., presence=1.) for j in range(33)]],
              pose_world_landmarks=[[NS(x=j*.01, y=j*.02, z=j*.03) for j in range(33)]])


class FakeEngine:
    identity = dict(name='synthetic-test-engine', version='1')
    backend = 'CPU'
    closed = False

    def __init__(self, *args):
        self.calls = []

    def detect(self, rgb, ms):
        self.calls.append(ms)
        return pose()

    def close(self):
        self.closed = True


class PoseTests(unittest.TestCase):
    def test_layout_and_hip_origin(self):
        data, missing, points = pack_pose(pose())
        self.assertEqual(len(data), 924)
        self.assertEqual(missing, 0)
        self.assertEqual(len(points), 33)
        rows = list(struct.iter_unpack('<7f', data))
        for axis in (2, 3, 4):
            self.assertAlmostEqual(rows[23][axis]+rows[24][axis], 0)

    def test_missing_confidence_world_and_out_of_frame(self):
        for attribute, value in [('presence', None), ('visibility', None), ('x', 1.1), ('y', math.inf)]:
            p = pose()
            setattr(p.pose_landmarks[0][0], attribute, value)
            data, missing, _ = pack_pose(p)
            self.assertEqual(data[:28], MISSING)
            self.assertEqual(missing, 1)
        p = pose()
        p.pose_world_landmarks = []
        self.assertEqual(pack_pose(p)[0], MISSING*33)

    def test_no_person_and_ambiguous_people(self):
        p = pose()
        for count in (0, 2):
            p.pose_landmarks = [pose().pose_landmarks[0]] * count
            self.assertEqual(pack_pose(p)[:2], (MISSING*33, 33))

    def test_low_confidence_is_retained(self):
        p = pose()
        p.pose_landmarks[0][0].presence = .1
        data, missing, points = pack_pose(p)
        self.assertEqual(missing, 0)
        self.assertEqual(len(points), 32)
        self.assertAlmostEqual(struct.unpack('<7f', data[:28])[-1], .1)

    def test_runtime_gpu_fallback_retries_same_frame(self):
        engine = PoseEngine.__new__(PoseEngine)
        engine.backend = 'GPU'
        engine.mp = NS(Image=lambda **kwargs: kwargs, ImageFormat=NS(SRGB=1))
        engine.task = NS(detect_for_video=lambda *args: (_ for _ in ()).throw(RuntimeError('GPU')))
        calls = []
        def fallback():
            engine.backend = 'CPU'
            engine.task = NS(detect_for_video=lambda image, ms: calls.append(ms) or pose())
        engine._fallback = fallback
        engine.detect(None, 123)
        self.assertEqual(calls, [123])

    def test_initialization_gpu_fallback_and_cpu_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            model = Path(folder)/'model.task'
            model.write_bytes(b'test')
            warnings, backends = [], []
            def create(engine):
                backends.append(engine.backend)
                if engine.backend == 'GPU':
                    raise RuntimeError('unsupported')
                return NS(close=lambda: None)
            with patch.object(PoseEngine, '_create', create):
                engine = PoseEngine(model, 'auto', warnings.append)
                engine.close()
            self.assertEqual(backends, ['GPU', 'CPU'])
            self.assertEqual(len(warnings), 1)
            with patch.object(PoseEngine, '_create', side_effect=RuntimeError('CPU failed')):
                with self.assertRaisesRegex(RuntimeError, 'CPU failed'):
                    PoseEngine(model, 'cpu', warnings.append)


class TimelineZoomTests(unittest.TestCase):
    def test_vfr_pts_and_sampling(self):
        timeline = Timeline(0)
        values = [0., .041, .110, .111, .352]
        self.assertEqual([t for t in values if timeline.accept(t)], values)
        timeline = Timeline(10)
        self.assertEqual([t for t in values if timeline.accept(t)], [0., .110, .352])

    def test_bad_pts_rejected(self):
        for t in (None, -1., math.inf, math.nan):
            with self.assertRaises(ValueError):
                Timeline(0).accept(t)
        timeline = Timeline(0)
        timeline.accept(.1)
        with self.assertRaises(ValueError):
            timeline.accept(.1)

    def test_model_milliseconds_do_not_change_export_time(self):
        timeline = Timeline(0)
        for t in (0., .0001, .0002):
            timeline.accept(t)
        self.assertEqual(timeline.selected, .0002)
        self.assertEqual(timeline.model_ms, 2)

    def test_crop_contains_full_motion_and_expands_only(self):
        quality = Quality()
        points = [(x, y) for x, y in ((.3,.2),(.7,.8))] + [(.5,.5)]*31
        quality.observe(0, 0, points, 1)
        quality.observe(.1, 0, [(.2,.15)]*33, 1)
        for aspect in (.1, 9/16, 16/9, 10):
            zoom = quality.zoom(1920, 1080, aspect)
            self.assertLessEqual(zoom['x'], .2)
            self.assertLessEqual(zoom['y'], .15)
            self.assertGreaterEqual(zoom['x']+zoom['width'], .7)
            self.assertGreaterEqual(zoom['y']+zoom['height'], .8)
            self.assertLessEqual(zoom['x']+zoom['width'], 1)
            self.assertLessEqual(zoom['y']+zoom['height'], 1)

    def test_quality_counts_and_zoom_fallback(self):
        quality = Quality()
        quality.observe(.3, 33, [], 0)
        quality.observe(1.4, 1, [(.5,.5)]*32, 1)
        zoom = quality.zoom(100, 100, 1)
        self.assertEqual((zoom['x'], zoom['y'], zoom['width'], zoom['height']), (0,0,1,1))
        report = quality.report()
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(report['missingLandmarks'], 34)
        self.assertTrue(any('0.300' in text and '1.400' in text for text in report['warnings']))

    def zoom_sequence(self, bad_indices, *, count=100, tolerance=10):
        quality = Quality(tolerance)
        points = [(.35,.2),(.65,.8)] + [(.5,.5)]*31
        for index in range(count):
            quality.observe(index/30, 1 if index in bad_indices else 0,
                            points[:-1] if index in bad_indices else points, 1)
        return quality, quality.zoom(1000, 1000, 1)

    def test_ten_percent_inclusive_and_next_frame_rejected(self):
        bad = set(range(5,100,10))
        quality, crop = self.zoom_sequence(bad)
        self.assertLess(crop['width'], 1)
        self.assertLess(crop['height'], 1)
        self.assertEqual(quality.missing, 10)
        _, over = self.zoom_sequence(bad | {2})
        self.assertEqual((over['width'], over['height']), (1,1))

    def test_strict_zero_and_invalid_tolerances(self):
        _, crop = self.zoom_sequence({5}, tolerance=0)
        self.assertEqual(crop['width'], 1)
        for tolerance in (-1,101,math.nan,math.inf):
            with self.assertRaises(ValueError):
                Quality(tolerance)

    def test_long_uncertain_run_falls_back_below_percentage_limit(self):
        quality, crop = self.zoom_sequence(set(range(50,70)), count=200)
        self.assertEqual(crop['width'], 1)
        self.assertTrue(any('zusammenhängende' in warning for warning in quality.warnings))

    def test_tolerated_missing_points_keep_reliable_extrema(self):
        quality = Quality()
        points = [(.4,.2),(.6,.8)] + [(.5,.5)]*31
        for index in range(10):
            current = [(.15,.5)]+points[1:-1] if index == 5 else points
            quality.observe(index/30, 1 if index == 5 else 0, current, 1)
        crop = quality.zoom(1000,1000,1)
        self.assertLess(crop['width'], 1)
        self.assertLessEqual(crop['x'], .15)
        self.assertGreaterEqual(crop['x']+crop['width'], .6)
        self.assertLessEqual(crop['y'], .2)
        self.assertGreaterEqual(crop['y']+crop['height'], .8)

    def test_border_and_timestamp_gaps_remain_hard_fallbacks(self):
        for timestamp, point in ((.1,(.01,.5)), (1.,(.5,.5))):
            quality = Quality()
            quality.observe(0,0,[(.5,.5)]*33,1)
            quality.observe(timestamp,0,[point]*33,1)
            crop = quality.zoom(1000,1000,1)
            self.assertEqual(crop['width'], 1)

    def test_uncertainty_uses_frame_union_without_double_counting(self):
        quality = Quality()
        for index in range(10):
            quality.observe(index/30,33 if index == 5 else 0,
                            [] if index == 5 else [(.4,.2),(.6,.8)]+[(.5,.5)]*31,
                            2 if index == 5 else 1)
        crop = quality.zoom(1000,1000,1)
        self.assertEqual(quality.uncertain_frames, 1)
        self.assertLess(crop['width'], 1)


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root/'Tanz ü leer.mp4'
        with zipfile.ZipFile(FIXTURE) as archive:
            self.source.write_bytes(archive.read('reference/video.mp4'))
        self.model = self.root/'test.task'
        self.model.write_bytes(b'test-only')
        self.output = self.root/'Tanz ü leer.choreo'

    def analyze(self, **kwargs):
        return analyze(self.source, self.output, self.model, engine_factory=FakeEngine, **kwargs)

    def ffmpeg(self, args):
        from imageio_ffmpeg import get_ffmpeg_exe
        subprocess.run([get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-y', *map(str, args)], check=True)

    def test_end_to_end_valid_export(self):
        manifest, quality = self.analyze()
        self.assertEqual(manifest, validate(self.output))
        self.assertEqual(manifest['frameCount'], 4)
        self.assertEqual(quality['missingLandmarks'], 0)
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(len(archive.namelist()), 7)
            self.assertEqual(struct.unpack('<4d', archive.read('reference/timestamps.bin')), (0,.25,.5,.75))
        self.assertEqual(list(self.root.glob('.analysis-*')), [])

    def test_vfr_timestamps_and_audio_offset_preserved(self):
        source = self.root/'vfr.mp4'
        self.ffmpeg(['-f','lavfi','-i','color=c=blue:s=160x120:r=10:d=1',
                     '-itsoffset','0.2','-f','lavfi','-i','sine=frequency=440:duration=0.7',
                     '-vf',"setpts='if(lt(N,4),N/(10*TB),(0.4+(N-4)*0.2)/TB)'",
                     '-fps_mode','passthrough','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',source])
        target = self.root/'normalized.mp4'
        normalize(source, target)
        times_before = [time for _, time in frames(source)]
        times_after = [time for _, time in frames(target)]
        self.assertEqual(len(times_before), len(times_after))
        for before, after in zip(times_before, times_after):
            self.assertAlmostEqual(before, after, places=4)
        self.assertGreater(len(set(round(b-a, 3) for a,b in zip(times_after,times_after[1:]))), 1)
        import av
        offsets = []
        for path in (source, target):
            with av.open(str(path)) as container:
                audio = container.streams.audio[0]
                offsets.append(float(audio.start_time * audio.time_base))
        self.assertLess(abs(offsets[0]-offsets[1]), .03)  # AAC priming, within one audio frame
        self.source = source
        manifest, _ = self.analyze()
        self.assertEqual(manifest['audio']['source'], 'reference/video.mp4')
        with zipfile.ZipFile(self.output) as archive:
            exported = list(struct.iter_unpack('<d', archive.read('reference/timestamps.bin')))
        self.assertEqual([t[0] for t in exported], times_after)

    def test_physical_rotation(self):
        rotated = self.root/'rotated.mp4'
        self.ffmpeg(['-display_rotation','90','-i',self.source,'-c','copy',rotated])
        info = normalize(rotated, self.root/'upright.mp4')
        self.assertEqual((info['width'], info['height']), (120,160))

    def test_subframe_pts_precision_is_preserved(self):
        source = self.root/'precise-pts.mp4'
        self.ffmpeg(['-f','lavfi','-i','color=c=blue:s=160x120:r=30:d=1',
                     '-vf',"settb=1/600,setpts='PTS+if(gte(N,4),3,0)'",
                     '-c:v','libx264','-pix_fmt','yuv420p','-enc_time_base:v','1:600',
                     '-fps_mode','passthrough',source])
        target = self.root/'precise-normalized.mp4'
        normalize(source, target)
        before = [time for _, time in frames(source)]
        after = [time for _, time in frames(target)]
        self.assertAlmostEqual(before[4]-before[3], 1/30+.005, places=6)
        self.assertEqual(len(before), len(after))
        for a, b in zip(before, after):
            self.assertAlmostEqual(a, b, places=6)

    def test_sampling_forces_conservative_zoom(self):
        manifest, _ = self.analyze(max_fps=2)
        self.assertEqual(manifest['frameCount'], 2)
        self.assertEqual(manifest['zoom']['width'], 1)

    def test_tolerated_uncertainty_exports_valid_partial_without_pose_changes(self):
        source = self.root/'ten-frames.mp4'
        self.ffmpeg(['-f','lavfi','-i','color=c=blue:s=160x120:r=10:d=1',
                     '-c:v','libx264','-pix_fmt','yuv420p',source])
        self.source = source
        results = [pose() for _ in range(10)]
        results[5].pose_landmarks[0][0].presence = None
        expected = b''.join(pack_pose(result)[0] for result in results)
        with patch.object(FakeEngine,'detect',side_effect=results):
            manifest, quality = self.analyze(aspect=1)
        self.assertLess(manifest['zoom']['width'],1)
        self.assertEqual(quality['status'],'partial')
        self.assertEqual(quality['missingLandmarks'],1)
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(archive.read('reference/poses.bin'), expected)
        validate(self.output)

    def test_failure_and_cancellation_leave_existing_output(self):
        self.output.write_bytes(b'previous')
        for exc in (RuntimeError('inference failed'), KeyboardInterrupt()):
            with patch.object(FakeEngine, 'detect', side_effect=exc):
                with self.assertRaises(type(exc)):
                    self.analyze(overwrite=True)
            self.assertEqual(self.output.read_bytes(), b'previous')
            self.assertEqual(list(self.root.glob('.analysis-*')), [])

    def test_no_clobber_and_bad_arguments(self):
        self.output.write_bytes(b'previous')
        with self.assertRaisesRegex(ValueError, 'existiert'):
            self.analyze()
        for args in ({'max_fps':math.nan}, {'aspect':-1}, {'max_side':0}, {'title':''}):
            with self.assertRaises(ValueError):
                self.analyze(overwrite=True, **args)

    def test_corrupt_video_and_missing_model(self):
        self.source.write_bytes(b'broken')
        with self.assertRaises(Exception):
            self.analyze()
        self.assertFalse(self.output.exists())
        self.model.unlink()
        with self.assertRaisesRegex(ValueError, 'fehlt'):
            self.analyze()

    def test_export_validation_failure_is_atomic(self):
        with patch('analyzer.export.validate', side_effect=ValueError('invalid')):
            with self.assertRaisesRegex(ValueError, 'invalid'):
                self.analyze()
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob('.choreo-*')), [])

    def test_cli_failure_exit_code(self):
        with self.assertRaises(SystemExit) as result:
            main([str(self.source), str(self.output), '--model', str(self.root/'missing.task')])
        self.assertEqual(result.exception.code, 1)

    def test_missing_person_quality_and_binary_agree(self):
        with patch.object(FakeEngine, 'detect', return_value=NS(pose_landmarks=[], pose_world_landmarks=[])):
            manifest, quality = self.analyze()
        self.assertEqual(quality['missingLandmarks'], manifest['frameCount']*33)
        self.assertEqual(quality['status'], 'partial')
        validate(self.output)

    def test_full_range_video_is_normalized(self):
        source = self.root/'fullrange.mp4'
        self.ffmpeg(['-f','lavfi','-i','color=c=blue:s=160x120:r=4:d=1',
                     '-c:v','libx264','-pix_fmt','yuv420p','-color_range','pc',source])
        info = normalize(source, self.root/'limited.mp4')
        self.assertEqual(info['pixel_format'], 'yuv420p')

    def test_package_budget_aborts_without_export(self):
        with patch.dict('analyzer.cli.SPEC', {'limits': {'archiveBytes': 100}}):
            with self.assertRaisesRegex(ValueError, 'Paketlimit'):
                self.analyze()
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob('.analysis-*')), [])

    def test_non_square_pixels_rejected(self):
        source = self.root/'anamorphic.mp4'
        self.ffmpeg(['-i',self.source,'-vf','setsar=2','-c:v','libx264',source])
        with self.assertRaisesRegex(ValueError, 'Nichtquadratische'):
            normalize(source, self.root/'normalized.mp4')

    def test_unspecified_pixel_aspect_ratio_is_accepted(self):
        import av
        from analyzer.video import inspect_video
        source = self.root/'unspecified-sar.mp4'
        self.ffmpeg(['-i',self.source,'-vf','setsar=0','-c:v','libx264',source])
        with av.open(str(source)) as container:
            self.assertEqual(container.streams.video[0].sample_aspect_ratio, 0)
        self.assertEqual(inspect_video(source)['width'], 160)
        self.source = source
        manifest, _ = self.analyze()
        self.assertEqual((manifest['video']['width'], manifest['video']['height']), (160,120))
        validate(self.output)
        target = self.root/'exported.mp4'
        with zipfile.ZipFile(self.output) as archive:
            target.write_bytes(archive.read('reference/video.mp4'))
        with av.open(str(target)) as container:
            self.assertEqual(container.streams.video[0].sample_aspect_ratio, 1)
        self.assertEqual([time for _, time in frames(source)], [time for _, time in frames(target)])

    def test_no_clobber_if_output_appears_during_export(self):
        from analyzer.validate import validate as real_validate
        def race(path):
            result = real_validate(path)
            self.output.write_bytes(b'another process')
            return result
        with patch('analyzer.export.validate', side_effect=race):
            with self.assertRaises(FileExistsError):
                self.analyze()
        self.assertEqual(self.output.read_bytes(), b'another process')


if __name__ == '__main__':
    unittest.main()
