"""
Rebuild thundergun viewmodel GLB in M14 format WITH scaling to match raygun proportions.

Raygun bounds: Center=[2.4, 0.8, -0.1], Size=[17.8, 10.2, 3.7]
Thundergun bounds: Center=[5.9, 5.7, -1.6], Size=[37.5, 18.7, 12.8]

Scale factor ~0.5 to match raygun X-size, then shift to match raygun center.
"""
import json, struct, math

SRC = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\model_export\thundergun_view_lod0.glb.bak"
DST = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\model_export\thundergun_view_lod0.glb"

SCALE = 0.60  # Bigger than raygun match - user said too small
# After scaling, thundergun center = [3.54, 3.42, -0.96]
# Raygun center = [2.4, 0.8, -0.1]
# Offset needed: [-1.14, -2.62, 0.86]
OFFSET = [-1.14, -2.62, 0.86]

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

def mat4_identity():
    return [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]

def mat4_from_trs(t, r, s=None):
    """Build 4x4 matrix from translation, rotation (quaternion xyzw), scale."""
    x, y, z, w = r
    m = [0]*16
    m[0] = 1 - 2*(y*y + z*z)
    m[1] = 2*(x*y + w*z)
    m[2] = 2*(x*z - w*y)
    m[4] = 2*(x*y - w*z)
    m[5] = 1 - 2*(x*x + z*z)
    m[6] = 2*(y*z + w*x)
    m[8] = 2*(x*z + w*y)
    m[9] = 2*(y*z - w*x)
    m[10] = 1 - 2*(x*x + y*y)
    if s:
        for i in range(3):
            m[i*4+0] *= s[i]
            m[i*4+1] *= s[i]
            m[i*4+2] *= s[i]
    m[12] = t[0]
    m[13] = t[1]
    m[14] = t[2]
    m[15] = 1
    return m

def mat4_multiply(a, b):
    r = [0]*16
    for i in range(4):
        for j in range(4):
            s = 0
            for k in range(4):
                s += a[k*4+i] * b[j*4+k]
            r[j*4+i] = s
    return r

def mat4_inverse(m):
    """Invert a 4x4 column-major matrix."""
    inv = [0]*16
    inv[0] = m[5]*m[10]*m[15] - m[5]*m[11]*m[14] - m[9]*m[6]*m[15] + m[9]*m[7]*m[14] + m[13]*m[6]*m[11] - m[13]*m[7]*m[10]
    inv[4] = -m[4]*m[10]*m[15] + m[4]*m[11]*m[14] + m[8]*m[6]*m[15] - m[8]*m[7]*m[14] - m[12]*m[6]*m[11] + m[12]*m[7]*m[10]
    inv[8] = m[4]*m[9]*m[15] - m[4]*m[11]*m[13] - m[8]*m[5]*m[15] + m[8]*m[7]*m[13] + m[12]*m[5]*m[11] - m[12]*m[7]*m[9]
    inv[12] = -m[4]*m[9]*m[14] + m[4]*m[10]*m[13] + m[8]*m[5]*m[14] - m[8]*m[6]*m[13] - m[12]*m[5]*m[10] + m[12]*m[6]*m[9]
    inv[1] = -m[1]*m[10]*m[15] + m[1]*m[11]*m[14] + m[9]*m[2]*m[15] - m[9]*m[3]*m[14] - m[13]*m[2]*m[11] + m[13]*m[3]*m[10]
    inv[5] = m[0]*m[10]*m[15] - m[0]*m[11]*m[14] - m[8]*m[2]*m[15] + m[8]*m[3]*m[14] + m[12]*m[2]*m[11] - m[12]*m[3]*m[10]
    inv[9] = -m[0]*m[9]*m[15] + m[0]*m[11]*m[13] + m[8]*m[1]*m[15] - m[8]*m[3]*m[13] - m[12]*m[1]*m[11] + m[12]*m[3]*m[9]
    inv[13] = m[0]*m[9]*m[14] - m[0]*m[10]*m[13] - m[8]*m[1]*m[14] + m[8]*m[2]*m[13] + m[12]*m[1]*m[10] - m[12]*m[2]*m[9]
    inv[2] = m[1]*m[6]*m[15] - m[1]*m[7]*m[14] - m[5]*m[2]*m[15] + m[5]*m[3]*m[14] + m[13]*m[2]*m[7] - m[13]*m[3]*m[6]
    inv[6] = -m[0]*m[6]*m[15] + m[0]*m[7]*m[14] + m[4]*m[2]*m[15] - m[4]*m[3]*m[14] - m[12]*m[2]*m[7] + m[12]*m[3]*m[6]
    inv[10] = m[0]*m[5]*m[15] - m[0]*m[7]*m[13] - m[4]*m[1]*m[15] + m[4]*m[3]*m[13] + m[12]*m[1]*m[7] - m[12]*m[3]*m[5]
    inv[14] = -m[0]*m[5]*m[14] + m[0]*m[6]*m[13] + m[4]*m[1]*m[14] - m[4]*m[2]*m[13] - m[12]*m[1]*m[6] + m[12]*m[2]*m[5]
    inv[3] = -m[1]*m[6]*m[11] + m[1]*m[7]*m[10] + m[5]*m[2]*m[11] - m[5]*m[3]*m[10] - m[9]*m[2]*m[7] + m[9]*m[3]*m[6]
    inv[7] = m[0]*m[6]*m[11] - m[0]*m[7]*m[10] - m[4]*m[2]*m[11] + m[4]*m[3]*m[10] + m[8]*m[2]*m[7] - m[8]*m[3]*m[6]
    inv[11] = -m[0]*m[5]*m[11] + m[0]*m[7]*m[9] + m[4]*m[1]*m[11] - m[4]*m[3]*m[9] - m[8]*m[1]*m[7] + m[8]*m[3]*m[5]
    inv[15] = m[0]*m[5]*m[10] - m[0]*m[6]*m[9] - m[4]*m[1]*m[10] + m[4]*m[2]*m[9] + m[8]*m[1]*m[6] - m[8]*m[2]*m[5]
    det = m[0]*inv[0] + m[1]*inv[4] + m[2]*inv[8] + m[3]*inv[12]
    if abs(det) < 1e-10:
        return mat4_identity()
    det = 1.0 / det
    return [x * det for x in inv]

