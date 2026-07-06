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
    ]

    def __init__(self, path: Optional[str] = None) -> None:
        super().__init__()
        self.path = path
        self.document = Document(0, 0)  # sized on mount
        self.pen_color = "#c0caf5"
        self.tool = "pen"
        self.config = load_config()
        self.smoothing = self.config.smoothing
        self.grid_on = False  # Task 10 toggles this

    def compose(self) -> ComposeResult:
        yield DrawCanvas(self.document)
        yield StatusBar()

    def on_mount(self) -> None:
        # Document sizing happens in DrawCanvas.on_resize, once the canvas
        # actually has its size (canvas.size is still 0x0 when Mount fires).
        self.update_status()

    # -- stroke pipeline (enriched by Tasks 5/6/8/9) --

    def finalize_stroke(self, points: List[Point], ctrl: bool) -> List[Stroke]:
        pts = smooth(points, self.smoothing)
        mode = self.config.shape_correct
        if mode == "always" or (mode == "ctrl" and ctrl):
            snapped = recognize(pts, grid_spacing=8.0 if self.grid_on else None)
            if snapped is not None:
                pts = snapped
        return [Stroke(points=pts, color=self.pen_color)]

    def preview_strokes(self, points: List[Point], ctrl: bool) -> List[Stroke]:
        pts = smooth(points, self.smoothing)
        return [Stroke(points=pts, color=self.pen_color)]

    # -- actions --

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

    def update_status(self) -> None:
        dirty = "●" if self.document.dirty else " "
        name = os.path.basename(self.path) if self.path else "untitled"
        self.query_one(StatusBar).update(
            f" {self.tool}  {name} {dirty}  ? help"
        )


def run(path: Optional[str] = None) -> None:
    MonolineApp(path).run(mouse=True)
