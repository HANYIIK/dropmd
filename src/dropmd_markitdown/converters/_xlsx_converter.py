import io
import re
import sys
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, BinaryIO

from ._html_converter import HtmlConverter
from .._base_converter import DocumentConverter, DocumentConverterResult
from .._exceptions import MissingDependencyException, MISSING_DEPENDENCY_MESSAGE
from .._stream_info import StreamInfo

_xlsx_dependency_exc_info = None
try:
    from openpyxl import load_workbook
    from openpyxl.cell.cell import MergedCell
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


def _has_value(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _plain_text(value: Any) -> str:
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def _markdown_text(value: Any) -> str:
    text = _plain_text(value).replace("\\", "\\\\").replace("|", "\\|")
    return "<br>".join(text.split("\n"))


def _format_number(value: int | float | Decimal, number_format: str) -> str:
    if isinstance(value, int):
        raw = str(value)
    else:
        raw = format(Decimal(str(value)), "f").rstrip("0").rstrip(".")
        if raw in {"", "-0"}:
            raw = "0"

    section = (number_format or "General").split(";", 1)[0]
    if section.lower() == "general" or not re.search(r"[0#]", section):
        return raw

    is_percent = "%" in section
    numeric_value = Decimal(str(value)) * (100 if is_percent else 1)
    placeholder = re.sub(r'"[^"]*"|\[[^\]]*\]|\\.', "", section)
    scientific = re.search(r"([0#]+)(?:\.([0#]+))?E[+-]0+", placeholder, re.IGNORECASE)
    if scientific:
        decimals = len(scientific.group(2) or "")
        rendered = f"{float(numeric_value):.{decimals}E}"
    else:
        decimal_match = re.search(r"\.([0#]+)", placeholder)
        decimal_pattern = decimal_match.group(1) if decimal_match else ""
        minimum_decimals = decimal_pattern.count("0")
        maximum_decimals = len(decimal_pattern)
        grouping = "," in placeholder.split(".", 1)[0]
        if maximum_decimals:
            rendered = f"{numeric_value:,.{maximum_decimals}f}" if grouping else f"{numeric_value:.{maximum_decimals}f}"
            if maximum_decimals > minimum_decimals:
                integer_part, fraction = rendered.split(".", 1)
                fraction = fraction.rstrip("0")
                if len(fraction) < minimum_decimals:
                    fraction += "0" * (minimum_decimals - len(fraction))
                rendered = integer_part + (f".{fraction}" if fraction else "")
        else:
            rendered = f"{numeric_value:,.0f}" if grouping else f"{numeric_value:.0f}"
    return rendered + ("%" if is_percent else "")


def _display_value(formula_cell: Any, cached_cell: Any) -> str:
    value = formula_cell.value
    format_cell = formula_cell
    if getattr(formula_cell, "data_type", None) == "f" and _has_value(cached_cell.value):
        value = cached_cell.value
        format_cell = cached_cell
    if not _has_value(value):
        return ""
    if isinstance(value, bool):
        rendered = "TRUE" if value else "FALSE"
    elif isinstance(value, datetime):
        rendered = value.isoformat(sep=" ", timespec="seconds")
    elif isinstance(value, date):
        rendered = value.isoformat()
    elif isinstance(value, time):
        rendered = value.isoformat(timespec="seconds")
    elif isinstance(value, (int, float, Decimal)):
        rendered = _format_number(value, getattr(format_cell, "number_format", "General"))
    else:
        rendered = _plain_text(value)

    hyperlink = getattr(formula_cell, "hyperlink", None)
    target = getattr(hyperlink, "target", None) or getattr(hyperlink, "location", None)
    if target and rendered:
        safe_target = str(target).replace(" ", "%20").replace(">", "%3E")
        return f"[{_markdown_text(rendered)}](<{safe_target}>)"
    return _markdown_text(rendered)


def _meaningful_bounds(sheet: Any) -> tuple[int, int, int, int] | None:
    populated = [cell for cell in sheet._cells.values() if _has_value(cell.value)]
    if not populated:
        return None
    min_row = min(cell.row for cell in populated)
    min_col = min(cell.column for cell in populated)
    max_row = max(cell.row for cell in populated)
    max_col = max(cell.column for cell in populated)
    for merged_range in sheet.merged_cells.ranges:
        anchor = sheet.cell(merged_range.min_row, merged_range.min_col)
        if _has_value(anchor.value):
            min_row = min(min_row, merged_range.min_row)
            min_col = min(min_col, merged_range.min_col)
            max_row = max(max_row, merged_range.max_row)
            max_col = max(max_col, merged_range.max_col)
    return min_row, min_col, max_row, max_col


class _SheetRenderer:
    def __init__(self, sheet: Any, cached_sheet: Any):
        self.sheet = sheet
        self.cached_sheet = cached_sheet
        self.bounds = _meaningful_bounds(sheet)
        self.merges = list(sheet.merged_cells.ranges)
        self.merge_by_cell: dict[tuple[int, int], Any] = {}
        for merged_range in self.merges:
            for row in range(merged_range.min_row, merged_range.max_row + 1):
                for column in range(merged_range.min_col, merged_range.max_col + 1):
                    self.merge_by_cell[(row, column)] = merged_range

    def _cell_value(self, row: int, column: int, *, expand_merges: bool = True) -> str:
        merged_range = self.merge_by_cell.get((row, column))
        if merged_range is not None:
            anchor_row = merged_range.min_row
            anchor_column = merged_range.min_col
            if not expand_merges and (row, column) != (anchor_row, anchor_column):
                return ""
            if merged_range.max_col > merged_range.min_col and column != anchor_column:
                return ""
            row = anchor_row
            column = anchor_column
        return _display_value(
            self.sheet.cell(row, column),
            self.cached_sheet.cell(row, column),
        )

    def _full_width_bands(self) -> tuple[dict[int, Any], set[int]]:
        if self.bounds is None:
            return {}, set()
        _, min_col, _, max_col = self.bounds
        bands: dict[int, Any] = {}
        covered_rows: set[int] = set()
        for merged_range in self.merges:
            if merged_range.min_col <= min_col and merged_range.max_col >= max_col:
                value = self._cell_value(merged_range.min_row, merged_range.min_col)
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
            if merged_range is not None and merged_range.max_col > merged_range.min_col:
                base = self._cell_value(merged_range.min_row, merged_range.min_col)
                position = column - merged_range.min_col + 1
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
        plain = value.replace("<br>", "\n")
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
                if isinstance(cell, MergedCell) or not _has_value(cell.value):
                    continue
                value = _display_value(cell, self.cached_sheet.cell(row, column))
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
                warnings.append(f"> **源数据提示：** “{header}”列存在重复值：{details}。DropMD 已按原文件保留。")
        return warnings

    def _comments(self) -> list[str]:
        comments = []
        for cell in self.sheet._cells.values():
            comment = getattr(cell, "comment", None)
            if comment is not None and _has_value(comment.text):
                comments.append(f"- `{cell.coordinate}`：{_markdown_text(comment.text)}")
        return comments

    def render(self) -> str:
        title = _markdown_text(self.sheet.title).replace("<br>", " ")
        if self.bounds is None:
            return f"## {title}"

        min_row, min_col, max_row, max_col = self.bounds
        bands, band_rows = self._full_width_bands()
        header_row = self._header_row(band_rows)
        parts = [f"## {title}"]
        if header_row is None:
            return parts[0]

        for row in range(min_row, header_row):
            if row in bands:
                merged_range = bands[row]
                value = self._cell_value(row, merged_range.min_col)
                if value and value.replace("<br>", " ") != title:
                    parts.append(self._render_band(value, merged_range.max_row - merged_range.min_row + 1))
            elif row not in band_rows:
                values = [self._cell_value(row, column) for column in range(min_col, max_col + 1)]
                values = [value for value in values if value]
                if values:
                    parts.append("  ".join(values))

        headers = self._headers(header_row)
        table_rows: list[list[str]] = []

        def flush_table() -> None:
            if table_rows:
                parts.append(self._render_table(headers, table_rows))
                table_rows.clear()

        for row in range(header_row + 1, max_row + 1):
            if row in bands:
                flush_table()
                merged_range = bands[row]
                value = self._cell_value(row, merged_range.min_col)
                parts.append(self._render_band(value, merged_range.max_row - merged_range.min_row + 1))
                continue
            if row in band_rows:
                continue
            values = [self._cell_value(row, column) for column in range(min_col, max_col + 1)]
            if any(values):
                table_rows.append(values)
            else:
                flush_table()
        flush_table()

        parts.extend(self._source_warnings(header_row, headers, band_rows))
        comments = self._comments()
        if comments:
            parts.append("### 批注\n\n" + "\n".join(comments))
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
        sheets = [
            _SheetRenderer(sheet, cached_workbook[sheet.title]).render()
            for sheet in workbook.worksheets
        ]
        return DocumentConverterResult(markdown="\n\n".join(sheets).strip())


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
