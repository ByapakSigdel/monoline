"""Command-line entry point."""
from __future__ import annotations

import argparse

from monoline import __version__


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="monoline",
        description="Aesthetic drawing in your terminal.",
    )
    parser.add_argument("file", nargs="?", default=None,
                        help="a .mono.json file to open or create")
    parser.add_argument("--version", action="version",
                        version=f"monoline {__version__}")
    args = parser.parse_args(argv)
    print("monoline: app not wired yet")  # replaced in Task 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
