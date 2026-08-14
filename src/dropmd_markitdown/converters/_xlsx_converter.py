import io
import re
import sys
from typing import Any, BinaryIO

from ._html_converter import HtmlConverter
from ._xlsx_semantic import (
    SemanticCell,
    SemanticSheet,
    SemanticWorkbook,
    build_semantic_workbook,
    has_value,
    plain_text,
)
from .._base_converter import DocumentConverter, DocumentConverterResult
from .._exceptions import MissingDependencyException, MISSING_DEPENDENCY_MESSAGE
from .._stream_info import StreamInfo

_xlsx_dependency_exc_info = None
try:
    from openpyxl import load_workbook
    from openpyxl.utils import get_column_letter
except ImportError:
    _xlsx_dependency_exc_info = sys.exc_info()

_xls_dependency_exc_info = None
try:
    import pandas as pd
    import xlrd  # noqa: F401
except ImportError:
    _xls_dependency_exc_info = sys.exc_info()

ACCEPTED_XLSX_MIME_TYPE_PREFIXES = [
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
]
ACCEPTED_XLSX_FILE_EXTENSIONS = [".xlsx"]

ACCEPTED_XLS_MIME_TYPE_PREFIXES = [
    "application/vnd.ms-excel",
    "application/excel",
]
ACCEPTED_XLS_FILE_EXTENSIONS = [".xls"]

_HIERARCHY_HEADER_PATTERN = re.compile(r"维度|层级|分类|模块|目录")
_IDENTIFIER_HEADER_PATTERN = re.compile(r"编号|序号|编码|(^|\b)id($|\b)", re.IGNORECASE)
_TOTAL_LABEL_PATTERN = re.compile(r"^(合计|小计|总计|总额|累计)$")
_FORMULA_ERROR_PATTERN = re.compile(r"^#(?:REF!|DIV/0!|VALUE!|NAME\?|N/A|NUM!|NULL!)$")


def _escape_markdown_text(value: Any) -> str:
    return plain_text(value).replace("\\", "\\\\").replace("|", "\\|")


def _inline_markdown_text(value: Any) -> str:
    lines = [line.strip() for line in plain_text(value).split("\n") if line.strip()]
    if not lines:
        return ""
    text = lines[0]
    for line in lines[1:]:
        punctuation = ("。", "；", ";", "！", "？", "!", "?", "：", ":", "，", ",", ".")
        if line.startswith(("（", "(", "【", "[")) or text.endswith(punctuation):
            separator = " "
        else:
            separator = "； "
        text += separator + line
    return _escape_markdown_text(text)


