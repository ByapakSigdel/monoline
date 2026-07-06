"""The drawing surface widget."""
from __future__ import annotations

from typing import Dict, List

from rich.segment import Segment
from rich.style import Style
from textual import events
from textual.strip import Strip
from textual.widget import Widget

from monoline.document import Document, Point, Stroke
from monoline.raster import render_cells


def cell_to_dot(col: int, row: int) -> Point:
    return (2 * col + 0.5, 4 * row + 1.5)


class DrawCanvas(Widget):
    DEFAULT_CSS = "DrawCanvas { height: 1fr; }"

    def __init__(self, document: Document) -> None:
        super().__init__()
        self.document = document
        self._raw: List[Point] = []          # in-progress gesture, dot space
        self._ctrl = False
        self._live: List[Stroke] = []        # preview strokes during drag
        self._cells: Dict = {}
        self.can_focus = True

    # -- gesture API (mouse handlers delegate; tests call directly) --

    def begin(self, col: int, row: int, ctrl: bool) -> None:
        self._raw = [cell_to_dot(col, row)]
        self._ctrl = ctrl
        self._update_live()

    def extend(self, col: int, row: int, ctrl: bool) -> None:
        if not self._raw:
            return
        pt = cell_to_dot(col, row)
        if pt != self._raw[-1]:
            self._raw.append(pt)
        self._ctrl = self._ctrl or ctrl
        self._update_live()

    def end(self) -> None:
        if not self._raw:
            return
        strokes = self.app.finalize_stroke(self._raw, self._ctrl)
        self.document.add_strokes(strokes)
        self._raw = []
        self._live = []
        self._ctrl = False
        self.rebuild()

    def _update_live(self) -> None:
        self._live = self.app.preview_strokes(self._raw, self._ctrl)
        self.rebuild()

    # -- rendering --

    def rebuild(self) -> None:
        w, h = self.size.width * 2, self.size.height * 4
        self._cells = render_cells(list(self.document.strokes) + self._live, w, h)
        self.refresh()

    def on_resize(self, event: events.Resize) -> None:
        # Size the document once, when the canvas first learns its real size.
        # Document size is fixed at creation; later terminal resizes do NOT
        # resize the document, and loaded documents (width != 0) keep theirs.
        if self.document.width == 0:
            self.document.width = max(self.size.width, 1) * 2
            self.document.height = max(self.size.height, 1) * 4
        self.rebuild()

    def render_line(self, y: int) -> Strip:
        segments = []
        for x in range(self.size.width):
            cell = self._cells.get((x, y))
            if cell is None:
                segments.append(Segment(" "))
            else:
                char, color = cell
                segments.append(Segment(char, Style(color=color)))
        return Strip(segments, self.size.width)

    # -- mouse --

    def on_mouse_down(self, event: events.MouseDown) -> None:
        if event.button != 1:
            return
        self.capture_mouse()
        self.begin(int(event.offset.x), int(event.offset.y), event.ctrl)

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if self._raw:
            self.extend(int(event.offset.x), int(event.offset.y), event.ctrl)

    def on_mouse_up(self, event: events.MouseUp) -> None:
        self.release_mouse()
        self.end()
