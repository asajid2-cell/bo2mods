"""
Rebuild thundergun_view GLB with full 133-bone skeleton from xanim_export.

The E2E pipeline exported only weapon bones (25 joints). The animations target
133 bones (arms + hands + weapon + camera). We need to add the missing 108 bones
so the engine can properly position and animate the viewmodel.
"""
import json
import struct
import copy
import glob
from pathlib import Path

ROOT = Path(r"z:\Games\pluto_t6_full_game")
GLB_PATH = ROOT / "_build/panzer_work/so_zsurvival_zm_transit/model_export/thundergun_view_lod0.glb"
GLB_BACKUP = GLB_PATH.with_suffix(".glb.bak")
XANIM_PATH = ROOT / "_build/panzer_work/so_zsurvival_zm_transit/xanim_export/viewmodel/vm_thunder_gun_idle.xanim_export"
XANIM_DIR = ROOT / "_build/panzer_work/so_zsurvival_zm_transit/xanim_export"
XANIM_PATTERN = "vm_thunder_gun_*.xanim_export"

# ============================================================
# Define the FULL bone hierarchy (parent -> children mapping)
# Based on standard CoD viewmodel skeleton conventions
# ============================================================
BONE_PARENT = {
    # Root
    "tag_torso": None,

    # Left arm chain
    "j_shoulder_le": "tag_torso",
    "j_elbow_le": "j_shoulder_le",
    "j_elbow_bulge_le": "j_elbow_le",
    "j_sleeve1_01_le": "j_elbow_le",
    "j_sleeve1_02_le": "j_elbow_le",
    "j_sleeve1_03_le": "j_elbow_le",
    "j_sleeve1_04_le": "j_elbow_le",
    "j_sleeve1_05_le": "j_elbow_le",
    "j_sleeve1_06_le": "j_elbow_le",
    "j_sleeve2_01_le": "j_elbow_le",
    "j_sleeve2_02_le": "j_elbow_le",
    "j_sleeve2_03_le": "j_elbow_le",
    "j_sleeve2_04_le": "j_elbow_le",
    "j_sleeve2_05_le": "j_elbow_le",
    "j_sleeve2_06_le": "j_elbow_le",
    "j_sleeve3_01_le": "j_elbow_le",
    "j_sleeve3_02_le": "j_elbow_le",
    "j_sleeve3_03_le": "j_elbow_le",
    "j_sleeve3_04_le": "j_elbow_le",
    "j_sleeve3_05_le": "j_elbow_le",
    "j_sleeve3_06_le": "j_elbow_le",
    "j_wrist_le": "j_elbow_le",
    "j_wristtwist1_le": "j_wrist_le",
    "j_wristtwist2_le": "j_wrist_le",
    "j_wristtwist3_le": "j_wrist_le",
    "j_wristtwist4_le": "j_wrist_le",
    "j_wristtwist5_le": "j_wrist_le",
    "j_wristtwist6_le": "j_wrist_le",
    "j_wristtwist_le": "j_wrist_le",
    "j_wristcrease_le": "j_wrist_le",
    "j_wristcrease2_le": "j_wrist_le",

    # Left hand fingers
    "j_indexbase_le": "j_wrist_le",
    "j_indexretract_le": "j_indexbase_le",
    "j_index_le_1": "j_indexbase_le",
    "j_index_le_2": "j_index_le_1",
    "j_index_le_3": "j_index_le_2",
    "j_mid_le_1": "j_wrist_le",
    "j_mid_le_2": "j_mid_le_1",
    "j_mid_le_3": "j_mid_le_2",
    "j_ringbase_le": "j_wrist_le",
    "j_ring_le_1": "j_ringbase_le",
    "j_ring_le_2": "j_ring_le_1",
    "j_ring_le_3": "j_ring_le_2",
    "j_pinkybase_le": "j_wrist_le",
    "j_pinky_le_1": "j_pinkybase_le",
    "j_pinky_le_2": "j_pinky_le_1",
    "j_pinky_le_3": "j_pinky_le_2",
    "j_thumb_le_1": "j_wrist_le",
    "j_thumb_le_2": "j_thumb_le_1",
    "j_thumb_le_3": "j_thumb_le_2",

    # Right arm chain
    "j_shoulder_ri": "tag_torso",
    "j_elbow_ri": "j_shoulder_ri",
    "j_elbow_bulge_ri": "j_elbow_ri",
    "j_sleeve1_01_ri": "j_elbow_ri",
    "j_sleeve1_02_ri": "j_elbow_ri",
    "j_sleeve1_03_ri": "j_elbow_ri",
    "j_sleeve1_04_ri": "j_elbow_ri",
    "j_sleeve1_05_ri": "j_elbow_ri",
    "j_sleeve1_06_ri": "j_elbow_ri",
    "j_sleeve2_01_ri": "j_elbow_ri",
    "j_sleeve2_02_ri": "j_elbow_ri",
    "j_sleeve2_03_ri": "j_elbow_ri",
    "j_sleeve2_04_ri": "j_elbow_ri",
    "j_sleeve2_05_ri": "j_elbow_ri",
    "j_sleeve2_06_ri": "j_elbow_ri",
    "j_sleeve3_01_ri": "j_elbow_ri",
    "j_sleeve3_02_ri": "j_elbow_ri",
    "j_sleeve3_03_ri": "j_elbow_ri",
    "j_sleeve3_04_ri": "j_elbow_ri",
    "j_sleeve3_05_ri": "j_elbow_ri",
    "j_sleeve3_06_ri": "j_elbow_ri",
    "j_wrist_ri": "j_elbow_ri",
    "j_wristtwist1_ri": "j_wrist_ri",
    "j_wristtwist2_ri": "j_wrist_ri",
    "j_wristtwist3_ri": "j_wrist_ri",
    "j_wristtwist4_ri": "j_wrist_ri",
    "j_wristtwist5_ri": "j_wrist_ri",
    "j_wristtwist6_ri": "j_wrist_ri",
    "j_wristtwist_ri": "j_wrist_ri",
    "j_wristcrease_ri": "j_wrist_ri",
    "j_wristcrease2_ri": "j_wrist_ri",

    # Right hand fingers
    "j_indexbase_ri": "j_wrist_ri",
    "j_indexretract_ri": "j_indexbase_ri",
    "j_index_ri_1": "j_indexbase_ri",
    "j_index_ri_2": "j_index_ri_1",
    "j_index_ri_3": "j_index_ri_2",
    "j_mid_ri_1": "j_wrist_ri",
    "j_mid_ri_2": "j_mid_ri_1",
    "j_mid_ri_3": "j_mid_ri_2",
    "j_ringbase_ri": "j_wrist_ri",
    "j_ring_ri_1": "j_ringbase_ri",
    "j_ring_ri_2": "j_ring_ri_1",
    "j_ring_ri_3": "j_ring_ri_2",
    "j_pinkybase_ri": "j_wrist_ri",
    "j_pinky_ri_1": "j_pinkybase_ri",
    "j_pinky_ri_2": "j_pinky_ri_1",
    "j_pinky_ri_3": "j_pinky_ri_2",
    "j_thumb_ri_1": "j_wrist_ri",
    "j_thumb_ri_2": "j_thumb_ri_1",
    "j_thumb_ri_3": "j_thumb_ri_2",

    # Weapon attachment points
    "tag_weapon_left": "tag_torso",
    "tag_weapon_right": "tag_torso",
    "tag_weapon": "tag_weapon_right",

    # Weapon-specific bones (already in GLB, children of tag_weapon_right)
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

    # Camera bones
    "tag_cambone": "tag_torso",
    "tag_camera": "tag_cambone",
    "tag_view": "tag_cambone",
    "tag_fill_light": "tag_cambone",
    "tag_flashlight": "tag_cambone",
    "tag_gasmask": "tag_cambone",
}


