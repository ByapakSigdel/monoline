"""Video frame extraction and braille conversion. Pure — no TUI imports."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from monoline.bitmap import Bitmap
from monoline.imageconv import convert

VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v"}


def is_animated_gif(path: str) -> bool:
    with Image.open(path) as img:
        return bool(getattr(img, "n_frames", 1) > 1)


def is_video_path(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    if suffix in VIDEO_SUFFIXES:
        return True
    return suffix == ".gif" and is_animated_gif(path)


class VideoPlayer:
    """Reads video frames on demand and converts them to bitmaps."""

    def __init__(self, path: str, dot_w: int, dot_h: int, background: str) -> None:
        import imageio.v3 as iio

        self.path = path
        self.dot_w = dot_w
        self.dot_h = dot_h
        self.background = background
        meta = iio.immeta(path, exclude_applied=False)
        fps = meta.get("fps") or 24.0
        self.fps = max(float(fps), 1.0)
        self._index = 0

    def next_bitmap(self) -> Bitmap:
        import imageio.v3 as iio
        import numpy as np

        try:
            frame = iio.imread(self.path, index=self._index)
        except (IndexError, StopIteration, ValueError, EOFError):
            self._index = 0
            frame = iio.imread(self.path, index=0)
        self._index += 1

        arr = np.asarray(frame)
        if arr.ndim == 2:
            img = Image.fromarray(arr).convert("RGB")
        elif arr.shape[-1] >= 3:
            img = Image.fromarray(arr[..., :3])
        else:
            img = Image.fromarray(arr).convert("RGB")
        return convert(img, self.dot_w, self.dot_h, self.background)
