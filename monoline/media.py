"""Media path detection for drag-drop and paste imports."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import unquote, urlparse

from monoline.model3d import MODEL_SUFFIXES, is_model_path
from monoline.video import VIDEO_SUFFIXES, is_video_path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
MEDIA_SUFFIXES = IMAGE_SUFFIXES | VIDEO_SUFFIXES | MODEL_SUFFIXES

_BRACE_TOKEN = re.compile(r"\{([^}]+)\}")


def _file_url_to_path(url: str) -> str:
    path = unquote(urlparse(url).path)
    if os.name == "nt" and len(path) >= 3 and path[0] == "/" and path[2] == ":":
        path = path[1:]
    return path


def _normalize_token(token: str) -> str:
    token = token.strip().strip("\x00").strip('"').strip("'").strip("{}").strip()
    if token.lower().startswith("file:"):
        token = _file_url_to_path(token)
    return os.path.normpath(token)


def _extract_tokens(text: str) -> Iterable[str]:
    """Split a paste/drop line into individual path tokens."""
    text = text.strip().strip("\x00")
    if not text:
        return
    if "{" in text:
        matched = False
        for match in _BRACE_TOKEN.finditer(text):
            matched = True
            token = _normalize_token(match.group(1))
            if token:
                yield token
        if matched:
            return
    if ((text.startswith('"') and text.endswith('"'))
            or (text.startswith("'") and text.endswith("'"))):
        yield _normalize_token(text[1:-1])
        return
    yield _normalize_token(text)


def _is_media_file(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in MEDIA_SUFFIXES or is_video_path(path) or is_model_path(path)


def media_path_from_paste(text: str) -> Optional[str]:
    """Extract an image, video, or 3D model path from terminal paste / drag-drop."""
    if not text:
        return None
    if text.strip().lower().startswith("file:"):
        text = _file_url_to_path(text.strip())
    for line in text.splitlines():
        line = line.strip().strip("\x00")
        if not line:
            continue
        for token in _extract_tokens(line):
            if not token:
                continue
            p = Path(token)
            if p.is_file() and _is_media_file(str(p)):
                return str(p)
    return None


def image_path_from_paste(text: str) -> Optional[str]:
    """Extract an image file path (excludes video and 3D model paths)."""
    path = media_path_from_paste(text)
    if path is None or is_video_path(path) or is_model_path(path):
        return None
    return path
