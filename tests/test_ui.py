from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from dropmd.app import JobRow, MainWindow, prefers_reduced_motion, system_theme


def test_copy_markdown_places_full_content_on_clipboard(qt_app: QApplication, tmp_path: Path):
    source = tmp_path / "示例.docx"
    destination = tmp_path / "示例.md"
    markdown = "# 标题\n\n完整 Markdown 内容。\n"
    destination.write_text(markdown, encoding="utf-8")
    row = JobRow(source)
    row.mark_success(destination)

    row.copy_markdown()

    assert qt_app.clipboard().text() == markdown
    assert row.copy_button.text() == "已复制 ✓"


def test_theme_mode_is_persisted(qt_app: QApplication, tmp_path: Path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow("system", settings)

    window.set_theme_mode("dark")

    assert window.theme == "dark"
    assert window.theme_mode == "dark"
    assert settings.value("theme_mode") == "dark"
    window.close()


def test_system_theme_is_default_and_resolved(qt_app: QApplication, tmp_path: Path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow("system", settings)

    assert window.theme_mode == "system"
    assert window.theme == system_theme(qt_app)
    assert window.title_bar.theme_actions["system"].isChecked()
    window.close()


def test_completed_row_has_reveal_and_retry_actions(qt_app: QApplication, tmp_path: Path):
    source = tmp_path / "示例.pdf"
    destination = tmp_path / "示例.md"
    destination.write_text("# Done\n", encoding="utf-8")
    row = JobRow(source)

    row.mark_success(destination)

    assert row.status.minimumWidth() == 0
    assert row.status.minimumHeight() == 24
    assert row.more_button.isHidden() is False
    assert row.retry_action.isVisible() is False

    row.mark_error("文件损坏，请换一个文件后重试")

    assert row.retry_action.isVisible() is True


def test_window_controls_are_available(qt_app: QApplication, tmp_path: Path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow("light", settings)

    assert window.title_bar.close_button.accessibleName() == "关闭"
    assert window.title_bar.minimize_button.accessibleName() == "最小化"
    assert window.title_bar.maximize_button.accessibleName() == "最大化"
    assert window.title_bar.theme_button.focusPolicy().name == "NoFocus"
    window.close()


def test_notice_uses_padded_container(qt_app: QApplication, tmp_path: Path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow("light", settings)

    window._show_notice("已生成 example.md。", success=True)

    margins = window.notice_frame.layout().contentsMargins()
    assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (14, 9, 14, 9)
    assert window.notice_frame.objectName() == "noticeFrameSuccess"
    window.close()


def test_rows_are_top_aligned_without_trailing_stretch(qt_app: QApplication, tmp_path: Path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow("light", settings)

    assert window.rows_layout.alignment().name == "AlignTop"
    assert window.rows_layout.count() == 0
    window.close()


def test_default_window_shows_three_history_rows_with_notice(qt_app: QApplication, tmp_path: Path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow("light", settings)
    window.resize(920, 760)
    for index in range(3):
        row = JobRow(tmp_path / f"项目资料 {index + 1}.docx", animations_enabled=False)
        window.rows_layout.addWidget(row)
    window.panel_stack.setCurrentWidget(window.scroll)
    window._show_notice("已生成 项目资料 3.md。", success=True)
    window.show()
    qt_app.processEvents()

    assert window.scroll.viewport().height() >= 3 * 66
    window.close()


def test_reduced_motion_environment_override(monkeypatch):
    monkeypatch.setenv("DROPMD_REDUCE_MOTION", "1")
    assert prefers_reduced_motion() is True

    monkeypatch.setenv("DROPMD_REDUCE_MOTION", "0")
    assert prefers_reduced_motion() is False
