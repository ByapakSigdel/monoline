"""Strokes -> braille cells. Pure — no TUI imports."""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Tuple

from monoline.document import Point, Stroke

BRAILLE_BASE = 0x2800
DOT_BITS: Dict[Tuple[int, int], int] = {
    (0, 0): 0x01, (0, 1): 0x02, (0, 2): 0x04, (1, 0): 0x08,
    (1, 1): 0x10, (1, 2): 0x20, (0, 3): 0x40, (1, 3): 0x80,
}


def _line_dots(a: Point, b: Point):
    """Integer Bresenham between rounded dot coordinates."""
    x0, y0 = int(round(a[0])), int(round(a[1]))
    x1, y1 = int(round(b[0])), int(round(b[1]))
    dx, sx = abs(x1 - x0), 1 if x0 < x1 else -1
    dy, sy = -abs(y1 - y0), 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        yield x0, y0
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def _disc_offsets(radius: float) -> List[Tuple[int, int]]:
    r = int(math.ceil(radius))
    return [(dx, dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1)
            if dx * dx + dy * dy <= radius * radius]


def render_cells(strokes: Iterable[Stroke], width: int, height: int
                 ) -> Dict[Tuple[int, int], Tuple[str, str]]:
    dots: Dict[Tuple[int, int], Tuple[int, str]] = {}  # (x,y) -> (seq, color)
    seq = 0
    for stroke in strokes:
        seq += 1
        pts = stroke.points or []
        if len(pts) == 1:
            pts = [pts[0], pts[0]]
        offsets = [(0, 0)] if stroke.width <= 1.0 else _disc_offsets(stroke.width / 2)
        for a, b in zip(pts, pts[1:]):
            for x, y in _line_dots(a, b):
                for dx, dy in offsets:
                    px, py = x + dx, y + dy
                    if not (0 <= px < width and 0 <= py < height):
                        continue
                    if stroke.kind == "erase":
                        dots.pop((px, py), None)
                    else:
                        dots[(px, py)] = (seq, stroke.color)

    bits: Dict[Tuple[int, int], int] = {}
    best: Dict[Tuple[int, int], Tuple[int, str]] = {}
    for (x, y), (sq, color) in dots.items():
        key = (x // 2, y // 4)
        bits[key] = bits.get(key, 0) | DOT_BITS[(x % 2, y % 4)]
        if sq >= best.get(key, (-1, ""))[0]:
            best[key] = (sq, color)
    return {key: (chr(BRAILLE_BASE + b), best[key][1]) for key, b in bits.items()}
