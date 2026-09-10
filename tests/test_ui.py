from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from shiboken6 import isValid

from dropmd.app import ConversionWorker, JobRow, MainWindow, TitleBar, prefers_reduced_motion, system_theme


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


def test_repeated_copy_restarts_confirmation_timer(qt_app, qt_wait_until, tmp_path):
    destination = tmp_path / "example.md"
    destination.write_text("# Example\n", encoding="utf-8")
    row = JobRow(tmp_path / "example.txt", animations_enabled=False)
    row.mark_success(destination)
    row.copy_markdown()
    row.copy_reset_timer.start(30)

    row.copy_markdown()
    QTest.qWait(60)

    assert row.copy_button.text() == "已复制 ✓"
    assert row.copy_reset_timer.isActive()
    assert row.copy_reset_timer.interval() == 1800
    row.copy_reset_timer.start(10)
    qt_wait_until(lambda: row.copy_button.text() == "复制")
    assert row.copy_button.text() == "复制"
    assert row.copy_button.property("copied") is False
    row.close()


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


def test_excel_color_option_is_front_facing_off_by_default_and_persisted(
    qt_app: QApplication, tmp_path: Path
):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow("system", settings)

    assert window.preserve_excel_colors.text() == "Excel 保留颜色"
    assert window.preserve_excel_colors.isChecked() is False
    assert window.preserve_excel_colors.accessibleName() == "Excel 保留单元格颜色"
    assert "仅适用于 XLSX" in window.preserve_excel_colors.toolTip()

    window.preserve_excel_colors.setChecked(True)

    assert settings.value("preserve_excel_colors", type=bool) is True
    window.close()

    restored = MainWindow("system", settings)
    assert restored.preserve_excel_colors.isChecked() is True
    restored.close()


def test_conversion_worker_uses_the_front_facing_excel_color_snapshot(
    qt_app: QApplication, tmp_path: Path, monkeypatch
):
    source = tmp_path / "颜色.xlsx"
    destination = tmp_path / "颜色.md"
    captured: dict[str, object] = {}

    def fake_convert(path: Path, **kwargs: object) -> Path:
        captured["path"] = path
        captured.update(kwargs)
        return destination

    monkeypatch.setattr("dropmd.app.convert_file", fake_convert)

    ConversionWorker(source, overwrite=False, preserve_excel_colors=True).run()

    assert captured == {
        "path": source,
        "overwrite": False,
        "preserve_excel_colors": True,
    }


def test_completed_row_has_reveal_and_retry_actions(qt_app: QApplication, tmp_path: Path):
    source = tmp_path / "示例.pdf"
    destination = tmp_path / "示例.md"
    destination.write_text("# Done\n", encoding="utf-8")
    row = JobRow(source)

    row.mark_success(destination)

    assert row.status.minimumWidth() == 0
    assert row.status.minimumHeight() == 24
    assert row.status.maximumHeight() == 24
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


