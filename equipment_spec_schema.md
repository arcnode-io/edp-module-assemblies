# ARCNODE Equipment Spec Schema

---

## 1. Purpose and Scope

Every piece of OTS equipment specified for use in an ARCNODE deployment is described by an `equipment_spec` — a structured YAML document that captures the equipment's identity, electrical/thermal/mechanical/port characteristics, geometry, and provenance.

This document defines the canonical schema. It is the coupling contract between the equipment library curation pipeline (which writes `equipment_spec` files) and every downstream consumer (sizing engine, BOM generator, drawing generator, document generator).

The equipment_spec is read-only at runtime. It is authored once per equipment SKU through the curation pipeline, reviewed by a human, and locked. Downstream automation trusts it.

---

## 2. System Architecture Context

```
                ┌─────────────────────────┐
   Vendor       │ Equipment Library       │   Sizing Engine
   datasheet ──▶│ Curation Pipeline       │──▶ BOM Generator
   Vendor STEP  │  (skill + script + human) │   Drawing Generator
                │                         │   Document Generator
                └─────────────────────────┘   EMS Configurator
                          │
                          ▼
                   equipment_spec.yaml
                   equipment_envelope.step
                   service_envelope.step
```

The curation pipeline (see Equipment Curation Pipeline doc) produces the spec files. This schema defines their shape.

The equipment library lives in its own repository, separate from EWA templates and ARCNODE pipeline code. Schema versioning is deferred to v0 — there is one schema, the one defined here, and it is what every spec must conform to.

---

## 3. File Format and Naming

### 3.1 Format

YAML. Human-readable for review, machine-parseable for tooling. JSON Schema (`equipment_spec.schema.json`) is generated from this document and is the runtime validation artifact.

### 3.2 File naming

```
{equipment_id}.yaml

Examples:
  GRD-PCS-001.yaml    Grid Container, PCS class, sequence 001
  CMP-RACK-003.yaml   Compute Container, rack class, sequence 003
  CMP-CDU-001.yaml    Compute Container, CDU class, sequence 001
  EXT-BESS-001.yaml   External equipment, BESS class, sequence 001
  EXT-DRYC-001.yaml   External equipment, dry cooler class, sequence 001
```

### 3.3 Equipment ID convention

```
{container}-{category}-{sequence}

container: GRD | CMP | EXT     (3-letter, uppercase)
           GRD = Grid Container
           CMP = Compute Container
           EXT = External customer-supplied equipment
category:  4-letter category code, uppercase
sequence:  3-digit zero-padded, sequential within (container, category)
```

ARCNODE is a two-container product. The `EXT` prefix is used for customer-supplied external equipment that ARCNODE interfaces with but does not contain — BESS, dry coolers, adiabatic coolers — and cross-container commodity hardware.

---

## 4. Schema Definition

### 4.1 Top-level structure

```yaml
equipment_id: string              # GRD-PCS-001
schema_version: string            # "0"
category: enum                    # see §4.2
vendor: string
model_number: string
description: string               # one-line summary
datasheet_url: url                # vendor source PDF
datasheet_hash: string            # SHA-256, for refresh detection
step_source: url | null           # null if STEP unavailable
fab_tier: enum                    # commercial | federal_civilian | dod_eligible
restricted_entities: [enum] | null  # DOD_1260H | BIS_ENTITY_LIST | NDAA_889 |
                                  # state_owned_china | state_owned_russia
                                  # — null means none known; populated when
                                  # vendor or component is on a restricted list
install_video_url: url | null     # vendor-published install / unboxing video
                                  # for site installers; surfaced on BOM xlsx.
                                  # null = not yet researched.
lead_time_weeks: int | null
unit_cost_usd: float | null

spec:                             # see §4.3 — sparse per category
  electrical: {...} | null
  thermal:    {...} | null
  mechanical: {...}                # always required
  ports:      [...] | null
  control:    {...} | null

geometry:                         # see §4.4
  source: enum                    # extracted | synthesized | traced
  fidelity: enum                  # featured | bounding_box
  equipment_envelope_path: path
  service_envelope_path: path
  bounding_box: {...}
  service_clearance: {...}

provenance:                       # see §4.5
  authored_by: string             # operator handle or "skill:datasheet_extractor"
  authored_date: ISO8601
  reviewed_by: string             # human reviewer handle, required
  reviewed_date: ISO8601
  confidence_flags: [...] | null

notes: string | null              # free text, gotchas, deployment caveats
```

