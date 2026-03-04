from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent

import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import (  # noqa: E402
    XModelAst,
    XModelBone,
    XModelVertex,
    clamp_vertex_influences,
    normalize_weights,
    parse_xmodel_export_ast,
    render_xmodel_export_ast,
)


def pick_kept_bones(ast: XModelAst, max_bones: int) -> Set[int]:
    if max_bones <= 0 or len(ast.bones) <= max_bones:
        return {bone.index for bone in ast.bones}

    usage: Dict[int, float] = {bone.index: 0.0 for bone in ast.bones}
    for vertex in ast.vertices:
        for bone_idx, weight in vertex.bones:
            usage[bone_idx] = usage.get(bone_idx, 0.0) + float(weight)

    score = sorted(usage.items(), key=lambda item: (-item[1], item[0]))
    kept = {idx for idx, _ in score[:max_bones]}

    # Keep root if present for safer re-parenting.
    if 0 in usage and 0 not in kept:
        worst = max(kept, key=lambda idx: (usage.get(idx, 0.0), idx))
        kept.remove(worst)
        kept.add(0)
    return kept


def reparent(old_parent: int, parent_lookup: Dict[int, int], remap: Dict[int, int]) -> int:
    current = old_parent
    while current != -1 and current not in remap:
        current = parent_lookup.get(current, -1)
    return remap[current] if current in remap else -1


def remap_bones(ast: XModelAst, kept_old: Set[int]) -> XModelAst:
    old_bones_sorted = [bone for bone in sorted(ast.bones, key=lambda bone: bone.index) if bone.index in kept_old]
    remap = {bone.index: new_index for new_index, bone in enumerate(old_bones_sorted)}
    parent_lookup = {bone.index: bone.parent for bone in ast.bones}

    new_bones: List[XModelBone] = []
    new_transforms: Dict[int, Dict[str, Tuple[float, float, float]]] = {}

    for bone in old_bones_sorted:
        new_idx = remap[bone.index]
        new_parent = reparent(bone.parent, parent_lookup=parent_lookup, remap=remap)
        new_bones.append(XModelBone(index=new_idx, parent=new_parent, name=bone.name))
        if bone.index in ast.transforms:
            new_transforms[new_idx] = ast.transforms[bone.index]

    fallback_bone = 0 if new_bones else -1
    new_vertices: List[XModelVertex] = []
    for vertex in ast.vertices:
        remapped = [(remap[idx], weight) for idx, weight in vertex.bones if idx in remap]
        remapped = normalize_weights(remapped)
        if not remapped and fallback_bone != -1:
            remapped = [(fallback_bone, 1.0)]
        new_vertices.append(XModelVertex(index=vertex.index, offset=vertex.offset, bones=remapped))

    return XModelAst(
        header_lines=ast.header_lines,
        version=ast.version,
        bones=new_bones,
        transforms=new_transforms,
        vertices=new_vertices,
        tail_lines=ast.tail_lines,
    )


def process_file(
    input_path: Path,
    output_path: Path,
    target_version: int,
    max_influences: int,
    max_bones: int,
) -> None:
    ast = parse_xmodel_export_ast(input_path)
    ast.version = target_version
    ast.vertices = clamp_vertex_influences(ast.vertices, max_influences=max_influences)

    kept = pick_kept_bones(ast, max_bones=max_bones)
    ast = remap_bones(ast, kept_old=kept)

    rendered = render_xmodel_export_ast(ast)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply deterministic BO2 compatibility compression to xmodel_export files."
    )
    parser.add_argument("--input", required=True, help="Input xmodel_export file or directory.")
    parser.add_argument("--output", required=True, help="Output file or directory.")
    parser.add_argument("--target-version", type=int, default=6, help="Output VERSION field (default 6).")
    parser.add_argument(
        "--max-influences",
        type=int,
        default=4,
        help="Maximum bone influences per vertex (default 4).",
    )
    parser.add_argument(
        "--max-bones",
        type=int,
        default=128,
        help="Maximum number of bones to keep. 0 disables pruning.",
    )
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    if input_path.is_file():
        target_file = output_path
        if output_path.is_dir():
            target_file = output_path / input_path.name
        process_file(
            input_path=input_path,
            output_path=target_file,
            target_version=args.target_version,
            max_influences=max(1, args.max_influences),
            max_bones=max(0, args.max_bones),
        )
        print(f"Wrote: {target_file}")
        return

    if not input_path.is_dir():
        raise FileNotFoundError(f"Input not found: {input_path}")

    files = sorted(input_path.rglob("*.xmodel_export"))
    if not files:
        raise FileNotFoundError(f"No .xmodel_export files found in {input_path}")
    output_path.mkdir(parents=True, exist_ok=True)

    for idx, source in enumerate(files, start=1):
        relative = source.relative_to(input_path)
        destination = output_path / relative
        process_file(
            input_path=source,
            output_path=destination,
            target_version=args.target_version,
            max_influences=max(1, args.max_influences),
            max_bones=max(0, args.max_bones),
        )
        if idx % 200 == 0:
            print(f"processed {idx}/{len(files)}")

    print(f"Wrote {len(files)} files to: {output_path}")


if __name__ == "__main__":
    main()

