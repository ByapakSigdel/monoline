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
    for f in ("screenshot-drawing.svg", "screenshot-import.svg",
              "screenshot-model3d.svg"):
        p = ASSETS / f
        assert p.exists() and p.stat().st_size > 1000
        assert b"<svg" in p.read_bytes()[:200]


def test_make_gifs():
    run_script("make_gifs.py")
    for f in ("demo-drawing.gif", "demo-import.gif", "demo-model3d.gif"):
        p = ASSETS / f
        assert p.exists() and 1000 < p.stat().st_size < 4 * 1024 * 1024
        assert p.read_bytes()[:6] in (b"GIF87a", b"GIF89a")