print("=== Rebuilding thundergun GLB (scaled to raygun size) ===")

gltf, bin_data = read_glb(SRC)
print(f"Read original: {len(gltf['nodes'])} nodes, {len(gltf['meshes'])} meshes")

# Extract all primitives
all_prims = []
for mi, mesh in enumerate(gltf['meshes']):
    for pi, prim in enumerate(mesh['primitives']):
        mat_idx = prim.get('material', 0)
        positions = read_acc_all(gltf, bin_data, prim['attributes']['POSITION'])
        normals = read_acc_all(gltf, bin_data, prim['attributes']['NORMAL'])
        uvs = read_acc_all(gltf, bin_data, prim['attributes']['TEXCOORD_0'])
        joints = read_acc_all(gltf, bin_data, prim['attributes']['JOINTS_0'])
        weights = read_acc_all(gltf, bin_data, prim['attributes']['WEIGHTS_0'])
        indices = None
        if 'indices' in prim:
            indices = [x[0] for x in read_acc_all(gltf, bin_data, prim['indices'])]
        all_prims.append({
            'mat_idx': mat_idx, 'positions': positions, 'normals': normals,
            'uvs': uvs, 'joints': joints, 'weights': weights, 'indices': indices,
        })

# Apply scale + offset to positions
for p in all_prims:
    for v in p['positions']:
        v[0] = v[0] * SCALE + OFFSET[0]
        v[1] = v[1] * SCALE + OFFSET[1]
        v[2] = v[2] * SCALE + OFFSET[2]

# Group by material
mat_groups = {}
for p in all_prims:
    mi = p['mat_idx']
    if mi not in mat_groups:
        mat_groups[mi] = []
    mat_groups[mi].append(p)

# Merge vertices
global_positions = []
global_normals = []
global_uvs = []
global_joints = []
global_weights = []
material_indices = {}
global_vert_count = 0

for mat_idx in sorted(mat_groups.keys()):
    mat_indices = []
    for p in mat_groups[mat_idx]:
        base = global_vert_count
        global_positions.extend(p['positions'])
        global_normals.extend(p['normals'])
        global_uvs.extend(p['uvs'])
        global_joints.extend(p['joints'])
        global_weights.extend(p['weights'])
        if p['indices'] is not None:
            mat_indices.extend([idx + base for idx in p['indices']])
        else:
            mat_indices.extend(range(base, base + len(p['positions'])))
        global_vert_count += len(p['positions'])
    material_indices[mat_idx] = mat_indices

