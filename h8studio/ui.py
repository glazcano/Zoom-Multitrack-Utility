from __future__ import annotations
from .i18n import tr, set_language
from pathlib import Path
import math
import sys
import threading

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QRectF, QEvent, QStandardPaths, QTranslator, QLibraryInfo
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QKeySequence, QShortcut, QFontDatabase
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QListWidget, QListWidgetItem, QSplitter, QScrollArea,
    QSlider, QCheckBox, QComboBox, QMessageBox, QProgressBar, QInputDialog, QLineEdit, QStackedWidget,
    QToolButton, QMenu, QWidgetAction, QSizePolicy, QTextEdit, QPlainTextEdit, QAbstractSpinBox)

from .core import read_project, waveform, export_stems, ExportCancelled, rename_project, rename_track, title_settings, ProjectError, set_stereo_split
from .audio import Player
from .dialogs import PreparationDialog, TemplatesDialog, show_report, LocateDialog, ExportOptionsDialog, LoopDialog, AboutDialog
from .workflows import export_batch, analyze_project
from .platforms import project_files
from .preferences import Preferences, export_options, library_entry, matches_entry
from .relink import find_candidates, link_media, missing_sources

COLORS = ['#55d9b2', '#70b4fb', '#c79bf2', '#f4c276', '#f5899e']


def clock_text(seconds):
    minutes, seconds = divmod(max(0, seconds), 60)
    hours, minutes = divmod(int(minutes), 60)
    return f'{hours:02d}:{minutes:02d}:{seconds:06.3f}'


class Job(QThread):
    result = Signal(object)
    failed = Signal(str)
    progress = Signal(int)

    def __init__(self, function, parent=None):
        super().__init__(parent)
        self.function = function
        self.cancel = threading.Event()

    def run(self):
        try:
            self.result.emit(self.function(self))
        except ExportCancelled:
            self.failed.emit(tr('Tarea cancelada. No se publicaron archivos incompletos.'))
        except Exception as exc:
            self.failed.emit(str(exc))


