"""
Update all 14 thundergun material JSONs to use the BO2 raygun technique set.
Changes:
- techniqueSet: mc_lit_sm_b0c0_fw0jf955 -> mc_lit_sm_r0c0n0s0_zqq1fze7
- Add specularMap texture (reusing colorMap image as specular)
- Add occlusionAmount constant
- Add CASTS_SHADOW gameFlag
- Fix normalMap sampler states
- Update layeredSurfaceTypes to match raygun
"""
import json
import os
import glob

materials_dir = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\materials"

for mat_path in glob.glob(os.path.join(materials_dir, "mtl_wpn_t7_zmb_hd_thundergun_*.json")):
    with open(mat_path, 'r') as f:
        mat = json.load(f)

    # Find the colorMap image name
    color_image = None
    for tex in mat["textures"]:
        if tex["name"] == "colorMap":
            color_image = tex["image"]
            break

    if not color_image:
        print(f"WARNING: No colorMap found in {os.path.basename(mat_path)}")
        continue

    # 1. Update techniqueSet to known-good BO2 weapon technique
    mat["techniqueSet"] = "mc_lit_sm_r0c0n0s0_zqq1fze7"

    # 2. Add occlusionAmount constant (matches raygun)
    mat["constants"] = [
        {
            "literal": [1.0, 1.0, 1.0, 1.0],
            "name": "occlusionAmount"
        }
    ]

    # 3. Add CASTS_SHADOW to gameFlags
    mat["gameFlags"] = ["10", "CASTS_SHADOW"]

    # 4. Update layeredSurfaceTypes to match raygun
    mat["layeredSurfaceTypes"] = 536870925

    # 5. Create specularMap texture entry (reuse colorMap image)
    specular_tex = {
        "image": color_image,
        "isMatureContent": False,
        "name": "specularMap",
        "samplerState": {
            "clampU": False,
            "clampV": False,
            "clampW": False,
            "filter": "aniso4x",
            "mipMap": "linear"
        },
        "semantic": "specularMap"
    }

    # 6. Fix normalMap sampler state (some had nearest/disabled)
    for tex in mat["textures"]:
        if tex["name"] == "normalMap":
            tex["samplerState"]["filter"] = "aniso4x"
            tex["samplerState"]["mipMap"] = "linear"

    # 7. Rebuild textures in raygun order: specularMap, normalMap, colorMap
    new_textures = [specular_tex]
    for tex in mat["textures"]:
        if tex["name"] == "normalMap":
            new_textures.append(tex)
            break
    for tex in mat["textures"]:
        if tex["name"] == "colorMap":
            new_textures.append(tex)
            break

    mat["textures"] = new_textures

    with open(mat_path, 'w') as f:
        json.dump(mat, f, indent=4)

    print(f"Updated: {os.path.basename(mat_path)} (specular={color_image})")

print("\nDone! All 14 materials updated to mc_lit_sm_r0c0n0s0_zqq1fze7")
