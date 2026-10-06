"""Compact track controls, drawn locally for consistent native packages."""
import math
from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QPushButton, QSlider, QStyle, QStyleOptionSlider
from .i18n import tr


def track_button(kind, label, parent, checkable=False):
    canvas = QPixmap(48, 48)
    canvas.setDevicePixelRatio(2)
    canvas.fill(Qt.transparent)
    p = QPainter(canvas)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor('#dce7f4'), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    if kind == 'rename':
        p.drawPolygon(QPolygonF([QPointF(5, 16), QPointF(16, 5), QPointF(19, 8), QPointF(8, 19), QPointF(4, 20)]))
        p.drawLine(14, 7, 17, 10)
    elif kind == 'mute':
        p.drawPolyline(QPolygonF([QPointF(4, 9), QPointF(8, 9), QPointF(13, 5), QPointF(13, 19), QPointF(8, 15), QPointF(4, 15), QPointF(4, 9)]))
        p.drawLine(3, 3, 21, 21)
    elif kind == 'solo':
        p.drawArc(4, 4, 16, 16, 0, 180*16)
        p.drawRoundedRect(4, 11, 4, 9, 1, 1)
        p.drawRoundedRect(16, 11, 4, 9, 1, 1)
    else:
        p.drawRoundedRect(3, 5, 7, 14, 1, 1)
        p.drawRoundedRect(14, 5, 7, 14, 1, 1)
        if kind == 'join':
            p.drawLine(8, 12, 16, 12)
    p.end()
    button = QPushButton(parent)
    button.setIcon(QIcon(canvas))
    button.setIconSize(QSize(20, 20))
    button.setCheckable(checkable)
    button.setProperty('trackAction', kind)
    button.setToolTip(label)
    button.setAccessibleName(label)
    button.setStyleSheet('QPushButton {padding:2px;} QPushButton:checked {background:#357e69;border:1px solid #55d9b2;}')
    return button


def channel_button(track, parent):
    split = track.channels == 2
    button = track_button('split' if split else 'join',
                         tr('Separar en dos pistas mono') if split else tr('Unir como pista estéreo'), parent)
    button.setEnabled(split or track.output_channel is not None)
    return button


class MeterFader(QSlider):
    """Native slider input, with an independent input-peak meter on its rail."""
    def __init__(self, parent=None, orientation=Qt.Vertical):
        super().__init__(orientation, parent)
        self.peak = 0.0
        self.setRange(-600, 60)
        self.setAccessibleName(tr('Ganancia de escucha'))
        self.setToolTip(tr('Fader: ganancia de escucha. Luz: pico de entrada, independiente de la ganancia. No modifica los stems.'))

    def set_peak(self, value):
        if value != self.peak:
            self.peak = value
            self.update()

    def handle_rect(self):
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        return self.style().subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle, self)

    def paintEvent(self, event):
        p = QPainter(self)
        handle = self.handle_rect()
        vertical = self.orientation() == Qt.Vertical
        extent = max(1, self.height()-handle.height() if vertical else self.width()-handle.width())
        rail = (QRectF(self.width()/2-6, handle.height()/2, 12, extent) if vertical
                else QRectF(handle.width()/2, self.height()/2-5, extent, 10))
        p.fillRect(rail, QColor('#273548'))
        db = 20*math.log10(self.peak) if self.peak > 0 else -100
        fraction = max(0, min(1, (db+60)/66))
        for i in range(int(extent)//9):
            active = (i+1)*9 <= extent*fraction
            segment = (QRectF(rail.left(), rail.bottom()-(i+1)*9, rail.width(), 6) if vertical
                       else QRectF(rail.left()+i*9, rail.top(), 6, rail.height()))
            p.fillRect(segment,
                       QColor('#f5899e' if self.peak >= 1 else '#55d9b2') if active else QColor('#34465d'))
        p.setPen(QPen(QColor('#dce7f4'), 1))
        p.setBrush(QColor('#b9cfe5'))
        thumb = (QRectF(1, handle.top(), self.width()-2, handle.height()) if vertical
                 else QRectF(handle.left(), 1, handle.width(), self.height()-2))
        p.drawRoundedRect(thumb, 3, 3)
        if self.hasFocus():
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor('#55d9b2'), 1, Qt.DotLine))
            p.drawRect(self.rect().adjusted(0, 0, -1, -1))
