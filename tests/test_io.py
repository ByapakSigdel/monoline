import json

import pytest

from monoline.document import Document, Stroke
from monoline.io import MonolineError, load, save


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
