# System ADRs

## ADR-001 — BYOB BESS

BESS is customer-supplied. Optional for firm baseload (nuclear). EMS supervises but does not specify. Profiles: Tesla Megapack (AC), CATL EnerOne (DC).

## ADR-002 — v1 targets HGX B200

Supermicro SYS-421GE-NBRT-LCC, 4U, 8× B200 SXM, ~10.5 kW per node sustained. MGX/GB200 deferred.

## ADR-003 — Two-container product

ARCNODE ships Compute Container + Grid Container. Thermal Module retired — CDU rack-mounted inside Compute. Grid Container required for DC-coupled, conditional for AC-coupled (obsolete when Tesla Megablock ships).

## ADR-004 — 10ft high-cube ISO

All containers 10ft high-cube ISO (interior 2,680mm). SafeGear (2,413mm) does not fit standard. Uniform fleet.

## ADR-005 — 415Y/240V LV distribution

Trihal secondary 415Y/240V (not 480V). 60A 3-phase rack PDU = 34.5 kW per unit (48A rated). 6× PDUs per Compute Container, 3 on path A and 3 on path B: dual-path (A/B) distribution at 80 kW from a single source. Every node PSU pair splits across A and B, so either path carries the full load through a PDU or branch failure. It is not 2N: both paths share one CG feeder and one Trihal, so losing the grid container drops both. HGX PSUs accept 240V phase-to-neutral.

## ADR-006 — Manifest absorbs profile→asset mapping

`hardware_selector_map.yaml` in edp-api retired. Profile→asset selection moves into `manifest.yaml` as a `profiles:` section, authored in this repo where variant decisions originate. edp-api consumes the manifest as the single hardware contract — flat URL maps + curated profile mapping in one fetch. Prevents drift between adding a new variant and exposing it to a profile.

## ADR-007 — Per-container origin + named MATING_FRAMES

Each container assembly has its own local origin (floor center, X = container length toward mating face, Y across, Z up). Cross-container coupling is explicit: each container module exports named `cq.Location` constants for its mating frames (e.g. `CG_MATING_FRAME` on compute, with mirrored normal on grid). A higher-level deployment assembly composes containers by aligning frames. No shared global origin between containers.

## ADR-008 — Plate spec.yaml in edp-interface-plates

Each plate variant has `cad/specs/{plate_id}/spec.yaml` mirroring the equipment-spec pattern: schema_version, deployment_contexts (commercial / defense_forward), penetration_schedule, outer_dims, mating_pair, provenance. Single source for plate metadata feeding model build, BOM generator, drawing generator, and penetration-schedule artifact. Manifest exposes it as `plates.{id}.spec_url`.

## ADR-009 — Hardware↔edp-api contract artifacts

Two contract artifacts pinned: per-assembly `bom.yaml` (split sections — `parts:` equipment list with qty, `plates:` with id+version) expresses one container's BOM and is multiplied by container count downstream; `bom.json` is a flat line-items array with a `procurement_path` discriminator (`catalog` | `custom_fabrication`) and a top-level metadata block (deployment_id, profile, manifest_version, generated_at). No hierarchy in either.

## ADR-010 — Step 4 scope: compute-container only with grid mating-frame stub

Step 4 builds `compute-container/commercial-ac` only. Grid container is treated as a notional mating frame (named coordinate constant per ADR-007), not a built assembly. Grid container assembly lands in step 6.1, which is the first end-to-end validation of the mating-frame contract. `commercial-dc` compute-container assumed identical to `commercial-ac` pending step 6.8 verification — if they diverge there, that's a real second variant; if not, commercial-dc becomes a pointer.

## ADR-011 — Manifest URL versioning deferred

v1 ships single mutable URL `s3://arcnode-artifacts/manifest.yaml` with an in-file `version:` field populated by semantic-release. No per-version URL pattern, no `MANIFEST_VERSION` config in edp-api, no startup version check. Revisit when the schema stabilizes (post step 6) and dev/staging environments split. Risk being accepted: an in-flight edp-api job reading the manifest mid-update sees a torn read; mitigation is per-job fetch + in-memory pin for job duration.

## ADR-013 — Trihal sub-config locked for natural-convection clearance

ARCNODE-default Trihal sub-config (GRD-XFM-001):
  - 13.8 kV class (utility-typical US MV; matches GRD-SWG-001 SafeGear)
  - Off-load taps ±2.5%/±5% (standard, ~50 mm top adder)
  - Side-entry HV + LV terminal boxes (saves height vs top-entry)
  - Louvered IP31 ventilated top

