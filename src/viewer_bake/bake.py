"""Per-module GLB bake: material rebind + node-translation animation + hotspot extraction."""

import json
import logging
from pathlib import Path

import numpy as np
from pygltflib import (
    BLEND,
    GLTF2,
    OPAQUE,
    Accessor,
    Animation,
    AnimationChannel,
    AnimationChannelTarget,
    AnimationSampler,
    BufferView,
    Material,
    PbrMetallicRoughness,
)

from src.viewer_bake.spec import (
    ANIM_DURATION_S,
    HOTSPOT_COPY,
    MAT_SPECS,
    match_mat_spec,
    srgb_hex_to_linear_rgba,
)
from src.viewer_bake.transforms import node_translation, world_matrices

logger = logging.getLogger(__name__)

GL_FLOAT = 5126

# Source CAD exports in mm; glTF default unit is meters. Apply at root.
MM_TO_M: float = 0.001


def _scale_root_to_meters(gltf: GLTF2) -> None:
    """Set scale on the scene root node so child mm coords render as meters."""
    scene_idx = gltf.scene if gltf.scene is not None else 0
    for root_node_idx in gltf.scenes[scene_idx].nodes:
        gltf.nodes[root_node_idx].scale = [MM_TO_M, MM_TO_M, MM_TO_M]


def _replace_materials(gltf: GLTF2) -> dict[str, int]:
    """Replace existing materials with the spec set; return {role: material_idx}."""
    new_materials: list[Material] = []
    role_idx: dict[str, int] = {}
    for spec in MAT_SPECS:
        pbr = PbrMetallicRoughness(
            baseColorFactor=srgb_hex_to_linear_rgba(spec.rgb_hex, spec.alpha),
            metallicFactor=spec.metallic,
            roughnessFactor=spec.roughness,
        )
        mat = Material(
            name=spec.name,
            pbrMetallicRoughness=pbr,
            alphaMode=BLEND if spec.blend else OPAQUE,
            doubleSided=spec.blend,  # ghost shell looks better double-sided
        )
        role_idx[spec.name] = len(new_materials)
        new_materials.append(mat)
    gltf.materials = new_materials
    return role_idx


def _bind_meshes(gltf: GLTF2, role_idx: dict[str, int]) -> None:
    """Walk nodes, match name to spec, assign that spec's material to the node's mesh primitives."""
    for node in gltf.nodes:
        if node.mesh is None or not node.name:
            continue
        spec = match_mat_spec(node.name)
        if spec is None:
            logger.warning("no material spec matched node '%s'", node.name)
            continue
        for prim in gltf.meshes[node.mesh].primitives:
            prim.material = role_idx[spec.name]


