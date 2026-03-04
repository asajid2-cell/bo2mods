from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Sequence, Tuple

import bpy
from mathutils import Vector


def _argv_after_double_dash(argv: Sequence[str]) -> List[str]:
    if "--" in argv:
        return list(argv[argv.index("--") + 1 :])
    return list(argv)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert CoD XMODEL_BIN/XANIM_BIN assets via Blender.")
    parser.add_argument("--asset-kind", choices=["xmodel", "xanim"], required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--blender-cod-root", required=True, help="Path containing io_scene_cod package.")
    parser.add_argument("--scale", type=float, default=1.0, help="Global model scale multiplier.")
    return parser.parse_args(_argv_after_double_dash(sys.argv[1:]))


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def ensure_blender_cod_importable(blender_cod_root: Path) -> None:
    root = blender_cod_root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"blender-cod root not found: {root}")
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def create_armature(model, scale: float):
    if not model.bones:
        return None, []

    arm_data = bpy.data.armatures.new(f"{model.name}_arm")
    arm_obj = bpy.data.objects.new(f"{model.name}_arm_obj", arm_data)
    bpy.context.scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")

    bone_names: List[str] = []
    for bone in model.bones:
        bone_name = bone.name.lower()
        bone_names.append(bone_name)
        eb = arm_data.edit_bones.new(bone_name)
        head = Vector(bone.offset) * scale
        axis = Vector(bone.matrix[1]) * scale
        if axis.length < 1e-4:
            axis = Vector((0.0, 0.05, 0.0))
        eb.head = head
        eb.tail = head + axis
        try:
            eb.align_roll(Vector(bone.matrix[2]))
        except Exception:
            pass

    for idx, bone in enumerate(model.bones):
        if bone.parent == -1:
            continue
        if bone.parent < 0 or bone.parent >= len(bone_names):
            continue
        arm_data.edit_bones[bone_names[idx]].parent = arm_data.edit_bones[bone_names[bone.parent]]

    bpy.ops.object.mode_set(mode="OBJECT")
    return arm_obj, bone_names


def build_materials(model) -> List[bpy.types.Material]:
    mats: List[bpy.types.Material] = []
    for material in model.materials:
        mat_name = material.name.lower()
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            mat = bpy.data.materials.new(name=mat_name)
        mats.append(mat)
    return mats


def valid_faces(sub_mesh) -> Tuple[List[List[int]], List[object]]:
    out_faces: List[List[int]] = []
    src_faces: List[object] = []
    for face in sub_mesh.faces:
        if not face.isValid():
            continue
        indices = [int(corner.vertex) for corner in face.indices]
        if len(indices) != 3:
            continue
        if len(set(indices)) < 3:
            continue
        out_faces.append(indices)
        src_faces.append(face)
    return out_faces, src_faces


def mesh_from_submesh(
    model,
    sub_mesh,
    mesh_name: str,
    materials: List[bpy.types.Material],
    arm_obj: bpy.types.Object | None,
    bone_names: List[str],
    scale: float,
) -> bpy.types.Object | None:
    verts = [(v.offset[0] * scale, v.offset[1] * scale, v.offset[2] * scale) for v in sub_mesh.verts]
    faces, src_faces = valid_faces(sub_mesh)
    if not verts or not faces:
        return None

    mesh = bpy.data.meshes.new(mesh_name)
    mesh.from_pydata(verts, [], faces)
    mesh.update(calc_edges=True)

    for mat in materials:
        mesh.materials.append(mat)

    uv_layer = mesh.uv_layers.new(name="UVMap")
    loop_normals: List[Tuple[float, float, float]] = [(0.0, 0.0, 1.0)] * len(mesh.loops)

    for poly, face in zip(mesh.polygons, src_faces):
        mid = int(face.material_id)
        if 0 <= mid < len(mesh.materials):
            poly.material_index = mid
        for corner_idx, corner in enumerate(face.indices):
            loop_idx = poly.loop_start + corner_idx
            u, v = corner.uv
            uv_layer.data[loop_idx].uv = (float(u), float(1.0 - v))
            nx, ny, nz = corner.normal
            loop_normals[loop_idx] = (float(nx), float(ny), float(nz))

    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    try:
        mesh.normals_split_custom_set(loop_normals)
    except Exception:
        pass

    obj = bpy.data.objects.new(mesh_name, mesh)
    bpy.context.scene.collection.objects.link(obj)

    if arm_obj and bone_names:
        obj.parent = arm_obj
        for bone_name in bone_names:
            obj.vertex_groups.new(name=bone_name)

        for v_idx, vert in enumerate(sub_mesh.verts):
            for bone_idx, weight in vert.weights:
                if weight <= 0:
                    continue
                if bone_idx < 0 or bone_idx >= len(bone_names):
                    continue
                obj.vertex_groups[bone_names[bone_idx]].add([v_idx], float(weight), "ADD")

        mod = obj.modifiers.new("Armature", "ARMATURE")
        mod.object = arm_obj
        mod.use_vertex_groups = True
        mod.use_bone_envelopes = False

    return obj


