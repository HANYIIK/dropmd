from __future__ import annotations


PALETTES = {
    "light": {
        "canvas": "#edf1f0",
        "surface": "#f8faf9",
        "surface_alt": "#f1f5f4",
        "surface_hover": "#e8efed",
        "surface_pressed": "#dce7e4",
        "text": "#18302d",
        "text_soft": "#536c68",
        "text_faint": "#7a918d",
        "border": "#d7e2df",
        "border_strong": "#b9cbc7",
        "accent": "#147d72",
        "accent_hover": "#0f6d63",
        "accent_soft": "#e0f1ed",
        "accent_text": "#0f685f",
        "success": "#16786d",
        "success_soft": "#def0eb",
        "warning": "#9a6a25",
        "error": "#b24545",
        "error_soft": "#f7e7e7",
        "scroll": "#bdcfcb",
    },
    "dark": {
        "canvas": "#111817",
        "surface": "#18211f",
        "surface_alt": "#1d2826",
        "surface_hover": "#263330",
        "surface_pressed": "#30403c",
        "text": "#e6efed",
        "text_soft": "#adbfbb",
        "text_faint": "#7f9691",
        "border": "#2d3c39",
        "border_strong": "#415550",
        "accent": "#56b9aa",
        "accent_hover": "#6ccabb",
        "accent_soft": "#203d38",
        "accent_text": "#81d2c5",
        "success": "#6bc6b7",
        "success_soft": "#213b36",
        "warning": "#dfad60",
        "error": "#ed8585",
        "error_soft": "#442a2a",
        "scroll": "#40534f",
    },
}


