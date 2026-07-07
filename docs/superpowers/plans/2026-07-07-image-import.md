# monoline v0.2.0 — Image Import + Repo Media Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drop/import a normal image into monoline and get color-accurate braille art as a drawable-over background layer; ship real README screenshots and GIFs; release v0.2.0.

**Architecture:** A `Bitmap` value type (per-cell braille bits + color) becomes an optional document layer. The raster pipeline seeds its dot grid from the bitmap before applying strokes, so pen-over-image and visual (non-destructive) erasing fall out for free. A pure Pillow converter (EXIF → composite → LANCZOS fit → Floyd-Steinberg → per-cell average color) feeds four import doors. `.mono.json` bumps to version 2 only when a bitmap exists. Repo scripts generate SVG screenshots (Textual Pilot) and deterministic GIFs (Pillow frame renderer).

**Tech Stack:** Python ≥3.9, Textual ≥1.0, **Pillow ≥10 (new hard dependency)**, platformdirs, pytest + pytest-asyncio.

## Global Constraints

- Spec (authoritative): `docs/superpowers/specs/2026-07-06-image-import-design.md`. Baseline: commit 58e3cbf, 69 passing tests.
- Repo `C:\Users\user\Documents\monoline`, branch `main`. Every commit authored `ByapakSigdel <sigdelmb123@gmail.com>` (already in local git config), **never a Co-Authored-By trailer or AI attribution**. Push after every task. Conventional commit messages.
- Run tests: `.venv\Scripts\python.exe -m pytest -q` (Windows venv).
- Runtime deps after this release: `textual>=1.0`, `platformdirs>=3`, `tomli>=2 ; python_version < '3.11'`, `pillow>=10`. Nothing else.
- Core modules (`bitmap`, `document`, `raster`, `imageconv`, `io`) stay TUI-free (no Textual imports). Python 3.9 compatible (`from __future__ import annotations`, `typing.Dict/List/Tuple/Optional`).
- All file-loading validation failures raise `MonolineError` with a clear message — same hardening standard as v0.1.0 (finite numbers, bounded ints, `_color` hex check via `fullmatch`).
- tests/conftest.py already isolates config to tmp paths — never remove that fixture.

---

### Task 1: Bitmap value type + document layer with undo/redo

**Files:**
- Create: `monoline/bitmap.py`
- Modify: `monoline/document.py`
- Test: `tests/test_document.py` (append), `tests/test_bitmap.py` (new)

**Interfaces:**
- Consumes: existing `Document` (`strokes`, `_undo`/`_redo`, `dirty`, `_AddStrokes`, `_Clear`).
- Produces:
  - `monoline.bitmap.Bitmap(width: int, height: int, cells: Dict[Tuple[int,int], Tuple[int,str]] = {})` — dataclass; dots; `cells` maps `(col,row) -> (bits 1-255, "#rrggbb")`; empty cells absent; treated as immutable (replace whole object).
  - `Document.bitmap: Optional[Bitmap]` (default None).
  - `Document.set_bitmap(bitmap: Optional[Bitmap]) -> None` — one undo op (`_SetBitmap(previous, new)`); no-op when both current and new are None; clears redo; sets dirty.
  - `Document.clear()` now records and removes strokes AND bitmap as one op (`_Clear(previous, previous_bitmap)`); no-op only when `not strokes and bitmap is None`.

- [ ] **Step 1: Write the failing tests**

`tests/test_bitmap.py`:
```python
from monoline.bitmap import Bitmap


def test_bitmap_defaults():
    b = Bitmap(80, 40)
    assert (b.width, b.height) == (80, 40)
    assert b.cells == {}


def test_bitmap_cells():
    b = Bitmap(80, 40, {(3, 2): (255, "#ff0000")})
    assert b.cells[(3, 2)] == (255, "#ff0000")
```

Append to `tests/test_document.py`:
```python
from monoline.bitmap import Bitmap


BM1 = Bitmap(80, 40, {(0, 0): (255, "#ffffff")})
BM2 = Bitmap(80, 40, {(1, 1): (1, "#ff0000")})


def test_set_bitmap_undo_redo():
    doc = Document(80, 40)
    doc.set_bitmap(BM1)
    assert doc.bitmap is BM1 and doc.dirty is True
    doc.set_bitmap(BM2)  # replace
    assert doc.bitmap is BM2
    doc.undo()
    assert doc.bitmap is BM1
    doc.undo()
    assert doc.bitmap is None
    doc.redo()
    assert doc.bitmap is BM1
    doc.redo()
    assert doc.bitmap is BM2


def test_set_bitmap_none_when_none_is_noop():
    doc = Document(80, 40)
    doc.set_bitmap(None)
    assert doc.undo() is False


def test_set_bitmap_remove_is_undoable():
    doc = Document(80, 40)
    doc.set_bitmap(BM1)
    doc.set_bitmap(None)
    assert doc.bitmap is None
    doc.undo()
    assert doc.bitmap is BM1


def test_clear_takes_bitmap_and_strokes_one_op():
    doc = Document(80, 40)
    doc.add_strokes([stroke((0, 0), (1, 1))])
    doc.set_bitmap(BM1)
    doc.clear()
    assert doc.strokes == [] and doc.bitmap is None
    doc.undo()
    assert len(doc.strokes) == 1 and doc.bitmap is BM1


def test_clear_bitmap_only_not_noop():
    doc = Document(80, 40)
    doc.set_bitmap(BM1)
    doc.clear()
    assert doc.bitmap is None
    doc.undo()
    assert doc.bitmap is BM1


def test_set_bitmap_clears_redo():
    doc = Document(80, 40)
    doc.add_strokes([stroke((0, 0))])
    doc.undo()
    doc.set_bitmap(BM1)
    assert doc.redo() is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bitmap.py tests/test_document.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'monoline.bitmap'`

