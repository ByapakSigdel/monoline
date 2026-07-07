"""Generate README SVG screenshots by driving the real app headlessly.

Run: .venv\\Scripts\\python.exe scripts\\make_screenshots.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from demo_scene import make_demo_image, petal_points, wobbly_circle_points

from monoline.app import MonolineApp
from monoline.canvas import DrawCanvas
from monoline.document import Stroke
from monoline.imageconv import convert
from monoline.symmetry import siblings

ASSETS = Path(__file__).resolve().parent.parent / "docs" / "assets"
SIZE = (100, 30)


def add(app, points, color, symmetry="off"):
    doc = app.document
    strokes = [Stroke(points=list(points), color=color)]
    for pts in siblings(points, symmetry, doc.width, doc.height):
        strokes.append(Stroke(points=pts, color=color))
    doc.add_strokes(strokes)


async def shot_drawing() -> None:
    app = MonolineApp()
    async with app.run_test(size=SIZE) as pilot:
        app.grid_on = True
        canvas = app.query_one(DrawCanvas)
        canvas.grid_on = True
        canvas.grid_color = app.palette.grid
        w, h = app.document.width, app.document.height
        from monoline.shapes import recognize
        # The petal must be centered on (w/2, h/2): siblings() always
        # mirrors "radial4" around the canvas center, so the 4 arms only
        # share an origin (and read as one mandala) when the petal's own
        # center matches that pivot. An off-center petal produces 4
        # disconnected scattered arcs instead - confirmed by rendering a
        # PNG preview of the original w*0.28/h*0.55 placement.
        snapped = recognize(wobbly_circle_points(w * 0.80, h * 0.22, h * 0.14))
        add(app, snapped, app.palette.colors[1])
        add(app, petal_points(w * 0.5, h * 0.5, h * 0.34),
            app.palette.colors[4], symmetry="radial4")
        canvas.rebuild()
        app.update_status()
        await pilot.pause()
        app.save_screenshot("screenshot-drawing.svg", str(ASSETS))


async def shot_import() -> None:
    app = MonolineApp()
    async with app.run_test(size=SIZE) as pilot:
        doc = app.document
        doc.set_bitmap(convert(make_demo_image(), doc.width, doc.height,
                               doc.background))
        add(app, wobbly_circle_points(doc.width * 0.5, doc.height * 0.75,
                                      doc.height * 0.10),
            app.palette.colors[2])
        app.query_one(DrawCanvas).rebuild()
        app.update_status()
        await pilot.pause()
        app.save_screenshot("screenshot-import.svg", str(ASSETS))


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    asyncio.run(shot_drawing())
    asyncio.run(shot_import())
    print("wrote", ASSETS / "screenshot-drawing.svg")
    print("wrote", ASSETS / "screenshot-import.svg")


if __name__ == "__main__":
    main()
