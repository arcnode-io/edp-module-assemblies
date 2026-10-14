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


def test_grid_profiles_name_a_feeder_variant_without_the_poi_meter() -> None:
    # arrange — sites past one transformer add feeder grid containers
    manifest = build_manifest()
    # act
    feeders = {
        name: p.grid_feeder_container
        for name, p in manifest.profiles.items()
        if p.grid_container is not None
    }
    # assert
    assert feeders["commercial_ac"] == "feeder"
    assert feeders["defense_ac"] == "defense-feeder"
    assert feeders["commercial_dc_ext"] == "dc-ext-feeder"
    assert all(feeders.values())


def test_validate_profile_refs_clean_after_all_v1_variants_built() -> None:
    # arrange — every profile's variants exist
    # end-to-end after steps 6.1, 6.5, and 6.8. No deferred warnings expected.
    manifest = build_manifest()
    # act
    warnings = _validate_profile_refs(manifest)
    # assert — clean
    assert warnings == []


def test_manifest_pydantic_roundtrip(tmp_path: Path) -> None:
    # arrange
    manifest = build_manifest()
    # act — dump via model_dump(json) and reload
    dumped = yaml.safe_dump(manifest.model_dump(mode="json"))
    actual = Manifest.model_validate(yaml.safe_load(dumped))
    # assert
    assert actual.version == manifest.version
    assert set(actual.specs.keys()) == set(manifest.specs.keys())


def test_every_profile_maps_each_gpu_type_to_a_container_with_that_gpu() -> None:
    # Arrange — an H100 order must get H100 nodes (QA: B200s shipped instead)
    from src.assemblies.equipment_list import COMPUTE

    node_for = {"b200": "CMP-NODE-001", "h100_sxm": "CMP-NODE-002"}
    manifest = build_manifest()

    # Act
    actual = {
        (name, gpu): {
            i.equipment_id for i in COMPUTE[variant] if i.tag.startswith("NODE")
        }
        for name, prof in manifest.profiles.items()
        for gpu, variant in prof.compute_container_by_gpu.items()
    }

    # Assert
    expected = {
        (name, gpu): {node_for[gpu]} for name in manifest.profiles for gpu in node_for
    }
    assert actual == expected
