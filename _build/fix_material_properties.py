"""
Fix thundergun material properties to match working raygun materials.
- Revert ~-g prefix on colorMap images (OAT doesn't support it for external IWIs)
- Fix surfaceFlags, surfaceTypeBits, layeredSurfaceTypes
"""
import json
import glob
import os

MATERIALS_DIR = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\materials"

# Values from the working raygun material
FIXES = {
    "surfaceFlags": 13631488,
    "surfaceTypeBits": 4096,
    "layeredSurfaceTypes": 536870925,
}

pattern = os.path.join(MATERIALS_DIR, "mtl_wpn_t7_zmb_hd_thundergun_*.json")
files = sorted(glob.glob(pattern))

print(f"Found {len(files)} thundergun material files")

for filepath in files:
    name = os.path.basename(filepath)
    with open(filepath, 'r') as f:
        mat = json.load(f)

    changes = []

    # Fix surface properties
    for key, target_val in FIXES.items():
        old_val = mat.get(key)
        if old_val != target_val:
            mat[key] = target_val
            changes.append(f"  {key}: {old_val} -> {target_val}")

    # REVERT ~-g prefix on colorMap images (OAT doesn't support compositing for external IWIs)
    for tex in mat.get("textures", []):
        if tex.get("semantic") == "colorMap":
            old_img = tex["image"]
            if old_img.startswith("~-g"):
                new_img = old_img[3:]  # Remove ~-g prefix
                tex["image"] = new_img
                changes.append(f"  colorMap image: {old_img} -> {new_img} (reverted ~-g)")

    if changes:
        with open(filepath, 'w') as f:
            json.dump(mat, f, indent=4)
        print(f"\n{name}:")
        for c in changes:
            print(c)
    else:
        print(f"\n{name}: no changes needed")

print("\nDone!")
