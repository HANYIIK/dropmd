from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QPropertyAnimation, QRunnable, QSettings, QSize, Qt, QThreadPool, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QDesktopServices, QDragEnterEvent, QDropEvent, QIcon, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from .converter import SUPPORTED_EXTENSIONS, convert_file, is_supported, output_path_for
from .styles import stylesheet


THEME_LABELS = {"system": "跟随系统", "light": "浅色", "dark": "深色"}


def system_theme(application: QApplication) -> str:
    return "dark" if application.styleHints().colorScheme() == Qt.ColorScheme.Dark else "light"


def prefers_reduced_motion() -> bool:
    override = os.environ.get("DROPMD_REDUCE_MOTION")
    if override is not None:
        return override.lower() in {"1", "true", "yes"}
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return True
    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["defaults", "read", "com.apple.universalaccess", "reduceMotion"],
                capture_output=True,
                timeout=0.3,
                check=False,
            )
            return result.stdout.strip() == b"1"
        except (OSError, subprocess.SubprocessError):
            return False
    if sys.platform == "win32":
        try:
            import ctypes

            enabled = ctypes.c_int()
            ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0)
            return not bool(enabled.value)
        except (AttributeError, OSError):
            return False
    return False


def fade_widget(
    widget: QWidget,
    *,
    enabled: bool,
    start: float = 0.0,
    end: float = 1.0,
    duration: int = 220,
    hide_when_finished: bool = False,
) -> None:
    previous = getattr(widget, "_fade_animation", None)
    if previous:
        previous.stop()
    previous_effect = widget.graphicsEffect()
    if isinstance(previous_effect, QGraphicsOpacityEffect):
        widget.setGraphicsEffect(None)
    if not enabled:
        widget.setVisible(not hide_when_finished)
        return
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    effect.setOpacity(start)
    widget.show()
    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(duration)
    animation.setStartValue(start)
    animation.setEndValue(end)
    animation.setEasingCurve(QEasingCurve.Type.OutQuart)
    def finish() -> None:
        if hide_when_finished:
            widget.hide()
        if widget.graphicsEffect() is effect:
            widget.setGraphicsEffect(None)
        widget._fade_animation = None

    animation.finished.connect(finish)
    widget._fade_animation = animation
    animation.start()


class DesktopApplication(QApplication):
    filesOpened = Signal(object)

    def __init__(self, arguments: list[str]):
        self._pending_files: list[Path] = []
        self._file_handler_ready = False
        super().__init__(arguments)

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.FileOpen:
            path = event.file()
            if path:
                if self._file_handler_ready:
                    self.filesOpened.emit([Path(path)])
                else:
                    self._pending_files.append(Path(path))
                return True
        return super().event(event)

    def enable_file_handler(self) -> list[Path]:
        self._file_handler_ready = True
        pending, self._pending_files = self._pending_files, []
        return pending


class WorkerSignals(QObject):
    started = Signal(object)
    succeeded = Signal(object, object)
    failed = Signal(object, str)


class ConversionWorker(QRunnable):
    def __init__(self, source: Path, overwrite: bool):
        super().__init__()
        self.source = source
        self.overwrite = overwrite
        self.signals = WorkerSignals()

    def run(self) -> None:
        self.signals.started.emit(self.source)
        try:
            destination = convert_file(self.source, overwrite=self.overwrite)
        except Exception as error:
            message = str(error).strip() or error.__class__.__name__
            self.signals.failed.emit(self.source, message)
        else:
            self.signals.succeeded.emit(self.source, destination)