class _SheetRenderer:
    def __init__(self, sheet: SemanticSheet):
        self.sheet = sheet
        self.bounds = sheet.bounds
        self.merges = list(sheet.merges)
        self.merge_by_cell: dict[tuple[int, int], Any] = {}
        for merged_range in self.merges:
            for row in range(merged_range.min_row, merged_range.max_row + 1):
                for column in range(merged_range.min_column, merged_range.max_column + 1):
                    self.merge_by_cell[(row, column)] = merged_range

    def _resolved_cell(self, row: int, column: int, *, expand_merges: bool = True) -> SemanticCell | None:
        merged_range = self.merge_by_cell.get((row, column))
        if merged_range is not None:
            anchor = (merged_range.min_row, merged_range.min_column)
            if not expand_merges and (row, column) != anchor:
                return None
            if merged_range.width > 1 and column != merged_range.min_column:
                return None
            row, column = anchor
        return self.sheet.cell(row, column)

    def _cell_value(
        self,
        row: int,
        column: int,
        *,
        expand_merges: bool = True,
        preserve_newlines: bool = False,
    ) -> str:
        cell = self._resolved_cell(row, column, expand_merges=expand_merges)
        if cell is None or not cell.display_value:
            return ""
        markdown_text = (
            _escape_markdown_text(cell.display_value)
            if preserve_newlines
            else _inline_markdown_text(cell.display_value)
        )
        if cell.hyperlink:
            safe_target = cell.hyperlink.replace(" ", "%20").replace(">", "%3E")
            return f"[{markdown_text}](<{safe_target}>)"
        return markdown_text

    def _full_width_bands(self) -> tuple[dict[int, Any], set[int]]:
        if self.bounds is None:
            return {}, set()
        _, min_col, _, max_col = self.bounds
        bands: dict[int, Any] = {}
        covered_rows: set[int] = set()
        for merged_range in self.merges:
            if merged_range.min_column <= min_col and merged_range.max_column >= max_col:
                value = self._cell_value(merged_range.min_row, merged_range.min_column)
                if value:
                    bands[merged_range.min_row] = merged_range
                    covered_rows.update(range(merged_range.min_row, merged_range.max_row + 1))
        return bands, covered_rows

    def _header_row(self, band_rows: set[int]) -> int | None:
        if self.bounds is None:
            return None
        min_row, min_col, max_row, max_col = self.bounds
        fallback = None
        for row in range(min_row, max_row + 1):
            if row in band_rows:
                continue
            values = [self._cell_value(row, column, expand_merges=False) for column in range(min_col, max_col + 1)]
            count = sum(bool(value) for value in values)
            if count and fallback is None:
                fallback = row
            if count >= 2:
                return row
        return fallback

    def _headers(self, header_row: int) -> list[str]:
        assert self.bounds is not None
        _, min_col, _, max_col = self.bounds
        headers: list[str] = []
        for column in range(min_col, max_col + 1):
            merged_range = self.merge_by_cell.get((header_row, column))
            value = self._cell_value(header_row, column)
            if merged_range is not None and merged_range.width > 1:
                base = self._cell_value(merged_range.min_row, merged_range.min_column)
                position = column - merged_range.min_column + 1
                suffix = f"{position}级" if _HIERARCHY_HEADER_PATTERN.search(base) else str(position)
                value = f"{base}（{suffix}）"
            headers.append(value or f"列 {get_column_letter(column)}")

        counts: dict[str, int] = {}
        unique_headers: list[str] = []
        for header in headers:
            counts[header] = counts.get(header, 0) + 1
            occurrence = counts[header]
            unique_headers.append(header if occurrence == 1 else f"{header}（{occurrence}）")
        return unique_headers

    @staticmethod
    def _render_band(value: str, height: int) -> str:
        plain = value
        if height == 1 and len(plain) <= 80 and "\n" not in plain:
            return f"### {plain}"
        lines = plain.splitlines() or [plain]
        return "\n".join(f"> {line}" if line else ">" for line in lines)

    @staticmethod
    def _render_table(headers: list[str], rows: list[list[str]]) -> str:
        output = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        output.extend("| " + " | ".join(row) + " |" for row in rows)
        return "\n".join(output)

    def _is_total_row(self, row: int) -> bool:
        assert self.bounds is not None
        _, min_col, _, max_col = self.bounds
        for column in range(min_col, max_col + 1):
            cell = self._resolved_cell(row, column)
            if cell is not None and _TOTAL_LABEL_PATTERN.fullmatch(cell.display_value.strip()):
                return True
        return False

    def _has_direct_source_content(self, row: int) -> bool:
        assert self.bounds is not None
        _, min_col, _, max_col = self.bounds
        return any(self.sheet.cell(row, column) is not None for column in range(min_col, max_col + 1))

    def _is_merge_continuation(self, row: int) -> bool:
        assert self.bounds is not None
        _, min_col, _, max_col = self.bounds
        return any(
            merged_range.min_row < row <= merged_range.max_row
            and merged_range.min_column <= max_col
            and merged_range.max_column >= min_col
            for merged_range in self.merges
        )

    def _source_warnings(self, header_row: int, headers: list[str], skipped_rows: set[int]) -> list[str]:
        assert self.bounds is not None
        _, min_col, max_row, _ = self.bounds
        warnings: list[str] = []
        for offset, header in enumerate(headers):
            if not _IDENTIFIER_HEADER_PATTERN.search(header):
                continue
            column = min_col + offset
            groups: list[dict[str, list[str]]] = []
            occurrences: dict[str, list[str]] = {}
            for row in range(header_row + 1, max_row + 1):
                if row in skipped_rows:
                    if occurrences:
                        groups.append(occurrences)
                        occurrences = {}
                    continue
                cell = self.sheet.cell(row, column)
                if cell is None or not has_value(cell.source_value):
                    continue
                value = _inline_markdown_text(cell.display_value)
                if value:
                    occurrences.setdefault(value, []).append(cell.coordinate)
            if occurrences:
                groups.append(occurrences)
            duplicates = [
                (value, coordinates)
                for group in groups
                for value, coordinates in group.items()
                if len(coordinates) > 1
            ]
            if duplicates:
                details = "；".join(
                    f"`{value.replace('`', '´')}`（{'、'.join(coordinates)}）"
                    for value, coordinates in duplicates[:20]
                )
                if len(duplicates) > 20:
                    details += f"；另有 {len(duplicates) - 20} 项"
                warnings.append(
                    f"> **源数据提示：** “{header}”列存在重复值：{details}。DropMD 已按原文件保留。"
                )
        return warnings

    def _comments(self) -> list[str]:
        comments = []
        for cell in sorted(self.sheet.cells.values(), key=lambda item: (item.row, item.column)):
            if cell.comment:
                author = f"（{_inline_markdown_text(cell.comment_author)}）" if cell.comment_author else ""
                comments.append(f"- `{cell.coordinate}`{author}：{_inline_markdown_text(cell.comment)}")
        return comments

    def _formulas(self) -> tuple[list[str], list[str]]:
        formulas: list[str] = []
        errors: list[str] = []
        for cell in sorted(self.sheet.formula_cells, key=lambda item: (item.row, item.column)):
            formula = cell.formula.replace("`", "´") if cell.formula else ""
            if cell.has_cached_value:
                result = _inline_markdown_text(cell.display_value).replace("`", "´")
                formulas.append(f"- `{cell.coordinate}`：`{formula}` → `{result}`")
                if _FORMULA_ERROR_PATTERN.fullmatch(cell.display_value.strip()):
                    errors.append(f"`{cell.coordinate}`（`{cell.display_value}`）")
            else:
                formulas.append(f"- `{cell.coordinate}`：`{formula}`（原文件未保存计算结果）")
        return formulas, errors

    def _source_note(self) -> str | None:
        details: list[str] = []
        if self.sheet.state != "visible":
            state = "隐藏" if self.sheet.state == "hidden" else "深度隐藏"
            details.append(f"原工作表为{state}状态")
        if self.sheet.hidden_rows:
            details.append(f"隐藏行 {len(self.sheet.hidden_rows)} 个")
        if self.sheet.hidden_columns:
            details.append(f"隐藏列 {len(self.sheet.hidden_columns)} 个")
        if not details:
            return None
        return "> **源表提示：** " + "；".join(details) + "。"

    def render(self) -> str:
        title = _inline_markdown_text(self.sheet.name)
        parts = [f"## {title}"]
        source_note = self._source_note()
        if source_note:
            parts.append(source_note)
        if self.bounds is None:
            return "\n\n".join(parts)

        min_row, min_col, max_row, max_col = self.bounds
        bands, band_rows = self._full_width_bands()
        header_row = self._header_row(band_rows)
        if header_row is None:
            return "\n\n".join(parts)

        for row in range(min_row, header_row):
            if row in bands:
                merged_range = bands[row]
                value = self._cell_value(row, merged_range.min_column, preserve_newlines=True)
                if value and value.replace("\n", " ") != title:
                    parts.append(self._render_band(value, merged_range.height))
            elif row not in band_rows:
                if not self._has_direct_source_content(row):
                    continue
                values = [self._cell_value(row, column) for column in range(min_col, max_col + 1)]
                values = [value for value in values if value]
                if values:
                    parts.append("  ".join(values))

        headers = self._headers(header_row)
        table_rows: list[list[str]] = []
        folded_rows: list[int] = []

        def flush_table() -> None:
            if table_rows:
                parts.append(self._render_table(headers, table_rows))
                table_rows.clear()

        for row in range(header_row + 1, max_row + 1):
            if row in bands:
                flush_table()
                merged_range = bands[row]
                value = self._cell_value(row, merged_range.min_column, preserve_newlines=True)
                parts.append(self._render_band(value, merged_range.height))
                continue
            if row in band_rows:
                continue
            if not self._has_direct_source_content(row):
                if self._is_merge_continuation(row):
                    folded_rows.append(row)
                else:
                    flush_table()
                continue
            values = [self._cell_value(row, column) for column in range(min_col, max_col + 1)]
            if any(values):
                if self._is_total_row(row):
                    values = [f"**{value}**" if value else "" for value in values]
                table_rows.append(values)
            else:
                flush_table()
        flush_table()

        if folded_rows:
            row_list = "、".join(str(row) for row in folded_rows[:20])
            if len(folded_rows) > 20:
                row_list += f"，另有 {len(folded_rows) - 20} 行"
            parts.append(
                f"> **转换提示：** 已折叠 {len(folded_rows)} 个仅用于合并单元格排版的延续行"
                f"（源表第 {row_list} 行），未生成重复记录。"
            )
        parts.extend(self._source_warnings(header_row, headers, band_rows))
        comments = self._comments()
        if comments:
            parts.append("### 批注\n\n" + "\n".join(comments))
        formulas, formula_errors = self._formulas()
        if formulas:
            parts.append("### 公式\n\n" + "\n".join(formulas))
        if formula_errors:
            parts.append(
                "> **公式提示：** 以下单元格包含错误结果：" + "、".join(formula_errors) + "。"
            )
        return "\n\n".join(part for part in parts if part)


