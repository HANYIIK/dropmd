from PySide6.QtCore import QCoreApplication, QEasingCurve, QEvent, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
from shiboken6 import isValid

from dropmd.motion import flash_feedback


def flush_deletions():
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_disabled_or_hidden_feedback_creates_no_overlay(qt_app):
    widget = QWidget()
    assert flash_feedback(widget, QColor("red"), enabled=True) is None
    widget.show()
    assert flash_feedback(widget, QColor("red"), enabled=False) is None
    assert widget.findChildren(QWidget) == []
    assert widget.graphicsEffect() is None
    widget.close()


def test_feedback_uses_short_opacity_animation_without_changing_layout(qt_app):
    widget = QWidget()
    layout = QVBoxLayout(widget)
    button = QPushButton("复制")
    layout.addWidget(button)
    widget.resize(180, 70)
    widget.show()
    qt_app.processEvents()
    original_geometry = widget.geometry()
    original_button_geometry = button.geometry()

    overlay = flash_feedback(widget, QColor("#008577"), enabled=True)

    assert overlay.parentWidget() is widget
    assert overlay.animation.duration() == 240
    assert overlay.animation.easingCurve().type() == QEasingCurve.Type.OutQuart
    assert overlay.animation.propertyName() == b"feedbackOpacity"
    assert overlay.animation.startValue() == 1.0
    assert overlay.animation.endValue() == 0.0
    assert overlay.geometry() == widget.rect()
    assert overlay.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    assert overlay.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert QApplication.widgetAt(button.mapToGlobal(button.rect().center())) is button
    assert widget.geometry() == original_geometry
    assert button.geometry() == original_button_geometry
    assert layout.count() == 1
    assert widget.graphicsEffect() is None
    widget.close()


def test_feedback_only_paints_border_and_preserves_content(qt_app):
    widget = QWidget()
    widget.resize(100, 60)
    widget.setStyleSheet("background: #e5eeee;")
    widget.show()
    qt_app.processEvents()
    before = widget.grab().toImage()

    overlay = flash_feedback(widget, QColor("#008577"), enabled=True)
    overlay.animation.pause()
    after = widget.grab().toImage()
    center = before.rect().center()
    edge_x = before.width() // 2
    edge_y = round(before.devicePixelRatio())

    assert after.pixelColor(center) == before.pixelColor(center)
    assert after.pixelColor(edge_x, edge_y) != before.pixelColor(edge_x, edge_y)
    widget.close()


def test_repeated_feedback_reuses_overlay_and_clamps_duration(qt_app):
    widget = QWidget()
    widget.show()
    first = flash_feedback(widget, QColor("red"), enabled=True, duration=80)
    first.animation.setCurrentTime(40)

    second = flash_feedback(widget, QColor("blue"), enabled=True, duration=600, radius=3)

    assert second is first
    assert first.animation.duration() == 300
    assert first.animation.currentTime() == 0
    assert first.feedbackOpacity == 1.0
    assert first._color.name() == "#0000ff"
    assert first._radius == 3
    assert len(widget.findChildren(QWidget)) == 1
    widget.close()


def test_feedback_cleans_up_after_completion(qt_app, qt_wait_until):
    widget = QWidget()
    widget.show()
    overlay = flash_feedback(widget, QColor("red"), enabled=True, duration=40)
    animation = overlay.animation

    qt_wait_until(lambda: not hasattr(widget, "_dropmd_feedback_overlay"))
    flush_deletions()

    assert not hasattr(widget, "_dropmd_feedback_overlay")
    assert not isValid(overlay)
    assert not isValid(animation)
    assert widget.isVisible()
    assert widget.graphicsEffect() is None
    widget.close()


def test_feedback_tracks_resize_without_resizing_target(qt_app):
    widget = QWidget()
    widget.show()
    overlay = flash_feedback(widget, QColor("red"), enabled=True)

    widget.resize(270, 120)

    assert widget.width() == 270
    assert widget.height() == 120
    assert overlay.geometry() == widget.rect()
    widget.close()


def test_disabling_feedback_cancels_existing_animation(qt_app):
    widget = QWidget()
    widget.show()
    overlay = flash_feedback(widget, QColor("red"), enabled=True)

    assert flash_feedback(widget, QColor("red"), enabled=False) is None
    flush_deletions()

    assert not isValid(overlay)
    assert not hasattr(widget, "_dropmd_feedback_overlay")
    assert widget.findChildren(QWidget) == []
    widget.close()


def test_hiding_or_destroying_parent_cleans_up_feedback(qt_app):
    widget = QWidget()
    widget.show()
    overlay = flash_feedback(widget, QColor("red"), enabled=True)
    widget.hide()
    flush_deletions()
    assert not isValid(overlay)
    assert not hasattr(widget, "_dropmd_feedback_overlay")

    widget.show()
    replacement = flash_feedback(widget, QColor("red"), enabled=True)
    animation = replacement.animation
    widget.deleteLater()
    flush_deletions()
    assert not isValid(replacement)
    assert not isValid(animation)
