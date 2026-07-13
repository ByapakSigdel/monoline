"""Generate README GIFs with a deterministic Pillow frame renderer.

Run: .venv\\Scripts\\python.exe scripts\\make_gifs.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

import math
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from demo_scene import (
    demo_model_mesh,
    make_demo_image,
    petal_points,
    wobbly_circle_points,
)

from monoline.bitmap import Bitmap
from monoline.document import Stroke
from monoline.imageconv import convert
from monoline.model3d import ModelPose, render_model
from monoline.palettes import get_palette
from monoline.raster import BRAILLE_BASE, DOT_BITS, render_cells
from monoline.shapes import recognize
from monoline.symmetry import siblings

ASSETS = Path(__file__).resolve().parent.parent / "docs" / "assets"
W, H = 160, 96          # canvas in dots
DOT = 6                  # px per dot in the frame
SS = 2                   # supersampling factor
MAX_BYTES = 4 * 1024 * 1024


def render_frame(strokes: List[Stroke], bitmap: Optional[Bitmap],
                 background: str) -> Image.Image:
    px = DOT * SS
    img = Image.new("RGB", (W * px, H * px), background)
    d = ImageDraw.Draw(img)
    r = px * 0.42
    for (cx, cy), (char, color) in render_cells(strokes, W, H, bitmap).items():
        bits = ord(char) - BRAILLE_BASE
        for (dx, dy), bit in DOT_BITS.items():
            if bits & bit:
                x = (cx * 2 + dx + 0.5) * px
                y = (cy * 4 + dy + 0.5) * px
                d.ellipse((x - r, y - r, x + r, y + r), fill=color)
    return img.resize((W * DOT, H * DOT), Image.LANCZOS)


def save_gif(frames: List[Image.Image], path: Path, ms: int) -> None:
    quantized = [f.quantize(colors=128) for f in frames]
    quantized[0].save(path, save_all=True, append_images=quantized[1:],
                      duration=ms, loop=0, optimize=True)
    size = path.stat().st_size
    assert size < MAX_BYTES, f"{path} is {size} bytes (>= 4 MB)"
    print(f"wrote {path} ({size / 1024:.0f} KB)")


def reveal(stroke: Stroke, fraction: float) -> Stroke:
    n = max(1, round(len(stroke.points) * fraction))
    return Stroke(points=stroke.points[:n], color=stroke.color,
                  kind=stroke.kind, width=stroke.width)


def gif_drawing() -> None:
    pal = get_palette("tokyonight")
    # The petal must be centered on (W/2, H/2): siblings() always mirrors
    # "radial4" around the canvas center, so the 4 arms only share an
    # origin (and read as one mandala) when the petal's own center matches
    # that pivot. An off-center petal produces 4 disconnected scattered
    # arcs instead - confirmed by rendering a PNG preview of the original
    # W*0.30/H*0.55 placement, which also clipped off-canvas.
    raw = Stroke(points=wobbly_circle_points(W * 0.80, H * 0.22, H * 0.14),
                 color=pal.colors[1])
    snapped = Stroke(points=recognize(raw.points), color=pal.colors[1])
    petal = Stroke(points=petal_points(W * 0.5, H * 0.5, H * 0.34),
                   color=pal.colors[4])
    mirrors = [Stroke(points=p, color=petal.color)
               for p in siblings(petal.points, "radial4", W, H)]

    frames: List[Image.Image] = []
    steps = 24
    for i in range(1, steps + 1):            # wobbly circle grows...
        frames.append(render_frame([reveal(raw, i / steps)], None, pal.background))
    frames += [render_frame([snapped], None, pal.background)] * 8   # ...snaps!
    for i in range(1, steps + 1):            # mandala mirrors live
        part = [snapped, reveal(petal, i / steps)]
        part += [reveal(m, i / steps) for m in mirrors]
        frames.append(render_frame(part, None, pal.background))
    frames += [frames[-1]] * 16              # hold the finish
    save_gif(frames, ASSETS / "demo-drawing.gif", ms=70)


def gif_import() -> None:
    pal = get_palette("tokyonight")
    bitmap = convert(make_demo_image(), W, H, pal.background)
    order = sorted(bitmap.cells)             # reveal in scan order
    steps = 30
    frames: List[Image.Image] = []
    for i in range(1, steps + 1):
        shown = order[: round(len(order) * i / steps)]
        partial = Bitmap(W, H, {k: bitmap.cells[k] for k in shown})
        frames.append(render_frame([], partial, pal.background))
    doodle = Stroke(points=wobbly_circle_points(W * 0.5, H * 0.78, H * 0.12),
                    color=pal.colors[2])
    for i in range(1, 17):                   # doodle over the photo
        frames.append(render_frame([reveal(doodle, i / 16)], bitmap,
                                   pal.background))
    frames += [frames[-1]] * 16
    save_gif(frames, ASSETS / "demo-import.gif", ms=70)


def gif_model3d() -> None:
    pal = get_palette("tokyonight")
    vertices, faces = demo_model_mesh()
    frames: List[Image.Image] = []
    spin_steps = 28
    for i in range(spin_steps):
        pose = ModelPose(yaw=i * 2 * math.pi / spin_steps, pitch=0.35)
        bitmap = render_model(vertices, faces, pose, W, H,
                              pal.grid, pal.colors[3])
        frames.append(render_frame([], bitmap, pal.background))
    move_steps = 14
    base_yaw = 2 * math.pi * (spin_steps - 1) / spin_steps
    for i in range(1, move_steps + 1):
        t = i / move_steps
        pose = ModelPose(
            yaw=base_yaw + t * 0.6,
            pitch=0.35 + t * 0.25,
            pan_x=t * 18 - 9,
            pan_y=math.sin(t * math.pi) * 10,
        )
        bitmap = render_model(vertices, faces, pose, W, H,
                              pal.grid, pal.colors[3])
        frames.append(render_frame([], bitmap, pal.background))
    final_pose = ModelPose(yaw=base_yaw + 0.6, pitch=0.6, pan_x=9, pan_y=0)
    final_bitmap = render_model(vertices, faces, final_pose, W, H,
                                pal.grid, pal.colors[3])
    doodle = Stroke(points=wobbly_circle_points(W * 0.5, H * 0.82, H * 0.09),
                    color=pal.colors[2])
    for i in range(1, 13):
        frames.append(render_frame([reveal(doodle, i / 12)], final_bitmap,
                                   pal.background))
    frames += [frames[-1]] * 14
    save_gif(frames, ASSETS / "demo-model3d.gif", ms=75)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    gif_drawing()
    gif_import()
    gif_model3d()


if __name__ == "__main__":
    main()
