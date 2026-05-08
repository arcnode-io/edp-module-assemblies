"""compute_container assembly per ADR-007 + Q11-C.

Per-container origin = floor center inside container; X axis points toward
the grid container (+X end wall); Y axis across; Z axis up. Equipment
envelopes imported from `equipment/{id}/envelope.step`; CG plate imported
via `plate_loader.fetch("CG", "v1")`.

Emits `assemblies/compute-container/{variant}/{assembly.step,assembly.glb,bom.yaml}`.

Per ADR-010 step 4 scope: only `commercial-ac` variant for v1; grid container
is treated as a notional mating frame, not built.
"""

import argparse
import logging
from pathlib import Path
from typing import Final, Literal

import cadquery as cq
import yaml

from src import plate_loader
from src.assemblies import _decorations, _explode, _rack_layout

logger = logging.getLogger(__name__)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
EQUIPMENT_DIR: Final[Path] = REPO_ROOT / "equipment"
ASSEMBLIES_DIR: Final[Path] = REPO_ROOT / "assemblies"

# 10ft ISO HC container exterior dimensions (per ADR-004).
# Interior height ~2680mm; length/width slightly less than exterior.
L_EXT_MM: Final[float] = 2991.0
W_EXT_MM: Final[float] = 2438.0
H_EXT_MM: Final[float] = 2896.0

# Plate placement constants on +X end wall (grid-facing).
PLATE_CENTER_Z_MM: Final[float] = H_EXT_MM / 2

# Reason: ADR-007 cross-container coupling — each container exposes its
# mating frames as named cq.Location constants. Grid container will export
# a mirrored CG_MATING_FRAME with normal -X. Deployment-level assembly
# composes containers by aligning frames.
# Rotation -90° about Y rotates the plate from its build pose (normal +Z)
# to face the grid container (normal +X).
CG_MATING_FRAME: Final[cq.Location] = cq.Location(
    cq.Vector(L_EXT_MM / 2, 0.0, PLATE_CENTER_Z_MM),
    cq.Vector(0, 1, 0),
    -90,
)

# Reason: CD plate on -Y long wall (single long-wall plate per 3-plate fleet).
# Plate built normal +Z; rotation -90° about X → normal -Y (outward toward
# external drycooler). Carries secondary cooling loop QDs + drycooler comms.
CD_MATING_FRAME: Final[cq.Location] = cq.Location(
    cq.Vector(0.0, -W_EXT_MM / 2, PLATE_CENTER_Z_MM),
    cq.Vector(1, 0, 0),
    -90,
)

Variant = Literal["commercial-ac"]

# v1 commercial-ac BOM — multiplied by container count downstream by edp-api.
# Per ADR-009: split parts: + plates: sections.
COMMERCIAL_AC_BOM: Final[dict] = {
    "parts": [
        {"equipment_id": "CMP-NODE-001", "qty": 7},
        {"equipment_id": "CMP-RACK-001", "qty": 1},
        {"equipment_id": "CMP-CDU-001", "qty": 1},
        {"equipment_id": "CMP-SWITCH-001", "qty": 1},
        {"equipment_id": "CMP-PDU-001", "qty": 4},  # ADR-005: 2N redundant
    ],
    "plates": [
        {"id": "CG", "version": "v1", "qty": 1},
        {"id": "CD", "version": "v1", "qty": 1},
    ],
}


def _import_envelope(equipment_id: str) -> cq.Workplane:
    """Import an equipment envelope STEP from equipment/{id}/envelope.step."""
    path = EQUIPMENT_DIR / equipment_id / "envelope.step"
    return cq.importers.importStep(str(path))


def build_compute_container(
    variant: Variant = "commercial-ac", *, exploded: bool = False
) -> cq.Assembly:
    """Build the compute_container assembly.

    Args:
        variant: Compute-container variant. Only "commercial-ac" supported in v1.
        exploded: If True, omit container shell and apply Q3-C explode offsets.
            Used for the webview GLB artifact.

    Returns:
        CadQuery Assembly with equipment envelopes + CG plate (+ container
        shell when not exploded).

    Raises:
        NotImplementedError: For unsupported variants.
    """
    if variant != "commercial-ac":
        raise NotImplementedError(
            f"variant={variant!r} not supported in v1; only 'commercial-ac'. "
            "Per ADR-010 commercial-dc is assumed identical pending step 6.8."
        )

    suffix = "-exploded" if exploded else ""
    assy = cq.Assembly(name=f"compute_container_{variant}{suffix}")

    shell = _decorations.build_shell(top_open=exploded)
    assy.add(
        shell,
        name="container_shell",
        loc=cq.Location(cq.Vector(0, 0, H_EXT_MM / 2)),
        color=cq.Color(0.85, 0.85, 0.85, 0.15),
    )

    rack_height_mm = 2477.0
    rack_color = cq.Color(0.3, 0.3, 0.3, 0.25) if exploded else cq.Color(0.3, 0.3, 0.3)
    assy.add(
        _import_envelope("CMP-RACK-001"),
        name="CMP-RACK-001",
        loc=cq.Location(cq.Vector(0, 0, rack_height_mm / 2)),
        color=rack_color,
    )

    _rack_layout.place_rack_equipment(assy, exploded=exploded)

    cg_plate_step = plate_loader.fetch("CG", "v1")
    cg_plate = cq.importers.importStep(str(cg_plate_step))
    cg_loc = CG_MATING_FRAME
    if exploded:
        # Rebuild mating frame translated outward in +X (the wall-removal direction).
        base_pos = cq.Vector(*CG_MATING_FRAME.toTuple()[0])
        cg_loc = cq.Location(
            base_pos + _explode.cg_plate_offset(),
            cq.Vector(0, 1, 0),
            -90,
        )
    assy.add(cg_plate, name="ARC-PLT-CG", loc=cg_loc, color=cq.Color(0.6, 0.6, 0.7))

    cd_step = plate_loader.fetch("CD", "v1")
    cd_plate = cq.importers.importStep(str(cd_step))
    cd_loc = CD_MATING_FRAME
    if exploded:
        base_pos = cq.Vector(*CD_MATING_FRAME.toTuple()[0])
        cd_loc = cq.Location(
            base_pos + _explode.cd_plate_offset(),
            cq.Vector(1, 0, 0),
            -90,
        )
    assy.add(cd_plate, name="ARC-PLT-CD", loc=cd_loc, color=cq.Color(0.4, 0.6, 0.5))

    return assy


def emit_artifacts(
    assy: cq.Assembly, variant: Variant, exploded_assy: cq.Assembly | None = None
) -> dict[str, Path]:
    """Write assembly artifacts to assemblies/{type}/{variant}/.

    Always writes assembly.step + assembly.glb + bom.yaml. When
    exploded_assy is provided, also writes assembly-exploded.glb (Q3-C
    webview artifact — no shell, parts moved along installation axes).
    """
    out_dir = ASSEMBLIES_DIR / "compute-container" / variant
    out_dir.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {
        "step": out_dir / "assembly.step",
        "glb": out_dir / "assembly.glb",
        "bom": out_dir / "bom.yaml",
    }
    assy.export(str(paths["step"]))
    assy.export(str(paths["glb"]))
    paths["bom"].write_text(yaml.safe_dump(COMMERCIAL_AC_BOM, sort_keys=False))

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
    assy = build_compute_container(args.variant)
    exploded = build_compute_container(args.variant, exploded=True)
    artifacts = emit_artifacts(assy, args.variant, exploded_assy=exploded)
    for kind, path in artifacts.items():
        logger.info(f"  → {kind}: {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
