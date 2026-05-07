"""CLI: bake source assembly GLBs into web-viewer GLBs + hotspot manifest.

Usage:
    uv run python scripts/bake_viewer.py [--out path/to/dir]

Default output: ../website/assets/models/  (sibling website repo)
"""

import argparse
import logging
from pathlib import Path
from typing import Final

from src.viewer_bake.bake import bake_hotspots, bake_module

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
ASSEMBLIES_DIR: Final[Path] = REPO_ROOT / "assemblies"
DEFAULT_OUT: Final[Path] = REPO_ROOT.parent / "website" / "assets" / "models"


def main() -> None:
    """CLI entry: bake compute + grid GLBs and the hotspots manifest."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"output dir (default: {DEFAULT_OUT})",
    )
    args = parser.parse_args()

    bake_module(
        "compute", ASSEMBLIES_DIR / "compute-container" / "commercial-ac", args.out
    )
    bake_module("grid", ASSEMBLIES_DIR / "grid-container" / "commercial-ac", args.out)
    bake_hotspots(args.out)


if __name__ == "__main__":
    main()