def test_window_controls_have_no_tooltips_after_maximize_and_restore(qt_app, tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow("light", settings)
    for state in (Qt.WindowNoState, Qt.WindowMaximized, Qt.WindowNoState):
        window.setWindowState(state)
        qt_app.processEvents()
        for button in (
            window.title_bar.close_button,
            window.title_bar.minimize_button,
            window.title_bar.maximize_button,
        ):
            assert button.toolTip() == ""
    assert window.title_bar.maximize_button.accessibleName() == "最大化"
    window.close()


def test_native_titlebar_does_not_create_duplicate_qt_controls(qt_app):
    titlebar = TitleBar(native_controls=True)
    assert titlebar.close_button is None
    assert titlebar.minimize_button is None
    assert titlebar.maximize_button is None
    assert titlebar.theme_button.accessibleName() == "外观设置"
    titlebar.close()


def test_native_window_preserves_system_frame_in_all_states(qt_app, tmp_path, monkeypatch):
    class FakeChrome:
        def __init__(self, widget):
            widget.winId()
            self.mode = None

        def leading_inset(self):
            return 92

        def set_theme(self, mode):
            self.mode = mode

    monkeypatch.setattr("dropmd.app.uses_native_titlebar", lambda: True)
    monkeypatch.setattr("dropmd.app.MacWindowChrome", FakeChrome)
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow("system", settings)
    assert window.windowFlags() & Qt.ExpandedClientAreaHint
    assert window.windowFlags() & Qt.NoTitleBarBackgroundHint
    assert not window.windowFlags() & Qt.FramelessWindowHint
    assert window.shadow is None
    assert not window.testAttribute(Qt.WA_TranslucentBackground)
    for state in (Qt.WindowMaximized, Qt.WindowFullScreen, Qt.WindowNoState):
        window.setWindowState(state)
        qt_app.processEvents()
        assert window.canvas_layout.contentsMargins().isNull()
        assert window.surface.property("nativeChrome") is True
    for mode in ("light", "dark", "system"):
        window.set_theme_mode(mode)
        assert window.native_chrome.mode == mode
    assert window.title_bar.layout().contentsMargins().left() == 92
    window.close()


def test_notice_uses_padded_container(qt_app: QApplication, tmp_path: Path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow("light", settings)

    window._show_notice("已生成 example.md。", success=True)

    margins = window.notice_frame.layout().contentsMargins()
    assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (14, 9, 14, 9)
    assert window.notice_frame.objectName() == "noticeFrameSuccess"
    window.close()


def test_notice_animation_cleans_up_and_hides_without_layout_gap(qt_app: QApplication, tmp_path: Path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow("light", settings)
    window.animations_enabled = True
    window.show()

    window._show_notice("已生成 example.md。", success=True)

    assert window.notice_frame.graphicsEffect() is None
    window._hide_notice(window._notice_generation)
    assert window.notice_frame.isHidden()
    assert window.notice_frame.graphicsEffect() is None
    window.close()


def test_notice_timer_restarts_and_is_owned_by_window(qt_app, tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow("light", settings)
    window.show()
    window._show_notice("已复制。", success=True)
    window.notice_timer.start(30)
    window._show_notice("请检查文件。", success=False)
    QTest.qWait(60)
    assert window.notice_frame.isVisible()
    assert window.notice.text() == "请检查文件。"
    assert window.notice_timer.isActive()
    assert window.notice_timer.interval() == 4200
    timer = window.notice_timer
    assert timer.parent() is window
    timer.start(30)
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert not isValid(timer)
    QTest.qWait(60)


def test_rows_are_top_aligned_without_trailing_stretch(qt_app: QApplication, tmp_path: Path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow("light", settings)

    assert window.rows_layout.alignment().name == "AlignTop"
    assert window.rows_layout.count() == 0
    window.close()


def test_completed_row_animation_never_hides_controls(qt_app: QApplication, tmp_path: Path):
    source = tmp_path / "示例.docx"
    destination = tmp_path / "示例.md"
    destination.write_text("# Done\n", encoding="utf-8")
    row = JobRow(source, animations_enabled=True)
    row.show()

    row.mark_success(destination)
    QTest.qWait(280)

    assert row.graphicsEffect() is None
    assert row.status.graphicsEffect() is None
    assert row.status.isVisible()
    assert row.copy_button.isVisible()
    assert row.open_button.isVisible()
    assert row.more_button.isVisible()
    assert row.status.height() == 24
    row.close()


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


def test_tall_window_keeps_compact_drop_zone_and_expands_history(qt_app: QApplication, tmp_path: Path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow("light", settings)
    window.resize(1100, 900)
    window.show()
    qt_app.processEvents()

    assert window.drop_zone.height() == 176
    assert window.list_panel.height() >= 320
    window.close()


def test_reduced_motion_environment_override(monkeypatch):
    monkeypatch.setenv("DROPMD_REDUCE_MOTION", "1")
    assert prefers_reduced_motion() is True

    monkeypatch.setenv("DROPMD_REDUCE_MOTION", "0")
    assert prefers_reduced_motion() is False


def test_reduced_motion_reaches_menus_and_feedback(qt_app, tmp_path, monkeypatch):
    monkeypatch.setenv("DROPMD_REDUCE_MOTION", "1")
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow("light", settings)
    window.show()
    qt_app.processEvents()
    window.set_theme_mode("dark")
    window.drop_zone._set_drag_active(True)
    window._show_notice("已生成 example.md。", success=True)

    assert window.animations_enabled is False
    assert window.title_bar.theme_menu.animations_enabled is False
    assert window.drop_zone.animations_enabled is False
    for target in (window.title_bar.theme_button, window.drop_zone, window.notice_frame):
        assert not hasattr(target, "_dropmd_feedback_overlay")
    row = JobRow(tmp_path / "example.txt", animations_enabled=window.animations_enabled)
    assert row.more_menu.animations_enabled is False
    row.close()
    window.close()


def test_feedback_integrations_preserve_layout_and_clean_up(qt_app, qt_wait_until, tmp_path, monkeypatch):
    monkeypatch.setenv("DROPMD_REDUCE_MOTION", "0")
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow("light", settings)
    destination = tmp_path / "example.md"
    destination.write_text("# Example\n", encoding="utf-8")
    row = JobRow(tmp_path / "example.txt", animations_enabled=window.animations_enabled)
    window.rows_layout.addWidget(row)
    window.panel_stack.setCurrentWidget(window.scroll)
    window.show()
    qt_app.processEvents()

    window.drop_zone._set_drag_active(True)
    row.mark_success(destination)
    qt_app.processEvents()
    geometry = row.geometry()
    row.copy_markdown()
    window._show_notice("已生成 example.md。", success=True)
    window._show_notice("请检查文件。", success=False)
    targets = (window.drop_zone, row, row.copy_button, window.notice_frame)
    assert all(hasattr(target, "_dropmd_feedback_overlay") for target in targets)
    assert window.rows_layout.count() == 1
    assert row.geometry() == geometry
    assert row.status.height() == 24
    qt_wait_until(lambda: all(not hasattr(target, "_dropmd_feedback_overlay") for target in targets))
    assert all(not hasattr(target, "_dropmd_feedback_overlay") for target in targets)
    assert all(target.graphicsEffect() is None for target in targets)
    assert row.copy_button.isVisible()
    assert row.more_button.isVisible()
    assert window.notice_frame.isVisible()
    window._hide_notice(window._notice_generation)
    assert window.notice_frame.isHidden()
    window.close()
