"""Alarm spec model tests.

Verifies discriminated-union dispatch + round-trip parsing of pilot
spec.yaml alarm catalogs.
"""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from src.alarms.alarm_spec import (
    Alarm,
    AlarmPriority,
    AnalogThresholdSource,
    DiscreteRegisterSource,
    DnpEventSource,
    RedfishEventSource,
    Reset,
    SnmpTrapSource,
    load_alarms,
)

EQUIPMENT_DIR = Path(__file__).resolve().parents[2] / "equipment"


def _alarm_dict(condition_source: dict) -> dict:
    """One well-formed alarm dict with the given condition_source slot."""
    return {
        "id": "test_alarm",
        "description": "test alarm",
        "condition_source": condition_source,
        "priority": "P2",
        "operator_action": "do the thing",
        "on_delay_ms": 100,
        "off_delay_ms": 0,
        "reset": "latched",
        "reference_doc": "TEST-001 manual §1",
    }


def test_discriminator_routes_to_discrete_register_variant() -> None:
    # Arrange
    raw = _alarm_dict(
        {"type": "discrete_register", "address": 30001, "meaning_when_set": "alarm"}
    )

    # Act
    alarm = Alarm.model_validate(raw)

    # Assert
    assert isinstance(alarm.condition_source, DiscreteRegisterSource)
    assert alarm.condition_source.address == 30001


def test_discriminator_routes_to_each_of_five_variants() -> None:
    # Arrange / Act / Assert — one round-trip per condition_source variant.
    variants: list[tuple[dict, type]] = [
        (
            {
                "type": "discrete_register",
                "address": 1,
                "meaning_when_set": "alarm",
            },
            DiscreteRegisterSource,
        ),
        (
            {
                "type": "analog_threshold",
                "address": 2,
                "threshold": 55.0,
                "direction": "above",
                "unit": "celsius",
            },
            AnalogThresholdSource,
        ),
        ({"type": "snmp_trap", "oid": "1.3.6.1.4.1.1718"}, SnmpTrapSource),
        (
            {"type": "dnp_event", "point_index": 10, "point_type": "binary_input"},
            DnpEventSource,
        ),
        (
            {"type": "redfish_event", "event_id": "PumpFailure"},
            RedfishEventSource,
        ),
    ]
    for cs, expected_type in variants:
        alarm = Alarm.model_validate(_alarm_dict(cs))
        assert isinstance(alarm.condition_source, expected_type)


def test_priority_and_reset_enum_round_trip() -> None:
    # Arrange
    raw = _alarm_dict(
        {"type": "discrete_register", "address": 1, "meaning_when_set": "alarm"}
    )
    raw["priority"] = "P1"
    raw["reset"] = "auto"

    # Act
    alarm = Alarm.model_validate(raw)

    # Assert
    assert alarm.priority == AlarmPriority.P1
    assert alarm.reset == Reset.AUTO


def test_unknown_condition_source_type_rejected() -> None:
    # Arrange
    raw = _alarm_dict({"type": "carrier_pigeon", "color": "grey"})

    # Act / Assert
    with pytest.raises(ValidationError):
        Alarm.model_validate(raw)


def test_extra_field_on_alarm_rejected() -> None:
    # Arrange
    raw = _alarm_dict(
        {"type": "discrete_register", "address": 1, "meaning_when_set": "alarm"}
    )
    raw["sneaky_extra"] = "not allowed"

    # Act / Assert
    with pytest.raises(ValidationError):
        Alarm.model_validate(raw)


@pytest.mark.parametrize(
    "equipment_id",
    ["GRD-SWG-001", "EXT-BESS-002", "CMP-CDU-001"],
)
def test_pilot_spec_alarms_parse(equipment_id: str) -> None:
    """Real pilot spec.yaml files parse without error and have at least one alarm."""
    # Arrange
    spec_path = EQUIPMENT_DIR / equipment_id / "spec.yaml"
    spec_dict = yaml.safe_load(spec_path.read_text())

    # Act
    alarms = load_alarms(spec_dict)

    # Assert
    assert len(alarms) >= 1
    for alarm in alarms:
        assert alarm.id
        assert alarm.operator_action
        assert alarm.reference_doc