class TitleBar(QFrame):
    themeModeRequested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("titleBar")
        self.setFixedHeight(54)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 14, 0)
        layout.setSpacing(8)

        self.close_button = self._control_button("×", "closeButton", "关闭")
        self.minimize_button = self._control_button("−", "minimizeButton", "最小化")
        self.maximize_button = self._control_button("+", "maximizeButton", "最大化")
        self.close_button.clicked.connect(lambda: self.window().close())
        self.minimize_button.clicked.connect(lambda: self.window().showMinimized())
        self.maximize_button.clicked.connect(self._toggle_maximized)

        brand = QLabel("DROPMD")
        brand.setObjectName("brandMark")

        self.theme_button = QPushButton("◐")
        self.theme_button.setObjectName("themeButton")
        self.theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_button.setAccessibleName("外观设置")
        self.theme_button.setToolTip("外观设置")
        self.theme_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.theme_button.setFlat(True)

        self.theme_menu = QMenu(self.theme_button)
        self.theme_group = QActionGroup(self.theme_menu)
        self.theme_group.setExclusive(True)
        self.theme_actions: dict[str, QAction] = {}
        for mode in ("system", "light", "dark"):
            action = QAction(THEME_LABELS[mode], self.theme_menu)
            action.setCheckable(True)
            action.triggered.connect(lambda checked=False, selected=mode: self.themeModeRequested.emit(selected))
            self.theme_group.addAction(action)
            self.theme_menu.addAction(action)
            self.theme_actions[mode] = action
        self.theme_button.setMenu(self.theme_menu)

        layout.addWidget(self.close_button)
        layout.addWidget(self.minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addSpacing(12)
        layout.addWidget(brand)
        layout.addStretch()
        layout.addWidget(self.theme_button)

    @staticmethod
    def _control_button(text: str, name: str, accessible_name: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName(name)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setAccessibleName(accessible_name)
        button.setToolTip(accessible_name)
        return button

    def set_theme(self, mode: str, resolved_theme: str) -> None:
        self.theme_actions[mode].setChecked(True)
        self.theme_button.setText("◐" if mode == "system" else ("☀" if resolved_theme == "dark" else "☾"))
        self.theme_button.setToolTip(f"外观：{THEME_LABELS[mode]}")

    def _toggle_maximized(self) -> None:
        window = self.window()
        window.showNormal() if window.isMaximized() else window.showMaximized()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle:
                handle.startSystemMove()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximized()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class DropZone(QFrame):
    filesDropped = Signal(list)

    def __init__(self, *, animations_enabled: bool = True):
        super().__init__()
        self.animations_enabled = animations_enabled
        self.setObjectName("dropZone")
        self.setProperty("dragActive", False)
        self.setAcceptDrops(True)
        self.setFixedHeight(176)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 12, 32, 12)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon = QLabel("↓")
        self.icon.setObjectName("dropIcon")
        self.icon.setFixedSize(44, 44)
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("将文件拖到这里")
        title.setObjectName("dropTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("自动在原目录生成同名 Markdown 文件")
        hint.setObjectName("caption")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.choose_button = QPushButton("选择文件")
        self.choose_button.setObjectName("primaryButton")
        self.choose_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.choose_button.setShortcut("Ctrl+O")

        layout.addWidget(self.icon, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addSpacing(6)
        layout.addWidget(self.choose_button, alignment=Qt.AlignmentFlag.AlignCenter)

    def _set_drag_active(self, active: bool) -> None:
        self.setProperty("dragActive", active)
        self.icon.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)
        self.icon.style().unpolish(self.icon)
        self.icon.style().polish(self.icon)
        if active:
            fade_widget(self.icon, enabled=self.animations_enabled, start=0.38, end=1.0, duration=180)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()
            self._set_drag_active(True)

    def dragLeaveEvent(self, event) -> None:
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_drag_active(False)
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        self.filesDropped.emit(paths)
        event.acceptProposedAction()


class JobRow(QFrame):
    markdownCopied = Signal(object)
    copyFailed = Signal(str)
    retryRequested = Signal(object)

    def __init__(self, source: Path, *, animations_enabled: bool = True):
        super().__init__()
        self.animations_enabled = animations_enabled
        self.source = source
        self.destination: Path | None = None
        self.state = "pending"
        self.setObjectName("jobRow")
        self.setFixedHeight(66)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 7, 10, 7)
        layout.setSpacing(11)

        file_icon = QLabel(source.suffix[1:].upper()[:4] or "FILE")
        file_icon.setObjectName("fileType")
        file_icon.setFixedSize(40, 36)
        file_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        details = QVBoxLayout()
        details.setSpacing(3)
        name = QLabel(source.name)
        name.setObjectName("fileName")
        name.setToolTip(str(source))
        self.meta = QLabel(str(source.parent))
        self.meta.setObjectName("path")
        self.meta.setToolTip(str(source.parent))
        self.meta.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        details.addWidget(name)
        details.addWidget(self.meta)

        self.status = QLabel("等待转换")
        self.status.setObjectName("statusPending")
        self.status.setFixedHeight(24)
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.copy_button = QPushButton("复制")
        self.copy_button.setObjectName("copyButton")
        self.copy_button.setProperty("copied", False)
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_button.setAccessibleName("复制 Markdown 内容")
        self.copy_button.clicked.connect(self.copy_markdown)
        self.copy_button.hide()

        self.open_button = QPushButton("打开")
        self.open_button.setObjectName("linkButton")
        self.open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_button.clicked.connect(self._open_destination)
        self.open_button.hide()

        self.more_button = QPushButton("•••")
        self.more_button.setObjectName("moreButton")
        self.more_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.more_button.setAccessibleName("更多操作")
        self.more_button.setToolTip("更多操作")
        self.more_menu = QMenu(self.more_button)
        reveal_action = self.more_menu.addAction("在文件夹中显示")
        reveal_action.triggered.connect(self._reveal_destination)
        copy_path_action = self.more_menu.addAction("复制文件路径")
        copy_path_action.triggered.connect(self._copy_path)
        self.retry_action = self.more_menu.addAction("重新转换")
        self.retry_action.triggered.connect(lambda: self.retryRequested.emit(self.source))
        self.retry_action.setVisible(False)
        self.more_button.setMenu(self.more_menu)
        self.more_button.hide()

        layout.addWidget(file_icon)
        layout.addLayout(details, 1)
        layout.addWidget(self.status)
        layout.addWidget(self.copy_button)
        layout.addWidget(self.open_button)
        layout.addWidget(self.more_button)

    def mark_working(self) -> None:
        self.state = "working"
        self.status.setText("转换中…")
        self.status.setObjectName("statusWorking")
        self.copy_button.hide()
        self.open_button.hide()
        self.more_button.hide()
        self._refresh(self.status)

    def mark_success(self, destination: Path) -> None:
        self.state = "success"
        self.destination = destination
        size = destination.stat().st_size
        self.meta.setText(f"{self._format_size(size)} · {destination.parent}")
        self.meta.setToolTip(str(destination))
        self.status.setText("已完成")
        self.status.setObjectName("statusSuccess")
        self._refresh(self.status)
        self.copy_button.show()
        self.open_button.show()
        self.more_button.show()
        self.retry_action.setVisible(False)

    def mark_error(self, message: str) -> None:
        self.state = "error"
        self.status.setText("转换失败")
        self.status.setObjectName("statusError")
        self.status.setToolTip(message)
        self.meta.setText(message)
        self.meta.setToolTip(message)
        self.retry_action.setVisible(True)
        self.more_button.show()
        self._refresh(self.status)

    @staticmethod
    def _format_size(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.1f} MB"

    @staticmethod
    def _refresh(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def copy_markdown(self) -> bool:
        if not self.destination:
            return False
        try:
            markdown = self.destination.read_text(encoding="utf-8")
        except Exception as error:
            self.copyFailed.emit(str(error).strip() or "无法读取 Markdown 文件")
            return False
        QApplication.clipboard().setText(markdown)
        self.copy_button.setText("已复制 ✓")
        self.copy_button.setProperty("copied", True)
        self._refresh(self.copy_button)
        self.markdownCopied.emit(self.destination)
        QTimer.singleShot(1800, self._reset_copy_button)
        return True

    def _reset_copy_button(self) -> None:
        self.copy_button.setText("复制")
        self.copy_button.setProperty("copied", False)
        self._refresh(self.copy_button)

    def _open_destination(self) -> None:
        if self.destination:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.destination)))

    def _reveal_destination(self) -> None:
        if not self.destination:
            return
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(self.destination)])
        elif sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", str(self.destination)])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.destination.parent)))

    def _copy_path(self) -> None:
        if self.destination:
            QApplication.clipboard().setText(str(self.destination))


