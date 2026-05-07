"""Scene-graph transform helpers for glTF: TRS → 4x4 matrix, world matrix accumulation."""

import numpy as np
from pygltflib import GLTF2


def node_translation(gltf: GLTF2, node_idx: int) -> np.ndarray:
    """Return the node's translation as a (3,) float32 array; (0,0,0) if absent."""
    t = gltf.nodes[node_idx].translation
    return np.array(t if t else [0.0, 0.0, 0.0], dtype=np.float32)


def node_local_matrix(gltf: GLTF2, node_idx: int) -> np.ndarray:
    """Build the 4x4 local transform from TRS (or matrix if present)."""
    n = gltf.nodes[node_idx]
    if n.matrix:
        # glTF matrix is column-major flat list of 16.
        return np.array(n.matrix, dtype=np.float64).reshape(4, 4, order="F")
    t = np.eye(4, dtype=np.float64)
    if n.translation:
        t[0:3, 3] = n.translation
    r = np.eye(4, dtype=np.float64)
    if n.rotation:
        # glTF quaternion is [x, y, z, w].
        x, y, z, w = n.rotation
        r[0:3, 0:3] = np.array(
            [
                [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
            ]
        )
    s = np.eye(4, dtype=np.float64)
    if n.scale:
        s[0, 0], s[1, 1], s[2, 2] = n.scale
    return t @ r @ s


def world_matrices(gltf: GLTF2) -> dict[int, np.ndarray]:
    """Walk scene graph from scene roots, return {node_idx: 4x4 world matrix}."""
    scene_idx = gltf.scene if gltf.scene is not None else 0
    roots = list(gltf.scenes[scene_idx].nodes)
    out: dict[int, np.ndarray] = {}
    stack: list[tuple[int, np.ndarray]] = [
        (r, np.eye(4, dtype=np.float64)) for r in roots
    ]
    while stack:
        idx, parent_world = stack.pop()
        world = parent_world @ node_local_matrix(gltf, idx)
        out[idx] = world
        stack.extend((child, world) for child in (gltf.nodes[idx].children or []))
    return out
