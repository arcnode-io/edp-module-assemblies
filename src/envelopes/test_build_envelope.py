"""Tests for build_envelope.py."""

from pathlib import Path

import yaml

from src.envelopes.build_envelope import (
    BoundingBox,
    EquipmentSpec,
    build_envelope,
)


def _write_spec(tmp_path: Path, equipment_id: str, bbox: dict) -> Path:
    """Create a minimal spec.yaml fixture in tmp_path/{id}/spec.yaml."""
    spec_dir = tmp_path / equipment_id
    spec_dir.mkdir()
    spec_path = spec_dir / "spec.yaml"
    spec_path.write_text(
        yaml.safe_dump(
            {
                "equipment_id": equipment_id,
                "geometry": {"bounding_box": bbox},
            }
        )
    )
    return spec_path


def test_bounding_box_is_complete_when_all_fields_present() -> None:
    # arrange
    bbox = BoundingBox(L_mm=100.0, W_mm=200.0, H_mm=300.0)
    # act
    actual = bbox.is_complete()
    # assert
    assert actual is True


def test_bounding_box_is_incomplete_when_any_field_missing() -> None:
    # arrange
    bbox = BoundingBox(L_mm=100.0, W_mm=None, H_mm=300.0)
    # act
    actual = bbox.is_complete()
    # assert
    assert actual is False


def test_build_envelope_emits_step_file(tmp_path: Path) -> None:
    # arrange
    spec_path = _write_spec(
        tmp_path, "CMP-NODE-001", {"L_mm": 900.0, "W_mm": 482.0, "H_mm": 178.0}
    )
    # act
    actual = build_envelope(spec_path)
    # assert
    assert actual is not None
    assert actual.name == "envelope.step"
    assert actual.exists()
    assert actual.stat().st_size > 0


def test_build_envelope_skips_when_bbox_incomplete(tmp_path: Path) -> None:
    # arrange
    spec_path = _write_spec(
        tmp_path, "EXT-DC-001", {"L_mm": None, "W_mm": None, "H_mm": None}
    )
    # act
    actual = build_envelope(spec_path)
    # assert
    assert actual is None
    assert not (spec_path.parent / "envelope.step").exists()


def test_equipment_spec_ignores_extra_fields(tmp_path: Path) -> None:
    # arrange — real spec.yaml has many extra sections (electrical, thermal, ports, ...)
    raw = {
        "equipment_id": "CMP-NODE-001",
        "schema_version": "0",
        "category": "gpu_node",
        "spec": {"electrical": {"voltage_v": 240.0}},
        "geometry": {"bounding_box": {"L_mm": 900, "W_mm": 482, "H_mm": 178}},
        "provenance": {"authored_by": "test"},
    }
    # act
    actual = EquipmentSpec.model_validate(raw)
    # assert
    expected_id = "CMP-NODE-001"
    assert actual.equipment_id == expected_id
