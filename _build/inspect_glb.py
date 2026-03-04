"""Deep inspection of the thundergun viewmodel GLB - skin, joints, mesh skinning."""
import json, struct
from pathlib import Path

glb_path = Path(r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\model_export\thundergun_view_lod0.glb")

with open(glb_path, "rb") as f:
    magic = f.read(4)
    version = struct.unpack("<I", f.read(4))[0]
    length = struct.unpack("<I", f.read(4))[0]
    chunk_len = struct.unpack("<I", f.read(4))[0]
    chunk_type = f.read(4)
    json_data = f.read(chunk_len).decode("utf-8")

gltf = json.loads(json_data)

nodes = gltf.get("nodes", [])
skins = gltf.get("skins", [])
meshes = gltf.get("meshes", [])
accessors = gltf.get("accessors", [])
bufferViews = gltf.get("bufferViews", [])

print(f"=== GLB Overview ===")
print(f"Nodes: {len(nodes)}")
print(f"Skins: {len(skins)}")
print(f"Meshes: {len(meshes)}")
print(f"Accessors: {len(accessors)}")
print(f"BufferViews: {len(bufferViews)}")
print()

# Nodes detail
print(f"=== All Nodes ===")
for i, n in enumerate(nodes):
    has_mesh = "mesh" in n
    has_skin = "skin" in n
    has_children = "children" in n
    extras = ""
    if has_mesh: extras += f" mesh={n['mesh']}"
    if has_skin: extras += f" skin={n['skin']}"
    if has_children: extras += f" children={n['children']}"
    if "translation" in n: extras += f" T={[round(x,3) for x in n['translation']]}"
    if "rotation" in n: extras += f" R={[round(x,4) for x in n['rotation']]}"
    if "scale" in n: extras += f" S={[round(x,3) for x in n['scale']]}"
    print(f"  [{i:2d}] {n.get('name', 'unnamed')}{extras}")
print()

# Skins detail
for si, skin in enumerate(skins):
    joints = skin.get("joints", [])
    print(f"=== Skin {si} ===")
    print(f"  Name: {skin.get('name', 'unnamed')}")
    print(f"  Skeleton root: {skin.get('skeleton', 'none')}")
    print(f"  Joints ({len(joints)}): {joints}")
    if "inverseBindMatrices" in skin:
        ibm_accessor = accessors[skin["inverseBindMatrices"]]
        print(f"  IBM accessor: idx={skin['inverseBindMatrices']}, count={ibm_accessor['count']}, type={ibm_accessor['type']}")
    print(f"  Joint names:")
    for ji, j in enumerate(joints):
        print(f"    [{ji}] node[{j}] = {nodes[j].get('name', 'unnamed')}")
    print()

# Mesh details
for mi, mesh in enumerate(meshes):
    print(f"=== Mesh {mi}: {mesh.get('name', 'unnamed')} ===")
    for pi, prim in enumerate(mesh.get("primitives", [])):
        attrs = prim.get("attributes", {})
        print(f"  Primitive {pi}: material={prim.get('material', 'none')}")
        for attr_name, acc_idx in attrs.items():
            acc = accessors[acc_idx]
            print(f"    {attr_name}: accessor[{acc_idx}] count={acc['count']} type={acc['type']} componentType={acc['componentType']}")
        if "indices" in prim:
            acc = accessors[prim["indices"]]
            print(f"    INDICES: accessor[{prim['indices']}] count={acc['count']}")

# Check which nodes reference meshes
print(f"\n=== Mesh -> Node mapping ===")
for i, n in enumerate(nodes):
    if "mesh" in n:
        print(f"  node[{i}] '{n.get('name','')}' -> mesh[{n['mesh']}] '{meshes[n['mesh']].get('name','')}'")
        if "skin" in n:
            print(f"    uses skin[{n['skin']}]")
