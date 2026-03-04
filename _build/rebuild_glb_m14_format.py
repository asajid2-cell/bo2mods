"""
Rebuild thundergun viewmodel GLB to exactly match M14's format:
- One shared interleaved vertex buffer (pos+norm+uv, stride=32)
- Separate joints buffer (uint8 VEC4)
- Separate weights buffer (float VEC4)
- One mesh per material, each with its own index buffer
- All meshes reference the same shared vertex pool
- Skeleton structure: tag_weapon_right as root (same as current)
"""
import json, struct, sys, shutil

SRC = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\model_export\thundergun_view_lod0.glb.bak"
DST = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\model_export\thundergun_view_lod0.glb"

def read_glb(path):
    with open(path, 'rb') as f:
        magic = f.read(4)
        version = struct.unpack('<I', f.read(4))[0]
        total_len = struct.unpack('<I', f.read(4))[0]
        json_len = struct.unpack('<I', f.read(4))[0]
        f.read(4)
        json_bytes = f.read(json_len)
        bin_data = b''
        if f.tell() < total_len:
            bin_len = struct.unpack('<I', f.read(4))[0]
            f.read(4)
            bin_data = f.read(bin_len)
    return json.loads(json_bytes), bin_data

def read_acc_all(gltf, bin_data, acc_idx):
    """Read all data from an accessor."""
    acc = gltf['accessors'][acc_idx]
    bv = gltf['bufferViews'][acc['bufferView']]
    base_offset = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
    stride = bv.get('byteStride', 0)

    comp_fmts = {5120: 'b', 5121: 'B', 5122: 'h', 5123: 'H', 5125: 'I', 5126: 'f'}
    comp_sizes = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
    type_counts = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}

    fmt = comp_fmts[acc['componentType']]
    comp_size = comp_sizes[acc['componentType']]
    count = type_counts[acc['type']]
    item_size = count * comp_size

    if stride == 0:
        stride = item_size

    results = []
    for i in range(acc['count']):
        pos = base_offset + i * stride
        vals = struct.unpack_from(f'<{count}{fmt}', bin_data, pos)
        results.append(list(vals))
    return results

print("=== Rebuilding thundergun GLB in M14 format ===")

# Read original backup
gltf, bin_data = read_glb(SRC)
print(f"Read original: {len(gltf['nodes'])} nodes, {len(gltf['meshes'])} meshes")

# Extract all primitives grouped by material
# Each primitive -> (material_name, positions, normals, uvs, joints, weights, indices)
all_prims = []
for mi, mesh in enumerate(gltf['meshes']):
    for pi, prim in enumerate(mesh['primitives']):
        mat_idx = prim.get('material', 0)
        mat_name = gltf['materials'][mat_idx]['name']

        positions = read_acc_all(gltf, bin_data, prim['attributes']['POSITION'])
        normals = read_acc_all(gltf, bin_data, prim['attributes']['NORMAL'])
        uvs = read_acc_all(gltf, bin_data, prim['attributes']['TEXCOORD_0'])
        joints = read_acc_all(gltf, bin_data, prim['attributes']['JOINTS_0'])
        weights = read_acc_all(gltf, bin_data, prim['attributes']['WEIGHTS_0'])

        indices = None
        if 'indices' in prim:
            indices = read_acc_all(gltf, bin_data, prim['indices'])
            indices = [idx[0] for idx in indices]  # flatten SCALAR

        all_prims.append({
            'mat_idx': mat_idx,
            'mat_name': mat_name,
            'positions': positions,
            'normals': normals,
            'uvs': uvs,
            'joints': joints,
            'weights': weights,
            'indices': indices,
        })

print(f"Extracted {len(all_prims)} primitives")

# Group primitives by material
mat_groups = {}
for p in all_prims:
    mi = p['mat_idx']
    if mi not in mat_groups:
        mat_groups[mi] = []
    mat_groups[mi].append(p)

