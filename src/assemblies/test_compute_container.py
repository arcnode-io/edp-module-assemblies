"""Tests for compute_container assembly per Q14-C success criterion.

Q14-C bar:
- Assembly bbox within tolerance of 10ft ISO HC exterior dims
- CG plate's location matches CG_MATING_FRAME (round-trip)
"""

import math

import pytest

from src.assemblies.compute_container import (
    CD_MATING_FRAME,
    CG_MATING_FRAME,
    COMMERCIAL_AC_BOM,
    H_EXT_MM,
    L_EXT_MM,
    W_EXT_MM,
    build_compute_container,
)


def test_compute_container_commercial_ac_bbox() -> None:
    # arrange
    bbox_tolerance_mm = 50.0
    # act
    assy = build_compute_container(variant="commercial-ac")
    bbox = assy.toCompound().BoundingBox()
    # assert — assembly fits within 10ft ISO HC exterior + plate protrusion
    assert abs(bbox.xlen - L_EXT_MM) < bbox_tolerance_mm, f"xlen={bbox.xlen}"
    assert abs(bbox.ylen - W_EXT_MM) < bbox_tolerance_mm, f"ylen={bbox.ylen}"
    assert abs(bbox.zlen - H_EXT_MM) < bbox_tolerance_mm, f"zlen={bbox.zlen}"


def test_cg_plate_placed_at_mating_frame() -> None:
    # arrange
    pos_tolerance_mm = 0.1
    expected_pos = CG_MATING_FRAME.toTuple()[0]  # (x, y, z) tuple
    # act
    assy = build_compute_container(variant="commercial-ac")
    cg = next(c for c in assy.children if c.name == "ARC-PLT-CG")
    actual_pos = cg.loc.toTuple()[0]
    # assert
    for axis, (actual, expected) in enumerate(
        zip(actual_pos, expected_pos, strict=True)
    ):
        assert math.isclose(
            actual, expected, abs_tol=pos_tolerance_mm
        ), f"axis {axis}: actual={actual} expected={expected}"


def test_compute_container_rejects_unsupported_variant() -> None:
    # arrange / act / assert
    with pytest.raises(NotImplementedError, match="commercial-dc"):
        build_compute_container(variant="commercial-dc")  # type: ignore[arg-type]


def test_bom_has_seven_nodes_and_cg_plus_cd_plates() -> None:
    # arrange
    parts_by_id = {p["equipment_id"]: p["qty"] for p in COMMERCIAL_AC_BOM["parts"]}
    plates_by_id = {p["id"]: p["qty"] for p in COMMERCIAL_AC_BOM["plates"]}
    # act / assert — compute container has 2 of 3 plates: CG (+X) + CD (-Y)
    expected_node_qty = 7
    assert parts_by_id["CMP-NODE-001"] == expected_node_qty
    assert plates_by_id == {"CG": 1, "CD": 1}


def test_bom_has_pdus_per_adr_005() -> None:
    # arrange
    parts_by_id = {p["equipment_id"]: p["qty"] for p in COMMERCIAL_AC_BOM["parts"]}
    # act / assert
    expected_pdu_qty = 4  # ADR-005: 4x PDUs per Compute Container = 2N at 80kW
    assert parts_by_id["CMP-PDU-001"] == expected_pdu_qty


def test_exploded_assembly_includes_top_open_container_shell() -> None:
    # arrange / act
    actual = build_compute_container(variant="commercial-ac", exploded=True)
    # assert — shell present (per user: "keep the bounding box to exploded view")
    child_names = {c.name for c in actual.children}
    assert "container_shell" in child_names


def test_normal_assembly_includes_container_shell() -> None:
    # arrange / act
    actual = build_compute_container(variant="commercial-ac", exploded=False)
    # assert
    child_names = {c.name for c in actual.children}
    assert "container_shell" in child_names


def test_exploded_cg_plate_offset_outward_in_x() -> None:
    # arrange
    base_x = CG_MATING_FRAME.toTuple()[0][0]
    # act
    exploded = build_compute_container(variant="commercial-ac", exploded=True)
    cg = next(c for c in exploded.children if c.name == "ARC-PLT-CG")
    actual_x = cg.loc.toTuple()[0][0]
    # assert — explode moves CG plate outward in +X
    assert actual_x > base_x


def test_cd_plate_placed_at_mating_frame() -> None:
    # arrange
    pos_tolerance_mm = 0.1
    expected_pos = CD_MATING_FRAME.toTuple()[0]
    # act
    assy = build_compute_container(variant="commercial-ac")
    cd = next(c for c in assy.children if c.name == "ARC-PLT-CD")
    actual_pos = cd.loc.toTuple()[0]
    # assert
    for axis, (actual, expected) in enumerate(
        zip(actual_pos, expected_pos, strict=True)
    ):
        assert math.isclose(
            actual, expected, abs_tol=pos_tolerance_mm
        ), f"axis {axis}: actual={actual} expected={expected}"


def test_exploded_cd_plate_offset_outward_in_negative_y() -> None:
    # arrange
    base_y = CD_MATING_FRAME.toTuple()[0][1]
    # act
    exploded = build_compute_container(variant="commercial-ac", exploded=True)
    cd = next(c for c in exploded.children if c.name == "ARC-PLT-CD")
    actual_y = cd.loc.toTuple()[0][1]
    # assert — explode pushes CD plate further -Y off the long wall
    assert actual_y < base_y


def test_exploded_nodes_are_staggered_in_z() -> None:
    # arrange / act
    exploded = build_compute_container(variant="commercial-ac", exploded=True)
    nodes = sorted(
        (c for c in exploded.children if c.name.startswith("CMP-NODE-001#")),
        key=lambda c: c.name,
    )
    # assert — each node ends up higher than the previous one
    z_positions = [n.loc.toTuple()[0][2] for n in nodes]
    assert z_positions == sorted(z_positions)
    assert z_positions[-1] > z_positions[0] + 1000  # cumulative stagger ≥ 1m
