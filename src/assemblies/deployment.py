"""Deployment-level assembly composing containers + external equipment.

Each container builds at its own local origin (per ADR-007). Deployment
composes them with offsets (PM 2026-05-09):

- Compute at deployment origin (floor center).
- Grid at +X with 300 mm gap between end walls (CG flexible assembly room).
- EXT-DC at -Y with 2000 mm clearance from compute -Y wall (Güntner manual
  front service clearance).
- EXT-BESS at +X beyond grid with 3000 mm clearance (customer pad).

Defense profiles route external equipment by deployment_context: EXT-DC-002
(Evapco eco-Air, US-fab) + EXT-BESS-002 in place of commercial EXT-DC-001
(Güntner GFD) + EXT-BESS-001 (Tesla Megapack). Same logic as plate fetch
context routing in {compute,grid}_container.py.

Emits assemblies/deployment/{profile}/{assembly.step,assembly.glb}.
"""

import argparse
import logging
from pathlib import Path
from typing import Final, Literal

import cadquery as cq

from src.assemblies import compute_container, grid_container

logger = logging.getLogger(__name__)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
EQUIPMENT_DIR: Final[Path] = REPO_ROOT / "equipment"
ASSEMBLIES_DIR: Final[Path] = REPO_ROOT / "assemblies"

# Reason: container exterior dims (ADR-004).
L_EXT_MM: Final[float] = 2991.0
W_EXT_MM: Final[float] = 2438.0
H_EXT_MM: Final[float] = 2896.0

# Reason: PM 2026-05-09 layout defaults.
CONTAINER_GAP_MM: Final[float] = 300.0
DC_OFFSET_FROM_COMPUTE_Y_MM: Final[float] = 2000.0
BESS_OFFSET_FROM_GRID_X_MM: Final[float] = 3000.0

# Reason: dims pulled from equipment/{id}/spec.yaml mechanical.dimensions_mm.
# v1 default SKUs per #31 commit. Real SKU dims come from sizing engine at
# deployment time; these are visualization defaults.
_EXT_DC_DIMS_MM: Final[dict[str, tuple[float, float, float]]] = {
    "EXT-DC-001": (3500.0, 1100.0, 1700.0),  # Güntner GFD 080 2-fan
    "EXT-DC-002": (2700.0, 1500.0, 2200.0),  # Evapco EAW-DD smallest
}
_EXT_BESS_DIMS_MM: Final[dict[str, tuple[float, float, float]]] = {
    "EXT-BESS-001": (8800.0, 1650.0, 2785.0),  # Tesla Megapack 2 XL
    "EXT-BESS-002": (8800.0, 1650.0, 2785.0),  # placeholder; DoD-eligible TBD
}

Profile = Literal[
    "commercial_ac",
    "commercial_dc_int",
    "commercial_dc_ext",
    "commercial_no_bess",
    "defense_ac",
    "defense_dc_ext",
    "defense_no_bess",
]

# Reason: profile → (compute_variant, grid_variant, has_bess).
_PROFILE_CONFIG: Final[dict[str, tuple[str, str, bool]]] = {
    "commercial_ac": ("commercial-ac", "commercial-ac", True),
    "commercial_dc_int": ("commercial-ac", "commercial-ac", True),
    "commercial_dc_ext": ("commercial-ac", "commercial-dc-ext", True),
    "commercial_no_bess": ("commercial-ac", "no-bess", False),
    "defense_ac": ("defense-ac", "defense-ac", True),
    "defense_dc_ext": ("defense-ac", "defense-dc-ext", True),
    "defense_no_bess": ("defense-ac", "defense-no-bess", False),
}


def _is_defense(profile: str) -> bool:
    return profile.startswith("defense_")


def _ext_dc_id(profile: str) -> str:
    return "EXT-DC-002" if _is_defense(profile) else "EXT-DC-001"


def _ext_bess_id(profile: str) -> str:
    return "EXT-BESS-002" if _is_defense(profile) else "EXT-BESS-001"


def _import_envelope(equipment_id: str) -> cq.Workplane:
    """Import equipment envelope STEP from equipment/{id}/envelope.step."""
    return cq.importers.importStep(str(EQUIPMENT_DIR / equipment_id / "envelope.step"))


def build_deployment(profile: Profile) -> cq.Assembly:
    """Compose containers + external equipment for a deployment profile.

    Args:
        profile: deployment profile name (must be a key of _PROFILE_CONFIG).

    Returns:
        cq.Assembly with compute + grid + EXT-DC + (optional) EXT-BESS placed
        per the layout offsets.

    Raises:
        NotImplementedError: For unsupported profiles.
    """
    if profile not in _PROFILE_CONFIG:
        raise NotImplementedError(
            f"profile={profile!r} not supported. Available: {sorted(_PROFILE_CONFIG)}"
        )

    compute_variant, grid_variant, has_bess = _PROFILE_CONFIG[profile]
    deployment = cq.Assembly(name=f"deployment_{profile}")

    # Compute Container at deployment origin (floor center = (0, 0, 0)).
    compute = compute_container.build_compute_container(variant=compute_variant)
    deployment.add(compute, name="compute_container", loc=cq.Location())

    # Grid Container at +X with 300 mm gap between end walls.
    # grid center X = compute_+X_wall + gap + grid_L/2 = L_EXT/2 + gap + L_EXT/2.
    grid_center_x = L_EXT_MM + CONTAINER_GAP_MM
    grid = grid_container.build_grid_container(variant=grid_variant)
    deployment.add(
        grid,
        name="grid_container",
        loc=cq.Location(cq.Vector(grid_center_x, 0, 0)),
    )

    # EXT-DC at -Y with 2000 mm clearance from compute -Y wall.
    # Center under compute X axis (X=0), pad-mounted (Z = dc_height/2).
    dc_id = _ext_dc_id(profile)
    _, dc_w, dc_h = _EXT_DC_DIMS_MM[dc_id]
    dc_center_y = -(W_EXT_MM / 2 + DC_OFFSET_FROM_COMPUTE_Y_MM + dc_w / 2)
    deployment.add(
        _import_envelope(dc_id),
        name=dc_id,
        loc=cq.Location(cq.Vector(0.0, dc_center_y, dc_h / 2)),
    )

    # EXT-BESS at +X beyond Grid +X wall with 3000 mm clearance.
    if has_bess:
        bess_id = _ext_bess_id(profile)
        bess_l, _, bess_h = _EXT_BESS_DIMS_MM[bess_id]
        grid_plus_x_wall = grid_center_x + L_EXT_MM / 2
        bess_center_x = grid_plus_x_wall + BESS_OFFSET_FROM_GRID_X_MM + bess_l / 2
        deployment.add(
            _import_envelope(bess_id),
            name=bess_id,
            loc=cq.Location(cq.Vector(bess_center_x, 0.0, bess_h / 2)),
        )

    return deployment


def emit_artifacts(assy: cq.Assembly, profile: str) -> dict[str, Path]:
    """Write deployment artifacts to assemblies/deployment/{profile}/."""
    out_dir = ASSEMBLIES_DIR / "deployment" / profile
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {
        "step": out_dir / "assembly.step",
        "glb": out_dir / "assembly.glb",
    }
    assy.export(str(paths["step"]))
    assy.export(str(paths["glb"]))
    return paths


def main() -> None:
    """CLI entry: build a deployment assembly + write artifacts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        default="commercial_ac",
        choices=sorted(_PROFILE_CONFIG),
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    assy = build_deployment(args.profile)
    artifacts = emit_artifacts(assy, args.profile)
    for kind, path in artifacts.items():
        logger.info(f"  → {kind}: {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
