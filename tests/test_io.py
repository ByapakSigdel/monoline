import json
import xml.etree.ElementTree as ET

import pytest

from monoline.document import Document, Stroke
from monoline.io import MonolineError, export_ansi, export_svg, load, save


def make_doc():
    doc = Document(320, 192, background="#1a1b26")
    doc.add_strokes([
        Stroke(points=[(10.0, 12.5), (11.0, 13.0)], color="#7aa2f7"),
        Stroke(points=[(5.0, 5.0)], kind="erase", width=6.0),
    ])
    return doc


def test_round_trip(tmp_path):
    p = tmp_path / "a.mono.json"
    save(make_doc(), "tokyonight", p)
    doc2, palette = load(p)
    doc1 = make_doc()
    assert palette == "tokyonight"
    assert (doc2.width, doc2.height, doc2.background) == (320, 192, "#1a1b26")
    assert doc2.strokes == doc1.strokes
    assert doc2.dirty is False
    assert doc2.undo() is False  # history not persisted


def test_save_is_atomic_leaves_no_tmp_file(tmp_path):
    p = tmp_path / "a.mono.json"
    save(make_doc(), "tokyonight", p)
    assert not p.with_name(p.name + ".tmp").exists()
    doc2, palette = load(p)
    assert palette == "tokyonight"
    assert doc2.strokes == make_doc().strokes


def test_format_fields(tmp_path):
    p = tmp_path / "a.mono.json"
    save(make_doc(), "nord", p)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["format"] == "monoline"
    assert data["version"] == 1
    assert data["palette"] == "nord"


def test_load_rejects_wrong_format(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text('{"format": "other", "version": 1}')
    with pytest.raises(MonolineError):
        load(p)


def test_load_rejects_future_version(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text('{"format": "monoline", "version": 99}')
    with pytest.raises(MonolineError):
        load(p)


def test_load_rejects_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{nope")
    with pytest.raises(MonolineError):
        load(p)


def test_load_rejects_nan_point(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({
        "format": "monoline", "version": 1, "width": 8, "height": 8,
        "background": "#101010", "palette": "tokyonight",
        "strokes": [{"kind": "pen", "color": "#ffffff",
                     "width": 1.0, "points": [[0.0, float("nan")]]}],
    }))
    with pytest.raises(MonolineError):
        load(p)


def test_load_rejects_infinite_stroke_width(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(
        '{"format": "monoline", "version": 1, "width": 8, "height": 8, '
        '"background": "#101010", "palette": "tokyonight", '
        '"strokes": [{"kind": "pen", "color": "#ffffff", '
        '"width": Infinity, "points": [[0.0, 0.0]]}]}')
    with pytest.raises(MonolineError):
        load(p)


def test_load_rejects_huge_point_coordinate(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({
        "format": "monoline", "version": 1, "width": 8, "height": 8,
        "background": "#101010", "palette": "tokyonight",
        "strokes": [{"kind": "pen", "color": "#ffffff",
                     "width": 1.0, "points": [[0.0, 1e308]]}],
    }))
    with pytest.raises(MonolineError):
        load(p)


def test_load_rejects_overflowing_document_width(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(
        '{"format": "monoline", "version": 1, "width": 1e999, "height": 8, '
        '"background": "#101010", "palette": "tokyonight", "strokes": []}')
    with pytest.raises(MonolineError):
        load(p)


def test_load_rejects_nonpositive_document_width(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({
        "format": "monoline", "version": 1, "width": 0, "height": 8,
        "background": "#101010", "palette": "tokyonight",
        "strokes": [],
    }))
    with pytest.raises(MonolineError):
        load(p)


def test_load_rejects_invalid_color(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({
        "format": "monoline", "version": 1, "width": 8, "height": 8,
        "background": "#101010", "palette": "tokyonight",
        "strokes": [{"kind": "pen", "color": '" /><script>alert(1)</script>',
                     "width": 1.0, "points": [[0.0, 0.0]]}],
    }))
    with pytest.raises(MonolineError):
        load(p)


def test_export_ansi_contains_braille_and_color():
    doc = Document(16, 8)
    doc.add_strokes([Stroke(points=[(0.0, 0.0), (7.0, 0.0)], color="#ff0000")])
    out = export_ansi(doc)
    assert "\x1b[38;2;255;0;0m" in out
    assert "\x1b[0m" in out
    assert any(0x2800 <= ord(ch) <= 0x28FF for ch in out)
    assert len(out.splitlines()) == 2  # 8 dots tall = 2 cell rows


def test_export_ansi_trims_trailing_blanks():
    doc = Document(16, 8)
    doc.add_strokes([Stroke(points=[(0.0, 0.0)], color="#ffffff")])
    line = export_ansi(doc).splitlines()[0]
    assert not line.endswith(" ")


def test_export_svg_structure():
    doc = Document(320, 192, background="#101010")
    doc.add_strokes([
        Stroke(points=[(10.0, 10.0), (50.0, 50.0)], color="#7aa2f7"),
        Stroke(points=[(20.0, 20.0), (30.0, 30.0)], kind="erase", width=6.0),
    ])
    svg = export_svg(doc)
    root = ET.fromstring(svg)
    assert root.get("viewBox") == "0 0 320 192"
    ns = "{http://www.w3.org/2000/svg}"
    rect = root.find(f"{ns}rect")
    assert rect.get("fill") == "#101010"
    lines = root.findall(f"{ns}polyline")
    assert len(lines) == 2
    assert lines[0].get("stroke") == "#7aa2f7"
    assert lines[0].get("stroke-width") == "1.5"
    assert lines[1].get("stroke") == "#101010"  # erase = background color
    assert lines[1].get("stroke-width") == "6.0"
