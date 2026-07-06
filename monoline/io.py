"""Save/load and exports. Pure — no TUI imports."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Tuple, Union

from monoline.document import Document, Stroke
from monoline.raster import render_cells

FORMAT = "monoline"
VERSION = 1

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _color(value) -> str:
    s = str(value)
    if not _HEX_COLOR.match(s):
        raise ValueError(f"invalid color {s!r}")
    return s


class MonolineError(Exception):
    """A user-facing file error."""


def save(document: Document, palette_name: str, path: Union[str, Path]) -> None:
    data = {
        "format": FORMAT,
        "version": VERSION,
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
    Path(path).write_text(json.dumps(data), encoding="utf-8")


def load(path: Union[str, Path]) -> Tuple[Document, str]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MonolineError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise MonolineError(f"{path} is not a monoline file")
    if data.get("version") != VERSION:
        raise MonolineError(
            f"{path} uses format version {data.get('version')}; "
            f"this monoline supports version {VERSION}")
    try:
        doc = Document(int(data["width"]), int(data["height"]),
                       background=_color(data["background"]))
        doc.strokes = [
            Stroke(points=[(float(x), float(y)) for x, y in s["points"]],
                   color=_color(s["color"]), kind=str(s["kind"]),
                   width=float(s["width"]))
            for s in data["strokes"]
        ]
        palette = str(data.get("palette", "tokyonight"))
    except (KeyError, TypeError, ValueError) as exc:
        raise MonolineError(f"{path} is corrupt: {exc}") from exc
    doc.dirty = False
    return doc, palette


def _hex_to_rgb(color: str):
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def export_ansi(document: Document) -> str:
    cells = render_cells(document.strokes, document.width, document.height)
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
