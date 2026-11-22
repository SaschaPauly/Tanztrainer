"""Local Windows desktop analyzer. Start with python -m analyzer.gui."""
import argparse
import math
from pathlib import Path
import sys

from PySide6.QtCore import QThread, QTimer, QUrl, Signal, Qt
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox,
    QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QSlider, QSpinBox,
    QSplitter, QVBoxLayout, QWidget)

from analyzer.export_poses import export_poses
from analyzer.gui_backend import PreparedInput, PackageSession, prepare_input, open_package, analyze_prepared, save_package, read_frame
from analyzer.gui_view import VideoView
from analyzer.models import download_models, model_path
from analyzer.runtime import AnalysisCancelled

ROOT=Path(__file__).resolve().parent.parent


class Worker(QThread):
    progress=Signal(str,object,str)
    succeeded=Signal(object)
    failed=Signal(str)
    cancelled=Signal()
    def __init__(self,task,parent=None):
        super().__init__(parent);self.task=task
    def run(self):
        try:
            result=self.task(cancel=self.isInterruptionRequested,progress=self.progress.emit)
        except AnalysisCancelled:self.cancelled.emit()
        except Exception as exc:self.failed.emit(str(exc))
        else:self.succeeded.emit(result)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Showtanz-Analyzer · Phase 3')
        self.resize(1180,820)
        self.prepared=None;self.session=None;self.worker=None;self.result=None
        self.pending_cleanup=[];self.closing=False;self.unsaved=False
        self.view=VideoView()
        self.setCentralWidget(QWidget());outer=QVBoxLayout(self.centralWidget())
        bar=QHBoxLayout();outer.addLayout(bar)
        self.import_button=QPushButton('1  Video importieren …');bar.addWidget(self.import_button)
        self.open_button=QPushButton('.choreo öffnen …');bar.addWidget(self.open_button)
        bar.addStretch()
        privacy=QLabel('Video und Haltungspunkte bleiben auf diesem PC.');bar.addWidget(privacy)
        splitter=QSplitter();outer.addWidget(splitter,1)
        left=QWidget();layout=QVBoxLayout(left);layout.setContentsMargins(0,0,8,0)
        layout.addWidget(self.view,1)
        controls=QHBoxLayout();layout.addLayout(controls)
        self.play_button=QPushButton('▶ Abspielen');controls.addWidget(self.play_button)
        self.previous_button=QPushButton('‹ Bild');controls.addWidget(self.previous_button)
        self.next_button=QPushButton('Bild ›');controls.addWidget(self.next_button)
        self.time_label=QLabel('0,00 s');controls.addWidget(self.time_label);controls.addStretch()
        self.seek=QSlider(Qt.Orientation.Horizontal);layout.addWidget(self.seek)
        toggles=QHBoxLayout();layout.addLayout(toggles)
        self.skeleton=QCheckBox('Haltungspunkte');self.skeleton.setChecked(True)
        self.zoom=QCheckBox('Fester Zoom');self.zoom.setChecked(True)
        toggles.addWidget(self.skeleton);toggles.addWidget(self.zoom);toggles.addStretch()
        layout.addWidget(QLabel('Grün ≥ 0,65 · Gelb ≥ 0,5 · Rot < 0,5 · Fehlende Punkte werden nicht gezeichnet.'))
        right=QWidget();form=QVBoxLayout(right)
        self.source_label=QLabel('Noch kein Video gewählt.');self.source_label.setWordWrap(True)
        form.addWidget(self.source_label)
        settings=QFormLayout();form.addLayout(settings)
        self.title_edit=QLineEdit();self.title_edit.setMaxLength(200);settings.addRow('Titel',self.title_edit)
        model_row=QHBoxLayout();self.model_edit=QLineEdit(str(model_path(ROOT/'models','lite')))
        self.model_button=QPushButton('…');self.model_button.setMaximumWidth(36)
        model_row.addWidget(self.model_edit);model_row.addWidget(self.model_button)
        settings.addRow('Lokales Modell',model_row)
        self.download_button=QPushButton('Lite-Modell von Google herunterladen');form.addWidget(self.download_button)
        self.single_person=QCheckBox('Auf dem Video ist nur eine Person sichtbar')
        self.single_person.setToolTip('Bitte nur bestätigen, wenn dies für das gesamte Video gilt. Spiegelungen können Zusatzdetektionen auslösen.')
        form.addWidget(self.single_person)
        self.mark_button=QPushButton('Person am Videoanfang markieren');self.mark_button.setCheckable(True)
        form.addWidget(self.mark_button)
        self.mark_label=QLabel('Optional: auf den Oberkörper im ersten Bild klicken.');self.mark_label.setWordWrap(True)
        form.addWidget(self.mark_label)
        self.advanced=QGroupBox('Weitere Einstellungen');self.advanced.setCheckable(True);self.advanced.setChecked(False)
        advanced_form=QFormLayout(self.advanced)
        self.backend=QComboBox();self.backend.addItems(['cpu','auto','gpu']);advanced_form.addRow('Rechenweg',self.backend)
        self.percent=QDoubleSpinBox();self.percent.setRange(0,100);self.percent.setValue(30);self.percent.setSuffix(' %')
        advanced_form.addRow('Unsichere Bilder',self.percent)
        self.side=QSpinBox();self.side.setRange(64,4096);self.side.setValue(1280);advanced_form.addRow('Analyse-Bildkante',self.side)
        self.fps=QDoubleSpinBox();self.fps.setRange(0,240);self.fps.setSpecialValueText('Alle Bilder');advanced_form.addRow('Max. Bilder/s',self.fps)
        self.aspect=QComboBox();self.aspect.addItems(['9:16','16:9','1:1']);advanced_form.addRow('Zoom-Zielformat',self.aspect)
        form.addWidget(self.advanced)
        self.analyze_button=QPushButton('2  Analyse starten');form.addWidget(self.analyze_button)
        self.quality=QPlainTextEdit();self.quality.setReadOnly(True)
        self.quality.setPlaceholderText('Nach der Analyse: Qualität, Warnungen und Zoom prüfen.\n\n3D-Koordinaten sind Modellschätzungen. Die Bewertung ist heuristisch.')
        form.addWidget(self.quality,1)
        self.save_button=QPushButton('3  .choreo speichern …');form.addWidget(self.save_button)
        self.points_button=QPushButton('Haltungspunkte als CSV / SQLite ausgeben …');form.addWidget(self.points_button)
        splitter.addWidget(left);splitter.addWidget(right);splitter.setSizes([740,400])
        status=QHBoxLayout();outer.addLayout(status)
        self.status_label=QLabel('Bereit. Lite · CPU · 30 % · alle Bilder.');status.addWidget(self.status_label,1)
        self.progress=QProgressBar();self.progress.setMaximumWidth(200);status.addWidget(self.progress)
        self.cancel_button=QPushButton('Abbrechen');status.addWidget(self.cancel_button)
        self.import_button.clicked.connect(self.choose_video)
        self.open_button.clicked.connect(self.choose_package)
        self.model_button.clicked.connect(self.choose_model)
        self.download_button.clicked.connect(self.download)
        self.analyze_button.clicked.connect(self.start_analysis)
        self.save_button.clicked.connect(self.choose_save)
        self.points_button.clicked.connect(self.choose_points)
        self.cancel_button.clicked.connect(self.cancel)
        self.play_button.clicked.connect(self.play_pause)
        self.previous_button.clicked.connect(lambda:self.step(-1))
        self.next_button.clicked.connect(lambda:self.step(1))
        self.seek.sliderMoved.connect(self.seek_to)
        self.view.player.durationChanged.connect(lambda value:self.seek.setRange(0,value))
        self.view.player.positionChanged.connect(self.update_position)
        self.view.player.playbackStateChanged.connect(lambda state:self.play_button.setText('❚❚ Pause' if state==QMediaPlayer.PlaybackState.PlayingState else '▶ Abspielen'))
        self.view.player.errorOccurred.connect(lambda error,text:self.status_label.setText('Videowiedergabe fehlgeschlagen: '+text))
        self.skeleton.toggled.connect(self.toggle_view);self.zoom.toggled.connect(self.toggle_view)
        self.mark_button.toggled.connect(self.mark_mode);self.view.marked.connect(self.marked)
        self.cleanup_timer=QTimer(self);self.cleanup_timer.setInterval(250)
        self.cleanup_timer.timeout.connect(self.retry_cleanup)
        self.update_buttons()

    def update_buttons(self):
        busy=self.worker is not None
        for widget in (self.import_button,self.open_button,self.model_button,self.download_button,
                       self.model_edit,self.title_edit,self.single_person,self.advanced):widget.setEnabled(not busy)
        self.analyze_button.setEnabled(not busy and self.prepared is not None)
        self.mark_button.setEnabled(not busy and self.prepared is not None and self.session is None)
        self.save_button.setEnabled(not busy and self.session is not None)
        self.points_button.setEnabled(not busy and self.session is not None)
        for widget in (self.play_button,self.seek):widget.setEnabled(not busy and not self.mark_button.isChecked() and bool(self.prepared or self.session))
        for widget in (self.previous_button,self.next_button):widget.setEnabled(not busy and self.session is not None)
        self.cancel_button.setEnabled(busy)

    def run_job(self,task,on_success):
        if self.worker is not None:return
        self.view.player.pause();self.result=None;self.job_success=on_success
        self.worker=Worker(task,self)
        self.worker.progress.connect(self.set_progress)
        self.worker.succeeded.connect(self.job_result)
        self.worker.failed.connect(self.job_failed)
        self.worker.cancelled.connect(lambda:self.status_label.setText('Abgebrochen. Keine unvollständige Ausgabe gespeichert.'))
        self.worker.finished.connect(self.job_finished)
        self.progress.setRange(0,0);self.status_label.setText('Vorgang wird gestartet …')
        self.update_buttons();self.worker.start()

    def set_progress(self,stage,fraction,message):
        self.status_label.setText(message)
        self.progress.setRange(0,0 if fraction is None else 100)
        if fraction is not None:self.progress.setValue(round(fraction*100))

    def job_result(self,result):self.result=result

    def job_failed(self,message):
        self.status_label.setText('Fehlgeschlagen: '+message)
        if not self.closing:QMessageBox.warning(self,'Vorgang fehlgeschlagen',message)

    def job_finished(self):
        worker=self.worker;self.worker=None;worker.deleteLater()
        result=self.result;self.result=None
        if self.closing:
            if isinstance(result,(PreparedInput,PackageSession)):self.dispose(result)
        elif result is not None:
            try:self.job_success(result)
            except Exception as exc:
                if isinstance(result,(PreparedInput,PackageSession)):self.dispose(result)
                self.job_failed(str(exc))
        self.progress.setRange(0,100);self.progress.setValue(0);self.update_buttons()
        if self.closing:self.close()

    def cancel(self):
        if self.worker:
            self.worker.requestInterruption();self.cancel_button.setEnabled(False)
            self.status_label.setText('Abbruch angefordert; der laufende Arbeitsschritt wird beendet …')

    def allow_replace(self):
        if not self.unsaved:return True
        return QMessageBox.question(self,'Ergebnis noch nicht gespeichert',
            'Das neue Ergebnis wurde noch nicht gespeichert. Trotzdem eine andere Datei laden?',
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes

    def dispose(self,resource):
        if resource is None:return
        try:resource.close()
        except OSError:
            self.pending_cleanup.append(resource);self.cleanup_timer.start()

    def retry_cleanup(self):
        pending=self.pending_cleanup;self.pending_cleanup=[]
        for resource in pending:self.dispose(resource)
        if not self.pending_cleanup:
            self.cleanup_timer.stop()
            if self.closing:self.close()

    def release_source(self,keep_prepared=False):
        self.view.clear();self.dispose(self.session);self.session=None
        if not keep_prepared:self.dispose(self.prepared);self.prepared=None
        self.unsaved=False

    def choose_video(self):
        if not self.allow_replace():return
        path,_=QFileDialog.getOpenFileName(self,'Video importieren','','Videos (*.mp4 *.mov *.mkv *.avi *.webm *.m4v);;Alle Dateien (*)')
        if path:self.import_video(path)

    def import_video(self,path):
        self.run_job(lambda **kw:prepare_input(path,**kw),self.show_prepared)

    def show_prepared(self,prepared):
        self.release_source();self.prepared=prepared
        self.title_edit.setText(prepared.source.stem)
        self.source_label.setText(str(prepared.source))
        self.quality.clear();self.mark_button.setChecked(False)
        self.mark_label.setText('Optional: auf den Oberkörper im ersten Bild klicken.')
        self.view.load(prepared.video)
        self.status_label.setText('Video importiert. Einpersonenaufnahme bestätigen, optional markieren, Analyse starten.')
        self.update_buttons()

    def choose_package(self):
        if not self.allow_replace():return
        path,_=QFileDialog.getOpenFileName(self,'Choreografie öffnen','','Choreografie (*.choreo)')
        if path:self.load_package(path)

    def load_package(self,path):
        self.run_job(lambda **kw:open_package(path,**kw),lambda value:self.show_session(value,False))

    def show_session(self,session,is_new=True):
        self.release_source(keep_prepared=is_new);self.session=session;self.unsaved=is_new
        self.view.session=session
        self.view.load(session.video)
        self.title_edit.setText(session.manifest['title'])
        self.source_label.setText('Analyseergebnis · '+session.manifest['title'])
        self.mark_button.setChecked(False)
        z=session.manifest['zoom'];q=session.quality
        full=all(z[k]==v for k,v in (('x',0),('y',0),('width',1),('height',1)))
        text=(f"{session.frame_count} Bilder · {session.manifest['durationSeconds']:.2f} s\n"
              f"Qualität: {q['status']} · Fehlende Haltungspunkte: {q['missingLandmarks']}\n"
              f"Zoom: {'Ganzbild (Sicherheitsfallback)' if full else 'fester Ausschnitt'}\n\n")
        self.quality.setPlainText(text+'\n\n'.join(q['warnings']))
        self.status_label.setText('Ergebnis prüfen, dann als .choreo speichern.' if is_new else 'Choreografie geöffnet. Keine neue Analyse ausgeführt.')
        self.update_buttons()

    def choose_model(self):
        path,_=QFileDialog.getOpenFileName(self,'Lokales Pose-Modell wählen',self.model_edit.text(),'MediaPipe-Modell (*.task)')
        if path:self.model_edit.setText(path)

    def download(self):
        self.run_job(lambda **kw:(download_models(ROOT/'models',('lite',),**kw),model_path(ROOT/'models','lite'))[1],
                     lambda path:(self.model_edit.setText(str(path)),self.status_label.setText('Lite-Modell lokal bereit.')))

    def mark_mode(self,enabled):
        self.view.marking=enabled
        if enabled:
            self.view.player.pause();self.view.player.setPosition(0)
            self.mark_label.setText('Im ersten Bild auf die Mitte zwischen Schultern und Hüfte klicken.')
        else:self.view.target=None;self.view.update()
        self.update_buttons()

    def marked(self,point):
        self.mark_label.setText('Startperson markiert. Diese Auswahl wird beim Analysestart verwendet.')

    def start_analysis(self):
        if self.prepared is None:return
        model=Path(self.model_edit.text())
        if not model.is_file():
            self.job_failed('Lokales Modell fehlt. Lite-Modell herunterladen oder eine .task-Datei wählen.');return
        if self.mark_button.isChecked() and self.view.target is None:
            self.job_failed('Bitte zuerst den Oberkörper im ersten Bild markieren oder die Markierung ausschalten.');return
        a,b=map(int,self.aspect.currentText().split(':'))
        options=dict(title=self.title_edit.text(),single_person=self.single_person.isChecked(),
                     target_point=self.view.target if self.mark_button.isChecked() else None,
                     zoom_percent=self.percent.value(),backend=self.backend.currentText(),
                     max_side=self.side.value(),max_fps=self.fps.value(),aspect=a/b)
        self.run_job(lambda **kw:analyze_prepared(self.prepared,model,**options,**kw),self.show_session)

    def choose_save(self):
        path,_=QFileDialog.getSaveFileName(self,'Choreografie speichern',self.title_edit.text()+'.choreo','Choreografie (*.choreo)')
        if not path:return
        if not path.lower().endswith('.choreo'):path+='.choreo'
        output=Path(path)
        self.run_job(lambda **kw:save_package(self.session.package,output,overwrite=output.exists(),**kw),self.saved)

    def saved(self,path):
        self.unsaved=False;self.status_label.setText('Gespeichert: '+str(path))

    def choose_points(self):
        path,_=QFileDialog.getSaveFileName(self,'Neuen Ordner für Haltungspunkte anlegen',self.title_edit.text()+' - Haltungspunkte','Ordnername (*)')
        if path:
            self.run_job(lambda **kw:export_poses(self.session.package,path,**kw),
                         lambda report:self.status_label.setText('CSV, SQLite und Bericht gespeichert: '+path))

    def play_pause(self):
        self.view.manual_frame=False
        if self.view.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState:self.view.player.pause()
        else:self.view.player.play()

    def update_position(self,position):
        if not self.seek.isSliderDown():self.seek.setValue(position)
        self.time_label.setText(f'{position/1000:.2f} s')

    def step(self,direction):
        if not self.session or self.worker is not None:return
        self.view.player.pause()
        index=self.session.frame_at(self.view.seconds)
        index=max(0,min(self.session.frame_count-1,(index if index is not None else -1)+direction))
        timestamp=self.session.timestamp(index)
        self.view.manual_frame=True
        self.view.player.setPosition(math.ceil(timestamp*1000-1e-6))
        self.run_job(lambda **kw:read_frame(self.session.video,timestamp,**kw),self.show_exact_frame)

    def show_exact_frame(self,data):
        self.view.exact_frame(data)
        self.time_label.setText(f'{data["seconds"]:.3f} s')
        self.seek.setValue(round(data['seconds']*1000))
        self.status_label.setText(f'Einzelbild {self.session.frame_at(data["seconds"])+1} von {self.session.frame_count}')

    def seek_to(self,position):
        self.view.manual_frame=False;self.view.player.setPosition(position)

    def toggle_view(self):
        self.view.show_skeleton=self.skeleton.isChecked();self.view.show_zoom=self.zoom.isChecked();self.view.update()

    def closeEvent(self,event):
        if self.worker:
            self.closing=True;self.cancel();event.ignore();return
        if not self.closing and self.unsaved:
            if QMessageBox.question(self,'Ergebnis noch nicht gespeichert','Ohne Speichern schließen?',
                    QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:
                event.ignore();return
        self.closing=True;self.release_source()
        if self.pending_cleanup:event.ignore()
        else:event.accept()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package',type=Path,help='Vorhandene .choreo-Datei direkt öffnen')
    args=parser.parse_args(argv)
    app=QApplication(sys.argv[:1]);app.setApplicationName('Showtanz-Analyzer')
    window=MainWindow();window.show()
    if args.package:QTimer.singleShot(0,lambda:window.load_package(args.package))
    return app.exec()


if __name__=='__main__':raise SystemExit(main())
