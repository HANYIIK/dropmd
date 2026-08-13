from pathlib import Path
from copy import copy
from types import SimpleNamespace

import pytest
from openpyxl import Workbook

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


def test_xlsx_preserves_merged_hierarchy_and_text_identifiers(tmp_path: Path):
    source = tmp_path / "层级清单.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "功能清单"
    sheet.append(["功能模块", "编号", "功能项", "说明"])
    sheet.append(["数据建模", "1.1", "多模型管理", "第一项"])
    sheet.append([None, "1.2", "模型生命周期", "第二项"])
    sheet.append([None, "1.10", "敏感字段标识", "第十项"])
    sheet.merge_cells("A2:A4")
    workbook.save(source)

    destination = convert_file(source)
    markdown = destination.read_text(encoding="utf-8")

    assert "| 数据建模 | 1.1 | 多模型管理 | 第一项 |" in markdown
    assert "| 数据建模 | 1.2 | 模型生命周期 | 第二项 |" in markdown
    assert "| 数据建模 | 1.10 | 敏感字段标识 | 第十项 |" in markdown
    assert "1.20" not in markdown
    assert "NaN" not in markdown
    assert "Unnamed:" not in markdown


def test_xlsx_renders_horizontal_merges_as_sections_and_notes(tmp_path: Path):
    source = tmp_path / "报价表.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "成本总表"
    sheet.append(["序号", "需求类型", "金额", "价值"])
    sheet.append(["基础系统包"])
    sheet.merge_cells("A2:D2")
    sheet.append([1, "标品", 100, "基础能力"])
    sheet.append(["说明"])
    sheet.merge_cells("A4:D4")
    sheet.append(["报价不含第三方软件许可。"])
    sheet.merge_cells("A5:D6")
    workbook.save(source)

    markdown = convert_file(source).read_text(encoding="utf-8")

    assert "### 基础系统包" in markdown
    assert "| 1 | 标品 | 100 | 基础能力 |" in markdown
    assert "### 说明" in markdown
    assert "> 报价不含第三方软件许可。" in markdown


def test_xlsx_warns_only_for_duplicate_source_identifiers_within_a_section(tmp_path: Path):
    source = tmp_path / "重复编号.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "功能清单"
    sheet.append(["编号", "功能项"])
    sheet.append([1, "甲"])
    sheet.append([2, "乙"])
    sheet.append([2, "丙"])
    workbook.save(source)

    markdown = convert_file(source).read_text(encoding="utf-8")

    assert "源数据提示" in markdown
    assert "`2`（A3、A4）" in markdown
    assert "DropMD 已按原文件保留" in markdown


def test_xlsx_ignores_styled_empty_tail(tmp_path: Path):
    source = tmp_path / "有效区域.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["名称", "金额"])
    sheet.append(["项目", 100])
    sheet["H41"].fill = copy(sheet["A1"].fill)
    workbook.save(source)

    markdown = convert_file(source).read_text(encoding="utf-8")

    assert "| 名称 | 金额 |" in markdown
    assert "列 H" not in markdown
    assert markdown.count("| 项目 | 100 |") == 1
