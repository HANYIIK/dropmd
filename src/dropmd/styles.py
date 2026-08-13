from __future__ import annotations


PALETTES = {
    "light": {
        "canvas": "#e9efed",
        "surface": "#f9fbfa",
        "surface_alt": "#f1f5f4",
        "surface_raised": "#ffffff",
        "surface_hover": "#e8efed",
        "surface_pressed": "#dce7e4",
        "text": "#162c29",
        "text_soft": "#506864",
        "text_faint": "#748b87",
        "border": "#d5e0dd",
        "border_strong": "#b6c9c4",
        "accent": "#137f73",
        "accent_hover": "#0d6e64",
        "accent_soft": "#deefeb",
        "accent_text": "#0d695f",
        "button_text": "#f5fbf9",
        "success": "#15796e",
        "success_soft": "#dff1ec",
        "warning": "#986724",
        "error": "#b24444",
        "error_soft": "#f7e7e7",
        "scroll": "#b9cbc7",
    },
    "dark": {
        "canvas": "#0b0f12",
        "surface": "#151a1e",
        "surface_alt": "#1a2024",
        "surface_raised": "#22292e",
        "surface_hover": "#293137",
        "surface_pressed": "#313b41",
        "text": "#eef2f1",
        "text_soft": "#b1bab8",
        "text_faint": "#7f8b89",
        "border": "#2a3237",
        "border_strong": "#3b454b",
        "accent": "#4aaca1",
        "accent_hover": "#60bdb2",
        "accent_soft": "#17332f",
        "accent_text": "#79c9bf",
        "button_text": "#0f1d1b",
        "success": "#70c7a9",
        "success_soft": "#1a3029",
        "warning": "#d8a665",
        "error": "#ef9292",
        "error_soft": "#3a2428",
        "scroll": "#465158",
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
QMainWindow, QWidget#windowCanvas {{ background: transparent; }}
QFrame#windowSurface {{
    background: {color['surface']};
    border: 1px solid {color['border_strong']};
    border-radius: 18px;
}}
QFrame#windowSurface[maximized="true"] {{ border: none; border-radius: 0; }}
QFrame#titleBar {{ background: transparent; border-bottom: 1px solid {color['border']}; }}
QLabel#brandMark {{
    color: {color['accent']};
    font-size: 13px;
    font-weight: 750;
    letter-spacing: 1px;
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
    min-width: 34px;
    max-width: 34px;
    min-height: 34px;
    max-height: 34px;
    padding: 0;
    color: {color['text_soft']};
    background: transparent;
    border: none;
    border-radius: 9px;
    font-size: 16px;
}}
QPushButton#themeButton::menu-indicator {{ image: none; width: 0; }}
QPushButton#themeButton:hover {{
    color: {color['text']};
    background: {color['surface_hover']};
    border: none;
}}
QPushButton#themeButton:focus, QPushButton#themeButton:pressed, QPushButton#themeButton:checked {{
    border: none;
    outline: none;
}}
QMenu {{
    color: {color['text']};
    background: {color['surface_raised']};
    border: 1px solid {color['border_strong']};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{ min-width: 118px; padding: 7px 28px 7px 10px; border-radius: 6px; }}
QMenu::item:selected {{ background: {color['surface_hover']}; }}
QMenu::indicator {{ width: 14px; height: 14px; }}
QMenu::indicator:checked {{ image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png); }}
QLabel#eyebrow {{
    color: {color['accent']};
    font-size: 11px;
    font-weight: 750;
    letter-spacing: 1px;
}}
QLabel#title {{ color: {color['text']}; font-size: 29px; font-weight: 720; }}
QLabel#subtitle, QLabel#caption, QLabel#path, QLabel#emptyHint {{ color: {color['text_soft']}; }}
QLabel#path, QLabel#emptyHint {{ color: {color['text_faint']}; }}
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
    border-radius: 22px;
    font-size: 24px;
    font-weight: 500;
}}
QLabel#dropIcon[dragActive="true"] {{
    color: {color['button_text']};
    background: {color['accent']};
    border-color: {color['accent']};
}}
QLabel#dropTitle {{ color: {color['text']}; font-size: 18px; font-weight: 700; }}
QPushButton {{
    min-height: 34px;
    padding: 0 14px;
    color: {color['text']};
    background: {color['surface_alt']};
    border: 1px solid {color['border']};
    border-radius: 8px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {color['surface_hover']}; border-color: {color['border_strong']}; }}
