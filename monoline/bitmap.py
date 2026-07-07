"""Bitmap layer: converted-image dot data. Pure — no TUI imports."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass
class Bitmap:
    """A braille dot grid with one color per cell.

    cells maps (col, row) -> (bits, color): bits is the braille bit
    pattern 1-255 (an all-off cell is absent, never bits=0), color is
    "#rrggbb". Treated as immutable — mutations replace the object.
    """

    width: int   # dots
    height: int  # dots
    cells: Dict[Tuple[int, int], Tuple[int, str]] = field(default_factory=dict)
