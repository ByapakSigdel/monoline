from PIL import Image

from monoline.imageconv import convert


def solid(color, size=(20, 40)):
    return Image.new("RGB", size, color)


def lit_dots(bm):
    from monoline.raster import DOT_BITS
    out = set()
    for (cx, cy), (bits, _) in bm.cells.items():
        for (dx, dy), bit in DOT_BITS.items():
            if bits & bit:
                out.add((cx * 2 + dx, cy * 4 + dy))
    return out


def test_white_image_all_lit_white_cells():
    bm = convert(solid((255, 255, 255)), 20, 40, "#1a1b26")
    assert len(lit_dots(bm)) == 20 * 40
    assert all(color == "#ffffff" for _, color in bm.cells.values())
    assert (bm.width, bm.height) == (20, 40)


def test_black_image_empty():
    bm = convert(solid((0, 0, 0)), 20, 40, "#1a1b26")
    assert bm.cells == {}


def test_half_split_lit_left_only():
    img = Image.new("RGB", (40, 40), (0, 0, 0))
    img.paste((255, 255, 255), (0, 0, 20, 40))
    bm = convert(img, 40, 40, "#1a1b26")
    dots = lit_dots(bm)
    assert dots and all(x < 20 for x, _ in dots)


def test_color_halves_cell_colors():
    img = Image.new("RGB", (40, 40), (0, 0, 255))
    img.paste((255, 0, 0), (0, 0, 20, 40))
    bm = convert(img, 40, 40, "#1a1b26")
    for (cx, _), (_, color) in bm.cells.items():
        assert color == ("#ff0000" if cx < 10 else "#0000ff")


def test_gradient_density_increases():
    img = Image.new("L", (64, 16))
    img.putdata([x * 4 for _ in range(16) for x in range(64)])
    bm = convert(img.convert("RGB"), 64, 16, "#1a1b26")
    dots = lit_dots(bm)
    left = sum(1 for x, _ in dots if x < 16)
    right = sum(1 for x, _ in dots if x >= 48)
    assert right > left


def test_transparent_composites_over_background():
    img = Image.new("RGBA", (20, 40), (0, 0, 0, 0))
    assert convert(img, 20, 40, "#000000").cells == {}
    bm = convert(img, 20, 40, "#ffffff")
    assert len(lit_dots(bm)) == 20 * 40


def test_tall_image_centered_horizontally():
    bm = convert(solid((255, 255, 255), size=(10, 40)), 40, 40, "#1a1b26")
    xs = {x for x, _ in lit_dots(bm)}
    assert min(xs) == 15 and max(xs) == 24  # 10-wide fit centered in 40


def test_exif_orientation_respected(tmp_path):
    import io as _io
    img = Image.new("RGB", (8, 4), (255, 255, 255))
    exif = Image.Exif()
    exif[274] = 6  # rotate 270 to display upright -> portrait 4x8
    buf = _io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    buf.seek(0)
    bm = convert(Image.open(buf), 40, 40, "#1a1b26")
    xs = {x for x, _ in lit_dots(bm)}
    assert max(xs) - min(xs) + 1 <= 22  # portrait fit: ~20 dots wide, not 40
