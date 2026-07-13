"""The drawing surface widget."""
from __future__ import annotations

from copy import deepcopy
from typing import Dict, List, Optional, Tuple

from rich.segment import Segment
from rich.style import Style
from textual import events
from textual.strip import Strip
from textual.widget import Widget

from monoline.document import Document, Point, Stroke
from monoline.model3d import ModelPose, copy_pose
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
        self.grid_on = False
        self.grid_color = "#292e42"
        self._model_drag: Optional[str] = None
        self._model_last: Optional[Tuple[int, int]] = None
        self._model_pose_start: Optional[ModelPose] = None

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
        if self.document.reveal_bitmap is not None:
            self._cells = render_cells([], w, h,
                                       bitmap=self.document.reveal_bitmap)
        else:
            self._cells = render_cells(list(self.document.strokes) + self._live,
                                       w, h, bitmap=self.document.display_bitmap)
        self.refresh()

    def on_resize(self, event: events.Resize) -> None:
        # Size the document once, when the canvas first learns its real size.
        # Document size is fixed at creation; later terminal resizes do NOT
        # resize the document, and loaded documents (width != 0) keep theirs.
        if self.document.width == 0:
            self.document.width = max(self.size.width, 1) * 2
            self.document.height = max(self.size.height, 1) * 4
        self.rebuild()
        self.app.apply_pending_import()

    def render_line(self, y: int) -> Strip:
        segments = []
        for x in range(self.size.width):
            cell = self._cells.get((x, y))
            if cell is None:
                if self.grid_on and x % 4 == 0 and y % 2 == 0:
                    segments.append(Segment("⠂", Style(color=self.grid_color)))
                else:
                    segments.append(Segment(" ", Style()))
            else:
                char, color = cell
                segments.append(Segment(char, Style(color=color)))
        return Strip(segments, self.size.width)

    # -- mouse --

    def on_mouse_down(self, event: events.MouseDown) -> None:
        if event.shift and self.document.model3d is not None and event.button == 1:
            self.capture_mouse()
            self._model_drag = "manipulate"
            self._model_last = (int(event.offset.x), int(event.offset.y))
            self._model_pose_start = copy_pose(self.document.model3d.pose)
            return
        if event.button != 1:
            return
        self.capture_mouse()
        self.begin(int(event.offset.x), int(event.offset.y), event.ctrl)

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if self._model_drag and self._model_last and self.document.model3d:
            dx = int(event.offset.x) - self._model_last[0]
            dy = int(event.offset.y) - self._model_last[1]
            self._model_last = (int(event.offset.x), int(event.offset.y))
            pose = self.document.model3d.pose
            pose.yaw += dx * 0.04
            pose.pitch += dy * 0.04
            pose.pan_x += dx * 1.5
            pose.pan_y += dy * 1.5
            self.document.update_model_pose(pose)
            self.app.rerender_model()
            return
        if self._raw:
            self.extend(int(event.offset.x), int(event.offset.y), event.ctrl)

    def on_mouse_up(self, event: events.MouseUp) -> None:
        if self._model_drag:
            self.release_mouse()
            if self._model_pose_start is not None and self.document.model3d is not None:
                self.app.commit_model_pose(self._model_pose_start)
            self._model_drag = None
            self._model_last = None
            self._model_pose_start = None
            return
        self.release_mouse()
        self.end()

    def on_paste(self, event: events.Paste) -> None:
        if self.app.try_import_pasted_path(event.text):
            event.stop()