- [ ] **Step 3: Implement**

`monoline/bitmap.py`:
```python
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
```

`monoline/document.py` — add imports and ops:
```python
from typing import List, Optional, Tuple

from monoline.bitmap import Bitmap
```
```python
@dataclass
class _SetBitmap:
    previous: Optional[Bitmap]
    new: Optional[Bitmap]
```
Change `_Clear` to:
```python
@dataclass
class _Clear:
    previous: List[Stroke]
    previous_bitmap: Optional[Bitmap] = None
```
In `Document.__init__`, after `self.strokes`: `self.bitmap: Optional[Bitmap] = None`.

New method (after `add_strokes`):
```python
    def set_bitmap(self, bitmap: Optional[Bitmap]) -> None:
        if bitmap is None and self.bitmap is None:
            return
        self._undo.append(_SetBitmap(self.bitmap, bitmap))
        self.bitmap = bitmap
        self._redo.clear()
        self.dirty = True
```
Replace `clear`:
```python
    def clear(self) -> None:
        if not self.strokes and self.bitmap is None:
            return
        self._undo.append(_Clear(list(self.strokes), self.bitmap))
        self.strokes.clear()
        self.bitmap = None
        self._redo.clear()
        self.dirty = True
```
Replace `undo`/`redo` op-dispatch:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_bitmap.py tests/test_document.py -q`
Expected: all pass. Then full suite: `.venv\Scripts\python.exe -m pytest -q` — 69 + 8 new pass.

- [ ] **Step 5: Commit and push**

```bash
git add monoline/bitmap.py monoline/document.py tests/test_bitmap.py tests/test_document.py
git commit -m "feat: bitmap layer on the document model with undoable set/clear"
git push
```

---

### Task 2: Raster compositing — bitmap beneath strokes

**Files:**
- Modify: `monoline/raster.py` (render_cells signature), `monoline/canvas.py` (rebuild call site), `monoline/io.py` (export_ansi call site)
- Test: `tests/test_raster.py` (append)

**Interfaces:**
- Consumes: `Bitmap` from Task 1; existing `render_cells`, `DOT_BITS`.
- Produces: `render_cells(strokes, width, height, bitmap: Optional[Bitmap] = None)` — seeds the dot grid from `bitmap` at sequence 0 (bitmap cells outside width×height are clipped), then applies strokes exactly as before. Existing callers without a bitmap are unaffected.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_raster.py`:
```python
from monoline.bitmap import Bitmap


def test_bitmap_seeds_cells():
    bm = Bitmap(8, 8, {(0, 0): (0x01, "#112233"), (1, 1): (0xFF, "#445566")})
    cells = render_cells([], 8, 8, bitmap=bm)
    assert cells[(0, 0)] == ("⠁", "#112233")
    assert cells[(1, 1)] == ("⣿", "#445566")


def test_pen_stroke_wins_over_bitmap():
    bm = Bitmap(8, 8, {(0, 0): (0x01, "#111111")})
    pen = Stroke(points=[(1.0, 0.0)], color="#ff0000")  # same cell, dot 4
    cells = render_cells([pen], 8, 8, bitmap=bm)
    char, color = cells[(0, 0)]
    assert ord(char) - 0x2800 == 0x01 | 0x08  # bits merge
    assert color == "#ff0000"  # stroke color wins


def test_erase_clears_bitmap_dots_nondestructively():
    bm = Bitmap(8, 8, {(0, 0): (0xFF, "#ffffff")})
    rub = Stroke(points=[(0.5, 1.5)], kind="erase", width=8.0)
    cells = render_cells([rub], 8, 8, bitmap=bm)
    assert (0, 0) not in cells
    assert bm.cells[(0, 0)] == (0xFF, "#ffffff")  # source data untouched


def test_bitmap_cells_outside_canvas_clipped():
    bm = Bitmap(100, 100, {(30, 20): (0xFF, "#ffffff")})  # beyond an 8x8 canvas
    assert render_cells([], 8, 8, bitmap=bm) == {}


def test_no_bitmap_behaves_as_before():
    s = Stroke(points=[(0.0, 0.0)], color="#ff0000")
    assert render_cells([s], 8, 8) == {(0, 0): ("⠁", "#ff0000")}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_raster.py -q`
Expected: FAIL — `TypeError: render_cells() got an unexpected keyword argument 'bitmap'`

- [ ] **Step 3: Implement**

In `monoline/raster.py`, add imports `from typing import ... Optional` and `from monoline.bitmap import Bitmap`, and change `render_cells`:
```python
def render_cells(strokes: Iterable[Stroke], width: int, height: int,
                 bitmap: Optional[Bitmap] = None
                 ) -> Dict[Tuple[int, int], Tuple[str, str]]:
    dots: Dict[Tuple[int, int], Tuple[int, str]] = {}  # (x,y) -> (seq, color)
    if bitmap is not None:
        for (cx, cy), (bits, color) in bitmap.cells.items():
            for (dx, dy), bit in DOT_BITS.items():
                if bits & bit:
                    px, py = cx * 2 + dx, cy * 4 + dy
                    if 0 <= px < width and 0 <= py < height:
                        dots[(px, py)] = (0, color)
    seq = 0
    ...  # rest of the existing function body unchanged
```
(Only the seeding block and the signature change; the stroke loop and the cell-building tail stay identical.)

Call sites:
- `monoline/canvas.py` `rebuild()`: `self._cells = render_cells(list(self.document.strokes) + self._live, w, h, bitmap=self.document.bitmap)`
- `monoline/io.py` `export_ansi()`: `cells = render_cells(document.strokes, document.width, document.height, bitmap=document.bitmap)`

- [ ] **Step 4: Run all tests**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: all pass (77 + 5).

- [ ] **Step 5: Commit and push**

