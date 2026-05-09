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

Trihal secondary 415Y/240V (not 480V). 60A 3-phase rack PDU = 43 kW per unit. 4× PDUs per Compute Container = true 2N at 80 kW. HGX PSUs accept 240V phase-to-neutral.

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

## ADR-011 — CG plate parametric from day one; Module F is later authority

CG plate cadquery model is parametric on conduit OD, data conduit count, deployment_context, and revision from the first commit. v1 commercial values are hand-computed (~80 kW @ 415Y/240V → ~111A → 2.5″ rigid conduit) and passed in. edp-api `sizing engine Module F` (not yet implemented) becomes the sole authoritative source for those parameters in production; the v1 hand-computed value becomes Module F's first regression test. Plate model owns geometry; Module F owns input math.

## ADR-012 — Manifest URL versioning deferred

v1 ships single mutable URL `s3://arcnode-artifacts/manifest.yaml` with an in-file `version:` field populated by semantic-release. No per-version URL pattern, no `MANIFEST_VERSION` config in edp-api, no startup version check. Revisit when the schema stabilizes (post step 6) and dev/staging environments split. Risk being accepted: an in-flight edp-api job reading the manifest mid-update sees a torn read; mitigation is per-job fetch + in-memory pin for job duration.

## ADR-014 — Trihal sub-config locked for natural-convection clearance

ARCNODE-default Trihal sub-config (GRD-XFM-001):
  - 13.8 kV class (utility-typical US MV; matches GRD-SWG-001 SafeGear)
  - Off-load taps ±2.5%/±5% (standard, ~50 mm top adder)
  - Side-entry HV + LV terminal boxes (saves height vs top-entry)
  - Louvered IP31 ventilated top

That config lands at 1,580 × 820 × 1,860 mm. Container interior height 2,680 mm (ADR-004) gives 820 mm overhead, which exactly meets Schneider's natural-convection guideline. The 4× louver cutouts on long walls (Q5) augment but are not load-bearing for that guideline.

Procurement-time check: confirm the procured Schneider SKU encodes this sub-config. Alternate sub-configs (top-entry terminals add ~140 mm height; on-load tap changers add more) push past the natural-convection budget — those would require forced ventilation in addition to louvers, captured as a separate ADR if a different sub-config is procured.

## ADR-015 — Slotted bolt holes for thermal-expansion accommodation

All v1 plates (CG, BG-AC, BG-DC, CD) use **radially-slotted bolt holes** at the 4 corners + 2 long-axis midpoints (6 of 8 perimeter bolts). 13 mm slot × 11 mm Ø. Short-axis midpoints stay round.

**Per-bolt thermal offset analysis** (6061-T6 plate vs A36 receiver frame, Δα = 11.9e-6/K, commercial ΔT = 85 K):

| Bolt position | Distance from pattern center | Radial offset @ 85 K | Margin (round Ø11, 0.5 mm radial clearance) | After ISO 2768-m fab tol |
|---|---|---|---|---|
| Corners (±260, ±360) | 444 mm (half-diagonal) | **0.449 mm** | 0.051 mm | **NEGATIVE** |
| Long-axis midpoints (0, ±360) | 360 mm | **0.364 mm** | 0.136 mm | **0.036 mm** |
| Short-axis midpoints (±260, 0) | 260 mm | 0.263 mm | 0.237 mm | 0.137 mm |

Round corner holes fail outright; long-axis midpoints have only 36 µm net margin (positive but too tight to ship). Short-axis midpoints have ample margin and can stay round.

**Two mitigations were considered:**
- **Option 1 — slot the affected holes** (adopted): slot length = D_hole + 2·(δ_thermal + δ_fab + δ_margin) = 11 + 2·(0.449 + 0.1 + 0.2) = 12.5 → **13 mm**, oriented radially toward the bolt-pattern center. Same slot length covers both corners (0.449 mm) and long-axis midpoints (0.364 mm) — the budget is set by the worst case. ~$5–10/plate fab cost delta. 0.11 mm headroom remains even at defense-extreme ΔT = 111 K (-40 to +71 °C MIL-STD-810H).
- **Option 2 — tighten to ISO 2768-f**: drops fab tolerance from ±100 µm to ±50 µm. Buys back 50 µm everywhere; 15–30% fab-cost premium per plate forever. Brittle under wider operating ranges.

Option 1 is structurally robust (eliminates the constraint, not just shrinks fab uncertainty) and future-proof (defense ΔT works without rework).

Slot length is encoded in `mounting_bolts.slot_length_mm` in each plate's `cad/specs/{plate_id}/spec.yaml`. Geometry logic in `cad/model/_plate.py::_cut_mounting_bolts` (corners + long-axis midpoints get slots, short-axis midpoints get round holes). Sim asserts the slot accommodates `δ_thermal + δ_fab + δ_margin` per side (`sim/cg/test_run.py::test_slot_accommodates_thermal_offset`). Derivation lives in `theory.ipynb` "Design risk mitigation" cell.
