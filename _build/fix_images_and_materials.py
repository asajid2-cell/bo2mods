#!/usr/bin/env python3
"""
Fix thundergun images and materials:
1. Rename images from i_wpn_t7_zmb_hd_thundergun_* to tg_* (avoid loaded zone conflict)
2. Fix IWI format byte (0x0E = T6 DXT5, matching test.iwi)
3. Regenerate IWI files from DXT5 DDS with correct headers
4. Update all material JSON files with new image names
5. Update zone source with new image entries
"""
import struct
import os
import glob
import json
import re

# === CONFIG ===
BASE = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit"
IMAGES_DIR = os.path.join(BASE, "images")
DXT5_DIR = os.path.join(IMAGES_DIR, "dxt5")
MATERIALS_DIR = os.path.join(BASE, "materials")
ZONE_SOURCE = os.path.join(BASE, "zone_source", "so_zsurvival_zm_transit.zone")

# Old prefix -> new prefix
OLD_PREFIX = "i_wpn_t7_zmb_hd_thundergun_"
NEW_PREFIX = "tg_"

# T6 IWI header
IWI_HEADER_SIZE = 64
IWI_MAGIC = b"IWi"
IWI_VERSION = 0x1B
IWI_FORMAT_DXT5 = 0x0E  # T6 uses 0x0E for BC3/DXT5 (verified from test.iwi)
DDS_MAGIC = b"DDS "
DDS_HEADER_SIZE = 124


def read_dds(path):
    """Read a DXT5 DDS file and return width, height, mip data."""
    with open(path, "rb") as f:
        magic = f.read(4)
        assert magic == DDS_MAGIC, f"Not a DDS file: {path}"
        header = f.read(DDS_HEADER_SIZE)
        height = struct.unpack_from("<I", header, 8)[0]
        width = struct.unpack_from("<I", header, 12)[0]
        mip_count = struct.unpack_from("<I", header, 24)[0]
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

    return width, height, mips


def create_iwi(width, height, mips, output_path):
    """Create a T6 IWI file with correct headers."""
    reversed_mips = list(reversed(mips))
    total_data = sum(len(m[2]) for m in reversed_mips)
    num_mips = len(mips)

    picmip = [0] * 8
    for i in range(8):
        if i < num_mips:
            data_size = sum(len(mips[j][2]) for j in range(i, num_mips))
            picmip[i] = IWI_HEADER_SIZE + data_size
        else:
            picmip[i] = IWI_HEADER_SIZE

    header = bytearray(IWI_HEADER_SIZE)
    header[0:3] = IWI_MAGIC
    header[3] = IWI_VERSION
    header[4] = IWI_FORMAT_DXT5  # 0x0E for T6
    header[5] = 0x00
    struct.pack_into("<H", header, 6, width)
    struct.pack_into("<H", header, 8, height)
    struct.pack_into("<H", header, 10, 1)
    for i in range(8):
        struct.pack_into("<I", header, 32 + i * 4, picmip[i])

    with open(output_path, "wb") as f:
        f.write(header)
        for w, h, data in reversed_mips:
            f.write(data)

    return IWI_HEADER_SIZE + total_data


def rename_image(old_name):
    """Rename image from old prefix to new prefix."""
    return old_name.replace(OLD_PREFIX, NEW_PREFIX)


def main():
    # Step 1: Generate renamed IWI files from DXT5 DDS sources
    print("=== Step 1: Generate renamed IWI files ===")
    dds_files = sorted(glob.glob(os.path.join(DXT5_DIR, "*.dds")))

    # Also clean up old IWI and DDS files in images dir
    for f in glob.glob(os.path.join(IMAGES_DIR, "i_wpn_t7_zmb_hd_thundergun_*")):
        os.remove(f)
        print(f"  Removed old: {os.path.basename(f)}")

    for f in glob.glob(os.path.join(IMAGES_DIR, "tg_*")):
        os.remove(f)
        print(f"  Removed old tg_: {os.path.basename(f)}")

    image_rename_map = {}  # old_name -> new_name
    for dds_path in dds_files:
        old_name = os.path.splitext(os.path.basename(dds_path))[0]
        new_name = rename_image(old_name)
        image_rename_map[old_name] = new_name

        iwi_path = os.path.join(IMAGES_DIR, f"{new_name}.iwi")
        width, height, mips = read_dds(dds_path)
        size = create_iwi(width, height, mips, iwi_path)
        print(f"  {new_name}.iwi ({size} bytes, {width}x{height}, {len(mips)} mips, fmt=0x{IWI_FORMAT_DXT5:02X})")

    print(f"\nImage rename map ({len(image_rename_map)} images):")
    for old, new in sorted(image_rename_map.items()):
        print(f"  {old} -> {new}")

    # Step 2: Update material JSON files
    print("\n=== Step 2: Update material files ===")
    mat_files = sorted(glob.glob(os.path.join(MATERIALS_DIR, "mtl_wpn_t7_zmb_hd_thundergun_*.json")))
    for mat_path in mat_files:
        with open(mat_path, 'r') as f:
            content = f.read()

        modified = False
        for old_name, new_name in image_rename_map.items():
            if old_name in content:
                content = content.replace(old_name, new_name)
                modified = True

        if modified:
            with open(mat_path, 'w') as f:
                f.write(content)
            print(f"  Updated: {os.path.basename(mat_path)}")

    # Step 3: Update zone source
    print("\n=== Step 3: Update zone source ===")
    with open(ZONE_SOURCE, 'r') as f:
        zone_content = f.read()

    for old_name, new_name in image_rename_map.items():
        zone_content = zone_content.replace(f"image,{old_name}", f"image,{new_name}")

    with open(ZONE_SOURCE, 'w') as f:
        f.write(zone_content)
    print("  Zone source updated with new image names")

    print("\n=== Done! ===")
    print(f"Renamed {len(image_rename_map)} images: {OLD_PREFIX}* -> {NEW_PREFIX}*")
    print(f"Format byte: 0x{IWI_FORMAT_DXT5:02X} (matching T6 test.iwi)")


if __name__ == "__main__":
    main()
