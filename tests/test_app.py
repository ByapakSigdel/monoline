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


async def test_palette_switch_updates_background_wysiwyg():
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        canvas = app.query_one(DrawCanvas)
        canvas.begin(2, 2, ctrl=False)
        canvas.extend(8, 4, ctrl=False)
        canvas.end()
        await pilot.press("p")
        assert app.document.background == app.palette.background
        assert canvas.styles.background.hex.lower() == app.palette.background.lower()


async def test_eraser_tool_creates_erase_stroke():
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        canvas = app.query_one(DrawCanvas)
        await pilot.press("e")
        assert app.tool == "erase"
        canvas.begin(2, 2, ctrl=False)
        canvas.extend(8, 4, ctrl=False)
        canvas.end()
        s = app.document.strokes[0]
        assert s.kind == "erase" and s.width == 6.0
        await pilot.press("d")
        assert app.tool == "pen"


async def test_symmetry_gesture_is_one_undo_unit():
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        canvas = app.query_one(DrawCanvas)
        await pilot.press("s")  # vertical
        assert app.symmetry == "vertical"
        canvas.begin(2, 2, ctrl=False)
        canvas.extend(8, 4, ctrl=False)
        canvas.end()
        assert len(app.document.strokes) == 2
        await pilot.press("u")
        assert app.document.strokes == []


async def test_grid_toggle_renders_grid_dots():
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        canvas = app.query_one(DrawCanvas)
        strip = canvas.render_line(0)
        assert "⠂" not in strip.text
        await pilot.press("g")
        assert app.grid_on is True
        strip = canvas.render_line(0)
        assert "⠂" in strip.text
        await pilot.press("g")
        assert app.grid_on is False


async def test_save_and_reopen(tmp_path):
    path = str(tmp_path / "pic.mono.json")
    app = MonolineApp(path)
    async with app.run_test(size=(40, 12)) as pilot:
        canvas = app.query_one(DrawCanvas)
        canvas.begin(2, 2, ctrl=False)
        canvas.extend(8, 4, ctrl=False)
        canvas.end()
        await pilot.press("ctrl+s")
        assert app.document.dirty is False
    app2 = MonolineApp(path)
    async with app2.run_test(size=(40, 12)):
        assert len(app2.document.strokes) == 1


async def test_help_overlay_opens_and_closes():
    from monoline.help import HelpScreen
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        await pilot.press("question_mark")
        assert isinstance(app.screen, HelpScreen)
        await pilot.press("escape")
        assert not isinstance(app.screen, HelpScreen)


async def test_clear_asks_confirmation():
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        canvas = app.query_one(DrawCanvas)
        canvas.begin(2, 2, ctrl=False)
        canvas.extend(8, 4, ctrl=False)
        canvas.end()
        await pilot.press("c")
        await pilot.press("y")
        assert app.document.strokes == []
        # undo restores even after clear
        await pilot.press("u")
        assert len(app.document.strokes) == 1


async def test_quit_with_unsaved_changes_confirms():
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        canvas = app.query_one(DrawCanvas)
        canvas.begin(2, 2, ctrl=False)
        canvas.end()
        await pilot.press("q")
        await pilot.press("n")  # stay
        assert app.is_running


async def test_erase_removes_rendered_dots():
    from monoline.raster import render_cells
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        canvas = app.query_one(DrawCanvas)
        canvas.begin(2, 2, ctrl=False)
        canvas.extend(10, 2, ctrl=False)
        canvas.end()
        await pilot.press("e")
        canvas.begin(2, 2, ctrl=False)
        canvas.extend(10, 2, ctrl=False)
        canvas.end()
        cells = render_cells(app.document.strokes,
                             app.document.width, app.document.height)
        assert cells == {}


import pytest
from PIL import Image
from textual import events


@pytest.fixture
def png(tmp_path):
    p = tmp_path / "pic.png"
    Image.new("RGB", (10, 10), (255, 255, 255)).save(p)
    return str(p)


async def test_paste_image_path_imports(png):
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        app.post_message(events.Paste(f'"{png}"'))
        await pilot.pause()
        assert app.document.bitmap is not None


async def test_paste_non_image_ignored():
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        app.post_message(events.Paste("just some text"))
        await pilot.pause()
        assert app.document.bitmap is None


async def test_import_dialog_and_callback(png):
    from monoline.dialogs import TextPrompt
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        await pilot.press("i")
        assert isinstance(app.screen, TextPrompt)
        await pilot.press("escape")
        app._on_import_name(png)
        await pilot.pause()
        assert app.document.bitmap is not None


async def test_clipboard_image_imports(monkeypatch, png):
    from PIL import ImageGrab
    monkeypatch.setattr(ImageGrab, "grabclipboard",
                        lambda: Image.open(png))
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        await pilot.press("v")
        await pilot.pause()
        assert app.document.bitmap is not None


async def test_clipboard_empty_notifies(monkeypatch):
    from PIL import ImageGrab
    monkeypatch.setattr(ImageGrab, "grabclipboard", lambda: None)
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        await pilot.press("v")
        await pilot.pause()
        assert app.document.bitmap is None


async def test_cli_import_path_applies_after_layout(png):
    app = MonolineApp(None, import_path=png)
    async with app.run_test(size=(40, 12)) as pilot:
        await pilot.pause()
        assert app.document.bitmap is not None
        assert app.document.bitmap.width == app.document.width


async def test_import_is_one_undo_step(png):
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        app._import_image(png)
        await pilot.press("u")
        assert app.document.bitmap is None


async def test_import_failure_notifies_no_crash(tmp_path):
    bad = tmp_path / "not_an_image.png"
    bad.write_text("hello")
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        app._import_image(str(bad))
        await pilot.pause()
        assert app.document.bitmap is None
        assert app.is_running
