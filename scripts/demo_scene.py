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
