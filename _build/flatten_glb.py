"""
Aggressively flatten GLB: remove ALL bone nodes except tag_weapon_right.
Creates a truly rigid model that can't be deformed by animations.

Original structure:
  thundergun_view_lod0_skel (root)
    ├── surf0..surf13 (meshes, skin=0)
    └── tag_weapon_right (bone root, rot=-90°X)
        ├── tag_brass, tag_flash, ...
        └── tag_pump_animate -> ...24 more bones

New structure:
  tag_weapon_right (root, identity transform)
    └── surf0..surf13 (meshes, no skin)
"""
import json, struct, os, shutil

BASE = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\model_export"
SCALE = 0.65

def flatten_glb(glb_path):
    backup_path = glb_path + ".prescale_bak"
    if os.path.exists(backup_path):
        shutil.copy2(backup_path, glb_path)
        print(f"  Restored from backup")

    with open(glb_path, 'rb') as f:
        data = f.read()

    magic = struct.unpack_from('<I', data, 0)[0]
    assert magic == 0x46546C67

    offset = 12
    json_chunk = None
    bin_chunk = None
    while offset < len(data):
        chunk_len, chunk_type = struct.unpack_from('<II', data, offset)
        chunk_data = data[offset+8:offset+8+chunk_len]
        if chunk_type == 0x4E4F534A:
            json_chunk = chunk_data
        elif chunk_type == 0x004E4942:
            bin_chunk = bytearray(chunk_data)
        offset += 8 + chunk_len

    gltf = json.loads(json_chunk.decode('utf-8'))
    nodes = gltf['nodes']

    # Find all mesh nodes and their mesh indices
    mesh_nodes = []
    for i, node in enumerate(nodes):
        if 'mesh' in node:
            mesh_nodes.append((i, node))

    print(f"  Found {len(mesh_nodes)} mesh nodes")

    # Build new node list:
    # Node 0: tag_weapon_right (root, identity transform, children=[1..N])
    # Nodes 1..N: mesh nodes (no skin, no parent hierarchy)
    new_nodes = []

    # Root node - tag_weapon_right with identity transform (no rotation!)
    root_children = list(range(1, len(mesh_nodes) + 1))
    new_nodes.append({
        "name": "tag_weapon_right",
        "children": root_children
    })

    # Mesh nodes
    for old_idx, old_node in mesh_nodes:
        new_node = {
            "name": old_node.get("name", f"surf{len(new_nodes)-1}"),
            "mesh": old_node["mesh"]
        }
        # Do NOT copy: skin, translation, rotation, scale, children
        new_nodes.append(new_node)

    # Remove skins entirely
    if 'skins' in gltf:
        del gltf['skins']

    # Update nodes
    gltf['nodes'] = new_nodes

    # Update scene to reference new root (node 0)
    gltf['scenes'] = [{"nodes": [0]}]

    # Strip JOINTS_0, WEIGHTS_0 from all mesh primitives
    for mesh in gltf.get('meshes', []):
        for prim in mesh.get('primitives', []):
            attrs = prim.get('attributes', {})
            attrs.pop('JOINTS_0', None)
            attrs.pop('WEIGHTS_0', None)

    # Scale POSITION data
    scaled_accessors = set()
    for mesh in gltf.get('meshes', []):
        for prim in mesh.get('primitives', []):
            attrs = prim.get('attributes', {})
            if 'POSITION' not in attrs:
                continue
            acc_idx = attrs['POSITION']
            if acc_idx in scaled_accessors:
                continue
            scaled_accessors.add(acc_idx)

            accessor = gltf['accessors'][acc_idx]
            bv = gltf['bufferViews'][accessor['bufferView']]
            byte_off = bv.get('byteOffset', 0) + accessor.get('byteOffset', 0)
            cnt = accessor['count']
            stride = bv.get('byteStride', 12)

            for i in range(cnt):
                pos = byte_off + i * stride
                x, y, z = struct.unpack_from('<fff', bin_chunk, pos)
                struct.pack_into('<fff', bin_chunk, pos,
                               x * SCALE, y * SCALE, z * SCALE)

            if 'min' in accessor:
                accessor['min'] = [v * SCALE for v in accessor['min']]
            if 'max' in accessor:
                accessor['max'] = [v * SCALE for v in accessor['max']]

            print(f"  Scaled accessor {acc_idx}: {cnt} verts * {SCALE}")

    # Rebuild GLB
    new_json = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
    while len(new_json) % 4 != 0:
        new_json += b' '
    while len(bin_chunk) % 4 != 0:
        bin_chunk.append(0)

    total_length = 12 + 8 + len(new_json) + 8 + len(bin_chunk)
    output = bytearray()
    output += struct.pack('<III', 0x46546C67, 2, total_length)
    output += struct.pack('<II', len(new_json), 0x4E4F534A)
    output += new_json
    output += struct.pack('<II', len(bin_chunk), 0x004E4942)
    output += bin_chunk

    with open(glb_path, 'wb') as f:
        f.write(output)

    print(f"  Wrote: {os.path.basename(glb_path)} ({len(output)} bytes, was {len(data)})")
    print(f"  Nodes: {len(gltf['nodes'])} (was {len(nodes)})")

if __name__ == "__main__":
    print("=== Flatten view model ===")
    flatten_glb(os.path.join(BASE, "thundergun_view_lod0.glb"))

    world_path = os.path.join(BASE, "thundergun_world_lod0.glb")
    if os.path.exists(world_path + ".prescale_bak") or os.path.exists(world_path):
        print("\n=== Flatten world model ===")
        flatten_glb(world_path)

    print("\nDone!")
