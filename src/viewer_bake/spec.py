"""Material + hotspot spec tables for the web viewer bake."""

import re
from typing import Final, NamedTuple

ANIM_DURATION_S: Final[float] = 1.0


class MatSpec(NamedTuple):
    """One material role: regex match → linear PBR color + alpha + blend mode."""

    name: str
    pattern: re.Pattern[str]
    rgb_hex: str
    metallic: float
    roughness: float
    alpha: float
    blend: bool


# Reason: order matters — first regex match wins. Patterns from the brief.
MAT_SPECS: Final[list[MatSpec]] = [
    MatSpec(
        "ghost", re.compile(r"^container_shell$"), "#3a4048", 0.0, 0.9, 0.18, blend=True
    ),
    MatSpec(
        "platform",
        # Reason: all interface plates render with the same brushed-aluminum
        # look — CG, BG-AC, BG-DC, CD share the 6061-T6 finish in v1.
        re.compile(r"^ARC-PLT-(CG|BG-AC|BG-DC|CD)$"),
        "#6b7280",
        0.6,
        0.45,
        1.0,
        blend=False,
    ),
    MatSpec(
        "rack", re.compile(r"^CMP-RACK-001$"), "#2d3137", 0.7, 0.40, 0.22, blend=True
    ),
    MatSpec(
        "node",
        re.compile(r"^CMP-NODE-001#\d+$"),
        "#3a7fc4",
        0.3,
        0.55,
        1.0,
        blend=False,
    ),
    MatSpec(
        "cdu", re.compile(r"^CMP-CDU-001$"), "#4ba6b8", 0.3, 0.55, 1.0, blend=False
    ),
    MatSpec(
        "switch",
        re.compile(r"^CMP-SWITCH-001$"),
        "#5aa86c",
        0.3,
        0.55,
        1.0,
        blend=False,
    ),
    MatSpec(
        "pdu", re.compile(r"^CMP-PDU-001#\d+$"), "#d49538", 0.3, 0.55, 1.0, blend=False
    ),
    MatSpec(
        "xfm", re.compile(r"^GRD-XFM-001$"), "#a86a42", 0.4, 0.50, 1.0, blend=False
    ),
    MatSpec(
        "swg", re.compile(r"^GRD-SWG-001$"), "#b8482a", 0.3, 0.55, 1.0, blend=False
    ),
    MatSpec(
        "pcs", re.compile(r"^GRD-PCS-001$"), "#5b8c6a", 0.4, 0.50, 1.0, blend=False
    ),
    # ── DLR carrier PCB groups ──
    # Reason: scene graph from dlr-pcb has parent group
    # nodes (no mesh) plus leaf children named `<group>__<refdes>`. Patterns
    # match both: `^group(?:__.*)?$`. Colors: PCB green for the board,
    # gold/silver for connectors, warm hues for sensors, cool hues for power,
    # dark for SoC/modem packages.
    MatSpec(
        "pcb_board",
        re.compile(r"^pcb_board(?:__.*)?$"),
        "#1f3a26",
        0.0,
        0.70,
        1.0,
        blend=False,
    ),
    MatSpec(
        "cm4_socket",
        re.compile(r"^cm4_socket(?:__.*)?$"),
        "#c8a058",
        0.6,
        0.40,
        1.0,
        blend=False,
    ),
    MatSpec(
        "cellular_modem",
        re.compile(r"^cellular_modem(?:__.*)?$"),
        "#2d3137",
        0.4,
        0.50,
        1.0,
        blend=False,
    ),
    MatSpec(
        "cellular_io",
        re.compile(r"^cellular_io(?:__.*)?$"),
        "#8a929b",
        0.5,
        0.50,
        1.0,
        blend=False,
    ),
    # Reason: lens must match BEFORE the general vision_thermal pattern below
    # so the chrome bezel reads as silver, not matte black like the can body.
    MatSpec(
        "lepton_lens",
        re.compile(r"^(vision_thermal|lepton_daughterboard)__lepton_lens$"),
        "#c8ccd0",
        0.85,
        0.18,
        1.0,
        blend=False,
    ),
    MatSpec(
        "vision_thermal",
        re.compile(r"^(vision_thermal(?:__.*)?|lepton_daughterboard__lepton_body)$"),
        "#1a1c20",
        0.3,
        0.60,
        1.0,
        blend=False,
    ),
    MatSpec(
        "atmospherics",
        re.compile(r"^atmospherics(?:__.*)?$"),
        "#e0a050",
        0.2,
        0.60,
        1.0,
        blend=False,
    ),
    MatSpec(
        "power_harvest",
        re.compile(r"^power_harvest(?:__.*)?$"),
        "#d49538",
        0.3,
        0.50,
        1.0,
        blend=False,
    ),
    MatSpec(
        "power_buck",
        re.compile(r"^power_buck(?:__.*)?$"),
        "#5b8c6a",
        0.3,
        0.55,
        1.0,
        blend=False,
    ),
    MatSpec(
        "power_ldo",
        re.compile(r"^power_ldo(?:__.*)?$"),
        "#7baa84",
        0.3,
        0.55,
        1.0,
        blend=False,
    ),
    MatSpec(
        "bat_terminal",
        re.compile(r"^bat_terminal(?:__.*)?$"),
        "#8a3a3a",
        0.3,
        0.55,
        1.0,
        blend=False,
    ),
    MatSpec(
        "debug_header",
        re.compile(r"^debug_header(?:__.*)?$"),
        "#b8b8b8",
        0.5,
        0.40,
        1.0,
        blend=False,
    ),
    # ── Field-kit nodes (per dlr-pcb build_assembly.py _build_field_kit) ──
    MatSpec(
        "anemometer_body",
        re.compile(r"^anemometer_body$"),
        # Variant-neutral: the body color is set per cq.Color in build_assembly
        # (black for Calypso, light steel for WMT702). A mid-grey + low
        # metallic + medium roughness reads OK for both at the marketing zoom.
        "#9aa0a8",
        0.55,
        0.40,
        1.0,
        blend=False,
    ),
    MatSpec(
        "sensor_cable",
        re.compile(r"^sensor_cable$"),
        "#1a1c20",  # black cable jacket
        0.0,
        0.85,
        1.0,
        blend=False,
    ),
    MatSpec(
        "pv_panel",
        re.compile(r"^pv_panel$"),
        "#0e2a55",  # deep blue monocrystalline cells
        0.2,
        0.25,  # slight gloss to read as glass-faced
        1.0,
        blend=False,
    ),
    MatSpec(
        "battery_pack",
        re.compile(r"^battery_pack$"),
        "#d8d8da",  # light grey ABS enclosure
        0.05,
        0.55,
        1.0,
        blend=False,
    ),
]


