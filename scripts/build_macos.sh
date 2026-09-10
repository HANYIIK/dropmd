#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"

python -m pip install -e '.[build]'
python scripts/build_icons.py
python -m PyInstaller --noconfirm --clean DropMD.spec
python scripts/check_macos_compatibility.py dist/DropMD.app

mkdir -p release
architecture="$(uname -m)"
release_name="${DROPMD_RELEASE_NAME:-DropMD-macOS-${architecture}.dmg}"
python -m dmgbuild \
  -s packaging/macos/dmg_settings.py \
  -D app=dist/DropMD.app \
  "Install DropMD" \
  "release/$release_name"

echo "Created release/$release_name"
