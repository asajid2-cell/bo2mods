"""
Rebuild thundergun_view GLB to match T6 weapon viewmodel structure.

Working T6 pattern (from M14):
  scene_root (container, no transform)
    ├── surf0 (mesh, skin=0)
    ├── surf1 (mesh, skin=0)
    └── j_gun (skeleton root, R=[-0.7071,0,0,0.7071])
         ├── tag_brass
         ├── tag_flash
         └── ... weapon bones

Our thundergun needs:
  scene_root
    ├── mesh nodes (skin=0)
    └── tag_weapon_right (skeleton root, same rotation as j_gun)
         ├── tag_brass, tag_flash, tag_pump_animate, etc.
         └── ... weapon bones only (25 total)

NO tag_torso, tag_weapon_left, tag_weapon, tag_cambone, etc.
"""
import json
import struct
import shutil
from pathlib import Path

ROOT = Path(r"z:\Games\pluto_t6_full_game")
GLB_PATH = ROOT / "_build/panzer_work/so_zsurvival_zm_transit/model_export/thundergun_view_lod0.glb"
GLB_BACKUP = GLB_PATH.with_suffix(".glb.bak")


def read_glb(path):
    with open(path, "rb") as f:
        magic = f.read(4)
        assert magic == b"glTF"
        version = struct.unpack("<I", f.read(4))[0]
        total_len = struct.unpack("<I", f.read(4))[0]
        json_len = struct.unpack("<I", f.read(4))[0]
        f.read(4)
        json_bytes = f.read(json_len)
        bin_data = b""
        if f.tell() < total_len:
            bin_len = struct.unpack("<I", f.read(4))[0]
            f.read(4)
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


def main():
    print("=== Rebuilding thundergun_view GLB (T6 style) ===\n")

    # Restore original backup
    if GLB_BACKUP.exists():
        shutil.copy2(str(GLB_BACKUP), str(GLB_PATH))
        print("Restored original GLB from backup")
    else:
        print("ERROR: No backup!")
        return

    gltf, bin_data = read_glb(GLB_PATH)
    nodes = gltf["nodes"]
    skin = gltf["skins"][0]
    accessors = gltf["accessors"]
    buffer_views = gltf["bufferViews"]
    buffers = gltf["buffers"]

    # Original structure:
    # [0] empty node
    # [1-24] weapon bone nodes
    # [25] tag_weapon_right (weapon root)
    # [26-39] mesh nodes (skin=0)
    # [40] scene root (children: [0, 26-39, 25])
    #
    # Skin joints: [25, 1, 2, 3, 18, 5, 4, 7, 6, 9, 8, 14, 10, 11, 12, 13, 15, 17, 16, 19, 20, 21, 22, 23, 24]
    # = 25 joints, all weapon bones, tag_weapon_right is joint[0]

    print(f"Original: {len(nodes)} nodes, {len(skin['joints'])} joints")

    # The original GLB is already close to T6 style!
    # tag_weapon_right [25] = equivalent of j_gun
    # All weapon bones are children of tag_weapon_right
    # Mesh nodes use skin[0]
    #
    # We just need to:
    # 1. Set skin.skeleton to tag_weapon_right
    # 2. Make sure tag_weapon_right is a direct child of scene root
    # 3. Remove unused node [0] from scene root children

    tag_wr_idx = 25  # tag_weapon_right

    # Set skeleton root to tag_weapon_right
    skin["skeleton"] = tag_wr_idx
    print(f"Set skin.skeleton = {tag_wr_idx} (tag_weapon_right)")

    # Clean up scene root children: mesh nodes + tag_weapon_right only
    root_idx = 40
    mesh_nodes = list(range(26, 40))  # nodes 26-39
    nodes[root_idx]["children"] = mesh_nodes + [tag_wr_idx]
    print(f"Scene root children: {len(mesh_nodes)} mesh + tag_weapon_right")

    # Rename scene root to match T6 convention
    nodes[root_idx]["name"] = "thundergun_view_lod0_skel"

    # Remove node[0] (empty unused node) from hierarchy
    # It's not referenced by skin or meshes, just cleanup
    nodes[0] = {"name": "_unused"}

    # Verify skin joints are clean (should be original 25 weapon joints)
    print(f"Skin joints: {len(skin['joints'])}")
    for i, ji in enumerate(skin['joints']):
        print(f"  [{i}] node[{ji}] = {nodes[ji].get('name', '?')}")

    # Verify tag_weapon_right has the right transform
    twr = nodes[tag_wr_idx]
    print(f"\ntag_weapon_right: R={twr.get('rotation', 'none')}")
    print(f"Children: {twr.get('children', [])}")

    # Write
    write_glb(GLB_PATH, gltf, bin_data)
    print(f"\nWrote: {GLB_PATH.stat().st_size} bytes")
    print("Done!")


if __name__ == "__main__":
    main()
