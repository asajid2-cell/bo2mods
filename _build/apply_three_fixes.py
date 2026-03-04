"""
Three-fix hard reset for thundergun:
1. Swap all 14 materials to 2-texture techset mc_lit_sm_b0c0_fw0jf955
2. Scale GLB model to 0.65x
3. Strip all skin data from GLB (true rigid)
"""
import json, struct, os, shutil

BASE = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit"

def fix_materials():
    mat_dir = os.path.join(BASE, "materials")
    count = 0
    for fname in sorted(os.listdir(mat_dir)):
        if not fname.startswith("mtl_wpn_t7_zmb_hd_thundergun_") or not fname.endswith(".json"):
            continue
        fpath = os.path.join(mat_dir, fname)
        with open(fpath, 'r') as f:
            mat = json.load(f)

        normal_img = None
        color_img = None
        for tex in mat.get("textures", []):
            if tex["semantic"] == "normalMap":
                normal_img = tex["image"]
            elif tex["semantic"] == "colorMap":
                color_img = tex["image"]

        if not normal_img or not color_img:
            print(f"  WARNING: {fname} missing normalMap or colorMap, skipping")
            continue

        new_mat = {
            "$schema": "http://openassettools.dev/schema/material.v1.json",
            "_game": "t6",
            "_type": "material",
            "_version": 1,
            "cameraRegion": "litOpaque",
            "constants": [],
            "contents": 1,
            "gameFlags": ["10"],
            "layeredSurfaceTypes": 536870912,
            "sortKey": 4,
            "stateBits": [
                {
                    "alphaTest": "disabled",
                    "blendOpAlpha": "disabled",
                    "blendOpRgb": "disabled",
                    "colorWriteAlpha": False,
                    "colorWriteRgb": False,
                    "cullFace": "back",
                    "depthTest": "less_equal",
                    "depthWrite": True,
                    "dstBlendAlpha": "zero",
                    "dstBlendRgb": "zero",
                    "polygonOffset": "offset0",
                    "polymodeLine": False,
                    "srcBlendAlpha": "one",
                    "srcBlendRgb": "one",
                    "stencilFront": {
                        "fail": "keep",
                        "func": "equal",
                        "pass": "keep",
                        "zfail": "keep"
                    }
                },
                {
                    "alphaTest": "disabled",
                    "blendOpAlpha": "disabled",
                    "blendOpRgb": "disabled",
                    "colorWriteAlpha": False,
                    "colorWriteRgb": False,
                    "cullFace": "back",
                    "depthTest": "less_equal",
                    "depthWrite": True,
                    "dstBlendAlpha": "zero",
                    "dstBlendRgb": "zero",
                    "polygonOffset": "offsetShadowmap",
                    "polymodeLine": False,
                    "srcBlendAlpha": "one",
                    "srcBlendRgb": "one"
                },
                {
                    "alphaTest": "disabled",
                    "blendOpAlpha": "disabled",
                    "blendOpRgb": "disabled",
                    "colorWriteAlpha": True,
                    "colorWriteRgb": True,
                    "cullFace": "back",
                    "depthTest": "less_equal",
                    "depthWrite": True,
                    "dstBlendAlpha": "zero",
                    "dstBlendRgb": "zero",
                    "polygonOffset": "offset0",
                    "polymodeLine": False,
                    "srcBlendAlpha": "one",
                    "srcBlendRgb": "one"
                },
                {
                    "alphaTest": "disabled",
                    "blendOpAlpha": "disabled",
                    "blendOpRgb": "disabled",
                    "colorWriteAlpha": False,
                    "colorWriteRgb": True,
                    "cullFace": "back",
                    "depthTest": "less_equal",
                    "depthWrite": False,
                    "dstBlendAlpha": "zero",
                    "dstBlendRgb": "zero",
                    "polygonOffset": "offset2",
                    "polymodeLine": True,
                    "srcBlendAlpha": "one",
                    "srcBlendRgb": "one"
                },
                {
                    "alphaTest": "disabled",
                    "blendOpAlpha": "disabled",
                    "blendOpRgb": "add",
                    "colorWriteAlpha": True,
                    "colorWriteRgb": True,
                    "cullFace": "back",
                    "depthTest": "less_equal",
                    "depthWrite": True,
                    "dstBlendAlpha": "zero",
                    "dstBlendRgb": "one",
                    "polygonOffset": "offset0",
                    "polymodeLine": False,
                    "srcBlendAlpha": "one",
                    "srcBlendRgb": "one"
                }
            ],
            "stateBitsEntry": [
                0, 1, 2, -1,
                2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
                -1, -1, -1, -1, -1, -1,
                3, -1, 2, 4
            ],
            "stateFlags": 121,
            "surfaceFlags": 13631488,
            "surfaceTypeBits": 4096,
            "techniqueSet": "mc_lit_sm_b0c0_fw0jf955",
            "textureAtlas": {"columns": 1, "rows": 1},
            "textures": [
                {
                    "image": normal_img,
                    "isMatureContent": False,
                    "name": "normalMap",
                    "samplerState": {
                        "clampU": False, "clampV": False, "clampW": False,
                        "filter": "aniso4x", "mipMap": "linear"
                    },
                    "semantic": "normalMap"
                },
                {
                    "image": color_img,
                    "isMatureContent": False,
                    "name": "colorMap",
                    "samplerState": {
                        "clampU": False, "clampV": False, "clampW": False,
                        "filter": "aniso4x", "mipMap": "linear"
                    },
                    "semantic": "colorMap"
                }
            ],
            "debugName": fname.replace(".json", "")
        }

        with open(fpath, 'w') as f:
            json.dump(new_mat, f, indent=4)
        count += 1
        print(f"  Updated: {fname} (normal={normal_img}, color={color_img})")

    print(f"  Total materials updated: {count}")

