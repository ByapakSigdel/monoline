# monoline — design spec

**Date:** 2026-07-06
**Status:** Approved (design review with project owner)

## 1. Overview

monoline is a terminal drawing tool focused on aesthetics and fun rather than
pixel-editing utility. `pip install monoline` (or `pipx install monoline` /
`uv tool install monoline`), then run `monoline` in any modern terminal to get
a full-screen, chromeless drawing surface. Freehand strokes are drawn with the
mouse and rendered as smooth, colored braille lines — a single-weight
"monoline" pen-plotter look. Holding **Ctrl** while drawing snaps the finished
stroke to a perfect shape (line / circle / ellipse / rectangle), inspired by
tldraw's shape correction.

### Goals

- Drawing in a terminal that looks genuinely good, not like MS Paint in ASCII.
- Helpers that make drawing fun: live stroke smoothing, Ctrl shape correction,
  curated color palettes, symmetry mode, dot grid.
- Cross-platform: Windows / macOS / Linux, installable from PyPI, runs after
  install with no further setup.
- Public GitHub repository with an incremental, feature-by-feature commit
  history.

### Non-goals (v1)

- Layers, selection/move tools, text tool, fills, brush widths.
- PNG export (v1.1 candidate).
- Canvas panning/zooming; multi-document tabs.
- Pixel-resolution mouse input (terminal mouse protocol is cell-resolution).

## 2. UX

### Screen layout

- The canvas fills the entire terminal except a single-line **status bar** at
  the bottom.
- Status bar shows: current tool (pen/eraser) · active palette name + the nine
  color swatches with the selected one highlighted · symmetry state · grid
  state · unsaved-changes indicator (`●`) · hint `? help`.
- No toolbars, menus, or window chrome.

### Interactions

| Input | Action |
|---|---|
| Left mouse drag | Draw freehand stroke (smoothed live) |
| **Ctrl** + left drag | Draw with shape correction: on release, stroke snaps to best-fit shape if fit is good enough |
| `d` | Pen tool |
| `e` | Eraser tool (round eraser, radius 3 dots) |
| `1`–`9` | Select color from active palette |
| `p` / `P` | Next / previous palette |
| `s` | Cycle symmetry: off → vertical → horizontal → radial-4 → off |
| `g` | Toggle dot grid (and grid snapping for corrected shapes) |
| `u`, `Ctrl+Z` | Undo |
| `r`, `Ctrl+Y` | Redo |
| `Ctrl+S` | Save (`.mono.json`; prompts for filename if untitled) |
| `x` | Export prompt: ANSI text (`.txt`) or SVG (`.svg`) |
| `c` | Clear canvas (with confirmation) |
| `?` | Help overlay (full keymap) |
| `q` | Quit (confirmation if unsaved changes) |

### Shape correction behavior

- Config `shape_correct` = `"ctrl"` (default) | `"always"` | `"off"`.
  - `ctrl`: correction applies only to strokes drawn with Ctrl held.
  - `always`: every stroke is a correction candidate (Ctrl not needed).
  - `off`: never corrects — for people who don't want it, and for terminals
    that swallow Ctrl+drag (e.g. stock xterm reserves Ctrl+click for menus).
- Correction only replaces a stroke when the best fit's error is below
  threshold; a genuine scribble stays a scribble even with Ctrl held.

## 3. Architecture

Python package with TUI-free core modules (pure data/functions, unit-testable
without a terminal) and a thin Textual layer on top.

```
monoline/
  __init__.py   __version__
  cli.py        entry point: monoline [FILE], --version
  app.py        Textual App: layout, keybindings, status bar, dialogs
  canvas.py     Canvas widget: mouse events → strokes; renders via raster
  document.py   Stroke/Document model + undo-redo (pure)
  raster.py     strokes → braille cells + per-cell color (pure)
  smoothing.py  stroke smoothing/interpolation (pure)
  shapes.py     shape recognizer: least-squares fits + scoring (pure)
  symmetry.py   mirror/radial stroke transforms (pure)
  palettes.py   curated palette data
  io.py         .mono.json save/load, ANSI export, SVG export (pure)
  config.py     TOML config via platformdirs
```