```bash
git add monoline/raster.py monoline/canvas.py monoline/io.py tests/test_raster.py
git commit -m "feat: composite bitmap layer beneath strokes in the raster pipeline"
git push
```

---

### Task 3: SVG export renders bitmap dots

**Files:**
- Modify: `monoline/io.py` (export_svg)
- Test: `tests/test_io.py` (append)

**Interfaces:**
- Consumes: `Document.bitmap`, `DOT_BITS` from raster.
- Produces: `export_svg` emits, after the background `<rect>` and before stroke polylines, one `<circle cx="X" cy="Y" r="0.55" fill="#rrggbb"/>` per lit bitmap dot (center = dot coord + 0.5), in `sorted(cells)` order for deterministic output.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_io.py`:
```python
from monoline.bitmap import Bitmap


def test_export_svg_bitmap_dots_beneath_strokes():
    doc = Document(16, 8, background="#000000")
    doc.set_bitmap(Bitmap(16, 8, {(0, 0): (0x01 | 0x08, "#00ff00")}))
    doc.add_strokes([Stroke(points=[(0.0, 0.0), (4.0, 4.0)], color="#ffffff")])
    svg = export_svg(doc)
    root = ET.fromstring(svg)
    ns = "{http://www.w3.org/2000/svg}"
    children = list(root)
    kinds = [c.tag.replace(ns, "") for c in children]
    assert kinds == ["rect", "circle", "circle", "polyline"]  # dots before strokes
    c0 = children[1]
    assert c0.get("fill") == "#00ff00"
    assert c0.get("r") == "0.55"
    assert (c0.get("cx"), c0.get("cy")) == ("0.5", "0.5")   # dot (0,0)
    c1 = children[2]
    assert (c1.get("cx"), c1.get("cy")) == ("1.5", "0.5")   # dot 4 = (1,0)


def test_export_svg_no_bitmap_unchanged():
    doc = Document(16, 8)
    doc.add_strokes([Stroke(points=[(0.0, 0.0), (4.0, 4.0)])])
    root = ET.fromstring(export_svg(doc))
    ns = "{http://www.w3.org/2000/svg}"
    assert root.find(f"{ns}circle") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_io.py -q`
Expected: the two new tests FAIL (no circles emitted).

- [ ] **Step 3: Implement**

In `monoline/io.py`, extend the raster import to `from monoline.raster import DOT_BITS, render_cells`. In `export_svg`, insert between the background rect append and the stroke loop:
```python
    if document.bitmap is not None:
        for (cx, cy), (bits, color) in sorted(document.bitmap.cells.items()):
            for (dx, dy), bit in sorted(DOT_BITS.items()):
                if bits & bit:
                    x, y = cx * 2 + dx + 0.5, cy * 4 + dy + 0.5
                    parts.append(f'<circle cx="{x}" cy="{y}" r="0.55" fill="{color}"/>')
```

- [ ] **Step 4: Run all tests**

Run: `.venv\Scripts\python.exe -m pytest -q` — all pass.

- [ ] **Step 5: Commit and push**

```bash
git add monoline/io.py tests/test_io.py
git commit -m "feat: bitmap dots in SVG export"
git push
```

---

### Task 4: Image converter (Pillow + Floyd-Steinberg)

**Files:**
- Create: `monoline/imageconv.py`
- Modify: `pyproject.toml` (add `"pillow>=10",` to `[project] dependencies`)
- Test: `tests/test_imageconv.py`

**Interfaces:**
- Consumes: `Bitmap`, `DOT_BITS`.
- Produces: `convert(img: PIL.Image.Image, dot_w: int, dot_h: int, background: str) -> Bitmap` — EXIF-orient, composite over `background`, LANCZOS fit-inside centered, Floyd-Steinberg on luminance (lit = dithered white), cell color = average RGB of lit pixels. Deterministic. Raises nothing itself beyond what Pillow raises on broken images (callers catch).

- [ ] **Step 1: Install Pillow and add the dependency**

Add `"pillow>=10",` to the dependencies array in `pyproject.toml` (after `platformdirs>=3`), then run:
`.venv\Scripts\python.exe -m pip install -e .[dev]`
Expected: Pillow installs from a prebuilt wheel.

- [ ] **Step 2: Write the failing tests**

`tests/test_imageconv.py`:
```python
from PIL import Image

from monoline.imageconv import convert


def solid(color, size=(20, 40)):
    return Image.new("RGB", size, color)


def lit_dots(bm):
    from monoline.raster import DOT_BITS
    out = set()
    for (cx, cy), (bits, _) in bm.cells.items():
        for (dx, dy), bit in DOT_BITS.items():
            if bits & bit:
                out.add((cx * 2 + dx, cy * 4 + dy))
    return out


def test_white_image_all_lit_white_cells():
    bm = convert(solid((255, 255, 255)), 20, 40, "#1a1b26")
    assert len(lit_dots(bm)) == 20 * 40
    assert all(color == "#ffffff" for _, color in bm.cells.values())
    assert (bm.width, bm.height) == (20, 40)


def test_black_image_empty():
    bm = convert(solid((0, 0, 0)), 20, 40, "#1a1b26")
    assert bm.cells == {}


def test_half_split_lit_left_only():
    img = Image.new("RGB", (40, 40), (0, 0, 0))
    img.paste((255, 255, 255), (0, 0, 20, 40))
    bm = convert(img, 40, 40, "#1a1b26")
    dots = lit_dots(bm)
    assert dots and all(x < 20 for x, _ in dots)


def test_color_halves_cell_colors():
    img = Image.new("RGB", (40, 40), (0, 0, 255))
    img.paste((255, 0, 0), (0, 0, 20, 40))
    bm = convert(img, 40, 40, "#1a1b26")
    for (cx, _), (_, color) in bm.cells.items():
        assert color == ("#ff0000" if cx < 10 else "#0000ff")


