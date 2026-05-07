"""Tests for src/plate_loader.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from src import plate_loader


def test_cache_path_structure() -> None:
    # arrange / act
    actual = plate_loader.cache_path("CG", "v1")
    # assert
    assert actual.parts[-3:] == ("CG", "v1", "plate.step")


def test_fetch_returns_existing_cache_hit_without_s3(tmp_path: Path) -> None:
    # arrange — point cache at tmp_path, seed a fake plate file
    plate_loader.CACHE_DIR  # noqa: B018
    cache_dir = tmp_path / "cache"
    fake_target = cache_dir / "CG" / "v1" / "plate.step"
    fake_target.parent.mkdir(parents=True)
    fake_target.write_text("FAKE STEP CONTENT")
    with patch.object(plate_loader, "CACHE_DIR", cache_dir):
        # act
        actual = plate_loader.fetch("CG", "v1")
    # assert
    assert actual == fake_target
    assert actual.read_text() == "FAKE STEP CONTENT"


def test_fetch_downloads_from_s3_on_cache_miss(tmp_path: Path) -> None:
    # arrange
    cache_dir = tmp_path / "cache"
    mock_s3 = MagicMock()

    def fake_download(bucket: str, key: str, dest: str) -> None:
        Path(dest).write_text(f"S3 CONTENT: {bucket}/{key}")

    mock_s3.download_file.side_effect = fake_download

    with (
        patch.object(plate_loader, "CACHE_DIR", cache_dir),
        patch.object(plate_loader.boto3, "client", return_value=mock_s3),
    ):
        # act
        actual = plate_loader.fetch("CG", "v1")
    # assert
    assert actual.exists()
    assert "S3 CONTENT" in actual.read_text()
    mock_s3.download_file.assert_called_once()


def test_sync_local_creates_symlink_to_existing_source(tmp_path: Path) -> None:
    # arrange
    source = tmp_path / "fake_source.step"
    source.write_text("SOURCE")
    cache_dir = tmp_path / "cache"

    with (
        patch.object(plate_loader, "CACHE_DIR", cache_dir),
        patch.object(plate_loader, "LOCAL_PLATE_SOURCES", {("CG", "v1"): source}),
    ):
        # act
        plate_loader.sync_local()

    # assert
    target = cache_dir / "CG" / "v1" / "plate.step"
    assert target.is_symlink()
    assert target.resolve() == source.resolve()


def test_sync_local_skips_missing_source(tmp_path: Path) -> None:
    # arrange
    nonexistent = tmp_path / "does_not_exist.step"
    cache_dir = tmp_path / "cache"

    with (
        patch.object(plate_loader, "CACHE_DIR", cache_dir),
        patch.object(plate_loader, "LOCAL_PLATE_SOURCES", {("CG", "v1"): nonexistent}),
    ):
        # act — should not raise
        plate_loader.sync_local()

    # assert
    target = cache_dir / "CG" / "v1" / "plate.step"
    assert not target.exists()