class HotspotCopy(NamedTuple):
    """Hotspot label + sub-text keyed by mesh-name regex (one centroid per match)."""

    hid: str
    pattern: re.Pattern[str]
    label: str
    sub: str


# Reason: plate labels read as "what's on the other side of this wall" — `CG`
# reads "Grid Interface" inside the compute container and "Compute Interface"
# inside the grid container. The web viewer intentionally surfaces only the
# inter-container CG plate; the external-facing plates (CD on compute, BG-* on
# grid) are present in the GLB but unlabeled to keep the marketing render
# focused on the compute-grid story.
_PLATE_CG_FROM_COMPUTE: Final[HotspotCopy] = HotspotCopy(
    "plt-cg", re.compile(r"^ARC-PLT-CG$"), "Grid Interface", "AC feeder + data"
)
_PLATE_CG_FROM_GRID: Final[HotspotCopy] = HotspotCopy(
    "plt-cg", re.compile(r"^ARC-PLT-CG$"), "Compute Interface", "AC feeder + data"
)

_GRID_BASE: Final[list[HotspotCopy]] = [
    HotspotCopy("xfm", re.compile(r"^GRD-XFM-001$"), "Transformer", "MV → LV"),
    HotspotCopy(
        "swg", re.compile(r"^GRD-SWG-001$"), "Switchgear", "Protection + isolation"
    ),
    _PLATE_CG_FROM_GRID,
]

