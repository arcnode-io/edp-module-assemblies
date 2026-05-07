"""Tests for grid_container assembly per Q14-C success criterion (step 6.1)."""

import math

import pytest

from src.assemblies.grid_container import (
    BG_AC_MATING_FRAME,
    CG_MATING_FRAME,
    COMMERCIAL_AC_BOM,
    H_EXT_MM,
    L_EXT_MM,
    W_EXT_MM,
    build_grid_container,
)


def test_grid_container_commercial_ac_bbox() -> None:
    # arrange
    bbox_tolerance_mm = 50.0
    # act
    assy = build_grid_container(variant="commercial-ac")
    bbox = assy.toCompound().BoundingBox()
    # assert — assembly fits within 10ft ISO HC exterior + plate protrusion
    assert abs(bbox.xlen - L_EXT_MM) < bbox_tolerance_mm, f"xlen={bbox.xlen}"
    assert abs(bbox.ylen - W_EXT_MM) < bbox_tolerance_mm, f"ylen={bbox.ylen}"
    assert abs(bbox.zlen - H_EXT_MM) < bbox_tolerance_mm, f"zlen={bbox.zlen}"


def test_cg_plate_placed_at_mating_frame() -> None:
    # arrange
    pos_tolerance_mm = 0.1
    expected_pos = CG_MATING_FRAME.toTuple()[0]
    # act
    assy = build_grid_container(variant="commercial-ac")
    cg = next(c for c in assy.children if c.name == "ARC-PLT-CG")
    actual_pos = cg.loc.toTuple()[0]
    # assert — Q14-C: round-trip mating frame position
    for axis, (actual, expected) in enumerate(
        zip(actual_pos, expected_pos, strict=True)
    ):
        assert math.isclose(
            actual, expected, abs_tol=pos_tolerance_mm
        ), f"axis {axis}: actual={actual} expected={expected}"


def test_cg_mating_frame_at_negative_x_end() -> None:
    # arrange / act / assert — grid CG mates with compute at -X end wall
    expected_x = -L_EXT_MM / 2
    actual_x = CG_MATING_FRAME.toTuple()[0][0]
    assert math.isclose(actual_x, expected_x, abs_tol=0.1)


def test_grid_container_rejects_unsupported_variant() -> None:
    # arrange / act / assert
    with pytest.raises(NotImplementedError, match=r"commercial-dc|defense"):
        build_grid_container(variant="commercial-dc")  # type: ignore[arg-type]


def test_bom_has_xfm_and_swg_and_cg_plate() -> None:
    # arrange
    parts_by_id = {p["equipment_id"]: p["qty"] for p in COMMERCIAL_AC_BOM["parts"]}
    plates_by_id = {p["id"]: p["qty"] for p in COMMERCIAL_AC_BOM["plates"]}
    # act / assert
    assert parts_by_id["GRD-XFM-001"] == 1
    assert parts_by_id["GRD-SWG-001"] == 1
    assert parts_by_id["GRD-RLY-001"] == 1
    assert parts_by_id["GRD-MTR-001"] == 1
    assert plates_by_id["CG"] == 1


def test_bom_includes_bg_ac_per_step_6_2() -> None:
    # arrange
    plate_ids = {p["id"] for p in COMMERCIAL_AC_BOM["plates"]}
    # act / assert — step 6.2: BG-AC now in bom; EX-G/EX-C still deferred to 6.3
    assert "BG-AC" in plate_ids
    assert "EX-G" not in plate_ids
    assert "EX-C" not in plate_ids


def test_bg_ac_plate_placed_at_positive_x_end() -> None:
    # arrange — BG-AC at +X end (BESS pad), opposite from CG at -X (compute)
    expected_x = +L_EXT_MM / 2
    actual_x = BG_AC_MATING_FRAME.toTuple()[0][0]
    assert math.isclose(actual_x, expected_x, abs_tol=0.1)


def test_bg_ac_plate_in_assembly() -> None:
    # arrange / act
    assy = build_grid_container(variant="commercial-ac")
    child_names = {c.name for c in assy.children}
    # assert
    assert "ARC-PLT-BG-AC" in child_names


def test_exploded_xfm_lifted_in_z() -> None:
    # arrange
    base = build_grid_container(variant="commercial-ac", exploded=False)
    base_xfm_z = next(
        c for c in base.children if c.name == "GRD-XFM-001"
    ).loc.toTuple()[0][2]
    # act
    exploded = build_grid_container(variant="commercial-ac", exploded=True)
    expl_xfm_z = next(
        c for c in exploded.children if c.name == "GRD-XFM-001"
    ).loc.toTuple()[0][2]
    # assert
    assert expl_xfm_z > base_xfm_z


def test_exploded_cg_plate_offset_outward_in_negative_x() -> None:
    # arrange
    base_x = CG_MATING_FRAME.toTuple()[0][0]
    # act
    exploded = build_grid_container(variant="commercial-ac", exploded=True)
    cg = next(c for c in exploded.children if c.name == "ARC-PLT-CG")
    actual_x = cg.loc.toTuple()[0][0]
    # assert — explode pushes CG plate further in -X (more negative)
    assert actual_x < base_x
