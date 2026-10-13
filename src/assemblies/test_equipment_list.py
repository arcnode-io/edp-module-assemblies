"""Equipment lists: one tag per device, and BOM + topology agree by construction."""

from collections import Counter

import pytest

from src.assemblies import compute_container, grid_container
from src.assemblies.equipment_list import (
    COMPUTE,
    EQUIPMENT_DIR,
    GRID,
    Instance,
    topology,
)

_ALL: list[tuple[str, list[Instance]]] = [
    *[(f"compute/{v}", i) for v, i in COMPUTE.items()],
    *[(f"grid/{v}", i) for v, i in GRID.items()],
]


@pytest.mark.parametrize(("variant", "instances"), _ALL)
def test_every_device_has_its_own_tag(variant: str, instances: list[Instance]) -> None:
    # Act
    repeated = [t for t, n in Counter(i.tag for i in instances).items() if n > 1]

    # Assert
    assert repeated == []


@pytest.mark.parametrize(("variant", "instances"), _ALL)
def test_every_device_has_an_equipment_spec(
    variant: str, instances: list[Instance]
) -> None:
    # Act
    missing = [
        i.equipment_id
        for i in instances
        if not (EQUIPMENT_DIR / i.equipment_id / "spec.yaml").exists()
    ]

    # Assert
    assert missing == []


@pytest.mark.parametrize(
    ("boms", "lists"),
    [
        (compute_container.BOM_BY_VARIANT, COMPUTE),
        (grid_container.BOM_BY_VARIANT, GRID),
    ],
)
def test_bom_parts_are_the_equipment_list_counted(
    boms: dict[str, dict], lists: dict[str, list[Instance]]
) -> None:
    # Act
    actual = {
        v: {p["equipment_id"]: p["qty"] for p in bom["parts"]}
        for v, bom in boms.items()
    }

    # Assert
    expected = {v: dict(Counter(i.equipment_id for i in lists[v])) for v in boms}
    assert actual == expected


def test_topology_lists_every_device_with_its_tag() -> None:
    # Arrange
    instances = COMPUTE["commercial-ac"]

    # Act
    devices = topology(instances)["devices"]

    # Assert — passive gear has no connection; polled gear waits for commissioning
    by_tag = {d["tag"]: d for d in devices}
    assert len(devices) == len(instances)
    assert "connection" not in by_tag["PNL-1"]
    assert by_tag["PDU-B3"]["connection"]["host"] == "PROVISIONED_AT_COMMISSIONING"
