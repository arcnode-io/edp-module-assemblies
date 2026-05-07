"""Container shell variants for compute_container assembly.

Kept separate from compute_container.py to stay under the 200-line file
budget. Currently exposes build_shell() only (label code removed —
labels visually cluttered the exploded view).
"""

from typing import Final

import cadquery as cq

L_EXT_MM: Final[float] = 2991.0
W_EXT_MM: Final[float] = 2438.0
H_EXT_MM: Final[float] = 2896.0
SHELL_WALL_THICKNESS_MM: Final[float] = 30.0


def build_shell(*, top_open: bool) -> cq.Workplane:
    """Container shell. If top_open, removes the +Z face (5-sided trough)."""
    box = cq.Workplane("XY").box(L_EXT_MM, W_EXT_MM, H_EXT_MM)
    if not top_open:
        return box
    return box.faces(">Z").shell(-SHELL_WALL_THICKNESS_MM)
