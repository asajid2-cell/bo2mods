#!/usr/bin/env python3
"""Fix thundergun materials and apply gamma correction to BO3 color maps.

1. Restores all 14 material JSONs to vanilla T6 thundergun structure
   (techset mc_lit_sm_r0c0n0s0_zqq1fze7 with specularMap + normalMap + colorMap)
2. Applies gamma correction to color map DDS files (BO3 PBR albedo -> BO2 diffuse)
3. Converts all DDS to namespaced rogue_tg_*.iwi files
"""
import json
import os
import sys
import struct
import glob
import shutil
import subprocess
import tempfile

# Paths
MATERIALS_DIR = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\materials"
IMAGES_SRC = r"z:\Games\pluto_t6_full_game\_build\panzer_work\unlinked\images"
IMAGES_BUILD = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\images"
TEXCONV = r"z:\Games\pluto_t6_full_game\tools\texconv.exe"

# Brightness mode: "linear" multiplies RGB by BRIGHTNESS_FACTOR (preserves variation),
# "gamma" uses power curve (compresses dark values together - bad for BO3 PBR).
BRIGHTNESS_MODE = "linear"
BRIGHTNESS_FACTOR = 3.0  # Linear multiply factor for BO3 PBR albedo -> BO2 diffuse
GAMMA = 0.35  # Only used if BRIGHTNESS_MODE == "gamma"
FORCE_OPAQUE_ALPHA = True  # Force alpha=255 on color maps (BO3 DXT5 has bad alpha)

# Material-to-texture mapping (from vanilla zone_dump)
# Key: material suffix, Value: (normalMap_image, colorMap_image)
MATERIAL_MAP = {
    "back_body_a": ("rogue_tg_back_body_a_n", "rogue_tg_back_body_a_c"),
    "back_body_b": ("rogue_tg_back_body_b_n", "rogue_tg_back_body_b_c"),
    "back_body_c": ("rogue_tg_back_body_b_n", "rogue_tg_back_body_b_c"),
    "control_box": ("rogue_tg_control_box_n", "rogue_tg_control_box_c"),
    "front_body_a": ("rogue_tg_front_body_a_n", "rogue_tg_front_body_a_c"),
    "front_body_b": ("rogue_tg_front_body_b_n", "rogue_tg_front_body_b_c"),
    "glass":       ("rogue_tg_front_body_a_n", "rogue_tg_front_body_a_c"),
    "glo":         ("rogue_tg_front_body_a_n", "rogue_tg_front_body_a_c"),
    "glow_1":      ("rogue_tg_front_body_a_n", "rogue_tg_front_body_a_c"),
    "glow_2":      ("rogue_tg_front_body_a_n", "rogue_tg_front_body_a_c"),
    "glow_3":      ("rogue_tg_front_body_a_n", "rogue_tg_front_body_a_c"),
    "glow_4":      ("rogue_tg_front_body_a_n", "rogue_tg_front_body_a_c"),
    "quickdraw":   ("rogue_tg_quickdraw_n", "rogue_tg_quickdraw_c"),
    "stock":       ("rogue_tg_stock_n", "rogue_tg_stock_c"),
}

# Vanilla T6 thundergun material template (from zone_dump)
VANILLA_TEMPLATE = {
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
    "layeredSurfaceTypes": 536870925,
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
        0, 1, 2, -1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2, 2, 2, 2, -1, -1, -1, -1, -1, -1,
        3, -1, 2, 4
    ],
    "stateFlags": 121,
    "surfaceFlags": 13631488,
    "surfaceTypeBits": 4096,
    "techniqueSet": "mc_lit_sm_r0c0n0_2z223015",
    "textureAtlas": {"columns": 1, "rows": 1},
}

SAMPLER_STATE = {
    "clampU": False,
    "clampV": False,
    "clampW": False,
    "filter": "aniso4x",
    "mipMap": "linear"
}