### 4.2 Category enum

```
rack            — server or network rack chassis (19"/23" standard)
                  (NOT BESS — see `bess` for external battery storage)
pcs             — Power Conversion System (bidirectional inverter)
pdu             — Power Distribution Unit
ups             — Uninterruptible Power Supply
switchgear      — protective switching device
transformer     — voltage transformer (LV/MV)
bess            — external customer-supplied Battery Energy Storage System
                  (Tesla Megapack, CATL EnerOne, Fluence Cube, etc.). Sited
                  on customer pad, not inside ARCNODE container. Interface-
                  scoped spec only — customer owns siting, civils, internal
                  architecture, thermal management, and BMS. ARCNODE
                  specifies the DC bus and comms interface only.
cdu             — Coolant Distribution Unit
chiller         — refrigeration chiller
dry_cooler      — outdoor heat rejection (dry-air, no water supply required)
adiabatic_cooler — outdoor heat rejection with adiabatic / spray-assist mode
                   (requires pad-side treated water supply; can run dry below
                   switchover ambient. Frigel-class equipment.)
manifold        — coolant distribution manifold
gpu_node        — GPU compute node (component of a rack)
network_switch  — Ethernet/IB switch
serial_gateway  — serial-to-Ethernet gateway
bms             — Battery Management System controller (note: typically
                  internal to a `bess` unit; this category is for standalone
                  BMS hardware in non-bess applications)
sensor          — instrumentation (flow, temp, pressure, etc.)
connector       — electrical or fluid connector
cable           — pre-terminated cable assembly
hose            — pre-terminated hose assembly
plate           — mounting plate (non-ARCNODE custom)
fastener        — bolt, nut, washer, anchor
```

New categories require a schema revision. Don't add ad hoc.

### 4.3 Spec subsections — required matrix

The `spec` block is sparse. Which subsections are required depends on category. The validator enforces this.

| Category       | electrical | thermal | mechanical | ports | control |
|----------------|------------|---------|------------|-------|---------|
| rack           | required   | optional| required   | required | optional |
| pcs            | required   | required| required   | required | required |
| pdu            | required   | optional| required   | required | optional |
| ups            | required   | optional| required   | required | optional |
| switchgear     | required   | n/a     | required   | required | optional |
| transformer    | required   | optional| required   | required | n/a     |
| bess           | required   | optional| required   | required | required |
| cdu            | required   | required| required   | required | required |
| chiller        | required   | required| required   | required | required |
| dry_cooler     | required   | required| required   | required | optional |
| adiabatic_cooler | required | required| required   | required | optional |
| manifold       | n/a        | required| required   | required | n/a     |
| gpu_node       | required   | required| required   | required | optional |
| network_switch | required   | optional| required   | required | optional |
| serial_gateway | required   | n/a     | required   | required | optional |
| bms            | required   | n/a     | required   | required | required |
| sensor         | required   | optional| required   | required | required |
| connector      | optional   | optional| required   | required | n/a     |
| cable          | required   | n/a     | required   | required | n/a     |
| hose           | n/a        | required| required   | required | n/a     |
| plate          | n/a        | n/a     | required   | optional | n/a     |
| fastener       | n/a        | n/a     | required   | n/a   | n/a     |

`n/a` means the field must be omitted (or explicitly `null`). `optional` means it may be present and is consumed if present.

### 4.4 Spec subsection field definitions