That config lands at 1,580 × 820 × 1,860 mm. Container interior height 2,680 mm (ADR-004) gives 820 mm overhead, which exactly meets Schneider's natural-convection guideline. The 4× louver cutouts on long walls (Q5) augment but are not load-bearing for that guideline.

Procurement-time check: confirm the procured Schneider SKU encodes this sub-config. Alternate sub-configs (top-entry terminals add ~140 mm height; on-load tap changers add more) push past the natural-convection budget — those would require forced ventilation in addition to louvers, captured as a separate ADR if a different sub-config is procured.

## ADR-014 — Slotted bolt holes for thermal-expansion accommodation

All v1 plates (CG, CD) use **radially-slotted bolt holes** at the 4 corners + 2 long-axis midpoints (6 of 8 perimeter bolts). 13 mm slot × 11 mm Ø. Short-axis midpoints stay round.

**Per-bolt thermal offset analysis** (6061-T6 plate vs A36 receiver frame, Δα = 11.9e-6/K, commercial ΔT = 85 K):

| Bolt position | Distance from pattern center | Radial offset @ 85 K | Margin (round Ø11, 0.5 mm radial clearance) | After ISO 2768-m fab tol |
|---|---|---|---|---|
| Corners (±260, ±360) | 444 mm (half-diagonal) | **0.449 mm** | 0.051 mm | **NEGATIVE** |
| Long-axis midpoints (0, ±360) | 360 mm | **0.364 mm** | 0.136 mm | **0.036 mm** |
| Short-axis midpoints (±260, 0) | 260 mm | 0.263 mm | 0.237 mm | 0.137 mm |

Round corner holes fail outright; long-axis midpoints have only 36 µm net margin (positive but too tight to ship). Short-axis midpoints have ample margin and can stay round.

**Two mitigations were considered:**
- **Option 1 — slot the affected holes** (adopted): the constraint is bolt-to-slot-end clearance ≥ worst-case displacement. Min slot length = D_bolt + 2·(δ_thermal + δ_fab + δ_margin) = 10 + 2·(0.449 + 0.1 + 0.2) = 11.5 mm; rounded up to **13 mm** for round-number fab stock + extra safety. Per-side travel (slot_length − bolt_diameter)/2 = 1.5 mm covers both corners (0.449 mm budget = 0.749 mm with fab tol + margin) and long-axis midpoints (0.364 mm budget = 0.664 mm). Same slot length serves both. ~$5–10/plate fab cost delta. **Commercial headroom 0.75 mm; defense headroom 0.61 mm even at MIL-STD-810H ΔT = 111 K (-40 to +71 °C).**
- **Option 2 — tighten to ISO 2768-f**: drops fab tolerance from ±100 µm to ±50 µm. Buys back 50 µm everywhere; 15–30% fab-cost premium per plate forever. Brittle under wider operating ranges.

Option 1 is structurally robust (eliminates the constraint, not just shrinks fab uncertainty) and future-proof (defense ΔT works without rework).

Slot length is encoded in `mounting_bolts.slot_length_mm` in each plate's `cad/specs/{plate_id}/spec.yaml`. Geometry logic in `cad/model/_plate.py::_cut_mounting_bolts` (corners + long-axis midpoints get slots, short-axis midpoints get round holes). Sim asserts the slot accommodates `δ_thermal + δ_fab + δ_margin` per side (`sim/cg/test_run.py::test_slot_accommodates_thermal_offset`). Derivation lives in `theory.ipynb` "Design risk mitigation" cell.

## ADR-015 — Grid gear serviced from outside

SafeGear is worked from outside through the container's side doors, not from inside. The interior is not a working space, so the Trihal may sit in front of SafeGear's face (NEC 110.34 working space is outside the doors).

## ADR-016 — Every BESS ties in at 13.8 kV

Batteries connect to the site 13.8 kV bus through a customer-supplied step-up transformer and MV disconnect (BYOB, ADR-001): Tesla Megapack 2 XL (480 V), CATL with its own PCS, and CATL behind ARCNODE's PCS on dc_ext (ADR-022). None lands on the grid container's 415 V bus: a 480 V source can't parallel a 415Y/240 V bus, and a 480/415 transformer doesn't fit the grid container. Grid containers have no battery plate.

