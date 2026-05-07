"""Tests for scripts/build_manifest.py."""

from pathlib import Path

import yaml

from src.manifest_models import Manifest
from scripts.build_manifest import (
    _validate_profile_refs,
    build_manifest,
)


def test_build_manifest_runs_against_real_repo() -> None:
    # arrange / act
    actual = build_manifest()
    # assert — sanity: at least one of each section
    assert len(actual.specs) > 0
    assert len(actual.geometry) > 0
    assert len(actual.assemblies) > 0
    assert len(actual.plates) > 0
    assert len(actual.profiles) > 0


def test_manifest_specs_keyed_by_equipment_id() -> None:
    # arrange / act
    manifest = build_manifest()
    # assert — known equipment present
    assert "CMP-NODE-001" in manifest.specs
    assert manifest.specs["CMP-NODE-001"].endswith("CMP-NODE-001/spec.yaml")


def test_manifest_assemblies_has_compute_container_commercial_ac() -> None:
    # arrange / act
    manifest = build_manifest()
    # assert
    assert "compute_container" in manifest.assemblies
    assert "commercial-ac" in manifest.assemblies["compute_container"]
    av = manifest.assemblies["compute_container"]["commercial-ac"]
    assert av.bom.endswith("bom.yaml")
    assert av.step.endswith("assembly.step")


def test_manifest_plates_includes_cg() -> None:
    # arrange / act
    manifest = build_manifest()
    # assert
    assert "CG" in manifest.plates
    assert manifest.plates["CG"].step.endswith("CG/v1/plate.step")


def test_manifest_profile_commercial_ac_resolved() -> None:
    # arrange / act
    manifest = build_manifest()
    # assert
    assert "commercial_ac" in manifest.profiles
    profile = manifest.profiles["commercial_ac"]
    assert profile.compute_container == "commercial-ac"
    assert "CG" in profile.interface_plates


def test_validate_profile_refs_clean_after_grid_container_built() -> None:
    # arrange — step 6.1 grid container exists; profile refs should resolve
    manifest = build_manifest()
    # act
    warnings = _validate_profile_refs(manifest)
    # assert — no missing-variant warnings now that grid is built
    grid_warnings = [w for w in warnings if "grid_container" in w]
    assert grid_warnings == []


def test_manifest_pydantic_roundtrip(tmp_path: Path) -> None:
    # arrange
    manifest = build_manifest()
    # act — dump via model_dump(json) and reload
    dumped = yaml.safe_dump(manifest.model_dump(mode="json"))
    actual = Manifest.model_validate(yaml.safe_load(dumped))
    # assert
    assert actual.version == manifest.version
    assert set(actual.specs.keys()) == set(manifest.specs.keys())
