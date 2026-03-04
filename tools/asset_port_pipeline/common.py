from __future__ import annotations

import json
import math
import re
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


FLOAT_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")
BONE_DEF_RE = re.compile(r'^BONE\s+(\d+)\s+(-?\d+)\s+"(.*)"\s*$')
BONE_WEIGHT_RE = re.compile(r"^BONE\s+(\d+)\s+(-?\d+(?:\.\d+)?)\s*$")
VERT_RE = re.compile(r"^VERT\s+(\d+)\s*$")
NUM_LINE_RE = re.compile(r"^(NUM[A-Z]+)\s+(-?\d+)\s*$")
STATE_RE = re.compile(r"^([A-Za-z0-9_]+)\s*:")
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def percentile(sorted_values: Sequence[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    q = max(0.0, min(1.0, q))
    idx = (len(sorted_values) - 1) * q
    low = int(math.floor(idx))
    high = int(math.ceil(idx))
    if low == high:
        return float(sorted_values[low])
    frac = idx - low
    return float(sorted_values[low] * (1.0 - frac) + sorted_values[high] * frac)


def summarize_numeric(values: Sequence[float]) -> Dict[str, float]:
    if not values:
        return {
            "count": 0,
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "std": 0.0,
            "p50": 0.0,
            "p95": 0.0,
            "p99": 0.0,
        }
    sorted_vals = sorted(float(v) for v in values)
    return {
        "count": float(len(sorted_vals)),
        "min": float(sorted_vals[0]),
        "max": float(sorted_vals[-1]),
        "mean": float(statistics.fmean(sorted_vals)),
        "std": float(statistics.pstdev(sorted_vals)) if len(sorted_vals) > 1 else 0.0,
        "p50": percentile(sorted_vals, 0.50),
        "p95": percentile(sorted_vals, 0.95),
        "p99": percentile(sorted_vals, 0.99),
    }


def discover_files(roots: Sequence[Path], pattern: str) -> List[Path]:
    files: List[Path] = []
    for root in roots:
        if root.exists():
            files.extend(root.rglob(pattern))
    files = [path for path in files if path.is_file()]
    return sorted(files)


def parse_vec3(text: str) -> Tuple[float, float, float]:
    nums = [float(match.group(0)) for match in FLOAT_RE.finditer(text)]
    if len(nums) < 3:
        raise ValueError(f"Unable to parse vec3 from '{text}'")
    return nums[0], nums[1], nums[2]


def fmt_vec3(vec: Tuple[float, float, float]) -> str:
    return f"{vec[0]:.6f}, {vec[1]:.6f}, {vec[2]:.6f}"


@dataclass
class XModelVertex:
    index: int
    offset: Tuple[float, float, float]
    bones: List[Tuple[int, float]]


@dataclass
class XModelBone:
    index: int
    parent: int
    name: str


@dataclass
class XModelAst:
    header_lines: List[str]
    version: int
    bones: List[XModelBone]
    transforms: Dict[int, Dict[str, Tuple[float, float, float]]]
    vertices: List[XModelVertex]
    tail_lines: List[str]


def parse_xmodel_export_ast(path: Path) -> XModelAst:
    lines = read_text(path).splitlines()
    if not lines:
        raise ValueError("Empty xmodel_export file")

    model_idx = -1
    for idx, line in enumerate(lines):
        if line.strip() == "MODEL":
            model_idx = idx
            break
    if model_idx < 0:
        raise ValueError("MODEL token not found")

    i = model_idx + 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or not lines[i].strip().startswith("VERSION "):
        raise ValueError("VERSION token not found")
    version = int(lines[i].strip().split()[1])
    i += 1

    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines):
        raise ValueError("Unexpected EOF before NUMBONES")
    num_match = NUM_LINE_RE.match(lines[i].strip())
    if not num_match or num_match.group(1) != "NUMBONES":
        raise ValueError("NUMBONES token not found")
    num_bones = int(num_match.group(2))
    i += 1

    bones: List[XModelBone] = []
    for _ in range(num_bones):
        if i >= len(lines):
            raise ValueError("Unexpected EOF in bone definition list")
        line = lines[i].strip()
        match = BONE_DEF_RE.match(line)
        if not match:
            raise ValueError(f"Invalid bone definition line: '{line}'")
        bones.append(
            XModelBone(index=int(match.group(1)), parent=int(match.group(2)), name=match.group(3))
        )
        i += 1

    while i < len(lines) and not lines[i].strip():
        i += 1

    transforms: Dict[int, Dict[str, Tuple[float, float, float]]] = {}
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("NUMVERTS "):
            break
        if not line:
            i += 1
            continue
        if not line.startswith("BONE "):
            raise ValueError(f"Unexpected token before NUMVERTS: '{line}'")
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"Invalid transform bone line: '{line}'")
        bone_index = int(parts[1])
        i += 1

        transform: Dict[str, Tuple[float, float, float]] = {}
        for key in ("OFFSET", "SCALE", "X", "Y", "Z"):
            if i >= len(lines):
                raise ValueError("Unexpected EOF while parsing transforms")
            transform_line = lines[i].strip()
            if not transform_line.startswith(key + " "):
                raise ValueError(f"Expected '{key}' line, got '{transform_line}'")
            transform[key] = parse_vec3(transform_line[len(key) :].strip())
            i += 1
        transforms[bone_index] = transform

    if i >= len(lines):
        raise ValueError("Unexpected EOF before NUMVERTS")
    num_match = NUM_LINE_RE.match(lines[i].strip())
    if not num_match or num_match.group(1) != "NUMVERTS":
        raise ValueError("NUMVERTS token not found")
    num_verts = int(num_match.group(2))
    i += 1

    vertices: List[XModelVertex] = []
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("NUMFACES "):
            break
        if not line:
            i += 1
            continue

        vert_match = VERT_RE.match(line)
        if not vert_match:
            raise ValueError(f"Invalid vertex start line: '{line}'")
        vert_index = int(vert_match.group(1))
        i += 1

        if i >= len(lines):
            raise ValueError("Unexpected EOF after VERT")
        offset_line = lines[i].strip()
        if not offset_line.startswith("OFFSET "):
            raise ValueError(f"Expected OFFSET line, got '{offset_line}'")
        offset = parse_vec3(offset_line[len("OFFSET ") :])
        i += 1

        if i >= len(lines):
            raise ValueError("Unexpected EOF after OFFSET")
        bones_line = lines[i].strip()
        if not bones_line.startswith("BONES "):
            raise ValueError(f"Expected BONES line, got '{bones_line}'")
        num_inf = int(bones_line.split()[1])
        i += 1

        influences: List[Tuple[int, float]] = []
        for _ in range(num_inf):
            if i >= len(lines):
                raise ValueError("Unexpected EOF in vertex bones")
            bone_line = lines[i].strip()
            bone_match = BONE_WEIGHT_RE.match(bone_line)
            if not bone_match:
                raise ValueError(f"Invalid vertex BONE line: '{bone_line}'")
            influences.append((int(bone_match.group(1)), float(bone_match.group(2))))
            i += 1

        vertices.append(XModelVertex(index=vert_index, offset=offset, bones=influences))

    if len(vertices) != num_verts:
        raise ValueError(f"NUMVERTS mismatch: declared {num_verts}, parsed {len(vertices)}")
    if i >= len(lines):
        raise ValueError("NUMFACES token not found")

    return XModelAst(
        header_lines=lines[: model_idx + 1],
        version=version,
        bones=bones,
        transforms=transforms,
        vertices=vertices,
        tail_lines=lines[i:],
    )