```yaml
electrical:
  voltage_v: float                # nominal
  voltage_range_v: [min, max] | null
  current_a: float                # nominal
  phase: enum                     # dc | 1ph | 3ph
  frequency_hz: float | null      # null for DC
  power_kw: float
  power_factor_range: [min, max] | null   # leading-most to lagging-most;
                                          # full 4-quadrant captured as [-1.0, 1.0]
  efficiency_pct: float | null
  breaker_size_a: float | null
  aic_rating_ka: float | null
  thd_pct: float | null
  fault_current_contribution_pu: float | null   # for grid-forming devices
                                                # see §6.1 — vendor-published only

thermal:
  heat_load_kw: float | null      # heat generated
  heat_rejection_kw: float | null # heat removed (chillers, CDUs)
  coolant_compatibility: [enum] | null
                                  # list of supported fluids; populated for any
                                  # equipment in the coolant path. Enum values:
                                  # water | egw_25 | egw_30 | egw_40 | egw_50 |
                                  # pgw_20 | pgw_25 | pgw_30 | pgw_50 |
                                  # dielectric | air
  flow_rate_lpm: float | null
  supply_temp_c: float | null
  return_temp_c: float | null
  pump_head_kpa: float | null     # pump delivery pressure capability
                                  # (populated for active equipment with pumps)
  internal_pressure_drop_kpa: float | null
                                  # pressure loss through the unit at rated flow
                                  # (populated for any equipment in the coolant
                                  # path, active or passive)
  port_size_dn: int | null        # nominal pipe diameter, mm

mechanical:
  weight_kg: float
  dimensions_mm: [L, W, H]        # always L × W × H, vendor orientation
  container_type: enum | null      # 10ft_ISO_high_cube | 20ft_ISO_high_cube | null
                                  # populated for equipment installed inside an
                                  # ARCNODE container; null for external/pad equipment
  mounting: enum                  # rack_19 | rack_23 | floor | wall | pad |
                                  # rail | ceiling | proprietary_oem
  mounting_notes: string | null   # free text — required when
                                  # mounting == proprietary_oem
  rack_units: int | null          # for rack_19 / rack_23
  ip_rating: string | null        # e.g., "IP55"; null = no rating claimed
  lift_points: int | null
  ambient_temp_range_c: [min, max] | null
  max_elevation_m: int | null
  noise_dba_at_1m: float | null

ports:
  - port_id: string               # local ID, e.g., "AC1", "DC+", "ETH0"
    type: enum                    # ac_power | dc_power | control_power |
                                  # coolant_supply | coolant_return |
                                  # ethernet | infiniband | fiber | serial | can | usb |
                                  # dry_contact | signal_analog |
                                  # signal_digital | comms_other
                                  #
                                  # infiniband: NDR/HDR/EDR InfiniBand fabric ports
                                  # (QM9700, QM8790 class switches). Use this rather
                                  # than ethernet for IB-native ports.
                                  #
                                  # control_power: a port that accepts control-
                                  # supply power, often multi-mode (e.g., "120
                                  # VAC, 240 VAC, or 24 VDC"). Use this rather
                                  # than enumerating ac_power/dc_power variants.
    role: enum                    # input | output | bidirectional
    connector_spec: string        # e.g., "M12 D-coded female", "Parker BH series 1/2 NPT"
    mating_part: string | null    # vendor part for the mating side, if specified
    qty: int                      # how many of this port type on this equipment

control:
  protocol: enum                  # modbus_tcp | modbus_rtu | dnp3 | iec61850 |
                                  # snmp | redfish | bacnet_ip | bacnet_mstp |
                                  # proprietary | none
  register_map_url: url | null    # link to register/object dictionary doc
  command_latency_ms: float | null
  step_response_ms: float | null
  control_modes: [string]         # free-form list of modes the device supports
                                  # for PCS: ["grid_following", "grid_forming", "vf", "pq", "statcom"]
  black_start_capable: bool | null

geometry:
  source: enum                    # extracted | synthesized | traced
                                  #   extracted   = from vendor STEP via envelope_extractor
                                  #   synthesized = from datasheet dimensions via envelope_synthesizer
                                  #   traced      = from datasheet drawings via Sub-pipeline 3B
  fidelity: enum                  # featured | bounding_box
                                  #   featured     = port stubs + protrusions captured
                                  #   bounding_box = outer envelope only
  equipment_envelope_path: path   # relative to equipment library root
  service_envelope_path: path
  bounding_box:                   # axis-aligned, for fast checks
    L_mm: float
    W_mm: float
    H_mm: float
  service_clearance:              # directional, mm
    front: float
    rear: float
    left: float
    right: float
    top: float
    bottom: float
    install_clearance:            # optional — temporary clearance for crane/rigging
      direction: enum
      value_mm: float
    | null

provenance:
  authored_by: string
  authored_date: ISO8601
  reviewed_by: string             # required, must be a human handle
  reviewed_date: ISO8601
  confidence_flags:               # list of fields with extraction confidence issues
    - field: string               # dotted path, e.g., "spec.electrical.thd_pct"
      flag: enum                  # missing | ambiguous | conflicts_with_product_page |
                                  # assumed_default | low_confidence_extraction
      note: string | null
```

### 4.5 Provenance and confidence flags

Every spec carries provenance. Two fields are mandatory: `authored_by` and `reviewed_by`. The reviewer handle must be a human, not a skill. Skill-authored specs without human review do not enter the library.