def export_scene(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ext = output_path.suffix.lower()

    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.type in {"MESH", "ARMATURE"}:
            obj.select_set(True)
    active = next((obj for obj in bpy.context.scene.objects if obj.select_get()), None)
    if active is not None:
        bpy.context.view_layer.objects.active = active

    if ext == ".glb":
        bpy.ops.export_scene.gltf(
            filepath=str(output_path),
            export_format="GLB",
            use_selection=True,
            export_apply=True,
            export_yup=True,
        )
        return
    if ext == ".gltf":
        bpy.ops.export_scene.gltf(
            filepath=str(output_path),
            export_format="GLTF_SEPARATE",
            use_selection=True,
            export_apply=True,
            export_yup=True,
        )
        return
    if ext == ".fbx":
        bpy.ops.export_scene.fbx(filepath=str(output_path), use_selection=True, apply_scale_options="FBX_SCALE_NONE")
        return
    if ext == ".obj":
        if hasattr(bpy.ops.wm, "obj_export"):
            bpy.ops.wm.obj_export(filepath=str(output_path), export_selected_objects=True)
        else:
            bpy.ops.export_scene.obj(filepath=str(output_path), use_selection=True)
        return
    raise ValueError(f"Unsupported export extension: {output_path.suffix}")


def convert_xmodel(input_path: Path, output_path: Path, blender_cod_root: Path, scale: float) -> None:
    ensure_blender_cod_importable(blender_cod_root)
    from io_scene_cod.PyCoD import xmodel as XModel

    clear_scene()
    model = XModel.Model(input_path.stem)
    if input_path.suffix.lower() == ".xmodel_bin":
        model.LoadFile_Bin(str(input_path), split_meshes=False)
    else:
        model.LoadFile_Raw(str(input_path), split_meshes=False)

    arm_obj, bone_names = create_armature(model, scale=scale)
    materials = build_materials(model)

    created = 0
    for sub_idx, sub_mesh in enumerate(model.meshes):
        mesh_name = f"{model.name}_{sub_idx}"
        obj = mesh_from_submesh(
            model=model,
            sub_mesh=sub_mesh,
            mesh_name=mesh_name,
            materials=materials,
            arm_obj=arm_obj,
            bone_names=bone_names,
            scale=scale,
        )
        if obj is not None:
            created += 1

    if created == 0:
        raise RuntimeError(f"No valid mesh could be built from: {input_path}")

    export_scene(output_path)


def convert_xanim(input_path: Path, output_path: Path, blender_cod_root: Path) -> None:
    ensure_blender_cod_importable(blender_cod_root)
    from io_scene_cod.PyCoD import xanim as XAnim

    output_path.parent.mkdir(parents=True, exist_ok=True)
    anim = XAnim.Anim()
    if input_path.suffix.lower() == ".xanim_bin":
        try:
            anim.LoadFile_Bin(str(input_path))
        except Exception:
            # Some dumps may contain entries that are not in the default compressed mode.
            anim.LoadFile_Bin(str(input_path), is_compressed=False)
    else:
        anim.LoadFile_Raw(str(input_path), use_notetrack_file=True)

    if output_path.suffix.lower() == ".xanim_bin":
        anim.WriteFile_Bin(str(output_path), header_message="Generated by blender_cod_bin_worker.py")
    else:
        anim.WriteFile_Raw(str(output_path), header_message="Generated by blender_cod_bin_worker.py", embed_notes=False)


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    blender_cod_root = Path(args.blender_cod_root).resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    if args.asset_kind == "xmodel":
        convert_xmodel(
            input_path=input_path,
            output_path=output_path,
            blender_cod_root=blender_cod_root,
            scale=float(args.scale),
        )
    else:
        convert_xanim(
            input_path=input_path,
            output_path=output_path,
            blender_cod_root=blender_cod_root,
        )

    print(f"converted {args.asset_kind}: {input_path} -> {output_path}")


if __name__ == "__main__":
    main()