def test_gradient_density_increases():
    img = Image.new("L", (64, 16))
    img.putdata([x * 4 for _ in range(16) for x in range(64)])
    bm = convert(img.convert("RGB"), 64, 16, "#1a1b26")
    dots = lit_dots(bm)
    left = sum(1 for x, _ in dots if x < 16)
    right = sum(1 for x, _ in dots if x >= 48)
    assert right > left


def test_transparent_composites_over_background():
    img = Image.new("RGBA", (20, 40), (0, 0, 0, 0))
    assert convert(img, 20, 40, "#000000").cells == {}
    bm = convert(img, 20, 40, "#ffffff")
    assert len(lit_dots(bm)) == 20 * 40


def test_tall_image_centered_horizontally():
    bm = convert(solid((255, 255, 255), size=(10, 40)), 40, 40, "#1a1b26")
    xs = {x for x, _ in lit_dots(bm)}
    assert min(xs) == 15 and max(xs) == 24  # 10-wide fit centered in 40


def test_exif_orientation_respected(tmp_path):
    import io as _io
    img = Image.new("RGB", (8, 4), (255, 255, 255))
    exif = Image.Exif()
    exif[274] = 6  # rotate 270 to display upright -> portrait 4x8
    buf = _io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    buf.seek(0)
    bm = convert(Image.open(buf), 40, 40, "#1a1b26")
    xs = {x for x, _ in lit_dots(bm)}
    assert max(xs) - min(xs) + 1 <= 22  # portrait fit: ~20 dots wide, not 40
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_imageconv.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'monoline.imageconv'`

- [ ] **Step 4: Implement**

`monoline/imageconv.py`:
```python
"""Image -> Bitmap conversion. Pure logic on top of Pillow."""
from __future__ import annotations

from typing import Dict, List, Tuple

from PIL import Image, ImageOps

from monoline.bitmap import Bitmap
from monoline.raster import DOT_BITS

_FS_KERNEL = ((1, 0, 7 / 16), (-1, 1, 3 / 16), (0, 1, 5 / 16), (1, 1, 1 / 16))


