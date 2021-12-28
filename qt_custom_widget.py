import logging
from functools import cached_property

from PySide6.QtCore import (Property, QEasingCurve, QObject, QPoint,
                            QPropertyAnimation, QRect, Qt, Signal)
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QCheckBox, QComboBox, QPlainTextEdit, QStyleOption, QStyle


class PyToggle(QCheckBox):
    def __init__(self,
                 width=50,
                 bg_color="#777",
                 circle_color="#DDD",
                 active_color="#00BCFF",
                 animation_curve=QEasingCurve.OutBounce):
        QCheckBox.__init__(self)
        self.setFixedSize(width, 28)
        self.setCursor(Qt.PointingHandCursor)

        # COLORS
        self._bg_color = bg_color
        self._circle_color = circle_color
        self._active_color = active_color

        self._position = 3
        self.animation = QPropertyAnimation(self, b"position")
        self.animation.setEasingCurve(animation_curve)
        self.animation.setDuration(500)
        self.stateChanged.connect(self.setup_animation)

    @Property(float)
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        self._position = pos
        self.update()

    # START STOP ANIMATION
    def setup_animation(self, value):
        self.animation.stop()
        if value:
            self.animation.setEndValue(self.width() - 26)
        else:
            self.animation.setEndValue(4)
        self.animation.start()

    def hitButton(self, pos: QPoint):
        return self.contentsRect().contains(pos)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(QFont("Segoe UI", 9))

        # SET PEN
        p.setPen(Qt.NoPen)

        # DRAW RECT
        rect = QRect(0, 0, self.width(), self.height())

        if not self.isChecked():
            p.setBrush(QColor(self._bg_color))
            p.drawRoundedRect(0, 0, rect.width(), 28, 14, 14)
            p.setBrush(QColor(self._circle_color))
            p.drawEllipse(self._position, 3, 22, 22)
        else:
            p.setBrush(QColor(self._active_color))
            p.drawRoundedRect(0, 0, rect.width(), 28, 14, 14)
            p.setBrush(QColor(self._circle_color))
            p.drawEllipse(self._position, 3, 22, 22)

        p.end()


class PyQtSignal(QObject):
    log = Signal(str)


class PyLogOutput(logging.Handler):
    def __init__(self, parent=None):
        super().__init__()
        self.widget = QPlainTextEdit(parent)
        self.widget.setReadOnly(True)
        self.signal.log.connect(self.widget.appendHtml)

    @cached_property
    def signal(self):
        return PyQtSignal()

    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        color = {logging.ERROR: 'red', logging.INFO: 'white',
                 logging.WARNING: 'orange', logging.DEBUG: 'gray'}
        msg = '<span style="color:' + color[record.levelno] + ';">' + msg + "</span>"
        self.signal.log.emit(msg)


class PyCheckableComboBox(QComboBox):
    # once there is a checkState set, it is rendered
    # here we assume default Unchecked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_checked = False

    def addItem(self, item, state=Qt.Unchecked, enabled=True):
        super(PyCheckableComboBox, self).addItem(item)
        item: QCheckBox = self.model().item(self.count() - 1, 0)
        item.setFlags(Qt.ItemIsUserCheckable)
        item.setCheckState(state)
        item.setEnabled(enabled)

    def itemChecked(self, index):
        item = self.model().item(index, 0)
        return item.checkState() == Qt.Checked

    def checkAll(self):
        self.all_checked = False if self.all_checked else True
        for i in range(self.count()):
            item: QCheckBox = self.model().item(i, 0)
            if item.isEnabled() == False:
                continue
            if self.all_checked and item.checkState() != Qt.Checked:
                item.setCheckState(Qt.Checked)
            elif self.all_checked is False and item.checkState() == Qt.Checked:
                item.setCheckState(Qt.Unchecked)
