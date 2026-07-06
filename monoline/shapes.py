"""Shape recognition for Ctrl shape-correction. Pure geometry, no deps."""
from __future__ import annotations

import math
from typing import List, Optional, Tuple

from monoline.document import Point

THRESHOLD = 0.08
MIN_POINTS = 8
MIN_DIAG = 4.0


def _path_length(pts: List[Point]) -> float:
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def _bbox(pts: List[Point]) -> Tuple[float, float, float, float]:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _snap(p: Point, spacing: Optional[float]) -> Point:
    if not spacing:
        return p
    return (round(p[0] / spacing) * spacing, round(p[1] / spacing) * spacing)


def _rms(errors: List[float]) -> float:
    return math.sqrt(sum(e * e for e in errors) / len(errors))


def _fit_line(pts: List[Point]):
    """Total least squares via covariance principal axis."""
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts) / n
    syy = sum((p[1] - my) ** 2 for p in pts) / n
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts) / n
    theta = 0.5 * math.atan2(2 * sxy, sxx - syy)
    ux, uy = math.cos(theta), math.sin(theta)
    ts = [(p[0] - mx) * ux + (p[1] - my) * uy for p in pts]
    errors = [abs(-(p[0] - mx) * uy + (p[1] - my) * ux) for p in pts]
    a = (mx + min(ts) * ux, my + min(ts) * uy)
    b = (mx + max(ts) * ux, my + max(ts) * uy)
    return [a, b], _rms(errors)


def _fit_circle(pts: List[Point]):
    """Kåsa algebraic fit: minimize x²+y² + D·x + E·y + F."""
    n = len(pts)
    sx = sum(p[0] for p in pts); sy = sum(p[1] for p in pts)
    sxx = sum(p[0] * p[0] for p in pts); syy = sum(p[1] * p[1] for p in pts)
    sxy = sum(p[0] * p[1] for p in pts)
    sxz = sum(p[0] * (p[0] ** 2 + p[1] ** 2) for p in pts)
    syz = sum(p[1] * (p[0] ** 2 + p[1] ** 2) for p in pts)
    sz = sum(p[0] ** 2 + p[1] ** 2 for p in pts)
    # Solve [sxx sxy sx; sxy syy sy; sx sy n] · [D E F]ᵀ = [sxz; syz; sz]
    m = [[sxx, sxy, sx, sxz], [sxy, syy, sy, syz], [sx, sy, float(n), sz]]
    sol = _gauss3(m)
    if sol is None:
        return None, math.inf
    d, e, f = sol
    cx, cy = d / 2, e / 2
    rr = f + cx * cx + cy * cy
    if rr <= 0:
        return None, math.inf
    r = math.sqrt(rr)
    errors = [abs(math.dist((cx, cy), p) - r) for p in pts]
    return (cx, cy, r), _rms(errors)


def _gauss3(m):
    """Gaussian elimination on a 3x4 augmented matrix."""
    a = [row[:] for row in m]
    for col in range(3):
        pivot = max(range(col, 3), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-12:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        for r in range(3):
            if r != col:
                factor = a[r][col] / a[col][col]
                a[r] = [v - factor * w for v, w in zip(a[r], a[col])]
    return [a[i][3] / a[i][i] for i in range(3)]


def _fit_ellipse(pts: List[Point]):
    """Axis-aligned ellipse from the bounding box."""
    x0, y0, x1, y1 = _bbox(pts)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
    if rx < 1e-6 or ry < 1e-6:
        return None, math.inf
    scale = min(rx, ry)
    errors = []
    for x, y in pts:
        f = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
        errors.append(abs(math.sqrt(max(f, 0.0)) - 1.0) * scale)
    return (cx, cy, rx, ry), _rms(errors)


def _dominant_angle(pts: List[Point]) -> float:
    """Length-weighted mean segment angle folded into [0, π/2)."""
    sx = sy = 0.0
    for a, b in zip(pts, pts[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length < 1e-9:
            continue
        ang = math.atan2(dy, dx) % (math.pi / 2)
        sx += math.cos(4 * ang) * length
        sy += math.sin(4 * ang) * length
    return math.atan2(sy, sx) / 4 if (sx or sy) else 0.0


def _fit_rectangle(pts: List[Point]):
    theta = _dominant_angle(pts)
    c, s = math.cos(-theta), math.sin(-theta)
    rot = [(x * c - y * s, x * s + y * c) for x, y in pts]
    x0, y0, x1, y1 = _bbox(rot)
    errors = []
    for x, y in rot:
        d = min(abs(x - x0), abs(x - x1), abs(y - y0), abs(y - y1))
        errors.append(d)
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    ci, si = math.cos(theta), math.sin(theta)
    unrot = [(x * ci - y * si, x * si + y * ci) for x, y in corners]
    return unrot, _rms(errors)


def _sample_ellipse(cx, cy, rx, ry, n=64) -> List[Point]:
    out = [(cx + rx * math.cos(2 * math.pi * i / n),
            cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]
    out.append(out[0])
    return out


def recognize(points: List[Point], grid_spacing: Optional[float] = None
              ) -> Optional[List[Point]]:
    pts = [p for i, p in enumerate(points) if i == 0 or p != points[i - 1]]
    if len(pts) < MIN_POINTS:
        return None
    x0, y0, x1, y1 = _bbox(pts)
    diag = math.hypot(x1 - x0, y1 - y0)
    if diag < MIN_DIAG:
        return None
    closed = math.dist(pts[0], pts[-1]) < 0.2 * _path_length(pts)

    candidates = []  # (score, builder)
    if not closed:
        line, err = _fit_line(pts)
        candidates.append((err / diag, ("line", line)))
    else:
        circle, err = _fit_circle(pts)
        if circle is not None:
            candidates.append((err / diag, ("circle", circle)))
        ellipse, err = _fit_ellipse(pts)
        if ellipse is not None:
            candidates.append((err / diag, ("ellipse", ellipse)))
        rect, err = _fit_rectangle(pts)
        candidates.append((err / diag, ("rect", rect)))

    candidates.sort(key=lambda c: c[0])
    score, (kind, data) = candidates[0]
    if score >= THRESHOLD:
        return None

    if kind == "line":
        return [_snap(data[0], grid_spacing), _snap(data[1], grid_spacing)]
    if kind == "circle":
        cx, cy, r = data
        cx, cy = _snap((cx, cy), grid_spacing)
        return _sample_ellipse(cx, cy, r, r)
    if kind == "ellipse":
        cx, cy, rx, ry = data
        cx, cy = _snap((cx, cy), grid_spacing)
        return _sample_ellipse(cx, cy, rx, ry)
    corners = [_snap(p, grid_spacing) for p in data]
    return corners + [corners[0]]
