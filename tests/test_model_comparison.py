"""Selection safety, fair comparison timestamps, and offline preview contract."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import unittest
import zipfile

from analyzer.cli import analyze
from analyzer.compare_models import compare_models, diagnostic_frame, pose_metrics
from analyzer.pose import pack_pose
from analyzer.preview import write_preview
from analyzer.selection import PersonSelector, Selection

FIXTURE=Path(__file__).parent/'fixtures/synthetic.choreo'


def person(cx=.5,cy=.5,scale=1):
    image=[NS(x=cx+(.08 if j%2 else -.08)*scale,y=cy+(j-16)*.018*scale,
              visibility=1.,presence=1.) for j in range(33)]
    world=[NS(x=(p.x-cx),y=p.y-cy,z=0.) for p in image]
    return image,world


def result(*persons):
    return NS(pose_landmarks=[p[0] for p in persons],pose_world_landmarks=[p[1] for p in persons])


class SelectionTests(unittest.TestCase):
    def test_foreground_tracks_through_candidate_order_changes(self):
        selector=PersonSelector()
        main,reflection=person(),person(.8,.3,.4)
        first=selector.select(result(main,reflection),0)
        self.assertEqual(first.index,0)
        tracked=selector.select(result(reflection,person(.51)),.033)
        self.assertEqual(tracked.index,1)
        self.assertEqual(tracked.status,'tracked')
        self.assertEqual(pack_pose(tracked.result)[1],0)

    def test_equal_candidates_are_rejected_initially(self):
        decision=PersonSelector().select(result(person(.3),person(.7)),0)
        self.assertIsNone(decision.index)
        self.assertEqual(decision.status,'ambiguous')
        self.assertEqual(pack_pose(decision.result)[1],33)

    def test_jump_is_rejected_and_reacquisition_is_explicit(self):
        selector=PersonSelector()
        selector.select(result(person(.3)),0)
        rejected=selector.select(result(person(.85)),.033)
        self.assertEqual(rejected.status,'jump_rejected')
        reacquired=selector.select(result(person(.85)),1.)
        self.assertEqual(reacquired.status,'reacquired')

    def test_ambiguous_temporal_match_and_missing_torso(self):
        selector=PersonSelector()
        selector.select(result(person()),0)
        self.assertEqual(selector.select(result(person(.49),person(.51)),.033).status,'ambiguous')
        weak=person()
        for p in weak[0]:
            p.presence=.1
        self.assertEqual(selector.select(result(weak),.067).status,'missing')

    def test_strict_pack_pose_still_rejects_multiple_people(self):
        self.assertEqual(pack_pose(result(person(),person(.8,.3,.4)))[1],33)

    def test_diagnostics_show_discarded_candidates_and_never_write_nan(self):
        raw=result(person(),person(.8,.3,.4))
        raw.pose_landmarks[1][0].x=float('nan')
        decision=Selection(result(person()),0,2,'tracked')
        diagnostics=diagnostic_frame(1.,raw,decision)
        self.assertEqual(len(diagnostics['extras']),1)
        self.assertIsNone(diagnostics['extras'][0][0])
        json.dumps(diagnostics,allow_nan=False)


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.diagnostics=[dict(timestamp=t,selectedIndex=0,candidates=1,status='single',extras=[])
                          for t in (0.,.25,.5,.75)]

    def test_metrics_and_embedded_preview_match_package(self):
        metrics,rows=pose_metrics(FIXTURE,self.diagnostics)
        self.assertEqual(metrics['uncertainFrames'],0)
        self.assertEqual(metrics['usableBodyFrames'],4)
        self.assertEqual(len(rows),4)
        output=self.root/'preview.html'
        summary=dict(maxFps=0,models={name:dict(metrics,elapsedSeconds=1) for name in ('lite','full','heavy')})
        write_preview(output,[(name,FIXTURE,self.diagnostics) for name in summary['models']],summary)
        text=output.read_text(encoding='utf-8')
        payload=json.loads(text.split('<script id="payload" type="application/json">')[1].split('</script>')[0])
        self.assertEqual(len(payload['models']),3)
        self.assertIn('connect-src \'none\'',text)
        self.assertNotIn('fetch(',text)
        self.assertIn('reference.mp4',text)

    def test_preview_rejects_mismatched_model_timestamps(self):
        with zipfile.ZipFile(FIXTURE) as archive:
            payload={name:archive.read(name) for name in archive.namelist()}
        import struct
        payload['reference/timestamps.bin']=struct.pack('<4d',0,.2,.5,.75)
        manifest=json.loads(payload['manifest.json'])
        for name,meta in manifest['files'].items():
            meta.update(size=len(payload[name]),sha256=hashlib.sha256(payload[name]).hexdigest())
        payload['manifest.json']=json.dumps(manifest).encode()
        changed=self.root/'changed.choreo'
        with zipfile.ZipFile(changed,'w') as archive:
            for name,value in payload.items(): archive.writestr(name,value)
        with self.assertRaisesRegex(ValueError,'identische'):
            write_preview(self.root/'bad.html',[('lite',FIXTURE,self.diagnostics),('full',changed,self.diagnostics)],{})
        self.assertFalse((self.root/'bad.html').exists())

    def test_script_content_is_escaped(self):
        output=self.root/'safe.html'
        write_preview(output,[('lite',FIXTURE,self.diagnostics)],{'note':'</script><img src=x onerror=alert(1)>'})
        text=output.read_text(encoding='utf-8')
        self.assertNotIn('</script><img',text)
        payload=json.loads(text.split('<script id="payload" type="application/json">')[1].split('</script>')[0])
        self.assertEqual(payload['summary']['note'],'</script><img src=x onerror=alert(1)>')

    def test_compare_requires_all_local_models_and_preserves_existing_folder(self):
        with self.assertRaisesRegex(ValueError,'Modell fehlt'):
            compare_models(self.root/'video.mp4',self.root/'out',self.root)
        existing=self.root/'existing';existing.mkdir()
        with self.assertRaisesRegex(ValueError,'existiert bereits'):
            compare_models(self.root/'video.mp4',existing,self.root)

    def test_confirmed_single_person_mode_exports_foreground(self):
        source=self.root/'source.mp4'
        with zipfile.ZipFile(FIXTURE) as archive:
            source.write_bytes(archive.read('reference/video.mp4'))
        model=self.root/'test.task';model.write_bytes(b'fake')
        class Engine:
            identity=dict(name='synthetic-selection-test',version='1')
            backend='CPU'
            def __init__(self,*args):pass
            def detect(self,*args):return result(person(),person(.8,.3,.4))
            def close(self):pass
        _,strict=analyze(source,self.root/'strict.choreo',model,engine_factory=Engine)
        _,selected=analyze(source,self.root/'selected.choreo',model,single_person=True,engine_factory=Engine)
        self.assertEqual(strict['missingLandmarks'],132)
        self.assertEqual(selected['missingLandmarks'],0)

    def comparison_setup(self):
        source=self.root/'source.mp4'
        with zipfile.ZipFile(FIXTURE) as archive:
            source.write_bytes(archive.read('reference/video.mp4'))
        models=self.root/'models';models.mkdir()
        for name in ('lite','full','heavy'):
            (models/f'pose_landmarker_{name}.task').write_bytes(b'synthetic-test-model')
        class Engine:
            identity=dict(name='synthetic-comparison-test',version='1')
            backend='CPU'
            def __init__(self,*args):pass
            def detect(self,*args):return result(person())
            def close(self):pass
        return source,models,Engine

    def test_complete_three_model_pipeline(self):
        source,models,engine=self.comparison_setup()
        output=self.root/'comparison'
        summary=compare_models(source,output,models,single_person=True,engine_factory=engine)
        self.assertEqual(set(summary['models']),{'lite','full','heavy'})
        self.assertTrue((output/'vergleich.html').is_file())
        self.assertTrue((output/'reference.mp4').is_file())
        self.assertTrue((output/'bildervergleich.csv').is_file())
        for metrics in summary['models'].values():
            self.assertEqual(metrics['frames'],4)
            self.assertEqual(metrics['usableBodyPercent'],100)

    def test_middle_model_failure_publishes_no_partial_comparison(self):
        source,models,engine=self.comparison_setup()
        def factory(model,*args):
            if 'full' in model.name:raise RuntimeError('synthetic failure')
            return engine(model,*args)
        output=self.root/'failed'
        with self.assertRaisesRegex(RuntimeError,'synthetic failure'):
            compare_models(source,output,models,engine_factory=factory)
        self.assertFalse(output.exists())
        self.assertEqual(list(self.root.glob('.comparison-*')),[])


if __name__=='__main__':
    unittest.main()
