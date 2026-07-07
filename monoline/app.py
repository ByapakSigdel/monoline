"""The monoline Textual application."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Union

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from monoline.canvas import DrawCanvas
from monoline.config import load_config
from monoline.dialogs import Confirm, TextPrompt
from monoline.document import Document, Point, Stroke
from monoline.help import HelpScreen
from monoline.io import MonolineError, export_ansi, export_svg, load, save
from monoline.palettes import PALETTES, get_palette
from monoline.shapes import recognize
from monoline.smoothing import smooth
from monoline.symmetry import MODES, siblings

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


class StatusBar(Static):
    DEFAULT_CSS = "StatusBar { height: 1; dock: bottom; background: $panel; }"


class MonolineApp(App):
    BINDINGS = [
        Binding("u", "undo", "Undo", show=False),
        Binding("ctrl+z", "undo", "Undo", show=False, priority=True),
        Binding("r", "redo", "Redo", show=False),
        Binding("ctrl+y", "redo", "Redo", show=False, priority=True),
        Binding("q", "request_quit", "Quit", show=False),
        Binding("p", "next_palette", "Palette", show=False),
        Binding("P", "prev_palette", "Palette back", show=False),
        Binding("d", "tool_pen", "Pen", show=False),
        Binding("e", "tool_erase", "Eraser", show=False),
        Binding("s", "cycle_symmetry", "Symmetry", show=False),
        Binding("g", "toggle_grid", "Grid", show=False),
        Binding("ctrl+s", "save", "Save", show=False, priority=True),
        Binding("x", "export", "Export", show=False),
        Binding("question_mark", "help", "Help", show=False),
        Binding("c", "clear", "Clear", show=False),
        Binding("i", "import_image", "Import", show=False),
        Binding("v", "paste_image", "Paste image", show=False),
    ] + [Binding(str(i + 1), f"pick_color({i})", "Color", show=False) for i in range(9)]

    def __init__(self, path: Optional[str] = None,
                 import_path: Optional[str] = None) -> None:
        super().__init__()
        self.path = path
        self.pending_import = import_path
        self.document = Document(0, 0)  # sized on mount, unless loaded below
        self.config = load_config()
        if path is not None and os.path.exists(path):
            self.document, palette_name = load(path)
            self.config.palette = palette_name
        self.palette = get_palette(self.config.palette)
        self.color_index = 0
        self.tool = "pen"
        self.smoothing = self.config.smoothing
        self.grid_on = False  # Task 10 toggles this
        self.symmetry = "off"

    @property
    def pen_color(self) -> str:
        return self.palette.colors[self.color_index]

    def compose(self) -> ComposeResult:
        yield DrawCanvas(self.document)
        yield StatusBar()

    def on_mount(self) -> None:
        # Document sizing happens in DrawCanvas.on_resize, once the canvas
        # actually has its size (canvas.size is still 0x0 when Mount fires).
        self._apply_palette()

    # -- stroke pipeline (enriched by Tasks 5/6/8/9) --

    ERASER_WIDTH = 6.0

    def _gesture_strokes(self, points: List[Point], ctrl: bool,
                         final: bool) -> List[Stroke]:
        pts = smooth(points, self.smoothing)
        if self.tool == "erase":
            base = Stroke(points=pts, kind="erase", width=self.ERASER_WIDTH)
        else:
            mode = self.config.shape_correct
            if final and (mode == "always" or (mode == "ctrl" and ctrl)):
                snapped = recognize(pts, grid_spacing=8.0 if self.grid_on else None)
                if snapped is not None:
                    pts = snapped
            base = Stroke(points=pts, color=self.pen_color)

        result = [base]
        for pts2 in siblings(base.points, self.symmetry,
                             self.document.width, self.document.height):
            result.append(Stroke(points=pts2, color=base.color,
                                 kind=base.kind, width=base.width))
        return result

    def finalize_stroke(self, points: List[Point], ctrl: bool) -> List[Stroke]:
        return self._gesture_strokes(points, ctrl, final=True)

    def preview_strokes(self, points: List[Point], ctrl: bool) -> List[Stroke]:
        return self._gesture_strokes(points, ctrl, final=False)

    # -- actions --

    def action_tool_pen(self) -> None:
        self.tool = "pen"
        self.update_status()

    def action_tool_erase(self) -> None:
        self.tool = "erase"
        self.update_status()

    def action_cycle_symmetry(self) -> None:
        self.symmetry = MODES[(MODES.index(self.symmetry) + 1) % len(MODES)]
        self.update_status()

    def action_toggle_grid(self) -> None:
        self.grid_on = not self.grid_on
        canvas = self.query_one(DrawCanvas)
        canvas.grid_on = self.grid_on
        canvas.grid_color = self.palette.grid
        canvas.refresh()
        self.update_status()

    def action_undo(self) -> None:
        if self.document.undo():
            self.query_one(DrawCanvas).rebuild()
            self.update_status()

    def action_redo(self) -> None:
        if self.document.redo():
            self.query_one(DrawCanvas).rebuild()
            self.update_status()

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_clear(self) -> None:
        if not self.document.strokes:
            return
        self.push_screen(Confirm("Clear the canvas?"), self._on_clear)

    def _on_clear(self, yes) -> None:
        if yes:
            self.document.clear()
            self.query_one(DrawCanvas).rebuild()
            self.update_status()

    def action_request_quit(self) -> None:
        if not self.document.dirty:
            self.exit()
            return
        self.push_screen(Confirm("Unsaved changes — quit anyway?"),
                         self._on_quit)

    def _on_quit(self, yes) -> None:
        if yes:
            self.exit()

    def action_save(self) -> None:
        if self.path:
            self._do_save(self.path)
        else:
            self.push_screen(TextPrompt("Save as:", "drawing.mono.json"),
                             self._on_save_name)

    def _on_save_name(self, name) -> None:
        if name:
            self._do_save(name)

    def _do_save(self, path: str) -> None:
        try:
            save(self.document, self.palette.name, path)
        except OSError as exc:
            self.notify(f"save failed: {exc}", severity="error")
            return
        self.path = path
        self.document.dirty = False
        self.update_status()
        self.notify(f"saved {os.path.basename(path)}")

    def action_export(self) -> None:
        self.push_screen(
            TextPrompt("Export to (.txt = ANSI, .svg = SVG):", "drawing.txt"),
            self._on_export_name)

    def _on_export_name(self, name) -> None:
        if not name:
            return
        try:
            if name.lower().endswith(".svg"):
                content = export_svg(self.document)
            else:
                content = export_ansi(self.document)
            with open(name, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as exc:
            self.notify(f"export failed: {exc}", severity="error")
            return
        self.notify(f"exported {os.path.basename(name)}")

    def apply_pending_import(self) -> None:
        if self.pending_import is None:
            return
        path, self.pending_import = self.pending_import, None
        self._import_image(path)

    def _import_image(self, source: Union[str, "Image.Image"]) -> None:
        from PIL import Image, UnidentifiedImageError
        from monoline.imageconv import convert
        name = "clipboard image"
        try:
            if isinstance(source, Image.Image):
                img = source
            else:
                name = os.path.basename(str(source))
                img = Image.open(source)
            bitmap = convert(img, self.document.width,
                             self.document.height, self.document.background)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            self.notify(f"import failed: {exc}", severity="error")
            return
        self.document.set_bitmap(bitmap)
        self.query_one(DrawCanvas).rebuild()
        self.update_status()
        self.notify(f"imported {name}")

    def on_paste(self, event: events.Paste) -> None:
        text = event.text.strip().strip('"').strip("'")
        p = Path(text)
        if p.suffix.lower() in IMAGE_SUFFIXES and p.is_file():
            event.stop()
            self._import_image(str(p))

    def action_import_image(self) -> None:
        self.push_screen(TextPrompt("Import image:", "photo.png"),
                         self._on_import_name)

    def _on_import_name(self, name) -> None:
        if name:
            self._import_image(name)

    def action_paste_image(self) -> None:
        from PIL import Image as PILImage
        try:
            from PIL import ImageGrab
            data = ImageGrab.grabclipboard()
        except Exception as exc:  # NotImplementedError, missing xclip/wl-paste
            self.notify(f"clipboard unavailable: {exc}", severity="error")
            return
        if isinstance(data, PILImage.Image):
            self._import_image(data)
            return
        if isinstance(data, list):
            for item in data:
                if Path(str(item)).suffix.lower() in IMAGE_SUFFIXES:
                    self._import_image(str(item))
                    return
        self.notify("no image in the clipboard")

    def _apply_palette(self, switch: bool = False) -> None:
        canvas = self.query_one(DrawCanvas)
        if switch or not self.document.strokes:
            self.document.background = self.palette.background
        canvas.styles.background = self.document.background
        canvas.grid_color = self.palette.grid
        canvas.rebuild()
        self.update_status()

    def action_pick_color(self, index: int) -> None:
        self.color_index = index
        self.update_status()

    def action_next_palette(self) -> None:
        i = PALETTES.index(self.palette)
        self.palette = PALETTES[(i + 1) % len(PALETTES)]
        self._apply_palette(switch=True)

    def action_prev_palette(self) -> None:
        i = PALETTES.index(self.palette)
        self.palette = PALETTES[(i - 1) % len(PALETTES)]
        self._apply_palette(switch=True)

    def update_status(self) -> None:
        swatches = "".join(
            f"[{'underline ' if i == self.color_index else ''}{c}]●[/]"
            for i, c in enumerate(self.palette.colors)
        )
        dirty = "●" if self.document.dirty else " "
        name = os.path.basename(self.path) if self.path else "untitled"
        grid = "  grid" if self.grid_on else ""
        self.query_one(StatusBar).update(
            f" {self.tool}  {self.palette.name} {swatches}  sym:{self.symmetry}"
            f"{grid}  {name} {dirty}  ? help"
        )


def run(path: Optional[str] = None) -> None:
    if path is not None and Path(path).suffix.lower() in IMAGE_SUFFIXES:
        MonolineApp(None, import_path=path).run(mouse=True)
    else:
        MonolineApp(path).run(mouse=True)
