"""Stroke smoothing: dedupe -> Chaikin -> resample. Pure."""
from __future__ import annotations

import math
from typing import List

from monoline.document import Point


def _dedupe(points: List[Point]) -> List[Point]:
    out: List[Point] = []
    for p in points:
        if not out or p != out[-1]:
            out.append(p)
    return out


def _chaikin(points: List[Point]) -> List[Point]:
    if len(points) < 3:
        return points
    out = [points[0]]
    for a, b in zip(points, points[1:]):
        out.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
        out.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
    out.append(points[-1])
    return out


def _resample(points: List[Point], spacing: float = 1.0) -> List[Point]:
    if len(points) < 2:
        return points
    out = [points[0]]
    carried = 0.0
    for a, b in zip(points, points[1:]):
        seg = math.dist(a, b)
        if seg == 0:
            continue
        t = spacing - carried
        while t <= seg:
            f = t / seg
            out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
            t += spacing
        carried = seg - (t - spacing)
    if out[-1] != points[-1]:
        out.append(points[-1])
    return out


def smooth(points: List[Point], strength: float = 0.5) -> List[Point]:
    pts = _dedupe(list(points))
    if len(pts) < 3 or strength <= 0:
        return pts if len(pts) < len(points) else list(points)
    iterations = max(1, min(3, round(strength * 3)))
    for _ in range(iterations):
        pts = _chaikin(pts)
    return _resample(pts)
