"""Volumetric interference + containment checks on built assemblies.

Every equipment child of an assembly is turned into its placed solid
(envelope moved by the child's Location). The shell and the interface
plates sit in the walls, so they're left out. Rack-mounted gear (CMP-*
except the rack) lives inside CMP-RACK-001 by design: it's checked against
other rack gear and for containment in the rack, never against the rack.
"""

from dataclasses import dataclass
from itertools import combinations
from typing import Final

import cadquery as cq

RACK: Final[str] = "CMP-RACK-001"
_SKIP_PREFIXES: Final[tuple[str, ...]] = ("container_shell", "ARC-PLT-")
# Reason: OCCT booleans on touching faces can leave sliver volumes; anything
# under 1 mm³ is numerical noise, not a clash.
_MIN_OVERLAP_MM3: Final[float] = 1.0
_TOL_MM: Final[float] = 0.01

# (xmin, ymin, zmin, xmax, ymax, zmax) in mm
Bounds = tuple[float, float, float, float, float, float]


@dataclass(frozen=True)
class Interior:
    """Container interior: floor-centered box, z from the floor up (mm)."""

    length: float
    width: float
    height: float


def interferences(assy: cq.Assembly) -> list[tuple[str, str, float]]:
    """(a, b, overlap mm³) for every pair of equipment sharing space."""
    solids = _equipment(assy)
    clashes = []
    for (a, sa), (b, sb) in combinations(sorted(solids.items()), 2):
        if RACK in (a, b) and (_rack_mounted(a) or _rack_mounted(b)):
            continue
        volume = sa.intersect(sb).Volume()
        if volume > _MIN_OVERLAP_MM3:
            clashes.append((a, b, round(volume)))
    return clashes


def outside_interior(assy: cq.Assembly, interior: Interior) -> list[str]:
    """Equipment whose envelope pokes outside the container interior."""
    half_l, half_w = interior.length / 2, interior.width / 2
    bounds = (-half_l, -half_w, 0.0, half_l, half_w, interior.height)
    return _not_within(_equipment(assy), bounds)


def outside_rack(assy: cq.Assembly) -> list[str]:
    """Rack-mounted gear whose envelope pokes outside the rack."""
    solids = _equipment(assy)
    rack = _bounds(solids[RACK])
    return _not_within({n: s for n, s in solids.items() if _rack_mounted(n)}, rack)


def _equipment(assy: cq.Assembly) -> dict[str, cq.Shape]:
    """Placed solid per equipment child."""
    return {
        child.name: cq.Compound.makeCompound(child.obj.solids().vals()).moved(child.loc)
        for child in assy.children
        if not child.name.startswith(_SKIP_PREFIXES)
    }


def _rack_mounted(name: str) -> bool:
    return name.startswith("CMP-") and name != RACK


def _bounds(shape: cq.Shape) -> Bounds:
    bb = shape.BoundingBox()
    return (bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax)


def _not_within(solids: dict[str, cq.Shape], outer: Bounds) -> list[str]:
    return sorted(
        name for name, solid in solids.items() if not _within(_bounds(solid), outer)
    )


def _within(inner: Bounds, outer: Bounds) -> bool:
    mins_ok = all(i >= o - _TOL_MM for i, o in zip(inner[:3], outer[:3], strict=True))
    maxs_ok = all(i <= o + _TOL_MM for i, o in zip(inner[3:], outer[3:], strict=True))
    return mins_ok and maxs_ok
