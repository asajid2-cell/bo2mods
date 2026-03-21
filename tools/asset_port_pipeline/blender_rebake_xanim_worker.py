from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser(description="Rebake a BO3 xanim_export onto a reduced armature and export a normalized xanim_export.")
    parser.add_argument("--input-glb", required=True)
    parser.add_argument("--input-anim", required=True)
    parser.add_argument("--output-anim", required=True)
    parser.add_argument("--blender-cod-root", required=True)
    return parser.parse_args(argv)


def patch_import_xanim_for_blender5(import_xanim_module) -> None:
    def inherits_rotation(bone) -> bool:
        return bool(getattr(bone, "use_inherit_rotation", True))

    def inherits_scale(bone) -> bool:
        if hasattr(bone, "use_inherit_scale"):
            return bool(getattr(bone, "use_inherit_scale"))
        inherit_scale = str(getattr(bone, "inherit_scale", "FULL")).upper()
        return inherit_scale not in {"NONE", "NONE_LEGACY"}

    def get_mat_offs(bone):
        mat_offs = bone.matrix.to_4x4()
        mat_offs.translation = bone.head
        if bone.parent:
            mat_offs.translation.y += bone.parent.length
        return mat_offs

    def get_mat_rest(pose_bone, mat_pose_parent, mat_local_parent):
        bone = pose_bone.bone
        if pose_bone.parent:
            mat_offs = get_mat_offs(bone)
            use_inherit_rotation = inherits_rotation(bone)
            use_inherit_scale = inherits_scale(bone)

            if not use_inherit_rotation and not use_inherit_scale:
                mat_rotscale = mat_local_parent @ mat_offs
            elif not use_inherit_rotation:
                mat_size = Matrix.Identity(4)
                for idx in range(3):
                    mat_size[idx][idx] = mat_pose_parent.col[idx].magnitude
                mat_rotscale = mat_size @ mat_local_parent @ mat_offs
            elif not use_inherit_scale:
                mat_rotscale = mat_pose_parent.normalized() @ mat_offs
            else:
                mat_rotscale = mat_pose_parent @ mat_offs

            if not bone.use_local_location:
                mat_a = Matrix.Translation(mat_pose_parent @ mat_offs.translation)
                mat_b = mat_pose_parent.copy()
                mat_b.translation = Vector()
                mat_loc = mat_a @ mat_b
            elif not use_inherit_rotation or not use_inherit_scale:
                mat_loc = mat_pose_parent @ mat_offs
            else:
                mat_loc = mat_rotscale.copy()
        else:
            mat_rotscale = bone.matrix_local
            if not bone.use_local_location:
                mat_loc = Matrix.Translation(bone.matrix_local.translation)
            else:
                mat_loc = mat_rotscale.copy()
        return mat_rotscale, mat_loc

    def calc_basis(pose_bone, matrix, parent_mtx, parent_mtx_local):
        mat_rotscale, mat_loc = get_mat_rest(pose_bone, parent_mtx, parent_mtx_local)
        basis = (matrix.to_3x3().inverted() @ mat_rotscale.to_3x3()).transposed()
        basis.resize_4x4()
        basis.translation = mat_loc.inverted() @ matrix.translation
        return basis

    import_xanim_module.get_mat_offs = get_mat_offs
    import_xanim_module.get_mat_rest = get_mat_rest
    import_xanim_module.calc_basis = calc_basis


def patch_export_xanim_for_blender5(export_xanim_module) -> None:
    def calc_frame_range(action):
        if hasattr(action, "fcurves"):
            fcurves = getattr(action, "fcurves")
            if len(fcurves) == 0:
                return (0, 0)
            keys = [fcurve.keyframe_points for fcurve in fcurves]
            points = [point for keyframe_points in keys for point in keyframe_points]
            frames = [point.co[0] for point in points]
            return (min(frames), max(frames))

        frame_range = getattr(action, "frame_range", None)
        if frame_range and len(frame_range) >= 2:
            return (frame_range[0], frame_range[1])
        return (0, 0)

    export_xanim_module.calc_frame_range = calc_frame_range


