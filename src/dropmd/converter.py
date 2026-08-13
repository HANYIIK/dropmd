from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from dropmd_markitdown import MarkItDown


SUPPORTED_EXTENSIONS = {
    ".csv",
    ".docx",
    ".epub",
    ".htm",
    ".html",
    ".ipynb",
    ".json",
    ".msg",
    ".pdf",
    ".pptx",
    ".txt",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
}


class ConverterResult(Protocol):
    markdown: str


class DocumentConverter(Protocol):
    def convert(self, source: Path) -> ConverterResult: ...


class UnsupportedFileError(ValueError):
    pass


class OutputExistsError(FileExistsError):
    pass


def output_path_for(source: Path) -> Path:
    return source.with_suffix(".md")


def is_supported(source: Path) -> bool:
    return source.is_file() and source.suffix.lower() in SUPPORTED_EXTENSIONS


def convert_file(
    source: Path,
    *,
    overwrite: bool = True,
    converter_factory: Callable[[], DocumentConverter] = MarkItDown,
) -> Path:
    source = source.expanduser().resolve()
    if not is_supported(source):
        extension = source.suffix or "无扩展名"
        raise UnsupportedFileError(f"暂不支持 {extension} 文件")

    destination = output_path_for(source)
    if destination.exists() and not overwrite:
        raise OutputExistsError(f"{destination.name} 已存在")

    result = converter_factory().convert(source)
    markdown = result.markdown
    if not isinstance(markdown, str):
        raise TypeError("转换结果不是文本")

    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{source.stem}-",
        suffix=".md.tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(markdown)
            if markdown and not markdown.endswith("\n"):
                stream.write("\n")
        if destination.exists() and not overwrite:
            raise OutputExistsError(f"{destination.name} 已存在")
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return destination
