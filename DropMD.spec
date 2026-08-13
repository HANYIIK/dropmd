import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules


root = Path(SPECPATH)
datas = [
    (str(root / "THIRD_PARTY_NOTICES.md"), "."),
    (str(root / "assets" / "icon.png"), "assets"),
]
hiddenimports = []

for package in ("markitdown", "magika", "mammoth"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    hiddenimports += package_hiddenimports

hiddenimports += collect_submodules("markitdown.converters")
icon = root / "assets" / ("icon.icns" if sys.platform == "darwin" else "icon.ico")

a = Analysis(
    [str(root / "dropmd_entry.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "IPython", "pytest", "pygments"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DropMD",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(icon),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="DropMD",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="DropMD.app",
        icon=str(icon),
        bundle_identifier="com.dropmd.desktop",
        info_plist={
            "CFBundleDevelopmentRegion": "zh_CN",
            "CFBundleDisplayName": "DropMD",
            "CFBundleGetInfoString": "DropMD 1.2.0 — Document to Markdown converter",
            "CFBundleShortVersionString": "1.2.0",
            "CFBundleVersion": "120",
            "LSApplicationCategoryType": "public.app-category.productivity",
            "LSMinimumSystemVersion": "11.0",
            "NSHumanReadableCopyright": "Copyright © 2026 DropMD",
            "MDItemDescription": "将 DOCX、PDF、PPTX、XLSX 等文档转换为 Markdown",
            "NSHighResolutionCapable": True,
            "CFBundleDocumentTypes": [
                {
                    "CFBundleTypeName": "Supported document",
                    "CFBundleTypeRole": "Viewer",
                    "LSHandlerRank": "Alternate",
                    "CFBundleTypeExtensions": [
                        "csv", "docx", "epub", "htm", "html", "ipynb", "json",
                        "msg", "pdf", "pptx", "txt", "xls", "xlsx", "xml", "zip",
                    ],
                }
            ],
        },
    )
