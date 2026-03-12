import bpy
import bmesh
from pathlib import Path
from mathutils import Vector


GLB_PATH = Path(r"Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_weapon_only\bo3_rev_idg_weapon_only.glb")
OUT_PATH = Path(r"Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_glow_only.png")
KEEP = {"mtl_wpn_t7_zmb_zod_idg_eyes", "mtl_wpn_t7_zmb_zod_idg_sacks"}


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def isolate_keep_materials():
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        mesh = obj.data
        keep_slots = {idx for idx, slot in enumerate(obj.material_slots) if slot.material and slot.material.name in KEEP}
        bm = bmesh.new()
        bm.from_mesh(mesh)
        faces_to_delete = [f for f in bm.faces if f.material_index not in keep_slots]
        bmesh.ops.delete(bm, geom=faces_to_delete, context="FACES")
        bm.to_mesh(mesh)
        bm.free()


def tint_materials():
    for mat in bpy.data.materials:
        if mat.name not in KEEP:
            continue
        mat.use_nodes = True
        nt = mat.node_tree
        for node in list(nt.nodes):
            nt.nodes.remove(node)
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        em = nt.nodes.new("ShaderNodeEmission")
        if "eyes" in mat.name:
            em.inputs["Color"].default_value = (0.1, 0.5, 1.0, 1.0)
        else:
            em.inputs["Color"].default_value = (1.0, 0.85, 0.1, 1.0)
        em.inputs["Strength"].default_value = 2.0
        nt.links.new(em.outputs["Emission"], out.inputs["Surface"])


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
    cam.location = center + direction * (extent * 2.2)
    to_center = center - cam.location
    cam.rotation_euler = to_center.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 55


def setup_world():
    world = bpy.data.worlds["World"]
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.02, 0.02, 0.02, 1.0)
        bg.inputs["Strength"].default_value = 0.3


def main():
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(GLB_PATH))
    isolate_keep_materials()
    tint_materials()
    setup_camera()
    setup_world()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 900
    scene.render.filepath = str(OUT_PATH)
    bpy.ops.render.render(write_still=True)
    print(str(OUT_PATH))


main()
