"""Desktop lifecycle and cancellation contracts, without Qt or network."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import zipfile

from analyzer.cli import analyze
from analyzer.export_poses import export_poses
from analyzer.gui_backend import prepare_input, open_package, save_package, read_frame
from analyzer.runtime import AnalysisCancelled
from analyzer.selection import PersonSelector
from analyzer.video import normalize
from test_analyzer import FakeEngine
from test_model_comparison import person, result

FIXTURE=Path(__file__).parent/'fixtures/synthetic.choreo'


class DesktopBackendTests(unittest.TestCase):
    def test_cancel_normalization_kills_and_reaps_only_owned_ffmpeg(self):
        state={'calls':0,'killed':False,'waited':False}
        def cancel():
            state['calls']+=1
            return state['calls']>=2
        process=SimpleNamespace(poll=lambda:None,
            kill=lambda:state.update(killed=True),wait=lambda:state.update(waited=True))
        with tempfile.TemporaryDirectory() as directory,patch('analyzer.video.inspect_video',return_value={}),patch('analyzer.video.subprocess.Popen',return_value=process):
            with self.assertRaises(AnalysisCancelled):normalize(Path('source'),Path(directory)/'video.mp4',ffmpeg='ffmpeg',cancel=cancel)
        self.assertTrue(state['killed']);self.assertTrue(state['waited'])
    def test_exact_frame_decode_matches_every_recorded_pts(self):
        session=open_package(FIXTURE)
        try:
            for index in range(session.frame_count):
                time=session.timestamp(index);frame=read_frame(session.video,time)
                self.assertEqual(frame['seconds'],time)
                self.assertEqual(len(frame['pixels']),160*120*3)
            with self.assertRaises(ValueError):read_frame(session.video,.1)
            with self.assertRaises(AnalysisCancelled):read_frame(session.video,0,cancel=lambda:True)
        finally:session.close()
    def test_mapped_frames_use_recorded_timestamps_and_cleanup(self):
        session=open_package(FIXTURE)
        directory=Path(session.workspace.name)
        self.assertEqual(session.frame_count,4)
        self.assertIsNone(session.frame_at(-.1))
        self.assertEqual(session.frame_at(.249),0)
        self.assertEqual(session.frame_at(.25),1)
        self.assertEqual(session.frame_at(99),3)
        self.assertEqual(len(session.pose(2)),33)
        self.assertEqual(len(session.pose(2)[0]),7)
        session.close();session.close()
        self.assertFalse(directory.exists())

    def test_invalid_package_never_creates_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'bad.choreo';path.write_bytes(b'bad')
            with patch('analyzer.gui_backend.tempfile.TemporaryDirectory') as factory:
                with self.assertRaises(Exception):open_package(path)
                factory.assert_not_called()

    def test_save_is_byte_identical_and_guards_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'copy.choreo'
            save_package(FIXTURE,output)
            self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).digest(),hashlib.sha256(output.read_bytes()).digest())
            with self.assertRaises(ValueError):save_package(FIXTURE,output)
            with self.assertRaises(ValueError):save_package(output,output,overwrite=True)

    def test_cancel_during_save_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'existing.choreo';output.write_bytes(b'original')
            calls=[]
            def cancel():calls.append(1);return len(calls)>=3
            with self.assertRaises(AnalysisCancelled):save_package(FIXTURE,output,overwrite=True,cancel=cancel)
            self.assertEqual(output.read_bytes(),b'original')
            self.assertEqual(list(Path(directory).iterdir()),[output])

    def test_cancel_point_export_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'points'
            calls=[]
            def cancel():calls.append(1);return len(calls)>=3
            with self.assertRaises(AnalysisCancelled):export_poses(FIXTURE,output,cancel=cancel)
            self.assertEqual(list(Path(directory).iterdir()),[])

    def test_cancel_import_and_analysis_clean_owned_work(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source.mp4';model=root/'model.task'
            with zipfile.ZipFile(FIXTURE) as archive:source.write_bytes(archive.read('reference/video.mp4'))
            model.write_bytes(b'test')
            with self.assertRaises(AnalysisCancelled):prepare_input(source,cancel=lambda:True)
            output=root/'result.choreo'
            calls=[]
            def progress(stage,fraction,message):
                if stage=='analysis':calls.append(stage)
            with self.assertRaises(AnalysisCancelled):
                analyze(source,output,model,engine_factory=FakeEngine,cancel=lambda:bool(calls),progress=progress)
            self.assertFalse(output.exists());self.assertFalse(list(root.glob('.analysis-*')))

    def test_prepared_video_is_not_encoded_again(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source.mp4';model=root/'model.task'
            with zipfile.ZipFile(FIXTURE) as archive:source.write_bytes(archive.read('reference/video.mp4'))
            model.write_bytes(b'test')
            prepared=prepare_input(source)
            try:
                with patch('analyzer.cli.normalize',side_effect=AssertionError('double encode')):
                    analyze(source,root/'result.choreo',model,prepared_video=prepared.video,engine_factory=FakeEngine)
                with zipfile.ZipFile(root/'result.choreo') as archive:
                    self.assertEqual(archive.read('reference/video.mp4'),prepared.video.read_bytes())
            finally:prepared.close()

    def test_manual_selection_chooses_marked_equal_size_person(self):
        selected=PersonSelector(target_point=(.7,.53)).select(result(person(.3),person(.7)),0)
        self.assertEqual(selected.index,1);self.assertEqual(selected.status,'manual')

    def test_manual_selection_never_resets_to_larger_distant_person(self):
        selector=PersonSelector(target_point=(.2,.53))
        self.assertEqual(selector.select(result(person(.2)),0).index,0)
        self.assertEqual(selector.select(result(person(.9)),3).status,'jump_rejected')

    def test_manual_selection_rejects_ambiguous_and_far_seeds(self):
        self.assertEqual(PersonSelector((.5,.53)).select(result(person(.49),person(.51)),0).status,'ambiguous')
        self.assertEqual(PersonSelector((.01,.01)).select(result(person(.8)),0).status,'target_unmatched')
        for point in ((1.1,0),(0,float('nan')),(0,),('a',0)):
            with self.assertRaises(ValueError):PersonSelector(point)


if __name__=='__main__':unittest.main()
