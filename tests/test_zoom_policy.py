"""30% zoom budget and separate clocks for local occlusion vs body/identity loss."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from analyzer.analysis import Quality
from analyzer.pose import MISSING
from analyzer.rezoom import complete_frame_coverage, recompute_zoom
from analyzer.validate import validate

FIXTURE = Path(__file__).parent/'fixtures/synthetic.choreo'


def pose(weak=(), absent=()):
    rows=[]
    for index in range(33):
        if index in absent:
            rows.append(MISSING)
        else:
            x=.35+.3*(index%2); y=.2+.6*index/32
            rows.append(struct.pack('<7f',x,y,x-.5,y-.5,0,.2 if index in weak else 1,1))
    return b''.join(rows)


class ZoomPolicyTests(unittest.TestCase):
    def sequence(self,bad,*,count=100,weak=(21,),absent=(),people=1):
        quality=Quality()
        for i in range(count):
            data=pose(weak,absent) if i in bad else pose()
            quality.observe_pose(i/30,data,people if i in bad else 1)
        return quality,quality.zoom(1000,1000,1)

    def test_default_thirty_percent_inclusive_and_next_image_fails(self):
        bad=set(range(5,95,3))
        self.assertEqual(len(bad),30)
        quality,crop=self.sequence(bad)
        self.assertEqual(quality.zoom_max_uncertain_percent,30)
        self.assertEqual(quality.uncertain_frames,30)
        self.assertLess(crop['width'],1)
        _,over=self.sequence(bad|{0})
        self.assertEqual(over['width'],1)

    def test_long_occluded_finger_does_not_block_zoom_with_visible_torso(self):
        quality,crop=self.sequence(set(range(40,85)),count=200)
        self.assertGreater(quality.longest_partial_seconds,1)
        self.assertEqual(quality.longest_critical_seconds,0)
        self.assertLess(crop['width'],1)
        self.assertEqual(quality.report()['status'],'complete')

    def test_one_missing_torso_point_keeps_three_visible_anchors(self):
        quality,crop=self.sequence(set(range(40,85)),count=200,weak=(),absent=(11,))
        self.assertLess(crop['width'],1)
        self.assertEqual(quality.missing,45)
        self.assertEqual(quality.longest_critical_seconds,0)

    def test_lost_torso_still_falls_back_even_within_thirty_percent(self):
        quality,crop=self.sequence(set(range(40,85)),count=200,weak=(11,12))
        self.assertGreater(quality.longest_critical_seconds,1)
        self.assertEqual(crop['width'],1)

    def test_missing_whole_pose_and_ambiguous_identity_are_critical(self):
        for absent,people in ((tuple(range(33)),1),((),2)):
            quality,crop=self.sequence(set(range(40,65)),count=200,weak=(),absent=absent,people=people)
            self.assertGreater(quality.longest_critical_seconds,.5)
            self.assertEqual(crop['width'],1)

    def test_partial_runs_do_not_extend_short_body_loss_clock(self):
        quality=Quality()
        for i in range(200):
            if 40<=i<=42:data=pose(weak=(11,12))
            elif 20<=i<=62:data=pose(weak=(21,))
            else:data=pose()
            quality.observe_pose(i/30,data)
        crop=quality.zoom(1000,1000,1)
        self.assertGreater(quality.longest_uncertain_seconds,1)
        self.assertLess(quality.longest_critical_seconds,.2)
        self.assertLess(crop['width'],1)

    def test_critical_half_second_boundary(self):
        for recovery,expect_crop in ((.5,True),(.501,False)):
            quality=Quality(100)
            quality.observe_pose(0,pose())
            for t in (.1,.2,.3,.4):quality.observe_pose(t,pose(weak=(11,12)))
            quality.observe_pose(recovery,pose())
            crop=quality.zoom(1000,1000,1)
            self.assertEqual(crop['width']<1,expect_crop)


class RezoomTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.output=self.root/'new.choreo'

    def test_rezoom_preserves_binary_media_and_source(self):
        before=hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        manifest,report=recompute_zoom(FIXTURE,self.output)
        validate(self.output)
        with zipfile.ZipFile(FIXTURE) as a,zipfile.ZipFile(self.output) as b:
            for name in ('reference/video.mp4','reference/poses.bin','reference/timestamps.bin','assets/preview.jpg'):
                self.assertEqual(a.read(name),b.read(name))
            original=json.loads(a.read('manifest.json'))
            for key in ('title','durationSeconds','frameCount','model','video','audio','layout','coordinateSystem'):
                self.assertEqual(manifest[key],original[key])
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),before)
        self.assertTrue(any('Toleranz 30' in w for w in report['warnings']))

    def test_nonzero_audio_offset_is_preserved(self):
        with zipfile.ZipFile(FIXTURE) as archive:
            payload={n:archive.read(n) for n in archive.namelist()}
        m=json.loads(payload['manifest.json']);m['audio']['offsetSeconds']=.4
        payload['manifest.json']=json.dumps(m).encode()
        source=self.root/'offset.choreo'
        with zipfile.ZipFile(source,'w') as archive:
            for name,data in payload.items():archive.writestr(name,data)
        manifest,_=recompute_zoom(source,self.output)
        self.assertEqual(manifest['audio']['offsetSeconds'],.4)

    def test_incomplete_frame_coverage_keeps_full_image(self):
        with patch('analyzer.rezoom.complete_frame_coverage',return_value=False):
            manifest,report=recompute_zoom(FIXTURE,self.output)
        self.assertEqual((manifest['zoom']['width'],manifest['zoom']['height']),(1,1))
        self.assertTrue(any('Abtastung' in w for w in report['warnings']))
        with zipfile.ZipFile(FIXTURE) as archive:
            payload={n:archive.read(n) for n in archive.namelist()}
        old=json.loads(payload['reference/quality.json'])
        old['warnings'].append('Zeitliche Abtastung auf höchstens 4 fps; Zoom bleibt sicherheitshalber Ganzbild.')
        raw=json.dumps(old).encode();payload['reference/quality.json']=raw
        m=json.loads(payload['manifest.json'])
        m['files']['reference/quality.json'].update(size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        payload['manifest.json']=json.dumps(m).encode()
        source=self.root/'declared-sampling.choreo'
        with zipfile.ZipFile(source,'w') as archive:
            for name,data in payload.items():archive.writestr(name,data)
        manifest,_=recompute_zoom(source,self.root/'sampled-output.choreo')
        self.assertEqual(manifest['zoom']['width'],1)

    def test_coverage_check_rejects_real_omitted_frames(self):
        video=self.root/'video.mp4';times=self.root/'times.bin'
        with zipfile.ZipFile(FIXTURE) as archive:
            video.write_bytes(archive.read('reference/video.mp4'))
            times.write_bytes(archive.read('reference/timestamps.bin'))
        self.assertTrue(complete_frame_coverage(video,times))
        times.write_bytes(struct.pack('<2d',0,.5))
        self.assertFalse(complete_frame_coverage(video,times))

    def test_existing_output_and_in_place_rezoom_are_rejected(self):
        self.output.write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError,'existiert'):
            recompute_zoom(FIXTURE,self.output)
        self.assertEqual(self.output.read_bytes(),b'keep')
        with self.assertRaisesRegex(ValueError,'separate'):
            recompute_zoom(FIXTURE,FIXTURE,overwrite=True)


if __name__=='__main__':unittest.main()