def render_xmodel_export_ast(ast: XModelAst) -> str:
    out: List[str] = []
    out.extend(ast.header_lines)
    out.append(f"VERSION {ast.version}")
    out.append("")

    out.append(f"NUMBONES {len(ast.bones)}")
    for bone in ast.bones:
        out.append(f'BONE {bone.index} {bone.parent} "{bone.name}"')
    out.append("")

    for bone in ast.bones:
        if bone.index not in ast.transforms:
            raise ValueError(f"Missing transform block for bone index {bone.index}")
        transform = ast.transforms[bone.index]
        out.append(f"BONE {bone.index}")
        out.append(f"OFFSET {fmt_vec3(transform['OFFSET'])}")
        out.append(f"SCALE {fmt_vec3(transform['SCALE'])}")
        out.append(f"X {fmt_vec3(transform['X'])}")
        out.append(f"Y {fmt_vec3(transform['Y'])}")
        out.append(f"Z {fmt_vec3(transform['Z'])}")
        out.append("")

    out.append(f"NUMVERTS {len(ast.vertices)}")
    for idx, vertex in enumerate(ast.vertices):
        out.append(f"VERT {idx}")
        out.append(f"OFFSET {fmt_vec3(vertex.offset)}")
        out.append(f"BONES {len(vertex.bones)}")
        for bone_index, weight in vertex.bones:
            out.append(f"BONE {bone_index} {weight:.6f}")
        out.append("")

    out.extend(ast.tail_lines)
    return "\n".join(out).rstrip() + "\n"