Runtime dependencies: `textual` (>=1.0) and `platformdirs` only. Python
>= 3.9. No NumPy — the geometry is small enough for stdlib math.

### Coordinate system

- **Dot space**: the drawing surface is a grid of braille dots — width =
  2 × terminal columns, height = 4 × terminal rows (canvas area). All stroke
  points are floats in dot space.
- Because a terminal cell is ≈1:2 (w:h) and subdivides 2×4, dots are
  approximately square — so dot space doubles as a sane geometric space for
  shape fitting and SVG export.
- Terminal mouse events arrive at **cell** resolution. Input samples are
  mapped to the center of the cell in dot space; smoothing/interpolation
  (§5) reconstructs a smooth sub-cell path. This is the key input constraint
  of the medium and is embraced, not fought.
- Document size is fixed at creation (the terminal's canvas size at launch).
  Documents always render anchored to the top-left: larger-than-terminal
  documents are clipped, smaller ones leave unused space right/bottom. No
  panning or centering in v1 — deterministic and simple.

### Data model

- `Stroke`: `points: list[tuple[float, float]]` (dot space), `color: str`
  (hex, absolute — palette switching never recolors existing strokes),
  `kind: "pen" | "erase"`, `width: float` — the stroke diameter in dots
  (v1: pen = 1.0, eraser = 6.0, i.e. the §2 radius-3 eraser).
- `Document`: `width`, `height` (dots), `background: str` (hex),
  `strokes: list[Stroke]`, plus undo/redo stacks of operations.
- Operations: `AddStrokes(strokes)` (one op may add several strokes — the
  symmetry siblings of one gesture undo as a unit), `Clear(previous_strokes)`.
  New operations clear the redo stack.
- Eraser strokes are ordinary strokes with `kind="erase"`: at raster time,
  strokes apply in order and erase strokes clear dots within their radius.
  This keeps the document append-only and undo trivial.

## 4. Rendering pipeline

`Document → dot bitmap → braille cells`:

1. For each stroke in order, walk consecutive point pairs with a Bresenham-
   style line in dot space (pen: set dots + record stroke color per dot;
   erase: clear dots within radius).
2. Group dots 2×4 into cells; each non-empty cell becomes the braille char
   U+2800 + bit pattern, foreground color = color of the **most recently
   drawn** dot in that cell (last-stroke-wins).
3. The Textual Canvas widget renders cells as styled segments via the Line
   API; only rows whose cells changed are re-rendered (dirty-row tracking) so
   drawing stays responsive on large terminals.
4. Grid overlay (when on): cells that are empty show a faint dot (`·`-like
   braille dot pattern, dim color from palette) every 4 columns × 2 rows.

## 5. Stroke smoothing

Always on (strength configurable via `smoothing = 0.0–1.0`, default 0.5):

1. Deduplicate consecutive identical cell samples.
2. Chaikin corner-cutting (1–3 iterations scaled by strength) over the
   dot-space points.
3. Resample to roughly one point per dot of path length so downstream
   consumers (raster, SVG, shape fitting) see uniform density.

Pure function: `smooth(points, strength) -> points`.

## 6. Shape recognition

`recognize(points) -> Stroke-shaped points | None`, deterministic geometry:

1. Reject if < 8 samples or bounding-box diagonal < 4 dots.
2. Closed/open heuristic: `dist(start, end) < 0.2 × path_length` → closed
   candidates (circle, ellipse, rectangle); otherwise open (line).
3. Fits: line = total least squares; circle = Kåsa algebraic fit; ellipse =
   axis-aligned bounding fit; rectangle = dominant-direction corner detection
   (split stroke at direction changes > 60°, require 4 corners, fit
   axis-aligned or dominant-angle box).
4. Score each candidate by RMS residual normalized by bounding-box diagonal;
   accept the best if score < 0.08 (module constant, tuned with tests).
5. On accept, regenerate points as the perfect shape (uniformly sampled). If
   grid is on, snap defining geometry (endpoints, center, corners) to grid
   intersections first.

## 7. Symmetry

`s` cycles off / vertical / horizontal / radial-4 (mirror axes centered on
the canvas). While active, each input gesture produces the drawn stroke plus
its mirrored/rotated siblings live (previewed during the drag, committed as
one `AddStrokes` op). Shape correction applies to the source stroke before
mirroring, so all siblings are corrected consistently.

## 8. Palettes

Seven curated palettes, nine colors each, plus a background color per palette:
`tokyonight` (default), `catppuccin` (mocha), `gruvbox`, `nord`, `pastel`,
`neon`, `mono` (grayscale ramp). Switching palettes changes the background
and available colors but never recolors existing strokes. Colors are 24-bit;
Textual degrades gracefully on 256-color terminals.

## 9. Persistence & export

### `.mono.json` (native)

```json
{
  "format": "monoline",
  "version": 1,
  "width": 320, "height": 192,
  "background": "#1a1b26",
  "palette": "tokyonight",
  "strokes": [
    {"kind": "pen", "color": "#7aa2f7", "width": 1.0,
     "points": [[10.0, 12.5], [11.0, 13.0]]}
  ]
}
```

Load validates `format`/`version` and fails with a clear CLI error on
mismatch. Undo history is not persisted (stacks reset on load).

### ANSI text export (`.txt`)

The exact rendered braille output with 24-bit ANSI color escapes per color
run, reset at end of each line, trailing blank cells trimmed. `cat file.txt`
reproduces the drawing in any truecolor terminal.

### SVG export (`.svg`)

- `viewBox = "0 0 width height"` in dot units (dots ≈ square, so 1:1).
- Background `<rect>` in the document background color.
- Each pen stroke → `<polyline>` with `stroke-linecap/linejoin="round"`, its
  stroke color, no fill. Pen strokes use `stroke-width="1.5"` (slightly
  heavier than the 1-dot raster line, for visual weight parity on screens —
  a deliberate aesthetic choice).
- Erase strokes → same, in the background color with `stroke-width` equal to
  the stroke's `width` (correct on the solid background; documented
  limitation).

