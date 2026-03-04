#!/usr/bin/env python3
"""
Validate that thundergun runtime viewmodel model(s) contain the bone names
referenced by vm_thunder_gun_*.xanim_export files.

Why this matters:
- T6 does no retargeting. If XAnimParts references bones your model does not
  have, the viewmodel will stretch/warp when real payloads are loaded.

This script checks:
- xanim bone set (union across exports)
- union(GLB node name sets)
- union(GLB skin joint name sets) (if skins exist)

Exit code:
- 0: ok (or non-strict mode)
- 2: strict mode failed (missing bones)
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import struct
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


GLB_MAGIC = b"glTF"


@dataclass(frozen=True)
class GlbInfo:
    node_names: Set[str]
    joint_names: Set[str]
    node_count: int
    skin_count: int
    joint_count: int


def _read_glb_json(path: str) -> Dict:
    data = open(path, "rb").read()
    if len(data) < 20 or data[:4] != GLB_MAGIC:
        raise RuntimeError(f"Invalid GLB header: {path}")
    json_len = struct.unpack_from("<I", data, 12)[0]
    json_type = data[16:20]
    if json_type != b"JSON":
        raise RuntimeError(f"Invalid GLB JSON chunk type: {path}")
    json_start = 20
    json_end = json_start + json_len
    try:
        return json.loads(data[json_start:json_end].decode("utf-8"))
    except Exception as ex:
        raise RuntimeError(f"Failed parsing GLB JSON: {path} ({ex})") from ex


def load_glb_info(path: str, skin_index: int = 0) -> GlbInfo:
    gltf = _read_glb_json(path)
    nodes = gltf.get("nodes", []) or []
    skins = gltf.get("skins", []) or []

    node_names: Set[str] = set()
    for n in nodes:
        name = (n or {}).get("name")
        if isinstance(name, str) and name:
            node_names.add(name)

    joint_names: Set[str] = set()
    joint_count = 0
    if skins and 0 <= skin_index < len(skins):
        joints = (skins[skin_index] or {}).get("joints", []) or []
        if isinstance(joints, list):
            joint_count = len(joints)
            for idx in joints:
                if not isinstance(idx, int) or idx < 0 or idx >= len(nodes):
                    continue
                name = (nodes[idx] or {}).get("name")
                if isinstance(name, str) and name:
                    joint_names.add(name)

    return GlbInfo(
        node_names=node_names,
        joint_names=joint_names,
        node_count=len(nodes),
        skin_count=len(skins),
        joint_count=joint_count,
    )


def parse_xanim_export_parts(path: str) -> List[str]:
    parts: List[str] = []
    for line in open(path, "r", encoding="utf-8", errors="replace").read().splitlines():
        if not line.startswith("PART "):
            continue
        # PART 0 "name"
        q = line.split('"')
        if len(q) >= 2 and q[1]:
            parts.append(q[1])
    return parts


def collect_xanim_bones(xanim_dir: str, pattern: str) -> Tuple[Set[str], List[str]]:
    glob_path = os.path.join(xanim_dir, pattern)
    files = sorted(glob.glob(glob_path))
    bones: Set[str] = set()
    for fp in files:
        bones.update(parse_xanim_export_parts(fp))
    return bones, files


def _sorted_sample(items: Iterable[str], n: int = 30) -> List[str]:
    return sorted(set(items))[: max(0, int(n))]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True, help="Primary viewmodel GLB path.")
    ap.add_argument(
        "--extra-glb",
        action="append",
        default=[],
        help="Optional extra GLB(s) to include in the runtime DObj union check.",
    )
    ap.add_argument("--xanim-dir", required=True, help="Folder containing xanim_export files.")
    ap.add_argument("--pattern", default="vm_thunder_gun_*.xanim_export", help="Glob pattern inside --xanim-dir.")
    ap.add_argument("--skin-index", type=int, default=0, help="Which glTF skin index to inspect.")
    ap.add_argument("--strict", action="store_true", help="Exit non-zero if any bones are missing from GLB nodes.")
    ap.add_argument("--report", default="", help="Optional JSON report output path.")
    ap.add_argument("--sample", type=int, default=25, help="How many missing bone names to include in output.")
    args = ap.parse_args(argv)

    glb_paths: List[str] = [os.path.abspath(args.glb)]
    glb_paths.extend(os.path.abspath(p) for p in (args.extra_glb or []) if p)
    xanim_dir = os.path.abspath(args.xanim_dir)

    for glb_path in glb_paths:
        if not os.path.exists(glb_path):
            raise SystemExit(f"Missing GLB: {glb_path}")
    if not os.path.isdir(xanim_dir):
        raise SystemExit(f"Missing xanim dir: {xanim_dir}")

    xanim_bones, files = collect_xanim_bones(xanim_dir, args.pattern)
    if not files:
        raise SystemExit(f"No xanim_export files matched: {os.path.join(xanim_dir, args.pattern)}")

    infos: List[GlbInfo] = [load_glb_info(p, skin_index=args.skin_index) for p in glb_paths]
    union_node_names: Set[str] = set()
    union_joint_names: Set[str] = set()
    total_nodes = 0
    total_skins = 0
    total_joints = 0
    for info in infos:
        union_node_names.update(info.node_names)
        union_joint_names.update(info.joint_names)
        total_nodes += info.node_count
        total_skins += info.skin_count
        total_joints += info.joint_count

    missing_from_nodes = sorted(xanim_bones - union_node_names)
    missing_from_joints = sorted(xanim_bones - union_joint_names) if union_joint_names else []

    ok_nodes = len(missing_from_nodes) == 0
    ok_joints = (len(missing_from_joints) == 0) if union_joint_names else True

    print("Thundergun rig validation")
    print(f"  GLBs:      {len(glb_paths)}")
    for path in glb_paths:
        print(f"    - {path}")
    print(f"  XAnims:    {xanim_dir} ({len(files)} files)")
    print(
        f"  Bones:     xanim={len(xanim_bones)} "
        f"union_named_nodes={len(union_node_names)} total_nodes={total_nodes}"
    )
    print(
        f"  Skins:     total={total_skins} (skin_index={args.skin_index}, "
        f"total_joints={total_joints}, union_named_joints={len(union_joint_names)})"
    )
    print(
        "  Missing:   "
        f"nodes={len(missing_from_nodes)} joints={len(missing_from_joints) if union_joint_names else 0}"
    )

    if missing_from_nodes:
        print("  Missing in GLB nodes (sample):")
        for name in _sorted_sample(missing_from_nodes, args.sample):
            print(f"    - {name}")
    if union_joint_names and missing_from_joints:
        print("  Missing in GLB skin joints (sample):")
        for name in _sorted_sample(missing_from_joints, args.sample):
            print(f"    - {name}")

    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "glbs": glb_paths,
        "xanim_dir": xanim_dir,
        "pattern": args.pattern,
        "xanim_files": [os.path.abspath(p) for p in files],
        "counts": {
            "xanim_bones": len(xanim_bones),
            "glb_total_nodes": total_nodes,
            "glb_union_named_nodes": len(union_node_names),
            "glb_total_skins": total_skins,
            "glb_total_joints": total_joints,
            "glb_union_named_joints": len(union_joint_names),
            "missing_from_nodes": len(missing_from_nodes),
            "missing_from_joints": len(missing_from_joints) if union_joint_names else 0,
        },
        "ok": {"nodes": ok_nodes, "joints": ok_joints},
        "missing_from_nodes": missing_from_nodes,
        "missing_from_joints": missing_from_joints,
    }

    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"  Report:    {os.path.abspath(args.report)}")

    if args.strict and not ok_nodes:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