total_verts = len(global_positions)
pos_min = [min(p[i] for p in global_positions) for i in range(3)]
pos_max = [max(p[i] for p in global_positions) for i in range(3)]
center = [(pos_min[i]+pos_max[i])/2 for i in range(3)]
size = [pos_max[i]-pos_min[i] for i in range(3)]
print(f"Scaled bounds: min={[round(x,1) for x in pos_min]} max={[round(x,1) for x in pos_max]}")
print(f"Scaled center: {[round(x,1) for x in center]}")
print(f"Scaled size:   {[round(x,1) for x in size]}")
print(f"(Raygun ref:   center=[2.4, 0.8, -0.1] size=[17.8, 10.2, 3.7])")

# Build bone nodes with scaled translations
old_skin = gltf['skins'][0]
old_joints = old_skin['joints']  # [25, 1, 2, 3, 18, ...]

# Map old node indices to new
old_to_new = {25: 0}
new_idx = 1
for old_idx in old_joints[1:]:
    old_to_new[old_idx] = new_idx
    new_idx += 1
num_joints = len(old_joints)

# Build bone world transforms (for IBM recomputation)
def get_node_trs(node):
    t = node.get('translation', [0, 0, 0])
    r = node.get('rotation', [0, 0, 0, 1])
    s = node.get('scale', [1, 1, 1])
    return t, r, s

# Compute world transforms for all joints
world_transforms = {}

def compute_world_transform(old_idx, parent_world=None):
    node = gltf['nodes'][old_idx]
    t, r, s = get_node_trs(node)
    # Scale translation
    t_scaled = [t[0] * SCALE, t[1] * SCALE, t[2] * SCALE]
    local = mat4_from_trs(t_scaled, r, s)
    if parent_world:
        world = mat4_multiply(parent_world, local)
    else:
        world = local
    world_transforms[old_idx] = world
    if 'children' in node:
        for child in node['children']:
            if child in old_to_new:
                compute_world_transform(child, world)

# Start from tag_weapon_right (root bone)
compute_world_transform(25)

# Compute new IBMs
new_ibms = []
for old_idx in old_joints:
    if old_idx in world_transforms:
        ibm = mat4_inverse(world_transforms[old_idx])
    else:
        ibm = mat4_identity()
    new_ibms.append(ibm)

# Build binary data
new_bin = bytearray()

# BV0: interleaved pos+norm+uv (stride=32)
bv0_offset = len(new_bin)
for i in range(total_verts):
    new_bin.extend(struct.pack('<3f', *global_positions[i]))
    new_bin.extend(struct.pack('<3f', *global_normals[i]))
    new_bin.extend(struct.pack('<2f', *global_uvs[i]))
bv0_len = total_verts * 32

# BV1: joints
bv1_offset = len(new_bin)
for i in range(total_verts):
    new_bin.extend(struct.pack('4B', *global_joints[i]))
bv1_len = total_verts * 4

# BV2: weights
bv2_offset = len(new_bin)
for i in range(total_verts):
    new_bin.extend(struct.pack('<4f', *global_weights[i]))
bv2_len = total_verts * 16

# BV3: IBMs
while len(new_bin) % 4 != 0:
    new_bin.append(0)
bv3_offset = len(new_bin)
for ibm in new_ibms:
    new_bin.extend(struct.pack('<16f', *ibm))
bv3_len = num_joints * 64

# BV4+: index buffers
sorted_mats = sorted(material_indices.keys())
index_bv_info = []
for mat_idx in sorted_mats:
    indices = material_indices[mat_idx]
    while len(new_bin) % 2 != 0:
        new_bin.append(0)
    ibuf_offset = len(new_bin)
    for idx in indices:
        new_bin.extend(struct.pack('<H', idx))
    ibuf_len = len(new_bin) - ibuf_offset
    index_bv_info.append((ibuf_offset, ibuf_len, len(indices)))

# Build new nodes
new_nodes = []
num_meshes = len(sorted_mats)

# Node 0: tag_weapon_right
old_twr = gltf['nodes'][25]
twr_node = {'name': 'tag_weapon_right'}
if 'rotation' in old_twr:
    twr_node['rotation'] = old_twr['rotation']
# Translation scaled (should be [0,0,0] but just in case)
if 'translation' in old_twr:
    t = old_twr['translation']
    twr_node['translation'] = [t[0]*SCALE, t[1]*SCALE, t[2]*SCALE]
if 'children' in old_twr:
    twr_node['children'] = [old_to_new[c] for c in old_twr['children'] if c in old_to_new]
new_nodes.append(twr_node)

