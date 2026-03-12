from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser(description="Build a reduced BO3 IDG combined rig for T6.")
    parser.add_argument("--weapon-glb", required=True)
    parser.add_argument("--hands-glb", default="")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--metadata-out", default="")
    parser.add_argument("--mode", choices=("combined", "weapon_only"), default="combined")
    return parser.parse_args(argv)


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.outliner.orphans_purge(do_recursive=True)


def import_glb(filepath: Path, prefix: str) -> Tuple[bpy.types.Object, List[bpy.types.Object]]:
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.import_scene.gltf(filepath=str(filepath))
    imported = list(bpy.context.selected_objects)
    if not imported:
        raise RuntimeError(f"GLB import produced no objects: {filepath}")
    for obj in imported:
        obj.name = f"{prefix}{obj.name}"
        if obj.data and hasattr(obj.data, "name"):
            obj.data.name = f"{prefix}{obj.data.name}"
    armatures = [obj for obj in imported if obj.type == "ARMATURE"]
    meshes = [obj for obj in imported if obj.type == "MESH"]
    if len(armatures) != 1:
        raise RuntimeError(f"Expected a single armature in {filepath}, found {len(armatures)}")
    if not meshes:
        raise RuntimeError(f"No meshes found in import: {filepath}")
    return armatures[0], meshes


def load_manifest(path: Path) -> Dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Manifest must be an object: {path}")
    return payload


def armature_bone_names(armature_obj: bpy.types.Object) -> Set[str]:
    return {bone.name for bone in armature_obj.data.bones}


def armature_parent_map(armature_obj: bpy.types.Object) -> Dict[str, Optional[str]]:
    return {bone.name: (bone.parent.name if bone.parent else None) for bone in armature_obj.data.bones}


def parse_chain_index(name: str, prefix: str) -> Optional[int]:
    if not name.startswith(prefix):
        return None
    suffix = name[len(prefix) :]
    match = re.match(r"(\d+)(?:_animate)?$", suffix)
    return int(match.group(1)) if match else None


def build_weapon_keep_set(weapon_bones: Set[str], chain_limits: Dict[str, int]) -> Set[str]:
    keep = set(weapon_bones)
    for bone_name in list(weapon_bones):
        for prefix, limit in chain_limits.items():
            index = parse_chain_index(bone_name, prefix)
            if index is None:
                continue
            if index > int(limit):
                keep.discard(bone_name)
            break
    return keep


def build_weapon_keep_set_from_manifest(manifest: Dict[str, object], weapon_bones: Set[str]) -> Set[str]:
    explicit_keep = [str(name) for name in manifest.get("weapon_keep_bones", [])]
    if explicit_keep:
        keep = {name for name in explicit_keep if name in weapon_bones}
        required = {str(name) for name in manifest.get("required_bones", [])}
        keep.update(name for name in required if name in weapon_bones)
        return keep
    chain_limits = {str(key): int(value) for key, value in dict(manifest.get("weapon_chain_limits", {})).items()}
    return build_weapon_keep_set(weapon_bones, chain_limits=chain_limits)


def trim_keep_set_to_cap(
    keep_names: Set[str],
    required: Set[str],
    optional_order: Sequence[str],
    bone_cap: int,
) -> List[str]:
    removed_optional: List[str] = []
    for name in optional_order:
        if len(keep_names) <= bone_cap:
            break
        if name in required:
            continue
        if name in keep_names:
            keep_names.remove(name)
            removed_optional.append(name)
    missing_required = sorted(name for name in required if name not in keep_names)
    if missing_required:
        raise RuntimeError(f"Required bones missing from keep set: {missing_required}")
    if len(keep_names) > bone_cap:
        raise RuntimeError(f"Reduced rig still exceeds T6 cap: kept={len(keep_names)} cap={bone_cap}")
    return removed_optional


def select_combined_keep_set(
    manifest: Dict[str, object],
    weapon_bones: Set[str],
    hands_bones: Set[str],
) -> Tuple[Set[str], Set[str], List[str]]:
    hands_keep = set(str(name) for name in manifest.get("hands_keep_bones", []) if str(name) in hands_bones)
    weapon_keep = build_weapon_keep_set_from_manifest(manifest, weapon_bones)
    required = {str(name) for name in manifest.get("required_bones", [])}
    optional_order = [str(name) for name in manifest.get("optional_bones", [])]
    bone_cap = int(manifest.get("t6_bone_cap", 160))
    combined = set(weapon_keep) | set(hands_keep)
    removed_optional = trim_keep_set_to_cap(combined, required, optional_order, bone_cap)
    for name in removed_optional:
        weapon_keep.discard(name)
        hands_keep.discard(name)
    return weapon_keep, hands_keep, removed_optional