print(f"Grouped into {len(mat_groups)} materials")

# Merge all vertices into one global pool
# Track per-material index buffers
global_positions = []
global_normals = []
global_uvs = []
global_joints = []
global_weights = []
material_indices = {}  # mat_idx -> list of triangle indices

global_vert_count = 0
for mat_idx in sorted(mat_groups.keys()):
    prims = mat_groups[mat_idx]
    mat_indices = []

    for p in prims:
        base = global_vert_count
        n_verts = len(p['positions'])

        global_positions.extend(p['positions'])
        global_normals.extend(p['normals'])
        global_uvs.extend(p['uvs'])
        global_joints.extend(p['joints'])
        global_weights.extend(p['weights'])

        if p['indices'] is not None:
            mat_indices.extend([idx + base for idx in p['indices']])
        else:
            mat_indices.extend(range(base, base + n_verts))

        global_vert_count += n_verts

    material_indices[mat_idx] = mat_indices

total_verts = len(global_positions)
print(f"Total vertices: {total_verts}")
for mat_idx, indices in material_indices.items():
    print(f"  Material {mat_idx}: {len(indices)} indices ({len(indices)//3} triangles)")

# Compute global bounding box
pos_min = [min(p[i] for p in global_positions) for i in range(3)]
pos_max = [max(p[i] for p in global_positions) for i in range(3)]
print(f"Bounds: min={[round(x,2) for x in pos_min]} max={[round(x,2) for x in pos_max]}")

# Build binary data in M14 format
new_bin = bytearray()

# Buffer View 0: Interleaved pos(12) + norm(12) + uv(8) = 32 bytes stride
bv0_offset = len(new_bin)
for i in range(total_verts):
    new_bin.extend(struct.pack('<3f', *global_positions[i]))
    new_bin.extend(struct.pack('<3f', *global_normals[i]))
    new_bin.extend(struct.pack('<2f', *global_uvs[i]))
bv0_len = len(new_bin) - bv0_offset
assert bv0_len == total_verts * 32

# Buffer View 1: JOINTS_0 (uint8 VEC4, 4 bytes per vertex)
bv1_offset = len(new_bin)
for i in range(total_verts):
    new_bin.extend(struct.pack('4B', *global_joints[i]))
bv1_len = len(new_bin) - bv1_offset

# Buffer View 2: WEIGHTS_0 (float VEC4, 16 bytes per vertex)
bv2_offset = len(new_bin)
for i in range(total_verts):
    new_bin.extend(struct.pack('<4f', *global_weights[i]))
bv2_len = len(new_bin) - bv2_offset

# Buffer View 3: IBMs (reuse original)
old_skin = gltf['skins'][0]
old_ibm_acc = gltf['accessors'][old_skin['inverseBindMatrices']]
old_ibm_bv = gltf['bufferViews'][old_ibm_acc['bufferView']]
ibm_offset_in_old = old_ibm_bv.get('byteOffset', 0)
ibm_len = old_ibm_bv['byteLength']
# Align to 4 bytes
while len(new_bin) % 4 != 0:
    new_bin.append(0)
bv3_offset = len(new_bin)
new_bin.extend(bin_data[ibm_offset_in_old:ibm_offset_in_old + ibm_len])
bv3_len = ibm_len

# Buffer Views 4+: Index buffers (one per material)
# Use uint16 indices like M14
index_bv_info = []  # (bv_offset, bv_len, count) per material
sorted_mats = sorted(material_indices.keys())
for mat_idx in sorted_mats:
    indices = material_indices[mat_idx]
    # Align to 2 bytes
    while len(new_bin) % 2 != 0:
        new_bin.append(0)
    ibuf_offset = len(new_bin)
    for idx in indices:
        new_bin.extend(struct.pack('<H', idx))
    ibuf_len = len(new_bin) - ibuf_offset
    index_bv_info.append((ibuf_offset, ibuf_len, len(indices)))

