"""
Fix thundergun materials (trivial -> mc_lit_sm skinned) and weapon projectile behavior.
"""
import json
from pathlib import Path

ROOT = Path(r"z:\Games\pluto_t6_full_game")
WORK = ROOT / "_build/panzer_work/so_zsurvival_zm_transit"
MAT_DIR = WORK / "materials"
ZONE_SRC = WORK / "zone_source/so_zsurvival_zm_transit.zone"

# Template: proper T6 weapon material properties (from a real T6 weapon material)
# Uses mc_lit_sm_r0c0n0 techset = model_cached + lit + shadow + colorMap + normalMap
TECHSET = "mc_lit_sm_r0c0n0_2z223015"

MATERIAL_TEMPLATE = {
    "$schema": "http://openassettools.dev/schema/material.v1.json",
    "_game": "t6",
    "_type": "material",
    "_version": 1,
    "cameraRegion": "litOpaque",
    "constants": [],
    "contents": 1,
    "gameFlags": ["10", "CASTS_SHADOW"],
    "layeredSurfaceTypes": 536870912,
    "sortKey": 4,
    "stateBits": [
        {
            "alphaTest": "disabled", "blendOpAlpha": "disabled", "blendOpRgb": "disabled",
            "colorWriteAlpha": False, "colorWriteRgb": False, "cullFace": "back",
            "depthTest": "less_equal", "depthWrite": True,
            "dstBlendAlpha": "zero", "dstBlendRgb": "zero",
            "polygonOffset": "offset0", "polymodeLine": False,
            "srcBlendAlpha": "one", "srcBlendRgb": "one",
            "stencilFront": {"fail": "keep", "func": "equal", "pass": "keep", "zfail": "keep"}
        },
        {
            "alphaTest": "disabled", "blendOpAlpha": "disabled", "blendOpRgb": "disabled",
            "colorWriteAlpha": False, "colorWriteRgb": False, "cullFace": "back",
            "depthTest": "less_equal", "depthWrite": True,
            "dstBlendAlpha": "zero", "dstBlendRgb": "zero",
            "polygonOffset": "offsetShadowmap", "polymodeLine": False,
            "srcBlendAlpha": "one", "srcBlendRgb": "one"
        },
        {
            "alphaTest": "disabled", "blendOpAlpha": "disabled", "blendOpRgb": "disabled",
            "colorWriteAlpha": True, "colorWriteRgb": True, "cullFace": "back",
            "depthTest": "less_equal", "depthWrite": True,
            "dstBlendAlpha": "zero", "dstBlendRgb": "zero",
            "polygonOffset": "offset0", "polymodeLine": False,
            "srcBlendAlpha": "one", "srcBlendRgb": "one"
        },
        {
            "alphaTest": "disabled", "blendOpAlpha": "disabled", "blendOpRgb": "disabled",
            "colorWriteAlpha": False, "colorWriteRgb": True, "cullFace": "back",
            "depthTest": "less_equal", "depthWrite": False,
            "dstBlendAlpha": "zero", "dstBlendRgb": "zero",
            "polygonOffset": "offset2", "polymodeLine": True,
            "srcBlendAlpha": "one", "srcBlendRgb": "one"
        },
        {
            "alphaTest": "disabled", "blendOpAlpha": "disabled", "blendOpRgb": "add",
            "colorWriteAlpha": True, "colorWriteRgb": True, "cullFace": "back",
            "depthTest": "less_equal", "depthWrite": True,
            "dstBlendAlpha": "zero", "dstBlendRgb": "one",
            "polygonOffset": "offset1", "polymodeLine": False,
            "srcBlendAlpha": "one", "srcBlendRgb": "one"
        }
    ],
    "stateBitsEntry": [0,1,2,-1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,-1,-1,-1,-1,-1,-1,3,-1,2,4],
    "stateFlags": 121,
    "surfaceFlags": 0,
    "surfaceTypeBits": 0,
    "techniqueSet": TECHSET,
    "textureAtlas": {"columns": 1, "rows": 1},
}