def select_weapon_only_keep_set(
    manifest: Dict[str, object],
    weapon_bones: Set[str],
) -> Tuple[Set[str], List[str]]:
    weapon_keep = build_weapon_keep_set_from_manifest(manifest, weapon_bones)
    required = {str(name) for name in manifest.get("required_bones", [])}
    optional_order = [str(name) for name in manifest.get("optional_bones", [])]
    bone_cap = int(manifest.get("t6_bone_cap", 160))
    removed_optional = trim_keep_set_to_cap(weapon_keep, required, optional_order, bone_cap)
    return weapon_keep, removed_optional


def build_source_lookup(
    weapon_armature: bpy.types.Object,
    hands_armature: Optional[bpy.types.Object],
    keep_weapon: Set[str],
    keep_hands: Set[str],
) -> Dict[str, Tuple[str, bpy.types.Object, bpy.types.Bone]]:
    lookup: Dict[str, Tuple[str, bpy.types.Object, bpy.types.Bone]] = {}
    for name in keep_weapon:
        lookup[name] = ("weapon", weapon_armature, weapon_armature.data.bones[name])
    if hands_armature is not None:
        for name in keep_hands:
            lookup[name] = ("hands", hands_armature, hands_armature.data.bones[name])
    return lookup


def parent_target_for_removed(
    bone_name: str,
    keep_set: Set[str],
    parent_map: Dict[str, Optional[str]],
    explicit_remap: Dict[str, str],
) -> Optional[str]:
    target = explicit_remap.get(bone_name)
    if target in keep_set:
        return target
    current = parent_map.get(bone_name)
    visited: Set[str] = set()
    while current and current not in visited:
        if current in keep_set:
            return current
        visited.add(current)
        target = explicit_remap.get(current)
        if target in keep_set:
            return target
        current = parent_map.get(current)
    return None


def build_remap_table(
    source_bones: Set[str],
    keep_set: Set[str],
    parent_map: Dict[str, Optional[str]],
    explicit_remap: Dict[str, str],
) -> Dict[str, str]:
    remap: Dict[str, str] = {}
    for name in sorted(source_bones):
        if name in keep_set:
            continue
        target = parent_target_for_removed(name, keep_set, parent_map, explicit_remap)
        if target:
            remap[name] = target
    return remap


def combined_parent_map(
    keep_names: Set[str],
    source_lookup: Dict[str, Tuple[str, bpy.types.Object, bpy.types.Bone]],
    weapon_parent_map: Dict[str, Optional[str]],
    hands_parent_map: Dict[str, Optional[str]],
    explicit_parent_overrides: Dict[str, str],
    explicit_remap: Dict[str, str],
) -> Dict[str, Optional[str]]:
    parents: Dict[str, Optional[str]] = {}
    for name in keep_names:
        override = explicit_parent_overrides.get(name)
        if override:
            parents[name] = override if override in keep_names else None
            continue
        source_kind = source_lookup[name][0]
        source_parents = weapon_parent_map if source_kind == "weapon" else hands_parent_map
        current = source_parents.get(name)
        visited: Set[str] = set()
        while current and current not in visited:
            if current in keep_names:
                parents[name] = current
                break
            visited.add(current)
            remap = explicit_remap.get(current)
            if remap in keep_names:
                parents[name] = remap
                break
            current = source_parents.get(current)
        else:
            parents[name] = None
    return parents


def topo_sort_bones(parent_map: Dict[str, Optional[str]]) -> List[str]:
    ordered: List[str] = []
    temp: Set[str] = set()
    perm: Set[str] = set()

    def visit(name: str) -> None:
        if name in perm:
            return
        if name in temp:
            raise RuntimeError(f"Bone parent cycle detected at {name}")
        temp.add(name)
        parent = parent_map.get(name)
        if parent:
            visit(parent)
        temp.remove(name)
        perm.add(name)
        ordered.append(name)

    for bone_name in sorted(parent_map):
        visit(bone_name)
    return ordered


def create_reduced_armature(
    keep_names: Set[str],
    source_lookup: Dict[str, Tuple[str, bpy.types.Object, bpy.types.Bone]],
    parent_map: Dict[str, Optional[str]],
) -> bpy.types.Object:
    armature_data = bpy.data.armatures.new("bo3_rev_idg_reduced_armature")
    armature_obj = bpy.data.objects.new("bo3_rev_idg_reduced_armature", armature_data)
    bpy.context.scene.collection.objects.link(armature_obj)
    bpy.ops.object.select_all(action="DESELECT")
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode="EDIT")

    edit_bones = armature_data.edit_bones
    for bone_name in topo_sort_bones(parent_map):
        _, source_armature, source_bone = source_lookup[bone_name]
        edit_bone = edit_bones.new(bone_name)
        source_matrix = source_armature.matrix_world @ source_bone.matrix_local
        source_head = source_armature.matrix_world @ source_bone.head_local
        source_tail = source_armature.matrix_world @ source_bone.tail_local
        edit_bone.tail = Vector((0.0, 0.0, 0.05))
        edit_bone.matrix = source_matrix
        edit_bone.length = max((source_tail - source_head).length, 0.001)
        edit_bone.use_connect = False

    for bone_name, parent_name in parent_map.items():
        if parent_name:
            edit_bones[bone_name].parent = edit_bones[parent_name]
            edit_bones[bone_name].use_connect = False

    bpy.ops.object.mode_set(mode="OBJECT")
    return armature_obj


