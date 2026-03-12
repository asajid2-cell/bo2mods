from __future__ import annotations

import argparse
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
    parser = argparse.ArgumentParser(description="Preview BO3 IDG animations on a reduced combined rig.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--blender-cod-root", required=True)
    parser.add_argument("--anim-dir", required=True)
    parser.add_argument("--anim-stems", default="vm_zod_id_gun_idle,vm_zod_id_gun_pullout,vm_zod_id_gun_fire")
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


def main() -> None:
    args = parse_args()
    blender_cod_root = Path(args.blender_cod_root).resolve()
    if str(blender_cod_root) not in sys.path:
        sys.path.insert(0, str(blender_cod_root))

    from io_scene_cod import import_xanim  # type: ignore

    patch_import_xanim_for_blender5(import_xanim)
    if not hasattr(bpy.types.Scene, "update"):
        bpy.types.Scene.update = lambda self: bpy.context.view_layer.update()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(Path(args.input).resolve()))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"Expected exactly one armature in reduced GLB, found {len(armatures)}")
    armature = armatures[0]
    if armature.animation_data is None:
        armature.animation_data_create()

    scene = bpy.context.scene
    scene.frame_start = 0
    scene.frame_end = 60
    max_frame = 0
    stems = [stem.strip() for stem in args.anim_stems.split(",") if stem.strip()]
    anim_dir = Path(args.anim_dir).resolve()

    for stem in stems:
        anim_file = anim_dir / f"{stem}.xanim_export"
        if not anim_file.exists():
            raise FileNotFoundError(f"Missing anim export for preview: {anim_file}")
        anim = import_xanim.load_anim(
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
        if isinstance(anim, str):
            raise RuntimeError(anim)
        frames = [frame.frame for frame in getattr(anim, "frames", [])]
        if frames:
            max_frame = max(max_frame, max(frames))

    first_prefix = stems[0]
    for action in bpy.data.actions:
        if action.name.startswith(first_prefix):
            armature.animation_data.action = action
            break
    scene.frame_end = max(scene.frame_end, int(max_frame) if max_frame else 60)
    scene.frame_set(scene.frame_start)
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.output).resolve()))
    print(f"Saved reduced-rig preview blend: {args.output}")


if __name__ == "__main__":
    main()
