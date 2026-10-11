"""Every container variant's BOM names the ISO shell it's built in."""

from src.assemblies import compute_container, grid_container


def test_every_container_bom_carries_its_shell() -> None:
    # Arrange
    boms = {
        **{f"compute/{v}": b for v, b in compute_container.BOM_BY_VARIANT.items()},
        **{f"grid/{v}": b for v, b in grid_container.BOM_BY_VARIANT.items()},
    }

    # Act
    actual = {name: bom["shell"]["part_number"] for name, bom in boms.items()}

    # Assert
    expected = {
        name: "ARC-CNT-CMP-001" if name.startswith("compute/") else "ARC-CNT-GRD-001"
        for name in boms
    }
    assert actual == expected