def transfer_group_weight(mesh_obj: bpy.types.Object, source_name: str, target_name: str) -> None:
    source_group = mesh_obj.vertex_groups.get(source_name)
    if source_group is None:
        return
    target_group = mesh_obj.vertex_groups.get(target_name)
    if target_group is None:
        target_group = mesh_obj.vertex_groups.new(name=target_name)
    source_index = source_group.index
    for vertex in mesh_obj.data.vertices:
        for assignment in vertex.groups:
            if assignment.group == source_index and assignment.weight > 0.0:
                target_group.add([vertex.index], float(assignment.weight), "ADD")
    mesh_obj.vertex_groups.remove(source_group)


def remap_mesh_vertex_groups(
    mesh_obj: bpy.types.Object,
    remap_table: Dict[str, str],
    keep_names: Set[str],
) -> Dict[str, int]:
    transferred = 0
    removed = 0
    for source_name, target_name in remap_table.items():
        if mesh_obj.vertex_groups.get(source_name) is None:
            continue
        transfer_group_weight(mesh_obj, source_name, target_name)
        transferred += 1
    for group in list(mesh_obj.vertex_groups):
        if group.name not in keep_names:
            mesh_obj.vertex_groups.remove(group)
            removed += 1
    return {"transferred_groups": transferred, "removed_groups": removed}


def attach_meshes_to_armature(meshes: Sequence[bpy.types.Object], armature_obj: bpy.types.Object) -> None:
    for mesh_obj in meshes:
        mesh_obj.parent = armature_obj
        mesh_obj.parent_type = "OBJECT"
        mesh_obj.matrix_parent_inverse = armature_obj.matrix_world.inverted()
        for modifier in list(mesh_obj.modifiers):
            if modifier.type == "ARMATURE":
                mesh_obj.modifiers.remove(modifier)
        modifier = mesh_obj.modifiers.new(name="Armature", type="ARMATURE")
        modifier.object = armature_obj
        modifier.use_vertex_groups = True
        modifier.use_bone_envelopes = False


def apply_fit_transform(
    armature_obj: bpy.types.Object,
    meshes: Sequence[bpy.types.Object],
    manifest: Dict[str, object],
) -> Dict[str, List[float]]:
    fit = manifest.get("fit_transform", {})
    if not isinstance(fit, dict):
        return {"scale": [1.0, 1.0, 1.0], "translation": [0.0, 0.0, 0.0]}
    raw_scale = fit.get("scale", [1.0, 1.0, 1.0])
    raw_translation = fit.get("translation", [0.0, 0.0, 0.0])
    if not isinstance(raw_scale, (list, tuple)) or len(raw_scale) != 3:
        raise RuntimeError("fit_transform.scale must be a 3-element array")
    if not isinstance(raw_translation, (list, tuple)) or len(raw_translation) != 3:
        raise RuntimeError("fit_transform.translation must be a 3-element array")
    scale = [float(v) for v in raw_scale]
    translation = [float(v) for v in raw_translation]
    if scale == [1.0, 1.0, 1.0] and translation == [0.0, 0.0, 0.0]:
        return {"scale": scale, "translation": translation}

    objects = [armature_obj, *meshes]
    for obj in objects:
        obj.location = Vector(translation)
        obj.scale = Vector(scale)
    bpy.context.view_layer.update()

    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=True)
    bpy.context.view_layer.update()
    return {"scale": scale, "translation": translation}


