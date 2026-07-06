"""Document model: strokes plus undo/redo. Pure — no TUI imports."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

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
class _Clear:
    previous: List[Stroke]


class Document:
    def __init__(self, width: int, height: int, background: str = "#1a1b26"):
        self.width = width
        self.height = height
        self.background = background
        self.strokes: List[Stroke] = []
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

    def clear(self) -> None:
        if not self.strokes:
            return
        self._undo.append(_Clear(list(self.strokes)))
        self.strokes.clear()
        self._redo.clear()
        self.dirty = True

    def undo(self) -> bool:
        if not self._undo:
            return False
        op = self._undo.pop()
        if isinstance(op, _AddStrokes):
            del self.strokes[-len(op.strokes):]
        else:
            self.strokes.extend(op.previous)
        self._redo.append(op)
        self.dirty = True
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        op = self._redo.pop()
        if isinstance(op, _AddStrokes):
            self.strokes.extend(op.strokes)
        else:
            self.strokes.clear()
        self._undo.append(op)
        self.dirty = True
        return True
