from monoline.document import Stroke
from monoline.raster import render_cells


def test_single_dot():
    s = Stroke(points=[(0.0, 0.0)], color="#ff0000")
    cells = render_cells([s], 8, 8)
    assert cells == {(0, 0): ("⠁", "#ff0000")}  # dot 1 only


def test_full_cell():
    # all 8 dots of cell (0, 0)
    pts = [(float(x), float(y)) for y in range(4) for x in range(2)]
    strokes = [Stroke(points=[p], color="#ffffff") for p in pts]
    cells = render_cells(strokes, 8, 8)
    assert cells[(0, 0)][0] == "⣿"


def test_horizontal_line_spans_cells():
    s = Stroke(points=[(0.0, 0.0), (7.0, 0.0)], color="#00ff00")
    cells = render_cells([s], 8, 4)
    assert set(cells) == {(0, 0), (1, 0), (2, 0), (3, 0)}


def test_last_stroke_wins_color():
    a = Stroke(points=[(0.0, 0.0)], color="#aaaaaa")
    b = Stroke(points=[(1.0, 0.0)], color="#bbbbbb")  # same cell
    cells = render_cells([a, b], 8, 8)
    assert cells[(0, 0)][1] == "#bbbbbb"


def test_erase_clears_dots():
    pen = Stroke(points=[(0.0, 0.0), (7.0, 0.0)], color="#ffffff")
    rub = Stroke(points=[(4.0, 0.0)], kind="erase", width=2.0)
    cells = render_cells([pen, rub], 8, 4)
    assert (2, 0) not in cells  # dots 4-5 erased
    assert (0, 0) in cells


def test_clipping_outside_canvas():
    s = Stroke(points=[(-5.0, -5.0), (100.0, 100.0)], color="#ffffff")
    cells = render_cells([s], 8, 8)
    assert all(0 <= c < 4 and 0 <= r < 2 for c, r in cells)
