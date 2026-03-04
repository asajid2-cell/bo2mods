"""Inspect GLB node hierarchy and mesh structure."""
import json, struct

def inspect_glb(glb_path):
    with open(glb_path, 'rb') as f:
        data = f.read()

    magic, version, length = struct.unpack_from('<III', data, 0)
    offset = 12
    json_chunk = None
    while offset < len(data):
        chunk_len, chunk_type = struct.unpack_from('<II', data, offset)
        chunk_data = data[offset+8:offset+8+chunk_len]
        if chunk_type == 0x4E4F534A:
            json_chunk = chunk_data
        offset += 8 + chunk_len

    gltf = json.loads(json_chunk.decode('utf-8'))

    nodes = gltf.get('nodes', [])
    print(f"Total nodes: {len(nodes)}")
    print(f"Scenes: {gltf.get('scenes', [])}")
    print()

    for i, node in enumerate(nodes):
        name = node.get('name', f'<unnamed_{i}>')
        has_mesh = 'mesh' in node
        children = node.get('children', [])
        trans = node.get('translation')
        rot = node.get('rotation')
        scale = node.get('scale')
        skin = node.get('skin')

        prefix = "MESH" if has_mesh else "BONE"
        print(f"  [{i:2d}] {prefix} '{name}'", end="")
        if has_mesh:
            print(f" mesh={node['mesh']}", end="")
        if children:
            print(f" children={children}", end="")
        if trans:
            print(f" t=[{trans[0]:.4f},{trans[1]:.4f},{trans[2]:.4f}]", end="")
        if rot:
            print(f" r=[{rot[0]:.4f},{rot[1]:.4f},{rot[2]:.4f},{rot[3]:.4f}]", end="")
        if scale:
            print(f" s={scale}", end="")
        if skin is not None:
            print(f" skin={skin}", end="")
        print()

    print(f"\nMeshes: {len(gltf.get('meshes', []))}")
    for i, mesh in enumerate(gltf.get('meshes', [])):
        name = mesh.get('name', f'<unnamed_{i}>')
        prims = mesh.get('primitives', [])
        print(f"  mesh[{i}] '{name}': {len(prims)} primitives")

    if 'skins' in gltf:
        print(f"\nSkins: {len(gltf['skins'])}")
        for i, skin in enumerate(gltf['skins']):
            joints = skin.get('joints', [])
            print(f"  skin[{i}]: {len(joints)} joints = {joints}")
    else:
        print("\nNo skins")

BASE = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\model_export"

print("=== VIEW MODEL (backup) ===")
inspect_glb(f"{BASE}/thundergun_view_lod0.glb.prescale_bak")