def read_glb(path):
    """Read a GLB file and return (gltf_json, binary_data)."""
    with open(path, "rb") as f:
        magic = f.read(4)
        assert magic == b"glTF", f"Not a GLB file: {magic}"
        version = struct.unpack("<I", f.read(4))[0]
        total_len = struct.unpack("<I", f.read(4))[0]

        # JSON chunk
        json_len = struct.unpack("<I", f.read(4))[0]
        json_type = f.read(4)
        assert json_type == b"JSON"
        json_bytes = f.read(json_len)

        # Binary chunk
        bin_data = b""
        if f.tell() < total_len:
            bin_len = struct.unpack("<I", f.read(4))[0]
            bin_type = f.read(4)
            assert bin_type == b"BIN\x00"
            bin_data = f.read(bin_len)

    gltf = json.loads(json_bytes.decode("utf-8"))
    return gltf, bin_data


def write_glb(path, gltf, bin_data):
    """Write a GLB file from gltf JSON + binary data."""
    json_str = json.dumps(gltf, separators=(",", ":"))
    # Pad JSON to 4-byte alignment
    while len(json_str) % 4 != 0:
        json_str += " "
    json_bytes = json_str.encode("utf-8")

    # Pad binary to 4-byte alignment
    while len(bin_data) % 4 != 0:
        bin_data += b"\x00"

    total = 12 + 8 + len(json_bytes) + 8 + len(bin_data)

    with open(path, "wb") as f:
        # Header
        f.write(b"glTF")
        f.write(struct.pack("<I", 2))
        f.write(struct.pack("<I", total))
        # JSON chunk
        f.write(struct.pack("<I", len(json_bytes)))
        f.write(b"JSON")
        f.write(json_bytes)
        # Binary chunk
        f.write(struct.pack("<I", len(bin_data)))
        f.write(b"BIN\x00")
        f.write(bin_data)


