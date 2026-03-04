"""
Rebuild thundergun_view GLB with MINIMAL skeleton.

T6 has a 160 bone limit. The viewhands model provides arm/hand bones.
The gun model only needs:
  - tag_torso (skeleton root for positioning)
  - tag_weapon_left, tag_weapon_right (attachment points)
  - tag_weapon (sub-attachment)
  - All weapon-specific bones (original 25 from pipeline)
  - tag_cambone chain (camera bones)
"""
import json
import struct
import shutil
from pathlib import Path

ROOT = Path(r"z:\Games\pluto_t6_full_game")
GLB_PATH = ROOT / "_build/panzer_work/so_zsurvival_zm_transit/model_export/thundergun_view_lod0.glb"
GLB_BACKUP = GLB_PATH.with_suffix(".glb.bak")

# Only these bones are needed in the gun model.
# Arm/hand/finger/sleeve bones come from the viewhands model.
NEEDED_BONES = {
    # Skeleton root
    "tag_torso": None,
    # Weapon attachment points
    "tag_weapon_left": "tag_torso",
    "tag_weapon_right": "tag_torso",
    "tag_weapon": "tag_weapon_right",
    # Camera chain
    "tag_cambone": "tag_torso",
    "tag_camera": "tag_cambone",
    "tag_fill_light": "tag_cambone",
    "tag_flashlight": "tag_cambone",
    "tag_gasmask": "tag_cambone",
    # Weapon-specific bones (all children of tag_weapon_right, already in GLB)
    "tag_brass": "tag_weapon_right",
    "tag_dial_animate": "tag_weapon_right",
    "tag_flash": "tag_weapon_right",
    "tag_pump_animate": "tag_weapon_right",
    "tag_steam1": "tag_weapon_right",
    "tag_steam2": "tag_weapon_right",
    "tag_steam3": "tag_weapon_right",
    "tag_switch1_animate": "tag_weapon_right",
    "tag_switch2_animate": "tag_weapon_right",
    "tag_switch3_animate": "tag_weapon_right",
    "tag_ammo_arm_left1_animate": "tag_pump_animate",
    "tag_ammo_arm_left2_animate": "tag_ammo_arm_left1_animate",
    "tag_ammo_arm_mid1_animate": "tag_pump_animate",
    "tag_ammo_arm_mid2_animate": "tag_ammo_arm_mid1_animate",
    "tag_ammo_arm_right1_animate": "tag_pump_animate",
    "tag_ammo_arm_right2_animate": "tag_ammo_arm_right1_animate",
    "tag_ammo_drum_01": "tag_pump_animate",
    "tag_ammo_drum_02": "tag_pump_animate",
    "tag_bracket_1_animate": "tag_pump_animate",
    "tag_bracket_2_animate": "tag_bracket_1_animate",
    "tag_bulb1": "tag_ammo_drum_01",
    "tag_bulb2": "tag_ammo_drum_01",
    "tag_bulb3": "tag_ammo_drum_01",
    "tag_bulb4": "tag_ammo_drum_01",
}
# Total: ~34 bones (well under 160 even with viewhands)


def read_glb(path):
    with open(path, "rb") as f:
        magic = f.read(4)
        assert magic == b"glTF"
        version = struct.unpack("<I", f.read(4))[0]
        total_len = struct.unpack("<I", f.read(4))[0]
        json_len = struct.unpack("<I", f.read(4))[0]
        json_type = f.read(4)
        json_bytes = f.read(json_len)
        bin_data = b""
        if f.tell() < total_len:
            bin_len = struct.unpack("<I", f.read(4))[0]
            bin_type = f.read(4)
            bin_data = f.read(bin_len)
    return json.loads(json_bytes.decode("utf-8")), bin_data


def write_glb(path, gltf, bin_data):
    json_str = json.dumps(gltf, separators=(",", ":"))
    while len(json_str) % 4 != 0:
        json_str += " "
    json_bytes = json_str.encode("utf-8")
    while len(bin_data) % 4 != 0:
        bin_data += b"\x00"
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_data)
    with open(path, "wb") as f:
        f.write(b"glTF")
        f.write(struct.pack("<I", 2))
        f.write(struct.pack("<I", total))
        f.write(struct.pack("<I", len(json_bytes)))
        f.write(b"JSON")
        f.write(json_bytes)
        f.write(struct.pack("<I", len(bin_data)))
        f.write(b"BIN\x00")
        f.write(bin_data)


def identity_mat4():
    return [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]