def stylesheet(theme: str) -> str:
    color = PALETTES.get(theme, PALETTES["light"])
    return f"""
QWidget {{
    color: {color['text']};
    font-family: "PingFang SC", "Microsoft YaHei UI", "Segoe UI";
    font-size: 14px;
}}
QMainWindow, QWidget#windowCanvas {{
    background: transparent;
}}
QFrame#windowSurface {{
    background: {color['surface']};
    border: 1px solid {color['border_strong']};
    border-radius: 18px;
}}
QFrame#windowSurface[maximized="true"] {{
    border: none;
    border-radius: 0;
}}
QFrame#titleBar {{
    background: transparent;
    border-bottom: 1px solid {color['border']};
}}
QLabel#brandMark {{
    color: {color['accent']};
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QLabel#localBadge {{
    color: {color['text_faint']};
    background: {color['surface_alt']};
    border: 1px solid {color['border']};
    border-radius: 9px;
    padding: 2px 8px;
    font-size: 11px;
}}
QPushButton#closeButton, QPushButton#minimizeButton, QPushButton#maximizeButton {{
    min-width: 13px;
    max-width: 13px;
    min-height: 13px;
    max-height: 13px;
    padding: 0;
    border: none;
    border-radius: 6px;
    color: transparent;
    font-family: "Arial";
    font-size: 9px;
    font-weight: 900;
}}
QPushButton#closeButton {{ background: #ff5f57; }}
QPushButton#minimizeButton {{ background: #febc2e; }}
QPushButton#maximizeButton {{ background: #28c840; }}
QPushButton#closeButton:hover {{ color: #74120d; background: #ff6d66; }}
QPushButton#minimizeButton:hover {{ color: #805300; background: #ffc744; }}
QPushButton#maximizeButton:hover {{ color: #0d641b; background: #42d458; }}
QPushButton#closeButton:pressed {{ background: #e94b44; }}
QPushButton#minimizeButton:pressed {{ background: #e5a91c; }}
QPushButton#maximizeButton:pressed {{ background: #1eaf34; }}
QPushButton#themeButton {{
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    padding: 0;
    color: {color['text_soft']};
    background: transparent;
    border: 1px solid transparent;
    border-radius: 9px;
    font-size: 16px;
}}
QPushButton#themeButton:hover {{
    color: {color['text']};
    background: {color['surface_hover']};
    border-color: {color['border']};
}}
QLabel#eyebrow {{
    color: {color['accent']};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QLabel#title {{
    color: {color['text']};
    font-size: 30px;
    font-weight: 700;
}}
QLabel#subtitle, QLabel#caption, QLabel#path, QLabel#emptyHint {{
    color: {color['text_soft']};
}}
QLabel#path, QLabel#emptyHint {{
    color: {color['text_faint']};
}}
QFrame#dropZone {{
    background: {color['surface_alt']};
    border: 1px dashed {color['border_strong']};
    border-radius: 15px;
}}
QFrame#dropZone[dragActive="true"] {{
    background: {color['accent_soft']};
    border: 2px solid {color['accent']};
}}
QLabel#dropIcon {{
    color: {color['accent']};
    background: {color['accent_soft']};
    border: 1px solid {color['border']};
    border-radius: 25px;
    font-size: 13px;
    font-weight: 800;
}}
QLabel#dropTitle {{
    color: {color['text']};
    font-size: 18px;
    font-weight: 700;
}}
QPushButton {{
    min-height: 34px;
    padding: 0 14px;
    color: {color['text']};
    background: {color['surface_alt']};
    border: 1px solid {color['border']};
    border-radius: 8px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {color['surface_hover']};
    border-color: {color['border_strong']};
}}
QPushButton:pressed {{ background: {color['surface_pressed']}; }}
QPushButton:focus {{ border: 2px solid {color['accent']}; }}
QPushButton#primaryButton {{
    color: {color['surface']};
    background: {color['accent']};
    border-color: {color['accent']};
}}
QPushButton#primaryButton:hover {{
    background: {color['accent_hover']};
    border-color: {color['accent_hover']};
}}
QPushButton#linkButton, QPushButton#copyButton {{
    min-height: 29px;
    padding: 0 10px;
    color: {color['text_soft']};
    background: transparent;
    border: 1px solid transparent;
    border-radius: 7px;
}}
QPushButton#linkButton:hover, QPushButton#copyButton:hover {{
    color: {color['text']};
    background: {color['surface_hover']};
    border-color: {color['border']};
}}
QPushButton#copyButton {{
    color: {color['accent_text']};
    background: {color['accent_soft']};
}}
QPushButton#copyButton[copied="true"] {{
    color: {color['success']};
    border-color: {color['success']};
}}
QCheckBox {{
    color: {color['text_soft']};
    spacing: 8px;
}}
QCheckBox::indicator {{ width: 17px; height: 17px; }}
QCheckBox::indicator:unchecked {{
    background: {color['surface']};
    border: 1px solid {color['border_strong']};
    border-radius: 4px;
}}
QCheckBox::indicator:checked {{
    background: {color['accent']};
    border: 1px solid {color['accent']};
    border-radius: 4px;
    image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png);
}}
QFrame#listPanel {{
    background: {color['surface_alt']};
    border: 1px solid {color['border']};
    border-radius: 12px;
}}
QFrame#jobRow {{
    background: transparent;
    border-bottom: 1px solid {color['border']};
}}
QLabel#fileType {{
    color: {color['accent_text']};
    background: {color['accent_soft']};
    border-radius: 7px;
    font-size: 10px;
    font-weight: 700;
}}
QLabel#fileName, QLabel#sectionTitle {{
    color: {color['text']};
    font-weight: 650;
}}
QLabel#sectionMeta {{
    color: {color['text_faint']};
    font-size: 12px;
}}
QLabel#statusPending {{ color: {color['text_faint']}; }}
QLabel#statusWorking {{ color: {color['warning']}; }}
QLabel#statusSuccess {{ color: {color['success']}; }}
QLabel#statusError {{ color: {color['error']}; }}
QLabel#noticeSuccess {{
    color: {color['success']};
    background: {color['success_soft']};
    border: 1px solid {color['border']};
    border-radius: 8px;
    padding: 8px 12px;
}}
QLabel#noticeError {{
    color: {color['error']};
    background: {color['error_soft']};
    border: 1px solid {color['border']};
    border-radius: 8px;
    padding: 8px 12px;
}}
QScrollArea {{ background: transparent; border: 0; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ width: 8px; background: transparent; }}
QScrollBar::handle:vertical {{
    min-height: 28px;
    background: {color['scroll']};
    border-radius: 4px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QSizeGrip {{
    width: 18px;
    height: 18px;
    background: transparent;
}}
QToolTip {{
    color: {color['text']};
    background: {color['surface_alt']};
    border: 1px solid {color['border_strong']};
    padding: 5px 7px;
}}
"""
