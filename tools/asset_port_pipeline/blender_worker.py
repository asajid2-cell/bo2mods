from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

import bpy


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser(description="Blender worker for BO2 mesh conversion.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--skeleton-map", default="")
    parser.add_argument("--decimate-ratio", type=float, default=1.0)
    parser.add_argument("--max-bones", type=int, default=128)
    parser.add_argument("--max-weights", type=int, default=4)
    parser.add_argument("--max-submesh-vertices", type=int, default=2400)
    parser.add_argument("--metadata-out", default="")
    return parser.parse_args(argv)


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.outliner.orphans_purge(do_recursive=True)


def import_model(input_path: Path) -> None:
    ext = input_path.suffix.lower()
    if ext in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(input_path))
        return
    if ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(input_path), automatic_bone_orientation=True)
        return
    if ext == ".obj":
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=str(input_path))
        else:
            bpy.ops.import_scene.obj(filepath=str(input_path))
        return
    if ext == ".dae":
        bpy.ops.wm.collada_import(filepath=str(input_path))
        return
    raise ValueError(f"Unsupported input extension: {ext}")


def scene_meshes() -> List[bpy.types.Object]:
    return [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]


def scene_armatures() -> List[bpy.types.Object]:
    return [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]


def mesh_bounds(mesh_obj: bpy.types.Object) -> Dict[str, List[float]]:
    corners = [mesh_obj.matrix_world @ v.co for v in mesh_obj.data.vertices]
    if not corners:
        return {"min": [0.0, 0.0, 0.0], "max": [0.0, 0.0, 0.0], "size": [0.0, 0.0, 0.0], "max_dim": 0.0}
    xs = [float(v.x) for v in corners]
    ys = [float(v.y) for v in corners]
    zs = [float(v.z) for v in corners]
    mins = [min(xs), min(ys), min(zs)]
    maxs = [max(xs), max(ys), max(zs)]
    size = [maxs[0] - mins[0], maxs[1] - mins[1], maxs[2] - mins[2]]
    return {"min": mins, "max": maxs, "size": size, "max_dim": max(size)}


def split_mesh_by_material(mesh_obj: bpy.types.Object) -> None:
    """Separate a mesh into per-material meshes (one mesh per material slot)."""
    if len(mesh_obj.data.materials) <= 1:
        return
    bpy.ops.object.select_all(action="DESELECT")
    mesh_obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="MATERIAL")
    bpy.ops.object.mode_set(mode="OBJECT")


def split_mesh_by_face_halves(mesh_obj: bpy.types.Object, max_vertices: int, max_iterations: int = 10) -> None:
    # Deterministic fallback splitter: repeatedly separate half the faces until below vertex cap.
    iteration = 0
    while iteration < max_iterations and int(len(mesh_obj.data.vertices)) > int(max_vertices):
        polys = list(mesh_obj.data.polygons)
        if len(polys) < 2:
            break
        split_from = len(polys) // 2

        bpy.ops.object.select_all(action="DESELECT")
        mesh_obj.select_set(True)
        bpy.context.view_layer.objects.active = mesh_obj
        bpy.ops.object.mode_set(mode="OBJECT")
        for poly in mesh_obj.data.polygons:
            poly.select = False
        for poly in polys[split_from:]:
            mesh_obj.data.polygons[poly.index].select = True
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.separate(type="SELECTED")
        bpy.ops.object.mode_set(mode="OBJECT")

        # Continue splitting the largest remaining mesh in scene.
        meshes = sorted(scene_meshes(), key=lambda obj: len(obj.data.vertices), reverse=True)
        if not meshes:
            break
        mesh_obj = meshes[0]
        iteration += 1


