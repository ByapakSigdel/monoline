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
class _Clear:
    previous: List[Stroke]
    previous_bitmap: Optional[Bitmap] = None


class Document:
    def __init__(self, width: int, height: int, background: str = "#1a1b26"):
        self.width = width
        self.height = height
        self.background = background
        self.strokes: List[Stroke] = []
        self.bitmap: Optional[Bitmap] = None
        self._undo: list = []
        self._redo: list = []
        self.dirty = False

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
        self._redo.clear()
        self.dirty = True

    def clear(self) -> None:
        if not self.strokes and self.bitmap is None:
            return
        self._undo.append(_Clear(list(self.strokes), self.bitmap))
        self.strokes.clear()
        self.bitmap = None
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
        else:
            self.strokes.extend(op.previous)
            self.bitmap = op.previous_bitmap
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
        else:
            self.strokes.clear()
            self.bitmap = None
        self._undo.append(op)
        self.dirty = True
        return True