# Now build the glTF JSON
# Reuse original bone nodes (tag_weapon_right and children)
# Original skin joints: [25, 1, 2, 3, 18, 5, 4, 7, 6, 9, 8, 14, 10, 11, 12, 13, 15, 17, 16, 19, 20, 21, 22, 23, 24]
# Original skeleton root: node 25 (tag_weapon_right)

# Keep original bone nodes exactly as they are
# Node indices in original: 0-24 are bone nodes (0 is arm root which we'll discard)
# Node 25 = tag_weapon_right, nodes 1-24 = weapon bones

# Build new node list: bones first, then mesh nodes, then scene root
# Like M14: [j_gun(0), bone1(1), ..., boneN, surf0, surf1, ..., skel_root]

# Bone nodes: tag_weapon_right = new node 0, then its children
# Map old node indices to new ones
old_joints = old_skin['joints']  # [25, 1, 2, 3, 18, 5, 4, 7, 6, 9, 8, 14, 10, 11, 12, 13, 15, 17, 16, 19, 20, 21, 22, 23, 24]

# Create mapping: old_node_idx -> new_node_idx
# tag_weapon_right (old 25) -> new 0
# Then remaining joints in order
old_to_new = {}
old_to_new[25] = 0  # tag_weapon_right -> 0
new_idx = 1
for old_idx in old_joints[1:]:  # skip first (25)
    old_to_new[old_idx] = new_idx
    new_idx += 1
# new_idx is now 25 (number of joints)

num_joints = len(old_joints)
num_meshes = len(sorted_mats)

# Build new nodes
new_nodes = []

# Node 0: tag_weapon_right (skeleton root)
old_twr = gltf['nodes'][25]
twr_node = {'name': 'tag_weapon_right'}
if 'rotation' in old_twr:
    twr_node['rotation'] = old_twr['rotation']
if 'translation' in old_twr:
    twr_node['translation'] = old_twr['translation']
# Remap children
if 'children' in old_twr:
    twr_node['children'] = [old_to_new[c] for c in old_twr['children'] if c in old_to_new]
new_nodes.append(twr_node)

# Nodes 1-24: other bone nodes
for old_idx in old_joints[1:]:
    old_node = gltf['nodes'][old_idx]
    new_node = {'name': old_node.get('name', f'bone_{old_idx}')}
    if 'translation' in old_node:
        new_node['translation'] = old_node['translation']
    if 'rotation' in old_node:
        new_node['rotation'] = old_node['rotation']
    if 'scale' in old_node:
        new_node['scale'] = old_node['scale']
    if 'children' in old_node:
        remapped = [old_to_new[c] for c in old_node['children'] if c in old_to_new]
        if remapped:
            new_node['children'] = remapped
    new_nodes.append(new_node)

# Mesh nodes (25 to 25+num_meshes-1)
mesh_node_start = num_joints
for i in range(num_meshes):
    new_nodes.append({
        'name': f'surf{i}',
        'mesh': i,
        'skin': 0,
    })

# Scene root node
skel_node_idx = mesh_node_start + num_meshes
skel_children = list(range(mesh_node_start, mesh_node_start + num_meshes)) + [0]
new_nodes.append({
    'name': 'thundergun_view_lod0_skel',
    'children': skel_children,
})

print(f"New nodes: {len(new_nodes)} ({num_joints} bones + {num_meshes} meshes + 1 root)")

# Build buffer views
new_buffer_views = [
    # BV 0: interleaved pos+norm+uv
    {'buffer': 0, 'byteOffset': bv0_offset, 'byteLength': bv0_len, 'byteStride': 32, 'target': 34962},
    # BV 1: joints
    {'buffer': 0, 'byteOffset': bv1_offset, 'byteLength': bv1_len, 'target': 34962},
    # BV 2: weights
    {'buffer': 0, 'byteOffset': bv2_offset, 'byteLength': bv2_len, 'target': 34962},
    # BV 3: IBMs
    {'buffer': 0, 'byteOffset': bv3_offset, 'byteLength': bv3_len},
]
# Add index buffer views
for ibuf_offset, ibuf_len, _ in index_bv_info:
    new_buffer_views.append({
        'buffer': 0, 'byteOffset': ibuf_offset, 'byteLength': ibuf_len, 'target': 34963,
    })

