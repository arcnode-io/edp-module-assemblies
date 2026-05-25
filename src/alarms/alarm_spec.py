"""Alarm catalog per equipment SKU — Hollifield D&R captured in spec.yaml.

Each equipment spec.yaml has a top-level `spec.alarms[]` block declaring
the abnormal conditions that SKU can raise. This module provides the
canonical Pydantic models; downstream consumers (ems-device-api AsyncAPI
emitter, ems-industrial-gateway alarm poll task, ems-hmi alarm renderer)
mirror these shapes.

Design notes:
- `condition_source` is a discriminated union over the five transport
  patterns in active use across the catalog: Modbus discrete register,
  Modbus analog threshold, SNMP trap, DNP3 event, Redfish event.
- `priority` is a 4-tier enum per Hollifield §7.19. The "~3 P1 max per
  SKU" guidance is operator discipline, NOT enforced here — switchgear
  legitimately can have 4+ P1 (arc-flash, ground-fault, overvoltage-trip,
  breaker-failure). Reviewers challenge outliers in CR.
- `operator_action` is required. Hollifield §A4 step 4: if you can't
  write one, the alarm shouldn't exist.
- `on_delay_ms`, `off_delay_ms`, `reset` are required — chatter
  suppression + ack behavior define the alarm, can't be hand-waved.
"""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class AlarmPriority(StrEnum):
    """4-tier alarm priority per Hollifield §7.19."""

    P1 = "P1"  # safety / people
    P2 = "P2"  # equipment damage avoidance
    P3 = "P3"  # process deviation
    P4 = "P4"  # diagnostic / advisory


class Reset(StrEnum):
    """Clear behavior when the underlying condition returns to normal."""

    LATCHED = "latched"  # asserts until operator ack
    AUTO = "auto"  # clears on return-to-normal


class DiscreteRegisterSource(BaseModel):
    """One Modbus discrete/holding register bit is the trigger."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["discrete_register"]
    address: int = Field(ge=0)  # matches ModbusBinding.address convention
    meaning_when_set: Literal["alarm", "clear"]


class AnalogThresholdSource(BaseModel):
    """Modbus analog register crosses a threshold."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["analog_threshold"]
    address: int = Field(ge=0)
    threshold: float
    direction: Literal["above", "below"]
    unit: str
    deadband_pct: float | None = Field(default=None, ge=0)


class SnmpTrapSource(BaseModel):
    """SNMP trap OID is the trigger (PDU thermal, switch port-down)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["snmp_trap"]
    oid: str


class DnpEventSource(BaseModel):
    """DNP3 event point is the trigger (protective relay, OE)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["dnp_event"]
    point_index: int = Field(ge=0)
    point_type: Literal["binary_input", "analog_input"]


class RedfishEventSource(BaseModel):
    """Redfish event identifier is the trigger (GPU node, CDU)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["redfish_event"]
    event_id: str
    severity: Literal["OK", "Warning", "Critical"] | None = None


ConditionSource = Annotated[
    DiscreteRegisterSource
    | AnalogThresholdSource
    | SnmpTrapSource
    | DnpEventSource
    | RedfishEventSource,
    Field(discriminator="type"),
]


class Alarm(BaseModel):
    """One alarm definition per Hollifield D&R rationalization step."""

    model_config = ConfigDict(extra="forbid")

    id: str
    description: str
    condition_source: ConditionSource
    priority: AlarmPriority
    operator_action: str
    on_delay_ms: int = Field(ge=0)
    off_delay_ms: int = Field(ge=0)
    reset: Reset
    reference_doc: str


def load_alarms(spec_dict: dict) -> list[Alarm]:
    """Parse `spec.alarms[]` from a loaded spec.yaml dict.

    Returns an empty list when the SKU has no alarm catalog yet (specs
    are migrated incrementally). Raises ValidationError on malformed
    entries — fail fast at parse time.
    """
    alarms_raw = spec_dict.get("spec", {}).get("alarms") or []
    return [Alarm.model_validate(a) for a in alarms_raw]