def _append_animation(
    gltf: GLTF2, exploded_translations: dict[str, np.ndarray]
) -> None:
    """Add 'explode' clip with per-node translation tracks (assembled → exploded over ANIM_DURATION_S)."""
    moving = []
    for i, node in enumerate(gltf.nodes):
        if not node.name or node.name not in exploded_translations:
            continue
        from_t = node_translation(gltf, i)
        to_t = exploded_translations[node.name]
        if not np.allclose(from_t, to_t):
            moving.append((i, from_t, to_t))

    if not moving:
        logger.info("no nodes move between assembled and exploded — skipping animation")
        return

    times = np.array([0.0, ANIM_DURATION_S], dtype=np.float32)
    blob = bytearray(times.tobytes())
    output_offsets: list[int] = []
    for _, from_t, to_t in moving:
        output_offsets.append(len(blob))
        blob.extend(np.stack([from_t, to_t]).astype(np.float32).tobytes())

    existing = gltf.binary_blob() or b""
    base = len(existing)

    time_bv = len(gltf.bufferViews)
    gltf.bufferViews.append(BufferView(buffer=0, byteOffset=base, byteLength=8))
    time_acc = len(gltf.accessors)
    gltf.accessors.append(
        Accessor(
            bufferView=time_bv,
            componentType=GL_FLOAT,
            count=2,
            type="SCALAR",
            min=[0.0],
            max=[float(ANIM_DURATION_S)],
        )
    )

    samplers: list[AnimationSampler] = []
    channels: list[AnimationChannel] = []
    for (node_idx, from_t, to_t), ofs in zip(moving, output_offsets, strict=True):
        out_arr = np.stack([from_t, to_t]).astype(np.float32)
        gltf.bufferViews.append(
            BufferView(buffer=0, byteOffset=base + ofs, byteLength=24)
        )
        gltf.accessors.append(
            Accessor(
                bufferView=len(gltf.bufferViews) - 1,
                componentType=GL_FLOAT,
                count=2,
                type="VEC3",
                min=out_arr.min(axis=0).tolist(),
                max=out_arr.max(axis=0).tolist(),
            )
        )
        samplers.append(
            AnimationSampler(
                input=time_acc, output=len(gltf.accessors) - 1, interpolation="LINEAR"
            )
        )
        channels.append(
            AnimationChannel(
                sampler=len(samplers) - 1,
                target=AnimationChannelTarget(node=node_idx, path="translation"),
            )
        )

    gltf.set_binary_blob(existing + bytes(blob))
    gltf.buffers[0].byteLength = len(existing) + len(blob)
    gltf.animations.append(
        Animation(name="explode", channels=channels, samplers=samplers)
    )
    logger.info(
        "added 'explode' animation: %d channels, %.2fs", len(channels), ANIM_DURATION_S
    )


def _hotspots(gltf: GLTF2, kind: str) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    worlds = world_matrices(gltf)
    for hs in HOTSPOT_COPY[kind]:
        for node_idx, node in enumerate(gltf.nodes):
            if node.mesh is None or not node.name or not hs.pattern.match(node.name):
                continue
            prim = gltf.meshes[node.mesh].primitives[0]
            pos_acc = gltf.accessors[prim.attributes.POSITION]
            mn = np.array(pos_acc.min, dtype=np.float64)
            mx = np.array(pos_acc.max, dtype=np.float64)
            local_centroid = (mn + mx) / 2.0
            point = np.append(local_centroid, 1.0)
            world_pt = worlds[node_idx] @ point
            out.append(
                {
                    "id": hs.hid,
                    "pos": [round(float(c), 4) for c in world_pt[:3]],
                    "label": hs.label,
                    "sub": hs.sub,
                }
            )
            break
    return out


def bake_module(kind: str, src_dir: Path, out_dir: Path) -> Path:
    """Bake one module: read assembled+exploded sources, write animated GLB to out_dir."""
    assembled = GLTF2().load_binary(str(src_dir / "assembly.glb"))
    exploded = GLTF2().load_binary(str(src_dir / "assembly-exploded.glb"))
    exploded_translations = {
        n.name: node_translation(exploded, i)
        for i, n in enumerate(exploded.nodes)
        if n.name
    }
    role_idx = _replace_materials(assembled)
    _bind_meshes(assembled, role_idx)
    _append_animation(assembled, exploded_translations)
    _scale_root_to_meters(assembled)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{kind}.glb"
    assembled.save_binary(str(out_path))
    logger.info("wrote %s (%d bytes)", out_path, out_path.stat().st_size)
    return out_path


def bake_hotspots(out_dir: Path) -> Path:
    """Read post-bake GLBs and emit hotspots.json."""
    manifest: dict[str, list[dict[str, object]]] = {}
    for kind in ("compute", "grid"):
        gltf = GLTF2().load_binary(str(out_dir / f"{kind}.glb"))
        manifest[kind] = _hotspots(gltf, kind)
    out_path = out_dir / "hotspots.json"
    out_path.write_text(json.dumps(manifest, indent=2))
    logger.info("wrote %s", out_path)
    return out_path