def summarize_xmodel(path: Path) -> Dict[str, Any]:
    ast = parse_xmodel_export_ast(path)

    max_influences = 0
    total_influences = 0
    invalid_weight_sums = 0
    vertices_without_bones = 0
    max_ref_bone_index = -1

    xs: List[float] = []
    ys: List[float] = []
    zs: List[float] = []

    for vertex in ast.vertices:
        inf_count = len(vertex.bones)
        max_influences = max(max_influences, inf_count)
        total_influences += inf_count
        if inf_count == 0:
            vertices_without_bones += 1
        weight_sum = sum(weight for _, weight in vertex.bones)
        if inf_count > 0 and abs(weight_sum - 1.0) > 1e-3:
            invalid_weight_sums += 1
        if inf_count > 0:
            max_ref_bone_index = max(max_ref_bone_index, max(index for index, _ in vertex.bones))

        xs.append(vertex.offset[0])
        ys.append(vertex.offset[1])
        zs.append(vertex.offset[2])

    num_verts = len(ast.vertices)
    size_x = (max(xs) - min(xs)) if xs else 0.0
    size_y = (max(ys) - min(ys)) if ys else 0.0
    size_z = (max(zs) - min(zs)) if zs else 0.0
    bbox_diag = math.sqrt(size_x * size_x + size_y * size_y + size_z * size_z)

    num_faces = 0
    num_objects = 0
    num_materials = 0
    for line in ast.tail_lines:
        stripped = line.strip()
        match = NUM_LINE_RE.match(stripped)
        if not match:
            continue
        token, value = match.group(1), int(match.group(2))
        if token == "NUMFACES":
            num_faces = value
        elif token == "NUMOBJECTS":
            num_objects = value
        elif token == "NUMMATERIALS":
            num_materials = value

    return {
        "path": str(path),
        "version": ast.version,
        "num_bones": len(ast.bones),
        "num_verts": num_verts,
        "num_faces": num_faces,
        "num_objects": num_objects,
        "num_materials": num_materials,
        "max_vertex_influences": max_influences,
        "avg_vertex_influences": (float(total_influences) / float(num_verts)) if num_verts else 0.0,
        "invalid_weight_sums": invalid_weight_sums,
        "vertices_without_bones": vertices_without_bones,
        "max_ref_bone_index": max_ref_bone_index,
        "bbox_size_x": size_x,
        "bbox_size_y": size_y,
        "bbox_size_z": size_z,
        "bbox_diag": bbox_diag,
        "bone_names": [bone.name for bone in ast.bones],
    }


WEAPON_NUMERIC_KEYS = [
    "clipSize",
    "maxAmmo",
    "startAmmo",
    "damage",
    "playerDamage",
    "fireTime",
    "reloadTime",
    "reloadEmptyTime",
    "raiseTime",
    "dropTime",
    "projectileSpeed",
    "projectileLifetime",
    "explosionRadius",
    "explosionInnerDamage",
    "explosionOuterDamage",
]