## 10. Configuration

TOML at `platformdirs.user_config_dir("monoline")/config.toml`, created with
defaults on first run:

```toml
shape_correct = "ctrl"   # ctrl | always | off
palette = "tokyonight"
smoothing = 0.5           # 0.0 – 1.0
```

Read via stdlib `tomllib` (3.11+) with `tomli` fallback dependency for
3.9/3.10. Invalid values fall back to defaults with a status-bar notice.

## 11. CLI

- `monoline` — new untitled document (terminal-sized).
- `monoline FILE` — open `FILE` if it exists, else start new and save there
  on `Ctrl+S`.
- `monoline --version` — print version and exit.

Entry point: `[project.scripts] monoline = "monoline.cli:main"`.

## 12. Repository, packaging, CI

- Public GitHub repo `ByapakSigdel/monoline`, default branch `main`, MIT
  license. All commits authored `ByapakSigdel <sigdelmb123@gmail.com>`; **no
  co-author trailers**. Small feature-scoped commits pushed continuously
  (conventional-style messages: `feat:`, `fix:`, `test:`, `docs:`, `ci:`).
- `pyproject.toml` with hatchling backend; `requires-python = ">=3.9"`;
  dependencies `textual>=1.0`, `platformdirs>=3`, `tomli>=2; python_version <
  "3.11"`. Dev extras: `pytest`, `pytest-asyncio` (for Textual Pilot tests).
