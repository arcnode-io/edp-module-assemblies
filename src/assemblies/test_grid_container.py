"""Tests for grid_container assembly per Q14-C success criterion (step 6.1)."""

import math

import pytest

from src.assemblies.grid_container import (
    BG_MATING_FRAME,
    CG_MATING_FRAME,
    COMMERCIAL_AC_BOM,
    COMMERCIAL_DC_EXT_BOM,
    DEFENSE_AC_BOM,
    DEFENSE_FEEDER_BOM,
    FEEDER_BOM,
    H_EXT_MM,
    L_EXT_MM,
    W_EXT_MM,
    DC_EXT_FEEDER_BOM,
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
    # arrange / act / assert — variant outside the BOM_BY_VARIANT keys.
    # defense_dc_int (PCS-in-BESS at DoD) is invalid per module_resolver
    # (CATL EnerOne integrated PCS excluded from DoD procurement).
    with pytest.raises(NotImplementedError, match=r"not supported"):
        build_grid_container(variant="defense-dc-int")  # type: ignore[arg-type]


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


def test_ac_grid_container_has_no_bess_plate() -> None:
    # arrange
    plate_ids = {p["id"] for p in COMMERCIAL_AC_BOM["plates"]}
    # act / assert — AC batteries tie in at 13.8 kV outside the container (ADR-016)
    assert plate_ids == {"CG"}


def test_feeder_bom_drops_the_poi_meter_and_bess_plate() -> None:
    # arrange
    parts = {p["equipment_id"] for p in FEEDER_BOM["parts"]}
    plates = {p["id"] for p in FEEDER_BOM["plates"]}
    # act / assert — a site has one POI, so only the primary carries the meter
    assert (parts, plates) == ({"GRD-XFM-001", "GRD-SWG-001", "GRD-RLY-001"}, {"CG"})
    assert DEFENSE_FEEDER_BOM == {**FEEDER_BOM, "deployment_context": "defense_forward"}


def test_dc_ext_feeder_carries_its_own_pcs_but_not_the_poi_meter() -> None:
    # arrange
    parts = {p["equipment_id"]: p["qty"] for p in DC_EXT_FEEDER_BOM["parts"]}
    plates = {p["id"] for p in DC_EXT_FEEDER_BOM["plates"]}
    # act / assert — each dc-ext container converts its own BESS DC, so it
    # needs its own PCS pair and BG-DC; the one POI meter stays on the primary
    expected_parts = {
        "GRD-XFM-001": 1,
        "GRD-SWG-001": 1,
        "GRD-RLY-001": 1,
        "GRD-PCS-001": 2,
    }
    assert (parts, plates) == (expected_parts, {"CG", "BG-DC"})


def test_bg_plate_placed_at_positive_x_end() -> None:
    # arrange — BG-DC at +X end (BESS pad), opposite from CG at -X (compute)
    expected_x = +L_EXT_MM / 2
    actual_x = BG_MATING_FRAME.toTuple()[0][0]
    assert math.isclose(actual_x, expected_x, abs_tol=0.1)


def test_ac_assembly_has_no_bess_plate() -> None:
    # arrange / act
    assy = build_grid_container(variant="commercial-ac")
    child_names = {c.name for c in assy.children}
    # assert
    assert not any(n.startswith("ARC-PLT-BG") for n in child_names)


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
    # act / assert — two PCS (417 kW each at 415 V) fed through BG-DC
    assert parts_by_id["GRD-PCS-001"] == 2
    assert plate_ids == {"CG", "BG-DC"}


def test_dc_ext_assembly_includes_pcs_and_bg_dc_plate() -> None:
    # arrange / act
    assy = build_grid_container(variant="commercial-dc-ext")
    child_names = {c.name for c in assy.children}
    # assert
    assert {"GRD-PCS-001#1", "GRD-PCS-001#2"} <= child_names
    assert "ARC-PLT-BG-DC" in child_names


def test_dc_ext_bg_plate_sits_on_the_bg_mating_frame() -> None:
    # arrange — BG-DC on the +X end mating frame (BESS-facing wall)
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


@pytest.mark.parametrize("variant", ["commercial-dc-ext", "dc-ext-feeder"])
def test_dc_ext_equipment_does_not_clash(variant: str) -> None:
    """Pairwise bbox-overlap check on the equipment (XFM, SWG, 2x PCS).

    Caught in conversation 2026-05-09: PCS was placed at +X + -Y wall which
    clashed with SafeGear's rotated 2159 mm depth. Bbox-overlap test prevents
    the regression.
    """
    # arrange
    equipment_names = {"GRD-XFM-001", "GRD-SWG-001", "GRD-PCS-001#1", "GRD-PCS-001#2"}
    # act
    assy = build_grid_container(variant=variant)
    children = [c for c in assy.children if c.name in equipment_names]
    bboxes = {c.name: c.toCompound().BoundingBox() for c in children}
    # assert — all present
    assert set(bboxes.keys()) == equipment_names
    # assert — no pairwise overlap
    for name_a, bb_a in bboxes.items():
        for name_b, bb_b in bboxes.items():
            if name_a >= name_b:
                continue
            x_overlap = (bb_a.xmin < bb_b.xmax) and (bb_b.xmin < bb_a.xmax)
            y_overlap = (bb_a.ymin < bb_b.ymax) and (bb_b.ymin < bb_a.ymax)
            z_overlap = (bb_a.zmin < bb_b.zmax) and (bb_b.zmin < bb_a.zmax)
            assert not (x_overlap and y_overlap and z_overlap), (
                f"clash: {name_a} bbox=({bb_a.xmin:.0f}..{bb_a.xmax:.0f}, "
                f"{bb_a.ymin:.0f}..{bb_a.ymax:.0f}) overlaps {name_b}"
            )


# --- Defense variants (per PM 2026-05-09, #18) ---


def test_defense_ac_bom_carries_deployment_context() -> None:
    # arrange / act / assert — defense BOM has top-level deployment_context
    # field that routes plate_loader to -defense.step artifacts.
    assert DEFENSE_AC_BOM["deployment_context"] == "defense_forward"
    # Same parts + plate IDs as commercial twin.
    assert DEFENSE_AC_BOM["parts"] == COMMERCIAL_AC_BOM["parts"]
    assert DEFENSE_AC_BOM["plates"] == COMMERCIAL_AC_BOM["plates"]


def test_defense_ac_assembly_builds_with_cg_only() -> None:
    # arrange / act
    assy = build_grid_container(variant="defense-ac")
    child_names = {c.name for c in assy.children}
    # assert — same plate set as commercial-ac (CG only, ADR-016); fetch
    # routes to -defense.step artifacts (plate_loader tests cover the routing).
    assert "ARC-PLT-CG" in child_names
    assert not any(n.startswith("ARC-PLT-BG") for n in child_names)
    assert not any(n.startswith("GRD-PCS-001") for n in child_names)
