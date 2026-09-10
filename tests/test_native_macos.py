import sys
import time
from contextlib import contextmanager

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMainWindow

from dropmd.app import MainWindow


def wait_until(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        QTest.qWait(50)
    assert predicate()


@contextmanager
def native_notification(name, window):
    from AppKit import NSNotificationCenter

    received = []
    center = NSNotificationCenter.defaultCenter()
    observer = center.addObserverForName_object_queue_usingBlock_(name, window, None, lambda note: received.append(True))
    try:
        yield lambda: bool(received)
    finally:
        center.removeObserver_(observer)


def close_test_window(window):
    import objc

    native = objc.objc_object(c_void_p=int(window.winId())).window()
    try:
        window.close()
    finally:
        window.deleteLater()
        QCoreApplication.sendPostedEvents(window, QEvent.Type.DeferredDelete)
        QTest.qWait(300)
    wait_until(lambda: not native.isVisible())


def prepare_minimize_window(window, qt_app):
    import objc

    window.setMinimumSize(760, 660)
    window.resize(920, 760)
    window.move(qt_app.primaryScreen().availableGeometry().center() - window.rect().center())
    window.show()
    assert QTest.qWaitForWindowExposed(window)
    native = objc.objc_object(c_void_p=int(window.winId())).window()
    window.activateWindow()
    assert QTest.qWaitForWindowActive(window)
    wait_until(native.isKeyWindow)
    QTest.qWait(300)
    assert native.isKeyWindow()
    return native


def change_minimized_state(window, native, expected, timeout=5):
    from AppKit import NSWindowDidDeminiaturizeNotification, NSWindowDidMiniaturizeNotification

    name = NSWindowDidMiniaturizeNotification if expected else NSWindowDidDeminiaturizeNotification
    with native_notification(name, native) as completed:
        window.showMinimized() if expected else window.showNormal()
        deadline = time.monotonic() + timeout
        stable_since = None
        while time.monotonic() < deadline:
            if completed() and native.isMiniaturized() == expected and window.isMinimized() == expected:
                if stable_since is None:
                    stable_since = time.monotonic()
                elif time.monotonic() - stable_since >= 0.3:
                    return True
            else:
                stable_since = None
            QTest.qWait(50)
    return False


@pytest.fixture(autouse=True)
def keep_test_application_alive(qt_app):
    previous = qt_app.quitOnLastWindowClosed()
    qt_app.setQuitOnLastWindowClosed(False)
    try:
        yield
    finally:
        qt_app.setQuitOnLastWindowClosed(previous)


def test_cocoa_uses_standard_buttons_and_system_chrome(qt_app, tmp_path):
    if sys.platform != "darwin" or QApplication.platformName() != "cocoa":
        pytest.skip("Requires the real macOS Cocoa platform")
    from AppKit import NSAppearanceNameAqua, NSAppearanceNameDarkAqua, NSButton

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow("light", settings)
    try:
        window.show()
        assert QTest.qWaitForWindowExposed(window)
        chrome = window.native_chrome
        assert chrome is not None
        assert not window.windowFlags() & Qt.FramelessWindowHint
        assert window.title_bar.close_button is None
        assert window.surface.graphicsEffect() is None
        assert window.canvas_layout.contentsMargins().isNull()
        buttons = chrome.buttons
        assert all(isinstance(button, NSButton) for button in buttons)
        assert all(button.isEnabled() and not button.isHidden() for button in buttons)
        assert all(button.toolTip() is None for button in buttons)
        assert len({button.superview() for button in buttons}) == 1
        for mode, appearance in (("dark", NSAppearanceNameDarkAqua), ("light", NSAppearanceNameAqua)):
            window.set_theme_mode(mode)
            assert chrome.window.appearance().name() == appearance
        window.set_theme_mode("system")
        assert chrome.window.appearance() is None
    finally:
        close_test_window(window)


def test_cocoa_fullscreen_restore_keeps_native_buttons(qt_app, tmp_path):
    if sys.platform != "darwin" or QApplication.platformName() != "cocoa":
        pytest.skip("Requires the real macOS Cocoa platform")

    from AppKit import NSWindowDidEnterFullScreenNotification, NSWindowDidExitFullScreenNotification, NSWindowStyleMaskFullScreen

    settings = QSettings(str(tmp_path / "states.ini"), QSettings.Format.IniFormat)
    window = MainWindow("light", settings)
    try:
        window.show()
        assert QTest.qWaitForWindowExposed(window)
        native = window.native_chrome.window
        window.activateWindow()
        assert QTest.qWaitForWindowActive(window)
        with native_notification(NSWindowDidEnterFullScreenNotification, native) as entered:
            window.showFullScreen()
            wait_until(entered)
        assert window.isFullScreen() and native.styleMask() & NSWindowStyleMaskFullScreen
        with native_notification(NSWindowDidExitFullScreenNotification, native) as exited:
            window.showNormal()
            wait_until(exited)
        assert not window.isFullScreen() and not native.styleMask() & NSWindowStyleMaskFullScreen
        wait_until(lambda: all(button.isEnabled() and not button.isHidden() for button in window.native_chrome.buttons))
        for button in window.native_chrome.buttons:
            assert button.isEnabled() and not button.isHidden()
            assert button.toolTip() is None
            rect = button.convertRect_toView_(button.bounds(), native.contentView())
            assert rect.origin.y >= 0
            assert rect.origin.y + rect.size.height <= window.title_bar.height()
            assert rect.origin.x + rect.size.width < window.title_bar.layout().contentsMargins().left()
        assert window.canvas_layout.contentsMargins().isNull()
    finally:
        close_test_window(window)


def test_cocoa_minimize_restore_when_host_supports_it(qt_app, tmp_path):
    if sys.platform != "darwin" or QApplication.platformName() != "cocoa":
        pytest.skip("Requires the real macOS Cocoa platform")
    probe = QMainWindow()
    try:
        native_probe = prepare_minimize_window(probe, qt_app)
        supported = change_minimized_state(probe, native_probe, True)
        if supported:
            assert change_minimized_state(probe, native_probe, False), "Standard Qt window did not finish restoring"
    finally:
        close_test_window(probe)
    if not supported:
        pytest.skip("Standard native Qt window received no completed, stable minimization on this host")

    settings = QSettings(str(tmp_path / "minimize.ini"), QSettings.Format.IniFormat)
    window = MainWindow("light", settings)
    try:
        native = prepare_minimize_window(window, qt_app)
        assert change_minimized_state(window, native, True), "DropMD did not finish minimizing after the standard Qt window succeeded"
        assert change_minimized_state(window, native, False), "DropMD did not finish restoring"
        assert all(button.toolTip() is None for button in window.native_chrome.buttons)
        assert window.canvas_layout.contentsMargins().isNull()
    finally:
        close_test_window(window)