# Build accessors
new_accessors = []

# Accessor 0: POSITION (shared)
new_accessors.append({
    'bufferView': 0, 'byteOffset': 0,
    'componentType': 5126, 'count': total_verts, 'type': 'VEC3',
    'min': pos_min, 'max': pos_max,
})
# Accessor 1: NORMAL (shared)
new_accessors.append({
    'bufferView': 0, 'byteOffset': 12,
    'componentType': 5126, 'count': total_verts, 'type': 'VEC3',
})
# Accessor 2: TEXCOORD_0 (shared)
new_accessors.append({
    'bufferView': 0, 'byteOffset': 24,
    'componentType': 5126, 'count': total_verts, 'type': 'VEC2',
})
# Accessor 3: JOINTS_0 (shared)
new_accessors.append({
    'bufferView': 1, 'byteOffset': 0,
    'componentType': 5121, 'count': total_verts, 'type': 'VEC4',
})
# Accessor 4: WEIGHTS_0 (shared)
new_accessors.append({
    'bufferView': 2, 'byteOffset': 0,
    'componentType': 5126, 'count': total_verts, 'type': 'VEC4',
})
# Accessor 5: IBMs
new_accessors.append({
    'bufferView': 3, 'byteOffset': 0,
    'componentType': 5126, 'count': num_joints, 'type': 'MAT4',
})
# Accessors 6+: Index buffers
for i, (_, _, count) in enumerate(index_bv_info):
    new_accessors.append({
        'bufferView': 4 + i, 'byteOffset': 0,
        'componentType': 5123, 'count': count, 'type': 'SCALAR',
    })

# Build meshes (one per material)
new_meshes = []
for i, mat_idx in enumerate(sorted_mats):
    new_meshes.append({
        'primitives': [{
            'attributes': {
                'POSITION': 0,
                'NORMAL': 1,
                'TEXCOORD_0': 2,
                'JOINTS_0': 3,
                'WEIGHTS_0': 4,
            },
            'indices': 6 + i,
            'material': mat_idx,
        }],
    })

# Build materials (keep original)
new_materials = gltf['materials']

# Build skin
new_skin = {
    'joints': list(range(num_joints)),
    'skeleton': 0,
    'inverseBindMatrices': 5,
}

# Build final glTF
new_gltf = {
    'asset': {'generator': 'thundergun_rebuild', 'version': '2.0'},
    'scene': 0,
    'scenes': [{'nodes': [skel_node_idx]}],
    'nodes': new_nodes,
    'meshes': new_meshes,
    'accessors': new_accessors,
    'bufferViews': new_buffer_views,
    'buffers': [{'byteLength': len(new_bin)}],
    'materials': new_materials,
    'skins': [new_skin],
}

# Write GLB
json_bytes = json.dumps(new_gltf, separators=(',', ':')).encode('utf-8')
# Pad JSON to 4-byte alignment
while len(json_bytes) % 4 != 0:
    json_bytes += b' '

total_len = 12 + 8 + len(json_bytes) + 8 + len(new_bin)

with open(DST, 'wb') as f:
    f.write(b'glTF')
    f.write(struct.pack('<I', 2))
    f.write(struct.pack('<I', total_len))
    # JSON chunk
    f.write(struct.pack('<I', len(json_bytes)))
    f.write(b'JSON')
    f.write(json_bytes)
    # BIN chunk
    f.write(struct.pack('<I', len(new_bin)))
    f.write(b'BIN\x00')
    f.write(new_bin)

print(f"\nWrote {total_len} bytes to {DST}")
print("Done!")
