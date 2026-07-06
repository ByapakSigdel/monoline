"""Save/load and exports. Pure — no TUI imports."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple, Union

from monoline.document import Document, Stroke

FORMAT = "monoline"
VERSION = 1


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
                       background=str(data["background"]))
        doc.strokes = [
            Stroke(points=[(float(x), float(y)) for x, y in s["points"]],
                   color=str(s["color"]), kind=str(s["kind"]),
                   width=float(s["width"]))
            for s in data["strokes"]
        ]
        palette = str(data.get("palette", "tokyonight"))
    except (KeyError, TypeError, ValueError) as exc:
        raise MonolineError(f"{path} is corrupt: {exc}") from exc
    doc.dirty = False
    return doc, palette