# Material name -> (colorMap image, normalMap image)
# Maps each thundergun material to its color+normal texture pair
MATERIAL_TEXTURES = {
    "mtl_wpn_t7_zmb_hd_thundergun_back_body_a":  ("i_wpn_t7_zmb_hd_thundergun_back_body_a_c", "i_wpn_t7_zmb_hd_thundergun_back_body_a_n"),
    "mtl_wpn_t7_zmb_hd_thundergun_back_body_b":  ("i_wpn_t7_zmb_hd_thundergun_back_body_b_c", "i_wpn_t7_zmb_hd_thundergun_back_body_b_n"),
    "mtl_wpn_t7_zmb_hd_thundergun_control_box":  ("i_wpn_t7_zmb_hd_thundergun_control_box_c", "i_wpn_t7_zmb_hd_thundergun_control_box_n"),
    "mtl_wpn_t7_zmb_hd_thundergun_front_body_a": ("i_wpn_t7_zmb_hd_thundergun_front_body_a_c", "i_wpn_t7_zmb_hd_thundergun_front_body_a_n"),
    "mtl_wpn_t7_zmb_hd_thundergun_front_body_b": ("i_wpn_t7_zmb_hd_thundergun_front_body_b_c", "i_wpn_t7_zmb_hd_thundergun_front_body_b_n"),
    "mtl_wpn_t7_zmb_hd_thundergun_quickdraw":    ("i_wpn_t7_zmb_hd_thundergun_quickdraw_c",    "i_wpn_t7_zmb_hd_thundergun_quickdraw_n"),
    "mtl_wpn_t7_zmb_hd_thundergun_stock":         ("i_wpn_t7_zmb_hd_thundergun_stock_c",         "i_wpn_t7_zmb_hd_thundergun_stock_n"),
}

# Materials that don't have textures (glow/glass materials) - use simple colorMap-only techset
GLOW_MATERIALS = [
    "mtl_wpn_t7_zmb_hd_thundergun_glass",
    "mtl_wpn_t7_zmb_hd_thundergun_glo",
    "mtl_wpn_t7_zmb_hd_thundergun_glow_1",
    "mtl_wpn_t7_zmb_hd_thundergun_glow_2",
    "mtl_wpn_t7_zmb_hd_thundergun_glow_3",
    "mtl_wpn_t7_zmb_hd_thundergun_glow_4",
]


def fix_materials():
    """Rewrite all thundergun material JSONs with proper skinned techset."""
    print("=== Fixing Materials ===")

    for mat_name, (color_img, normal_img) in MATERIAL_TEXTURES.items():
        mat_path = MAT_DIR / f"{mat_name}.json"
        mat = dict(MATERIAL_TEMPLATE)
        mat["textures"] = [
            {
                "image": normal_img,
                "isMatureContent": False,
                "name": "normalMap",
                "samplerState": {"clampU": False, "clampV": False, "clampW": False, "filter": "aniso4x", "mipMap": "linear"},
                "semantic": "normalMap"
            },
            {
                "image": color_img,
                "isMatureContent": False,
                "name": "colorMap",
                "samplerState": {"clampU": False, "clampV": False, "clampW": False, "filter": "aniso4x", "mipMap": "linear"},
                "semantic": "colorMap"
            }
        ]
        mat["debugName"] = mat_name
        mat_path.write_text(json.dumps(mat, indent=4), encoding="utf-8")
        print(f"  Fixed: {mat_name} -> {TECHSET}")

    # Glow/glass materials - use same techset but with just a default colorMap
    # (they'll appear as solid colored surfaces rather than glowing, but at least they'll render)
    for mat_name in GLOW_MATERIALS:
        mat_path = MAT_DIR / f"{mat_name}.json"
        if not mat_path.exists():
            print(f"  SKIP: {mat_name} (no file)")
            continue
        mat = dict(MATERIAL_TEMPLATE)
        mat["techniqueSet"] = TECHSET
        # Use the front_body color map as a fallback (closest match)
        mat["textures"] = [
            {
                "image": "i_wpn_t7_zmb_hd_thundergun_front_body_a_n",
                "isMatureContent": False,
                "name": "normalMap",
                "samplerState": {"clampU": False, "clampV": False, "clampW": False, "filter": "aniso4x", "mipMap": "linear"},
                "semantic": "normalMap"
            },
            {
                "image": "i_wpn_t7_zmb_hd_thundergun_front_body_a_c",
                "isMatureContent": False,
                "name": "colorMap",
                "samplerState": {"clampU": False, "clampV": False, "clampW": False, "filter": "aniso4x", "mipMap": "linear"},
                "semantic": "colorMap"
            }
        ]
        mat["debugName"] = mat_name
        mat_path.write_text(json.dumps(mat, indent=4), encoding="utf-8")
        print(f"  Fixed: {mat_name} -> {TECHSET} (fallback textures)")