QPushButton:pressed {{ background: {color['surface_pressed']}; }}
QPushButton:focus {{ border: 2px solid {color['accent']}; }}
QPushButton#primaryButton {{
    min-height: 36px;
    padding: 0 18px;
    color: {color['button_text']};
    background: {color['accent']};
    border-color: {color['accent']};
}}
QPushButton#primaryButton:hover {{ background: {color['accent_hover']}; border-color: {color['accent_hover']}; }}
QPushButton#linkButton, QPushButton#copyButton, QPushButton#moreButton {{
    min-height: 30px;
    padding: 0 10px;
    color: {color['text_soft']};
    background: transparent;
    border: 1px solid transparent;
    border-radius: 7px;
}}
QPushButton#linkButton:hover, QPushButton#copyButton:hover, QPushButton#moreButton:hover {{
    color: {color['text']};
    background: {color['surface_hover']};
    border-color: {color['border']};
}}
QPushButton#copyButton {{ color: {color['accent_text']}; background: {color['accent_soft']}; }}
QPushButton#copyButton[copied="true"] {{ color: {color['success']}; border-color: {color['success']}; }}
QPushButton#moreButton {{ min-width: 30px; max-width: 30px; padding: 0; font-weight: 800; }}
QPushButton#moreButton::menu-indicator {{ image: none; width: 0; }}
QFrame#preferenceBar {{
    background: transparent;
    border-top: 1px solid {color['border']};
    border-bottom: 1px solid {color['border']};
}}
QCheckBox {{ color: {color['text_soft']}; spacing: 8px; }}
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
QFrame#listPanel {{ background: {color['surface_alt']}; border: 1px solid {color['border']}; border-radius: 12px; }}
QWidget#scrollContent {{ background: transparent; }}
QFrame#jobRow {{ background: transparent; border-bottom: 1px solid {color['border']}; }}
QLabel#fileType {{
    color: {color['accent_text']};
    background: {color['accent_soft']};
    border-radius: 7px;
    font-size: 10px;
    font-weight: 750;
}}
QLabel#fileName, QLabel#sectionTitle, QLabel#emptyTitle {{ color: {color['text']}; font-weight: 680; }}
QLabel#sectionMeta {{ color: {color['text_faint']}; font-size: 12px; }}
QLabel#statusPending, QLabel#statusWorking, QLabel#statusSuccess, QLabel#statusError {{
    border-radius: 6px;
    padding: 0 6px;
    font-size: 12px;
    font-weight: 650;
}}
QLabel#statusPending {{ color: {color['text_faint']}; background: {color['surface_hover']}; }}
QLabel#statusWorking {{ color: {color['warning']}; background: {color['surface_hover']}; }}
QLabel#statusSuccess {{ color: {color['success']}; background: {color['success_soft']}; }}
QLabel#statusError {{ color: {color['error']}; background: {color['error_soft']}; }}
QFrame#noticeFrameSuccess, QFrame#noticeFrameError {{
    min-height: 38px;
    border-radius: 9px;
}}
QFrame#noticeFrameSuccess {{
    background: {color['success_soft']};
    border: 1px solid {color['border']};
}}
QFrame#noticeFrameError {{
    background: {color['error_soft']};
    border: 1px solid {color['border']};
}}
QFrame#noticeFrameSuccess QLabel#noticeText, QFrame#noticeFrameSuccess QLabel#noticeIcon {{ color: {color['success']}; background: transparent; }}
QFrame#noticeFrameError QLabel#noticeText, QFrame#noticeFrameError QLabel#noticeIcon {{ color: {color['error']}; background: transparent; }}
QLabel#noticeIcon {{ font-size: 13px; font-weight: 800; }}
QProgressBar#batchProgress {{ background: {color['border']}; border: none; border-radius: 2px; }}
QProgressBar#batchProgress::chunk {{ background: {color['accent']}; border-radius: 2px; }}
QScrollArea {{ background: transparent; border: 0; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ width: 8px; background: transparent; }}
QScrollBar::handle:vertical {{ min-height: 28px; background: {color['scroll']}; border-radius: 4px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QSizeGrip {{ width: 18px; height: 18px; background: transparent; }}
QToolTip {{
    color: {color['text']};
    background: {color['surface_raised']};
    border: 1px solid {color['border_strong']};
    padding: 5px 7px;
}}
"""
