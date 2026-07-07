from monoline.bitmap import Bitmap


def test_bitmap_defaults():
    b = Bitmap(80, 40)
    assert (b.width, b.height) == (80, 40)
    assert b.cells == {}


def test_bitmap_cells():
    b = Bitmap(80, 40, {(3, 2): (255, "#ff0000")})
    assert b.cells[(3, 2)] == (255, "#ff0000")
