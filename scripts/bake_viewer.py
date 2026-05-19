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
# Reason: the DLR carrier source-of-truth lives in the PCB repo, not in
# edp-module-assemblies/assemblies (it's a board, not a container).
DLR_PCB_OUT: Final[Path] = REPO_ROOT.parent / "dlr-pcb" / "output"


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
    # Reason: `grid.glb` stays pinned to commercial-ac for backward compat with
    # arc-node.html. DC-ext + no-bess variants ship as additional assets the
    # website can reference when it wires variant switching.
    bake_module("grid", ASSEMBLIES_DIR / "grid-container" / "commercial-ac", args.out)
    bake_module(
        "grid-dc-ext",
        ASSEMBLIES_DIR / "grid-container" / "commercial-dc-ext",
        args.out,
    )
    bake_module(
        "grid-no-bess",
        ASSEMBLIES_DIR / "grid-container" / "no-bess",
        args.out,
    )
    bake_module(
        "dlr-carrier",
        DLR_PCB_OUT,
        args.out,
        assembled_name="dlr_carrier_pcb.glb",
        exploded_name="dlr_carrier_pcb-exploded.glb",
    )
    # Field-kit variants (per dlr-pcb project_anemometer_sku.md): same PCB,
    # different sensor body + cable harness + PV + battery in the kit BOM.
    # HW = Calypso ULP STD + 20 W PV + 50 Wh.
    # LW = Vaisala WMT702 + 30 W PV + 100 Wh.
    bake_module(
        "dlr-carrier-hw",
        DLR_PCB_OUT,
        args.out,
        assembled_name="dlr_carrier_kit_hw.glb",
        exploded_name="dlr_carrier_kit_hw-exploded.glb",
    )
    bake_module(
        "dlr-carrier-lw",
        DLR_PCB_OUT,
        args.out,
        assembled_name="dlr_carrier_kit_lw.glb",
        exploded_name="dlr_carrier_kit_lw-exploded.glb",
    )
    bake_hotspots(
        args.out,
        kinds=[
            "compute",
            "grid",
            "grid-dc-ext",
            "grid-no-bess",
            "dlr-carrier",
            "dlr-carrier-hw",
            "dlr-carrier-lw",
        ],
    )


if __name__ == "__main__":
    main()
