from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, QRunnable, QSettings, QSize, Qt, QThreadPool, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QDragEnterEvent, QDropEvent, QIcon, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .converter import SUPPORTED_EXTENSIONS, convert_file, is_supported, output_path_for
from .styles import stylesheet


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
    themeToggleRequested = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("titleBar")
        self.setFixedHeight(52)

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
        local = QLabel("LOCAL ONLY")
        local.setObjectName("localBadge")

        self.theme_button = QPushButton("☾")
        self.theme_button.setObjectName("themeButton")
        self.theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_button.setAccessibleName("切换深色模式")
        self.theme_button.setToolTip("切换深色模式")
        self.theme_button.clicked.connect(self.themeToggleRequested)

        layout.addWidget(self.close_button)
        layout.addWidget(self.minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addSpacing(12)
        layout.addWidget(brand)
        layout.addSpacing(4)
        layout.addWidget(local)
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

    def set_theme(self, theme: str) -> None:
        dark = theme == "dark"
        self.theme_button.setText("☀" if dark else "☾")
        action = "浅色" if dark else "深色"
        self.theme_button.setAccessibleName(f"切换{action}模式")
        self.theme_button.setToolTip(f"切换{action}模式")

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

    def __init__(self):
        super().__init__()
        self.setObjectName("dropZone")
        self.setProperty("dragActive", False)
        self.setAcceptDrops(True)
        self.setMinimumHeight(218)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(9)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel(".MD")
        icon.setObjectName("dropIcon")
        icon.setFixedSize(50, 50)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("拖入文件，立即转换")
        title.setObjectName("dropTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("Markdown 将以同名文件保存在原目录")
        hint.setObjectName("caption")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.choose_button = QPushButton("选择文件")
        self.choose_button.setObjectName("primaryButton")
        self.choose_button.setCursor(Qt.CursorShape.PointingHandCursor)

        layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addSpacing(5)
        layout.addWidget(self.choose_button, alignment=Qt.AlignmentFlag.AlignCenter)

    def _set_drag_active(self, active: bool) -> None:
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)

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

    def __init__(self, source: Path):
        super().__init__()
        self.source = source
        self.destination: Path | None = None
        self.setObjectName("jobRow")
        self.setMinimumHeight(70)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 10, 10)
        layout.setSpacing(11)

        file_icon = QLabel(source.suffix[1:].upper()[:4] or "FILE")
        file_icon.setObjectName("fileType")
        file_icon.setFixedSize(42, 36)
        file_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        details = QVBoxLayout()
        details.setSpacing(2)
        name = QLabel(source.name)
        name.setObjectName("fileName")
        name.setToolTip(str(source))
        path = QLabel(str(source.parent))
        path.setObjectName("path")
        path.setToolTip(str(source.parent))
        path.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        details.addWidget(name)
        details.addWidget(path)

        self.status = QLabel("等待转换")
        self.status.setObjectName("statusPending")
        self.status.setMinimumWidth(76)
        self.status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.copy_button = QPushButton("复制 Markdown")
        self.copy_button.setObjectName("copyButton")
        self.copy_button.setProperty("copied", False)
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_button.setAccessibleName("复制 Markdown 内容")
        self.copy_button.clicked.connect(self._copy_markdown)
        self.copy_button.hide()

        self.open_button = QPushButton("打开")
        self.open_button.setObjectName("linkButton")
        self.open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_button.clicked.connect(self._open_destination)
        self.open_button.hide()

        layout.addWidget(file_icon)
        layout.addLayout(details, 1)
        layout.addWidget(self.status)
        layout.addWidget(self.copy_button)
        layout.addWidget(self.open_button)

    def mark_working(self) -> None:
        self.status.setText("转换中…")
        self.status.setObjectName("statusWorking")
        self._refresh(self.status)

    def mark_success(self, destination: Path) -> None:
        self.destination = destination
        self.status.setText("已完成")
        self.status.setObjectName("statusSuccess")
        self._refresh(self.status)
        self.copy_button.show()
        self.open_button.show()

    def mark_error(self, message: str) -> None:
        self.status.setText("失败")
        self.status.setObjectName("statusError")
        self.status.setToolTip(message)
        self._refresh(self.status)

    @staticmethod
    def _refresh(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _copy_markdown(self) -> None:
        if not self.destination:
            return
        try:
            markdown = self.destination.read_text(encoding="utf-8")
        except Exception as error:
            self.copyFailed.emit(str(error).strip() or "无法读取 Markdown 文件")
            return
        QApplication.clipboard().setText(markdown)
        self.copy_button.setText("已复制 ✓")
        self.copy_button.setProperty("copied", True)
        self._refresh(self.copy_button)
        self.markdownCopied.emit(self.destination)
        QTimer.singleShot(1800, self._reset_copy_button)

    def _reset_copy_button(self) -> None:
        self.copy_button.setText("复制 Markdown")
        self.copy_button.setProperty("copied", False)
        self._refresh(self.copy_button)

    def _open_destination(self) -> None:
        if self.destination:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.destination)))


