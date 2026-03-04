"""
Build a minimal, cap-safe ZM viewhands GLB.

T6 has a hard 160-bone cap for first-person DObjs. When a full-rig viewmodel
weapon (e.g. BO3 thundergun viewmodel skeleton) is present, the stock ZM
viewhands (c_zom_*_viewhands) can push the combined DObj over the limit.

This tool clones the *transforms/hierarchy* for a small required subset of
viewhands bones from a source GLB and emits a tiny skinned mesh weighted to the
root joint. The resulting skeleton is typically 6 joints:
  tag_view, tag_ads, tag_torso, tag_weapon, tag_cambone, tag_camera
"""

from __future__ import annotations

import argparse
import json
import os
import struct
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


def _read_glb(path: str) -> Tuple[Dict[str, Any], bytes]:
    with open(path, "rb") as f:
        head = f.read(12)
        if len(head) != 12 or head[:4] != b"glTF":
            raise RuntimeError(f"not a GLB: {path}")
        total_len = struct.unpack("<I", head[8:12])[0]

        # JSON chunk
        jlen = struct.unpack("<I", f.read(4))[0]
        jtype = f.read(4)
        if jtype != b"JSON":
            raise RuntimeError(f"invalid JSON chunk: {path}")
        jbytes = f.read(jlen)
        gltf = json.loads(jbytes.decode("utf-8"))

        # BIN chunk (optional)
        bin_data = b""
        if f.tell() < total_len:
            blen = struct.unpack("<I", f.read(4))[0]
            btype = f.read(4)
            if btype != b"BIN\x00":
                raise RuntimeError(f"invalid BIN chunk: {path}")
            bin_data = f.read(blen)
        return gltf, bin_data


def _write_glb(path: str, gltf: Dict[str, Any], bin_data: bytes) -> None:
    j = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(j) % 4 != 0:
        j += b" "
    while len(bin_data) % 4 != 0:
        bin_data += b"\x00"

    total_len = 12 + 8 + len(j) + 8 + len(bin_data)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"glTF")
        f.write(struct.pack("<I", 2))
        f.write(struct.pack("<I", total_len))

        f.write(struct.pack("<I", len(j)))
        f.write(b"JSON")
        f.write(j)

        f.write(struct.pack("<I", len(bin_data)))
        f.write(b"BIN\x00")
        f.write(bin_data)


def _align4(data: bytearray) -> None:
    while len(data) % 4 != 0:
        data.extend(b"\x00")


@dataclass
class _NodeSpec:
    name: str
    translation: Optional[List[float]] = None
    rotation: Optional[List[float]] = None
    scale: Optional[List[float]] = None
    children: Optional[List[int]] = None
    mesh: Optional[int] = None
    skin: Optional[int] = None


def _get_parent_map(nodes: List[Dict[str, Any]]) -> Dict[int, int]:
    parent: Dict[int, int] = {}
    for i, n in enumerate(nodes):
        for ch in n.get("children") or []:
            if isinstance(ch, int):
                parent[ch] = i
    return parent


def _find_node(nodes: List[Dict[str, Any]], name: str) -> int:
    for i, n in enumerate(nodes):
        if n.get("name") == name:
            return i
    raise KeyError(name)


def _copy_trs(src_node: Dict[str, Any]) -> Tuple[Optional[List[float]], Optional[List[float]], Optional[List[float]]]:
    return (
        src_node.get("translation"),
        src_node.get("rotation"),
        src_node.get("scale"),
    )