def export_glb(output_path: Path, objects: Sequence[bpy.types.Object]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    supported = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    kwargs = {
        "filepath": str(output_path),
        "export_format": "GLB",
        "use_selection": True,
        "export_apply": True,
        "export_texcoords": True,
        "export_normals": True,
        "export_yup": True,
    }
    if "export_colors" in supported:
        kwargs["export_colors"] = True
    elif "export_vertex_color" in supported:
        kwargs["export_vertex_color"] = "MATERIAL"
        if "export_all_vertex_colors" in supported:
            kwargs["export_all_vertex_colors"] = True
    bpy.ops.export_scene.gltf(**{key: value for key, value in kwargs.items() if key in supported})


def main() -> None:
    args = parse_args()
    weapon_glb = Path(args.weapon_glb).resolve()
    hands_glb = Path(args.hands_glb).resolve() if args.hands_glb else None
    manifest_path = Path(args.manifest).resolve()
    output_path = Path(args.output).resolve()
    metadata_out = Path(args.metadata_out).resolve() if args.metadata_out else None
    manifest = load_manifest(manifest_path)

    reset_scene()
    weapon_armature, weapon_meshes = import_glb(weapon_glb, prefix="weapon_")
    hands_armature: Optional[bpy.types.Object] = None
    hands_meshes: List[bpy.types.Object] = []
    if args.mode == "combined":
        if hands_glb is None:
            raise RuntimeError("--hands-glb is required in combined mode")
        hands_armature, hands_meshes = import_glb(hands_glb, prefix="hands_")
    bpy.context.view_layer.update()

    weapon_bones = armature_bone_names(weapon_armature)
    hands_bones = armature_bone_names(hands_armature) if hands_armature is not None else set()
    explicit_remap = {str(key): str(value) for key, value in dict(manifest.get("explicit_weight_remap", {})).items()}
    explicit_parent_overrides = {
        str(key): str(value) for key, value in dict(manifest.get("explicit_parent_overrides", {})).items()
    }
    if args.mode == "combined":
        keep_weapon, keep_hands, removed_optional = select_combined_keep_set(manifest, weapon_bones, hands_bones)
    else:
        keep_weapon, removed_optional = select_weapon_only_keep_set(manifest, weapon_bones)
        keep_hands = set()
    keep_names = set(keep_weapon) | set(keep_hands)
    source_lookup = build_source_lookup(weapon_armature, hands_armature, keep_weapon, keep_hands)
    weapon_parent_map = armature_parent_map(weapon_armature)
    hands_parent_map = armature_parent_map(hands_armature) if hands_armature is not None else {}
    parent_map = combined_parent_map(
        keep_names=keep_names,
        source_lookup=source_lookup,
        weapon_parent_map=weapon_parent_map,
        hands_parent_map=hands_parent_map,
        explicit_parent_overrides=explicit_parent_overrides,
        explicit_remap=explicit_remap,
    )
    reduced_armature = create_reduced_armature(keep_names, source_lookup, parent_map)

    weapon_remap = build_remap_table(weapon_bones, keep_names, weapon_parent_map, explicit_remap)
    hands_remap = (
        build_remap_table(hands_bones, keep_names, hands_parent_map, explicit_remap)
        if hands_armature is not None
        else {}
    )
    transfer_stats: Dict[str, Dict[str, int]] = {}
    for mesh_obj in weapon_meshes:
        transfer_stats[mesh_obj.name] = remap_mesh_vertex_groups(mesh_obj, weapon_remap, keep_names)
    for mesh_obj in hands_meshes:
        transfer_stats[mesh_obj.name] = remap_mesh_vertex_groups(mesh_obj, hands_remap, keep_names)

    export_meshes = list(weapon_meshes) + list(hands_meshes)
    attach_meshes_to_armature(export_meshes, reduced_armature)
    fit_transform = apply_fit_transform(reduced_armature, export_meshes, manifest)
    bpy.context.view_layer.update()
    export_glb(output_path, [reduced_armature, *export_meshes])

    metadata = {
        "mode": args.mode,
        "weapon_glb": str(weapon_glb),
        "hands_glb": str(hands_glb) if hands_glb is not None else "",
        "output_glb": str(output_path),
        "bone_cap": int(manifest.get("t6_bone_cap", 160)),
        "source_weapon_bones": len(weapon_bones),
        "source_hands_bones": len(hands_bones),
        "kept_weapon_bones": len(keep_weapon),
        "kept_hands_bones": len(keep_hands),
        "kept_total_bones": len(keep_names),
        "removed_optional_bones": removed_optional,
        "kept_bones": sorted(keep_names),
        "weapon_removed_bones": sorted(weapon_bones - keep_names),
        "hands_removed_bones": sorted(hands_bones - keep_names),
        "weapon_remap": weapon_remap,
        "hands_remap": hands_remap,
        "unresolved_weapon_bones": sorted(set(weapon_bones) - keep_names - set(weapon_remap)),
        "unresolved_hands_bones": sorted(set(hands_bones) - keep_names - set(hands_remap)),
        "transfer_stats": transfer_stats,
        "weapon_mesh_names": [obj.name for obj in weapon_meshes],
        "hands_mesh_names": [obj.name for obj in hands_meshes],
        "within_cap": len(keep_names) <= int(manifest.get("t6_bone_cap", 160)),
        "fit_transform": fit_transform,
        "blender_version": list(bpy.app.version),
    }
    if metadata_out:
        metadata_out.parent.mkdir(parents=True, exist_ok=True)
        metadata_out.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