class MainWindow(QMainWindow):
    def __init__(self, theme_mode: str, settings: QSettings):
        super().__init__()
        self.theme_mode = theme_mode if theme_mode in THEME_LABELS else "system"
        self.theme = self._resolved_theme()
        self.settings = settings
        self.setWindowTitle("DropMD — 文档转 Markdown")
        self.setMinimumSize(QSize(760, 660))
        self.resize(920, 760)
        self.setAcceptDrops(True)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
        icon_path = bundle_root / "assets" / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(2)
        self.rows: dict[Path, JobRow] = {}
        self.running: set[Path] = set()
        self.auto_copy_sources: set[Path] = set()
        self.animations_enabled = not prefers_reduced_motion()
        self._notice_generation = 0

        canvas = QWidget()
        canvas.setObjectName("windowCanvas")
        self.setCentralWidget(canvas)
        self.canvas_layout = QVBoxLayout(canvas)
        self.canvas_layout.setContentsMargins(12, 12, 12, 12)

        self.surface = QFrame()
        self.surface.setObjectName("windowSurface")
        self.surface.setProperty("maximized", False)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setOffset(QPoint(0, 7))
        shadow.setColor(QColor(7, 20, 18, 72))
        self.surface.setGraphicsEffect(shadow)
        self.shadow = shadow
        self.canvas_layout.addWidget(self.surface)

        shell = QVBoxLayout(self.surface)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self.title_bar = TitleBar()
        self.title_bar.set_theme(self.theme_mode, self.theme)
        self.title_bar.themeModeRequested.connect(self.set_theme_mode)
        shell.addWidget(self.title_bar)

        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(36, 20, 36, 16)
        content_layout.setSpacing(10)
        shell.addWidget(self.content, 1)

        eyebrow = QLabel("DOCUMENT → MARKDOWN")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("把文档，变成好用的 Markdown。")
        title.setObjectName("title")
        subtitle = QLabel("拖入即可转换。结构、表格与内容会尽可能完整保留。")
        subtitle.setObjectName("subtitle")

        content_layout.addWidget(eyebrow)
        content_layout.addWidget(title)
        content_layout.addWidget(subtitle)

        self.drop_zone = DropZone(animations_enabled=self.animations_enabled)
        self.drop_zone.filesDropped.connect(self.add_files)
        self.drop_zone.choose_button.clicked.connect(self.choose_files)
        content_layout.addWidget(self.drop_zone)

        preference_bar = QFrame()
        preference_bar.setObjectName("preferenceBar")
        preference_layout = QHBoxLayout(preference_bar)
        preference_layout.setContentsMargins(12, 7, 12, 7)
        preference_layout.setSpacing(16)
        self.overwrite = QCheckBox("覆盖已有同名文件")
        self.overwrite.setChecked(self.settings.value("overwrite", True, type=bool))
        self.overwrite.toggled.connect(lambda value: self.settings.setValue("overwrite", value))
        self.auto_copy = QCheckBox("单个文件完成后自动复制")
        self.auto_copy.setChecked(self.settings.value("auto_copy", False, type=bool))
        self.auto_copy.toggled.connect(lambda value: self.settings.setValue("auto_copy", value))
        self.supported_label = QLabel("DOCX · PDF · PPTX · XLSX · HTML · CSV · TXT")
        self.supported_label.setObjectName("caption")
        preference_layout.addWidget(self.overwrite)
        preference_layout.addWidget(self.auto_copy)
        preference_layout.addStretch()
        preference_layout.addWidget(self.supported_label)
        content_layout.addWidget(preference_bar)

        self.notice_frame = QFrame()
        self.notice_frame.setObjectName("noticeFrameSuccess")
        notice_layout = QHBoxLayout(self.notice_frame)
        notice_layout.setContentsMargins(14, 9, 14, 9)
        notice_layout.setSpacing(8)
        self.notice_icon = QLabel("✓")
        self.notice_icon.setObjectName("noticeIcon")
        self.notice_icon.setFixedWidth(18)
        self.notice_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notice = QLabel()
        self.notice.setObjectName("noticeText")
        self.notice.setWordWrap(True)
        notice_layout.addWidget(self.notice_icon)
        notice_layout.addWidget(self.notice, 1)
        self.notice_frame.hide()
        content_layout.addWidget(self.notice_frame)

        list_header = QHBoxLayout()
        list_header.setSpacing(10)
        list_title = QLabel("最近转换")
        list_title.setObjectName("sectionTitle")
        self.section_meta = QLabel("拖入多个文件可批量处理")
        self.section_meta.setObjectName("sectionMeta")
        self.progress = QProgressBar()
        self.progress.setObjectName("batchProgress")
        self.progress.setTextVisible(False)
        self.progress.setFixedSize(86, 5)
        self.progress.hide()
        self.clear_button = QPushButton("清空记录")
        self.clear_button.setObjectName("linkButton")
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_button.clicked.connect(self.clear_finished)
        self.clear_button.hide()
        list_header.addWidget(list_title)
        list_header.addWidget(self.section_meta)
        list_header.addStretch()
        list_header.addWidget(self.progress)
        list_header.addWidget(self.clear_button)
        content_layout.addLayout(list_header)

        self.list_panel = QFrame()
        self.list_panel.setObjectName("listPanel")
        self.panel_stack = QStackedLayout(self.list_panel)
        self.panel_stack.setContentsMargins(0, 0, 0, 0)
        self.panel_stack.setStackingMode(QStackedLayout.StackingMode.StackOne)

        self.empty_state = QWidget()
        empty = QVBoxLayout(self.empty_state)
        empty.setContentsMargins(20, 16, 20, 16)
        empty.setSpacing(4)
        empty.addStretch()
        self.empty_title = QLabel("准备好开始第一次转换")
        self.empty_title.setObjectName("emptyTitle")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint = QLabel("转换结果和后续操作会集中显示在这里")
        self.empty_hint.setObjectName("emptyHint")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.addWidget(self.empty_title)
        empty.addWidget(self.empty_hint)
        empty.addStretch()
        self.panel_stack.addWidget(self.empty_state)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("scrollContent")
        self.rows_layout = QVBoxLayout(self.scroll_content)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(0)
        self.rows_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.scroll_content)
        self.panel_stack.addWidget(self.scroll)
        self.panel_stack.setCurrentWidget(self.empty_state)
        content_layout.addWidget(self.list_panel, 1)

    def _resolved_theme(self) -> str:
        if self.theme_mode == "system":
            application = QApplication.instance()
            return system_theme(application) if application else "light"
        return self.theme_mode

    def set_theme_mode(self, mode: str) -> None:
        if mode not in THEME_LABELS:
            return
        self.theme_mode = mode
        self.settings.setValue("theme_mode", mode)
        self._apply_theme()

    def _apply_theme(self) -> None:
        self.theme = self._resolved_theme()
        QApplication.instance().setStyleSheet(stylesheet(self.theme))
        self.title_bar.set_theme(self.theme_mode, self.theme)

    def system_color_scheme_changed(self) -> None:
        if self.theme_mode == "system":
            self._apply_theme()

    def choose_files(self) -> None:
        extensions = " ".join(f"*{extension}" for extension in sorted(SUPPORTED_EXTENSIONS))
        initial_folder = self.settings.value("last_folder", str(Path.home()))
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择要转换的文件",
            initial_folder,
            f"支持的文件 ({extensions});;所有文件 (*)",
        )
        if paths:
            self.settings.setValue("last_folder", str(Path(paths[0]).parent))
        self.add_files([Path(path) for path in paths])

    def add_files(self, candidates: list[Path]) -> None:
        files: list[Path] = []
        for candidate in candidates:
            if candidate.is_dir():
                files.extend(path for path in candidate.iterdir() if path.is_file())
            else:
                files.append(candidate)

        supported = [path.expanduser().resolve() for path in files if is_supported(path.expanduser().resolve())]
        enable_auto_copy = self.auto_copy.isChecked() and len(supported) == 1
        accepted = 0
        unsupported: list[str] = []
        for source in files:
            source = source.expanduser().resolve()
            if not is_supported(source):
                unsupported.append(source.name)
                continue
            if source in self.running:
                continue
            destination = output_path_for(source)
            if any(output_path_for(active) == destination for active in self.running):
                unsupported.append(f"{source.name}（输出名称冲突）")
                continue

            old_row = self.rows.pop(source, None)
            if old_row:
                self.rows_layout.removeWidget(old_row)
                old_row.deleteLater()

            row = JobRow(source, animations_enabled=self.animations_enabled)
            row.markdownCopied.connect(self._markdown_copied)
            row.copyFailed.connect(lambda message, name=source.name: self._show_notice(f"{name} 复制失败：{message}", success=False))
            row.retryRequested.connect(lambda path: self.add_files([path]))
            self.rows[source] = row
            self.rows_layout.insertWidget(0, row)
            self.running.add(source)
            if enable_auto_copy:
                self.auto_copy_sources.add(source)
            accepted += 1

            worker = ConversionWorker(source, self.overwrite.isChecked())
            worker.signals.started.connect(lambda path, item=row: item.mark_working())
            worker.signals.succeeded.connect(self._conversion_succeeded)
            worker.signals.failed.connect(self._conversion_failed)
            self.thread_pool.start(worker)

        if accepted:
            self.panel_stack.setCurrentWidget(self.scroll)
            self.clear_button.show()
            self._update_summary()
            self._show_notice(f"已加入 {accepted} 个文件，正在转换…", success=True)
        if unsupported:
            names = "、".join(unsupported[:3])
            extra = f" 等 {len(unsupported)} 个文件" if len(unsupported) > 3 else ""
            self._show_notice(f"未加入 {names}{extra}。请选择支持的文件格式。", success=False)

    def _conversion_succeeded(self, source: Path, destination: Path) -> None:
        self.running.discard(source)
        row = self.rows.get(source)
        if row:
            row.mark_success(destination)
            if source in self.auto_copy_sources:
                row.copy_markdown()
        self.auto_copy_sources.discard(source)
        self._update_summary()
        self._show_notice(f"已生成 {destination.name}。", success=True)

    def _conversion_failed(self, source: Path, message: str) -> None:
        self.running.discard(source)
        self.auto_copy_sources.discard(source)
        row = self.rows.get(source)
        if row:
            row.mark_error(message)
        self._update_summary()
        self._show_notice(f"{source.name} 转换失败：{message}", success=False)

    def _update_summary(self) -> None:
        total = len(self.rows)
        completed = sum(row.state in {"success", "error"} for row in self.rows.values())
        successes = sum(row.state == "success" for row in self.rows.values())
        errors = sum(row.state == "error" for row in self.rows.values())
        if self.running:
            self.section_meta.setText(f"{completed} / {total} 完成")
            self.progress.setRange(0, max(total, 1))
            self.progress.setValue(completed)
            self.progress.show()
        elif total:
            suffix = f" · {errors} 个失败" if errors else ""
            self.section_meta.setText(f"{successes} 个文件已完成{suffix}")
            self.progress.hide()
        else:
            self.section_meta.setText("拖入多个文件可批量处理")
            self.progress.hide()

    def _markdown_copied(self, destination: Path) -> None:
        self._show_notice(f"已复制 {destination.name} 的 Markdown 内容。", success=True)

    def _show_notice(self, message: str, *, success: bool) -> None:
        self._notice_generation += 1
        generation = self._notice_generation
        self.notice.setText(message)
        self.notice_icon.setText("✓" if success else "!")
        self.notice_frame.setObjectName("noticeFrameSuccess" if success else "noticeFrameError")
        self.notice_frame.style().unpolish(self.notice_frame)
        self.notice_frame.style().polish(self.notice_frame)
        self.notice_frame.show()
        QTimer.singleShot(4200, lambda: self._hide_notice(generation))

    def _hide_notice(self, generation: int) -> None:
        if generation != self._notice_generation or not self.notice_frame.isVisible():
            return
        animation = getattr(self.notice_frame, "_fade_animation", None)
        if animation:
            animation.stop()
        if isinstance(self.notice_frame.graphicsEffect(), QGraphicsOpacityEffect):
            self.notice_frame.setGraphicsEffect(None)
        self.notice_frame.hide()

    def clear_finished(self) -> None:
        for source, row in list(self.rows.items()):
            if source not in self.running:
                self.rows.pop(source)
                self.rows_layout.removeWidget(row)
                row.deleteLater()
        if not self.rows:
            self.panel_stack.setCurrentWidget(self.empty_state)
            self.clear_button.hide()
        self._update_summary()

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.WindowStateChange:
            maximized = self.isMaximized()
            self.canvas_layout.setContentsMargins(0, 0, 0, 0) if maximized else self.canvas_layout.setContentsMargins(12, 12, 12, 12)
            self.surface.setProperty("maximized", maximized)
            self.shadow.setEnabled(not maximized)
            self.surface.style().unpolish(self.surface)
            self.surface.style().polish(self.surface)
            self.title_bar.maximize_button.setToolTip("还原" if maximized else "最大化")
        super().changeEvent(event)

    def resizeEvent(self, event) -> None:
        self.supported_label.setVisible(self.width() >= 870)
        self.section_meta.setVisible(self.width() >= 780)
        super().resizeEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        self.add_files(paths)
        event.acceptProposedAction()


def main() -> int:
    application = DesktopApplication(sys.argv)
    application.setApplicationName("DropMD")
    application.setApplicationDisplayName("DropMD")
    application.setApplicationVersion("1.2.2")
    application.setOrganizationName("DropMD")
    application.setOrganizationDomain("dropmd.app")
    application.setDesktopFileName("com.dropmd.desktop")
    application.setStyle("Fusion")
    settings = QSettings("DropMD", "DropMD")
    theme_mode = settings.value("theme_mode", "system")
    if theme_mode not in THEME_LABELS:
        theme_mode = "system"
    initial_theme = system_theme(application) if theme_mode == "system" else theme_mode
    application.setStyleSheet(stylesheet(initial_theme))
    window = MainWindow(theme_mode, settings)
    application.styleHints().colorSchemeChanged.connect(lambda scheme: window.system_color_scheme_changed())
    application.filesOpened.connect(window.add_files)
    window.show()
    launch_files = application.enable_file_handler()
    launch_files.extend(Path(argument) for argument in sys.argv[1:] if Path(argument).is_file())
    if launch_files:
        QTimer.singleShot(0, lambda: window.add_files(launch_files))
    return application.exec()
