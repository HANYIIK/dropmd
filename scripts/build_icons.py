from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def render(size: int) -> Image.Image:
    scale = size / 1024
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def box(values):
        return tuple(round(value * scale) for value in values)

    draw.rounded_rectangle(box((52, 52, 972, 972)), radius=round(220 * scale), fill="#168478")
    draw.polygon([box((300, 218)), box((586, 218)), box((736, 368)), box((736, 806)), box((300, 806))], fill="#F7FCFA")
    draw.polygon([box((586, 218)), box((736, 368)), box((586, 368))], fill="#B8DDD6")
    width = max(2, round(54 * scale))
    draw.line([box((394, 480)), box((512, 598)), box((630, 480))], fill="#168478", width=width, joint="curve")
    draw.line([box((512, 430)), box((512, 598))], fill="#168478", width=width)
    draw.line([box((386, 700)), box((638, 700))], fill="#168478", width=max(2, round(42 * scale)))
    return image


def main() -> int:
    ASSETS.mkdir(exist_ok=True)
    render(512).save(ASSETS / "icon.png")
    render(256).save(ASSETS / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    if sys.platform == "darwin" and shutil.which("iconutil"):
        iconset = ASSETS / "DropMD.iconset"
        iconset.mkdir(exist_ok=True)
        for points in (16, 32, 128, 256, 512):
            render(points).save(iconset / f"icon_{points}x{points}.png")
            render(points * 2).save(iconset / f"icon_{points}x{points}@2x.png")
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(ASSETS / "icon.icns")], check=True)
        shutil.rmtree(iconset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