# Nodes 1-24: other bones with scaled translations
for old_idx in old_joints[1:]:
    old_node = gltf['nodes'][old_idx]
    new_node = {'name': old_node.get('name', f'bone_{old_idx}')}
    if 'translation' in old_node:
        t = old_node['translation']
        new_node['translation'] = [t[0]*SCALE, t[1]*SCALE, t[2]*SCALE]
    if 'rotation' in old_node:
        new_node['rotation'] = old_node['rotation']
    if 'scale' in old_node:
        new_node['scale'] = old_node['scale']
    if 'children' in old_node:
        remapped = [old_to_new[c] for c in old_node['children'] if c in old_to_new]
        if remapped:
            new_node['children'] = remapped
    new_nodes.append(new_node)

# Mesh nodes
mesh_node_start = num_joints
for i in range(num_meshes):
    new_nodes.append({'name': f'surf{i}', 'mesh': i, 'skin': 0})

# Scene root
skel_node_idx = mesh_node_start + num_meshes
new_nodes.append({
    'name': 'thundergun_view_lod0_skel',
    'children': list(range(mesh_node_start, mesh_node_start + num_meshes)) + [0],
})

# Build bufferViews
new_bvs = [
    {'buffer': 0, 'byteOffset': bv0_offset, 'byteLength': bv0_len, 'byteStride': 32, 'target': 34962},
    {'buffer': 0, 'byteOffset': bv1_offset, 'byteLength': bv1_len, 'target': 34962},
    {'buffer': 0, 'byteOffset': bv2_offset, 'byteLength': bv2_len, 'target': 34962},
    {'buffer': 0, 'byteOffset': bv3_offset, 'byteLength': bv3_len},
]
for ibuf_offset, ibuf_len, _ in index_bv_info:
    new_bvs.append({'buffer': 0, 'byteOffset': ibuf_offset, 'byteLength': ibuf_len, 'target': 34963})

# Build accessors
new_accs = [
    {'bufferView': 0, 'byteOffset': 0, 'componentType': 5126, 'count': total_verts, 'type': 'VEC3', 'min': pos_min, 'max': pos_max},
    {'bufferView': 0, 'byteOffset': 12, 'componentType': 5126, 'count': total_verts, 'type': 'VEC3'},
    {'bufferView': 0, 'byteOffset': 24, 'componentType': 5126, 'count': total_verts, 'type': 'VEC2'},
    {'bufferView': 1, 'byteOffset': 0, 'componentType': 5121, 'count': total_verts, 'type': 'VEC4'},
    {'bufferView': 2, 'byteOffset': 0, 'componentType': 5126, 'count': total_verts, 'type': 'VEC4'},
    {'bufferView': 3, 'byteOffset': 0, 'componentType': 5126, 'count': num_joints, 'type': 'MAT4'},
]
for i, (_, _, count) in enumerate(index_bv_info):
    new_accs.append({'bufferView': 4+i, 'byteOffset': 0, 'componentType': 5123, 'count': count, 'type': 'SCALAR'})

# Meshes
new_meshes = []
for i, mat_idx in enumerate(sorted_mats):
    new_meshes.append({'primitives': [{'attributes': {'POSITION': 0, 'NORMAL': 1, 'TEXCOORD_0': 2, 'JOINTS_0': 3, 'WEIGHTS_0': 4}, 'indices': 6+i, 'material': mat_idx}]})

new_gltf = {
    'asset': {'generator': 'thundergun_rebuild_scaled', 'version': '2.0'},
    'scene': 0, 'scenes': [{'nodes': [skel_node_idx]}],
    'nodes': new_nodes, 'meshes': new_meshes, 'accessors': new_accs,
    'bufferViews': new_bvs, 'buffers': [{'byteLength': len(new_bin)}],
    'materials': gltf['materials'], 'skins': [{'joints': list(range(num_joints)), 'skeleton': 0, 'inverseBindMatrices': 5}],
}

json_bytes = json.dumps(new_gltf, separators=(',', ':')).encode('utf-8')
while len(json_bytes) % 4 != 0:
    json_bytes += b' '
total_len = 12 + 8 + len(json_bytes) + 8 + len(new_bin)

with open(DST, 'wb') as f:
    f.write(b'glTF')
    f.write(struct.pack('<I', 2))
    f.write(struct.pack('<I', total_len))
    f.write(struct.pack('<I', len(json_bytes)))
    f.write(b'JSON')
    f.write(json_bytes)
    f.write(struct.pack('<I', len(new_bin)))
    f.write(b'BIN\x00')
    f.write(new_bin)

print(f"\nWrote {total_len} bytes")
print("Done!")
