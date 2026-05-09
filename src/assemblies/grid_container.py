"""grid_container assembly per ADR-007 + Q11-C.

Per-container origin = floor center; X axis points toward compute container
(-X end wall mates compute via CG plate); Y axis across; Z axis up. Equipment
envelopes from equipment/{id}/envelope.step. Plates via plate_loader.

Emits assemblies/grid-container/{variant}/{assembly.step,assembly.glb,bom.yaml}
plus -exploded.{step,glb} per Q8.

Variants:
- commercial-ac: CG (-X) + BG-AC (+X). BESS lands AC at grid wall.
- no-bess: CG (-X) only. No BESS connection; utility tie-in routes
  through SafeGear's standard service entrance fitting (no ARCNODE
  plate needed at +X end). Compute container connects directly to
  utility-fed switchgear.
"""

import argparse
import logging
from pathlib import Path
from typing import Final, Literal

import cadquery as cq
import yaml

from src import plate_loader
from src.assemblies import _decorations, _explode, _grid_layout

logger = logging.getLogger(__name__)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
ASSEMBLIES_DIR: Final[Path] = REPO_ROOT / "assemblies"

L_EXT_MM: Final[float] = 2991.0
W_EXT_MM: Final[float] = 2438.0
H_EXT_MM: Final[float] = 2896.0

PLATE_CENTER_Z_MM: Final[float] = H_EXT_MM / 2

# Reason: Q4 — mirror of compute container's CG_MATING_FRAME.
# Compute uses +L/2 with -90° about Y (normal +X). Grid uses -L/2 with
# +90° about Y (normal -X). When deployment composes the two, plate
# normals oppose across the flexible-assembly gap.
CG_MATING_FRAME: Final[cq.Location] = cq.Location(
    cq.Vector(-L_EXT_MM / 2, 0.0, PLATE_CENTER_Z_MM),
    cq.Vector(0, 1, 0),
    +90,
)

# Reason: BG-AC plate at +X end (BESS-facing). Plate built normal +Z;
# rotation -90° about Y → normal +X (away from grid, toward BESS pad).
BG_AC_MATING_FRAME: Final[cq.Location] = cq.Location(
    cq.Vector(+L_EXT_MM / 2, 0.0, PLATE_CENTER_Z_MM),
    cq.Vector(0, 1, 0),
    -90,
)

Variant = Literal["commercial-ac", "no-bess"]

# Reason: hardware doesn't change between commercial-ac and no-bess —
# transformer + switchgear + relay + meter are needed for utility tie-in
# regardless of whether BESS is present. Only the +X end plate differs.
_PARTS: Final[list[dict]] = [
    {"equipment_id": "GRD-XFM-001", "qty": 1},
    {"equipment_id": "GRD-SWG-001", "qty": 1},
    {"equipment_id": "GRD-RLY-001", "qty": 1},  # in SafeGear LV (Q7-A)
    {"equipment_id": "GRD-MTR-001", "qty": 1},  # panel mount on SafeGear (Q7-A)
]

COMMERCIAL_AC_BOM: Final[dict] = {
    "parts": _PARTS,
    "plates": [
        {"id": "CG", "version": "v1", "qty": 1},
        {"id": "BG-AC", "version": "v1", "qty": 1},
    ],
}

NO_BESS_BOM: Final[dict] = {
    "parts": _PARTS,
    "plates": [
        {"id": "CG", "version": "v1", "qty": 1},
    ],
}

BOM_BY_VARIANT: Final[dict[str, dict]] = {
    "commercial-ac": COMMERCIAL_AC_BOM,
    "no-bess": NO_BESS_BOM,
}


def build_grid_container(
    variant: Variant = "commercial-ac", *, exploded: bool = False
) -> cq.Assembly:
    """Build the grid_container assembly.

    Args:
        variant: Grid container variant — "commercial-ac" or "no-bess".
        exploded: If True, top-open shell + Q8 explode offsets.

    Returns:
        CadQuery Assembly with shell + Trihal + SafeGear + plates.

    Raises:
        NotImplementedError: For unsupported variants.
    """
    if variant not in BOM_BY_VARIANT:
        raise NotImplementedError(
            f"variant={variant!r} not supported. Available: {sorted(BOM_BY_VARIANT)}"
        )

    suffix = "-exploded" if exploded else ""
    assy = cq.Assembly(name=f"grid_container_{variant}{suffix}")

    # Shell with louver + side door cuts (Q5). Door X = SafeGear X.
    safegear_x = _grid_layout.safegear_position().x
    shell = _decorations.build_grid_shell(top_open=exploded, safegear_x=safegear_x)
    assy.add(
        shell,
        name="container_shell",
        loc=cq.Location(cq.Vector(0, 0, H_EXT_MM / 2)),
        color=cq.Color(0.85, 0.85, 0.85, 0.15),
    )

    _grid_layout.place_grid_equipment(assy, exploded=exploded)

    _add_plates(assy, variant=variant, exploded=exploded)
    return assy


def _add_plates(assy: cq.Assembly, *, variant: Variant, exploded: bool) -> None:
    """Place CG (always) + BG-AC (commercial-ac only)."""
    cg_plate = cq.importers.importStep(str(plate_loader.fetch("CG", "v1")))
    cg_loc = CG_MATING_FRAME
    if exploded:
        base = cq.Vector(*CG_MATING_FRAME.toTuple()[0])
        cg_loc = cq.Location(
            base + _explode.cg_plate_grid_offset(), cq.Vector(0, 1, 0), +90
        )
    assy.add(cg_plate, name="ARC-PLT-CG", loc=cg_loc, color=cq.Color(0.6, 0.6, 0.7))

    if variant == "commercial-ac":
        bg_plate = cq.importers.importStep(str(plate_loader.fetch("BG-AC", "v1")))
        bg_loc = BG_AC_MATING_FRAME
        if exploded:
            base = cq.Vector(*BG_AC_MATING_FRAME.toTuple()[0])
            bg_loc = cq.Location(
                base + _explode.bg_ac_plate_offset(), cq.Vector(0, 1, 0), -90
            )
        assy.add(
            bg_plate, name="ARC-PLT-BG-AC", loc=bg_loc, color=cq.Color(0.7, 0.5, 0.3)
        )


def emit_artifacts(
    assy: cq.Assembly, variant: Variant, exploded_assy: cq.Assembly | None = None
) -> dict[str, Path]:
    """Write artifacts to assemblies/grid-container/{variant}/."""
    out_dir = ASSEMBLIES_DIR / "grid-container" / variant
    out_dir.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {
        "step": out_dir / "assembly.step",
        "glb": out_dir / "assembly.glb",
        "bom": out_dir / "bom.yaml",
    }
    assy.export(str(paths["step"]))
    assy.export(str(paths["glb"]))
    paths["bom"].write_text(yaml.safe_dump(BOM_BY_VARIANT[variant], sort_keys=False))

    if exploded_assy is not None:
        paths["glb_exploded"] = out_dir / "assembly-exploded.glb"
        paths["step_exploded"] = out_dir / "assembly-exploded.step"
        exploded_assy.export(str(paths["glb_exploded"]))
        exploded_assy.export(str(paths["step_exploded"]))

    return paths


def main() -> None:
    """CLI entry: build assembly + exploded twin, write artifacts."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", default="commercial-ac")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    assy = build_grid_container(args.variant)
    exploded = build_grid_container(args.variant, exploded=True)
    artifacts = emit_artifacts(assy, args.variant, exploded_assy=exploded)
    for kind, path in artifacts.items():
        logger.info(f"  → {kind}: {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
