"""The monoline Textual application."""
from __future__ import annotations

import os
from typing import List, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from monoline.canvas import DrawCanvas
from monoline.config import load_config
from monoline.document import Document, Point, Stroke
from monoline.palettes import PALETTES, get_palette
from monoline.shapes import recognize
from monoline.smoothing import smooth


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
    ] + [Binding(str(i + 1), f"pick_color({i})", "Color", show=False) for i in range(9)]

    def __init__(self, path: Optional[str] = None) -> None:
        super().__init__()
        self.path = path
        self.document = Document(0, 0)  # sized on mount
        self.config = load_config()
        self.palette = get_palette(self.config.palette)
        self.color_index = 0
        self.tool = "pen"
        self.smoothing = self.config.smoothing
        self.grid_on = False  # Task 10 toggles this

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
            return [Stroke(points=pts, kind="erase", width=self.ERASER_WIDTH)]
        mode = self.config.shape_correct
        if final and (mode == "always" or (mode == "ctrl" and ctrl)):
            snapped = recognize(pts, grid_spacing=8.0 if self.grid_on else None)
            if snapped is not None:
                pts = snapped
        return [Stroke(points=pts, color=self.pen_color)]

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

    def action_undo(self) -> None:
        if self.document.undo():
            self.query_one(DrawCanvas).rebuild()
            self.update_status()

    def action_redo(self) -> None:
        if self.document.redo():
            self.query_one(DrawCanvas).rebuild()
            self.update_status()

    def action_request_quit(self) -> None:
        self.exit()  # Task 13 adds the unsaved-changes confirmation

    def _apply_palette(self) -> None:
        canvas = self.query_one(DrawCanvas)
        canvas.styles.background = self.palette.background
        if not self.document.strokes:
            self.document.background = self.palette.background
        canvas.rebuild()
        self.update_status()

    def action_pick_color(self, index: int) -> None:
        self.color_index = index
        self.update_status()

    def action_next_palette(self) -> None:
        i = PALETTES.index(self.palette)
        self.palette = PALETTES[(i + 1) % len(PALETTES)]
        self._apply_palette()

    def action_prev_palette(self) -> None:
        i = PALETTES.index(self.palette)
        self.palette = PALETTES[(i - 1) % len(PALETTES)]
        self._apply_palette()

    def update_status(self) -> None:
        swatches = "".join(
            f"[{'underline ' if i == self.color_index else ''}{c}]●[/]"
            for i, c in enumerate(self.palette.colors)
        )
        dirty = "●" if self.document.dirty else " "
        name = os.path.basename(self.path) if self.path else "untitled"
        self.query_one(StatusBar).update(
            f" {self.tool}  {self.palette.name} {swatches}  {name} {dirty}  ? help"
        )


def run(path: Optional[str] = None) -> None:
    MonolineApp(path).run(mouse=True)