`confidence_flags` is a list. Each flag identifies a specific field that needed attention during authoring. The defined flag values:

```
missing                         — field not found in source documents
ambiguous                       — multiple possible values found, picked one
conflicts_with_product_page     — datasheet and product page disagreed
assumed_default                 — value not stated, industry default applied
low_confidence_extraction       — skill flagged its own extraction as uncertain
```

These flags drive the human review queue in the curation pipeline. Once reviewed, flags can remain on the spec (as audit trail) but downstream tools should treat reviewed specs as authoritative regardless of flag presence.

### 4.6 Fab tier and restricted entities

`fab_tier` is the deployment-eligibility classification of the equipment. Three values:

```
commercial         — no sourcing restrictions; broadly available; appropriate
                     for commercial datacenter deployments where the customer
                     does not face federal procurement constraints.
federal_civilian   — eligible for non-DOD federal civilian procurement.
                     Acceptable today even with Chinese cells/components,
                     subject to NDAA Section 889 and BIS Entity List
                     compliance documentation.
dod_eligible       — eligible for DOD procurement and classified deployments.
                     Must clear DOD 1260H, NDAA 889, and any active export-
                     control restrictions. The strictest tier.
```

The previous binary `commercial | itar_domestic` framing was too coarse — most "domestic" equipment uses imported components, and most "Chinese" equipment is eligible in commercial and many federal civilian deployments. The three-tier model matches the real procurement landscape.

`restricted_entities` is an optional list capturing specific regulatory exposures:

```
DOD_1260H              — Vendor or critical component is on the DOD 1260H
                         "Chinese Military Companies" list. Triggers DOD
                         procurement restrictions starting January 2027.
                         CATL is on this list as of 2024.
BIS_ENTITY_LIST        — Vendor or component is on the Bureau of Industry
                         and Security Entity List. Export-controlled.
NDAA_889               — Vendor matches an NDAA Section 889 named entity
                         (Huawei, ZTE, Hikvision, Dahua, Hytera) or
                         affiliate.
state_owned_china      — Vendor is a Chinese state-owned enterprise.
                         Soft flag; does not automatically disqualify but
                         affects sourcing risk assessment.
state_owned_russia     — Vendor is a Russian state-owned enterprise.
```

Sizing engine consults both `fab_tier` and `restricted_entities` against deployment context. A `dod_eligible` deployment refuses any equipment with a non-null `restricted_entities` list. A `commercial` deployment accepts everything. A `federal_civilian` deployment accepts most, with documentation.

The schema does not encode all possible restriction lists exhaustively — the goal is the common cases. Add new entries as deployments surface them.

---

## 5. Validation Rules

### 5.1 Hard rules (validator fails)

1. `equipment_id` matches the file name and the convention in §3.3.
2. `category` is in the enum from §4.2.
3. The required spec subsections per category (§4.3) are present.
4. `provenance.reviewed_by` is non-empty and not a skill handle.
5. `geometry.source` and `geometry.fidelity` are populated.
6. `geometry.equipment_envelope_path` and `geometry.service_envelope_path` resolve to existing files.
7. All `port_id` values within a single spec are unique.
8. No two specs share an `equipment_id`.
9. If `spec.mechanical.mounting == proprietary_oem`, `spec.mechanical.mounting_notes` must be non-null.

### 5.2 Soft rules (validator warns)

1. `unit_cost_usd` is null or absent — prompt during sizing engine cost estimation.
2. `lead_time_weeks` is null or absent — prompt during procurement planning.
3. `geometry.fidelity == bounding_box` and category is in {pcs, cdu, gpu_node} — these high-port-density categories benefit from `featured` fidelity.
4. `confidence_flags` contains any unresolved `missing` flags.
5. `step_source` is null but `geometry.source == extracted` — provenance contradiction.

---

## 6. Per-Category Authoring Notes

Notes that apply to specific categories during authoring. Not exhaustive; updated as patterns emerge.

### 6.1 PCS

