"""Reveal animations for canvas content. Pure — no TUI imports."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from monoline.bitmap import Bitmap
from monoline.document import Stroke
from monoline.raster import BRAILLE_BASE, render_cells

CellKey = Tuple[int, int]
CellVal = Tuple[int, str]

STYLES: Tuple[str, ...] = (
    "drop",
    "rain",
    "scan_down",
    "scan_right",
    "scatter",
    "radial",
    "pop",
)


@dataclass(frozen=True)
class _AnimCell:
    col: int
    row: int
    bits: int
    color: str
    start: float
    duration: float
    from_col: int
    from_row: int


def snapshot_bitmap(
    strokes: Iterable[Stroke],
    width: int,
    height: int,
    bitmap: Optional[Bitmap] = None,
) -> Optional[Bitmap]:
    """Merge strokes and a bitmap layer into one snapshot for animation."""
    rendered = render_cells(strokes, width, height, bitmap=bitmap)
    if not rendered:
        return None
    cells: Dict[CellKey, CellVal] = {}
    for (col, row), (char, color) in rendered.items():
        bits = ord(char) - BRAILLE_BASE
        if bits:
            cells[(col, row)] = (bits, color)
    return Bitmap(width, height, cells)


def _ease_out_quad(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) * (1.0 - t)


def _cell_rows(height: int) -> int:
    return max(1, (height + 3) // 4)


def _cell_cols(width: int) -> int:
    return max(1, (width + 1) // 2)


def _hash_offset(col: int, row: int) -> Tuple[int, int]:
    h = (col * 73856093) ^ (row * 19349663)
    return ((h % 17) - 8, ((h // 17) % 19) - 9)


def _pop_order(col: int, row: int, width: int, height: int) -> float:
    h = (col * 92837111) ^ (row * 689287499) ^ (width * 97) ^ (height * 131)
    return float(h & 0xFFFF)


def _schedule_cells(final: Bitmap, style: str) -> List[_AnimCell]:
    rows = _cell_rows(final.height)
    cols = _cell_cols(final.width)
    cx, cy = (cols - 1) / 2.0, (rows - 1) / 2.0
    fall = max(6, rows // 2 + 2)
    items: List[_AnimCell] = []

    for (col, row), (bits, color) in final.cells.items():
        if style == "drop":
            start = row * 1.4 + col * 0.08
            duration = float(fall)
            from_row = row - fall
            items.append(_AnimCell(col, row, bits, color, start, duration,
                                   col, from_row))
        elif style == "rain":
            start = col * 1.6 + row * 0.05
            duration = float(fall)
            from_row = row - fall
            items.append(_AnimCell(col, row, bits, color, start, duration,
                                   col, from_row))
        elif style == "scan_down":
            start = float(row * 2)
            items.append(_AnimCell(col, row, bits, color, start, 1.0,
                                   col, row))
        elif style == "scan_right":
            start = float(col * 2)
            items.append(_AnimCell(col, row, bits, color, start, 1.0,
                                   col, row))
        elif style == "scatter":
            ox, oy = _hash_offset(col, row)
            start = _pop_order(col, row, final.width, final.height) * 0.004
            duration = 14.0
            items.append(_AnimCell(col, row, bits, color, start, duration,
                                   col + ox, row + oy))
        elif style == "radial":
            dist = math.hypot(col - cx, row - cy)
            start = dist * 2.2
            duration = 10.0
            angle = math.atan2(row - cy, col - cx)
            from_col = int(round(col - math.cos(angle) * (dist + 4)))
            from_row = int(round(row - math.sin(angle) * (dist + 4)))
            items.append(_AnimCell(col, row, bits, color, start, duration,
                                   from_col, from_row))
        elif style == "pop":
            start = _pop_order(col, row, final.width, final.height) * 0.003
            items.append(_AnimCell(col, row, bits, color, start, 1.0,
                                   col, row))
        else:
            raise ValueError(f"unknown reveal style: {style}")

    return items


def _normalize_timing(items: List[_AnimCell], frame_budget: float) -> List[_AnimCell]:
    last_end = max(ac.start + ac.duration for ac in items)
    if last_end <= frame_budget:
        return items
    scale = frame_budget / last_end
    return [
        _AnimCell(
            ac.col, ac.row, ac.bits, ac.color,
            ac.start * scale, max(1.0, ac.duration * scale),
            ac.from_col, ac.from_row,
        )
        for ac in items
    ]


def _frame_count(items: List[_AnimCell], min_frames: int, max_frames: int) -> int:
    if not items:
        return 0
    last_end = max(ac.start + ac.duration for ac in items)
    return max(min_frames, min(max_frames, int(math.ceil(last_end)) + 2))


def _frame_bitmap(items: List[_AnimCell], frame: float,
                  width: int, height: int) -> Bitmap:
    cells: Dict[CellKey, CellVal] = {}
    max_col = _cell_cols(width) - 1
    max_row = _cell_rows(height) - 1
    for ac in items:
        if frame < ac.start:
            continue
        t = _ease_out_quad((frame - ac.start) / ac.duration)
        col = int(round(ac.from_col + (ac.col - ac.from_col) * t))
        row = int(round(ac.from_row + (ac.row - ac.from_row) * t))
        if 0 <= col <= max_col and 0 <= row <= max_row:
            cells[(col, row)] = (ac.bits, ac.color)
    return Bitmap(width, height, cells)


def build_frames(
    final: Bitmap,
    style: str,
    *,
    fps: float = 24.0,
    duration: float = 2.0,
    min_frames: int = 16,
    max_frames: int = 120,
) -> List[Bitmap]:
    """Build reveal animation frames from a final bitmap snapshot."""
    if style not in STYLES:
        raise ValueError(f"unknown reveal style: {style}")
    items = _schedule_cells(final, style)
    if not items:
        return []
    frame_budget = max(min_frames, min(max_frames, int(fps * duration)))
    items = _normalize_timing(items, frame_budget)
    count = _frame_count(items, min_frames, max_frames)
    return [_frame_bitmap(items, float(i), final.width, final.height)
            for i in range(count)]


@dataclass
class RevealPlayer:
    """Step through precomputed reveal frames."""

    frames: List[Bitmap]
    fps: float = 24.0
    _index: int = 0

    def next_bitmap(self) -> Optional[Bitmap]:
        if self._index >= len(self.frames):
            return None
        bitmap = self.frames[self._index]
        self._index += 1
        return bitmap

    @property
    def done(self) -> bool:
        return self._index >= len(self.frames)
