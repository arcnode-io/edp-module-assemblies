"""Container shell variants — compute and grid containers.

Kept separate from container build modules to stay under the 200-line file
budget. Exposes build_shell() (compute, plain box) and build_grid_shell()
(grid, with louvers + side door cuts per Q5).
"""

from typing import Final

import cadquery as cq

L_EXT_MM: Final[float] = 2991.0
W_EXT_MM: Final[float] = 2438.0
H_EXT_MM: Final[float] = 2896.0
SHELL_WALL_THICKNESS_MM: Final[float] = 30.0

# Grid shell features (Q5)
LOUVER_W_MM: Final[float] = 600.0
LOUVER_H_MM: Final[float] = 600.0
LOUVER_PER_LONG_WALL: Final[int] = 2
DOOR_W_MM: Final[float] = 800.0
DOOR_H_MM: Final[float] = 2030.0


def build_shell(*, top_open: bool) -> cq.Workplane:
    """Compute container shell. If top_open, removes the +Z face."""
    box = cq.Workplane("XY").box(L_EXT_MM, W_EXT_MM, H_EXT_MM)
    if not top_open:
        return box
    return box.faces(">Z").shell(-SHELL_WALL_THICKNESS_MM)


def build_grid_shell(*, top_open: bool, safegear_x: float = 0.0) -> cq.Workplane:
    """Grid container shell with louver + side door cuts per Q5.

    Args:
        top_open: If True, removes the +Z face (exploded variant).
        safegear_x: X coordinate of SafeGear center; door is centered on
            this so the door faces SafeGear's front (+Y) face.

    Returns:
        Shell with 4 louver cutouts (long walls) + 1 side door cutout (+Y wall).
    """
    shell = cq.Workplane("XY").box(L_EXT_MM, W_EXT_MM, H_EXT_MM)
    if top_open:
        shell = shell.faces(">Z").shell(-SHELL_WALL_THICKNESS_MM)

    # Reason: louvers on each long wall, distributed along X. Cut all the
    # way through wall thickness using a generous extrusion depth.
    cut_depth_mm = SHELL_WALL_THICKNESS_MM * 4
    louver_z = H_EXT_MM / 2  # vertical center on the wall

    for x_frac in (-0.3, 0.3):
        x = x_frac * L_EXT_MM
        for y_sign in (-1, 1):
            louver_cut = (
                cq.Workplane("XZ")
                .center(x, louver_z)
                .rect(LOUVER_W_MM, LOUVER_H_MM)
                .extrude(cut_depth_mm * y_sign)
                .translate((0, y_sign * W_EXT_MM / 2, 0))
            )
            shell = shell.cut(louver_cut)

    # Side door in +Y wall, aligned with SafeGear
    door_z = DOOR_H_MM / 2  # door starts at floor; center at half height
    door_cut = (
        cq.Workplane("XZ")
        .center(safegear_x, door_z)
        .rect(DOOR_W_MM, DOOR_H_MM)
        .extrude(cut_depth_mm)
        .translate((0, W_EXT_MM / 2, 0))
    )
    shell = shell.cut(door_cut)

    return shell
