"""The monoline Textual application."""
from __future__ import annotations

import os
from typing import List, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from monoline.canvas import DrawCanvas
from monoline.document import Document, Point, Stroke


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

    def compose(self) -> ComposeResult:
        yield DrawCanvas(self.document)
        yield StatusBar()

    def on_mount(self) -> None:
        canvas = self.query_one(DrawCanvas)
        self.document.width = max(canvas.size.width, 1) * 2
        self.document.height = max(canvas.size.height, 1) * 4
        self.document.dirty = False
        self.update_status()

    # -- stroke pipeline (enriched by Tasks 5/6/8/9) --

    def finalize_stroke(self, points: List[Point], ctrl: bool) -> List[Stroke]:
        return [Stroke(points=list(points), color=self.pen_color)]

    def preview_strokes(self, points: List[Point], ctrl: bool) -> List[Stroke]:
        return [Stroke(points=list(points), color=self.pen_color)]

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
