from __future__ import annotations

import math
import sys

from PySide6.QtWidgets import QApplication, QWidget


def uses_native_titlebar() -> bool:
    return sys.platform == "darwin" and QApplication.platformName() == "cocoa"


class MacWindowChrome:
    def __init__(self, widget: QWidget):
        import objc
        from AppKit import NSToolbar, NSWindowTitleHidden, NSWindowToolbarStyleUnifiedCompact

        self.window = objc.objc_object(c_void_p=int(widget.winId())).window()
        self.toolbar = NSToolbar.alloc().initWithIdentifier_("com.dropmd.titlebar")
        self.toolbar.setShowsBaselineSeparator_(False)
        self.toolbar.setAllowsUserCustomization_(False)
        self.window.setTitleVisibility_(NSWindowTitleHidden)
        self.window.setToolbar_(self.toolbar)
        self.window.setToolbarStyle_(NSWindowToolbarStyleUnifiedCompact)
        for button in self.buttons:
            button.setToolTip_(None)

    @property
    def buttons(self) -> tuple:
        from AppKit import NSWindowCloseButton, NSWindowMiniaturizeButton, NSWindowZoomButton

        return tuple(
            self.window.standardWindowButton_(kind)
            for kind in (NSWindowCloseButton, NSWindowMiniaturizeButton, NSWindowZoomButton)
        )

    def leading_inset(self) -> int:
        frames = [
            button.convertRect_toView_(button.bounds(), self.window.contentView())
            for button in self.buttons
        ]
        return math.ceil(max(frame.origin.x + frame.size.width for frame in frames)) + 20

    def set_theme(self, mode: str) -> None:
        from AppKit import NSAppearance, NSAppearanceNameAqua, NSAppearanceNameDarkAqua

        appearance = None
        if mode != "system":
            name = NSAppearanceNameDarkAqua if mode == "dark" else NSAppearanceNameAqua
            appearance = NSAppearance.appearanceNamed_(name)
        self.window.setAppearance_(appearance)
