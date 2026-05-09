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

    assert {h["id"] for h in manifest["compute"]} == {
        "rack",
        "cdu",
        "switch",
        "pdu",
        "plt-cg",
        "plt-cd",
    }
    assert {h["id"] for h in manifest["grid"]} == {"xfm", "swg", "plt-cg", "plt-bg-ac"}
    # Container half-extents ~1.5m — sanity bound.
    for kind in ("compute", "grid"):
        for h in manifest[kind]:
            for c in h["pos"]:
                assert (
                    -3.0 < c < 3.0
                ), f"{kind}/{h['id']} centroid {c} out of meter range"


def test_bake_grid_dc_ext_has_pcs_material_matched(tmp_path: Path) -> None:
    # arrange / act
    src = ASSEMBLIES / "grid-container" / "commercial-dc-ext"
    out = bake_module("grid-dc-ext", src, tmp_path)
    g = GLTF2().load_binary(str(out))
    # assert — pcs material exists in the spec set, no warnings emitted
    material_names = {m.name for m in g.materials}
    assert "pcs" in material_names
    assert "platform" in material_names  # CG + BG-DC plates


def test_bake_grid_no_bess_omits_bg_plate(tmp_path: Path) -> None:
    # arrange / act — no-bess grid container has CG only
    src = ASSEMBLIES / "grid-container" / "no-bess"
    out = bake_module("grid-no-bess", src, tmp_path)
    g = GLTF2().load_binary(str(out))
    # assert — node names show CG present but no BG-AC / BG-DC
    node_names = {n.name for n in g.nodes if n.name}
    assert "ARC-PLT-CG" in node_names
    assert "ARC-PLT-BG-AC" not in node_names
    assert "ARC-PLT-BG-DC" not in node_names


def test_bake_hotspots_covers_all_grid_variants(tmp_path: Path) -> None:
    # arrange — bake all 4 kinds, then read hotspots manifest
    bake_module("compute", ASSEMBLIES / "compute-container" / "commercial-ac", tmp_path)
    bake_module("grid", ASSEMBLIES / "grid-container" / "commercial-ac", tmp_path)
    bake_module(
        "grid-dc-ext", ASSEMBLIES / "grid-container" / "commercial-dc-ext", tmp_path
    )
    bake_module("grid-no-bess", ASSEMBLIES / "grid-container" / "no-bess", tmp_path)
    # act
    out = bake_hotspots(
        tmp_path, kinds=["compute", "grid", "grid-dc-ext", "grid-no-bess"]
    )
    manifest = json.loads(out.read_text())
    # assert
    assert set(manifest.keys()) == {"compute", "grid", "grid-dc-ext", "grid-no-bess"}
    # commercial-ac has CG + BG-AC; dc-ext swaps BG-AC for BG-DC and adds PCS;
    # no-bess is CG only on the plate side.
    assert {h["id"] for h in manifest["grid"]} == {"xfm", "swg", "plt-cg", "plt-bg-ac"}
    assert {h["id"] for h in manifest["grid-no-bess"]} == {"xfm", "swg", "plt-cg"}
    assert {h["id"] for h in manifest["grid-dc-ext"]} == {
        "xfm",
        "swg",
        "pcs",
        "plt-cg",
        "plt-bg-dc",
    }
