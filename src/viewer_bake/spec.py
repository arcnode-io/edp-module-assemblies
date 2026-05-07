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
        "platform", re.compile(r"^ARC-PLT-CG$"), "#6b7280", 0.6, 0.45, 1.0, blend=False
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
]


class HotspotCopy(NamedTuple):
    """Hotspot label + sub-text keyed by mesh-name regex (one centroid per match)."""

    hid: str
    pattern: re.Pattern[str]
    label: str
    sub: str


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
    ],
    "grid": [
        HotspotCopy("xfm", re.compile(r"^GRD-XFM-001$"), "Transformer", "MV → LV"),
        HotspotCopy(
            "swg", re.compile(r"^GRD-SWG-001$"), "Switchgear", "Protection + isolation"
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
