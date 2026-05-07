"""Generates equipment envelope STEP files from spec.yaml bounding boxes.

Walks `equipment/*/spec.yaml`, reads `geometry.bounding_box.{L,W,H}_mm`,
emits a CadQuery box at `equipment/{id}/envelope.step`. Origin = bbox
center; consumers translate into their placement frame.

Per ADR-013-tbd / Q13: equipment envelopes only for v1; service envelopes
deferred to step 6.7 (installation_graph).
"""

import logging
from pathlib import Path
from typing import Final

import cadquery as cq
import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

EQUIPMENT_DIR: Final[Path] = Path(__file__).resolve().parents[2] / "equipment"
ENVELOPE_FILENAME: Final[str] = "envelope.step"


class BoundingBox(BaseModel):
    """Equipment envelope dimensions in millimeters.

    Fields are Optional because external equipment (EXT-DC-*, EXT-BESS-*)
    can have model-dependent dims populated only by the sizing engine at
    deployment time. Such equipment is skipped during envelope build.
    """

    L_mm: float | None = Field(default=None, gt=0)
    W_mm: float | None = Field(default=None, gt=0)
    H_mm: float | None = Field(default=None, gt=0)

    def is_complete(self) -> bool:
        """Returns True iff all three dimensions are populated."""
        return self.L_mm is not None and self.W_mm is not None and self.H_mm is not None


class GeometryBlock(BaseModel):
    """Geometry section of an equipment spec; only bounding_box consumed here."""

    bounding_box: BoundingBox

    model_config = {"extra": "ignore"}


class EquipmentSpec(BaseModel):
    """Minimal spec slice this script consumes — id + bbox only."""

    equipment_id: str
    geometry: GeometryBlock

    model_config = {"extra": "ignore"}


def build_envelope(spec_path: Path) -> Path | None:
    """Read spec.yaml, emit envelope.step as a CadQuery box at bbox center.

    Args:
        spec_path: Absolute path to an equipment spec.yaml file.

    Returns:
        Absolute path to the emitted envelope.step file, or None if the
        spec has incomplete bounding-box dims (skipped intentionally).

    Raises:
        ValidationError: If spec.yaml is malformed.
    """
    spec_data = yaml.safe_load(spec_path.read_text())
    spec = EquipmentSpec.model_validate(spec_data)
    bbox = spec.geometry.bounding_box

    if not bbox.is_complete():
        return None

    box = cq.Workplane("XY").box(bbox.L_mm, bbox.W_mm, bbox.H_mm)

    out_path = spec_path.parent / ENVELOPE_FILENAME
    cq.exporters.export(box, str(out_path))
    return out_path


def main() -> None:
    """Walk equipment/, emit envelope.step beside each spec.yaml."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    spec_paths = sorted(EQUIPMENT_DIR.glob("*/spec.yaml"))
    built = 0
    skipped: list[str] = []
    for spec_path in spec_paths:
        out = build_envelope(spec_path)
        if out is None:
            skipped.append(spec_path.parent.name)
            logger.info(
                f"  ⊘ {spec_path.parent.name} (incomplete bbox — sized at deployment)"
            )
            continue
        built += 1
        logger.info(f"  → {out.relative_to(EQUIPMENT_DIR.parent)}")
    logger.info(
        f"\n{built} envelopes built; {len(skipped)} skipped: {', '.join(skipped) or 'none'}"
    )


if __name__ == "__main__":
    main()
