"""Smoke test: end-to-end bake produces well-formed GLB + manifest."""

import json
from pathlib import Path

from pygltflib import BLEND, GLTF2, OPAQUE

from src.viewer_bake.bake import bake_hotspots, bake_module
from src.viewer_bake.spec import MAT_SPECS, srgb_hex_to_linear_rgba

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSEMBLIES = REPO_ROOT / "assemblies"


def test_srgb_to_linear_white_passes_through() -> None:
    assert srgb_hex_to_linear_rgba("#ffffff", 1.0) == [1.0, 1.0, 1.0, 1.0]


def test_srgb_to_linear_black_is_zero() -> None:
    assert srgb_hex_to_linear_rgba("#000000", 1.0) == [0.0, 0.0, 0.0, 1.0]


def test_srgb_to_linear_mid_grey_in_curve_segment() -> None:
    # 0.5 sRGB → ~0.214 linear (well above piecewise threshold)
    r, g, b, a = srgb_hex_to_linear_rgba("#808080", 0.5)
    assert abs(r - 0.2159) < 0.001
    assert r == g == b
    assert a == 0.5


def test_bake_compute_produces_animated_glb_with_spec_materials(tmp_path: Path) -> None:
    src = ASSEMBLIES / "compute-container" / "commercial-ac"
    out = bake_module("compute", src, tmp_path)
    g = GLTF2().load_binary(str(out))

    assert [m.name for m in g.materials] == [s.name for s in MAT_SPECS]
    assert next(m for m in g.materials if m.name == "ghost").alphaMode == BLEND
    # Rack is now BLEND too so the GPU nodes inside read through.
    assert next(m for m in g.materials if m.name == "rack").alphaMode == BLEND
    assert next(m for m in g.materials if m.name == "node").alphaMode == OPAQUE
    assert len(g.animations) == 1
    assert g.animations[0].name == "explode"
    assert len(g.animations[0].channels) > 0
    # Root scaled to meters.
    root_idx = g.scenes[g.scene or 0].nodes[0]
    assert g.nodes[root_idx].scale == [0.001, 0.001, 0.001]


def test_bake_hotspots_emits_meter_scale_centroids(tmp_path: Path) -> None:
    bake_module("compute", ASSEMBLIES / "compute-container" / "commercial-ac", tmp_path)
    bake_module("grid", ASSEMBLIES / "grid-container" / "commercial-ac", tmp_path)
    out = bake_hotspots(tmp_path)
    manifest = json.loads(out.read_text())

    assert {h["id"] for h in manifest["compute"]} == {"rack", "cdu", "switch", "pdu"}
    assert {h["id"] for h in manifest["grid"]} == {"xfm", "swg"}
    # Container half-extents ~1.5m — sanity bound.
    for kind in ("compute", "grid"):
        for h in manifest[kind]:
            for c in h["pos"]:
                assert -3.0 < c < 3.0, f"{kind}/{h['id']} centroid {c} out of meter range"


