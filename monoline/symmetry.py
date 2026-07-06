"""Mirror/radial stroke transforms. Pure."""
from __future__ import annotations

from typing import List

from monoline.document import Point

MODES = ["off", "vertical", "horizontal", "radial4"]


def siblings(points: List[Point], mode: str, width: int, height: int
             ) -> List[List[Point]]:
    cx, cy = width / 2, height / 2
    if mode == "vertical":
        return [[(2 * cx - x, y) for x, y in points]]
    if mode == "horizontal":
        return [[(x, 2 * cy - y) for x, y in points]]
    if mode == "radial4":
        out = []
        for _ in range(3):
            points = [(cx - (y - cy), cy + (x - cx)) for x, y in points]
            out.append(list(points))
        return out
    return []
