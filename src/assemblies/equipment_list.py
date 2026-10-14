"""Per-variant equipment list: the one source for a container's BOM parts and topology.

Every physical device in a container is one Instance with a container-local
tag. bom.yaml `parts` are counted from this list and topology.yaml `devices`
are written from it, so the two can't disagree. edp-api prefixes the
container (C1, G2) to make each tag site-unique.
"""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import yaml

EQUIPMENT_DIR: Final[Path] = Path(__file__).resolve().parents[2] / "equipment"
PROVISIONED: Final[str] = "PROVISIONED_AT_COMMISSIONING"


@dataclass(frozen=True)
class Instance:
    """One physical device in a container."""

    tag: str  # container-local, e.g. PDU-A1
    equipment_id: str
    template: str  # edp-api device template
    networked: bool  # polled by the EMS: gets a commissioning-time address


# GPU node part + its edp-api template, per GPU type
_B200: Final[tuple[str, str]] = ("CMP-NODE-001", "gpu_node")
_H100: Final[tuple[str, str]] = ("CMP-NODE-002", "gpu_node_h100")


def _compute(node: tuple[str, str], dry_cooler: Instance) -> list[Instance]:
    return [
        Instance("RACK-1", "CMP-RACK-001", "rack", False),
        Instance("PNL-1", "CMP-PNL-001", "panelboard", False),
        *[Instance(f"NODE-{i}", node[0], node[1], True) for i in range(1, 8)],
        Instance("CDU-1", "CMP-CDU-001", "cdu", True),
        Instance("SW-DATA-1", "CMP-SWITCH-001", "network_switch", True),
        Instance("SW-MGMT-1", "CMP-SWITCH-003", "mgmt_switch", False),
        # ADR-005: A/B dual-path, 3 PDUs per path
        *[
            Instance(f"PDU-{path}{i}", "CMP-PDU-001", "pdu", True)
            for path in ("A", "B")
            for i in range(1, 4)
        ],
        dry_cooler,
    ]


_GRID_FEEDER: Final[list[Instance]] = [
    Instance("SWG-1", "GRD-SWG-001", "switchgear", False),
    Instance("RLY-1", "GRD-RLY-001", "protective_relay", True),
    Instance("T1", "GRD-XFM-001", "transformer", False),
    Instance("SWBD-1", "GRD-LVS-001", "lv_switchboard", False),
    Instance("SW-MGMT-1", "GRD-SWITCH-001", "grid_mgmt_switch", False),
]
# ADR-020: the POI meter ships loose with the primary, installed at the service
_POI_METER: Final[Instance] = Instance("MTR-POI", "GRD-MTR-001", "poi_meter", True)
# ADR-022: the dc-ext PCS pair ships with each dc-ext grid container, to the pad
_PCS_PAIR: Final[list[Instance]] = [
    Instance(f"PCS-{i}", "GRD-PCS-001", "pcs", False) for i in (1, 2)
]

_DC: Final[Instance] = Instance("DC-1", "EXT-DC-001", "dc_external", True)
_DC_DOD: Final[Instance] = Instance("DC-1", "EXT-DC-002", "dc_external_dod", False)
COMPUTE: Final[dict[str, list[Instance]]] = {
    "commercial-ac": _compute(_B200, _DC),
    "commercial-ac-h100": _compute(_H100, _DC),
    "defense-ac": _compute(_B200, _DC_DOD),
    "defense-ac-h100": _compute(_H100, _DC_DOD),
}
# Module template where it isn't edp-api's default for the assembly type:
# an H100 container's GPU power cap must target H100 nodes.
MODULE_TEMPLATE: Final[dict[str, str]] = {
    "commercial-ac-h100": "compute_module_h100",
    "defense-ac-h100": "compute_module_h100",
}
GRID: Final[dict[str, list[Instance]]] = {
    "commercial-ac": [*_GRID_FEEDER, _POI_METER],
    "defense-ac": [*_GRID_FEEDER, _POI_METER],
    "commercial-dc-ext": [*_GRID_FEEDER, _POI_METER, *_PCS_PAIR],
    "feeder": _GRID_FEEDER,
    "defense-feeder": _GRID_FEEDER,
    "dc-ext-feeder": [*_GRID_FEEDER, *_PCS_PAIR],
}


def bom_parts(instances: list[Instance]) -> list[dict]:
    """bom.yaml `parts`: qty per equipment_id, in first-seen order."""
    counts = Counter(i.equipment_id for i in instances)
    return [{"equipment_id": eid, "qty": qty} for eid, qty in counts.items()]


def topology(instances: list[Instance], module_template: str | None = None) -> dict:
    """topology.yaml body: one device per instance, plus the grid's AC bus."""
    devices = []
    for inst in instances:
        device: dict = {
            "template": inst.template,
            "tag": inst.tag,
            "description": f"{_model(inst.equipment_id)} ({inst.equipment_id})",
        }
        if inst.networked:
            device["connection"] = {"host": PROVISIONED, "port": PROVISIONED}
        devices.append(device)
    body: dict = {"devices": devices, "buses": _buses(instances)}
    if module_template is not None:
        body = {"module_template": module_template, **body}
    return body


def write_topology(
    instances: list[Instance], path: Path, module_template: str | None = None
) -> None:
    """Write topology.yaml for one variant."""
    header = "# Generated from src/assemblies/equipment_list.py — edit there.\n"
    body = topology(instances, module_template)
    path.write_text(header + yaml.safe_dump(body, sort_keys=False))


def _buses(instances: list[Instance]) -> list[dict]:
    """Grid AC bus: the relay (and POI meter) watch the switchgear's line."""
    templates = [i.template for i in instances]
    if "switchgear" not in templates:
        return []
    members = [{"device_template": "switchgear", "port": "line_out"}]
    if "poi_meter" in templates:
        members.append({"device_template": "poi_meter", "port": "voltage_in"})
    members.append({"device_template": "protective_relay", "port": "line_in"})
    return [{"bus_id": "ac_main", "type": "ac", "members": members}]


def _model(equipment_id: str) -> str:
    spec = yaml.safe_load((EQUIPMENT_DIR / equipment_id / "spec.yaml").read_text())
    return f"{spec['vendor']} {spec['model_number'].split(' (')[0]}"