def get_anim_bones(xanim_path):
    """Parse one xanim_export file and return ordered PART bone names."""
    bones = []
    with open(xanim_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line.startswith("PART ") and '"' in line:
                name = line.split('"')[1]
                bones.append(name)
            if line.startswith("FRAMERATE"):
                break
    return bones


def get_anim_bones_union(xanim_dir, pattern):
    """Union PART names across all matching vm_thunder_gun_*.xanim_export files."""
    files = sorted(glob.glob(str(Path(xanim_dir) / pattern)))
    if not files:
        # Legacy fallback to original single-file behavior.
        return get_anim_bones(XANIM_PATH)
    seen = set()
    ordered = []
    for fp in files:
        for b in get_anim_bones(fp):
            if b not in seen:
                seen.add(b)
                ordered.append(b)
    return ordered


def identity_mat4():
    """Return a 4x4 identity matrix as 16 floats."""
    return [
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        0, 0, 0, 1,
    ]


def main():
    print("=== Rebuilding thundergun_view GLB with full skeleton ===\n")

    # Backup original
    import shutil
    if not GLB_BACKUP.exists():
        shutil.copy2(str(GLB_PATH), str(GLB_BACKUP))
        print(f"Backed up original to {GLB_BACKUP.name}")

    # Read GLB
    gltf, bin_data = read_glb(GLB_PATH)
    nodes = gltf["nodes"]
    skin = gltf["skins"][0]
    accessors = gltf["accessors"]
    buffer_views = gltf["bufferViews"]
    buffers = gltf["buffers"]

    # Get animation bone list
    anim_bones = get_anim_bones_union(XANIM_DIR, XANIM_PATTERN)
    print(f"Animation bones: {len(anim_bones)}")

    # Map existing node names to indices
    existing_name_to_node = {}
    for i, n in enumerate(nodes):
        name = n.get("name", "")
        if name:
            existing_name_to_node[name] = i

    # Map existing skin joint names
    existing_joint_names = set()
    for ji in skin["joints"]:
        existing_joint_names.add(nodes[ji].get("name", ""))

    print(f"Existing nodes: {len(nodes)}")
    print(f"Existing skin joints: {len(skin['joints'])} -> {sorted(existing_joint_names)[:5]}...")

    # Determine which bones need to be added
    bones_to_add = []
    for bone_name in anim_bones:
        if bone_name not in existing_joint_names:
            bones_to_add.append(bone_name)

    print(f"Bones to add: {len(bones_to_add)}")

    # Create new nodes for missing bones
    new_node_map = {}  # bone_name -> new_node_index
    for bone_name in bones_to_add:
        new_idx = len(nodes)
        new_node = {"name": bone_name}
        nodes.append(new_node)
        new_node_map[bone_name] = new_idx
        existing_name_to_node[bone_name] = new_idx

    print(f"Total nodes after adding: {len(nodes)}")

    # Build complete name->node_index map
    name_to_idx = {}
    for i, n in enumerate(nodes):
        name = n.get("name", "")
        if name:
            name_to_idx[name] = i

    # Now restructure the hierarchy based on BONE_PARENT
    # First, clear all children from nodes that we'll reparent
    # We need to be careful: only reparent bones, not mesh nodes

    # Collect all bone node indices (existing joints + new bones)
    all_bone_indices = set(skin["joints"])
    for bone_name in bones_to_add:
        all_bone_indices.add(name_to_idx[bone_name])

    # Build the desired children map from BONE_PARENT
    desired_children = {}  # node_idx -> [child_node_idx, ...]
    for bone_name, parent_name in BONE_PARENT.items():
        if bone_name not in name_to_idx:
            continue
        bone_idx = name_to_idx[bone_name]
        if parent_name is None:
            continue  # root bone
        if parent_name not in name_to_idx:
            print(f"  WARNING: parent '{parent_name}' for '{bone_name}' not found!")
            continue
        parent_idx = name_to_idx[parent_name]
        if parent_idx not in desired_children:
            desired_children[parent_idx] = []
        desired_children[parent_idx].append(bone_idx)

    # Clear existing children for all bone nodes
    for idx in all_bone_indices:
        if "children" in nodes[idx]:
            # Remove only bone children, keep non-bone children
            old_children = nodes[idx]["children"]
            non_bone_children = [c for c in old_children if c not in all_bone_indices]
            if non_bone_children:
                nodes[idx]["children"] = non_bone_children
            else:
                del nodes[idx]["children"]

    # Apply desired bone children
    for parent_idx, child_indices in desired_children.items():
        if "children" not in nodes[parent_idx]:
            nodes[parent_idx]["children"] = []
        nodes[parent_idx]["children"].extend(child_indices)

    # Update the scene root to have tag_torso as child instead of tag_weapon_right.
    # Use glTF scene data instead of hardcoded node indices.
    scene_idx = gltf.get("scene", 0)
    scene_nodes = (gltf.get("scenes", [{}])[scene_idx] or {}).get("nodes", [])
    root_idx = scene_nodes[0] if scene_nodes else None
    tag_torso_idx = name_to_idx["tag_torso"]
    tag_weapon_right_idx = name_to_idx["tag_weapon_right"]

    if isinstance(root_idx, int) and 0 <= root_idx < len(nodes) and root_idx != tag_torso_idx:
        # Root should have: mesh nodes + tag_torso (the new skeleton root)
        root_children = nodes[root_idx].get("children", [])
        # Remove tag_weapon_right from root (it's now under tag_torso)
        if tag_weapon_right_idx in root_children:
            root_children.remove(tag_weapon_right_idx)
        # Add tag_torso if not already there
        if tag_torso_idx not in root_children:
            root_children.append(tag_torso_idx)
        nodes[root_idx]["children"] = root_children

    # Add new bones to skin joints array (append to end so existing indices stay valid)
    new_joint_indices = []
    for bone_name in bones_to_add:
        new_joint_indices.append(name_to_idx[bone_name])
    skin["joints"].extend(new_joint_indices)

    # Set skeleton root to tag_torso
    skin["skeleton"] = tag_torso_idx

    print(f"Skin joints after: {len(skin['joints'])}")

    # Extend inverse bind matrices
    # Current IBM accessor
    ibm_acc_idx = skin["inverseBindMatrices"]
    ibm_acc = accessors[ibm_acc_idx]
    ibm_bv_idx = ibm_acc["bufferView"]
    ibm_bv = buffer_views[ibm_bv_idx]

    old_ibm_count = ibm_acc["count"]
    new_ibm_count = len(skin["joints"])
    num_new_ibms = new_ibm_count - old_ibm_count

    print(f"IBM: {old_ibm_count} -> {new_ibm_count} (adding {num_new_ibms})")

    # Each IBM is a MAT4 = 16 floats = 64 bytes
    ibm_byte_offset = ibm_bv["byteOffset"]
    ibm_byte_length = ibm_bv["byteLength"]

    # Read existing IBMs
    existing_ibm_data = bin_data[ibm_byte_offset:ibm_byte_offset + ibm_byte_length]

    # Create identity IBMs for new bones
    new_ibm_bytes = b""
    for _ in range(num_new_ibms):
        for val in identity_mat4():
            new_ibm_bytes += struct.pack("<f", val)

    # Append new IBM data to the end of the binary buffer
    new_ibm_offset = len(bin_data)
    combined_ibm_data = existing_ibm_data + new_ibm_bytes

    # Add new buffer view for the combined IBMs
    new_bv_idx = len(buffer_views)
    buffer_views.append({
        "buffer": 0,
        "byteOffset": new_ibm_offset,
        "byteLength": len(combined_ibm_data),
    })

    # Update IBM accessor to point to new buffer view
    ibm_acc["bufferView"] = new_bv_idx
    ibm_acc["count"] = new_ibm_count

    # Append the combined IBM data to binary buffer
    bin_data = bin_data + combined_ibm_data

    # Update buffer size
    buffers[0]["byteLength"] = len(bin_data)

    # Verify hierarchy
    print("\n=== Verifying hierarchy ===")
    def print_bone_tree(idx, depth=0, max_depth=3):
        name = nodes[idx].get("name", f"node_{idx}")
        children = nodes[idx].get("children", [])
        bone_children = [c for c in children if c in all_bone_indices]
        print(f"  {'  ' * depth}{name} (node {idx}, {len(bone_children)} bone children)")
        if depth < max_depth:
            for c in bone_children:
                print_bone_tree(c, depth + 1, max_depth)

    print_bone_tree(tag_torso_idx, max_depth=2)

    # Write rebuilt GLB
    write_glb(GLB_PATH, gltf, bin_data)
    new_size = GLB_PATH.stat().st_size
    old_size = GLB_BACKUP.stat().st_size
    print(f"\nWrote rebuilt GLB: {old_size} -> {new_size} bytes (+{new_size - old_size})")
    print("Done!")


if __name__ == "__main__":
    main()
