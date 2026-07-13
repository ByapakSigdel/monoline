"""Deterministic demo content shared by the screenshot and GIF scripts."""
from __future__ import annotations

import math

from PIL import Image, ImageDraw


def make_demo_image(size=(320, 200)):
    """A generated sunset scene — no licensing, fully reproducible."""
    w, h = size
    img = Image.new("RGB", size)
    top, bottom = (26, 27, 38), (247, 118, 142)
    for y in range(h):
        t = y / (h - 1)
        img.paste(tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)),
                  (0, y, w, y + 1))
    d = ImageDraw.Draw(img)
    d.ellipse((w * 0.30, h * 0.18, w * 0.70, h * 0.62), fill=(224, 175, 104))
    d.polygon([(0, h), (w * 0.35, h * 0.55), (w * 0.62, h)], fill=(65, 72, 104))
    d.polygon([(w * 0.45, h), (w * 0.78, h * 0.45), (w, h)], fill=(52, 59, 88))
    return img


def circle_points(cx, cy, r, n=48):
    return [(cx + r * math.cos(2 * math.pi * i / n),
             cy + r * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]


def wobbly_circle_points(cx, cy, r, n=48):
    """A hand-drawn-looking circle (deterministic wobble, no random)."""
    return [(cx + (r + 1.5 * math.sin(7 * a)) * math.cos(a),
             cy + (r + 1.5 * math.sin(7 * a)) * math.sin(a))
            for a in [2 * math.pi * i / n for i in range(n + 1)]]


def petal_points(cx, cy, r, n=32):
    """One flowing curve; radial-4 symmetry turns it into a mandala."""
    return [(cx + r * t * math.cos(3.0 * t), cy + r * t * math.sin(3.0 * t))
            for t in [i / n for i in range(1, n + 1)]]


def demo_model_mesh():
    """A normalized icosahedron — reproducible, no external model file."""
    t = (1.0 + math.sqrt(5.0)) / 2.0
    raw = [
        (-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0),
        (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
        (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1),
    ]
    vertices = []
    for x, y, z in raw:
        length = math.sqrt(x * x + y * y + z * z)
        vertices.append((x / length, y / length, z / length))
    faces = [
        (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
        (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
        (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
        (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1),
    ]
    return vertices, faces


def write_demo_model_obj(path) -> None:
    """Write the demo icosahedron as an OBJ file."""
    vertices, faces = demo_model_mesh()
    lines = [f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in vertices]
    lines += [f"f {a + 1} {b + 1} {c + 1}" for a, b, c in faces]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
