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

# Grid container explode offsets (Q8)
XFM_LIFT_Z_MM: Final[float] = 600.0  # Trihal lifts off floor
SWG_LIFT_Z_MM: Final[float] = (
    1200.0  # SafeGear lifts higher (tall, distinct from Trihal)
)


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
    """CG plate slides further +X off the end wall (compute side)."""
    return cq.Vector(CG_PLATE_OUTWARD_X_MM, 0, 0)


def cg_plate_grid_offset() -> cq.Vector:
    """CG plate slides further -X off the grid container's -X end wall."""
    return cq.Vector(-CG_PLATE_OUTWARD_X_MM, 0, 0)


def bg_ac_plate_offset() -> cq.Vector:
    """BG-AC plate slides further +X off the grid container's +X end wall."""
    return cq.Vector(CG_PLATE_OUTWARD_X_MM, 0, 0)


def cd_plate_offset() -> cq.Vector:
    """CD plate slides further -Y off the compute container's -Y long wall."""
    return cq.Vector(0, -CG_PLATE_OUTWARD_X_MM, 0)


def xfm_offset() -> cq.Vector:
    """Trihal lifts +Z off the container floor in exploded view."""
    return cq.Vector(0, 0, XFM_LIFT_Z_MM)


def swg_offset() -> cq.Vector:
    """SafeGear lifts +Z off the container floor in exploded view."""
    return cq.Vector(0, 0, SWG_LIFT_Z_MM)
