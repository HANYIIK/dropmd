from pathlib import Path
from xml.etree import ElementTree

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QCheckBox, QStyle, QStyleOptionButton

import dropmd.styles as styles


def luminance(hex_color):
    channels = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_checkmark_matches_theme_and_has_clear_contrast(theme):
    palette = styles.PALETTES[theme]
    asset = Path(styles.__file__).parent / "assets" / f"check-{theme}.svg"
    path = ElementTree.parse(asset).find("{http://www.w3.org/2000/svg}path")
    assert path.attrib["stroke"] == palette["button_text"]
    foreground, background = sorted((luminance(palette["button_text"]), luminance(palette["accent"])))
    assert (background + 0.05) / (foreground + 0.05) >= 4.5
    assert f'url("{asset.as_posix()}")' in styles.stylesheet(theme)


def test_checkbox_renders_theme_checkmark_and_still_toggles(qt_app):
    checkbox = QCheckBox("Excel 保留颜色")
    checkbox.resize(200, 36)
    checkbox.show()
    checkbox.setFocus()
    for theme in ("light", "dark", "light"):
        checkbox.setStyleSheet(styles.stylesheet(theme))
        checkbox.setChecked(False)
        QTest.keyClick(checkbox, Qt.Key_Space)
        assert checkbox.isChecked()
        qt_app.processEvents()
        option = QStyleOptionButton()
        checkbox.initStyleOption(option)
        rect = checkbox.style().subElementRect(QStyle.SE_CheckBoxIndicator, option, checkbox)
        pixmap = checkbox.grab(rect)
        image = pixmap.toImage()
        colors = {
            image.pixelColor(x, y).name()
            for x in range(image.width())
            for y in range(image.height())
        }
        assert QColor(styles.PALETTES[theme]["button_text"]).name() in colors
        QTest.keyClick(checkbox, Qt.Key_Space)
        assert not checkbox.isChecked()
    checkbox.close()
