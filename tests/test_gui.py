"""Qt lifecycle and timing tests; run with requirements-gui installed."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from analyzer.gui import MainWindow
from analyzer.gui_backend import open_package
from analyzer.runtime import check_cancel
from analyzer.cli import analyze
from test_analyzer import FakeEngine

FIXTURE=Path(__file__).parent/'fixtures/synthetic.choreo'
APP=QApplication.instance() or QApplication([])


def finish(window):
    deadline=time.monotonic()+10
    while window.worker is not None and time.monotonic()<deadline:
        APP.processEvents();time.sleep(.005)
    if window.worker is not None:raise AssertionError('Background job did not finish')


class DesktopGuiTests(unittest.TestCase):
    def setUp(self):self.window=MainWindow()
    def tearDown(self):
        self.window.unsaved=False;self.window.close()
        if self.window.worker is not None:finish(self.window)
        QTest.qWait(100)

    def test_defaults_and_open_existing_without_inference(self):
        w=self.window
        self.assertEqual(w.backend.currentText(),'cpu');self.assertEqual(w.percent.value(),30)
        self.assertFalse(w.single_person.isChecked());self.assertFalse(w.analyze_button.isEnabled())
        with patch('analyzer.gui.analyze_prepared',side_effect=AssertionError('inference')):
            w.load_package(FIXTURE);finish(w)
        self.assertEqual(w.session.frame_count,4)
        self.assertTrue(w.save_button.isEnabled());self.assertFalse(w.unsaved)
        self.assertIn('fester Ausschnitt',w.quality.toPlainText())

    def test_import_analyze_review_save_and_points_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'input.mp4';model=root/'model.task'
            package=open_package(FIXTURE)
            source.write_bytes(package.video.read_bytes());package.close();model.write_bytes(b'test')
            w=self.window;w.import_video(source);finish(w)
            self.assertTrue(w.analyze_button.isEnabled());self.assertFalse(w.save_button.isEnabled())
            w.model_edit.setText(str(model));w.single_person.setChecked(True)
            with patch('analyzer.gui_backend.analyze',side_effect=lambda *a,**kw:analyze(*a,engine_factory=FakeEngine,**kw)):
                w.start_analysis();finish(w)
            self.assertTrue(w.unsaved);self.assertTrue(w.save_button.isEnabled())
            self.assertEqual(w.session.frame_count,4)
            output=root/'saved.choreo'
            with patch('analyzer.gui.QFileDialog.getSaveFileName',return_value=(str(output),'')):
                w.choose_save();finish(w)
            self.assertTrue(output.is_file());self.assertFalse(w.unsaved)
            points=root/'points'
            with patch('analyzer.gui.QFileDialog.getSaveFileName',return_value=(str(points),'')):
                w.choose_points();finish(w)
            self.assertTrue((points/'haltungspunkte.sqlite').is_file())
            w.release_source()

    def test_cancel_worker_keeps_ui_alive_and_old_session(self):
        w=self.window;w.show_session(open_package(FIXTURE),False)
        session=w.session
        def task(**kw):
            while True:check_cancel(kw['cancel']);time.sleep(.005)
        w.run_job(task,lambda value:self.fail('cancelled job delivered'))
        self.assertFalse(w.open_button.isEnabled());self.assertTrue(w.cancel_button.isEnabled())
        w.cancel();finish(w)
        self.assertIs(w.session,session);self.assertTrue(w.open_button.isEnabled())

    def test_close_during_worker_cancels_before_destroying_window(self):
        w=self.window;w.show()
        def task(**kw):
            while True:check_cancel(kw['cancel']);time.sleep(.005)
        w.run_job(task,lambda value:None);w.close();finish(w);QTest.qWait(20)
        self.assertTrue(w.closing);self.assertFalse(w.isVisible())

    def test_decoded_frame_timestamp_selects_pose_and_fractional_step_rounds_up(self):
        w=self.window;w.show_session(open_package(FIXTURE),False)
        frame=type('Frame',(),{'isValid':lambda _:True,'toImage':lambda _:QImage(160,120,QImage.Format.Format_RGB32),
                              'startTime':lambda _:250000})()
        w.view.receive_frame(frame)
        self.assertEqual(w.session.frame_at(w.view.seconds),1)
        with patch.object(w,'run_job'),patch.object(w.view.player,'setPosition') as seek:
            w.step(1);seek.assert_called_once_with(500)
        with patch.object(w,'run_job'),patch.object(w.session,'timestamp',return_value=.533333333),patch.object(w.view.player,'setPosition') as seek:
            w.step(1);seek.assert_called_once_with(534)

    def test_consecutive_steps_show_exact_recorded_frames(self):
        w=self.window;w.show_session(open_package(FIXTURE),False)
        w.view.seconds=0.
        for expected in (.25,.5,.75):
            w.step(1);finish(w)
            self.assertEqual(w.view.seconds,expected)
            self.assertTrue(w.view.manual_frame)
        w.step(-1);finish(w);self.assertEqual(w.view.seconds,.5)

    def test_crop_geometry_and_click_coordinates_use_original_image(self):
        w=self.window;w.show_session(open_package(FIXTURE),False)
        w.view.resize(640,480);w.view.image=QImage(160,120,QImage.Format.Format_RGB32)
        source,target=w.view.geometry_rects()
        self.assertAlmostEqual(source.x(),16);self.assertAlmostEqual(source.width(),128)
        self.assertEqual(w.view.video_point(target.center()),(.5,.5))
        self.assertIsNone(w.view.video_point(QPointF(-1,-1)))
        w.zoom.setChecked(False)
        self.assertEqual(w.view.geometry_rects()[0].width(),160)

    def test_cleanup_retries_decoder_file_lock(self):
        resource=type('Resource',(),{'close':lambda _:None})()
        with patch.object(resource,'close',side_effect=[PermissionError('decoder'),None]) as close:
            self.window.dispose(resource);self.assertEqual(len(self.window.pending_cleanup),1)
            self.window.retry_cleanup();self.assertEqual(self.window.pending_cleanup,[])
            self.assertEqual(close.call_count,2)

    def test_open_error_preserves_current_session(self):
        w=self.window;w.show_session(open_package(FIXTURE),False);session=w.session
        with patch('analyzer.gui.QMessageBox.warning') as warning:
            w.load_package('does-not-exist.choreo');finish(w)
        self.assertIs(w.session,session);warning.assert_called_once()


if __name__=='__main__':unittest.main()
