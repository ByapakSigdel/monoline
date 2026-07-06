import math
import random

from monoline.shapes import recognize


def _jitter(pts, amount, seed=7):
    rng = random.Random(seed)
    return [(x + rng.uniform(-amount, amount), y + rng.uniform(-amount, amount))
            for x, y in pts]


def _circle(cx, cy, r, n=40):
    return [(cx + r * math.cos(2 * math.pi * i / n),
             cy + r * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]


def test_too_few_points_rejected():
    assert recognize([(0.0, 0.0), (10.0, 10.0)]) is None


def test_tiny_stroke_rejected():
    pts = [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (1.5, 1.0),
           (2.0, 1.5), (2.0, 2.0), (1.5, 2.0), (1.0, 1.5), (0.5, 1.0)]
    assert recognize(pts) is None


def test_noisy_line_snaps_to_line():
    pts = _jitter([(float(i), float(2 * i)) for i in range(20)], 0.4)
    out = recognize(pts)
    assert out is not None and len(out) == 2
    (x0, y0), (x1, y1) = out
    # slope ≈ 2
    assert abs((y1 - y0) / (x1 - x0) - 2.0) < 0.2


def test_noisy_circle_snaps_to_circle():
    pts = _jitter(_circle(50, 50, 20), 0.8)
    out = recognize(pts)
    assert out is not None and len(out) == 65
    cx = sum(x for x, _ in out[:-1]) / 64
    cy = sum(y for _, y in out[:-1]) / 64
    radii = [math.dist((cx, cy), p) for p in out[:-1]]
    assert abs(cx - 50) < 2 and abs(cy - 50) < 2
    assert max(radii) - min(radii) < 0.01  # perfect circle out


def test_noisy_rectangle_snaps_to_rectangle():
    top = [(float(x), 10.0) for x in range(10, 41, 2)]
    right = [(40.0, float(y)) for y in range(10, 31, 2)]
    bottom = [(float(x), 30.0) for x in range(40, 9, -2)]
    left = [(10.0, float(y)) for y in range(30, 9, -2)]
    pts = _jitter(top + right + bottom + left + [(10.0, 10.0)], 0.5)
    out = recognize(pts)
    assert out is not None and len(out) == 5
    assert out[0] == out[-1]


def test_scribble_stays_scribble():
    rng = random.Random(3)
    pts = [(rng.uniform(0, 60), rng.uniform(0, 60)) for _ in range(60)]
    assert recognize(pts) is None


def test_grid_snapping_line_endpoints():
    pts = [(float(i), 7.0) for i in range(3, 36)]
    out = recognize(pts, grid_spacing=8.0)
    assert out is not None
    for x, y in out:
        assert x % 8 == 0 and y % 8 == 0