def fix_glb(glb_path, scale_factor=0.65):
    backup_path = glb_path + ".prescale_bak"
    if os.path.exists(backup_path):
        shutil.copy2(backup_path, glb_path)
        print(f"  Restored from backup: {backup_path}")
    else:
        shutil.copy2(glb_path, backup_path)
        print(f"  Created backup: {backup_path}")

    with open(glb_path, 'rb') as f:
        data = f.read()

    magic, version, length = struct.unpack_from('<III', data, 0)
    assert magic == 0x46546C67, "Not a GLB file"

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

    # Strip skin data
    if 'skins' in gltf:
        del gltf['skins']
        print("  Removed skins array")

    for node in gltf.get('nodes', []):
        if 'skin' in node:
            del node['skin']

    removed_accessors = set()
    for mesh in gltf.get('meshes', []):
        for prim in mesh.get('primitives', []):
            attrs = prim.get('attributes', {})
            if 'JOINTS_0' in attrs:
                removed_accessors.add(attrs['JOINTS_0'])
                del attrs['JOINTS_0']
            if 'WEIGHTS_0' in attrs:
                removed_accessors.add(attrs['WEIGHTS_0'])
                del attrs['WEIGHTS_0']

    print(f"  Stripped JOINTS_0/WEIGHTS_0 (removed accessor refs: {removed_accessors})")

    # Scale vertex positions (track already-scaled accessors to avoid double-scaling)
    scaled_accessors = set()
    for mesh in gltf.get('meshes', []):
        for prim in mesh.get('primitives', []):
            attrs = prim.get('attributes', {})
            if 'POSITION' in attrs:
                acc_idx = attrs['POSITION']
                if acc_idx in scaled_accessors:
                    continue
                scaled_accessors.add(acc_idx)
                accessor = gltf['accessors'][acc_idx]
                bv_idx = accessor['bufferView']
                bv = gltf['bufferViews'][bv_idx]

                byte_offset = bv.get('byteOffset', 0) + accessor.get('byteOffset', 0)
                cnt = accessor['count']
                stride = bv.get('byteStride', 12)

                for i in range(cnt):
                    pos = byte_offset + i * stride
                    x, y, z = struct.unpack_from('<fff', bin_chunk, pos)
                    struct.pack_into('<fff', bin_chunk, pos,
                                   x * scale_factor, y * scale_factor, z * scale_factor)

                if 'min' in accessor:
                    accessor['min'] = [v * scale_factor for v in accessor['min']]
                if 'max' in accessor:
                    accessor['max'] = [v * scale_factor for v in accessor['max']]

                print(f"  Scaled POSITION accessor {acc_idx}: {cnt} vertices * {scale_factor}")

    # Scale node translations
    for node in gltf.get('nodes', []):
        if 'translation' in node:
            node['translation'] = [v * scale_factor for v in node['translation']]

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
    print(f"  Wrote: {glb_path} ({len(output)} bytes, was {len(data)})")

if __name__ == "__main__":
    print("=== FIX 1: Swap materials to 2-texture techset ===")
    fix_materials()

    print("\n=== FIX 2+3: Scale to 0.65x + Strip skin data ===")
    view_glb = os.path.join(BASE, "model_export", "thundergun_view_lod0.glb")
    world_glb = os.path.join(BASE, "model_export", "thundergun_world_lod0.glb")

    fix_glb(view_glb, 0.65)
    if os.path.exists(world_glb):
        fix_glb(world_glb, 0.65)

    print("\n=== All 3 fixes applied! ===")