- `control.control_modes` must explicitly list `grid_forming` if the vendor documents grid-forming capability. Marketing phrases like "grid support" or "voltage regulation" are not sufficient — confirm explicit GFM in datasheet or interconnect manual. Acceptable evidence includes datasheet entries for "V&f islanded mode", "grid-forming control", "virtual synchronous machine", or equivalent.
- `electrical.fault_current_contribution_pu` is required *if vendor publishes it* for grid-forming PCS. If not published, leave null and add `confidence_flags` entry with flag `missing` — the value will be needed eventually for fault studies and is a sales-touch follow-up item.
- `thermal` subsection required because PCS units are significant heat sources whose rejection has to integrate with the Compute Container CDU loop (cross-container coupling — see `equipment/GRD-PCS-001/spec.yaml` notes for the PD500 selection rationale).
- `electrical.power_factor_range` should typically be `[-1.0, 1.0]` for modern 4-quadrant PCS. Single-quadrant or limited-range devices are unusual at this product class — flag as ambiguous if vendor docs are unclear.
- `mounting: proprietary_oem` is common for PCS at non-standard widths. Capture vendor cabinet model in `mounting_notes` when known.

### 6.2 BESS

- BESS is **external customer-supplied equipment** in ARCNODE's architecture. The equipment_spec is interface-scoped — captures only what ARCNODE needs to integrate over the DC bus and comms.
- `electrical.voltage_range_v` must overlap with the Grid Module PCS DC input range. For PD500, that's 310–1250 VDC; for sovereign deployments using GFM-capable PCS, the BESS voltage class drives PCS selection.
- `electrical.power_kw` is the rated discharge power, not the energy capacity. Energy capacity (kWh) is captured in `notes` for now — schema does not yet have an energy field. (Defer until a real sizing decision forces it.)
- `control.protocol` — Modbus TCP is most common at the system level for utility-scale BESS (Tesla, Fluence, Sungrow, etc.). CAN exists internally but is typically not exposed to external integrators. Use `modbus_tcp` unless vendor docs state otherwise.
- `thermal` subsection is `n/a` — the BESS handles its own thermal management externally. ARCNODE does not couple to BESS cooling.
- `mechanical.dimensions_mm` and `weight_kg` are captured for customer site planning reference, not for ARCNODE container fit. No service envelope or mounting detail beyond `mounting: pad`.
- `fab_tier` and `restricted_entities` matter most in this category. BESS is the largest single line item in many deployments and the most regulated. CATL is on DOD 1260H; Tesla Megapack uses mixed-source cells with documented provenance; sovereign deployments need careful flagging.

### 6.3 GPU node

- `thermal.heat_load_kw` is the maximum, not TDP. Vendor TDP is a lower bound.
- `electrical.power_kw` is grid-side draw including PSU efficiency, not the silicon-side number.

### 6.4 CDU

- `thermal.heat_rejection_kw` is the rated capacity, not a momentary peak.
- `thermal.flow_rate_lpm` and `thermal.pressure_drop_kpa` together define the pump curve operating point.

### 6.5 Connector / cable / hose

- `mechanical.weight_kg` is per unit, not per spool or per box.
- `ports` list captures the connector at each end (typically two entries for cable/hose).

### 6.6 Adiabatic cooler

- `ports[]` must include a `water_supply` and `water_drain` entry in addition to the coolant loop ports — the adiabatic mode requires pad-side treated water and a drain. This is the defining interface difference vs `dry_cooler`.
- Capacity has two operating regimes: dry-mode capacity (low-ambient) and adiabatic-mode capacity (high-ambient). Capture both as separate `heat_rejection_kw` values in `notes` if the schema's single field cannot represent the bimodal behavior. Future schema work may split this.
- `control.control_modes` should list `dry_mode` and `adiabatic_mode` explicitly, plus the switchover threshold if vendor-published.
- For ARCNODE off-grid / sovereign deployments where pad water supply is not part of the customer civil works, adiabatic coolers are architecturally inappropriate. Sizing engine should refuse to select an adiabatic_cooler unless the deployment context explicitly enables water supply.

### 6.7 BESS (external)

- BESS is customer-supplied equipment sited on the customer's pad, not inside ARCNODE. The equipment_spec is interface-scoped: capture only what ARCNODE's Grid Module PCS, EMS, and pad civil works need to integrate.
- `electrical.voltage_v` and `voltage_range_v` are the DC bus operating range. Must overlap with the selected Grid Module PCS DC input range; sizing engine validates compatibility.
- `electrical.power_kw` is rated discharge power, not energy capacity. Capture energy capacity in `notes` since the schema doesn't have a dedicated energy field (kWh is fundamentally different from kW; treat as deployment-level sizing concern, not equipment_spec field).
- `thermal` subsection is optional and typically omitted. External BESS handles its own thermal management; ARCNODE does not couple to BESS cooling.
- `control.protocol` is the supervisory interface — typically Modbus TCP for utility-scale BESS. The internal BMS protocol (CAN, vendor-proprietary) is the BESS vendor's concern, not ARCNODE's.
- `control.control_modes` must indicate grid-forming compatibility if the BESS is intended to support black-start with the Grid Module PCS. Most modern utility BESS are grid-following only and rely on a paired PCS for grid-forming behavior.
- `mechanical.mounting` is `pad`. Dimensions are for site planning and pad design, not ARCNODE container fit.
- Service envelopes, cycle life, warranty, augmentation strategy, and internal cell architecture are explicitly out of scope. They belong to the customer's BESS procurement decision, not ARCNODE's equipment library.

