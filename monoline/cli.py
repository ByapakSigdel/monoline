"""Command-line entry point."""
from __future__ import annotations

import argparse
import sys

from monoline import __version__


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="monoline",
        description="Aesthetic drawing in your terminal.",
    )
    parser.add_argument("file", nargs="?", default=None,
                        help="a .mono.json drawing or a media file (.png/.mp4/...) to import")
    parser.add_argument("--version", action="version",
                        version=f"monoline {__version__}")
    args = parser.parse_args(argv)
    from monoline.app import run
    from monoline.io import MonolineError
    try:
        run(args.file)
    except MonolineError as exc:
        print(f"monoline: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