class Timeline(QWidget):
    seek = Signal(int)
    rename_requested = Signal(int)
    split_requested = Signal(int)
    LEFT, TOP, ROW = 260, 44, 144

    def __init__(self):
        super().__init__()
        self.project = None
        self.peaks = {}
        self.position = 0
        self.controls = []
        self.meter_values = []
        self.setMinimumSize(800, 360)

    def set_project(self, project, peaks):
        self.project, self.peaks, self.position = project, peaks, 0
        for widget in self.controls:
            widget.hide()
            widget.deleteLater()
        self.controls.clear()
        for i, t in enumerate(project.tracks):
            y = self.TOP+i*self.ROW
            mute, solo = QCheckBox('Mute', self), QCheckBox('Solo', self)
            mute.setGeometry(18, y+53, 75, 28)
            solo.setGeometry(100, y+53, 75, 28)
            mute.setChecked(t.mute)
            solo.setChecked(t.solo)
            mute.toggled.connect(lambda value, track=t: setattr(track, 'mute', value))
            solo.toggled.connect(lambda value, track=t: setattr(track, 'solo', value))
            gain = QSlider(Qt.Horizontal, self)
            gain.setRange(-600, 60)
            gain.setValue(round(200*math.log10(max(t.gain, .001))))
            gain.setGeometry(18, y+88, 155, 22)
            value = QLabel(f'{gain.value()/10:.1f} dB', self)
            value.setGeometry(183, y+85, 70, 25)
            def change(v, track=t, label=value):
                track.gain = 10**(v/200)
                label.setText(f'{v/10:.1f} dB')
            gain.valueChanged.connect(change)
            gain.setToolTip(tr('Volumen de escucha. No modifica los stems.'))
            for w in (mute, solo, gain, value):
                w.show()
                self.controls.append(w)
            rename = QPushButton(tr('Nombre…'), self)
            rename.setGeometry(172, y+8, 78, 29)
            rename.setStyleSheet('padding:3px;font-size:11px;')
            rename.setToolTip(tr('Etiquetar esta pista con el nombre del instrumento'))
            rename.clicked.connect(lambda checked=False, index=i: self.rename_requested.emit(index))
            rename.show()
            self.controls.append(rename)
            if t.channels == 2 or t.output_channel is not None:
                channels = QPushButton('2 mono' if t.channels == 2 else tr('Estéreo'), self)
                channels.setGeometry(178, y+45, 72, 30)
                channels.setStyleSheet('padding:3px;font-size:11px;')
                channels.setToolTip(tr('Alternar una pista estéreo y dos pistas mono L/R; también afecta a los stems'))
                channels.clicked.connect(lambda checked=False, index=i: self.split_requested.emit(index))
                channels.show()
                self.controls.append(channels)
        self.setMinimumHeight(max(360, self.TOP+len(project.tracks)*self.ROW+30))
        self.update()

    def x_for(self, sample):
        return self.LEFT+sample/max(1, self.project.length)*(self.width()-self.LEFT-28)

    def mousePressEvent(self, event):
        if self.project and event.position().x() >= self.LEFT and event.button() == Qt.LeftButton:
            fraction = (event.position().x()-self.LEFT)/max(1, self.width()-self.LEFT-28)
            self.seek.emit(round(max(0, min(1, fraction))*self.project.length))

    def mouseMoveEvent(self, event):
        if self.project and event.buttons() & Qt.LeftButton and event.position().x() >= self.LEFT:
            fraction = (event.position().x()-self.LEFT)/max(1, self.width()-self.LEFT-28)
            self.seek.emit(round(max(0, min(1, fraction))*self.project.length))

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor('#111720'))
        p.setFont(QFont(QApplication.font().family(), 9))
        if not self.project:
            p.setPen(QColor('#91a1b5'))
            p.drawText(self.rect(), Qt.AlignCenter, tr('Abre un proyecto .h8prj para ver sus pistas'))
            return
        duration = self.project.length/self.project.rate
        scale = max(1, (self.width()-self.LEFT)/110)
        desired = duration/scale
        steps = [0.1, .25, .5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 1800, 3600]
        step = next((s for s in steps if s >= desired), max(3600, desired))
        for n in range(int(duration/step)+1):
            sec = n*step
            x = self.x_for(sec*self.project.rate)
            p.setPen(QColor('#283342'))
            p.drawLine(int(x), 32, int(x), self.height())
            p.setPen(QColor('#8fa0b5'))
            p.drawText(QRectF(x+5, 5, 108, 26), Qt.AlignLeft, clock_text(sec)[:-4])
        for i, t in enumerate(self.project.tracks):
            y = self.TOP+i*self.ROW
            color = QColor(COLORS[i%len(COLORS)])
            p.fillRect(QRectF(0, y, self.LEFT-1, self.ROW-1), QColor('#1a2330'))
            p.fillRect(QRectF(0, y, 4, self.ROW-1), color)
            p.setPen(QColor('#eef4fb'))
            p.setFont(QFont(QApplication.font().family(), 11, QFont.DemiBold))
            p.drawText(18, y+25, p.fontMetrics().elidedText(t.name, Qt.ElideRight, 146))
            p.setFont(QFont(QApplication.font().family(), 9))
            p.setPen(QColor('#8fa0b5'))
            p.drawText(18, y+44, tr('Estéreo · 2 canales') if t.channels == 2 else tr('Mono · 1 canal'))
            peak = self.meter_values[i] if i < len(self.meter_values) else 0
            db = 20*math.log10(peak) if peak > 0 else -90
            p.fillRect(QRectF(18, y+120, 155, 6), QColor('#34465d'))
            p.fillRect(QRectF(18, y+120, 155*max(0, min(1, (db+60)/60)), 6),
                       QColor('#f5899e' if peak >= 1 else '#55d9b2'))
            p.setPen(QColor('#f5899e' if peak >= 1 else '#8fa0b5'))
            p.drawText(183, y+128, f'{db:.1f}' if peak else '−∞ dBFS')
            for c in t.clips:
                x1, x2 = self.x_for(c.start), self.x_for(c.start+c.frames)
                rect = QRectF(x1+1, y+10, max(2, x2-x1-2), self.ROW-21)
                fill = QColor('#482b35') if c.missing else QColor(color)
                if not c.missing:
                    fill.setAlpha(35)
                p.fillRect(rect, fill)
                p.setPen(QPen(QColor('#ed8795') if c.missing else color, 1))
                p.drawRoundedRect(rect, 5, 5)
                p.save()
                p.setClipRect(rect.adjusted(7, 1, -7, -1))
                p.drawText(QRectF(x1+10, y+15, max(1, x2-x1-20), 22), Qt.AlignLeft,
                           (tr('FALTA AUDIO · ') if c.missing else '')+c.path.name)
                peaks = self.peaks.get((str(c.path), c.channel))
                if peaks is None:
                    peaks = self.peaks.get(str(c.path))
                if peaks is not None and len(peaks):
                    middle = y+76
                    # At zoomed-out scales aggregate peaks by visible pixel.
                    width = max(1, int(rect.width()-16))
                    for pixel in range(min(width, len(peaks))):
                        lo = pixel*len(peaks)//min(width, len(peaks))
                        hi = max(lo+1, (pixel+1)*len(peaks)//min(width, len(peaks)))
                        group = peaks[lo:hi]
                        x = x1+8+pixel*width/min(width, len(peaks))
                        p.drawLine(int(x), int(middle-float(group[:,1].max())*30),
                                   int(x), int(middle-float(group[:,0].min())*30))
                p.restore()
            p.setPen(QColor('#27313f'))
            p.drawLine(0, y+self.ROW-1, self.width(), y+self.ROW-1)
        x = int(self.x_for(self.position))
        if self.project.export_range:
            a, b = self.project.export_range
            p.fillRect(QRectF(self.x_for(a), 31, self.x_for(b)-self.x_for(a), 8), QColor('#55d9b2'))
        if self.project.loop_range:
            a, b = self.project.loop_range
            p.fillRect(QRectF(self.x_for(a), 23, self.x_for(b)-self.x_for(a), 5), QColor('#f4c276'))
        p.setPen(QPen(QColor('#fff0c2'), 2))
        p.drawLine(x, 30, x, self.height())
        p.end()


class Console(Timeline):
    """One strip per track, with a seekable waveform above a vertical fader."""
    COLUMN = 240
    WAVE_TOP, WAVE_BOTTOM = 76, 166

    def __init__(self):
        super().__init__()
        self.strips = []
        self.setMinimumSize(240, 360)

    def set_project(self, project, peaks):
        self.project, self.peaks = project, peaks
        for widget in self.controls:
            widget.hide()
            widget.deleteLater()
        self.controls.clear()
        self.strips.clear()
        for i, track in enumerate(project.tracks):
            mute, solo = QCheckBox('Mute', self), QCheckBox('Solo', self)
            mute.setChecked(track.mute)
            solo.setChecked(track.solo)
            mute.toggled.connect(lambda value, t=track: setattr(t, 'mute', value))
            solo.toggled.connect(lambda value, t=track: setattr(t, 'solo', value))
            fader = QSlider(Qt.Vertical, self)
            fader.setRange(-600, 60)
            fader.setValue(round(200*math.log10(max(track.gain, .001))))
            fader.setToolTip(tr('Volumen de escucha; no modifica los stems. Arriba: +6 dB; abajo: −60 dB.'))
            value = QLabel(f'{fader.value()/10:.1f} dB', self)
            value.setAlignment(Qt.AlignCenter)
            def change(v, t=track, label=value):
                t.gain = 10**(v/200)
                label.setText(f'{v/10:.1f} dB')
            fader.valueChanged.connect(change)
            rename = QPushButton(tr('Nombre…'), self)
            rename.clicked.connect(lambda checked=False, index=i: self.rename_requested.emit(index))
            channels = QPushButton('2 mono' if track.channels == 2 else tr('Estéreo'), self)
            channels.setEnabled(track.channels == 2 or track.output_channel is not None)
            channels.clicked.connect(lambda checked=False, index=i: self.split_requested.emit(index))
            for w in (rename, channels):
                w.setStyleSheet('padding:4px;font-size:11px;')
            strip = (mute, solo, fader, value, rename, channels)
            self.strips.append(strip)
            self.controls.extend(strip)
            for widget in strip:
                widget.show()
        self.setMinimumWidth(max(240, len(project.tracks)*self.COLUMN))
        self.layout_strips()
        self.update()

    def layout_strips(self):
        for i, (mute, solo, fader, value, rename, channels) in enumerate(self.strips):
            x = i*self.COLUMN
            rename.setGeometry(x+14, 40, 92, 28)
            channels.setGeometry(x+130, 40, 96, 28)
            mute.setGeometry(x+28, 190, 80, 28)
            solo.setGeometry(x+135, 190, 80, 28)
            fader.setGeometry(x+66, 234, 32, self.height()-282)
            value.setGeometry(x+24, self.height()-32, 116, 25)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.layout_strips()

    def seek_at(self, point):
        if not self.project or not self.WAVE_TOP <= point.y() <= self.WAVE_BOTTOM:
            return
        index = int(point.x()//self.COLUMN)
        if not 0 <= index < len(self.project.tracks):
            return
        offset = point.x()-index*self.COLUMN-14
        if 0 <= offset <= self.COLUMN-28:
            self.seek.emit(round(offset/(self.COLUMN-28)*self.project.length))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.seek_at(event.position())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.seek_at(event.position())

    def paintEvent(self, event):
        if not self.project:
            return super().paintEvent(event)
        p = QPainter(self)
        p.fillRect(self.rect(), QColor('#111720'))
        duration = max(1, self.project.length)
        width = self.COLUMN-28
        for i, track in enumerate(self.project.tracks):
            x, color = i*self.COLUMN, QColor(COLORS[i%len(COLORS)])
            p.fillRect(QRectF(x+4, 4, self.COLUMN-8, self.height()-8), QColor('#1a2330'))
            p.fillRect(QRectF(x+4, 4, self.COLUMN-8, 3), color)
            p.setFont(QFont(QApplication.font().family(), 11, QFont.DemiBold))
            p.setPen(QColor('#eef4fb'))
            p.drawText(x+14, 28, p.fontMetrics().elidedText(track.name, Qt.ElideRight, width))
            p.setFont(QFont(QApplication.font().family(), 8))
            wave_rect = QRectF(x+14, self.WAVE_TOP, width, self.WAVE_BOTTOM-self.WAVE_TOP)
            p.fillRect(wave_rect, QColor('#111720'))
            p.save()
            p.setClipRect(wave_rect)
            for clip in track.clips:
                start = x+14+clip.start/duration*width
                end = x+14+(clip.start+clip.frames)/duration*width
                rect = QRectF(start, self.WAVE_TOP, max(1, end-start), wave_rect.height())
                p.fillRect(rect, QColor('#482b35') if clip.missing else QColor('#223d40'))
                p.setPen(QColor('#ed8795') if clip.missing else color)
                p.drawText(QRectF(start+4, self.WAVE_TOP+4, max(1, end-start-8), 22), Qt.AlignLeft,
                           tr('FALTA AUDIO') if clip.missing else clip.path.name)
                peaks = self.peaks.get((str(clip.path), clip.channel))
                if peaks is None:
                    peaks = self.peaks.get(str(clip.path))
                if peaks is not None and len(peaks):
                    pixels = max(1, min(len(peaks), int(end-start)))
                    for pixel in range(pixels):
                        lo, hi = pixel*len(peaks)//pixels, (pixel+1)*len(peaks)//pixels
                        group = peaks[lo:hi]
                        xx = int(start+pixel*(end-start)/pixels)
                        p.drawLine(xx, int(134-group[:, 1].max()*25), xx, int(134-group[:, 0].min()*25))
            if self.project.export_range:
                a, b = self.project.export_range
                p.fillRect(QRectF(x+14+a/duration*width, self.WAVE_TOP, (b-a)/duration*width, 4), QColor('#55d9b2'))
            if self.project.loop_range:
                a, b = self.project.loop_range
                p.fillRect(QRectF(x+14+a/duration*width, self.WAVE_TOP+6, (b-a)/duration*width, 4), QColor('#f4c276'))
            cursor = int(x+14+self.position/duration*width)
            p.setPen(QPen(QColor('#fff0c2'), 2))
            p.drawLine(cursor, self.WAVE_TOP, cursor, self.WAVE_BOTTOM)
            p.restore()
            p.setPen(QColor('#8fa0b5'))
            p.drawText(x+14, 182, '0:00')
            p.drawText(QRectF(x+80, 166, width-66, 20), Qt.AlignRight, clock_text(self.project.length/self.project.rate))
            peak = self.meter_values[i] if i < len(self.meter_values) else 0
            db = 20*math.log10(peak) if peak else -90
            height = self.height()-282
            p.fillRect(QRectF(x+148, 234, 18, height), QColor('#34465d'))
            fill = height*max(0, min(1, (db+60)/60))
            p.fillRect(QRectF(x+148, 234+height-fill, 18, fill), QColor('#f5899e' if peak >= 1 else '#55d9b2'))
            p.setPen(QColor('#8fa0b5'))
            for level in (0, -12, -24, -36, -48, -60):
                p.drawText(x+174, int(238-level/60*height), str(level))
            p.drawText(QRectF(x+134, self.height()-32, 95, 25), Qt.AlignCenter, f'{db:.1f} dBFS' if peak else '−∞ dBFS')
        p.end()


class VerticalConsole(Console):
    """Shared sample timeline running down each channel strip."""
    def wave_rect(self, index):
        return QRectF(index*self.COLUMN+14, 114, 118, max(1, self.height()-148))

    def layout_strips(self):
        for i, (mute, solo, fader, value, rename, channels) in enumerate(self.strips):
            x = i*self.COLUMN
            rename.setGeometry(x+14, 34, 92, 25)
            channels.setGeometry(x+130, 34, 96, 25)
            mute.setGeometry(x+16, 62, 84, 26)
            solo.setGeometry(x+132, 62, 84, 26)
            fader.setGeometry(x+145, 114, 30, self.height()-186)
            value.setGeometry(x+136, self.height()-59, 96, 24)

    def seek_at(self, point):
        if not self.project:
            return
        index = int(point.x()//self.COLUMN)
        if 0 <= index < len(self.project.tracks):
            rect = self.wave_rect(index)
            if rect.contains(point):
                fraction = (point.y()-rect.top())/rect.height()
                self.seek.emit(round(fraction*self.project.length))

    def paintEvent(self, event):
        if not self.project:
            return Timeline.paintEvent(self, event)
        p = QPainter(self)
        p.fillRect(self.rect(), QColor('#111720'))
        duration = max(1, self.project.length)
        for i, track in enumerate(self.project.tracks):
            x, color = i*self.COLUMN, QColor(COLORS[i%len(COLORS)])
            rect = self.wave_rect(i)
            p.fillRect(QRectF(x+4, 4, self.COLUMN-8, self.height()-8), QColor('#1a2330'))
            p.fillRect(QRectF(x+4, 4, self.COLUMN-8, 3), color)
            p.setFont(QFont(QApplication.font().family(), 11, QFont.DemiBold))
            p.setPen(QColor('#eef4fb'))
            p.drawText(x+14, 27, p.fontMetrics().elidedText(track.name, Qt.ElideRight, self.COLUMN-28))
            p.setFont(QFont(QApplication.font().family(), 8))
            p.setPen(QColor('#8fa0b5'))
            p.drawText(x+14, 106, tr('0:00  ↓ tiempo'))
            p.drawText(QRectF(x+14, self.height()-28, 120, 22), Qt.AlignLeft, clock_text(self.project.length/self.project.rate))
            p.fillRect(rect, QColor('#111720'))
            p.save()
            p.setClipRect(rect)
            for clip in track.clips:
                start = rect.top()+clip.start/duration*rect.height()
                end = rect.top()+(clip.start+clip.frames)/duration*rect.height()
                p.fillRect(QRectF(rect.left(), start, rect.width(), max(1, end-start)),
                           QColor('#482b35') if clip.missing else QColor('#223d40'))
                p.setPen(QColor('#ed8795') if clip.missing else color)
                peaks = self.peaks.get((str(clip.path), clip.channel))
                if peaks is None:
                    peaks = self.peaks.get(str(clip.path))
                if peaks is not None and len(peaks):
                    pixels = max(1, min(len(peaks), int(end-start)))
                    for pixel in range(pixels):
                        lo, hi = pixel*len(peaks)//pixels, (pixel+1)*len(peaks)//pixels
                        group = peaks[lo:hi]
                        yy = int(start+pixel*(end-start)/pixels)
                        center = rect.center().x()
                        p.drawLine(int(center+group[:, 0].min()*50), yy, int(center+group[:, 1].max()*50), yy)
                if clip.missing:
                    p.drawText(QRectF(rect.left()+4, start+4, rect.width()-8, 36), Qt.TextWordWrap, tr('FALTA AUDIO'))
            if self.project.export_range:
                a, b = self.project.export_range
                p.fillRect(QRectF(rect.left(), rect.top()+a/duration*rect.height(), 4, (b-a)/duration*rect.height()), QColor('#55d9b2'))
            if self.project.loop_range:
                a, b = self.project.loop_range
                p.fillRect(QRectF(rect.right()-4, rect.top()+a/duration*rect.height(), 4, (b-a)/duration*rect.height()), QColor('#f4c276'))
            p.setPen(QPen(QColor('#8fa0b5'), 1, Qt.DotLine))
            for fraction in (.25, .5, .75):
                yy = int(rect.top()+rect.height()*fraction)
                p.drawLine(int(rect.left()), yy, int(rect.right()), yy)
            cursor = int(rect.top()+self.position/duration*rect.height())
            p.setPen(QPen(QColor('#fff0c2'), 2))
            p.drawLine(int(rect.left()), cursor, int(rect.right()), cursor)
            p.restore()
            peak = self.meter_values[i] if i < len(self.meter_values) else 0
            db = 20*math.log10(peak) if peak else -90
            height = self.height()-186
            p.fillRect(QRectF(x+188, 114, 12, height), QColor('#34465d'))
            fill = height*max(0, min(1, (db+60)/60))
            p.fillRect(QRectF(x+188, 114+height-fill, 12, fill), QColor('#f5899e' if peak >= 1 else '#55d9b2'))
            p.setPen(QColor('#8fa0b5'))
            for level in (0, -12, -24, -36, -48, -60):
                p.drawText(x+204, int(118-level/60*height), str(level))
            p.drawText(QRectF(x+136, self.height()-30, 96, 24), Qt.AlignCenter, f'{db:.1f} dBFS' if peak else '−∞ dBFS')
        p.end()


def compact_menu(label, widgets, parent):
    button = QToolButton(parent)
    button.setText(label)
    button.setPopupMode(QToolButton.InstantPopup)
    menu = QMenu(button)
    for widget in widgets:
        action = QWidgetAction(menu)
        action.setDefaultWidget(widget)
        menu.addAction(action)
        if isinstance(widget, QPushButton):
            widget.clicked.connect(menu.close)
    button.setMenu(menu)
    return button


class Window(QMainWindow):
    def __init__(self, initial=None, state_path=None):
        super().__init__()
        if state_path is None:
            state_path = Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation))/'preferences.json'
        self.preferences = Preferences(state_path)
        set_language(self.preferences.data.get('language', 'en'))
        app = QApplication.instance()
        if getattr(app, '_h8_translator', None):
            app.removeTranslator(app._h8_translator)
        app._h8_translator = QTranslator(app)
        if self.preferences.data.get('language') == 'es':
            if app._h8_translator.load('qtbase_es', QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
                app.installTranslator(app._h8_translator)
        QApplication.instance().installEventFilter(self)
        self.session = self.preferences.data.get('session', {})
        if not isinstance(self.session, dict):
            self.session = {}
        self.restore_position = None
        self.portable_delivery = False
        self.export_naming = 'track'
        self.setWindowTitle(tr('H8 Studio · Proyectos Zoom'))
        self.resize(1320, 800)
        self.setMinimumSize(920, 620)
        self.player = Player()
        self.project = None
        self.job = None
        self.after_job = None
        self.library_root = None
        self.setAcceptDrops(True)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        heading = QHBoxLayout()
        brand = QLabel('H8 <span style="color:#55d9b2">STUDIO</span>')
        brand.setStyleSheet('font-size:18px;font-weight:700')
        heading.addWidget(brand)
        self.library_toggle = QCheckBox(tr('Biblioteca'))
        self.library_toggle.setChecked(True)
        heading.addWidget(self.library_toggle)
        heading.addStretch()
        self.about_button = QPushButton(tr('Acerca de…'))
        self.about_button.clicked.connect(self.about_dialog)
        heading.addWidget(self.about_button)
        self.open_button = QPushButton(tr('Abrir proyecto…'))
        self.folder_button = QPushButton(tr('Explorar carpeta…'))
        self.open_button.clicked.connect(self.open_dialog)
        self.folder_button.clicked.connect(self.folder_dialog)
        heading.addWidget(compact_menu(tr('Abrir'), (self.open_button, self.folder_button), self))
        layout.addLayout(heading)
        split = QSplitter()
        side = QWidget()
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 0, 6, 0)
        sl.setSpacing(4)
        self.library_toggle.toggled.connect(side.setVisible)
        self.library_label = QLabel(tr('PROYECTOS'))
        sl.addWidget(self.library_label)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr('Buscar nombre, notas o carpeta…'))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.filter_library)
        sl.addWidget(self.search)
        self.library_filter = QComboBox()
        self.library_filter.addItems([tr('Todos los proyectos'), tr('★ Favoritos'), tr('Falta audio / error de lectura')])
        self.library_filter.currentIndexChanged.connect(self.filter_library)
        sl.addWidget(self.library_filter)
        self.library = QListWidget()
        self.library.setMinimumWidth(190)
        self.library.itemActivated.connect(lambda item: self.load(item.data(Qt.UserRole)))
        sl.addWidget(self.library)
        selection = QHBoxLayout()
        for label, mode in [(tr('Todas'), 'all'), (tr('Ninguna'), 'none'), ('★', 'favorites')]:
            button = QPushButton(label)
            button.setToolTip(tr('Marcar favoritas para el lote') if mode == 'favorites' else label)
            button.clicked.connect(lambda checked=False, value=mode: self.check_projects(value))
            selection.addWidget(button)
        sl.addLayout(selection)
        self.channel_mode = QComboBox()
        self.channel_mode.addItems([tr('Usar elección guardada'), tr('Una pista estéreo'), tr('Dos pistas mono (L/R)')])
        self.channel_mode.setToolTip(tr('Al abrir guarda la elección. Al exportar un lote solo cambia esa exportación.'))
        self.channels_batch_button = QPushButton(tr('Aplicar canales al lote'))
        self.channels_batch_button.clicked.connect(self.channels_batch)
        sl.addWidget(compact_menu(tr('Canales al abrir / lote'), (self.channel_mode, self.channels_batch_button), self))
        self.batch_button = QPushButton(tr('Exportar lote marcado…'))
        self.batch_button.clicked.connect(self.batch_dialog)
        sl.addWidget(self.batch_button)
        hint = QLabel(tr('Doble clic: abrir · casillas: lote'))
        hint.setWordWrap(True)
        hint.setStyleSheet('color:#8fa0b5;font-size:12px')
        sl.addWidget(hint)
        split.addWidget(side)
        main = QWidget()
        ml = QVBoxLayout(main)
        ml.setContentsMargins(4, 0, 0, 0)
        ml.setSpacing(4)
        self.title = QLabel(tr('Tu grabación, lista para continuar.'))
        self.title.setTextFormat(Qt.PlainText)
        self.title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.title.setStyleSheet('font-size:18px;font-weight:600')
        self.subtitle = QLabel(tr('Abre un archivo .h8prj con sus WAV en la misma carpeta.'))
        self.subtitle.setStyleSheet('color:#9eafc3')
        title_row = QHBoxLayout()
        title_row.addWidget(self.title, 1)
        self.rename_button = QPushButton(tr('Cambiar título…'))
        self.rename_button.clicked.connect(self.rename_dialog)
        ml.addLayout(title_row)
        ml.addWidget(self.subtitle)
        self.prepare_button = QPushButton(tr('Favorita, notas y tramo…'))
        self.prepare_button.clicked.connect(self.prepare_dialog)
        self.templates_button = QPushButton(tr('Plantillas…'))
        self.templates_button.clicked.connect(self.templates_dialog)
        self.problems_button = QPushButton(tr('Resumen de problemas…'))
        self.problems_button.clicked.connect(self.problems_dialog)
        self.locate_button = QPushButton(tr('Localizar WAV…'))
        self.locate_button.clicked.connect(self.locate_dialog)
        title_row.addWidget(compact_menu(tr('Proyecto'), (self.rename_button, self.prepare_button,
            self.templates_button, self.problems_button, self.locate_button), self))
        self.notice = QPushButton(tr('Avisos'))
        self.notice.setEnabled(False)
        self.notice.clicked.connect(lambda: show_report(self, tr('Observaciones del proyecto'), '\n'.join(self.project.warnings)) if self.project else None)
        title_row.addWidget(self.notice)
        toolbar = QHBoxLayout()
        self.play_button = QPushButton(tr('▶  Reproducir'))
        self.stop_button = QPushButton(tr('■  Inicio'))
        self.play_button.clicked.connect(self.toggle_play)
        self.stop_button.clicked.connect(self.stop)
        toolbar.addWidget(self.play_button)
        toolbar.addWidget(self.stop_button)
        self.time_label = QLabel('00:00:00.000 / 00:00:00.000')
        self.time_label.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.time_label.setStyleSheet('font-size:12px;color:#fff0c2')
        toolbar.addWidget(self.time_label)
        self.loop_button = QCheckBox(tr('Bucle'))
        self.loop_button.setToolTip(tr('Repite el tramo del bucle o toda la toma. Usa A–B para definir inicio y fin.'))
        self.loop_button.toggled.connect(lambda value: setattr(self.player, 'loop', value))
        toolbar.addWidget(self.loop_button)
        self.loop_range_button = QPushButton('A–B…')
        self.loop_range_button.setToolTip(tr('Definir el tramo del bucle'))
        self.loop_range_button.clicked.connect(self.loop_dialog)
        toolbar.addWidget(self.loop_range_button)
        toolbar.addStretch()
        self.view_mode = QComboBox()
        self.view_mode.addItems([tr('Línea de tiempo'), tr('Consola'), tr('Consola vertical')])
        self.view_mode.currentIndexChanged.connect(self.change_view)
        toolbar.addWidget(self.view_mode)
        toolbar.addWidget(QLabel('Zoom'))
        self.zoom = QComboBox()
        self.zoom.addItems([tr('Ajustar'), '2×', '4×', '8×'])
        self.zoom.setToolTip(tr('Zoom de la línea de tiempo. Las consolas muestran la toma completa.'))
        self.zoom.currentIndexChanged.connect(self.resize_timeline)
        toolbar.addWidget(self.zoom)
        ml.addLayout(toolbar)
        self.timeline = Timeline()
        self.timeline.seek.connect(self.seek)
        self.timeline.rename_requested.connect(self.rename_track_dialog)
        self.timeline.split_requested.connect(self.toggle_channels)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.timeline)
        self.console = Console()
        self.console.seek.connect(self.seek)
        self.console.rename_requested.connect(self.rename_track_dialog)
        self.console.split_requested.connect(self.toggle_channels)
        self.console_scroll = QScrollArea()
        self.console_scroll.setWidgetResizable(True)
        self.console_scroll.setWidget(self.console)
        self.vertical_console = VerticalConsole()
        self.vertical_console.seek.connect(self.seek)
        self.vertical_console.rename_requested.connect(self.rename_track_dialog)
        self.vertical_console.split_requested.connect(self.toggle_channels)
        self.vertical_scroll = QScrollArea()
        self.vertical_scroll.setWidgetResizable(True)
        self.vertical_scroll.setWidget(self.vertical_console)
        self.views = QStackedWidget()
        self.views.addWidget(self.scroll)
        self.views.addWidget(self.console_scroll)
        self.views.addWidget(self.vertical_scroll)
        ml.addWidget(self.views, 1)
        bottom = QHBoxLayout()
        bottom.addWidget(QLabel(tr('Escucha')))
        self.master = QSlider(Qt.Horizontal)
        self.master.setRange(-600, 0)
        self.master.setValue(-60)
        self.master.setMaximumWidth(120)
        self.master.valueChanged.connect(lambda v: setattr(self.player, 'master', 10**(v/200)))
        self.player.master = 10**(-60/200)
        bottom.addWidget(self.master)
        self.meter = QLabel('−∞ dBFS')
        self.meter.setMinimumWidth(105)
        bottom.addWidget(self.meter)
        self.center_mono = QCheckBox(tr('Mono centrado'))
        self.center_mono.setToolTip(tr('Escuchar los canales mono L/R por ambos altavoces. Solo monitoreo.'))
        self.center_mono.toggled.connect(lambda value: setattr(self.player, 'center_mono', value))
        bottom.addWidget(self.center_mono)
        bottom.addStretch()
        self.rpp = QCheckBox(tr('Crear .rpp'))
        self.rpp.setChecked(True)
        self.format = QComboBox()
        self.format.addItems(['WAV · 24 bits', 'FLAC · 24 bits'])
        self.export_button = QPushButton(tr('Exportar…'))
        self.export_button.setObjectName('primary')
        self.export_button.clicked.connect(self.export_dialog)
        bottom.addWidget(self.export_button)
        ml.addLayout(bottom)
        self.options_button = QPushButton(tr('Exportación y presets…'))
        self.options_button.clicked.connect(self.options_dialog)
        self.export_menu = compact_menu(tr('Exportación'), (self.format, self.rpp, self.options_button), self)
        bottom.insertWidget(bottom.count()-1, self.export_menu)
        self.options_summary = QLabel('', self)
        self.options_summary.hide()
        self.meter.setToolTip(tr('Pico de escucha en dBFS. Los medidores de pista muestran el pico de entrada.'))
        split.addWidget(main)
        split.setSizes([220, 1050])
        layout.addWidget(split, 1)
        status = QHBoxLayout()
        self.status = QLabel(tr('Listo'))
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(200)
        self.progress.hide()
        self.cancel_button = QPushButton(tr('Cancelar tarea'))
        self.cancel_button.clicked.connect(lambda: self.job.cancel.set() if self.job else None)
        self.cancel_button.hide()
        status.addWidget(self.status, 1)
        status.addWidget(self.progress)
        status.addWidget(self.cancel_button)
        layout.addLayout(status)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(60)
        QShortcut(QKeySequence('Space'), self, activated=self.toggle_play)
        QShortcut(QKeySequence(QKeySequence.StandardKey.Open), self, activated=self.open_dialog)
        QShortcut(QKeySequence('Home'), self, activated=self.stop)
        self.set_busy(False)
        self.restore_controls()
        if initial:
            p = Path(initial)
            if p.is_dir() and p.suffix.lower() != '.zprj':
                self.scan(p)
            else:
                self.scan(p.parent)
                QTimer.singleShot(100, lambda: self.load(p))
        elif isinstance(self.session.get('library'), str) and Path(self.session['library']).is_dir():
            self.scan(self.session['library'])
            last = self.session.get('project')
            if isinstance(last, str) and Path(last).is_file():
                self.restore_position = (str(Path(last).resolve()), self.session.get('position', 0))
                QTimer.singleShot(100, lambda: self.load(last, use_saved_channels=True))
        else:
            base = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
            candidates = [base/'Projects', base.parent/'Projects', base.parent.parent/'Projects']
            for p in candidates:
                if p.is_dir():
                    self.scan(p)
                    break
        if self.preferences.error:
            self.status.setText(self.preferences.error)

    def eventFilter(self, watched, event):
        # Preserve spaces and Home while editing, including dialog text fields.
        if event.type() == QEvent.ShortcutOverride and event.key() in (Qt.Key_Space, Qt.Key_Home):
            if isinstance(watched, (QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox)):
                event.accept()
                return True
        return super().eventFilter(watched, event)

    def about_dialog(self):
        if not self.job:
            AboutDialog(self.preferences, self).exec()

    def loop_dialog(self):
        if self.project and not self.job:
            self.player.pause()
            if LoopDialog(self.project, self.player.position, self).exec():
                self.loop_button.setChecked(True)
                for view in (self.timeline, self.console, self.vertical_console):
                    view.update()

    def set_busy(self, busy):
        self.locate_button.setEnabled(not busy and self.project is not None and bool(missing_sources(self.project)))
        self.options_button.setEnabled(not busy)
        self.loop_button.setEnabled(not busy and self.project is not None)
        self.loop_range_button.setEnabled(not busy and self.project is not None)
        self.about_button.setEnabled(not busy)
        for w in (self.prepare_button, self.templates_button, self.problems_button):
            w.setEnabled(not busy and self.project is not None)
        self.batch_button.setEnabled(not busy)
        self.channels_batch_button.setEnabled(not busy)
        self.channel_mode.setEnabled(not busy)
        self.timeline.setEnabled(not busy)
        self.console.setEnabled(not busy)
        self.vertical_console.setEnabled(not busy)
        self.view_mode.setEnabled(not busy)
        self.rename_button.setEnabled(not busy and self.project is not None)
        for w in (self.open_button, self.folder_button, self.library, self.search, self.library_filter):
            w.setEnabled(not busy)
        self.export_button.setEnabled(not busy and self.project is not None and
                                      not any(c.missing for t in self.project.tracks for c in t.clips))
        self.play_button.setEnabled(not busy and self.project is not None and
                                    any(not c.missing for t in self.project.tracks for c in t.clips))
        self.stop_button.setEnabled(not busy and self.project is not None)

    def current_export_options(self):
        return dict(format=('WAV', 'FLAC')[self.format.currentIndex()],
                    channels=self.channel_mode.currentIndex(), rpp=self.rpp.isChecked(),
                    portable=self.portable_delivery, naming=self.export_naming)

    def apply_export_options(self, options):
        options = export_options(options)
        self.format.setCurrentIndex(0 if options['format'] == 'WAV' else 1)
        self.channel_mode.setCurrentIndex(options['channels'])
        self.rpp.setChecked(options['rpp'])
        self.portable_delivery, self.export_naming = options['portable'], options['naming']
        self.options_summary.setText(tr('Entrega portátil: .rpp, notas y checksums incluidos') if options['portable']
                                     else tr('Stems · nombres ')+(tr('por instrumento') if options['naming'] == 'track' else tr('con prefijo de proyecto')))
        self.export_menu.setToolTip(self.options_summary.text())

    def options_dialog(self):
        if self.job:
            return
        dialog = ExportOptionsDialog(self.preferences, self.current_export_options(), self)
        if dialog.exec():
            self.apply_export_options(dialog.options())

    def restore_controls(self):
        try:
            self.apply_export_options(self.preferences.data.get('export', {}))
        except ProjectError:
            self.apply_export_options({})
        for key, widget, minimum, maximum in [('zoom', self.zoom, 0, 3), ('filter', self.library_filter, 0, 2), ('view', self.view_mode, 0, 2)]:
            value = self.session.get(key, 0)
            widget.setCurrentIndex(value if type(value) is int and minimum <= value <= maximum else 0)
        query = self.session.get('search', '')
        self.search.setText(query if isinstance(query, str) else '')
        self.center_mono.setChecked(self.session.get('center_mono') is True)
        self.library_toggle.setChecked(self.session.get('library_visible', True) is not False)
        master = self.session.get('master', -60)
        self.master.setValue(master if type(master) is int and -600 <= master <= 0 else -60)

    def save_session(self):
        self.preferences.data['session'] = dict(
            library=str(self.library_root or (self.project.path.parent if self.project else '')),
            project=str(self.project.path) if self.project else '', position=self.player.position,
            zoom=self.zoom.currentIndex(), search=self.search.text(), filter=self.library_filter.currentIndex(),
            view=self.view_mode.currentIndex(),
            library_visible=self.library_toggle.isChecked(),
            center_mono=self.center_mono.isChecked(), master=self.master.value())
        self.preferences.data['export'] = self.current_export_options()
        try:
            self.preferences.save()
        except OSError as exc:
            QMessageBox.warning(self, tr('Preferencias'), tr('No se pudo guardar la sesión: {0}', exc))

    def locate_dialog(self):
        if not self.project or self.job:
            return
        folder = QFileDialog.getExistingDirectory(self, tr('Buscar WAV en esta carpeta y subcarpetas'), str(self.library_root or self.project.path.parent))
        if not folder:
            return
        self.player.pause()
        project, position = self.project, self.player.position
        def found(candidates):
            dialog = LocateDialog(candidates, self)
            if not dialog.exec() or not dialog.selections():
                return
            selections = dialog.selections()
            def work(job):
                reopened = link_media(project, selections)
                return reopened, self.project_peaks(reopened)
            def loaded(result):
                self.loaded(result)
                self.player.position = min(position, self.project.length)
                self.status.setText(tr('WAV asociados y guardados. Los archivos originales no se modificaron.'))
            action = lambda: self.start_job(work, loaded)
            if self.job:
                self.after_job = action
            else:
                action()
        self.status.setText(tr('Buscando WAV compatibles…'))
        self.start_job(lambda job: find_candidates(project, folder, job.cancel), found, exporting=True)

    def scan(self, folder):
        self.library_root = Path(folder)
        self.library.clear()
        for p in project_files(self.library_root, recursive=True):
            entry = library_entry(p)
            label = ('★ ' if entry['favorite'] else '') + entry['name']
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, str(p))
            item.setData(Qt.UserRole+1, entry)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setToolTip(f'{label}\n{entry["notes"]}\n{entry["detail"]}\n{p}')
            self.library.addItem(item)
        self.filter_library()

    def filter_library(self, *_):
        if not hasattr(self, 'library'):
            return
        visible = 0
        for i in range(self.library.count()):
            item = self.library.item(i)
            shown = matches_entry(item.data(Qt.UserRole+1), self.search.text(), self.library_filter.currentIndex())
            item.setHidden(not shown)
            visible += int(shown)
        self.library_label.setText(tr('PROYECTOS  /  {0} de {1}', visible, self.library.count()))

    def checked_paths(self):
        return [self.library.item(i).data(Qt.UserRole) for i in range(self.library.count())
                if not self.library.item(i).isHidden() and self.library.item(i).checkState() == Qt.Checked]

    def check_projects(self, mode):
        if self.job:
            return
        for i in range(self.library.count()):
            item = self.library.item(i)
            if item.isHidden() and mode != 'none':
                continue
            selected = mode == 'all'
            if mode == 'favorites':
                try:
                    selected = title_settings(Path(item.data(Qt.UserRole))).get('favorite', False)
                except ProjectError:
                    selected = False
            item.setCheckState(Qt.Checked if selected else Qt.Unchecked)

    def refresh_preparation(self):
        p = self.project
        for i in range(self.library.count()):
            item = self.library.item(i)
            if Path(item.data(Qt.UserRole)).resolve() == p.path:
                item.setText(('★ ' if p.favorite else '') + p.name)
                item.setToolTip(f'{p.name}\n{p.notes}\n{p.path}')
                item.setData(Qt.UserRole+1, library_entry(p.path))
        a, b = p.export_range or (0, p.length)
        self.subtitle.setText(tr('{0} pistas · {1:g} kHz · Exportar {2} → {3}', len(p.tracks), p.rate / 1000, clock_text(a / p.rate), clock_text(b / p.rate)))
        self.timeline.update()
        self.filter_library()
        self.loop_button.setEnabled(not self.job)
        self.loop_range_button.setEnabled(not self.job)

    def prepare_dialog(self):
        if self.project and not self.job:
            self.player.pause()
            if PreparationDialog(self.project, self.player.position, self).exec():
                self.refresh_preparation()

    def templates_dialog(self):
        if not self.project or self.job:
            return
        try:
            path = (self.library_root or self.project.path.parent)/'.h8studio-templates.json'
            dialog = TemplatesDialog(self.project, path, self)
            dialog.exec()
            self.timeline.update()
        except (ProjectError, OSError) as exc:
            self.job_error(str(exc))

    def problems_dialog(self):
        if not self.project or self.job:
            return
        paths = self.checked_paths() or [str(self.project.path)]
        self.player.pause()
        def work(job):
            rows = [tr('Análisis de las tomas completas. Pico ≥ −0,1 dBFS: posible saturación; RMS < −60 dBFS: nivel muy bajo.\n')]
            for i, path in enumerate(paths):
                if job.cancel.is_set():
                    raise ExportCancelled()
                rows.append('\n'+Path(path).stem)
                try:
                    project = read_project(path)
                    rows.extend(analyze_project(project, job.cancel,
                        lambda percent, n=i: job.progress.emit(int((n+percent/100)*100/len(paths)))))
                except ExportCancelled:
                    raise
                except Exception as exc:
                    rows.append(f'ERROR: {exc}')
            return '\n'.join(rows)
        self.status.setText(tr('Analizando proyectos marcados o la toma abierta…'))
        self.start_job(work, lambda report: show_report(self, tr('Resumen de problemas'), report), exporting=True)

    def batch_dialog(self):
        if self.job:
            return
        paths = self.checked_paths()
        if not paths:
            self.job_error(tr('Marca las casillas de los proyectos que quieres exportar.'))
            return
        folder = QFileDialog.getExistingDirectory(self, tr('Exportar {0} proyectos: destino del lote', len(paths)), str(self.library_root or Path.home()))
        if not folder:
            return
        self.player.pause()
        fmt, rpp = ('WAV' if self.format.currentIndex() == 0 else 'FLAC'), self.rpp.isChecked()
        split_stereo = self.selected_channel_mode()
        portable, naming = self.portable_delivery, self.export_naming
        self.status.setText(tr('Exportando {0} proyectos con sus tramos guardados…', len(paths)))
        self.start_job(lambda job: export_batch(paths, Path(folder), fmt, rpp, job.progress.emit, job.cancel, split_stereo=split_stereo, portable=portable, naming=naming), self.batch_finished, exporting=True)

    def selected_channel_mode(self):
        return (None, False, True)[self.channel_mode.currentIndex()]

    def channels_batch(self):
        if self.job:
            return
        paths, mode = self.checked_paths(), self.selected_channel_mode()
        if not paths or mode is None:
            self.job_error(tr('Marca proyectos y elige una pista estéreo o dos pistas mono.'))
            return
        self.player.pause()
        current = self.project
        position = self.player.position
        def work(job):
            rows, refreshed = [], None
            for index, path in enumerate(paths):
                if job.cancel.is_set():
                    rows.append(tr('Cancelado: las elecciones ya guardadas se conservan.'))
                    break
                try:
                    p = current if current and current.path == Path(path).resolve() else read_project(path)
                    set_stereo_split(p, mode)
                    if p is current:
                        refreshed = (p, self.project_peaks(p))
                    rows.append(tr('{0}: canales guardados', Path(path).stem))
                except Exception as exc:
                    rows.append(f'{Path(path).stem}: ERROR: {exc}')
                job.progress.emit(round(100*(index+1)/len(paths)))
            return rows, refreshed
        def finished(result):
            rows, refreshed = result
            if refreshed:
                self.loaded(refreshed)
                self.player.position = position
            show_report(self, tr('Canales del lote'), '\n'.join(rows))
        self.start_job(work, finished, exporting=True)

    @staticmethod
    def project_peaks(project):
        return {(str(c.path), c.channel): waveform(c) for t in project.tracks for c in t.clips}

    def toggle_channels(self, index):
        if not self.project or self.job:
            return
        self.player.pause()
        position = self.player.position
        track = self.project.tracks[index]
        try:
            set_stereo_split(self.project, track.channels == 2, track.clips[0].path.name)
        except (ProjectError, OSError) as exc:
            self.job_error(str(exc))
            return
        def finished(peaks):
            self.loaded((self.project, peaks))
            self.player.position = position
            self.status.setText(tr('Canales guardados · la exportación usará las pistas visibles'))
        self.start_job(lambda job: self.project_peaks(self.project), finished)

    def batch_finished(self, result):
        lines = [tr('Exportados: {0}', len(result['completed'])), tr('Fallidos: {0}', len(result['failed'])),
                 tr('Pendientes: {0}', len(result['pending'])), tr('Cancelado') if result['cancelled'] else tr('Lote terminado'),
                 tr('Carpeta e informe lote.json: {0}', result['folder'])]
        lines += [f'{Path(x["source"]).stem}: {x["error"]}' for x in result['failed']]
        self.status.setText(tr('Lote: {0} exportados; {1} fallidos.', len(result['completed']), len(result['failed'])))
        show_report(self, tr('Resultado del lote'), '\n'.join(lines))

    def open_dialog(self):
        if self.job:
            return
        path, _ = QFileDialog.getOpenFileName(self, tr('Abrir proyecto Zoom H8'), str(self.library_root or Path.home()), tr('Proyecto Zoom (*.h8prj)'))
        if path:
            self.load(path)

    def folder_dialog(self):
        if self.job:
            return
        folder = QFileDialog.getExistingDirectory(self, tr('Carpeta de proyectos'), str(self.library_root or Path.home()))
        if folder:
            self.scan(folder)
            if self.library.count() == 1:
                self.load(self.library.item(0).data(Qt.UserRole))

    def start_job(self, function, success, exporting=False):
        self.set_busy(True)
        self.progress.setRange(0, 100 if exporting else 0)
        self.progress.setValue(0)
        self.progress.show()
        self.cancel_button.setVisible(exporting)
        job = Job(function, self)
        self.job = job
        job.progress.connect(self.progress.setValue)
        job.result.connect(success)
        job.failed.connect(self.job_error)
        job.finished.connect(self.job_finished)
        job.start()

    def job_finished(self):
        if self.job:
            self.job.deleteLater()
        self.job = None
        self.progress.hide()
        self.cancel_button.hide()
        self.set_busy(False)
        if self.after_job:
            action, self.after_job = self.after_job, None
            QTimer.singleShot(0, action)

    def job_error(self, error):
        self.status.setText(error)
        QMessageBox.warning(self, 'H8 Studio', error)

    def load(self, path, use_saved_channels=False):
        if self.job:
            return
        self.player.pause()
        self.status.setText(tr('Leyendo proyecto y formas de onda…'))
        mode = None if use_saved_channels else self.selected_channel_mode()
        def work(job):
            project = read_project(path)
            if mode is not None:
                set_stereo_split(project, mode)
            peaks = self.project_peaks(project)
            return project, peaks
        self.start_job(work, self.loaded)

    def loaded(self, result):
        project, peaks = result
        try:
            self.player.load(project)
        except Exception as exc:
            self.project = None
            self.job_error(str(exc))
            return
        self.project = project
        if self.restore_position and self.restore_position[0] == str(project.path):
            position = self.restore_position[1]
            self.player.position = max(0, min(position, project.length)) if type(position) is int else 0
            self.restore_position = None
        self.title.setText(project.name)
        self.subtitle.setText(tr('{0} pistas  ·  {1:g} kHz  ·  {2}  ·  {3}', len(project.tracks), project.rate / 1000, clock_text(project.length / project.rate), project.alignment))
        missing = sum(c.missing for t in project.tracks for c in t.clips)
        self.notice.setText(tr('Faltan WAV') if missing else tr('Avisos ({0})', len(project.warnings)))
        self.notice.setToolTip('\n'.join(project.warnings))
        self.notice.setEnabled(bool(project.warnings))
        self.timeline.set_project(project, peaks)
        self.console.set_project(project, peaks)
        self.vertical_console.set_project(project, peaks)
        self.refresh_preparation()
        self.status.setText(tr('Proyecto abierto · clic en una onda para mover el cursor · Espacio para reproducir'))
        self.resize_timeline()

    def rename_dialog(self):
        if not self.project or self.job:
            return
        title, accepted = QInputDialog.getText(self, tr('Cambiar título del proyecto'),
            tr('Título (hasta 100 caracteres):'), text=self.project.name)
        if not accepted:
            return
        try:
            rename_project(self.project, title)
        except (ProjectError, OSError) as exc:
            self.job_error(tr('No se guardó el título: {0}', exc))
            return
        self.title.setText(self.project.name)
        for i in range(self.library.count()):
            item = self.library.item(i)
            if Path(item.data(Qt.UserRole)).resolve() == self.project.path.resolve():
                item.setText(('★ ' if self.project.favorite else '') + self.project.name)
                item.setToolTip(f'{self.project.name}\n{self.project.path}')
        self.status.setText(tr('Título guardado. Se usará también al exportar los stems.'))
        self.refresh_preparation()

    def rename_track_dialog(self, index):
        if not self.project or self.job:
            return
        track = self.project.tracks[index]
        title, accepted = QInputDialog.getText(self, tr('Nombre del instrumento'),
            tr('Nombre de pista (hasta 100 caracteres):'), text=track.name)
        if not accepted:
            return
        try:
            rename_track(self.project, track, title)
        except (ProjectError, OSError) as exc:
            self.job_error(tr('No se guardó el nombre: {0}', exc))
            return
        self.timeline.update()
        self.refresh_preparation()
        self.status.setText(tr('Pista guardada: {0}. Los stems usarán esta etiqueta.', track.name))

    def change_view(self, index):
        if not hasattr(self, 'views'):
            return
        self.views.setCurrentIndex(index)
        self.zoom.setEnabled(index == 0)
        if self.project:
            view = (self.timeline, self.console, self.vertical_console)[index]
            view.set_project(self.project, self.timeline.peaks)
            view.position = self.player.position
            view.meter_values = [t.peak if self.player.playing else 0 for t in self.project.tracks]
        self.resize_timeline()

    def resize_timeline(self, *_):
        self.timeline.setMinimumWidth(max(650, self.scroll.viewport().width())*(2**self.zoom.currentIndex()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'timeline'):
            self.resize_timeline()

    def toggle_play(self):
        if not self.project or self.job:
            return
        try:
            if self.player.playing:
                self.player.pause()
            else:
                self.player.play()
        except Exception as exc:
            self.job_error(tr('No se pudo abrir la salida de audio: {0}', exc))

    def stop(self):
        self.player.pause()
        self.player.position = 0

    def seek(self, sample):
        if not self.job:
            try:
                self.player.seek(sample)
            except Exception as exc:
                self.job_error(str(exc))

    def tick(self):
        self.play_button.setText(tr('Ⅱ  Pausa') if self.player.playing else tr('▶  Reproducir'))
        if self.project:
            self.time_label.setText(f'{clock_text(self.player.position/self.project.rate)} / {clock_text(self.project.length/self.project.rate)}')
            view = (self.timeline, self.console, self.vertical_console)[self.view_mode.currentIndex()]
            meters = [t.peak if self.player.playing else 0 for t in self.project.tracks]
            if view.position != self.player.position or view.meter_values != meters:
                view.position = self.player.position
                view.meter_values = meters
                view.update()
        peak = self.player.peak if self.player.playing else 0
        self.meter.setText('CLIP' if peak >= 1 else f'{20*math.log10(peak):.1f} dBFS' if peak > 0 else '−∞ dBFS')
        self.meter.setStyleSheet('color:#f5899e' if peak >= 1 else 'color:#55d9b2')
        if self.player.error:
            error, self.player.error = self.player.error, ''
            self.player.pause()
            self.job_error(error)

    def export_dialog(self):
        if not self.project or self.job:
            return
        folder = QFileDialog.getExistingDirectory(self, tr('Destino: se creará una carpeta nueva para los stems'), str(self.project.path.parent.parent))
        if not folder:
            return
        self.player.pause()
        fmt = 'WAV' if self.format.currentIndex() == 0 else 'FLAC'
        create_rpp = self.rpp.isChecked()
        portable, naming = self.portable_delivery, self.export_naming
        self.status.setText(tr('Exportando stems {0} a 24 bits…', fmt))
        self.start_job(lambda job: export_stems(self.project, Path(folder), fmt, job.progress.emit, job.cancel, create_rpp=create_rpp, portable=portable, naming=naming),
                       self.exported, exporting=True)

    def exported(self, folder):
        self.status.setText(tr('Stems guardados en {0}', folder))
        QMessageBox.information(self, tr('Exportación terminada'),
            tr('{0}\n\nSi activaste Crear .rpp, abre Proyecto.rpp en Reaper. También puedes importar los stems desde 00:00. Todos respetan el tramo elegido.', folder))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and not self.job:
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not self.job:
            path = Path(event.mimeData().urls()[0].toLocalFile())
            if path.is_dir() and path.suffix.lower() != '.zprj':
                self.scan(path)
            else:
                self.load(path)

    def closeEvent(self, event):
        if self.job:
            self.status.setText(tr('Espera a que termine la lectura o cancela la exportación antes de cerrar.'))
            event.ignore()
            return
        self.save_session()
        self.player.close()
        event.accept()


STYLE = '''
QWidget { background:#111720; color:#dce7f4; font-size:13px; }
QPushButton, QToolButton { background:#273548; border:1px solid #35465b; border-radius:5px; padding:4px 8px; }
QToolButton::menu-indicator { subcontrol-position:right center; }
QMenu { background:#1a2330; border:1px solid #35465b; padding:6px; }
QPushButton:hover { background:#344961; }
QPushButton:disabled { color:#64748b; background:#1a2330; }
QPushButton#primary { background:#55d9b2; color:#102b23; font-weight:700; border:0; }
QPushButton#primary:disabled { background:#273548; color:#64748b; }
QListWidget { background:#161f2b; border:1px solid #2b3849; border-radius:6px; outline:0; }
QListWidget::item { padding:6px 8px; border-bottom:1px solid #202c3b; }
QListWidget::item:selected { background:#26443f; color:#7aebca; }
QListWidget::item:hover { background:#273548; }
QScrollArea { border:1px solid #2b3849; border-radius:6px; }
QComboBox { background:#273548; border:1px solid #35465b; padding:4px 6px; border-radius:5px; }
QSlider::groove:horizontal { height:4px; background:#34465d; border-radius:2px; }
QSlider::handle:horizontal { width:12px; margin:-4px 0; background:#b9cfe5; border-radius:6px; }
QSlider::sub-page:horizontal { background:#55d9b2; }
QSlider::groove:vertical { width:6px; background:#34465d; border-radius:3px; }
QSlider::handle:vertical { height:18px; margin:0 -10px; background:#b9cfe5; border-radius:4px; }
QSlider::add-page:vertical { background:#55d9b2; }
QCheckBox { background:transparent; }
QCheckBox::indicator { width:15px; height:15px; border:1px solid #53677f; border-radius:3px; background:#17202b; }
QCheckBox::indicator:checked { background:#55d9b2; }
QProgressBar { border:1px solid #35465b; text-align:center; }
QProgressBar::chunk { background:#357e69; }
QToolTip { background:#263548; color:#fff; border:1px solid #526780; }
'''


class Application(QApplication):
    """Handle Finder's open-document events without bootloader argv emulation."""
    def __init__(self, argv):
        self.window = None
        self.pending_file = None
        super().__init__(argv)

    def event(self, event):
        if event.type() == QEvent.FileOpen and event.file():
            if self.window is None or self.window.job:
                self.pending_file = event.file()
            else:
                self.window.load(event.file())
            return True
        return super().event(event)

    def open_pending(self):
        if self.pending_file and self.window and not self.window.job:
            path, self.pending_file = self.pending_file, None
            self.window.load(path)


def run():
    app = Application(sys.argv)
    app.setApplicationName('H8 Studio')
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    window = Window(sys.argv[1] if len(sys.argv) > 1 else None)
    app.window = window
    pending_timer = QTimer(window)
    pending_timer.timeout.connect(app.open_pending)
    pending_timer.start(250)
    window.show()
    return app.exec()