def enforce_vertex_limit(max_vertices: int, max_surfaces: int = 255) -> Dict[str, int]:
    meshes = scene_meshes()
    if not meshes:
        return {"max_submesh_vertices": 0, "submesh_count": 0, "submesh_over_limit": 0}

    if max_vertices <= 0:
        return {
            "max_submesh_vertices": max((len(obj.data.vertices) for obj in meshes), default=0),
            "submesh_count": len(meshes),
            "submesh_over_limit": 0,
        }

    # Step 1: Separate by material (not loose parts) to get a sane starting count.
    if len(meshes) == 1 and len(meshes[0].data.materials) > 1:
        split_mesh_by_material(meshes[0])
        bpy.context.view_layer.update()

    # Step 2: Iteratively split the largest oversized mesh until all are under limit
    # or we hit the max_surfaces cap (T6 engine limit = 255).
    for _pass in range(64):
        meshes = sorted(scene_meshes(), key=lambda obj: len(obj.data.vertices), reverse=True)
        if not meshes:
            break
        biggest = meshes[0]
        if int(len(biggest.data.vertices)) <= int(max_vertices):
            break
        if len(meshes) >= max_surfaces:
            break
        split_mesh_by_face_halves(
            mesh_obj=biggest,
            max_vertices=max_vertices,
            max_iterations=4,
        )
        bpy.context.view_layer.update()

    meshes = scene_meshes()
    counts = [int(len(obj.data.vertices)) for obj in meshes]
    return {
        "max_submesh_vertices": max(counts) if counts else 0,
        "submesh_count": len(counts),
        "submesh_over_limit": sum(1 for count in counts if count > int(max_vertices)),
    }


def join_meshes(meshes: List[bpy.types.Object]) -> bpy.types.Object:
    if len(meshes) == 1:
        return meshes[0]
    bpy.ops.object.select_all(action="DESELECT")
    for mesh in meshes:
        mesh.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def apply_transforms(obj: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def add_and_apply_modifier(obj: bpy.types.Object, mod_type: str, setup: Optional[dict] = None) -> None:
    setup = setup or {}
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    modifier = obj.modifiers.new(name=f"{mod_type}_mod", type=mod_type)
    for key, value in setup.items():
        setattr(modifier, key, value)
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def bone_usage(mesh_obj: bpy.types.Object) -> Dict[str, float]:
    usage: Dict[str, float] = {}
    groups = mesh_obj.vertex_groups
    for vertex in mesh_obj.data.vertices:
        for assignment in vertex.groups:
            group = groups[assignment.group]
            usage[group.name] = usage.get(group.name, 0.0) + float(assignment.weight)
    return usage


def load_skeleton_map(path: Path) -> Dict[str, str]:
    if not path or not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    mapping = payload.get("bone_map", {})
    if not isinstance(mapping, dict):
        return {}
    out: Dict[str, str] = {}
    for key, value in mapping.items():
        src = str(key).strip()
        dst = str(value).strip()
        if not src or not dst:
            continue
        out[src] = dst
        out[src.lower()] = dst
    return out


def rename_bones(armature_obj: bpy.types.Object, mapping: Dict[str, str]) -> Dict[str, int]:
    if not mapping:
        return {"renamed": 0, "unchanged": len(armature_obj.data.bones)}
    renamed = 0
    unchanged = 0
    bpy.ops.object.select_all(action="DESELECT")
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode="EDIT")
    for bone in armature_obj.data.edit_bones:
        target = mapping.get(bone.name) or mapping.get(bone.name.lower())
        if target:
            if bone.name != target:
                bone.name = target
                renamed += 1
            else:
                unchanged += 1
        else:
            unchanged += 1
    bpy.ops.object.mode_set(mode="OBJECT")
    return {"renamed": renamed, "unchanged": unchanged}


