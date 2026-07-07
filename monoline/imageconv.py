"""Image -> Bitmap conversion. Pure logic on top of Pillow."""
from __future__ import annotations

from typing import Dict, List, Tuple

from PIL import Image, ImageOps

from monoline.bitmap import Bitmap
from monoline.raster import DOT_BITS

_FS_KERNEL = ((1, 0, 7 / 16), (-1, 1, 3 / 16), (0, 1, 5 / 16), (1, 1, 1 / 16))


def _hex_to_rgb(color: str) -> Tuple[int, int, int]:
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def _pixels(img: Image.Image) -> List:
    """Pixel values as a flat list.

    Pillow 12.1 deprecated ``getdata()`` in favor of ``get_flattened_data()``
    (same output shape, no internal-type wrapper). ``pillow>=10`` is our
    declared floor and predates that method, so prefer it when present and
    fall back for older installs — keeps this warning-free on current
    Pillow without narrowing the supported range.
    """
    getter = getattr(img, "get_flattened_data", None)
    return list(getter()) if getter is not None else list(img.getdata())


def convert(img: Image.Image, dot_w: int, dot_h: int, background: str) -> Bitmap:
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGBA")
    base = Image.new("RGBA", img.size, _hex_to_rgb(background) + (255,))
    img = Image.alpha_composite(base, img).convert("RGB")

    scale = min(dot_w / img.width, dot_h / img.height)
    nw = max(1, round(img.width * scale))
    nh = max(1, round(img.height * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    ox, oy = (dot_w - nw) // 2, (dot_h - nh) // 2

    lum: List[float] = [float(v) for v in _pixels(img.convert("L"))]
    rgb = _pixels(img)

    bits: Dict[Tuple[int, int], int] = {}
    sums: Dict[Tuple[int, int], List[int]] = {}
    for y in range(nh):
        row = y * nw
        for x in range(nw):
            old = lum[row + x]
            new = 255.0 if old >= 127.5 else 0.0
            err = old - new
            for dx, dy, w in _FS_KERNEL:
                nx, ny = x + dx, y + dy
                if 0 <= nx < nw and 0 <= ny < nh:
                    lum[ny * nw + nx] += err * w
            if not new:
                continue
            px, py = x + ox, y + oy
            if not (0 <= px < dot_w and 0 <= py < dot_h):
                continue
            key = (px // 2, py // 4)
            bits[key] = bits.get(key, 0) | DOT_BITS[(px % 2, py % 4)]
            r, g, b = rgb[row + x]
            acc = sums.setdefault(key, [0, 0, 0, 0])
            acc[0] += r
            acc[1] += g
            acc[2] += b
            acc[3] += 1

    cells: Dict[Tuple[int, int], Tuple[int, str]] = {}
    for key, pattern in bits.items():
        r, g, b, n = sums[key]
        cells[key] = (pattern, f"#{r // n:02x}{g // n:02x}{b // n:02x}")
    return Bitmap(dot_w, dot_h, cells)
