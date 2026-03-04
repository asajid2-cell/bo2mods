"""
Update all 14 thundergun materials to use tg_specular_black as specularMap
instead of the colorMap (which caused the chrome/metallic look).
"""
import json
import os
import glob

materials_dir = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\materials"

for mat_path in glob.glob(os.path.join(materials_dir, "mtl_wpn_t7_zmb_hd_thundergun_*.json")):
    with open(mat_path, 'r') as f:
        mat = json.load(f)

    for tex in mat["textures"]:
        if tex["name"] == "specularMap":
            old_image = tex["image"]
            tex["image"] = "tg_specular_black"
            print(f"{os.path.basename(mat_path)}: specular {old_image} -> tg_specular_black")
            break

    with open(mat_path, 'w') as f:
        json.dump(mat, f, indent=4)

print("\nDone!")
