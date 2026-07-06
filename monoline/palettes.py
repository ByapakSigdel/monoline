"""Curated color palettes. 9 colors each, plus background and grid colors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Palette:
    name: str
    background: str
    grid: str
    colors: Tuple[str, ...]


PALETTES = [
    Palette("tokyonight", "#1a1b26", "#292e42", (
        "#c0caf5", "#7aa2f7", "#7dcfff", "#9ece6a", "#bb9af7",
        "#f7768e", "#ff9e64", "#e0af68", "#73daca")),
    Palette("catppuccin", "#1e1e2e", "#313244", (
        "#cdd6f4", "#89b4fa", "#89dceb", "#a6e3a1", "#cba6f7",
        "#f38ba8", "#fab387", "#f9e2af", "#94e2d5")),
    Palette("gruvbox", "#282828", "#3c3836", (
        "#ebdbb2", "#83a598", "#8ec07c", "#b8bb26", "#d3869b",
        "#fb4934", "#fe8019", "#fabd2f", "#d5c4a1")),
    Palette("nord", "#2e3440", "#3b4252", (
        "#eceff4", "#88c0d0", "#81a1c1", "#8fbcbb", "#a3be8c",
        "#b48ead", "#bf616a", "#d08770", "#ebcb8b")),
    Palette("pastel", "#2b2b3a", "#3a3a4c", (
        "#fffffc", "#a0c4ff", "#9bf6ff", "#caffbf", "#bdb2ff",
        "#ffadad", "#ffd6a5", "#fdffb6", "#ffc6ff")),
    Palette("neon", "#0a0a12", "#1c1c2e", (
        "#ffffff", "#00ccff", "#00ffff", "#00ff66", "#cc00ff",
        "#ff0055", "#ff6600", "#ffee00", "#ff00ff")),
    Palette("mono", "#111111", "#222222", (
        "#ffffff", "#e8e8e8", "#d0d0d0", "#b8b8b8", "#a0a0a0",
        "#888888", "#707070", "#585858", "#404040")),
]

_BY_NAME = {p.name: p for p in PALETTES}


def get_palette(name: str) -> Palette:
    return _BY_NAME.get(name, PALETTES[0])
