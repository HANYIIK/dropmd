#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"

python -m pip install -e '.[build]'
python scripts/build_icons.py
python -m PyInstaller --noconfirm --clean DropMD.spec

mkdir -p release
architecture="$(uname -m)"
release_name="${DROPMD_RELEASE_NAME:-DropMD-macOS-${architecture}.dmg}"
hdiutil create -volname "DropMD" -srcfolder dist/DropMD.app -ov -format UDZO "release/$release_name"

echo "Created release/$release_name"
