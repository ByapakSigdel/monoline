"""Save/load and exports. Pure — no TUI imports."""
from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Tuple, Union

from monoline.bitmap import Bitmap
from monoline.document import Document, Stroke
from monoline.raster import DOT_BITS, render_cells

FORMAT = "monoline"
VERSIONS = (1, 2)

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _color(value) -> str:
    s = str(value)
    if not _HEX_COLOR.fullmatch(s):
        raise ValueError(f"invalid color {s!r}")
    return s


def _reject_constant(value):
    raise ValueError(f"non-finite number {value!r} not allowed")


def _finite(value, limit: float) -> float:
    f = float(value)
    if not (math.isfinite(f) and abs(f) <= limit):
        raise ValueError(f"non-finite or out-of-range number {value!r}")
    return f


class MonolineError(Exception):
    """A user-facing file error."""


def save(document: Document, palette_name: str, path: Union[str, Path]) -> None:
    data = {
        "format": FORMAT,
        "version": 1,
        "width": document.width,
        "height": document.height,
        "background": document.background,
        "palette": palette_name,
        "strokes": [
            {"kind": s.kind, "color": s.color, "width": s.width,
             "points": [[x, y] for x, y in s.points]}
            for s in document.strokes
        ],
    }
    if document.bitmap is not None:
        data["version"] = 2
        data["bitmap"] = {
            "width": document.bitmap.width,
            "height": document.bitmap.height,
            "cells": [[cx, cy, bits, color]
                      for (cx, cy), (bits, color)
                      in sorted(document.bitmap.cells.items())],
        }
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(tmp, path)


def load(path: Union[str, Path]) -> Tuple[Document, str]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"),
                          parse_constant=_reject_constant)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise MonolineError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise MonolineError(f"{path} is not a monoline file")
    version = data.get("version")
    if version not in VERSIONS:
        raise MonolineError(
            f"{path} uses format version {version}; "
            f"this monoline supports versions {VERSIONS}")
    if version == 1 and "bitmap" in data:
        raise MonolineError(f"{path} is corrupt: version 1 cannot carry a bitmap")
    if version == 2 and "bitmap" not in data:
        raise MonolineError(f"{path} is corrupt: version 2 requires a bitmap")
    try:
        width = int(_finite(data["width"], 100_000))
        height = int(_finite(data["height"], 100_000))
        if not (0 < width <= 100_000):
            raise ValueError(f"invalid document width {width!r}")
        if not (0 < height <= 100_000):
            raise ValueError(f"invalid document height {height!r}")
        doc = Document(width, height, background=_color(data["background"]))
        strokes = []
        for s in data["strokes"]:
            width_ = _finite(s["width"], 1e4)
            if width_ <= 0:
                raise ValueError(f"invalid stroke width {width_!r}")
            strokes.append(Stroke(
                points=[(_finite(x, 1e6), _finite(y, 1e6)) for x, y in s["points"]],
                color=_color(s["color"]), kind=str(s["kind"]), width=width_))
        doc.strokes = strokes
        doc.bitmap = _bitmap_from_json(data["bitmap"]) if version == 2 else None
        palette = str(data.get("palette", "tokyonight"))
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise MonolineError(f"{path} is corrupt: {exc}") from exc
    doc.dirty = False
    return doc, palette


def _bitmap_from_json(b) -> Bitmap:
    w = int(_finite(b["width"], 100_000))
    h = int(_finite(b["height"], 100_000))
    if w <= 0 or h <= 0:
        raise ValueError("bitmap dimensions must be positive")
    cols, rows = w // 2, h // 4
    entries = b["cells"]
    if not isinstance(entries, list) or len(entries) > cols * rows:
        raise ValueError("bitmap cell list invalid")
    cells = {}
    for entry in entries:
        cx, cy, bits, color = entry
        cx, cy, bits = int(cx), int(cy), int(bits)
        if not (0 <= cx < cols and 0 <= cy < rows):
            raise ValueError(f"bitmap cell ({cx},{cy}) out of range")
        if not (1 <= bits <= 255):
            raise ValueError(f"bitmap bits {bits} out of range")
        cells[(cx, cy)] = (bits, _color(color))
    return Bitmap(w, h, cells)


def _hex_to_rgb(color: str):
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def export_ansi(document: Document) -> str:
    cells = render_cells(document.strokes, document.width, document.height, bitmap=document.bitmap)
    cols, rows = document.width // 2, document.height // 4
    lines = []
    for y in range(rows):
        parts = []
        current = None
        used_color = False
        for x in range(cols):
            cell = cells.get((x, y))
            if cell is None:
                parts.append(" ")
                continue
            char, color = cell
            if color != current:
                r, g, b = _hex_to_rgb(color)
                parts.append(f"\x1b[38;2;{r};{g};{b}m")
                current = color
                used_color = True
            parts.append(char)
        line = "".join(parts).rstrip()
        if used_color:
            line += "\x1b[0m"
        lines.append(line)
    return "\n".join(lines) + "\n"


def export_svg(document: Document) -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {document.width} {document.height}">',
        f'<rect width="{document.width}" height="{document.height}" '
        f'fill="{document.background}"/>',
    ]
    if document.bitmap is not None:
        for (cx, cy), (bits, color) in sorted(document.bitmap.cells.items()):
            for (dx, dy), bit in sorted(DOT_BITS.items()):
                if bits & bit:
                    x, y = cx * 2 + dx + 0.5, cy * 4 + dy + 0.5
                    parts.append(f'<circle cx="{x}" cy="{y}" r="0.55" fill="{color}"/>')
    for s in document.strokes:
        color = document.background if s.kind == "erase" else s.color
        width = s.width if s.kind == "erase" else 1.5
        pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in s.points)
        parts.append(
            f'<polyline points="{pts}" fill="none" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round" '
            f'stroke-linejoin="round"/>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"
