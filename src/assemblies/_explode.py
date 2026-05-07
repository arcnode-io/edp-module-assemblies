"""Explosion offsets for compute_container webview GLB (Q3-C).

Direction-of-installation aware: rack-stack items lift Z with stagger,
PDUs slide outward in Y (the rail-removal direction), CG plate slides
outward in +X (the wall-mount-removal direction). Communicates assembly
order at a glance in the GLB webview.
"""

from typing import Final

import cadquery as cq

NODE_STAGGER_Z_MM: Final[float] = 200.0
CDU_LIFT_Z_MM: Final[float] = 400.0
SWITCH_LIFT_Z_MM: Final[float] = 300.0
PDU_OUTWARD_Y_MM: Final[float] = 400.0
PDU_LIFT_Z_MM: Final[float] = 200.0
CG_PLATE_OUTWARD_X_MM: Final[float] = 500.0


def node_offset(index: int) -> cq.Vector:
    """Per-node Z stagger so each node is visually separable in webview."""
    return cq.Vector(0, 0, (index + 1) * NODE_STAGGER_Z_MM)


def cdu_offset(node_count: int) -> cq.Vector:
    """CDU lifts above the highest exploded node."""
    return cq.Vector(0, 0, node_count * NODE_STAGGER_Z_MM + CDU_LIFT_Z_MM)


def switch_offset(node_count: int) -> cq.Vector:
    """Switch lifts above the exploded CDU."""
    base = node_count * NODE_STAGGER_Z_MM + CDU_LIFT_Z_MM + SWITCH_LIFT_Z_MM
    return cq.Vector(0, 0, base)


def pdu_offset(y_sign: int) -> cq.Vector:
    """PDUs slide outward in Y (the removal direction from rack rails)."""
    return cq.Vector(0, y_sign * PDU_OUTWARD_Y_MM, PDU_LIFT_Z_MM)


def cg_plate_offset() -> cq.Vector:
    """CG plate slides further +X off the end wall."""
    return cq.Vector(CG_PLATE_OUTWARD_X_MM, 0, 0)