def main():
    print("=== Rebuilding thundergun_view GLB (SLIM skeleton) ===\n")

    # Restore from backup (undo previous 133-bone rebuild)
    if GLB_BACKUP.exists():
        shutil.copy2(str(GLB_BACKUP), str(GLB_PATH))
        print("Restored original GLB from backup")
    else:
        print("ERROR: No backup found!")
        return

    gltf, bin_data = read_glb(GLB_PATH)
    nodes = gltf["nodes"]
    skin = gltf["skins"][0]
    accessors = gltf["accessors"]
    buffer_views = gltf["bufferViews"]
    buffers = gltf["buffers"]

    # Map existing node names
    name_to_idx = {}
    for i, n in enumerate(nodes):
        name = n.get("name", "")
        if name:
            name_to_idx[name] = i

    existing_joint_names = set()
    for ji in skin["joints"]:
        existing_joint_names.add(nodes[ji].get("name", ""))

    print(f"Original: {len(nodes)} nodes, {len(skin['joints'])} joints")
    print(f"Target: {len(NEEDED_BONES)} bones")

    # Find which bones to add (not already in GLB)
    bones_to_add = []
    for bone_name in NEEDED_BONES:
        if bone_name not in existing_joint_names:
            bones_to_add.append(bone_name)

    print(f"Bones to add: {len(bones_to_add)} -> {bones_to_add}")

    # Create new nodes for missing bones
    for bone_name in bones_to_add:
        new_idx = len(nodes)
        nodes.append({"name": bone_name})
        name_to_idx[bone_name] = new_idx

    print(f"Total nodes: {len(nodes)}")

    # Collect all bone node indices
    all_bone_indices = set(skin["joints"])
    for bone_name in bones_to_add:
        all_bone_indices.add(name_to_idx[bone_name])

    # Build desired children map from NEEDED_BONES
    desired_children = {}
    for bone_name, parent_name in NEEDED_BONES.items():
        if parent_name is None or bone_name not in name_to_idx:
            continue
        if parent_name not in name_to_idx:
            print(f"  WARNING: parent '{parent_name}' not found for '{bone_name}'")
            continue
        parent_idx = name_to_idx[parent_name]
        bone_idx = name_to_idx[bone_name]
        if parent_idx not in desired_children:
            desired_children[parent_idx] = []
        desired_children[parent_idx].append(bone_idx)

    # Clear bone children from existing nodes
    for idx in all_bone_indices:
        if "children" in nodes[idx]:
            old = nodes[idx]["children"]
            non_bone = [c for c in old if c not in all_bone_indices]
            if non_bone:
                nodes[idx]["children"] = non_bone
            else:
                del nodes[idx]["children"]

    # Apply desired hierarchy
    for parent_idx, children in desired_children.items():
        if "children" not in nodes[parent_idx]:
            nodes[parent_idx]["children"] = []
        nodes[parent_idx]["children"].extend(children)

    # Update root node (40): replace tag_weapon_right with tag_torso
    root_idx = 40
    tag_torso_idx = name_to_idx["tag_torso"]
    tag_weapon_right_idx = name_to_idx["tag_weapon_right"]
    root_children = nodes[root_idx].get("children", [])
    if tag_weapon_right_idx in root_children:
        root_children.remove(tag_weapon_right_idx)
    if tag_torso_idx not in root_children:
        root_children.append(tag_torso_idx)
    nodes[root_idx]["children"] = root_children

    # Add new bones to skin joints (append)
    for bone_name in bones_to_add:
        skin["joints"].append(name_to_idx[bone_name])

    skin["skeleton"] = tag_torso_idx

    print(f"Final skin joints: {len(skin['joints'])}")

    # Extend IBM accessor
    ibm_acc_idx = skin["inverseBindMatrices"]
    ibm_acc = accessors[ibm_acc_idx]
    ibm_bv_idx = ibm_acc["bufferView"]
    ibm_bv = buffer_views[ibm_bv_idx]

    old_count = ibm_acc["count"]
    new_count = len(skin["joints"])
    num_new = new_count - old_count

    # Read existing IBMs
    existing_ibm = bin_data[ibm_bv["byteOffset"]:ibm_bv["byteOffset"] + ibm_bv["byteLength"]]

    # Create identity IBMs for new bones
    new_ibm_bytes = b""
    for _ in range(num_new):
        for val in identity_mat4():
            new_ibm_bytes += struct.pack("<f", val)

    # Append combined IBM data to binary buffer
    combined_ibm = existing_ibm + new_ibm_bytes
    new_bv_idx = len(buffer_views)
    buffer_views.append({
        "buffer": 0,
        "byteOffset": len(bin_data),
        "byteLength": len(combined_ibm),
    })
    ibm_acc["bufferView"] = new_bv_idx
    ibm_acc["count"] = new_count
    bin_data = bin_data + combined_ibm
    buffers[0]["byteLength"] = len(bin_data)

    # Verify
    print(f"\n=== Final hierarchy ===")
    def show(idx, depth=0):
        name = nodes[idx].get("name", f"node_{idx}")
        children = [c for c in nodes[idx].get("children", []) if c in all_bone_indices]
        print(f"  {'  '*depth}{name} ({len(children)} children)")
        for c in children:
            show(c, depth+1)
    show(tag_torso_idx)

    # Joint names for reference
    print(f"\nAll {len(skin['joints'])} joint names:")
    for i, ji in enumerate(skin["joints"]):
        print(f"  [{i}] {nodes[ji].get('name','?')}")

    write_glb(GLB_PATH, gltf, bin_data)
    print(f"\nWrote: {GLB_PATH.stat().st_size} bytes ({len(skin['joints'])} joints)")
    print("Done!")


if __name__ == "__main__":
    main()
