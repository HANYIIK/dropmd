import pytest
from PySide6.QtCore import QPoint, Qt, QAbstractAnimation, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from dropmd.app import TitleBar
from dropmd.menus import RoundedMenu
from dropmd.styles import stylesheet


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_menu_has_transparent_corners_without_native_square_frame(qt_app, theme):
    menu = RoundedMenu(animations_enabled=False)
    menu.setStyleSheet(stylesheet(theme))
    for title in ("跟随系统", "浅色", "深色"):
        menu.addAction(title)
    menu.popup(QPoint(100, 100))
    qt_app.processEvents()
    assert menu.windowFlags() & Qt.FramelessWindowHint
    assert menu.windowFlags() & Qt.NoDropShadowWindowHint
    assert menu.testAttribute(Qt.WA_TranslucentBackground)
    image = menu.grab().toImage()
    for x, y in ((0, 0), (image.width() - 1, 0), (0, image.height() - 1), (image.width() - 1, image.height() - 1)):
        assert image.pixelColor(x, y).alpha() == 0
    assert image.pixelColor(image.width() // 2, 3).alpha() == 255
    if QApplication.platformName() == "cocoa":
        import objc
        from AppKit import NSWindowStyleMaskTitled, NSWindowStyleMaskResizable

        native_window = objc.objc_object(c_void_p=int(menu.winId())).window()
        assert not native_window.styleMask() & (NSWindowStyleMaskTitled | NSWindowStyleMaskResizable)
        assert not native_window.hasShadow()
        assert not native_window.isOpaque()
    menu.close()


def test_menu_supports_keyboard_selection_and_escape(qt_app):
    menu = RoundedMenu(animations_enabled=False)
    selected = []
    first = menu.addAction("跟随系统")
    second = menu.addAction("深色")
    second.triggered.connect(lambda: selected.append("dark"))
    menu.popup(QPoint(100, 100))
    menu.setActiveAction(first)
    QTest.keyClick(menu, Qt.Key_Down)
    QTest.keyClick(menu, Qt.Key_Return)
    assert selected == ["dark"]
    assert not menu.isVisible()
    menu.popup(QPoint(100, 100))
    QTest.keyClick(menu, Qt.Key_Escape)
    assert not menu.isVisible()


def test_menu_animation_cleans_up_when_closed_and_reopened(qt_app, qt_wait_until):
    menu = RoundedMenu(animations_enabled=True)
    menu.addAction("浅色")
    menu.popup(QPoint(100, 100))
    assert menu.reveal_animation.state() == QAbstractAnimation.Running
    menu.close()
    assert menu.reveal_animation.state() == QAbstractAnimation.Stopped
    assert menu.windowOpacity() == 1.0
    menu.popup(QPoint(100, 100))
    qt_wait_until(lambda: menu.reveal_animation.state() == QAbstractAnimation.Stopped)
    assert menu.windowOpacity() == 1.0
    menu.close()
    menu.animations_enabled = False
    menu.popup(QPoint(100, 100))
    assert menu.reveal_animation.state() == QAbstractAnimation.Stopped
    assert menu.windowOpacity() == 1.0
    menu.close()


def test_theme_button_opens_menu_and_selection_updates(qt_app):
    titlebar = TitleBar(animations_enabled=True)
    titlebar.resize(400, 54)
    titlebar.show()
    titlebar.set_theme("light", "light")
    selected = []
    titlebar.themeModeRequested.connect(selected.append)
    observed = []

    def choose_dark():
        observed.append(titlebar.theme_menu.isVisible())
        titlebar.theme_menu.setActiveAction(titlebar.theme_actions["dark"])
        QTest.keyClick(titlebar.theme_menu, Qt.Key_Return)
        titlebar.theme_menu.close()

    QTimer.singleShot(200, choose_dark)
    titlebar.theme_button.showMenu()
    QTest.qWait(300)
    assert observed == [True]
    assert selected == ["dark"]
    assert not titlebar.theme_menu.isVisible()
    titlebar.close()
