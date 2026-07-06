import subprocess
import sys

from monoline import __version__


def test_version_flag():
    out = subprocess.run(
        [sys.executable, "-m", "monoline.cli", "--version"],
        capture_output=True, text=True,
    )
    assert out.returncode == 0
    assert f"monoline {__version__}" in out.stdout


def test_main_importable():
    from monoline.cli import main
    assert callable(main)
