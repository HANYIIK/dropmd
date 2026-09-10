from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtWidgets import QMenu


class RoundedMenu(QMenu):
    def __init__(self, parent=None, *, animations_enabled=True):
        super().__init__(parent)
        self.animations_enabled = animations_enabled
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.reveal_animation = QPropertyAnimation(self, b"windowOpacity", self)
        self.reveal_animation.setDuration(150)
        self.reveal_animation.setEasingCurve(QEasingCurve.OutQuart)

    def showEvent(self, event):
        self.reveal_animation.stop()
        self.setWindowOpacity(0.55 if self.animations_enabled else 1.0)
        super().showEvent(event)
        if self.animations_enabled:
            self.reveal_animation.setStartValue(0.55)
            self.reveal_animation.setEndValue(1.0)
            self.reveal_animation.start()

    def hideEvent(self, event):
        self.reveal_animation.stop()
        self.setWindowOpacity(1.0)
        super().hideEvent(event)