def prune_bones_and_groups(
    mesh_obj: bpy.types.Object,
    armature_obj: bpy.types.Object,
    max_bones: int,
    required_bones: Iterable[str],
) -> Set[str]:
    if max_bones <= 0:
        return {bone.name for bone in armature_obj.data.bones}

    usage = bone_usage(mesh_obj)
    existing = [bone.name for bone in armature_obj.data.bones]
    required = [name for name in required_bones if name in existing]

    sorted_names = sorted(existing, key=lambda name: (-usage.get(name, 0.0), name))
    kept: List[str] = []
    for name in required + sorted_names:
        if name not in kept:
            kept.append(name)
        if len(kept) >= max_bones:
            break
    kept_set = set(kept)

    for group in list(mesh_obj.vertex_groups):
        if group.name not in kept_set:
            mesh_obj.vertex_groups.remove(group)

    bpy.ops.object.select_all(action="DESELECT")
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode="EDIT")
    for bone in list(armature_obj.data.edit_bones):
        if bone.name not in kept_set:
            armature_obj.data.edit_bones.remove(bone)
    bpy.ops.object.mode_set(mode="OBJECT")
    return kept_set


def clamp_vertex_weights(mesh_obj: bpy.types.Object, max_weights: int) -> None:
    if mesh_obj is None or mesh_obj.type != "MESH":
        return
    if not list(mesh_obj.vertex_groups):
        return
    bpy.ops.object.select_all(action="DESELECT")
    mesh_obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.object.mode_set(mode="OBJECT")
    try:
        bpy.ops.object.vertex_group_limit_total(limit=max(1, int(max_weights)))
        bpy.ops.object.vertex_group_normalize_all(lock_active=False)
    except RuntimeError:
        return


def bo2_bone_tag_quality(kept_bones: Iterable[str]) -> Dict[str, float]:
    names = [str(name) for name in kept_bones]
    total = float(len(names))
    if total <= 0:
        return {"bo2_style_count": 0.0, "bo2_style_ratio": 0.0, "tag_count": 0.0}
    bo2_style = sum(1 for name in names if name.startswith(("j_", "tag_")))
    tag_count = sum(1 for name in names if name.startswith("tag_"))
    return {
        "bo2_style_count": float(bo2_style),
        "bo2_style_ratio": float(bo2_style / total),
        "tag_count": float(tag_count),
    }


def collect_material_names(mesh_objects: Iterable[bpy.types.Object]) -> List[str]:
    names: List[str] = []
    seen = set()
    for mesh in mesh_objects:
        for mat in mesh.data.materials:
            if not mat:
                continue
            name = str(mat.name).strip()
            if not name:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            names.append(name)
    return sorted(names)


