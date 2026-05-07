"""Grid container interior equipment placement.

v1 layout (Q6-B):
- Trihal at -X side, anchored to -Y wall
- SafeGear at +X side, rotated 90° about Z, depth aligned with +Y wall
RLY + MTR are inside SafeGear's LV compartment (Q7-A) — bom-only, no geometry.
"""

from pathlib import Path
from typing import Final

import cadquery as cq

from src.assemblies import _explode

EQUIPMENT_DIR: Final[Path] = Path(__file__).resolve().parents[2] / "equipment"

# Container interior usable dims (per handoff: 2848 x 2235 x 2680 mm).
L_INT_MM: Final[float] = 2848.0
W_INT_MM: Final[float] = 2235.0
H_INT_MM: Final[float] = 2680.0

# Trihal envelope (per spec.yaml — Q2-C used the larger spec value).
XFM_L_MM: Final[float] = 1800.0
XFM_W_MM: Final[float] = 1400.0
XFM_H_MM: Final[float] = 2000.0

# SafeGear envelope (rotated 90° Z so depth=2159 goes along Y).
SWG_L_MM: Final[float] = 2159.0  # depth (Y axis after rotation)
SWG_W_MM: Final[float] = 914.0  # width (X axis after rotation)
SWG_H_MM: Final[float] = 2413.0


def _import_envelope(equipment_id: str) -> cq.Workplane:
    """Import equipment envelope STEP from equipment/{id}/envelope.step."""
    return cq.importers.importStep(str(EQUIPMENT_DIR / equipment_id / "envelope.step"))


def trihal_position() -> cq.Vector:
    """Trihal anchored to -X end + -Y wall, on the floor."""
    x = -(L_INT_MM / 2 - XFM_L_MM / 2)
    y = -(W_INT_MM / 2 - XFM_W_MM / 2)
    z = XFM_H_MM / 2
    return cq.Vector(x, y, z)


def safegear_position() -> cq.Vector:
    """SafeGear anchored to +X end + +Y wall, on the floor.

    SafeGear envelope is in default orientation (L along X). Rotation is
    applied separately at placement to put depth (2159) along Y.
    """
    x = +(L_INT_MM / 2 - SWG_W_MM / 2)
    y = +(W_INT_MM / 2 - SWG_L_MM / 2)
    z = SWG_H_MM / 2
    return cq.Vector(x, y, z)


def place_grid_equipment(assy: cq.Assembly, *, exploded: bool = False) -> None:
    """Add Trihal + SafeGear to assembly. Q8: lift +Z when exploded."""
    xfm_pos = trihal_position()
    if exploded:
        xfm_pos = xfm_pos.add(_explode.xfm_offset())
    assy.add(
        _import_envelope("GRD-XFM-001"),
        name="GRD-XFM-001",
        loc=cq.Location(xfm_pos),
        color=cq.Color(0.5, 0.4, 0.2),
    )

    swg_pos = safegear_position()
    if exploded:
        swg_pos = swg_pos.add(_explode.swg_offset())
    # Reason: rotate 90° Z so SafeGear's spec L=2159 (depth) goes along
    # container Y axis (matches +Y wall front-face orientation per Q6-B).
    assy.add(
        _import_envelope("GRD-SWG-001"),
        name="GRD-SWG-001",
        loc=cq.Location(swg_pos, cq.Vector(0, 0, 1), 90),
        color=cq.Color(0.3, 0.3, 0.5),
    )