class _WorkbookRenderer:
    def __init__(self, workbook: SemanticWorkbook):
        self.workbook = workbook

    @staticmethod
    def _state_label(state: str) -> str:
        if state == "visible":
            return "可见"
        if state == "hidden":
            return "隐藏"
        return "深度隐藏"

    def render(self) -> str:
        title = _inline_markdown_text(self.workbook.title or "Excel 工作簿")
        visible_count = sum(sheet.state == "visible" for sheet in self.workbook.sheets)
        hidden_count = len(self.workbook.sheets) - visible_count
        overview = (
            f"> **工作簿概览：** {len(self.workbook.sheets)} 个工作表"
            f"（{visible_count} 个可见，{hidden_count} 个隐藏）；"
            f"{self.workbook.merge_count} 个合并区域；{self.workbook.formula_count} 个公式单元格。"
        )
        index = []
        for sheet in self.workbook.sheets:
            details = [f"区域 `{sheet.dimension or '空白'}`", self._state_label(sheet.state)]
            if sheet.merges:
                details.append(f"{len(sheet.merges)} 个合并区域")
            if sheet.formula_cells:
                details.append(f"{len(sheet.formula_cells)} 个公式")
            if sheet.table_refs:
                details.append(f"{len(sheet.table_refs)} 个结构化表")
            index.append(f"- `{_inline_markdown_text(sheet.name)}`：" + "；".join(details))

        parts = [f"# {title}", overview, "## 工作表索引\n\n" + "\n".join(index)]
        parts.extend(_SheetRenderer(sheet).render() for sheet in self.workbook.sheets)
        if self.workbook.defined_names:
            names = "、".join(f"`{_inline_markdown_text(name)}`" for name, _ in self.workbook.defined_names)
            parts.append(f"> **定义名称：** {names}。")
        return "\n\n".join(part for part in parts if part)


