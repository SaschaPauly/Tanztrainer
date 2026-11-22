"""Native video rendering; pose coordinates always refer to the full video."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoSink
from PySide6.QtWidgets import QWidget

EDGES=((11,12),(11,13),(13,15),(15,17),(15,19),(17,19),(15,21),
       (12,14),(14,16),(16,18),(16,20),(18,20),(16,22),(11,23),(12,24),
       (23,24),(23,25),(25,27),(27,29),(29,31),(27,31),
       (24,26),(26,28),(28,30),(30,32),(28,32),(0,1),(1,2),(2,3),(3,7),
       (0,4),(4,5),(5,6),(6,8),(9,10))


def confidence_color(point):
    score=min(point[5:7])
    return QColor('#55e19b' if score>=.65 else '#ffca55' if score>=.5 else '#ff7777')


class VideoView(QWidget):
    marked=Signal(object)
    frameChanged=Signal(float)
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setMinimumSize(320,220)
        self.image=QImage();self.session=None;self.seconds=0.
        self.show_skeleton=True;self.show_zoom=True;self.marking=False;self.target=None;self.priming=False;self.manual_frame=False
        self.player=QMediaPlayer(self)
        self.audio=QAudioOutput(self);self.audio.setVolume(.7)
        self.player.setAudioOutput(self.audio)
        self.sink=QVideoSink(self);self.player.setVideoSink(self.sink)
        self.sink.videoFrameChanged.connect(self.receive_frame)

    def receive_frame(self,frame):
        if self.manual_frame:return
        if not frame.isValid():return
        image=frame.toImage()
        if image.isNull():return
        self.image=image
        # Actual decoded presentation timestamp, rather than rounded player ms.
        self.seconds=max(0.,frame.startTime()/1_000_000) if frame.startTime()>=0 else self.player.position()/1000
        if self.priming:
            self.priming=False;self.player.pause();self.audio.setMuted(False)
        self.frameChanged.emit(self.seconds)
        self.update()

    def clear(self):
        from PySide6.QtCore import QUrl
        self.priming=False;self.manual_frame=False;self.player.stop();self.player.setSource(QUrl());self.audio.setMuted(False)
        self.session=None;self.image=QImage();self.seconds=0.;self.target=None
        self.update()

    def load(self,path):
        from PySide6.QtCore import QUrl
        # Qt does not deliver an initial frame for a merely loaded source.
        # Decode the first frame silently, then pause for immediate inspection.
        self.priming=True;self.audio.setMuted(True)
        self.player.setSource(QUrl.fromLocalFile(str(path)));self.player.play()

    def exact_frame(self,data):
        self.manual_frame=True
        self.image=QImage(data['pixels'],data['width'],data['height'],data['width']*3,QImage.Format.Format_RGB888).copy()
        self.seconds=data['seconds'];self.frameChanged.emit(self.seconds);self.update()

    def geometry_rects(self):
        if self.image.isNull():return QRectF(),QRectF()
        source=QRectF(0,0,self.image.width(),self.image.height())
        if self.session and self.show_zoom:
            z=self.session.manifest['zoom']
            source=QRectF(z['x']*self.image.width(),z['y']*self.image.height(),
                          z['width']*self.image.width(),z['height']*self.image.height())
        scale=min(self.width()/source.width(),self.height()/source.height())
        target=QRectF((self.width()-source.width()*scale)/2,(self.height()-source.height()*scale)/2,
                      source.width()*scale,source.height()*scale)
        return source,target

    def video_point(self,position):
        source,target=self.geometry_rects()
        if target.isEmpty() or not target.contains(position):return None
        return ((source.x()+(position.x()-target.x())/target.width()*source.width())/self.image.width(),
                (source.y()+(position.y()-target.y())/target.height()*source.height())/self.image.height())

    def mousePressEvent(self,event):
        if self.marking and self.seconds<.05 and event.button()==Qt.MouseButton.LeftButton:
            point=self.video_point(event.position())
            if point is not None:
                self.target=point;self.marked.emit(point);self.update()

    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor('#101822'))
        if self.image.isNull():
            p.setPen(QColor('#dce4ec'))
            p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,'Video importieren oder .choreo öffnen')
            return
        source,target=self.geometry_rects()
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawImage(target,self.image,source)
        p.save();p.setClipRect(target);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        def point(x,y):
            return QPointF(target.x()+(x*self.image.width()-source.x())/source.width()*target.width(),
                           target.y()+(y*self.image.height()-source.y())/source.height()*target.height())
        if self.session and self.show_skeleton:
            index=self.session.frame_at(self.seconds)
            if index is not None:
                points=self.session.pose(index)
                valid=lambda a:all(math.isfinite(v) for v in a[:2])
                for a,b in EDGES:
                    if valid(points[a]) and valid(points[b]):
                        weakest=min((points[a],points[b]),key=lambda v:min(v[5:7]))
                        p.setPen(QPen(confidence_color(weakest),2.5))
                        p.drawLine(point(*points[a][:2]),point(*points[b][:2]))
                for values in points:
                    if valid(values):
                        p.setPen(QPen(QColor('#101822'),1));p.setBrush(confidence_color(values))
                        p.drawEllipse(point(*values[:2]),3.5,3.5)
        if self.target:
            marker=point(*self.target)
            p.setPen(QPen(QColor('#ffffff'),2));p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(marker,12,12);p.drawLine(marker-QPointF(18,0),marker+QPointF(18,0))
            p.drawLine(marker-QPointF(0,18),marker+QPointF(0,18))
        p.restore()