- README: hero screenshot/GIF placeholder, install commands (pip/pipx/uv),
  full keymap, palette list, terminal-support notes, contributing blurb.
- **CI (`.github/workflows/ci.yml`)**: on push/PR — pytest across
  {ubuntu, macos, windows} × Python {3.9, 3.11, 3.13} (corners of the
  support matrix; full range covered by `requires-python`).
- **Release (`.github/workflows/release.yml`)**: on tag `v*` — build
  sdist+wheel (`python -m build`), publish to PyPI via **Trusted
  Publishing** (`pypa/gh-action-pypi-publish`, OIDC, no stored token).
  One-time manual step for the owner: create a PyPI account and register
  `ByapakSigdel/monoline` + `release.yml` as a pending trusted publisher for
  the `monoline` project. Exact instructions delivered at release milestone.

## 13. Cross-platform constraints (documented in README)

- Requires a terminal with mouse reporting and Unicode: Windows Terminal
  (Windows 10/11 default on 11), macOS Terminal/iTerm2/kitty, any modern
  Linux VTE. Legacy `conhost.exe` is explicitly unsupported for drawing
  (keyboard-only fallback still functions: the app runs, tools/palettes/
  export all work, but freehand drawing needs a mouse in v1).
- Braille glyphs require a font containing U+2800–U+28FF: Cascadia Code/Mono,
  all Nerd Fonts, and default macOS/Linux monospace fonts qualify.
- Textual abstracts mouse protocols, key decoding, and color depth across
  platforms — this is the load-bearing reason for the Python+Textual stack.

## 14. Testing

- **Unit (pure modules, no TTY):**
  - `raster`: known point sets → exact braille char/bit patterns and colors;
    erase strokes clear dots; last-stroke-wins color.
  - `shapes`: synthetic noisy lines/circles/ellipses/rectangles (parametric +
    jitter) classify correctly; scribbles and low-sample strokes return
    `None`; grid snapping applies.
  - `smoothing`: output density, endpoint preservation, jitter reduction.
  - `symmetry`: mirrored/rotated coordinates exact for each mode.
  - `document`: undo/redo invariants, symmetry-group ops undo atomically,
    redo cleared on new op.
  - `io`: `.mono.json` round-trip equality; ANSI output stable snapshot; SVG
    parses (stdlib `xml.etree`) and contains expected polylines; version
    mismatch errors.
- **App-level (Textual Pilot):** launch, simulated drag creates a stroke,
  Ctrl-drag of a near-circle becomes a circle, keybindings toggle state,
  quit-with-unsaved shows confirmation. Marked async; run in CI on all OSes.

## 15. Build order (each milestone = passing tests + push)

1. Scaffold: package skeleton, pyproject, LICENSE, README, CI — installable,
   `monoline --version` works.
2. `document` model + undo/redo.
3. `raster` braille rasterizer.
4. Textual app + canvas: freehand pen drawing, one color, status bar shell.
5. `smoothing` live smoothing.
6. `shapes` Ctrl shape correction.
7. `palettes` + color/palette keys.
8. Eraser.
9. `symmetry` modes.
10. Grid & guides (+ snap).
11. Save/load `.mono.json` + untitled-save prompt.
12. ANSI + SVG export.
13. Help overlay, confirmations, README polish.
14. `v0.1.0` tag → PyPI release (after owner's trusted-publisher setup).

## 16. Risks & mitigations

- **Ctrl+drag unavailable in some terminals** → `shape_correct = "always"`
  mode and `"off"`; documented.
- **Cell-resolution input feels coarse** → smoothing/interpolation is the
  core mitigation; tuned constants live in one module.
- **Braille font gaps on odd setups** → README font note; ANSI export still
  viewable anywhere a proper font exists.
- **PyPI publish blocked on owner's account setup** → everything else ships
  first; release is the final milestone with a 2-minute instruction list.