class XlsxConverter(DocumentConverter):
    """Converts XLSX files while preserving merged-cell hierarchy and text identifiers."""

    def accepts(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> bool:
        mimetype = (stream_info.mimetype or "").lower()
        extension = (stream_info.extension or "").lower()
        return extension in ACCEPTED_XLSX_FILE_EXTENSIONS or any(
            mimetype.startswith(prefix) for prefix in ACCEPTED_XLSX_MIME_TYPE_PREFIXES
        )

    def convert(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> DocumentConverterResult:
        if _xlsx_dependency_exc_info is not None:
            raise MissingDependencyException(
                MISSING_DEPENDENCY_MESSAGE.format(
                    converter=type(self).__name__,
                    extension=".xlsx",
                    feature="xlsx",
                )
            ) from _xlsx_dependency_exc_info[1].with_traceback(_xlsx_dependency_exc_info[2])  # type: ignore[union-attr]

        file_stream.seek(0)
        workbook_bytes = file_stream.read()
        workbook = load_workbook(io.BytesIO(workbook_bytes), data_only=False, keep_links=False)
        cached_workbook = load_workbook(io.BytesIO(workbook_bytes), data_only=True, keep_links=False)
        semantic_workbook = build_semantic_workbook(workbook, cached_workbook, stream_info.filename)
        return DocumentConverterResult(
            markdown=_WorkbookRenderer(semantic_workbook).render().strip(),
            title=semantic_workbook.title,
        )


class XlsConverter(DocumentConverter):
    """Converts legacy XLS files to Markdown tables."""

    def __init__(self):
        super().__init__()
        self._html_converter = HtmlConverter()

    def accepts(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> bool:
        mimetype = (stream_info.mimetype or "").lower()
        extension = (stream_info.extension or "").lower()
        return extension in ACCEPTED_XLS_FILE_EXTENSIONS or any(
            mimetype.startswith(prefix) for prefix in ACCEPTED_XLS_MIME_TYPE_PREFIXES
        )

    def convert(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> DocumentConverterResult:
        if _xls_dependency_exc_info is not None:
            raise MissingDependencyException(
                MISSING_DEPENDENCY_MESSAGE.format(
                    converter=type(self).__name__,
                    extension=".xls",
                    feature="xls",
                )
            ) from _xls_dependency_exc_info[1].with_traceback(_xls_dependency_exc_info[2])  # type: ignore[union-attr]

        sheets = pd.read_excel(file_stream, sheet_name=None, engine="xlrd")
        md_content = ""
        for sheet_name, sheet in sheets.items():
            md_content += f"## {sheet_name}\n"
            html_content = sheet.to_html(index=False)
            md_content += self._html_converter.convert_string(html_content, **kwargs).markdown.strip() + "\n\n"
        return DocumentConverterResult(markdown=md_content.strip())
