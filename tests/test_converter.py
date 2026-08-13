from pathlib import Path
from types import SimpleNamespace

import pytest

from dropmd.converter import OutputExistsError, UnsupportedFileError, convert_file, output_path_for


class FakeConverter:
    def convert(self, source: Path):
        return SimpleNamespace(markdown=f"# {source.stem}\n\n转换成功")


def test_output_path_keeps_the_original_stem(tmp_path: Path):
    source = tmp_path / "AI 打标字段 (2).docx"
    assert output_path_for(source) == tmp_path / "AI 打标字段 (2).md"


def test_convert_writes_utf8_markdown_beside_source(tmp_path: Path):
    source = tmp_path / "示例.docx"
    source.write_bytes(b"test")

    destination = convert_file(source, converter_factory=FakeConverter)

    assert destination == tmp_path / "示例.md"
    assert destination.read_text(encoding="utf-8") == "# 示例\n\n转换成功\n"


def test_existing_output_is_preserved_when_overwrite_is_disabled(tmp_path: Path):
    source = tmp_path / "example.pdf"
    source.write_bytes(b"test")
    destination = tmp_path / "example.md"
    destination.write_text("keep", encoding="utf-8")

    with pytest.raises(OutputExistsError):
        convert_file(source, overwrite=False, converter_factory=FakeConverter)

    assert destination.read_text(encoding="utf-8") == "keep"


def test_unsupported_file_is_rejected(tmp_path: Path):
    source = tmp_path / "archive.rar"
    source.write_bytes(b"test")

    with pytest.raises(UnsupportedFileError):
        convert_file(source, converter_factory=FakeConverter)
