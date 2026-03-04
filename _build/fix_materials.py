#!/usr/bin/env python3
"""Fix all thundergun materials to use the raygun's known-working techset format."""
import json
import os

MATERIALS_DIR = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\materials"

# Raygun techset - known to work in T6 for weapon viewmodels
TECHSET = "mc_lit_sm_r0c0n0s0_zqq1fze7"

# Material -> (normalMap_image, colorMap_image)
# For specularMap, we'll use the colorMap image as a placeholder
MATERIAL_TEXTURES = {
    "mtl_wpn_t7_zmb_hd_thundergun_back_body_a": ("i_wpn_t7_zmb_hd_thundergun_back_body_a_n", "i_wpn_t7_zmb_hd_thundergun_back_body_a_c"),
    "mtl_wpn_t7_zmb_hd_thundergun_back_body_b": ("i_wpn_t7_zmb_hd_thundergun_back_body_b_n", "i_wpn_t7_zmb_hd_thundergun_back_body_b_c"),
    "mtl_wpn_t7_zmb_hd_thundergun_back_body_c": ("i_wpn_t7_zmb_hd_thundergun_back_body_b_n", "i_wpn_t7_zmb_hd_thundergun_back_body_b_c"),  # reuses back_body_b
    "mtl_wpn_t7_zmb_hd_thundergun_control_box": ("i_wpn_t7_zmb_hd_thundergun_control_box_n", "i_wpn_t7_zmb_hd_thundergun_control_box_c"),
    "mtl_wpn_t7_zmb_hd_thundergun_front_body_a": ("i_wpn_t7_zmb_hd_thundergun_front_body_a_n", "i_wpn_t7_zmb_hd_thundergun_front_body_a_c"),
    "mtl_wpn_t7_zmb_hd_thundergun_front_body_b": ("i_wpn_t7_zmb_hd_thundergun_front_body_b_n", "i_wpn_t7_zmb_hd_thundergun_front_body_b_c"),
    "mtl_wpn_t7_zmb_hd_thundergun_glass":        ("i_wpn_t7_zmb_hd_thundergun_front_body_a_n", "i_wpn_t7_zmb_hd_thundergun_front_body_a_c"),
    "mtl_wpn_t7_zmb_hd_thundergun_glo":          ("i_wpn_t7_zmb_hd_thundergun_front_body_a_n", "i_wpn_t7_zmb_hd_thundergun_front_body_a_c"),
    "mtl_wpn_t7_zmb_hd_thundergun_glow_1":       ("i_wpn_t7_zmb_hd_thundergun_front_body_a_n", "i_wpn_t7_zmb_hd_thundergun_front_body_a_c"),
    "mtl_wpn_t7_zmb_hd_thundergun_glow_2":       ("i_wpn_t7_zmb_hd_thundergun_front_body_a_n", "i_wpn_t7_zmb_hd_thundergun_front_body_a_c"),
    "mtl_wpn_t7_zmb_hd_thundergun_glow_3":       ("i_wpn_t7_zmb_hd_thundergun_front_body_a_n", "i_wpn_t7_zmb_hd_thundergun_front_body_a_c"),
    "mtl_wpn_t7_zmb_hd_thundergun_glow_4":       ("i_wpn_t7_zmb_hd_thundergun_front_body_a_n", "i_wpn_t7_zmb_hd_thundergun_front_body_a_c"),
    "mtl_wpn_t7_zmb_hd_thundergun_quickdraw":    ("i_wpn_t7_zmb_hd_thundergun_quickdraw_n", "i_wpn_t7_zmb_hd_thundergun_quickdraw_c"),
    "mtl_wpn_t7_zmb_hd_thundergun_stock":        ("i_wpn_t7_zmb_hd_thundergun_stock_n", "i_wpn_t7_zmb_hd_thundergun_stock_c"),
}

SAMPLER_STATE = {
    "clampU": False,
    "clampV": False,
    "clampW": False,
    "filter": "aniso4x",
    "mipMap": "linear"
}

# Exact raygun stateBits (copy from mtl_t6_wpn_zmb_raygun.json)
STATE_BITS = [
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
]

STATE_BITS_ENTRY = [
    0, 1, 2, -1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, -1, -1, -1, -1, -1, -1,
    3, -1, 2, 4
]


def make_material(mat_name, normal_img, color_img):
    """Create a material JSON matching the raygun format exactly."""
    return {
        "$schema": "http://openassettools.dev/schema/material.v1.json",
        "_game": "t6",
        "_type": "material",
        "_version": 1,
        "cameraRegion": "litOpaque",
        "constants": [
            {
                "literal": [1.0, 1.0, 1.0, 1.0],
                "name": "occlusionAmount"
            }
        ],
        "contents": 1,
        "gameFlags": ["10", "CASTS_SHADOW"],
        "layeredSurfaceTypes": 536870912,
        "sortKey": 4,
        "stateBits": STATE_BITS,
        "stateBitsEntry": STATE_BITS_ENTRY,
        "stateFlags": 121,
        "surfaceFlags": 0,
        "surfaceTypeBits": 0,
        "techniqueSet": TECHSET,
        "textureAtlas": {"columns": 1, "rows": 1},
        "textures": [
            {
                "image": color_img,  # use colorMap as specular placeholder
                "isMatureContent": False,
                "name": "specularMap",
                "samplerState": dict(SAMPLER_STATE),
                "semantic": "specularMap"
            },
            {
                "image": normal_img,
                "isMatureContent": False,
                "name": "normalMap",
                "samplerState": dict(SAMPLER_STATE),
                "semantic": "normalMap"
            },
            {
                "image": color_img,
                "isMatureContent": False,
                "name": "colorMap",
                "samplerState": dict(SAMPLER_STATE),
                "semantic": "colorMap"
            }
        ],
        "debugName": mat_name
    }


def main():
    for mat_name, (normal_img, color_img) in MATERIAL_TEXTURES.items():
        mat = make_material(mat_name, normal_img, color_img)
        path = os.path.join(MATERIALS_DIR, f"{mat_name}.json")
        with open(path, 'w') as f:
            json.dump(mat, f, indent=4)
        print(f"  Updated: {mat_name}")

    print(f"\nAll {len(MATERIAL_TEXTURES)} materials updated to use techset: {TECHSET}")
    print("Texture order: specularMap -> normalMap -> colorMap (matching raygun)")


if __name__ == "__main__":
    main()