# ---- IWI constants ----
IWI_HEADER_SIZE = 64
IWI_MAGIC = b"IWi"
IWI_VERSION = 0x1B
IWI_FORMAT_DXT5 = 0x0D
IWI_FORMAT_DXN = 0x0E
DDS_MAGIC = b"DDS "
DDS_HEADER_SIZE = 124
DXGI_FORMAT_BC5_UNORM = 83
DXGI_FORMAT_BC5_SNORM = 84


def make_texture_entry(name, image, semantic):
    return {
        "image": image,
        "isMatureContent": False,
        "name": name,
        "samplerState": dict(SAMPLER_STATE),
        "semantic": semantic
    }


def fix_materials():
    """Restore all 14 material JSONs to vanilla thundergun structure."""
    print("=" * 60)
    print("STEP 1: Restoring material JSONs to vanilla structure")
    print("=" * 60)

    for suffix, (normal_img, color_img) in MATERIAL_MAP.items():
        mtl_name = f"mtl_rogue_tg_{suffix}"
        mtl_path = os.path.join(MATERIALS_DIR, f"{mtl_name}.json")

        material = dict(VANILLA_TEMPLATE)
        material["constants"] = list(VANILLA_TEMPLATE["constants"])
        material["stateBits"] = list(VANILLA_TEMPLATE["stateBits"])
        material["stateBitsEntry"] = list(VANILLA_TEMPLATE["stateBitsEntry"])
        material["textures"] = [
            make_texture_entry("normalMap", normal_img, "normalMap"),
            make_texture_entry("colorMap", color_img, "colorMap"),
        ]

        with open(mtl_path, "w", newline="\n") as f:
            json.dump(material, f, indent=4)

        print(f"  {mtl_name}: techset={VANILLA_TEMPLATE['techniqueSet']}, textures={len(material['textures'])}")

    print(f"\n  Fixed {len(MATERIAL_MAP)} materials")