def fix_weapon_files():
    """Fix weapon files: remove raygun projectile behavior."""
    print("\n=== Fixing Weapon Files ===")

    for wpn_name in ["thundergun_zm", "thundergun_upgraded_zm"]:
        wpn_path = WORK / "weapons" / wpn_name
        data = wpn_path.read_text(encoding="utf-8")

        # Change weaponType from projectile to bullet
        # Thundergun damage is handled by GSC, so bullet type with
        # no actual bullet damage works fine
        replacements = [
            # Weapon type: projectile -> bullet (no visible projectile)
            (r"\weaponType\projectile\\", r"\weaponType\bullet\\"),
            # Remove raygun projectile effects
            (r"\projExplosionEffect\misc/fx_exp_raygun_impact\\", r"\projExplosionEffect\\"),
            (r"\projExplosionEffect\misc/fx_exp_raygun_ug_impact\\", r"\projExplosionEffect\\"),
            (r"\projTrailEffect\misc/fx_trail_raygun_geotrail\\", r"\projTrailEffect\\"),
            (r"\projTrailEffect\misc/fx_trail_raygun_ug_geotrail\\", r"\projTrailEffect\\"),
            # Remove raygun projectile sound
            (r"\projectileSound\wpn_rgun_loop\\", r"\projectileSound\\"),
            # Remove raygun view/world flash effects
            (r"\viewFlashEffect\weapon/muzzleflashes/fx_raygun_view\\", r"\viewFlashEffect\\"),
            (r"\worldFlashEffect\weapon/muzzleflashes/fx_raygun_world\\", r"\worldFlashEffect\\"),
            (r"\viewFlashEffect\weapon/muzzleflashes/fx_raygun_ug_view\\", r"\viewFlashEffect\\"),
            (r"\worldFlashEffect\weapon/muzzleflashes/fx_raygun_ug_world\\", r"\worldFlashEffect\\"),
            # Zero out projectile-specific explosion damage (GSC handles damage)
            (r"\explosionInnerDamage\1500\\", r"\explosionInnerDamage\0\\"),
            (r"\explosionInnerDamage\2000\\", r"\explosionInnerDamage\0\\"),
            (r"\explosionOuterDamage\300\\", r"\explosionOuterDamage\0\\"),
            # Set projectile model to empty
            (r"\projectileModel\tag_flash\\", r"\projectileModel\\"),
        ]

        changes = 0
        for old, new in replacements:
            if old in data:
                data = data.replace(old, new)
                changes += 1

        wpn_path.write_text(data, encoding="utf-8")
        print(f"  {wpn_name}: {changes} fields fixed")

        # Verify
        if "projectile" in data.lower().split("weapontype")[1][:20] if "weapontype" in data.lower() else "":
            print(f"    WARNING: weaponType still contains 'projectile'")


def add_techset_to_zone():
    """Add the mc_lit_sm techset entry to zone source if not present."""
    print("\n=== Updating Zone Source ===")
    data = ZONE_SRC.read_text(encoding="utf-8")

    if TECHSET in data:
        print(f"  Techset {TECHSET} already in zone source")
        return

    # Add techset entry before the thundergun material entries
    marker = "// --- Thundergun weapon port"
    if marker in data:
        insert = f"techniqueset,,{TECHSET}\n{marker}"
        data = data.replace(marker, insert)
        ZONE_SRC.write_text(data, encoding="utf-8")
        print(f"  Added techset {TECHSET} to zone source")
    else:
        print(f"  WARNING: marker not found, appending")
        data += f"\ntechniqueset,,{TECHSET}\n"
        ZONE_SRC.write_text(data, encoding="utf-8")


def main():
    fix_materials()
    fix_weapon_files()
    add_techset_to_zone()

    # Copy weapon files to mod dirs
    print("\n=== Syncing weapon files to mod dirs ===")
    import shutil
    for wpn in ["thundergun_zm", "thundergun_upgraded_zm"]:
        src = WORK / "weapons" / wpn
        # Game mod dir
        dst1 = ROOT / "mods/zm_roguelike_panzer/weapons" / wpn
        shutil.copy2(str(src), str(dst1))
        # Plutonium storage
        dst2 = Path(r"C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\mods\zm_roguelike_panzer\weapons") / wpn
        shutil.copy2(str(src), str(dst2))
    print("  Weapon files synced")

    print("\nDone! Ready to recompile zone.")


if __name__ == "__main__":
    main()