# Reason: external-facing plates exist in the source GLBs (real BOM parts) but
# the web viewer is the marketing render — we want only the inter-container CG
# plate visible. Mesh on these nodes is cleared during bake; geometry is
# preserved in source assemblies.
HIDDEN_NODES: Final[dict[str, list[str]]] = {
    "compute": ["ARC-PLT-CD"],
    "grid": ["ARC-PLT-BG-AC"],
    "grid-dc-ext": ["ARC-PLT-BG-DC"],
    # Daughterboard scaffolding (ADR-013) — marketing view shows the Lepton
    # only; bracket + small PCB + socket pedestal stay out of the scene.
    "dlr-carrier": [
        "lepton_daughterboard__bracket",
        "lepton_daughterboard__pcb",
        "lepton_daughterboard__socket",
    ],
    # Same scaffolding rule applies to both kit variants.
    "dlr-carrier-hw": [
        "lepton_daughterboard__bracket",
        "lepton_daughterboard__pcb",
        "lepton_daughterboard__socket",
    ],
    "dlr-carrier-lw": [
        "lepton_daughterboard__bracket",
        "lepton_daughterboard__pcb",
        "lepton_daughterboard__socket",
    ],
}


HOTSPOT_COPY: Final[dict[str, list[HotspotCopy]]] = {
    "compute": [
        HotspotCopy(
            "rack", re.compile(r"^CMP-RACK-001$"), "GPU Rack", "7x compute nodes"
        ),
        HotspotCopy("cdu", re.compile(r"^CMP-CDU-001$"), "CDU", "Liquid cooling"),
        HotspotCopy(
            "switch", re.compile(r"^CMP-SWITCH-001$"), "Network Switch", "400G fabric"
        ),
        HotspotCopy("pdu", re.compile(r"^CMP-PDU-001#1$"), "PDUs", "Redundant power"),
        _PLATE_CG_FROM_COMPUTE,
    ],
    "grid": _GRID_BASE,
    "grid-dc-ext": [
        *_GRID_BASE,
        HotspotCopy("pcs", re.compile(r"^GRD-PCS-001$"), "PCS", "DC → AC, 500 kW"),
    ],
    "grid-no-bess": _GRID_BASE,
    # Reason: the Lepton sits at a tilt that's not obvious from geometry alone
    # without the (hidden) bracket showing the mechanism. A single hotspot at
    # the lens explains why the camera is angled — ADR-013 boresight set by
    # the integrator during commissioning.
    "dlr-carrier": [
        HotspotCopy(
            "aim",
            re.compile(r"^lepton_daughterboard__lepton_lens$"),
            "Aim adjustment",
            "±15° tilt set at commissioning",
        ),
    ],
    # Kit-variant hotspots: same Lepton aim hotspot + sensor body + PV +
    # battery callouts so the variant card's 3D viewer is self-explaining.
    "dlr-carrier-hw": [
        HotspotCopy(
            "aim",
            re.compile(r"^lepton_daughterboard__lepton_lens$"),
            "Aim adjustment",
            "±15° tilt set at commissioning",
        ),
        HotspotCopy(
            "anemometer",
            re.compile(r"^anemometer_body$"),
            "Calypso ULP STD",
            "Ultra-low-power, 1 mW, 1 m/s threshold",
        ),
        HotspotCopy(
            "pv",
            re.compile(r"^pv_panel$"),
            "Solar panel",
            "20 W monocrystalline",
        ),
        HotspotCopy(
            "battery",
            re.compile(r"^battery_pack$"),
            "Battery pack",
            "50 Wh LiFePO4 · ~1.6 d autonomy",
        ),
    ],
    "dlr-carrier-lw": [
        HotspotCopy(
            "aim",
            re.compile(r"^lepton_daughterboard__lepton_lens$"),
            "Aim adjustment",
            "±15° tilt set at commissioning",
        ),
        HotspotCopy(
            "anemometer",
            re.compile(r"^anemometer_body$"),
            "Vaisala WMT702",
            "FAA / NWS grade · ±0.1 m/s · 0.01 m/s threshold",
        ),
        HotspotCopy(
            "pv",
            re.compile(r"^pv_panel$"),
            "Solar panel",
            "30 W monocrystalline",
        ),
        HotspotCopy(
            "battery",
            re.compile(r"^battery_pack$"),
            "Battery pack",
            "100 Wh LiFePO4 · ~2.2 d autonomy",
        ),
    ],
}


def srgb_hex_to_linear_rgba(hex_str: str, alpha: float) -> list[float]:
    """sRGB hex → linear RGBA per glTF baseColorFactor convention. Piecewise."""
    h = hex_str.lstrip("#")
    chans = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return [
        c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in chans
    ] + [alpha]


def match_mat_spec(node_name: str) -> MatSpec | None:
    """Return the first MatSpec whose pattern matches `node_name`, or None."""
    return next((s for s in MAT_SPECS if s.pattern.match(node_name)), None)
