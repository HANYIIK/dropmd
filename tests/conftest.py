import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qt_app():
    application = QApplication.instance() or QApplication([])
    application.setStyle("Fusion")
    return application
