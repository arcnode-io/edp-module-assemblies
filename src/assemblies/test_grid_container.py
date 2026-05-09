"""Tests for grid_container assembly per Q14-C success criterion (step 6.1)."""

import math

import pytest

from src.assemblies.grid_container import (
    BG_MATING_FRAME,
    CG_MATING_FRAME,
    COMMERCIAL_AC_BOM,
    COMMERCIAL_DC_EXT_BOM,
    H_EXT_MM,
    L_EXT_MM,
    NO_BESS_BOM,
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
    # arrange / act / assert — defense variants land in step 6.9
    with pytest.raises(NotImplementedError, match=r"defense"):
        build_grid_container(variant="defense-ac")  # type: ignore[arg-type]


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


def test_bom_plates_match_4_plate_fleet() -> None:
    # arrange
    plate_ids = {p["id"] for p in COMMERCIAL_AC_BOM["plates"]}
    # act / assert — commercial-ac grid container has 2 plates: CG + BG-AC
    assert plate_ids == {"CG", "BG-AC"}


def test_no_bess_bom_drops_bg_ac_keeps_cg_and_parts() -> None:
    # arrange
    plate_ids = {p["id"] for p in NO_BESS_BOM["plates"]}
    parts_by_id = {p["equipment_id"]: p["qty"] for p in NO_BESS_BOM["parts"]}
    # act / assert — same hardware (utility tie-in still needs xfm + swg + relay
    # + meter), only the BESS-side plate is gone
    assert plate_ids == {"CG"}
    assert parts_by_id["GRD-XFM-001"] == 1
    assert parts_by_id["GRD-SWG-001"] == 1
    assert parts_by_id["GRD-RLY-001"] == 1
    assert parts_by_id["GRD-MTR-001"] == 1


def test_no_bess_assembly_omits_bg_ac_plate() -> None:
    # arrange / act
    assy = build_grid_container(variant="no-bess")
    child_names = {c.name for c in assy.children}
    # assert
    assert "ARC-PLT-CG" in child_names
    assert "ARC-PLT-BG-AC" not in child_names


def test_no_bess_bbox_matches_container_envelope() -> None:
    # arrange — same shell as commercial-ac, just missing one plate
    bbox_tolerance_mm = 50.0
    # act
    assy = build_grid_container(variant="no-bess")
    bbox = assy.toCompound().BoundingBox()
    # assert
    assert abs(bbox.xlen - L_EXT_MM) < bbox_tolerance_mm
    assert abs(bbox.ylen - W_EXT_MM) < bbox_tolerance_mm
    assert abs(bbox.zlen - H_EXT_MM) < bbox_tolerance_mm


def test_bg_ac_plate_placed_at_positive_x_end() -> None:
    # arrange — BG-AC at +X end (BESS pad), opposite from CG at -X (compute)
    expected_x = +L_EXT_MM / 2
    actual_x = BG_MATING_FRAME.toTuple()[0][0]
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


def test_dc_ext_bom_has_pcs_and_bg_dc() -> None:
    # arrange
    parts_by_id = {p["equipment_id"]: p["qty"] for p in COMMERCIAL_DC_EXT_BOM["parts"]}
    plate_ids = {p["id"] for p in COMMERCIAL_DC_EXT_BOM["plates"]}
    # act / assert — PCS present, BG-DC instead of BG-AC
    assert parts_by_id["GRD-PCS-001"] == 1
    assert plate_ids == {"CG", "BG-DC"}


def test_dc_ext_assembly_includes_pcs_and_bg_dc_plate() -> None:
    # arrange / act
    assy = build_grid_container(variant="commercial-dc-ext")
    child_names = {c.name for c in assy.children}
    # assert
    assert "GRD-PCS-001" in child_names
    assert "ARC-PLT-BG-DC" in child_names
    assert "ARC-PLT-BG-AC" not in child_names


def test_dc_ext_bg_plate_at_same_position_as_ac() -> None:
    # arrange — BG-AC and BG-DC share the +X end mating frame (same wall slot)
    expected_pos = BG_MATING_FRAME.toTuple()[0]
    # act
    assy = build_grid_container(variant="commercial-dc-ext")
    bg_dc = next(c for c in assy.children if c.name == "ARC-PLT-BG-DC")
    actual_pos = bg_dc.loc.toTuple()[0]
    # assert
    for axis, (actual, expected) in enumerate(
        zip(actual_pos, expected_pos, strict=True)
    ):
        assert math.isclose(
            actual, expected, abs_tol=0.1
        ), f"axis {axis}: actual={actual} expected={expected}"


def test_dc_ext_bbox_matches_container_envelope() -> None:
    # arrange
    bbox_tolerance_mm = 50.0
    # act
    assy = build_grid_container(variant="commercial-dc-ext")
    bbox = assy.toCompound().BoundingBox()
    # assert — same shell as commercial-ac, PCS sits inside
    assert abs(bbox.xlen - L_EXT_MM) < bbox_tolerance_mm
    assert abs(bbox.ylen - W_EXT_MM) < bbox_tolerance_mm
    assert abs(bbox.zlen - H_EXT_MM) < bbox_tolerance_mm