def _hex_to_rgb(color: str) -> Tuple[int, int, int]:
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def convert(img: Image.Image, dot_w: int, dot_h: int, background: str) -> Bitmap:
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGBA")
    base = Image.new("RGBA", img.size, _hex_to_rgb(background) + (255,))
    img = Image.alpha_composite(base, img).convert("RGB")

    scale = min(dot_w / img.width, dot_h / img.height)
    nw = max(1, round(img.width * scale))
    nh = max(1, round(img.height * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    ox, oy = (dot_w - nw) // 2, (dot_h - nh) // 2

    lum: List[float] = [float(v) for v in img.convert("L").getdata()]
    rgb = list(img.getdata())

    bits: Dict[Tuple[int, int], int] = {}
    sums: Dict[Tuple[int, int], List[int]] = {}
    for y in range(nh):
        row = y * nw
        for x in range(nw):
            old = lum[row + x]
            new = 255.0 if old >= 127.5 else 0.0
            err = old - new
            for dx, dy, w in _FS_KERNEL:
                nx, ny = x + dx, y + dy
                if 0 <= nx < nw and 0 <= ny < nh:
                    lum[ny * nw + nx] += err * w
            if not new:
                continue
            px, py = x + ox, y + oy
            if not (0 <= px < dot_w and 0 <= py < dot_h):
                continue
            key = (px // 2, py // 4)
            bits[key] = bits.get(key, 0) | DOT_BITS[(px % 2, py % 4)]
            r, g, b = rgb[row + x]
            acc = sums.setdefault(key, [0, 0, 0, 0])
            acc[0] += r
            acc[1] += g
            acc[2] += b
            acc[3] += 1

    cells: Dict[Tuple[int, int], Tuple[int, str]] = {}
    for key, pattern in bits.items():
        r, g, b, n = sums[key]
        cells[key] = (pattern, f"#{r // n:02x}{g // n:02x}{b // n:02x}")
    return Bitmap(dot_w, dot_h, cells)
```

- [ ] **Step 5: Run all tests**

Run: `.venv\Scripts\python.exe -m pytest -q` — all pass. If a dithering assertion is borderline (off-by-one at a boundary), loosen the TEST bound minimally and note it in the report — never “fix” the kernel to satisfy a test.

- [ ] **Step 6: Commit and push**

```bash
git add pyproject.toml monoline/imageconv.py tests/test_imageconv.py
git commit -m "feat: Floyd-Steinberg image-to-braille converter (adds pillow dependency)"
git push
```

---

### Task 5: File format v2 (bitmap persistence)

**Files:**
- Modify: `monoline/io.py` (save/load)
- Test: `tests/test_io.py` (append)

**Interfaces:**
- Consumes: `Bitmap`, existing `_finite`, `_color`, `MonolineError`.
- Produces: `save` writes `"version": 2` plus `"bitmap": {width, height, cells: [[cx,cy,bits,color],...]}` (sorted cells) when `document.bitmap` is not None, else version 1 with no bitmap key. `load` accepts versions 1 and 2: v1 with a `bitmap` key → corrupt; v2 without one → corrupt. Bitmap validation: dims ints `0 < v <= 100_000`; cell count ≤ `(w//2)*(h//4)`; each entry `[cx, cy, bits, color]` with in-grid ints, bits `1..255`, `_color`-valid color. All failures → `MonolineError`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_io.py`:
```python
def test_v2_round_trip_with_bitmap(tmp_path):
    p = tmp_path / "img.mono.json"
    doc = make_doc()
    doc.set_bitmap(Bitmap(320, 192, {(2, 3): (129, "#aabbcc"), (0, 0): (255, "#ffffff")}))
    save(doc, "tokyonight", p)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["version"] == 2
    assert data["bitmap"]["cells"][0] == [0, 0, 255, "#ffffff"]  # sorted
    doc2, _ = load(p)
    assert doc2.bitmap is not None
    assert doc2.bitmap.cells == doc.bitmap.cells
    assert (doc2.bitmap.width, doc2.bitmap.height) == (320, 192)


def test_no_bitmap_still_writes_version_1(tmp_path):
    p = tmp_path / "plain.mono.json"
    save(make_doc(), "tokyonight", p)
    assert json.loads(p.read_text(encoding="utf-8"))["version"] == 1


def test_v1_with_bitmap_rejected(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"format": "monoline", "version": 1, "width": 8,
                             "height": 8, "background": "#101010",
                             "palette": "tokyonight", "strokes": [],
                             "bitmap": {"width": 8, "height": 8, "cells": []}}))
    with pytest.raises(MonolineError):
        load(p)


def test_v2_without_bitmap_rejected(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"format": "monoline", "version": 2, "width": 8,
                             "height": 8, "background": "#101010",
                             "palette": "tokyonight", "strokes": []}))
    with pytest.raises(MonolineError):
        load(p)


def _v2(bitmap):
    return {"format": "monoline", "version": 2, "width": 8, "height": 8,
            "background": "#101010", "palette": "tokyonight", "strokes": [],
            "bitmap": bitmap}


@pytest.mark.parametrize("bitmap", [
    {"width": 8, "height": 8, "cells": [[0, 0, 0, "#ffffff"]]},     # bits 0
    {"width": 8, "height": 8, "cells": [[0, 0, 256, "#ffffff"]]},   # bits > 255
    {"width": 8, "height": 8, "cells": [[9, 0, 1, "#ffffff"]]},     # col out of grid
    {"width": 8, "height": 8, "cells": [[0, 0, 1, "nothex"]]},      # bad color
    {"width": 0, "height": 8, "cells": []},                          # bad dims
    {"width": 8, "height": 8, "cells": [[0, 0, 1, "#ffffff"]] * 9}, # count > 4*2
])
def test_v2_bitmap_validation(tmp_path, bitmap):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(_v2(bitmap)))
    with pytest.raises(MonolineError):
        load(p)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_io.py -q`
Expected: new tests FAIL (v2 unsupported / bitmap not saved).

- [ ] **Step 3: Implement**

In `monoline/io.py`: change `VERSION = 1` to `VERSIONS = (1, 2)` (update the version-check error message to name both). In `save()`, before writing, extend `data`:
```python
    if document.bitmap is not None:
        data["version"] = 2
        data["bitmap"] = {
            "width": document.bitmap.width,
            "height": document.bitmap.height,
            "cells": [[cx, cy, bits, color]
                      for (cx, cy), (bits, color)
                      in sorted(document.bitmap.cells.items())],
        }
```
(base `data` keeps `"version": 1`). In `load()`, replace the version gate with:
```python
    version = data.get("version")
    if version not in VERSIONS:
        raise MonolineError(
            f"{path} uses format version {version}; "
            f"this monoline supports versions {VERSIONS}")
    if version == 1 and "bitmap" in data:
        raise MonolineError(f"{path} is corrupt: version 1 cannot carry a bitmap")
    if version == 2 and "bitmap" not in data:
        raise MonolineError(f"{path} is corrupt: version 2 requires a bitmap")
```
Add a helper (above `load`) and call it inside the existing field-parsing `try` block after strokes are built (`doc.bitmap = _bitmap_from_json(data["bitmap"]) if version == 2 else None`):
```python
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
```
Add `from monoline.bitmap import Bitmap` to io.py imports.

- [ ] **Step 4: Run all tests**

Run: `.venv\Scripts\python.exe -m pytest -q` — all pass.

- [ ] **Step 5: Commit and push**

```bash
git add monoline/io.py tests/test_io.py
git commit -m "feat: .mono.json format v2 with validated bitmap persistence"
git push
```

---

### Task 6: The four import doors (app + CLI + help)

**Files:**
- Modify: `monoline/app.py`, `monoline/cli.py`, `monoline/canvas.py` (one call in on_resize), `monoline/help.py` (keymap lines)
- Test: `tests/test_app.py` (append)

**Interfaces:**
- Consumes: `convert` (Task 4), `Document.set_bitmap` (Task 1), existing `TextPrompt`, `notify`, pending-layout mechanism (`DrawCanvas.on_resize`).
- Produces:
  - `monoline.app.IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}`
  - `MonolineApp(path=None, import_path: Optional[str] = None)`; `MonolineApp.apply_pending_import() -> None` (no-op when nothing pending; called by canvas after every resize).
  - `MonolineApp._import_image(source: Union[str, PIL.Image.Image]) -> None` — converts + `set_bitmap` + rebuild + notify; failures notify with `severity="error"`, never raise.
  - Bindings: `i` → import dialog, `v` → clipboard grab. App-level `on_paste` imports dropped image paths.
  - `run(path)` routes image-suffixed paths to `import_path`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_app.py`:
```python
import pytest
from PIL import Image
from textual import events


@pytest.fixture
def png(tmp_path):
    p = tmp_path / "pic.png"
    Image.new("RGB", (10, 10), (255, 255, 255)).save(p)
    return str(p)


async def test_paste_image_path_imports(png):
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        app.post_message(events.Paste(f'"{png}"'))
        await pilot.pause()
        assert app.document.bitmap is not None


async def test_paste_non_image_ignored():
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        app.post_message(events.Paste("just some text"))
        await pilot.pause()
        assert app.document.bitmap is None


async def test_import_dialog_and_callback(png):
    from monoline.dialogs import TextPrompt
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        await pilot.press("i")
        assert isinstance(app.screen, TextPrompt)
        await pilot.press("escape")
        app._on_import_name(png)
        await pilot.pause()
        assert app.document.bitmap is not None


async def test_clipboard_image_imports(monkeypatch, png):
    from PIL import ImageGrab
    monkeypatch.setattr(ImageGrab, "grabclipboard",
                        lambda: Image.open(png))
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        await pilot.press("v")
        await pilot.pause()
        assert app.document.bitmap is not None


async def test_clipboard_empty_notifies(monkeypatch):
    from PIL import ImageGrab
    monkeypatch.setattr(ImageGrab, "grabclipboard", lambda: None)
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        await pilot.press("v")
        await pilot.pause()
        assert app.document.bitmap is None


async def test_cli_import_path_applies_after_layout(png):
    app = MonolineApp(None, import_path=png)
    async with app.run_test(size=(40, 12)) as pilot:
        await pilot.pause()
        assert app.document.bitmap is not None
        assert app.document.bitmap.width == app.document.width


async def test_import_is_one_undo_step(png):
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        app._import_image(png)
        await pilot.press("u")
        assert app.document.bitmap is None


async def test_import_failure_notifies_no_crash(tmp_path):
    bad = tmp_path / "not_an_image.png"
    bad.write_text("hello")
    app = MonolineApp()
    async with app.run_test(size=(40, 12)) as pilot:
        app._import_image(str(bad))
        await pilot.pause()
        assert app.document.bitmap is None
        assert app.is_running
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_app.py -q`
Expected: new tests FAIL (no `import_path` kwarg, no bindings, no handlers).

- [ ] **Step 3: Implement app changes**

`monoline/app.py`:
- Imports: add `from pathlib import Path`, `from typing import List, Optional, Union` (extend existing), `from textual import events`.
- Module constant after the imports:
```python
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
```
- `__init__` signature becomes `def __init__(self, path: Optional[str] = None, import_path: Optional[str] = None) -> None:` and add `self.pending_import = import_path` (after `self.path = path`).
- Bindings to add:
```python
        Binding("i", "import_image", "Import", show=False),
        Binding("v", "paste_image", "Paste image", show=False),
```
- New methods:
```python
    def apply_pending_import(self) -> None:
        if self.pending_import is None:
            return
        path, self.pending_import = self.pending_import, None
        self._import_image(path)

    def _import_image(self, source) -> None:
        from PIL import Image, UnidentifiedImageError
        from monoline.imageconv import convert
        name = "clipboard image"
        try:
            if isinstance(source, Image.Image):
                img = source
            else:
                name = os.path.basename(str(source))
                img = Image.open(source)
            bitmap = convert(img, self.document.width,
                             self.document.height, self.document.background)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            self.notify(f"import failed: {exc}", severity="error")
            return
        self.document.set_bitmap(bitmap)
        self.query_one(DrawCanvas).rebuild()
        self.update_status()
        self.notify(f"imported {name}")

    def on_paste(self, event: events.Paste) -> None:
        text = event.text.strip().strip('"').strip("'")
        p = Path(text)
        if p.suffix.lower() in IMAGE_SUFFIXES and p.is_file():
            event.stop()
            self._import_image(str(p))

    def action_import_image(self) -> None:
        self.push_screen(TextPrompt("Import image:", "photo.png"),
                         self._on_import_name)

    def _on_import_name(self, name) -> None:
        if name:
            self._import_image(name)

    def action_paste_image(self) -> None:
        from PIL import Image as PILImage
        try:
            from PIL import ImageGrab
            data = ImageGrab.grabclipboard()
        except Exception as exc:  # NotImplementedError, missing xclip/wl-paste
            self.notify(f"clipboard unavailable: {exc}", severity="error")
            return
        if isinstance(data, PILImage.Image):
            self._import_image(data)
            return
        if isinstance(data, list):
            for item in data:
                if Path(str(item)).suffix.lower() in IMAGE_SUFFIXES:
                    self._import_image(str(item))
                    return
        self.notify("no image in the clipboard")
```
- `run()` becomes:
```python
def run(path: Optional[str] = None) -> None:
    if path is not None and Path(path).suffix.lower() in IMAGE_SUFFIXES:
        MonolineApp(None, import_path=path).run(mouse=True)
    else:
        MonolineApp(path).run(mouse=True)
```

`monoline/canvas.py` — at the END of `on_resize` (after the existing sizing guard block, so it runs on every resize):
```python
        self.app.apply_pending_import()
```

`monoline/help.py` — in `KEYMAP`, add after the export/clear line:
```
 i               import image  v           paste image
```
(keep the two-column layout of the surrounding lines).

`monoline/cli.py` — update the `file` argument help text to `"a .mono.json drawing or an image (.png/.jpg/...) to import"`. No logic change (routing lives in `run`).

- [ ] **Step 4: Run all tests**

Run: `.venv\Scripts\python.exe -m pytest -q` — all pass, pristine output. If `on_paste` at App level never fires because a widget consumed the event, move the handler to `DrawCanvas` (it has focus) and note the adaptation in your report — the test assertions stay identical.

- [ ] **Step 5: Commit and push**

```bash
git add monoline/app.py monoline/canvas.py monoline/cli.py monoline/help.py tests/test_app.py
git commit -m "feat: image import via drop, dialog, CLI, and clipboard"
git push
```

---

### Task 7: README media — demo scene, SVG screenshots, GIFs

**Files:**
- Create: `scripts/demo_scene.py`, `scripts/make_screenshots.py`, `scripts/make_gifs.py`, `docs/assets/` (generated: `screenshot-drawing.svg`, `screenshot-import.svg`, `demo-drawing.gif`, `demo-import.gif`)
- Modify: `README.md`
- Test: `tests/test_scripts.py`

**Interfaces:**
- Consumes: the whole app (Pilot), `render_cells`, `Bitmap`, palettes.
- Produces: committed media in `docs/assets/`; scripts are repo-only (not in the wheel — hatchling only packages `monoline/`, verify with `git ls-files` vs wheel contents if unsure).

- [ ] **Step 1: Write the shared demo scene**

`scripts/demo_scene.py`:
```python
"""Deterministic demo content shared by the screenshot and GIF scripts."""
from __future__ import annotations

import math

from PIL import Image, ImageDraw


def make_demo_image(size=(320, 200)):
    """A generated sunset scene — no licensing, fully reproducible."""
    w, h = size
    img = Image.new("RGB", size)
    top, bottom = (26, 27, 38), (247, 118, 142)
    for y in range(h):
        t = y / (h - 1)
        img.paste(tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)),
                  (0, y, w, y + 1))
    d = ImageDraw.Draw(img)
    d.ellipse((w * 0.30, h * 0.18, w * 0.70, h * 0.62), fill=(224, 175, 104))
    d.polygon([(0, h), (w * 0.35, h * 0.55), (w * 0.62, h)], fill=(65, 72, 104))
    d.polygon([(w * 0.45, h), (w * 0.78, h * 0.45), (w, h)], fill=(52, 59, 88))
    return img


def circle_points(cx, cy, r, n=48):
    return [(cx + r * math.cos(2 * math.pi * i / n),
             cy + r * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]


def wobbly_circle_points(cx, cy, r, n=48):
    """A hand-drawn-looking circle (deterministic wobble, no random)."""
    return [(cx + (r + 1.5 * math.sin(7 * a)) * math.cos(a),
             cy + (r + 1.5 * math.sin(7 * a)) * math.sin(a))
            for a in [2 * math.pi * i / n for i in range(n + 1)]]


def petal_points(cx, cy, r, n=32):
    """One flowing curve; radial-4 symmetry turns it into a mandala."""
    return [(cx + r * t * math.cos(3.0 * t), cy + r * t * math.sin(3.0 * t))
            for t in [i / n for i in range(1, n + 1)]]
```

- [ ] **Step 2: Write the screenshot script**

`scripts/make_screenshots.py`:
```python
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
        snapped = recognize(wobbly_circle_points(w * 0.72, h * 0.32, h * 0.18))
        add(app, snapped, app.palette.colors[1])
        add(app, petal_points(w * 0.28, h * 0.55, h * 0.30),
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
```

- [ ] **Step 3: Write the GIF script**

`scripts/make_gifs.py`:
```python
"""Generate README GIFs with a deterministic Pillow frame renderer.

Run: .venv\\Scripts\\python.exe scripts\\make_gifs.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from demo_scene import make_demo_image, petal_points, wobbly_circle_points

from monoline.bitmap import Bitmap
from monoline.document import Stroke
from monoline.imageconv import convert
from monoline.palettes import get_palette
from monoline.raster import BRAILLE_BASE, DOT_BITS, render_cells
from monoline.shapes import recognize
from monoline.symmetry import siblings

ASSETS = Path(__file__).resolve().parent.parent / "docs" / "assets"
W, H = 160, 96          # canvas in dots
DOT = 6                  # px per dot in the frame
SS = 2                   # supersampling factor
MAX_BYTES = 4 * 1024 * 1024


def render_frame(strokes: List[Stroke], bitmap: Optional[Bitmap],
                 background: str) -> Image.Image:
    px = DOT * SS
    img = Image.new("RGB", (W * px, H * px), background)
    d = ImageDraw.Draw(img)
    r = px * 0.42
    for (cx, cy), (char, color) in render_cells(strokes, W, H, bitmap).items():
        bits = ord(char) - BRAILLE_BASE
        for (dx, dy), bit in DOT_BITS.items():
            if bits & bit:
                x = (cx * 2 + dx + 0.5) * px
                y = (cy * 4 + dy + 0.5) * px
                d.ellipse((x - r, y - r, x + r, y + r), fill=color)
    return img.resize((W * DOT, H * DOT), Image.LANCZOS)


def save_gif(frames: List[Image.Image], path: Path, ms: int) -> None:
    quantized = [f.quantize(colors=128) for f in frames]
    quantized[0].save(path, save_all=True, append_images=quantized[1:],
                      duration=ms, loop=0, optimize=True)
    size = path.stat().st_size
    assert size < MAX_BYTES, f"{path} is {size} bytes (>= 4 MB)"
    print(f"wrote {path} ({size / 1024:.0f} KB)")


def reveal(stroke: Stroke, fraction: float) -> Stroke:
    n = max(1, round(len(stroke.points) * fraction))
    return Stroke(points=stroke.points[:n], color=stroke.color,
                  kind=stroke.kind, width=stroke.width)


def gif_drawing() -> None:
    pal = get_palette("tokyonight")
    raw = Stroke(points=wobbly_circle_points(W * 0.70, H * 0.35, H * 0.22),
                 color=pal.colors[1])
    snapped = Stroke(points=recognize(raw.points), color=pal.colors[1])
    petal = Stroke(points=petal_points(W * 0.30, H * 0.55, H * 0.34),
                   color=pal.colors[4])
    mirrors = [Stroke(points=p, color=petal.color)
               for p in siblings(petal.points, "radial4", W, H)]

    frames: List[Image.Image] = []
    steps = 24
    for i in range(1, steps + 1):            # wobbly circle grows...
        frames.append(render_frame([reveal(raw, i / steps)], None, pal.background))
    frames += [render_frame([snapped], None, pal.background)] * 8   # ...snaps!
    for i in range(1, steps + 1):            # mandala mirrors live
        part = [snapped, reveal(petal, i / steps)]
        part += [reveal(m, i / steps) for m in mirrors]
        frames.append(render_frame(part, None, pal.background))
    frames += [frames[-1]] * 16              # hold the finish
    save_gif(frames, ASSETS / "demo-drawing.gif", ms=70)


def gif_import() -> None:
    pal = get_palette("tokyonight")
    bitmap = convert(make_demo_image(), W, H, pal.background)
    order = sorted(bitmap.cells)             # reveal in scan order
    steps = 30
    frames: List[Image.Image] = []
    for i in range(1, steps + 1):
        shown = order[: round(len(order) * i / steps)]
        partial = Bitmap(W, H, {k: bitmap.cells[k] for k in shown})
        frames.append(render_frame([], partial, pal.background))
    doodle = Stroke(points=wobbly_circle_points(W * 0.5, H * 0.78, H * 0.12),
                    color=pal.colors[2])
    for i in range(1, 17):                   # doodle over the photo
        frames.append(render_frame([reveal(doodle, i / 16)], bitmap,
                                   pal.background))
    frames += [frames[-1]] * 16
    save_gif(frames, ASSETS / "demo-import.gif", ms=70)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    gif_drawing()
    gif_import()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Write the failing smoke tests, then generate**

`tests/test_scripts.py`:
```python
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "docs" / "assets"


def run_script(name):
    out = subprocess.run([sys.executable, str(REPO / "scripts" / name)],
                         capture_output=True, text=True, cwd=str(REPO))
    assert out.returncode == 0, out.stderr


def test_make_screenshots():
    run_script("make_screenshots.py")
    for f in ("screenshot-drawing.svg", "screenshot-import.svg"):
        p = ASSETS / f
        assert p.exists() and p.stat().st_size > 1000
        assert b"<svg" in p.read_bytes()[:200]


def test_make_gifs():
    run_script("make_gifs.py")
    for f in ("demo-drawing.gif", "demo-import.gif"):
        p = ASSETS / f
        assert p.exists() and 1000 < p.stat().st_size < 4 * 1024 * 1024
        assert p.read_bytes()[:6] in (b"GIF87a", b"GIF89a")
```
Run: `.venv\Scripts\python.exe -m pytest tests/test_scripts.py -q` — first FAIL (scripts missing / assets absent), then after Steps 1-3 exist, PASS and the four asset files appear. Eyeball the SVGs (open in a browser) and GIFs before committing — they are the public face of the repo; if the composition looks off, adjust the scene constants.

- [ ] **Step 5: Update the README**

Replace the `> 🚧 Under construction — screenshot coming soon.` line with:
```markdown
![monoline drawing demo](docs/assets/demo-drawing.gif)

*Freehand drawing with live smoothing — hold **Ctrl** and a rough circle
snaps to a perfect one; symmetry mirrors strokes as you draw.*
```
Add a new section after the keymap:
```markdown
## Import images

Drop any image file onto the terminal (or press `i` for a path prompt,
`v` to paste one from the clipboard, or run `monoline photo.png`) and it
becomes braille art you can draw over — Floyd-Steinberg dithered, with
24-bit color per cell. A braille cell's eight dots share one color, so
chroma resolution is per-cell: that's the medium, not a bug. Erasing over
an image hides its dots non-destructively; undo brings the import back.

On Linux, clipboard paste needs `xclip` (X11) or `wl-clipboard` (Wayland).

![image import demo](docs/assets/demo-import.gif)
```
And add both screenshots near the top, after the hero GIF:
```markdown
| | |
|---|---|
| ![drawing](docs/assets/screenshot-drawing.svg) | ![import](docs/assets/screenshot-import.svg) |
```
Also add `i` / `v` rows to the keymap table (`i` — import image, `v` — paste image from clipboard).

- [ ] **Step 6: Run all tests, commit and push**

Run: `.venv\Scripts\python.exe -m pytest -q` — all pass.

```bash
git add scripts/ docs/assets/ README.md tests/test_scripts.py
git commit -m "docs: README screenshots and GIF demos generated by repo scripts"
git push
```

---

### Task 8: Version 0.2.0 + release

**Files:**
- Modify: `pyproject.toml` (`version = "0.2.0"`), `monoline/__init__.py` (`__version__ = "0.2.0"`)

- [ ] **Step 1: Bump the version in both files, run tests**

Run: `.venv\Scripts\python.exe -m pytest -q` — all pass (test_cli reads `__version__`, so no test edits needed).

- [ ] **Step 2: Commit and push**

```bash
git add pyproject.toml monoline/__init__.py
git commit -m "chore: bump version to 0.2.0"
git push
```

- [ ] **Step 3: Controller gate — final whole-branch review, then tag**

The controller (not the task implementer): run the final whole-branch code review over the v0.2.0 range, fix any findings, confirm CI green, then:
```bash
git tag v0.2.0
git push origin v0.2.0
gh run watch --exit-status
```
Expected: release workflow publishes to PyPI (trusted publisher already configured — no owner action). Verify: fresh venv → `pip install monoline==0.2.0` → `monoline --version` prints `monoline 0.2.0`.

---

## Self-Review Notes

- **Spec coverage:** §2 bitmap model (Task 1), §3 compositing + SVG (Tasks 2-3), §4 converter + Pillow dep (Task 4), §5 four doors + help (Task 6), §6 format v2 (Task 5), §7 media scripts + README (Task 7), §8 help/README touch-ups (Tasks 6-7), §9 testing (throughout), §10 release (Task 8). No gaps.
- **Type consistency:** `Bitmap(width, height, cells)` and `cells: (col,row)->(bits,color)` used identically in Tasks 1-5, 7; `render_cells(..., bitmap=None)` (Tasks 2, 7); `set_bitmap(Optional[Bitmap])` (Tasks 1, 5, 6, 7); `convert(img, dot_w, dot_h, background)` (Tasks 4, 6, 7); `IMAGE_SUFFIXES` defined once in app (Task 6).
- **Known judgment points for implementers:** App-level `on_paste` routing (Task 6 Step 4 names the fallback); dithering boundary assertions (Task 4 Step 5 names the rule: loosen the test bound, never the kernel); media composition is eyeballed before commit (Task 7 Step 4).
- **GIF size:** dot-art frames quantize to ~100-400 KB per GIF at these settings; the 4 MB assertion guards regressions.




