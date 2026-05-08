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
S3_KEY_TEMPLATE: Final[str] = "plates/{plate_id}/{version}/plate.step"

# Reason: dev-only local source map for plate STEPs in the sibling
# edp-interface-plates repo. Used by `poe sync-plates` to seed the cache
# via symlink. CI ignores this and relies on S3 download (cache miss path).
LOCAL_PLATE_SOURCES: Final[dict[tuple[str, str], Path]] = {
    ("CG", "v1"): REPO_ROOT.parent
    / "edp-interface-plates"
    / "cad"
    / "specs"
    / "CG"
    / "plate.step",
    ("BG-AC", "v1"): REPO_ROOT.parent
    / "edp-interface-plates"
    / "cad"
    / "specs"
    / "BG-AC"
    / "plate.step",
}


def cache_path(plate_id: str, version: str) -> Path:
    """Compute the local cache path for a plate STEP file."""
    return CACHE_DIR / plate_id / version / "plate.step"


def fetch(plate_id: str, version: str) -> Path:
    """Resolve plate STEP path; download from S3 on cache miss.

    Args:
        plate_id: Plate variant code, e.g. "CG".
        version: Plate version string, e.g. "v1".

    Returns:
        Absolute path to the cached plate STEP file.

    Raises:
        botocore.exceptions.ClientError: If S3 download fails on cache miss.
    """
    target = cache_path(plate_id, version)
    if target.exists():
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    key = S3_KEY_TEMPLATE.format(plate_id=plate_id, version=version)
    logger.info(
        f"plate_loader: cache miss for {plate_id} {version}, "
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
    for (plate_id, version), source in LOCAL_PLATE_SOURCES.items():
        target = cache_path(plate_id, version)
        if not source.exists():
            logger.warning(
                f"sync-plates: source missing for {plate_id} {version}: {source}"
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
