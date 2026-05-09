"""Plate STEP file loader with local cache + S3 fallback.

Per ADR-006 + Q6: uniform code path in dev and CI for loading plate STEP
files into the compute_container / grid_container assemblies.

Locally, `poe sync-plates` seeds the cache by symlinking to the sibling
edp-interface-plates repo. In CI, cache miss triggers S3 download.
"""

import logging
import os
from pathlib import Path
from typing import Final

import boto3

logger = logging.getLogger(__name__)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
CACHE_DIR: Final[Path] = REPO_ROOT / ".cache" / "plates"
S3_BUCKET: Final[str] = os.environ.get("ARCNODE_ARTIFACTS_BUCKET", "arcnode-artifacts")
S3_KEY_TEMPLATE: Final[str] = "plates/{plate_id}/{version}/{filename}"

# Reason: defense + sovereign_government share the -defense suffix because the
# plate-side spec.yaml has identical values for both DoD contexts. Split into
# separate suffixes if they ever diverge.
_DEFENSE_CONTEXTS: Final[frozenset[str]] = frozenset(
    {"defense_forward", "sovereign_government"}
)


def _filename_for(deployment_context: str) -> str:
    """Return plate.step or plate-defense.step keyed by deployment context."""
    return (
        "plate-defense.step"
        if deployment_context in _DEFENSE_CONTEXTS
        else "plate.step"
    )


# Reason: dev-only local source map for plate STEPs in the sibling
# edp-interface-plates repo. Used by `poe sync-plates` to seed the cache
# via symlink. CI ignores this and relies on S3 download (cache miss path).
_PLATES_REPO: Final[Path] = REPO_ROOT.parent / "edp-interface-plates" / "cad" / "specs"
PLATE_IDS: Final[tuple[str, ...]] = ("CG", "BG-AC", "BG-DC", "CD")
_DEPLOYMENT_CONTEXTS_TO_SYNC: Final[tuple[str, ...]] = ("commercial", "defense_forward")
LOCAL_PLATE_SOURCES: Final[dict[tuple[str, str, str], Path]] = {
    (pid, "v1", ctx): _PLATES_REPO / pid / _filename_for(ctx)
    for pid in PLATE_IDS
    for ctx in _DEPLOYMENT_CONTEXTS_TO_SYNC
}


def cache_path(
    plate_id: str, version: str, deployment_context: str = "commercial"
) -> Path:
    """Compute the local cache path for a plate STEP file."""
    return CACHE_DIR / plate_id / version / _filename_for(deployment_context)


def fetch(plate_id: str, version: str, deployment_context: str = "commercial") -> Path:
    """Resolve plate STEP path; download from S3 on cache miss.

    Args:
        plate_id: Plate variant code, e.g. "CG".
        version: Plate version string, e.g. "v1".
        deployment_context: "commercial" (default), "defense_forward",
            or "sovereign_government". Defense + sovereign share an
            artifact (5083-H116 marine grade, 10mm).

    Returns:
        Absolute path to the cached plate STEP file.

    Raises:
        botocore.exceptions.ClientError: If S3 download fails on cache miss.
    """
    target = cache_path(plate_id, version, deployment_context)
    if target.exists():
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    filename = _filename_for(deployment_context)
    key = S3_KEY_TEMPLATE.format(plate_id=plate_id, version=version, filename=filename)
    logger.info(
        f"plate_loader: cache miss for {plate_id} {version} {deployment_context}, "
        f"downloading s3://{S3_BUCKET}/{key}"
    )
    s3 = boto3.client("s3")
    s3.download_file(S3_BUCKET, key, str(target))
    return target


def sync_local() -> None:
    """Seed cache by symlinking to local sibling-repo plate STEPs.

    Used by `poe sync-plates` during local development. Skips entries
    whose source file doesn't exist yet (sibling repo not built).
    """
    for (plate_id, version, ctx), source in LOCAL_PLATE_SOURCES.items():
        target = cache_path(plate_id, version, ctx)
        if not source.exists():
            logger.warning(
                f"sync-plates: source missing for {plate_id} {version} {ctx}: "
                f"{source}"
            )
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            target.unlink()
        target.symlink_to(source.resolve())
        try:
            display = target.relative_to(REPO_ROOT)
        except ValueError:
            display = target
        logger.info(f"sync-plates: {display} → {source.resolve()}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sync_local()
