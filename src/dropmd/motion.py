from PySide6.QtCore import QEasingCurve, QEvent, Property, QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class _FeedbackOverlay(QWidget):
    def __init__(self, target: QWidget):
        super().__init__(target)
        self.setObjectName("feedbackOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._opacity = 0.0
        self._color = QColor()
        self._radius = 0.0
        self._disposed = False
        self.animation = QPropertyAnimation(self, b"feedbackOpacity", self)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuart)
        self.animation.finished.connect(self.dispose)
        target.installEventFilter(self)

    def _get_opacity(self) -> float:
        return self._opacity

    def _set_opacity(self, value: float) -> None:
        self._opacity = value
        self.update()

    feedbackOpacity = Property(float, _get_opacity, _set_opacity)

    def start(self, color: QColor, duration: int, radius: float) -> None:
        self.animation.stop()
        self._color = QColor(color)
        self._color.setAlphaF(self._color.alphaF() * 0.7)
        self._radius = max(0.0, radius)
        self.setGeometry(self.parentWidget().rect())
        self.animation.setDuration(max(1, min(duration, 300)))
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self._set_opacity(1.0)
        self.show()
        self.raise_()
        self.animation.start()

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        self.animation.stop()
        target = self.parentWidget()
        if target is not None:
            target.removeEventFilter(self)
            if getattr(target, "_dropmd_feedback_overlay", None) is self:
                del target._dropmd_feedback_overlay
        self.hide()
        self.deleteLater()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Resize:
            self.setGeometry(watched.rect())
        elif event.type() == QEvent.Type.Hide:
            self.dispose()
        return False

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self._opacity)
        painter.setPen(QPen(self._color, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        rectangle = self.rect().toRectF().adjusted(1.0, 1.0, -1.0, -1.0)
        radius = min(self._radius, rectangle.width() / 2, rectangle.height() / 2)
        painter.drawRoundedRect(rectangle, radius, radius)


def flash_feedback(
    widget: QWidget,
    color: QColor,
    *,
    enabled: bool,
    duration: int = 240,
    radius: float = 8,
) -> _FeedbackOverlay | None:
    overlay = getattr(widget, "_dropmd_feedback_overlay", None)
    if not enabled or not widget.isVisible():
        if overlay is not None:
            overlay.dispose()
        return None
    if overlay is None:
        overlay = _FeedbackOverlay(widget)
        widget._dropmd_feedback_overlay = overlay
    overlay.start(color, duration, radius)
    return overlay
