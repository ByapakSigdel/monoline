import math

from monoline.smoothing import smooth


def test_short_input_unchanged():
    pts = [(0.0, 0.0), (4.0, 4.0)]
    assert smooth(pts) == pts


def test_zero_strength_unchanged():
    pts = [(0.0, 0.0), (5.0, 9.0), (10.0, 0.0)]
    assert smooth(pts, strength=0.0) == pts


def test_endpoints_preserved():
    pts = [(0.0, 0.0), (10.0, 20.0), (20.0, 0.0), (30.0, 20.0)]
    out = smooth(pts)
    assert out[0] == pts[0]
    assert out[-1] == pts[-1]


def test_jitter_reduced():
    # zigzag along y=0 with ±1 jitter; smoothing must shrink deviation
    pts = [(float(x), (1.0 if x % 2 else -1.0)) for x in range(20)]
    out = smooth(pts, strength=1.0)
    inner = out[2:-2]
    assert max(abs(y) for _, y in inner) < 1.0


def test_resample_density():
    pts = [(0.0, 0.0), (100.0, 0.0)]  # after dedupe len 2 → unchanged path
    zig = [(float(x * 5), float(x % 2)) for x in range(21)]
    out = smooth(zig, strength=0.5)
    # ~1 point per dot of path length (~100), generous bounds
    assert 50 <= len(out) <= 220


def test_duplicate_points_deduped():
    pts = [(0.0, 0.0), (0.0, 0.0), (5.0, 5.0), (5.0, 5.0), (10.0, 0.0)]
    out = smooth(pts, strength=0.5)
    for a, b in zip(out, out[1:]):
        assert a != b
