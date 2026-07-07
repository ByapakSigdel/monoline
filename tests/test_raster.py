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


from monoline.bitmap import Bitmap


def test_bitmap_seeds_cells():
    bm = Bitmap(8, 8, {(0, 0): (0x01, "#112233"), (1, 1): (0xFF, "#445566")})
    cells = render_cells([], 8, 8, bitmap=bm)
    assert cells[(0, 0)] == ("⠁", "#112233")
    assert cells[(1, 1)] == ("⣿", "#445566")


def test_pen_stroke_wins_over_bitmap():
    bm = Bitmap(8, 8, {(0, 0): (0x01, "#111111")})
    pen = Stroke(points=[(1.0, 0.0)], color="#ff0000")  # same cell, dot 4
    cells = render_cells([pen], 8, 8, bitmap=bm)
    char, color = cells[(0, 0)]
    assert ord(char) - 0x2800 == 0x01 | 0x08  # bits merge
    assert color == "#ff0000"  # stroke color wins


def test_erase_clears_bitmap_dots_nondestructively():
    bm = Bitmap(8, 8, {(0, 0): (0xFF, "#ffffff")})
    rub = Stroke(points=[(0.5, 1.5)], kind="erase", width=8.0)
    cells = render_cells([rub], 8, 8, bitmap=bm)
    assert (0, 0) not in cells
    assert bm.cells[(0, 0)] == (0xFF, "#ffffff")  # source data untouched


def test_bitmap_cells_outside_canvas_clipped():
    bm = Bitmap(100, 100, {(30, 20): (0xFF, "#ffffff")})  # beyond an 8x8 canvas
    assert render_cells([], 8, 8, bitmap=bm) == {}


def test_no_bitmap_behaves_as_before():
    s = Stroke(points=[(0.0, 0.0)], color="#ff0000")
    assert render_cells([s], 8, 8) == {(0, 0): ("⠁", "#ff0000")}