def read_dds(path):
    """Read a DDS file, handling both standard and DX10 extended headers."""
    with open(path, "rb") as f:
        magic = f.read(4)
        assert magic == DDS_MAGIC, f"Not a DDS file: {path}"
        header = f.read(DDS_HEADER_SIZE)
        height = struct.unpack_from("<I", header, 8)[0]
        width = struct.unpack_from("<I", header, 12)[0]
        mip_count = struct.unpack_from("<I", header, 24)[0]
        pf_fourcc = header[80:84]

        if pf_fourcc == b"DX10":
            dx10_header = f.read(20)
            dxgi_format = struct.unpack_from("<I", dx10_header, 0)[0]
            if dxgi_format in (DXGI_FORMAT_BC5_UNORM, DXGI_FORMAT_BC5_SNORM):
                iwi_format = IWI_FORMAT_DXN
            else:
                iwi_format = IWI_FORMAT_DXT5
        elif pf_fourcc == b"DXT5":
            iwi_format = IWI_FORMAT_DXT5
        else:
            iwi_format = IWI_FORMAT_DXT5

        all_data = f.read()

    mips = []
    offset = 0
    w, h = width, height
    for i in range(mip_count):
        bw = max(1, w // 4)
        bh = max(1, h // 4)
        mip_size = bw * bh * 16
        mip_data = all_data[offset:offset + mip_size]
        mips.append((w, h, mip_data))
        offset += mip_size
        w = max(1, w // 2)
        h = max(1, h // 2)

    return width, height, mips, iwi_format


def create_iwi(width, height, mips, iwi_format, output_path):
    """Create a T6 IWI file from mip data."""
    num_mips = len(mips)
    picmip = [0] * 8
    for i in range(8):
        if i < num_mips:
            data_size = sum(len(mips[j][2]) for j in range(i, num_mips))
            picmip[i] = IWI_HEADER_SIZE + data_size
        else:
            picmip[i] = IWI_HEADER_SIZE + len(mips[-1][2])

    header = bytearray(IWI_HEADER_SIZE)
    header[0:3] = IWI_MAGIC
    header[3] = IWI_VERSION
    header[4] = iwi_format
    header[5] = 0x00
    struct.pack_into("<H", header, 6, width)
    struct.pack_into("<H", header, 8, height)
    struct.pack_into("<H", header, 10, 1)
    for i in range(8):
        struct.pack_into("<I", header, 32 + i * 4, picmip[i])

    with open(output_path, "wb") as f:
        f.write(header)
        for w, h, data in reversed(mips):
            f.write(data)

    total_size = IWI_HEADER_SIZE + sum(len(m[2]) for m in mips)
    return total_size


def brighten_color_map(src_dds, dst_dds, temp_dir):
    """Decompress DDS, apply brightness correction to RGB, recompress to DXT5 DDS.

    Uses texconv for decompression/recompression and PIL/numpy for correction.
    Supports two modes:
    - "linear": multiply RGB by BRIGHTNESS_FACTOR (preserves relative variation)
    - "gamma": power curve (compresses dark differences - usually bad for PBR albedo)
    """
    from PIL import Image
    import numpy as np

    basename = os.path.splitext(os.path.basename(src_dds))[0]

    # Decompress DDS to PNG using texconv
    decomp_dir = os.path.join(temp_dir, "decomp")
    os.makedirs(decomp_dir, exist_ok=True)
    result = subprocess.run(
        [TEXCONV, "-ft", "png", "-y", "-o", decomp_dir, src_dds],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        print(f"    texconv decompress failed: {result.stderr}")
        return False

    png_path = os.path.join(decomp_dir, f"{basename}.png")
    if not os.path.exists(png_path):
        print(f"    PNG not found after decompress: {png_path}")
        return False

    # Apply brightness correction to RGB channels only
    img = Image.open(png_path)
    arr = np.array(img, dtype=np.float32)

    if arr.ndim == 3 and arr.shape[2] >= 3:
        rgb = arr[:, :, :3]
        if BRIGHTNESS_MODE == "linear":
            rgb = rgb * BRIGHTNESS_FACTOR
        else:  # gamma
            rgb = np.power(rgb / 255.0, GAMMA) * 255.0
        arr[:, :, :3] = np.clip(rgb, 0, 255)
        # Force alpha to 255 - BO3 DXT5 color maps have bad alpha (some pixels alpha=0)
        # which causes missing geometry in T6's shader
        if FORCE_OPAQUE_ALPHA and arr.shape[2] == 4:
            arr[:, :, 3] = 255.0
    else:
        print(f"    Unexpected image shape: {arr.shape}")
        return False

    # Save corrected PNG
    corrected_dir = os.path.join(temp_dir, "corrected")
    os.makedirs(corrected_dir, exist_ok=True)
    corrected_png = os.path.join(corrected_dir, f"{basename}.png")
    Image.fromarray(arr.astype(np.uint8)).save(corrected_png)

    # Recompress to DXT5 DDS using texconv
    recomp_dir = os.path.join(temp_dir, "recomp")
    os.makedirs(recomp_dir, exist_ok=True)
    result = subprocess.run(
        [TEXCONV, "-f", "BC3_UNORM", "-y", "-m", "0", "-o", recomp_dir, corrected_png],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        print(f"    texconv recompress failed: {result.stderr}")
        return False

    recomp_dds = os.path.join(recomp_dir, f"{basename}.dds")
    if not os.path.exists(recomp_dds):
        print(f"    Recompressed DDS not found: {recomp_dds}")
        return False

    shutil.copy2(recomp_dds, dst_dds)
    return True


def create_zero_gloss_specular(output_path):
    """Create a 4x4 DXT5 IWI with RGBA=(0,0,0,0) — zero specular color AND zero gloss.

    In T6's shader, specular alpha = glossiness. Alpha=255 means max gloss (chrome).
    We need alpha=0 for matte/diffuse-only appearance.

    DXT5 block for all-zero RGBA: 16 bytes of zeros (alpha endpoints=0, color endpoints=0).
    Must include all 3 mip levels (4x4, 2x2, 1x1) to pass OAT's picmip validation.
    """
    # Each mip level = 1 DXT5 block (minimum) = 16 bytes of zeros
    block_zero = b'\x00' * 16
    mips = [(4, 4, block_zero), (2, 2, block_zero), (1, 1, block_zero)]
    return create_iwi(4, 4, mips, IWI_FORMAT_DXT5, output_path)


def process_images(gamma=None):
    """Convert all DDS files to namespaced IWI, with brightness correction on color maps."""
    print(f"\n{'=' * 60}")
    print(f"STEP 2: Processing images ({BRIGHTNESS_MODE} mode, factor={BRIGHTNESS_FACTOR})")
    print("=" * 60)

    os.makedirs(IMAGES_BUILD, exist_ok=True)

    temp_dir = os.path.join(os.path.dirname(IMAGES_BUILD), "temp_gamma")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    dds_files = sorted(glob.glob(os.path.join(IMAGES_SRC, "tg_*.dds")))
    print(f"  Found {len(dds_files)} source DDS files")

    total_bytes = 0
    for dds_path in dds_files:
        src_name = os.path.splitext(os.path.basename(dds_path))[0]  # e.g. "tg_front_body_a_c"
        dst_name = f"rogue_{src_name}"  # e.g. "rogue_tg_front_body_a_c"
        iwi_path = os.path.join(IMAGES_BUILD, f"{dst_name}.iwi")

        is_color_map = src_name.endswith("_c")
        is_specular = "specular" in src_name

        if is_specular:
            # Specular map: create zero-gloss version (RGBA=0,0,0,0)
            # BO3 specular has alpha=255 (max gloss) which causes chrome in T6
            sz = create_zero_gloss_specular(iwi_path)
            total_bytes += sz
            print(f"  {dst_name:40s} 4x4 ZERO GLOSS specular -> {sz:,}b")
        elif is_color_map:
            # Brighten: DDS -> PNG -> correct -> PNG -> DXT5 DDS -> IWI
            corrected_dds = os.path.join(temp_dir, f"{src_name}_corrected.dds")
            ok = brighten_color_map(dds_path, corrected_dds, temp_dir)
            if ok:
                width, height, mips, iwi_format = read_dds(corrected_dds)
                sz = create_iwi(width, height, mips, iwi_format, iwi_path)
                total_bytes += sz
                print(f"  {dst_name:40s} {width}x{height} {len(mips)} mips {BRIGHTNESS_MODE}x{BRIGHTNESS_FACTOR} -> {sz:,}b")
            else:
                # Fallback: use original DDS
                print(f"  WARNING: Brightness correction failed for {src_name}, using original")
                width, height, mips, iwi_format = read_dds(dds_path)
                sz = create_iwi(width, height, mips, iwi_format, iwi_path)
                total_bytes += sz
        else:
            # Normal maps and specular: direct DDS -> IWI, no gamma
            width, height, mips, iwi_format = read_dds(dds_path)
            sz = create_iwi(width, height, mips, iwi_format, iwi_path)
            total_bytes += sz
            fmt_name = "BC5/DXN" if iwi_format == IWI_FORMAT_DXN else "DXT5/BC3"
            print(f"  {dst_name:40s} {width}x{height} {len(mips)} mips {fmt_name} -> {sz:,}b")

    # Clean up temp directory
    shutil.rmtree(temp_dir, ignore_errors=True)

    print(f"\n  {len(dds_files)} IWI files created ({total_bytes:,} bytes total)")
    return True


def main():
    print("Thundergun Texture Fix")
    print("=" * 60)
    print(f"  Brightness: {BRIGHTNESS_MODE} x{BRIGHTNESS_FACTOR}")
    print(f"  Materials dir: {MATERIALS_DIR}")
    print(f"  Images source: {IMAGES_SRC}")
    print(f"  Images build:  {IMAGES_BUILD}")
    print()

    # Step 1: Fix materials
    fix_materials()

    # Step 2: Process images with brightness correction
    process_images()

    print(f"\n{'=' * 60}")
    print("DONE! Materials fixed + gamma-corrected IWIs generated.")
    print("Run two_phase_build.py to build and deploy the zone.")
    print("=" * 60)


if __name__ == "__main__":
    main()