## ADR-017 — LV protection

Grid container: a 415 V LV switchboard (GRD-LVS-001) with a main breaker on the Trihal secondary and one feeder breaker per compute container it feeds; the Trihal is its only source (ADR-022). Compute container: a panelboard (CMP-PNL-001) with one branch breaker per PDU, the CDU and the dry cooler. Both are engineered to order against their specs, with Square D QED-2 and NF as reference designs.

## ADR-018 — Compute containers split evenly over grid containers

Site with N compute and M grid containers: grid container k feeds compute containers in order, q = ceil(N / M) each (G1 feeds C1…Cq, G2 the next q, and so on). M is sized from site peak, so an even split keeps each under its rating. The 13.8 kV site bus joining the utility service, the M grid containers and the BESS step-up is by others.

## ADR-019 — Management network

Each container gets a 1 GbE managed switch for device management: server BMCs, PDUs, CDU, relay, meter, PCS. The SN5600 stays the data-plane fabric. Compute switches (CMP-SWITCH-003) uplink through CG to the grid container switch (GRD-SWITCH-001), which carries the uplink to the EMS gateway. Gateway hardware is the platform-ems-iso host, not specified here. Parts are pending selection, datasheet check and CAD fit.

## ADR-020 — POI meter sits at the utility service

The ION9000 (GRD-MTR-001) meters the point of interconnection: the utility service ahead of the 13.8 kV site bus. Inside G1 it would miss the MV-tied BESS (ADR-016) and every other grid container (ADR-018), so the EMS would read the wrong site import/export. It ships loose with G1 (one per site, on G1's BOM) and is installed at the service with revenue-class CTs/PTs by the site MV contractor, along with any utility-required interconnection protection. Its Ethernet runs to G1's management switch (ADR-019).

## ADR-021 — Grid containers sized to 80% of the Trihal

Each grid container carries at most 800 kVA of continuous load, 80% of the Trihal's 1000 kVA. The Trihal runs on natural convection in a closed container with no overhead margin (ADR-013) and no in-container ambient derating data, so it isn't loaded to nameplate. Site load per compute container is its 80 kW (B200) or 62.6 kW (H100) plus the dry cooler's fans, a 6 kW allowance until a Güntner selection gives the real figure (EXT-DC-001/-002 `power_kw`, flagged). B200: 9 compute containers per grid container; H100: 11. Each compute feeder carries 86 kW ≈ 121 A at 415 V; continuous × 1.25 = 151 A, so feeder breakers are 175 A (ADR-017).

## ADR-022 — dc_ext PCS on the battery pad, tied in at 13.8 kV

On dc_ext the customer's CATL EnerOne+ DC strings feed EPC CAB1000 PCS units (GRD-PCS-001, 1043 kW at 480 V, outdoor IP55 / NEMA 3R) on the battery pad. Their 480 V AC ties in at 13.8 kV through a customer-supplied step-up and MV disconnect, the same as Megapack (ADR-016). Every coupling therefore uses the same grid containers and plates (CG, CD), with no battery plate. The PCS is a site line on the BOM and sits under the battery module in the device data.

The PCS meets the load only on the 13.8 kV bus, so its count follows the battery's power job, not the grid containers: N = max(1, ceil(P_need / 1043 kW)). P_need is the largest of: the site's grid peak (ride-through or off grid), the curtailed depth d·P_g and the recharge power (flex), the export limit (limited export), or the bank's own DC power (unlimited export). With none of those, one PCS connects the battery. CATL racks are 379.4 kWh at 1C; when whole racks × 379.4 kW fall short of P_need, sizing raises BESS_POWER_SHORTFALL rather than shrinking the PCS fleet.

Reason: tied in at 415 V, the PCS would be a second ~1400 A source on the 1600 A switchboard bus. Its breaker exceeds the I-Line distribution section's 1200 A frame (QED-2 Table 21), the extra section doesn't fit the container wall, and two sources fail the NEC 705.12 bus rule. Tied in at 13.8 kV, the switchboard keeps the Trihal as its only source and the 415Y/240 V neutral comes from the Trihal.

Open: how many CATL racks one CAB1000 DC input takes (combiner), and whether it can black-start the site by energizing the step-up and the Trihals (both open with EPC). The CATL maximum DC voltage (1497.6 V) sits 2 V under the CAB1000's 1500 V limit; confirm cold open-circuit voltage with CATL.
