import struct, json, os

files = [
    ("prescale_bak", r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\model_export\thundergun_view_lod0.glb.prescale_bak"),
    ("bak_pre_bindfix", r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\model_export\thundergun_view_lod0.glb.bak.pre_bindfix"),
    ("bak_master", r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\model_export\thundergun_view_lod0.glb.bak"),
    ("current_glb", r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\model_export\thundergun_view_lod0.glb"),
]

for label, path in files:
    if not os.path.exists(path):
        print(f"{label:20s}: NOT FOUND")
        continue
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"glTF":
        print(f"{label:20s}: NOT GLB")
        continue
    jl = struct.unpack_from("<I", data, 12)[0]
    g = json.loads(data[20:20+jl])
    bvs = g.get("bufferViews", [])
    ms = g.get("meshes", [])
    tp = sum(len(m.get("primitives", [])) for m in ms)
    ns = g.get("nodes", [])
    sk = g.get("skins", [])
    hs = any("byteStride" in b for b in bvs)
    ri = sk[0]["joints"][0] if sk else -1
    rr = ns[ri].get("rotation", [0, 0, 0, 1]) if ri >= 0 else "none"
    print(f"{label:20s}: {size:>10,} B | {len(bvs):3d} BVs | {len(ms):2d}m/{tp:2d}p | {len(ns):2d} nodes | stride={hs} | rootR={[round(x,4) for x in rr]}")