class MainWindow(QMainWindow):
    def __init__(self, theme: str, settings: QSettings):
        super().__init__()
        self.theme = theme
        self.settings = settings
        self.setWindowTitle("DropMD — 文件转 Markdown")
        self.setMinimumSize(QSize(760, 650))
        self.resize(900, 740)
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
        shadow.setColor(QColor(7, 20, 18, 85))
        self.surface.setGraphicsEffect(shadow)
        self.shadow = shadow
        self.canvas_layout.addWidget(self.surface)

        shell = QVBoxLayout(self.surface)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self.title_bar = TitleBar()
        self.title_bar.set_theme(self.theme)
        self.title_bar.themeToggleRequested.connect(self.toggle_theme)
        shell.addWidget(self.title_bar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(34, 26, 34, 22)
        content_layout.setSpacing(16)
        shell.addWidget(content, 1)

        eyebrow = QLabel("LOCAL DOCUMENT PIPELINE")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("文件进来，Markdown 出去。")
        title.setObjectName("title")
        subtitle = QLabel("完全在本机完成转换，不上传文件，也不依赖外部服务。")
        subtitle.setObjectName("subtitle")

        content_layout.addWidget(eyebrow)
        content_layout.addWidget(title)
        content_layout.addWidget(subtitle)

        self.drop_zone = DropZone()
        self.drop_zone.filesDropped.connect(self.add_files)
        self.drop_zone.choose_button.clicked.connect(self.choose_files)
        content_layout.addWidget(self.drop_zone)

        options = QHBoxLayout()
        options.setSpacing(12)
        self.overwrite = QCheckBox("覆盖已有同名 .md")
        self.overwrite.setChecked(self.settings.value("overwrite", True, type=bool))
        self.overwrite.toggled.connect(lambda value: self.settings.setValue("overwrite", value))
        self.supported_label = QLabel("DOCX · PDF · PPTX · XLSX · HTML · CSV · TXT")
        self.supported_label.setObjectName("caption")
        options.addWidget(self.overwrite)
        options.addStretch()
        options.addWidget(self.supported_label)
        content_layout.addLayout(options)

        self.notice = QLabel()
        self.notice.setWordWrap(True)
        self.notice.hide()
        content_layout.addWidget(self.notice)

        list_header = QHBoxLayout()
        list_header.setSpacing(10)
        list_title = QLabel("转换记录")
        list_title.setObjectName("sectionTitle")
        self.section_meta = QLabel("完成后可直接复制 Markdown")
        self.section_meta.setObjectName("sectionMeta")
        self.clear_button = QPushButton("清空")
        self.clear_button.setObjectName("linkButton")
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_button.clicked.connect(self.clear_finished)
        self.clear_button.hide()
        list_header.addWidget(list_title)
        list_header.addWidget(self.section_meta)
        list_header.addStretch()
        list_header.addWidget(self.clear_button)
        content_layout.addLayout(list_header)

        self.list_panel = QFrame()
        self.list_panel.setObjectName("listPanel")
        panel_layout = QVBoxLayout(self.list_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        self.empty_hint = QLabel("转换记录会出现在这里")
        self.empty_hint.setObjectName("emptyHint")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint.setMinimumHeight(94)
        panel_layout.addWidget(self.empty_hint)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.hide()
        self.scroll_content = QWidget()
        self.rows_layout = QVBoxLayout(self.scroll_content)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(0)
        self.rows_layout.addStretch()
        self.scroll.setWidget(self.scroll_content)
        panel_layout.addWidget(self.scroll)
        content_layout.addWidget(self.list_panel, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        footer.addWidget(QSizeGrip(self))
        content_layout.addLayout(footer)

    def toggle_theme(self) -> None:
        self.theme = "light" if self.theme == "dark" else "dark"
        self.settings.setValue("theme", self.theme)
        QApplication.instance().setStyleSheet(stylesheet(self.theme))
        self.title_bar.set_theme(self.theme)

    def choose_files(self) -> None:
        extensions = " ".join(f"*{extension}" for extension in sorted(SUPPORTED_EXTENSIONS))
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择要转换的文件",
            str(Path.home()),
            f"支持的文件 ({extensions});;所有文件 (*)",
        )
        self.add_files([Path(path) for path in paths])

    def add_files(self, candidates: list[Path]) -> None:
        files: list[Path] = []
        for candidate in candidates:
            if candidate.is_dir():
                files.extend(path for path in candidate.iterdir() if path.is_file())
            else:
                files.append(candidate)

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

            row = JobRow(source)
            row.markdownCopied.connect(self._markdown_copied)
            row.copyFailed.connect(lambda message, name=source.name: self._show_notice(f"{name} 复制失败：{message}", success=False))
            self.rows[source] = row
            self.rows_layout.insertWidget(0, row)
            self.running.add(source)
            accepted += 1

            worker = ConversionWorker(source, self.overwrite.isChecked())
            worker.signals.started.connect(lambda path, item=row: item.mark_working())
            worker.signals.succeeded.connect(self._conversion_succeeded)
            worker.signals.failed.connect(self._conversion_failed)
            self.thread_pool.start(worker)

        if accepted:
            self.empty_hint.hide()
            self.scroll.show()
            self.clear_button.show()
            self._show_notice(f"正在转换 {accepted} 个文件…", success=True)
        if unsupported:
            names = "、".join(unsupported[:3])
            extra = f" 等 {len(unsupported)} 个文件" if len(unsupported) > 3 else ""
            self._show_notice(f"未加入：{names}{extra}。请检查格式或同名输出冲突。", success=False)

    def _conversion_succeeded(self, source: Path, destination: Path) -> None:
        self.running.discard(source)
        row = self.rows.get(source)
        if row:
            row.mark_success(destination)
        self._show_notice(f"已生成 {destination.name}，现在可以一键复制。", success=True)

    def _conversion_failed(self, source: Path, message: str) -> None:
        self.running.discard(source)
        row = self.rows.get(source)
        if row:
            row.mark_error(message)
        self._show_notice(f"{source.name} 转换失败：{message}", success=False)

    def _markdown_copied(self, destination: Path) -> None:
        self._show_notice(f"已复制 {destination.name} 的全部 Markdown 内容。", success=True)

    def _show_notice(self, message: str, *, success: bool) -> None:
        self.notice.setText(message)
        self.notice.setObjectName("noticeSuccess" if success else "noticeError")
        self.notice.style().unpolish(self.notice)
        self.notice.style().polish(self.notice)
        self.notice.show()
        QTimer.singleShot(5000, self.notice.hide)

    def clear_finished(self) -> None:
        for source, row in list(self.rows.items()):
            if source not in self.running:
                self.rows.pop(source)
                self.rows_layout.removeWidget(row)
                row.deleteLater()
        if not self.rows:
            self.scroll.hide()
            self.empty_hint.show()
            self.clear_button.hide()

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
        self.supported_label.setVisible(self.width() >= 820)
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
    application.setOrganizationName("DropMD")
    application.setStyle("Fusion")
    settings = QSettings("DropMD", "DropMD")
    theme = settings.value("theme", "light")
    if theme not in {"light", "dark"}:
        theme = "light"
    application.setStyleSheet(stylesheet(theme))
    window = MainWindow(theme, settings)
    application.filesOpened.connect(window.add_files)
    window.show()
    launch_files = application.enable_file_handler()
    launch_files.extend(Path(argument) for argument in sys.argv[1:] if Path(argument).is_file())
    if launch_files:
        QTimer.singleShot(0, lambda: window.add_files(launch_files))
    return application.exec()
