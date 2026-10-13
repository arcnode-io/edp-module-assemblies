"""grid_container assembly per ADR-007 + Q11-C.

Per-container origin = floor center; X axis points toward compute container
(-X end wall mates compute via CG plate); Y axis across; Z axis up. Equipment
envelopes from equipment/{id}/envelope.step. Plates via plate_loader.

Emits assemblies/grid-container/{variant}/{assembly.step,assembly.glb,bom.yaml}
plus -exploded.{step,glb} per Q8.

Variants:
- commercial-ac: CG (-X) only. AC batteries tie in at 13.8 kV outside the
  container (ADR-016).
- commercial-dc-ext: CG (-X) + BG-AC (+X). The PCS pair (2x PD500, 834 kW
  at 415 V) sits on the battery pad and feeds AC in through BG-AC (ADR-022);
  it's on this BOM because ARCNODE supplies it.
- feeder: commercial-ac minus the POI meter. Sites past one transformer add
  N-1 of these beside the primary; a site has one POI, so one meter.
- dc-ext-feeder: commercial-dc-ext minus the POI meter (keeps its PCS pair
  + BG-AC, since each container takes its own share of the battery).
- defense-ac / defense-feeder: same equipment as the
  commercial counterpart but plates are 5083-H116 marine grade, 10 mm
  thick, with hard anodize + EPDM secondary seal. Plate fetcher pulls
  the -defense.step artifact via deployment_context="defense_forward".
"""

import argparse
import logging
from pathlib import Path
from typing import Final, Literal

import cadquery as cq
import yaml

from src import plate_loader
from src.assemblies.equipment_list import GRID, bom_parts, write_topology
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

# Reason: BG-AC plate at +X end (battery-pad wall) on the dc-ext variants.
# Plate built normal +Z; rotation -90° about Y → normal +X.
BG_MATING_FRAME: Final[cq.Location] = cq.Location(
    cq.Vector(+L_EXT_MM / 2, 0.0, PLATE_CENTER_Z_MM),
    cq.Vector(0, 1, 0),
    -90,
)

Variant = Literal[
    "commercial-ac",
    "commercial-dc-ext",
    "defense-ac",
    "feeder",
    "defense-feeder",
    "dc-ext-feeder",
]

# Reason: built-to-order line, like the plates. The box vendor comes from an
# RFQ against these requirements; nobody sells this shell off the shelf.
SHELL: Final[dict] = {
    "part_number": "ARC-CNT-GRD-001",
    "description": (
        f"Grid container shell: new-build 10ft ISO high-cube, {L_EXT_MM:.0f} x {W_EXT_MM:.0f} x {H_EXT_MM:.0f} mm exterior, "
        "2,680 mm interior height (ADR-004). CSC-plated and rated to lift loaded, "
        "so not cut down from a 20ft. ARCNODE cuts the plate penetrations and louvers."
    ),
}

# Parts are each variant's equipment list counted (equipment_list.py), so
# the BOM and topology.yaml come from one source.
_CG_ONLY: Final[list[dict]] = [{"id": "CG", "version": "v1", "qty": 1}]
# ADR-022: the dc-ext PCS pair's 415 V AC comes in through BG-AC
_CG_AND_BG: Final[list[dict]] = [*_CG_ONLY, {"id": "BG-AC", "version": "v1", "qty": 1}]

COMMERCIAL_AC_BOM: Final[dict] = {
    "shell": SHELL,
    "parts": bom_parts(GRID["commercial-ac"]),
    "plates": _CG_ONLY,
}
COMMERCIAL_DC_EXT_BOM: Final[dict] = {
    "shell": SHELL,
    "parts": bom_parts(GRID["commercial-dc-ext"]),
    "plates": _CG_AND_BG,
}
FEEDER_BOM: Final[dict] = {
    "shell": SHELL,
    "parts": bom_parts(GRID["feeder"]),
    "plates": _CG_ONLY,
}
DC_EXT_FEEDER_BOM: Final[dict] = {
    "shell": SHELL,
    "parts": bom_parts(GRID["dc-ext-feeder"]),
    "plates": _CG_AND_BG,
}

