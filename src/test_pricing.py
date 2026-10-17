"""pricing.yaml: one budget price list per part, every key a real part."""

from pathlib import Path

import yaml

from scripts.build_manifest import build_manifest
from src.pricing_models import PriceBook

REPO_ROOT = Path(__file__).resolve().parents[1]


def _book() -> PriceBook:
    return PriceBook.model_validate(
        yaml.safe_load((REPO_ROOT / "pricing.yaml").read_text())
    )


def _known_parts() -> set[str]:
    # Equipment ids, container shell PNs, and plate PNs (-D = defense build)
    manifest = build_manifest()
    shells = {
        yaml.safe_load(p.read_text())["shell"]["part_number"]
        for p in (REPO_ROOT / "assemblies").glob("*-container/*/bom.yaml")
    }
    plates = {
        f"ARC-PLT-{pid}-001{suffix}" for pid in manifest.plates for suffix in ("", "-D")
    }
    return set(manifest.specs) | shells | plates


def test_every_priced_key_is_a_part_and_prices_from_qty_one() -> None:
    # Arrange
    book = _book()

    # Act
    unknown = set(book.prices) - _known_parts()
    no_qty_one = [k for k, breaks in book.prices.items() if breaks[0].min_qty != 1]

    # Assert
    assert (unknown, no_qty_one) == (set(), [])


def test_manifest_points_at_the_price_list() -> None:
    # Act
    actual = build_manifest().pricing

    # Assert
    assert actual == "s3://arcnode-artifacts/pricing.yaml"