def parse_weapon_file(path: Path) -> Dict[str, Any]:
    text = read_text(path).strip()
    tokens = text.split("\\")
    if not tokens:
        raise ValueError("Empty weapon file")
    if tokens[0].upper() == "WEAPONFILE":
        tokens = tokens[1:]

    fields: Dict[str, str] = {}
    for idx in range(0, len(tokens), 2):
        key = tokens[idx].strip()
        value = tokens[idx + 1].strip() if idx + 1 < len(tokens) else ""
        if key:
            fields[key] = value

    numeric_values: Dict[str, float] = {}
    for key in WEAPON_NUMERIC_KEYS:
        raw = fields.get(key, "")
        if raw == "":
            continue
        try:
            numeric_values[key] = float(raw)
        except ValueError:
            continue

    model_ref_keys = [key for key in fields if "Model" in key]
    anim_ref_keys = [key for key in fields if "Anim" in key or "anim" in key]

    model_refs = [fields[key] for key in model_ref_keys if fields[key]]
    anim_refs = [fields[key] for key in anim_ref_keys if fields[key]]

    return {
        "path": str(path),
        "field_count": len(fields),
        "fields": fields,
        "numeric_values": numeric_values,
        "model_ref_count": len(model_refs),
        "anim_ref_count": len(anim_refs),
        "model_refs": model_refs,
        "anim_refs": anim_refs,
        "weapon_type": fields.get("weaponType", ""),
        "inventory_type": fields.get("inventoryType", ""),
        "fire_type": fields.get("fireType", ""),
    }


def parse_animtree_atr(path: Path) -> Dict[str, Any]:
    entries: List[str] = []
    for raw_line in read_text(path).splitlines():
        line = raw_line.split("//", 1)[0].strip()
        if not line or line in ("{", "}") or line.endswith("{"):
            continue
        if line == "body":
            continue
        if IDENT_RE.match(line):
            entries.append(line)
    unique_entries = sorted(set(entries))
    return {
        "path": str(path),
        "entry_count": len(entries),
        "unique_entry_count": len(unique_entries),
        "entries": unique_entries,
    }


def parse_animstate_asd(path: Path) -> Dict[str, Any]:
    lines = read_text(path).splitlines()
    state_count = 0
    anim_refs: List[str] = []
    inside_block = False

    for raw_line in lines:
        line = raw_line.split("//", 1)[0].strip()
        if not line:
            continue
        if STATE_RE.match(line):
            state_count += 1
            continue
        if line == "{":
            inside_block = True
            continue
        if line == "}":
            inside_block = False
            continue
        if inside_block and IDENT_RE.match(line):
            anim_refs.append(line)

    unique_anims = sorted(set(anim_refs))
    return {
        "path": str(path),
        "state_count": state_count,
        "anim_ref_count": len(anim_refs),
        "unique_anim_ref_count": len(unique_anims),
        "anim_refs": unique_anims,
    }


def feature_vector_from_xmodel_summary(summary: Dict[str, Any]) -> Tuple[List[float], List[str]]:
    feature_names = [
        "version",
        "num_bones",
        "num_verts",
        "num_faces",
        "num_materials",
        "max_vertex_influences",
        "avg_vertex_influences",
        "invalid_weight_sums",
        "vertices_without_bones",
        "bbox_diag",
        "bbox_size_x",
        "bbox_size_y",
        "bbox_size_z",
    ]
    vector = [float(summary.get(name, 0.0)) for name in feature_names]
    return vector, feature_names


def normalize_weights(weights: List[Tuple[int, float]]) -> List[Tuple[int, float]]:
    if not weights:
        return []
    total = sum(weight for _, weight in weights)
    if total <= 0:
        uniform = 1.0 / float(len(weights))
        return [(idx, uniform) for idx, _ in weights]
    return [(idx, weight / total) for idx, weight in weights]


def clamp_vertex_influences(
    vertices: Iterable[XModelVertex], max_influences: int
) -> List[XModelVertex]:
    out: List[XModelVertex] = []
    for vertex in vertices:
        sorted_weights = sorted(vertex.bones, key=lambda item: (-item[1], item[0]))
        trimmed = sorted_weights[: max(1, max_influences)]
        trimmed = normalize_weights(trimmed)
        out.append(XModelVertex(index=vertex.index, offset=vertex.offset, bones=trimmed))
    return out


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
