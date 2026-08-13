from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from dropmd.app import JobRow, MainWindow


def test_copy_markdown_places_full_content_on_clipboard(qt_app: QApplication, tmp_path: Path):
    source = tmp_path / "示例.docx"
    destination = tmp_path / "示例.md"
    markdown = "# 标题\n\n完整 Markdown 内容。\n"
    destination.write_text(markdown, encoding="utf-8")
    row = JobRow(source)
    row.mark_success(destination)

    row._copy_markdown()

    assert qt_app.clipboard().text() == markdown
    assert row.copy_button.text() == "已复制 ✓"


def test_theme_toggle_is_persisted(qt_app: QApplication, tmp_path: Path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow("light", settings)

    window.toggle_theme()

    assert window.theme == "dark"
    assert settings.value("theme") == "dark"
    window.close()


def test_window_controls_are_available(qt_app: QApplication, tmp_path: Path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow("light", settings)

    assert window.title_bar.close_button.accessibleName() == "关闭"
    assert window.title_bar.minimize_button.accessibleName() == "最小化"
    assert window.title_bar.maximize_button.accessibleName() == "最大化"
    window.close()
