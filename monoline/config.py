"""User configuration (TOML). Pure — no TUI imports."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_config_dir

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

DEFAULT_TOML = '''# monoline configuration
shape_correct = "ctrl"   # ctrl | always | off
palette = "tokyonight"   # see README for the palette list
smoothing = 0.5           # 0.0 - 1.0
'''


@dataclass
class Config:
    shape_correct: str = "ctrl"
    palette: str = "tokyonight"
    smoothing: float = 0.5


def config_path() -> Path:
    return Path(user_config_dir("monoline")) / "config.toml"


def load_config(path: Path | None = None) -> Config:
    p = path or config_path()
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(DEFAULT_TOML, encoding="utf-8")
        return Config()
    try:
        data = tomllib.loads(p.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError, ValueError):
        return Config()
    cfg = Config()
    sc = data.get("shape_correct")
    if sc in ("ctrl", "always", "off"):
        cfg.shape_correct = sc
    pal = data.get("palette")
    if isinstance(pal, str) and pal:
        cfg.palette = pal
    sm = data.get("smoothing")
    if isinstance(sm, (int, float)) and 0.0 <= sm <= 1.0:
        cfg.smoothing = float(sm)
    return cfg
