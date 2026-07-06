from monoline.symmetry import MODES, siblings

PTS = [(10.0, 20.0), (30.0, 40.0)]


def test_off_returns_nothing():
    assert siblings(PTS, "off", 100, 80) == []


def test_vertical_mirror():
    out = siblings(PTS, "vertical", 100, 80)
    assert out == [[(90.0, 20.0), (70.0, 40.0)]]


def test_horizontal_mirror():
    out = siblings(PTS, "horizontal", 100, 80)
    assert out == [[(10.0, 60.0), (30.0, 40.0)]]


def test_radial4_three_copies_rotated():
    out = siblings([(60.0, 40.0)], "radial4", 100, 80)
    assert len(out) == 3
    # center (50,40); point at (+10,0) → rotations: (0,+10),(-10,0),(0,-10)
    assert out[0] == [(50.0, 50.0)]
    assert out[1] == [(40.0, 40.0)]
    assert out[2] == [(50.0, 30.0)]


def test_modes_order():
    assert MODES == ["off", "vertical", "horizontal", "radial4"]
