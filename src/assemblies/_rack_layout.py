"""Rack-internal equipment placement for compute_container assembly.

Stack-based v1 layout: nodes pile up vertically from rack floor; CDU + switch
above; PDUs vertical 0U on rack rails. Rack U-precise positioning lands in
step 6.7 (installation_graph). Exploded mode applies Q3-C offsets per part.
"""

from pathlib import Path
from typing import Final

import cadquery as cq

from src.assemblies import _explode

EQUIPMENT_DIR: Final[Path] = Path(__file__).resolve().parents[2] / "equipment"

NODE_PITCH_MM: Final[float] = 178.0  # 4U
SWITCH_HALF_HEIGHT_MM: Final[float] = 22.0  # half of 1U
PDU_LENGTH_MM: Final[float] = 1778.0
PDU_POSITIONS: Final[list[tuple[float, float]]] = [
    (-350, -300),
    (-350, 300),
    (350, -300),
    (350, 300),
]


def _import_envelope(equipment_id: str) -> cq.Workplane:
    """Import an equipment envelope STEP from equipment/{id}/envelope.step."""
    return cq.importers.importStep(str(EQUIPMENT_DIR / equipment_id / "envelope.step"))


def place_rack_equipment(assy: cq.Assembly, *, exploded: bool = False) -> None:
    """Add nodes + CDU + switch + PDUs to the assembly.

    Args:
        assy: Assembly being populated.
        exploded: If True, apply Q3-C explode offsets per part type.
    """
    node_count = 7
    for i in range(node_count):
        z = NODE_PITCH_MM / 2 + i * NODE_PITCH_MM
        pos = cq.Vector(0, 0, z)
        if exploded:
            pos = pos.add(_explode.node_offset(i))
        assy.add(
            _import_envelope("CMP-NODE-001"),
            name=f"CMP-NODE-001#{i + 1}",
            loc=cq.Location(pos),
            color=cq.Color(0.2, 0.4, 0.7),
        )

    cdu_z = node_count * NODE_PITCH_MM + NODE_PITCH_MM / 2
    cdu_pos = cq.Vector(0, 0, cdu_z)
    if exploded:
        cdu_pos = cdu_pos.add(_explode.cdu_offset(node_count))
    assy.add(
        _import_envelope("CMP-CDU-001"),
        name="CMP-CDU-001",
        loc=cq.Location(cdu_pos),
        color=cq.Color(0.7, 0.7, 0.2),
    )

    switch_pos = cq.Vector(0, 0, cdu_z + NODE_PITCH_MM / 2 + SWITCH_HALF_HEIGHT_MM)
    if exploded:
        switch_pos = switch_pos.add(_explode.switch_offset(node_count))
    assy.add(
        _import_envelope("CMP-SWITCH-001"),
        name="CMP-SWITCH-001",
        loc=cq.Location(switch_pos),
        color=cq.Color(0.4, 0.7, 0.4),
    )

    # PDU envelope is 1778x56x56; rotate 90° so length points up (+Z).
    for i, (x, y) in enumerate(PDU_POSITIONS):
        pos = cq.Vector(x, y, PDU_LENGTH_MM / 2)
        if exploded:
            pos = pos.add(_explode.pdu_offset(1 if y > 0 else -1))
        assy.add(
            _import_envelope("CMP-PDU-001"),
            name=f"CMP-PDU-001#{i + 1}",
            loc=cq.Location(pos, cq.Vector(0, 1, 0), 90),
            color=cq.Color(0.5, 0.2, 0.2),
        )
