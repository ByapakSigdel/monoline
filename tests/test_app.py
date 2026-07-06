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


async def test_cell_to_dot_mapping():
    app = MonolineApp()
    async with app.run_test(size=(40, 12)):
        canvas = app.query_one(DrawCanvas)
        canvas.begin(3, 5, ctrl=False)
        canvas.end()
        (x, y) = app.document.strokes[0].points[0]
        assert (x, y) == (6.5, 21.5)
