"""Tests for deployment assembly composition (PM 2026-05-09)."""

import pytest

from src.assemblies.deployment import (
    BESS_OFFSET_FROM_GRID_X_MM,
    CONTAINER_GAP_MM,
    DC_OFFSET_FROM_COMPUTE_Y_MM,
    L_EXT_MM,
    W_EXT_MM,
    _EXT_BESS_DIMS_MM,
    _EXT_DC_DIMS_MM,
    build_deployment,
)


def test_commercial_ac_includes_all_four_modules() -> None:
    # arrange / act
    assy = build_deployment(profile="commercial_ac")
    child_names = {c.name for c in assy.children}
    # assert — compute + grid + Güntner DC + Tesla Megapack
    assert "compute_container" in child_names
    assert "grid_container" in child_names
    assert "EXT-DC-001" in child_names
    assert "EXT-BESS-001" in child_names


def test_no_bess_omits_bess() -> None:
    # arrange / act
    assy = build_deployment(profile="no_bess")
    child_names = {c.name for c in assy.children}
    # assert — DC still present, no BESS
    assert "EXT-DC-001" in child_names
    assert "EXT-BESS-001" not in child_names
    assert "EXT-BESS-002" not in child_names


def test_defense_routes_to_evapco_dc_and_dod_bess() -> None:
    # arrange / act
    assy = build_deployment(profile="defense_ac")
    child_names = {c.name for c in assy.children}
    # assert — Evapco eco-Air (US-fab) replaces Güntner; EXT-BESS-002 in place
    assert "EXT-DC-002" in child_names
    assert "EXT-DC-001" not in child_names
    assert "EXT-BESS-002" in child_names


def test_grid_container_300mm_gap_from_compute() -> None:
    # arrange / act
    assy = build_deployment(profile="commercial_ac")
    grid = next(c for c in assy.children if c.name == "grid_container")
    grid_center_x = grid.loc.toTuple()[0][0]
    # assert — grid center at L_EXT (compute +X wall) + 300 (gap) + L_EXT/2 wait,
    # actually: grid_center_x = compute_+X_wall + gap + grid_L/2 = L/2 + gap + L/2
    expected_grid_center_x = L_EXT_MM + CONTAINER_GAP_MM
    assert abs(grid_center_x - expected_grid_center_x) < 0.1
    # plates face each other across the gap; gap distance check:
    compute_plus_x_wall = L_EXT_MM / 2
    grid_minus_x_wall = grid_center_x - L_EXT_MM / 2
    assert abs(grid_minus_x_wall - compute_plus_x_wall - CONTAINER_GAP_MM) < 0.1


def test_ext_dc_clearance_from_compute_minus_y_wall() -> None:
    # arrange / act
    assy = build_deployment(profile="commercial_ac")
    dc = next(c for c in assy.children if c.name == "EXT-DC-001")
    dc_center_y = dc.loc.toTuple()[0][1]
    # assert — Güntner front service clearance 2000 mm
    _, dc_w, _ = _EXT_DC_DIMS_MM["EXT-DC-001"]
    expected_dc_center_y = -(W_EXT_MM / 2 + DC_OFFSET_FROM_COMPUTE_Y_MM + dc_w / 2)
    assert abs(dc_center_y - expected_dc_center_y) < 0.1


def test_ext_bess_clearance_from_grid_plus_x_wall() -> None:
    # arrange / act
    assy = build_deployment(profile="commercial_ac")
    bess = next(c for c in assy.children if c.name == "EXT-BESS-001")
    bess_center_x = bess.loc.toTuple()[0][0]
    # assert — 3000 mm beyond grid +X wall
    bess_l, _, _ = _EXT_BESS_DIMS_MM["EXT-BESS-001"]
    grid_plus_x_wall = (L_EXT_MM + CONTAINER_GAP_MM) + L_EXT_MM / 2
    expected_bess_center_x = grid_plus_x_wall + BESS_OFFSET_FROM_GRID_X_MM + bess_l / 2
    assert abs(bess_center_x - expected_bess_center_x) < 0.1


def test_unknown_profile_raises() -> None:
    # arrange / act / assert
    with pytest.raises(NotImplementedError, match="not supported"):
        build_deployment(profile="defense_dc_int")  # type: ignore[arg-type]
