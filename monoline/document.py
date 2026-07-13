"""Document model: strokes plus undo/redo. Pure — no TUI imports."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from monoline.bitmap import Bitmap

Point = Tuple[float, float]


@dataclass
class Stroke:
    points: List[Point]
    color: str = "#c0caf5"
    kind: str = "pen"  # "pen" | "erase"
    width: float = 1.0  # diameter in dots


@dataclass
class _AddStrokes:
    strokes: List[Stroke]


@dataclass
class _SetBitmap:
    previous: Optional[Bitmap]
    new: Optional[Bitmap]


@dataclass
class _SetVideo:
    previous: Optional[str]
    new: Optional[str]


@dataclass
class _SetModel3D:
    previous: Optional["Model3DState"]
    new: Optional["Model3DState"]


@dataclass
class _Clear:
    previous: List[Stroke]
    previous_bitmap: Optional[Bitmap] = None
    previous_video: Optional[str] = None
    previous_model: Optional["Model3DState"] = None


class Document:
    def __init__(self, width: int, height: int, background: str = "#1a1b26"):
        self.width = width
        self.height = height
        self.background = background
        self.strokes: List[Stroke] = []
        self.bitmap: Optional[Bitmap] = None
        self.video_path: Optional[str] = None
        self.playback_bitmap: Optional[Bitmap] = None
        self.model3d: Optional["Model3DState"] = None
        self.model_bitmap: Optional[Bitmap] = None
        self._undo: list = []
        self._redo: list = []
        self.dirty = False

    @property
    def display_bitmap(self) -> Optional[Bitmap]:
        """Bitmap shown beneath strokes: video frame, 3D model, or static import."""
        if self.playback_bitmap is not None:
            return self.playback_bitmap
        if self.model_bitmap is not None:
            return self.model_bitmap
        return self.bitmap

    def add_strokes(self, strokes: List[Stroke]) -> None:
        if not strokes:
            return
        self.strokes.extend(strokes)
        self._undo.append(_AddStrokes(list(strokes)))
        self._redo.clear()
        self.dirty = True

    def set_bitmap(self, bitmap: Optional[Bitmap]) -> None:
        if bitmap is None and self.bitmap is None:
            return
        self._undo.append(_SetBitmap(self.bitmap, bitmap))
        self.bitmap = bitmap
        self.video_path = None
        self.playback_bitmap = None
        self.model3d = None
        self.model_bitmap = None
        self._redo.clear()
        self.dirty = True

    def set_video(self, path: Optional[str]) -> None:
        if path is None and self.video_path is None:
            return
        self._undo.append(_SetVideo(self.video_path, path))
        self.video_path = path
        self.bitmap = None
        self.playback_bitmap = None
        self.model3d = None
        self.model_bitmap = None
        self._redo.clear()
        self.dirty = True

    def set_model3d(self, state: Optional["Model3DState"]) -> None:
        if state is None and self.model3d is None:
            return
        self._undo.append(_SetModel3D(self.model3d, state))
        self.model3d = state
        self.bitmap = None
        self.video_path = None
        self.playback_bitmap = None
        self.model_bitmap = None
        self._redo.clear()
        self.dirty = True

    def update_model_pose(self, pose: "ModelPose") -> None:
        """Live pose update while dragging — not an undo step."""
        if self.model3d is not None:
            self.model3d.pose = pose

    def commit_model_pose(self, previous: "ModelPose") -> None:
        """Record a completed Shift+drag manipulation as one undo step."""
        from monoline.model3d import Model3DState, copy_pose
        if self.model3d is None:
            return
        current = copy_pose(self.model3d.pose)
        if (previous.yaw == current.yaw and previous.pitch == current.pitch
                and previous.pan_x == current.pan_x and previous.pan_y == current.pan_y):
            return
        prev_state = Model3DState(
            path=self.model3d.path, pose=previous, color=self.model3d.color)
        new_state = Model3DState(
            path=self.model3d.path, pose=current, color=self.model3d.color)
        self._undo.append(_SetModel3D(prev_state, new_state))
        self._redo.clear()
        self.dirty = True

    def set_model_bitmap(self, bitmap: Optional[Bitmap]) -> None:
        self.model_bitmap = bitmap

    def set_playback_bitmap(self, bitmap: Optional[Bitmap]) -> None:
        """Update the current video frame without creating an undo step."""
        self.playback_bitmap = bitmap

    def clear(self) -> None:
        if (not self.strokes and self.bitmap is None and self.video_path is None
                and self.model3d is None):
            return
        self._undo.append(_Clear(list(self.strokes), self.bitmap,
                                 self.video_path, self.model3d))
        self.strokes.clear()
        self.bitmap = None
        self.video_path = None
        self.playback_bitmap = None
        self.model3d = None
        self.model_bitmap = None
        self._redo.clear()
        self.dirty = True

    def undo(self) -> bool:
        if not self._undo:
            return False
        op = self._undo.pop()
        if isinstance(op, _AddStrokes):
            del self.strokes[-len(op.strokes):]
        elif isinstance(op, _SetBitmap):
            self.bitmap = op.previous
            self.playback_bitmap = None
        elif isinstance(op, _SetVideo):
            self.video_path = op.previous
            self.playback_bitmap = None
        elif isinstance(op, _SetModel3D):
            self.model3d = op.previous
            self.model_bitmap = None
        else:
            self.strokes.extend(op.previous)
            self.bitmap = op.previous_bitmap
            self.video_path = op.previous_video
            self.playback_bitmap = None
            self.model3d = op.previous_model
            self.model_bitmap = None
        self._redo.append(op)
        self.dirty = True
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        op = self._redo.pop()
        if isinstance(op, _AddStrokes):
            self.strokes.extend(op.strokes)
        elif isinstance(op, _SetBitmap):
            self.bitmap = op.new
            self.playback_bitmap = None
        elif isinstance(op, _SetVideo):
            self.video_path = op.new
            self.playback_bitmap = None
        elif isinstance(op, _SetModel3D):
            self.model3d = op.new
            self.model_bitmap = None
        else:
            self.strokes.clear()
            self.bitmap = None
            self.video_path = None
            self.playback_bitmap = None
            self.model3d = None
            self.model_bitmap = None
        self._undo.append(op)
        self.dirty = True
        return True