---

## 7. Library Directory Layout

Equipment specs live in a flat per-ID directory tree. Each equipment dir co-locates the `spec.yaml`, the source `datasheet.pdf`, and a synthesized `envelope.step`:

```
edp-module-assemblies/
├── equipment/                          # one dir per equipment ID
│   ├── CMP-CDU-001/
│   │   ├── spec.yaml                   # this schema
│   │   ├── datasheet.pdf               # vendor source PDF
│   │   └── envelope.step               # synthesized geometry envelope
│   ├── CMP-NODE-001/
│   ├── CMP-PDU-001/
│   ├── CMP-RACK-001/
│   ├── CMP-SWITCH-001/
│   ├── CMP-SWITCH-002/
│   ├── EXT-BESS-001/
│   ├── EXT-BESS-002/
│   ├── EXT-DC-001/
│   ├── EXT-DC-002/
│   ├── GRD-MTR-001/
│   ├── GRD-PCS-001/
│   ├── GRD-RLY-001/
│   ├── GRD-SWG-001/
│   └── GRD-XFM-001/
├── assemblies/                         # container-scoped assembly logic
│   ├── compute-container/
│   ├── grid-container/
│   └── deployment/
├── manifest.yaml                       # generated: equipment_id → S3 spec URL
├── manifest_plates.yaml
├── manifest_profiles.yaml
└── scripts/
    └── build_manifest.py               # regenerates manifest.yaml
```

`manifest.yaml` is a generated artifact — do not hand-edit. Run `scripts/build_manifest.py` after adding or removing an equipment dir.

The three-letter prefix on each `equipment_id` classifies where the equipment lives:

- `CMP-*` — installed inside the Compute Container
- `GRD-*` — installed inside the Grid Container
- `EXT-*` — external customer-supplied equipment that ARCNODE interfaces with but does not contain (BESS, dry coolers, adiabatic coolers, plus cross-container commodity hardware: connectors, cables, hoses)

ARCNODE is a two-container product (Grid Container, Compute Container) per ADR-003. The `EXT-` prefix categorizes equipment that lives outside both containers — see §6 for per-category authoring notes.

---

## 8. Open Items and Deferrals

| # | Item | Resolution | Notes |
|---|---|---|---|
| 1 | STEP file licensing per vendor | Open | Treated as cache-and-commit per user direction (public docs, non-lucrative use). Revisit if commercial licensing model changes. |
| 2 | Confidence flag taxonomy completeness | Defined | The five flags in §4.5 are the initial set. Add as gaps appear. |
| 3 | `control.register_map_url` for proprietary protocols | Open | Vendor-supplied register maps are often gated. Library may end up with null URL and a sales-engagement-required note. |
| 4 | Cost field freshness | Open | `unit_cost_usd` decays in accuracy. No automated refresh; flag with `confidence_flags.assumed_default` if older than 6 months. |
| 5 | Multi-port equipment with per-port heterogeneous specs | Open | E.g., a switch with mixed 1G/10G/40G ports. Current schema represents this with multiple `ports` entries differing in `connector_spec`. Verify this scales. |

---

## 9. Standards Reference

| Spec | Standard | Applies To |
|---|---|---|
| YAML format | YAML 1.2.2 | All spec files |
| JSON Schema | Draft 2020-12 | Generated validator |
| File hash | SHA-256 | Datasheet refresh tracking |
| Date format | ISO 8601 | All date fields |
| Coordinate system | Right-handed, mm, vendor's stated orientation | `mechanical.dimensions_mm` |
| Port type vocabulary | This document §4.4 | `ports[].type` enum |
| Protocol vocabulary | This document §4.4 | `control.protocol` enum |

---

*End of Equipment Spec Schema*