# Reason: defense variants share equipment + plate IDs with their commercial
# counterparts; the difference is the deployment_context flag at the BOM root,
# which routes plate_loader.fetch to the -defense.step artifacts (5083-H116
# marine grade, 10 mm). Defense is AC only: our DC batteries are CATL
# (DOD 1260H), and edp-api rejects federal + either DC coupling at ingress.
DEFENSE_AC_BOM: Final[dict] = {
    **COMMERCIAL_AC_BOM,
    "deployment_context": "defense_forward",
}
DEFENSE_FEEDER_BOM: Final[dict] = {
    **FEEDER_BOM,
    "deployment_context": "defense_forward",
}

BOM_BY_VARIANT: Final[dict[str, dict]] = {
    "commercial-ac": COMMERCIAL_AC_BOM,
    "commercial-dc-ext": COMMERCIAL_DC_EXT_BOM,
    "defense-ac": DEFENSE_AC_BOM,
    "feeder": FEEDER_BOM,
    "defense-feeder": DEFENSE_FEEDER_BOM,
    "dc-ext-feeder": DC_EXT_FEEDER_BOM,
}

# Reason: which BG plate goes at the +X end. Only dc-ext takes battery
# power into the container, as PCS AC through BG-AC (ADR-016, ADR-022).
_BG_PLATE_BY_VARIANT: Final[dict[str, str | None]] = {
    "commercial-ac": None,
    "commercial-dc-ext": "BG-AC",
    "defense-ac": None,
    "feeder": None,
    "defense-feeder": None,
    "dc-ext-feeder": "BG-AC",
}


def _deployment_context_for(variant: str) -> str:
    """Map variant name prefix to the plate-fetch deployment_context."""
    return "defense_forward" if variant.startswith("defense-") else "commercial"


def build_grid_container(
    variant: Variant = "commercial-ac", *, exploded: bool = False
) -> cq.Assembly:
    """Build the grid_container assembly.

    Args:
        variant: Grid container variant, a key of BOM_BY_VARIANT.
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
    shell = _decorations.build_grid_shell(
        top_open=exploded,
        safegear_x=safegear_x,
        switchboard_x=_grid_layout.lv_switchboard_position().x,
    )
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
    """Place CG (always) + BG-AC (dc-ext variants only).

    Defense variants pull -defense.step artifacts via plate_loader's
    deployment_context arg; commercial variants pull plate.step.
    """
    deployment_context = _deployment_context_for(variant)
    cg_plate = cq.importers.importStep(
        str(plate_loader.fetch("CG", "v1", deployment_context))
    )
    cg_loc = CG_MATING_FRAME
    if exploded:
        base = cq.Vector(*CG_MATING_FRAME.toTuple()[0])
        cg_loc = cq.Location(
            base + _explode.cg_plate_grid_offset(), cq.Vector(0, 1, 0), +90
        )
    assy.add(cg_plate, name="ARC-PLT-CG", loc=cg_loc, color=cq.Color(0.6, 0.6, 0.7))

    bg_plate_id = _BG_PLATE_BY_VARIANT[variant]
    if bg_plate_id is not None:
        bg_plate = cq.importers.importStep(
            str(plate_loader.fetch(bg_plate_id, "v1", deployment_context))
        )
        bg_loc = BG_MATING_FRAME
        if exploded:
            base = cq.Vector(*BG_MATING_FRAME.toTuple()[0])
            bg_loc = cq.Location(
                base + _explode.bg_plate_offset(), cq.Vector(0, 1, 0), -90
            )
        assy.add(
            bg_plate,
            name=f"ARC-PLT-{bg_plate_id}",
            loc=bg_loc,
            color=cq.Color(0.7, 0.5, 0.3),
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
    write_topology(GRID[variant], out_dir / "topology.yaml")

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
