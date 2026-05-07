"""Push manifest.yaml + all referenced artifacts to S3.

For each entry in the manifest, uploads the local file at the matching
relative path to its S3 URL. Plates come from the sibling
`edp-interface-plates` repo per `manifest_plates.yaml` curation.

Backend: real AWS S3 by default; localstack via `S3_ENDPOINT_URL` env var
(per Q7-D — testcontainers localstack for tests, real bucket for smoke job).

Usage:
    poe push-s3                              # push to real bucket
    S3_ENDPOINT_URL=http://localhost:4566 poe push-s3   # push to localstack
"""

import logging
import os
from pathlib import Path
from typing import Final

import boto3
import yaml
from botocore.client import BaseClient

from src.manifest_models import Manifest

logger = logging.getLogger(__name__)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
MANIFEST_FILE: Final[Path] = REPO_ROOT / "manifest.yaml"
PLATES_FILE: Final[Path] = REPO_ROOT / "manifest_plates.yaml"
PLATES_REPO_ROOT: Final[Path] = REPO_ROOT.parent / "edp-interface-plates"

S3_BUCKET: Final[str] = os.environ.get("ARCNODE_ARTIFACTS_BUCKET", "arcnode-artifacts")
S3_ENDPOINT_URL: Final[str | None] = os.environ.get("S3_ENDPOINT_URL")


def _s3_client() -> BaseClient:
    """Create an S3 client honoring optional localstack endpoint override."""
    if S3_ENDPOINT_URL:
        return boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id="test",
            aws_secret_access_key="test",  # noqa: S106 — localstack-only literal
            region_name="us-east-1",
        )
    return boto3.client("s3")


def _ensure_bucket(s3: BaseClient, bucket: str) -> None:
    """Create the bucket if it doesn't exist (localstack convenience)."""
    try:
        s3.head_bucket(Bucket=bucket)
    except s3.exceptions.ClientError:
        s3.create_bucket(Bucket=bucket)
        logger.info(f"created bucket: {bucket}")


def _s3_url_to_key(url: str) -> str:
    """Strip s3://bucket/ prefix → key."""
    prefix = f"s3://{S3_BUCKET}/"
    if not url.startswith(prefix):
        raise ValueError(f"URL doesn't match bucket {S3_BUCKET}: {url}")
    return url[len(prefix) :]


def _upload(s3: BaseClient, local_path: Path, s3_url: str) -> None:
    if not local_path.exists():
        logger.warning(
            f"  ⊘ skip (missing local): {local_path.relative_to(REPO_ROOT.parent)}"
        )
        return
    key = _s3_url_to_key(s3_url)
    s3.upload_file(str(local_path), S3_BUCKET, key)
    logger.info(f"  → s3://{S3_BUCKET}/{key}")


def push_manifest_artifacts(manifest: Manifest) -> None:
    """Upload manifest.yaml + every URL-referenced artifact in it."""
    s3 = _s3_client()
    _ensure_bucket(s3, S3_BUCKET)

    # Manifest itself
    s3.upload_file(str(MANIFEST_FILE), S3_BUCKET, "manifest.yaml")
    logger.info(f"  → s3://{S3_BUCKET}/manifest.yaml")

    # Equipment specs + envelopes
    for equipment_id, spec_url in manifest.specs.items():
        _upload(s3, REPO_ROOT / "equipment" / equipment_id / "spec.yaml", spec_url)
    for equipment_id, geom in manifest.geometry.items():
        _upload(
            s3, REPO_ROOT / "equipment" / equipment_id / "envelope.step", geom.envelope
        )

    # Assemblies
    for asm_type, variants in manifest.assemblies.items():
        type_dir_name = asm_type.replace("_", "-")
        for variant, av in variants.items():
            base = REPO_ROOT / "assemblies" / type_dir_name / variant
            _upload(s3, base / "bom.yaml", av.bom)
            _upload(s3, base / "assembly.step", av.step)
            _upload(s3, base / "assembly.glb", av.glb)
            if av.glb_exploded:
                _upload(s3, base / "assembly-exploded.glb", av.glb_exploded)
            if av.step_exploded:
                _upload(s3, base / "assembly-exploded.step", av.step_exploded)

    # Plates from sibling repo
    plates_curation = yaml.safe_load(PLATES_FILE.read_text())
    for plate_id, plate_urls in manifest.plates.items():
        entry = plates_curation["plates"][plate_id]
        _upload(s3, PLATES_REPO_ROOT / entry["spec_relpath"], plate_urls.spec)
        _upload(s3, PLATES_REPO_ROOT / entry["step_relpath"], plate_urls.step)
        if plate_urls.dxf and "dxf_relpath" in entry:
            _upload(s3, PLATES_REPO_ROOT / entry["dxf_relpath"], plate_urls.dxf)
        if plate_urls.drawing_meta and "drawing_meta_relpath" in entry:
            _upload(
                s3,
                PLATES_REPO_ROOT / entry["drawing_meta_relpath"],
                plate_urls.drawing_meta,
            )


def main() -> None:
    """CLI entry: load manifest.yaml + push every referenced artifact to S3."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not MANIFEST_FILE.exists():
        raise FileNotFoundError(
            f"manifest.yaml not found at {MANIFEST_FILE}; run `poe build-manifest` first"
        )
    manifest = Manifest.model_validate(yaml.safe_load(MANIFEST_FILE.read_text()))
    push_manifest_artifacts(manifest)


if __name__ == "__main__":
    main()
