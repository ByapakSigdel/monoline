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

from monoline.model3d import copy_pose


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


async def test_canvas_paste_image_path_imports(png):
    """Drag-drop pastes go to the focused canvas, not the app."""
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        canvas = app.query_one(DrawCanvas)
        canvas.post_message(events.Paste(png))
        await pilot.pause()
        assert app.document.bitmap is not None


async def test_file_url_paste_imports(png):
    from monoline.media import media_path_from_paste
    from pathlib import Path

    url = Path(png).as_uri()
    assert media_path_from_paste(url) == png


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


@pytest.fixture
def anim_gif(tmp_path):
    p = tmp_path / "anim.gif"
    frames = [
        Image.new("RGB", (10, 10), (255, 0, 0)),
        Image.new("RGB", (10, 10), (0, 255, 0)),
    ]
    frames[0].save(p, save_all=True, append_images=frames[1:],
                   duration=100, loop=0)
    return str(p)


async def test_video_drop_imports(anim_gif):
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        canvas = app.query_one(DrawCanvas)
        canvas.post_message(events.Paste(anim_gif))
        await pilot.pause()
        assert app.document.video_path == anim_gif
        assert app.document.playback_bitmap is not None
        assert app._video_player is not None
        app._stop_video()
        await pilot.pause()


async def test_video_undo_stops_playback(anim_gif):
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        app._import_video(anim_gif)
        await pilot.pause()
        assert app._video_player is not None
        await pilot.press("u")
        assert app.document.video_path is None
        assert app._video_player is None
        await pilot.pause()


async def test_static_gif_imports_as_image(static_gif):
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        app._import_media(static_gif)
        await pilot.pause()
        assert app.document.bitmap is not None
        assert app.document.video_path is None


@pytest.fixture
def triangle_obj(tmp_path):
    p = tmp_path / "tri.obj"
    p.write_text(
        "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n",
        encoding="utf-8",
    )
    return str(p)


async def test_model_drop_imports(triangle_obj):
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        canvas = app.query_one(DrawCanvas)
        canvas.post_message(events.Paste("{" + triangle_obj + "}"))
        await pilot.pause()
        assert app.document.model3d is not None
        assert app.document.model_bitmap is not None


async def test_model_drop_deferred_until_layout(triangle_obj):
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        app.pending_import = None
        app.document.width = 0
        app.document.height = 0
        app._import_media(triangle_obj)
        assert app.pending_import == triangle_obj
        assert app.document.model3d is None
        app.document.width = 80
        app.document.height = 48
        app.apply_pending_import()
        await pilot.pause()
        assert app.document.model3d is not None
        assert app.document.model_bitmap is not None


async def test_shift_drag_updates_model_pose(triangle_obj):
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        app._import_model3d(triangle_obj)
        before = copy_pose(app.document.model3d.pose)
        before_cells = app.document.model_bitmap.cells
        app.document.model3d.pose.yaw += 0.6
        app.document.model3d.pose.pan_x += 8.0
        app.rerender_model()
        await pilot.pause()
        assert app.document.model3d.pose.yaw != before.yaw
        assert app.document.model_bitmap.cells != before_cells


async def test_model_undo_removes_import(triangle_obj):
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        app._import_model3d(triangle_obj)
        await pilot.press("u")
        assert app.document.model3d is None
        assert app.document.model_bitmap is None


async def test_reveal_animation_plays_and_stops():
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        canvas = app.query_one(DrawCanvas)
        canvas.begin(2, 2, ctrl=False)
        canvas.extend(8, 4, ctrl=False)
        canvas.end()
        await pilot.press("a")
        await pilot.pause()
        assert app._reveal_player is not None
        assert app.document.reveal_bitmap is not None
        app._stop_reveal()
        canvas.rebuild()
        await pilot.pause()
        assert app.document.reveal_bitmap is None
        assert app._reveal_player is None


async def test_reveal_empty_canvas_notifies():
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        await pilot.press("a")
        await pilot.pause()
        assert app._reveal_player is None


async def test_reveal_cycle_changes_style():
    from monoline.reveal import STYLES
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        start = app.reveal_style
        await pilot.press("A")
        assert app.reveal_style == (start + 1) % len(STYLES)


@pytest.fixture
def static_gif(tmp_path):
    p = tmp_path / "still.gif"
    Image.new("RGB", (10, 10), (128, 128, 128)).save(p)
    return str(p)
