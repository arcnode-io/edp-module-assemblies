"""Volumetric check: no two pieces of equipment share space, all fit inside.

Envelopes are real solids placed exactly as the assemblies place them; any
intersection with volume > 1 mm³ fails. Rack-mounted gear is checked
against each other and for containment in the rack, not against the rack.
"""

import cadquery as cq
import pytest

from src.assemblies._grid_layout import H_INT_MM, L_INT_MM, W_INT_MM
from src.assemblies._interference import (
    Interior,
    interferences,
    outside_interior,
    outside_rack,
)
from src.assemblies.compute_container import build_compute_container
from src.assemblies.grid_container import BOM_BY_VARIANT, build_grid_container

INTERIOR = Interior(length=L_INT_MM, width=W_INT_MM, height=H_INT_MM)


@pytest.mark.parametrize("variant", sorted(BOM_BY_VARIANT))
def test_grid_equipment_does_not_overlap(variant: str) -> None:
    # Act
    actual = interferences(build_grid_container(variant))

    # Assert
    assert actual == []


@pytest.mark.parametrize("variant", sorted(BOM_BY_VARIANT))
def test_grid_equipment_fits_inside_the_container(variant: str) -> None:
    # Act
    actual = outside_interior(build_grid_container(variant), INTERIOR)

    # Assert
    assert actual == []


@pytest.mark.parametrize("variant", ["commercial-ac", "defense-ac"])
def test_compute_equipment_does_not_overlap_and_fits(variant: str) -> None:
    # Arrange
    assy = build_compute_container(variant)

    # Act
    actual = (
        interferences(assy),
        outside_interior(assy, INTERIOR),
        outside_rack(assy),
    )

    # Assert
    assert actual == ([], [], [])


def test_the_check_catches_a_clash_and_an_escape() -> None:
    # Arrange — two 100 mm cubes overlapping by 50 mm in x; the second also
    # pokes 50 mm through the floor
    assy = cq.Assembly(name="probe")
    cube = cq.Workplane().box(100, 100, 100)
    assy.add(cube, name="A", loc=cq.Location(cq.Vector(0, 0, 50)))
    assy.add(cube, name="B", loc=cq.Location(cq.Vector(50, 0, 0)))

    # Act
    actual = (interferences(assy), outside_interior(assy, INTERIOR))

    # Assert — overlap is 50 x 100 x 50 mm
    assert actual == ([("A", "B", 250_000)], ["B"])
