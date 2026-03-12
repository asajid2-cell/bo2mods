import bpy
import math
from pathlib import Path
from mathutils import Vector


GLB_PATH = Path(r"Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_weapon_only\bo3_rev_idg_weapon_only.glb")
OUT_PATH = Path(r"Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_material_regions.png")


COLORS = {
    "mtl_wpn_t7_zmb_zod_idg_bone": (0.35, 0.12, 0.12, 1.0),
    "mtl_wpn_t7_zmb_zod_idg_body": (0.08, 0.18, 0.08, 0.18),
    "mtl_wpn_t7_zmb_zod_idg_eyes": (0.05, 0.45, 1.0, 1.0),
    "mtl_wpn_t7_zmb_zod_idg_sacks": (1.0, 0.85, 0.05, 1.0),
    "mtl_wpn_t7_zmb_zod_idg_tentacles": (0.45, 0.08, 0.65, 0.65),
}


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in list(bpy.data.meshes):
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in list(bpy.data.materials):
        if block.users == 0:
            bpy.data.materials.remove(block)


def make_flat_material(name: str, rgba):
    mat = bpy.data.materials.new(name=f"dbg_{name}")
    mat.use_nodes = True
    mat.blend_method = "BLEND" if rgba[3] < 1.0 else "OPAQUE"
    nt = mat.node_tree
    for node in list(nt.nodes):
        nt.nodes.remove(node)
    output = nt.nodes.new("ShaderNodeOutputMaterial")
    emission = nt.nodes.new("ShaderNodeEmission")
    transparent = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    emission.inputs["Color"].default_value = rgba
    emission.inputs["Strength"].default_value = 1.0
    mix.inputs["Fac"].default_value = 1.0 - rgba[3]
    nt.links.new(transparent.outputs["BSDF"], mix.inputs[1])
    nt.links.new(emission.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], output.inputs["Surface"])
    return mat


def assign_debug_materials():
    debug_mats = {name: make_flat_material(name, rgba) for name, rgba in COLORS.items()}
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        for slot in obj.material_slots:
            src = slot.material.name if slot.material else ""
            if src in debug_mats:
                slot.material = debug_mats[src]


def scene_bounds():
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    found = False
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            mins.x = min(mins.x, world.x)
            mins.y = min(mins.y, world.y)
            mins.z = min(mins.z, world.z)
            maxs.x = max(maxs.x, world.x)
            maxs.y = max(maxs.y, world.y)
            maxs.z = max(maxs.z, world.z)
            found = True
    if not found:
        return Vector((0.0, 0.0, 0.0)), 1.0
    center = (mins + maxs) * 0.5
    extent = max(maxs.x - mins.x, maxs.y - mins.y, maxs.z - mins.z)
    return center, max(extent, 1.0)


def setup_camera():
    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    center, extent = scene_bounds()
    direction = Vector((0.35, -1.0, 0.28)).normalized()
    cam.location = center + direction * (extent * 1.9)
    to_center = center - cam.location
    cam.rotation_euler = to_center.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 42
    return cam


def setup_light():
    light_data = bpy.data.lights.new(name="Sun", type="SUN")
    light = bpy.data.objects.new(name="Sun", object_data=light_data)
    bpy.context.collection.objects.link(light)
    light.rotation_euler = (math.radians(45.0), 0.0, math.radians(-35.0))
    light.data.energy = 2.5
    world = bpy.data.worlds["World"]
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.04, 0.04, 0.04, 1.0)
        bg.inputs["Strength"].default_value = 0.7


def main():
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(GLB_PATH))
    assign_debug_materials()
    setup_camera()
    setup_light()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 900
    scene.render.filepath = str(OUT_PATH)
    bpy.ops.render.render(write_still=True)
    print(str(OUT_PATH))


main()
