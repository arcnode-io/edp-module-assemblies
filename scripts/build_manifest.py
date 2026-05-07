"""Build manifest.yaml by walking equipment/, assemblies/, and curation files.

Per ADR-006 + ADR-009 + ADR-012:
  - Single source of truth for hardware↔edp-api contract
  - Profile mapping curated in manifest_profiles.yaml
  - Plate registry curated in manifest_plates.yaml (sibling repo URLs)
  - In-file `version:` from package version (semantic-release later)

Output: manifest.yaml at repo root.
"""

import logging
from pathlib import Path
from typing import Final

import yaml

from src.manifest_models import (
    AssemblyVariant,
    GeometryUrls,
    Manifest,
    PlateUrls,
    ProfileAssemblies,
)

logger = logging.getLogger(__name__)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
EQUIPMENT_DIR: Final[Path] = REPO_ROOT / "equipment"
ASSEMBLIES_DIR: Final[Path] = REPO_ROOT / "assemblies"
PROFILES_FILE: Final[Path] = REPO_ROOT / "manifest_profiles.yaml"
PLATES_FILE: Final[Path] = REPO_ROOT / "manifest_plates.yaml"
OUTPUT_FILE: Final[Path] = REPO_ROOT / "manifest.yaml"

# v1 single bucket (per ADR-012 versioning deferred).
S3_BASE: Final[str] = "s3://arcnode-artifacts"
PLATES_S3_BASE: Final[str] = "s3://arcnode-artifacts/plates"

# Reason: read package version once for manifest in-file `version:` field.
PACKAGE_VERSION: Final[str] = "0.1.0"


def _collect_specs() -> dict[str, str]:
    """Walk equipment/*/spec.yaml → equipment_id → S3 URL."""
    specs: dict[str, str] = {}
    for spec_path in sorted(EQUIPMENT_DIR.glob("*/spec.yaml")):
        equipment_id = spec_path.parent.name
        specs[equipment_id] = f"{S3_BASE}/equipment/{equipment_id}/spec.yaml"
    return specs


def _collect_geometry() -> dict[str, GeometryUrls]:
    """Walk equipment/*/envelope.step → GeometryUrls per equipment_id."""
    geom: dict[str, GeometryUrls] = {}
    for envelope_path in sorted(EQUIPMENT_DIR.glob("*/envelope.step")):
        equipment_id = envelope_path.parent.name
        geom[equipment_id] = GeometryUrls(
            envelope=f"{S3_BASE}/equipment/{equipment_id}/envelope.step",
            vendor_step=None,
        )
    return geom


def _collect_assemblies() -> dict[str, dict[str, AssemblyVariant]]:
    """Walk assemblies/{type}/{variant}/ → assemblies dict."""
    assemblies: dict[str, dict[str, AssemblyVariant]] = {}
    if not ASSEMBLIES_DIR.exists():
        return assemblies
    for type_dir in sorted(ASSEMBLIES_DIR.iterdir()):
        if not type_dir.is_dir():
            continue
        type_key = type_dir.name.replace(
            "-", "_"
        )  # compute-container → compute_container
        assemblies[type_key] = {}
        for variant_dir in sorted(type_dir.iterdir()):
            if not variant_dir.is_dir():
                continue
            variant = variant_dir.name
            base = f"{S3_BASE}/assemblies/{type_dir.name}/{variant}"
            glb_exploded_local = variant_dir / "assembly-exploded.glb"
            step_exploded_local = variant_dir / "assembly-exploded.step"
            assemblies[type_key][variant] = AssemblyVariant(
                bom=f"{base}/bom.yaml",
                step=f"{base}/assembly.step",
                glb=f"{base}/assembly.glb",
                glb_exploded=(
                    f"{base}/assembly-exploded.glb"
                    if glb_exploded_local.exists()
                    else None
                ),
                step_exploded=(
                    f"{base}/assembly-exploded.step"
                    if step_exploded_local.exists()
                    else None
                ),
                topology_yaml=None,
            )
    return assemblies


def _collect_plates() -> dict[str, PlateUrls]:
    """Read manifest_plates.yaml curation → PlateUrls per plate_id."""
    if not PLATES_FILE.exists():
        return {}
    data = yaml.safe_load(PLATES_FILE.read_text())
    plates: dict[str, PlateUrls] = {}
    for plate_id, entry in (data.get("plates") or {}).items():
        version = entry["version"]
        base = f"{PLATES_S3_BASE}/{plate_id}/{version}"
        plates[plate_id] = PlateUrls(
            spec=f"{base}/spec.yaml",
            step=f"{base}/plate.step",
            dxf=f"{base}/plate.dxf",
            drawing_meta=f"{base}/drawing_meta.json",
        )
    return plates


def _collect_profiles() -> dict[str, ProfileAssemblies]:
    """Read manifest_profiles.yaml curation → ProfileAssemblies per profile."""
    if not PROFILES_FILE.exists():
        return {}
    data = yaml.safe_load(PROFILES_FILE.read_text())
    profiles: dict[str, ProfileAssemblies] = {}
    for name, entry in (data.get("profiles") or {}).items():
        profiles[name] = ProfileAssemblies.model_validate(entry)
    return profiles


def _validate_profile_refs(manifest: Manifest) -> list[str]:
    """Check that profiles reference assemblies/plates that exist.

    Returns list of warning strings. Empty list = no dangling references.
    """
    warnings: list[str] = []
    for profile_name, profile in manifest.profiles.items():
        cc_variants = manifest.assemblies.get("compute_container", {})
        if profile.compute_container not in cc_variants:
            warnings.append(
                f"profile '{profile_name}': compute_container variant "
                f"'{profile.compute_container}' not found in assemblies"
            )
        if profile.grid_container is not None:
            gc_variants = manifest.assemblies.get("grid_container", {})
            if profile.grid_container not in gc_variants:
                warnings.append(
                    f"profile '{profile_name}': grid_container variant "
                    f"'{profile.grid_container}' not found in assemblies"
                )
        warnings.extend(
            f"profile '{profile_name}': plate '{plate_id}' not found"
            for plate_id in profile.interface_plates
            if plate_id not in manifest.plates
        )
    return warnings


def build_manifest() -> Manifest:
    """Assemble Manifest from filesystem walk + curation files."""
    return Manifest(
        version=PACKAGE_VERSION,
        specs=_collect_specs(),
        geometry=_collect_geometry(),
        assemblies=_collect_assemblies(),
        plates=_collect_plates(),
        profiles=_collect_profiles(),
    )


def main() -> None:
    """CLI entry: build manifest from filesystem walk + curation, write yaml."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    manifest = build_manifest()

    warnings = _validate_profile_refs(manifest)
    for w in warnings:
        logger.warning(f"  ⚠ {w}")

    OUTPUT_FILE.write_text(
        yaml.safe_dump(
            manifest.model_dump(mode="json", exclude_none=False),
            sort_keys=False,
        )
    )
    logger.info(
        f"  → manifest.yaml ({len(manifest.specs)} specs, "
        f"{len(manifest.plates)} plates, "
        f"{len(manifest.profiles)} profiles)"
    )


if __name__ == "__main__":
    main()
