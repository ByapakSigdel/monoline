import os
from pathlib import Path

import pytest

from monoline.media import image_path_from_paste, media_path_from_paste


@pytest.fixture
def obj(tmp_path):
    p = tmp_path / "shape.obj"
    p.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n", encoding="utf-8")
    return str(p)


def test_media_path_plain(obj):
    assert media_path_from_paste(obj) == obj


def test_media_path_quoted(obj):
    assert media_path_from_paste(f'"{obj}"') == obj


def test_media_path_file_url(obj):
    assert media_path_from_paste(Path(obj).as_uri()) == obj


def test_media_path_brace_wrapped(obj):
    assert media_path_from_paste("{" + obj + "}") == obj


def test_media_path_brace_wrapped_multiple(obj, tmp_path):
    other = tmp_path / "other.stl"
    other.write_bytes(b"solid x\nendsolid x\n")
    text = "{" + obj + "} {" + str(other) + "}"
    assert media_path_from_paste(text) == obj


def test_media_path_ignores_non_media(tmp_path):
    p = tmp_path / "notes.txt"
    p.write_text("hello", encoding="utf-8")
    assert media_path_from_paste(str(p)) is None


def test_image_path_excludes_model(obj):
    assert image_path_from_paste(obj) is None


def test_media_path_windows_slashes(obj):
    assert media_path_from_paste(obj.replace(os.sep, "/")) == obj