def build_min_viewhands_glb(src_glb: str, out_glb: str) -> None:
    gltf, _ = _read_glb(src_glb)
    nodes: List[Dict[str, Any]] = gltf.get("nodes") or []
    if not nodes:
        raise RuntimeError(f"no nodes in source GLB: {src_glb}")

    # Use a material name that already exists in the stock zones so OAT can
    # resolve it to a T6 "material" asset during xmodel import.
    src_mat_name = ""
    for m in gltf.get("materials") or []:
        nm = (m or {}).get("name")
        if isinstance(nm, str) and nm:
            src_mat_name = nm
            break

    required = ["tag_view", "tag_ads", "tag_torso", "tag_weapon", "tag_cambone", "tag_camera"]
    for nm in required:
        _find_node(nodes, nm)

    parent = _get_parent_map(nodes)
    tag_view_idx = _find_node(nodes, "tag_view")
    root_idx = parent.get(tag_view_idx)
    root_name = (nodes[root_idx].get("name") if root_idx is not None else None) or "viewhands_skel"

    # Extract TRS for required nodes.
    trs = {}
    for nm in required:
        idx = _find_node(nodes, nm)
        trs[nm] = _copy_trs(nodes[idx])

    # Output node layout:
    # 0 root (non-joint)
    # 1 tag_view (joint)
    # 2 tag_ads (joint)
    # 3 tag_torso (joint)
    # 4 tag_weapon (joint)
    # 5 tag_cambone (joint)
    # 6 tag_camera (joint)
    # 7 surf0 mesh node (skinned, not part of bone hierarchy)
    out_nodes: List[Dict[str, Any]] = []
    out_nodes.append({"name": root_name, "children": [1]})

    def _node(name: str, children: Optional[List[int]] = None, mesh: Optional[int] = None, skin: Optional[int] = None) -> Dict[str, Any]:
        t, r, s = trs.get(name, (None, None, None))
        n: Dict[str, Any] = {"name": name}
        if t is not None:
            n["translation"] = t
        if r is not None:
            n["rotation"] = r
        if s is not None:
            n["scale"] = s
        if children:
            n["children"] = children
        if mesh is not None:
            n["mesh"] = mesh
        if skin is not None:
            n["skin"] = skin
        return n

    out_nodes.append(_node("tag_view", children=[2, 5]))
    out_nodes.append(_node("tag_ads", children=[3]))
    out_nodes.append(_node("tag_torso", children=[4]))
    out_nodes.append(_node("tag_weapon"))
    out_nodes.append(_node("tag_cambone", children=[6]))
    out_nodes.append(_node("tag_camera"))
    out_nodes.append({"name": "surf0", "mesh": 0, "skin": 0})

    # Minimal mesh data (single triangle).
    positions = [0.0, 0.0, 0.0, 0.001, 0.0, 0.0, 0.0, 0.001, 0.0]
    normals = [0.0, 0.0, 1.0] * 3
    uvs = [0.0, 0.0, 1.0, 0.0, 0.0, 1.0]
    # JOINTS_0 indices into skin.joints array (0 == tag_view).
    joints = [0, 0, 0, 0] * 3
    weights = [1.0, 0.0, 0.0, 0.0] * 3
    indices = [0, 1, 2]

    # Inverse bind matrices: identity for each joint.
    ibms = []
    for _ in range(6):
        ibms.extend(
            [
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
            ]
        )

    bin_buf = bytearray()

    def _add_f32(data: List[float]) -> Tuple[int, int]:
        _align4(bin_buf)
        off = len(bin_buf)
        bin_buf.extend(struct.pack("<" + "f" * len(data), *data))
        return off, len(data) * 4

    def _add_u16(data: List[int]) -> Tuple[int, int]:
        _align4(bin_buf)
        off = len(bin_buf)
        bin_buf.extend(struct.pack("<" + "H" * len(data), *data))
        return off, len(data) * 2

    def _add_u8(data: List[int]) -> Tuple[int, int]:
        _align4(bin_buf)
        off = len(bin_buf)
        bin_buf.extend(bytes(data))
        return off, len(data)

    # BufferViews
    buffer_views: List[Dict[str, Any]] = []
    accessors: List[Dict[str, Any]] = []

    def _bv(off: int, length: int, target: Optional[int] = None) -> int:
        d: Dict[str, Any] = {"buffer": 0, "byteOffset": off, "byteLength": length}
        if target is not None:
            d["target"] = target
        buffer_views.append(d)
        return len(buffer_views) - 1

    # Accessors and views
    pos_off, pos_len = _add_f32(positions)
    pos_bv = _bv(pos_off, pos_len, 34962)
    accessors.append(
        {
            "bufferView": pos_bv,
            "componentType": 5126,
            "count": 3,
            "type": "VEC3",
            "min": [0.0, 0.0, 0.0],
            "max": [0.001, 0.001, 0.0],
        }
    )
    pos_acc = len(accessors) - 1

    nrm_off, nrm_len = _add_f32(normals)
    nrm_bv = _bv(nrm_off, nrm_len, 34962)
    accessors.append({"bufferView": nrm_bv, "componentType": 5126, "count": 3, "type": "VEC3"})
    nrm_acc = len(accessors) - 1

    uv_off, uv_len = _add_f32(uvs)
    uv_bv = _bv(uv_off, uv_len, 34962)
    accessors.append({"bufferView": uv_bv, "componentType": 5126, "count": 3, "type": "VEC2"})
    uv_acc = len(accessors) - 1

    j_off, j_len = _add_u8(joints)
    j_bv = _bv(j_off, j_len, 34962)
    accessors.append(
        {
            "bufferView": j_bv,
            "componentType": 5121,
            "count": 3,
            "type": "VEC4",
            "normalized": False,
        }
    )
    j_acc = len(accessors) - 1

    w_off, w_len = _add_f32(weights)
    w_bv = _bv(w_off, w_len, 34962)
    accessors.append({"bufferView": w_bv, "componentType": 5126, "count": 3, "type": "VEC4"})
    w_acc = len(accessors) - 1

    i_off, i_len = _add_u16(indices)
    i_bv = _bv(i_off, i_len, 34963)
    accessors.append({"bufferView": i_bv, "componentType": 5123, "count": 3, "type": "SCALAR"})
    i_acc = len(accessors) - 1

    ibm_off, ibm_len = _add_f32(ibms)
    ibm_bv = _bv(ibm_off, ibm_len)
    accessors.append({"bufferView": ibm_bv, "componentType": 5126, "count": 6, "type": "MAT4"})
    ibm_acc = len(accessors) - 1

    out_gltf: Dict[str, Any] = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0, 7]}],
        "nodes": out_nodes,
        "skins": [{"joints": [1, 2, 3, 4, 5, 6], "skeleton": 1, "inverseBindMatrices": ibm_acc}],
        "meshes": [
            {
                "primitives": [
                    {
                        "attributes": {
                            "POSITION": pos_acc,
                            "NORMAL": nrm_acc,
                            "TEXCOORD_0": uv_acc,
                            "JOINTS_0": j_acc,
                            "WEIGHTS_0": w_acc,
                        },
                        "indices": i_acc,
                        "material": 0,
                    }
                ]
            }
        ],
        "materials": [{"name": src_mat_name or "mc/mtl_viewarm_zom_suit"}],
        "bufferViews": buffer_views,
        "accessors": accessors,
        "buffers": [{"byteLength": len(bin_buf)}],
    }

    _write_glb(out_glb, out_gltf, bytes(bin_buf))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-glb", required=True)
    ap.add_argument("--out-glb", required=True)
    args = ap.parse_args()

    build_min_viewhands_glb(args.src_glb, args.out_glb)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
