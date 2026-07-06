from monoline.app import MonolineApp
from monoline.canvas import DrawCanvas


async def test_drag_creates_stroke():
    app = MonolineApp()
    async with app.run_test(size=(40, 12)):
        canvas = app.query_one(DrawCanvas)
        canvas.begin(2, 2, ctrl=False)
        canvas.extend(6, 4, ctrl=False)
        canvas.extend(10, 6, ctrl=False)
        canvas.end()
        assert len(app.document.strokes) == 1
        assert len(app.document.strokes[0].points) >= 3


async def test_undo_key_removes_stroke():
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        canvas = app.query_one(DrawCanvas)
        canvas.begin(2, 2, ctrl=False)
        canvas.extend(6, 4, ctrl=False)
        canvas.end()
        await pilot.press("u")
        assert app.document.strokes == []
        await pilot.press("r")
        assert len(app.document.strokes) == 1


async def test_document_sized_from_canvas_after_layout():
    app = MonolineApp()
    async with app.run_test(size=(40, 12)):
        canvas = app.query_one(DrawCanvas)
        assert canvas.size.width > 0
        assert app.document.width == canvas.size.width * 2
        assert app.document.height == canvas.size.height * 4
        assert app.document.dirty is False


async def test_cell_to_dot_mapping():
    app = MonolineApp()
    async with app.run_test(size=(40, 12)):
        canvas = app.query_one(DrawCanvas)
        canvas.begin(3, 5, ctrl=False)
        canvas.end()
        (x, y) = app.document.strokes[0].points[0]
        assert (x, y) == (6.5, 21.5)


async def test_ctrl_drag_snaps_near_circle():
    app = MonolineApp()
    app.config.shape_correct = "ctrl"
    async with app.run_test(size=(60, 20)):
        canvas = app.query_one(DrawCanvas)
        import math
        cells = [(15 + round(8 * math.cos(a * math.pi / 12)),
                  8 + round(4 * math.sin(a * math.pi / 12))) for a in range(25)]
        canvas.begin(*cells[0], ctrl=True)
        for c, r in cells[1:]:
            canvas.extend(c, r, ctrl=True)
        canvas.end()
        pts = app.document.strokes[0].points
        assert len(pts) == 65  # snapped to sampled ellipse/circle


async def test_color_and_palette_keys():
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        start = app.palette.name
        await pilot.press("3")
        assert app.color_index == 2
        assert app.pen_color == app.palette.colors[2]
        await pilot.press("p")
        assert app.palette.name != start


async def test_palette_switch_keeps_existing_stroke_colors():
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        canvas = app.query_one(DrawCanvas)
        canvas.begin(2, 2, ctrl=False)
        canvas.extend(8, 4, ctrl=False)
        canvas.end()
        before = app.document.strokes[0].color
        await pilot.press("p")
        assert app.document.strokes[0].color == before