def export_glb(output_path: Path, objects: List[bpy.types.Object]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    # Blender glTF operator options vary by version; pass only supported keys.
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
        # Blender 5 uses enum values: MATERIAL/ACTIVE/NAME/NONE.
        kwargs["export_vertex_color"] = "MATERIAL"
        if "export_all_vertex_colors" in supported:
            kwargs["export_all_vertex_colors"] = True
    filtered = {k: v for k, v in kwargs.items() if k in supported}
    bpy.ops.export_scene.gltf(**filtered)


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    metadata_out = Path(args.metadata_out).resolve() if args.metadata_out else None
    skeleton_map_path = Path(args.skeleton_map).resolve() if args.skeleton_map else None

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    reset_scene()
    import_model(input_path)

    meshes = scene_meshes()
    if not meshes:
        raise RuntimeError("No mesh objects found after import")
    mesh = join_meshes(meshes)
    source_bounds = mesh_bounds(mesh)
    source_vertices = int(len(mesh.data.vertices))
    source_faces = int(len(mesh.data.polygons))
    apply_transforms(mesh)

    armatures = scene_armatures()
    has_armature = len(armatures) > 0
    armature = armatures[0] if has_armature else None

    rename_stats = {"renamed": 0, "unchanged": 0}
    if armature:
        # Default BO3->BO2 bone renames (applied before any user skeleton map).
        default_map: Dict[str, str] = {
            "tag_weapon": "tag_weapon_right",
        }
        existing_names = {b.name for b in armature.data.bones}
        # Only apply a default rename if the target doesn't already exist.
        auto_map = {k: v for k, v in default_map.items() if k in existing_names and v not in existing_names}
        mapping = load_skeleton_map(skeleton_map_path) if skeleton_map_path else {}
        # Auto-map overrides identity mappings (e.g. tag_weapon->tag_weapon) from skeleton maps.
        combined = {**mapping, **auto_map}
        rename_stats = rename_bones(armature, mapping=combined)
        required = list(set(mapping.values()))
        kept_bones = prune_bones_and_groups(
            mesh_obj=mesh,
            armature_obj=armature,
            max_bones=max(0, int(args.max_bones)),
            required_bones=required,
        )
    else:
        kept_bones = set()

    split_stats = enforce_vertex_limit(max_vertices=max(0, int(args.max_submesh_vertices)))
    for split_mesh in scene_meshes():
        clamp_vertex_weights(mesh_obj=split_mesh, max_weights=max(1, int(args.max_weights)))

    for split_mesh in scene_meshes():
        add_and_apply_modifier(split_mesh, "TRIANGULATE")
    decimate_ratio = float(args.decimate_ratio)
    if decimate_ratio < 0.999:
        for split_mesh in scene_meshes():
            add_and_apply_modifier(split_mesh, "DECIMATE", {"ratio": max(0.01, min(1.0, decimate_ratio))})

    export_meshes = scene_meshes()
    export_objects = list(export_meshes)
    if armature:
        export_objects.append(armature)
    export_glb(output_path=output_path, objects=export_objects)

    output_bounds = {}
    output_vertices = 0
    output_faces = 0
    if export_meshes:
        mins = [1e30, 1e30, 1e30]
        maxs = [-1e30, -1e30, -1e30]
        for mesh_obj in export_meshes:
            stats = mesh_bounds(mesh_obj)
            output_vertices += int(len(mesh_obj.data.vertices))
            output_faces += int(len(mesh_obj.data.polygons))
            for idx in range(3):
                mins[idx] = min(mins[idx], float(stats["min"][idx]))
                maxs[idx] = max(maxs[idx], float(stats["max"][idx]))
        size = [maxs[idx] - mins[idx] for idx in range(3)]
        output_bounds = {"min": mins, "max": maxs, "size": size, "max_dim": max(size)}
    source_max_dim = float(source_bounds.get("max_dim", 0.0))
    output_max_dim = float(output_bounds.get("max_dim", 0.0)) if output_bounds else 0.0
    bbox_ratio_max_dim = (output_max_dim / source_max_dim) if source_max_dim > 0.00001 else 1.0

    if metadata_out:
        metadata_out.parent.mkdir(parents=True, exist_ok=True)
        quality = bo2_bone_tag_quality(kept_bones)
        material_names = collect_material_names(export_meshes)
        max_vertex_groups = max((len(item.vertex_groups) for item in export_meshes), default=0)
        metadata = {
            "input": str(input_path),
            "output": str(output_path),
            "has_armature": has_armature,
            "source_has_armature": has_armature,
            "kept_bones": sorted(list(kept_bones)),
            "mesh_vertices": int(output_vertices),
            "mesh_faces": int(output_faces),
            "vertex_group_count": int(max_vertex_groups),
            "source_mesh_vertices": source_vertices,
            "source_mesh_faces": source_faces,
            "source_bounds": source_bounds,
            "output_bounds": output_bounds,
            "bbox_ratio_max_dim": float(bbox_ratio_max_dim),
            "split_stats": split_stats,
            "rename_stats": rename_stats,
            "material_names": material_names,
            "bo2_bone_name_ratio": quality["bo2_style_ratio"],
            "bo2_bone_name_count": int(quality["bo2_style_count"]),
            "tag_count": int(quality["tag_count"]),
            "potential_unit_scale_issue": bool(bbox_ratio_max_dim > 2.8 or bbox_ratio_max_dim < 0.35),
            "blender_version": list(bpy.app.version),
            "cwd": os.getcwd(),
        }
        metadata_out.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