def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def action_frame_range(action) -> tuple[int, int]:
    frame_range = getattr(action, "frame_range", None)
    if frame_range and len(frame_range) >= 2:
        start = int(round(frame_range[0]))
        end = int(round(frame_range[1]))
        return start, end
    return 0, 0


def dump_local_basis_animation(armature, action, output_anim: Path) -> None:
    start_frame, end_frame = action_frame_range(action)
    part_names = [bone.name for bone in armature.pose.bones]
    name_to_idx = {name: idx for idx, name in enumerate(part_names)}
    frames: dict[str, dict[str, object]] = {}

    for frame_number in range(start_frame, end_frame + 1):
        bpy.context.scene.frame_set(frame_number)
        bpy.context.view_layer.update()
        frame_parts: dict[str, object] = {}
        for pose_bone in armature.pose.bones:
            idx = name_to_idx.get(pose_bone.name)
            if idx is None:
                continue
            loc, rot, _scale = pose_bone.matrix_basis.decompose()
            rot = rot.normalized()
            frame_parts[str(idx)] = {
                "offset": [float(loc.x), float(loc.y), float(loc.z)],
                "quat": [float(rot.x), float(rot.y), float(rot.z), float(rot.w)],
            }
        frames[str(frame_number)] = frame_parts

    basis_payload = {
        "format": "local_basis_v1",
        "action": action.name,
        "part_names": part_names,
        "frame_range": [start_frame, end_frame],
        "frames": frames,
    }
    sidecar_path = output_anim.with_suffix(".basis.json")
    sidecar_path.write_text(json.dumps(basis_payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote local-basis sidecar: {sidecar_path}")


def main() -> None:
    args = parse_args()
    blender_cod_root = Path(args.blender_cod_root).resolve()
    if str(blender_cod_root) not in sys.path:
        sys.path.insert(0, str(blender_cod_root))

    from io_scene_cod import export_xanim, import_xanim  # type: ignore

    patch_import_xanim_for_blender5(import_xanim)
    patch_export_xanim_for_blender5(export_xanim)
    if not hasattr(bpy.types.Scene, "update"):
        bpy.types.Scene.update = lambda self: bpy.context.view_layer.update()

    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(Path(args.input_glb).resolve()))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"Expected exactly one armature in reduced GLB, found {len(armatures)}")
    armature = armatures[0]
    if armature.animation_data is None:
        armature.animation_data_create()

    existing_actions = {action.name for action in bpy.data.actions}
    anim_file = Path(args.input_anim).resolve()
    stem = anim_file.stem

    result = import_xanim.load_anim(
        None,
        bpy.context,
        armature=armature,
        filepath=str(anim_file),
        global_scale=1.0,
        use_actions=True,
        use_actions_skip_existing=False,
        use_notetracks=False,
        use_notetrack_file=False,
        fps_scale_type="DISABLED",
        fps_scale_target_fps=30,
        update_scene_fps=False,
        anim_offset=0,
    )
    if isinstance(result, str):
        raise RuntimeError(result)

    imported_actions = [action for action in bpy.data.actions if action.name not in existing_actions]
    target_action = None
    for action in imported_actions:
        if action.name.startswith(stem):
            target_action = action
            break
    if target_action is None:
        for action in bpy.data.actions:
            if action.name.startswith(stem):
                target_action = action
                break
    if target_action is None:
        raise RuntimeError(f"Unable to locate imported action for {stem}")

    armature.animation_data.action = target_action
    bpy.context.view_layer.objects.active = armature

    output_anim = Path(args.output_anim).resolve()
    output_anim.parent.mkdir(parents=True, exist_ok=True)
    save_result = export_xanim.save(
        None,
        bpy.context,
        filepath=str(output_anim),
        target_format="XANIM_EXPORT",
        use_selection=False,
        global_scale=1.0,
        apply_unit_scale=False,
        use_all_actions=False,
        use_notetracks=False,
        use_notetrack_mode="ACTION",
        use_notetrack_file=False,
        use_frame_range_mode="ACTION",
        use_custom_framerate=True,
        use_framerate=30,
    )
    if isinstance(save_result, str) and save_result:
        raise RuntimeError(save_result)

    dump_local_basis_animation(armature, target_action, output_anim)
    print(f"Rebaked xanim_export: {output_anim}")


if __name__ == "__main__":
    main()
