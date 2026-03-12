from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser(description="Build a donor-pose first-person preview scene.")
    parser.add_argument("--custom-glb", required=True)
    parser.add_argument("--donor-glb", required=True)
    parser.add_argument("--viewhands-glb", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--hide-donor", action="store_true")
    return parser.parse_args(argv)


def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def ensure_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def import_glb(filepath: Path, prefix: str, collection_name: str) -> list[bpy.types.Object]:
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.import_scene.gltf(filepath=str(filepath))
    imported = list(bpy.context.selected_objects)
    if not imported:
        raise RuntimeError(f"Import produced no objects: {filepath}")
    collection = ensure_collection(collection_name)
    scene_root = bpy.context.scene.collection
    for obj in imported:
        obj.name = f"{prefix}{obj.name}"
        if obj.data and hasattr(obj.data, "name"):
            obj.data.name = f"{prefix}{obj.data.name}"
        if obj.name not in collection.objects:
            collection.objects.link(obj)
        if obj.name in scene_root.objects:
            scene_root.objects.unlink(obj)
    return imported


def first_armature(objects: list[bpy.types.Object]) -> bpy.types.Object:
    for obj in objects:
        if obj.type == "ARMATURE":
            return obj
    raise RuntimeError("Expected an armature in imported objects")


def set_reference_visibility(objects: list[bpy.types.Object], *, hide: bool) -> None:
    for obj in objects:
        if obj.type != "MESH":
            continue
        obj.hide_set(hide)
        obj.hide_render = hide
        if not hide:
            obj.display_type = "WIRE"
            obj.show_in_front = True


def add_camera() -> bpy.types.Object:
    camera_data = bpy.data.cameras.new("PreviewCamera")
    camera_obj = bpy.data.objects.new("PreviewCamera", camera_data)
    bpy.context.scene.collection.objects.link(camera_obj)
    camera_obj.location = Vector((-2.5, -18.0, 2.0))
    camera_obj.rotation_euler = Euler((1.5359, 0.0, 0.0), "XYZ")
    bpy.context.scene.camera = camera_obj
    return camera_obj


def add_light() -> bpy.types.Object:
    light_data = bpy.data.lights.new(name="PreviewSun", type="SUN")
    light_obj = bpy.data.objects.new(name="PreviewSun", object_data=light_data)
    bpy.context.scene.collection.objects.link(light_obj)
    light_obj.rotation_euler = Euler((0.9, 0.2, -0.6), "XYZ")
    light_data.energy = 2.2
    return light_obj


def configure_scene() -> None:
    scene = bpy.context.scene
    scene.frame_start = 0
    scene.frame_end = 1
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        scene.render.engine = "BLENDER_EEVEE"
    if hasattr(scene, "eevee"):
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = 16
        if hasattr(scene.eevee, "taa_samples"):
            scene.eevee.taa_samples = 16
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_xray = False


def main() -> None:
    args = parse_args()
    clear_scene()
    configure_scene()

    donor_objects = import_glb(Path(args.donor_glb).resolve(), prefix="donor_", collection_name="DonorM14")
    hands_objects = import_glb(Path(args.viewhands_glb).resolve(), prefix="hands_", collection_name="ZombieViewHands")
    custom_objects = import_glb(Path(args.custom_glb).resolve(), prefix="custom_", collection_name="CustomWeapon")

    donor_armature = first_armature(donor_objects)
    hands_armature = first_armature(hands_objects)
    custom_armature = first_armature(custom_objects)

    # Keep every armature/object in the same world frame so the preview matches the engine's donor composition.
    hands_armature.matrix_world = donor_armature.matrix_world.copy()
    custom_armature.matrix_world = donor_armature.matrix_world.copy()

    set_reference_visibility(donor_objects, hide=args.hide_donor)
    add_camera()
    add_light()

    bpy.context.scene.frame_set(0)
    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_path))
    print(f"Saved donor-pose preview blend: {out_path}")


if __name__ == "__main__":
    main()
