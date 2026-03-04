#!/usr/bin/env python3
"""Test: recompile the full zone with huge VIRTUAL to check if it's size vs structure."""
import struct
import os
import subprocess
import sys

# Import our zone compiler
sys.path.insert(0, os.path.dirname(__file__))
from compile_xanim_zone import (
    XChunkWriter, T6_ZONE_MAGIC_UNSIGNED, T6_ZONE_VERSION,
    XFILE_BLOCK_COUNT, BLOCK_TEMP, BLOCK_VIRTUAL,
    parse_xanim_export, build_zone_data, write_zone_file
)

LINKER = r"z:\Games\pluto_t6_full_game\tools\oat\Linker.exe"
OUTPUT_DIR = r"z:\Games\pluto_t6_full_game\_build\panzer_work\output"

def patch_virtual_size(raw_data, new_virtual_size):
    """Patch the VIRTUAL block size in already-built raw zone data."""
    buf = bytearray(raw_data)
    # blockSizes start at offset 8 (after totalSize + externalSize)
    block_sizes_pos = 8
    struct.pack_into('<I', buf, block_sizes_pos + BLOCK_VIRTUAL * 4, new_virtual_size)
    return bytes(buf)


def test_load(zone_path):
    """Try to load the zone with OAT Linker."""
    test_dir = os.path.join(OUTPUT_DIR, "test_zone")
    os.makedirs(os.path.join(test_dir, "zone_source"), exist_ok=True)
    with open(os.path.join(test_dir, "zone_source", "load_test.zone"), 'w') as f:
        f.write("// Empty\n")

    args = [LINKER, "--verbose", "--base-folder", test_dir, "--output-folder", OUTPUT_DIR,
            "--load", zone_path, "load_test"]
    result = subprocess.run(args, capture_output=True, text=True, timeout=60)
    output = result.stdout + result.stderr
    return output, result.returncode


def main():
    import glob as globmod
    xanim_dir = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\xanim_export"
    pattern = os.path.join(xanim_dir, "vm_thunder_gun_*.xanim_export")
    files = sorted(globmod.glob(pattern))

    print(f"Found {len(files)} xanim files")

    # Parse all
    anims = []
    for f in files:
        from compile_xanim_zone import parse_xanim_export
        anim = parse_xanim_export(f)
        anims.append(anim)

    # Test 1: Single xanim (smallest) with huge VIRTUAL
    print("\n=== Test 1: Single xanim, VIRTUAL=1MB ===")
    raw1 = build_zone_data(anims[:1], "thundergun_xanims")
    raw1 = patch_virtual_size(raw1, 1024*1024)
    ff1 = os.path.join(OUTPUT_DIR, "thundergun_xanims.ff")
    write_zone_file(raw1, "thundergun_xanims", ff1)
    out, rc = test_load(ff1)
    print(f"  RC={rc}")
    if "overflowed" in out.lower():
        print("  OVERFLOW!")
    elif rc == 0:
        print("  OK!")
    else:
        # Print last few lines
        for line in out.strip().split('\n')[-5:]:
            print(f"  {line}")

    # Test 2: Full zone with huge VIRTUAL (1MB)
    print("\n=== Test 2: Full zone (28 xanims), VIRTUAL=1MB ===")
    raw2 = build_zone_data(anims, "thundergun_xanims")
    raw2 = patch_virtual_size(raw2, 1024*1024)
    write_zone_file(raw2, "thundergun_xanims", ff1)
    out, rc = test_load(ff1)
    print(f"  RC={rc}")
    if "overflowed" in out.lower():
        print("  OVERFLOW!")
    elif rc == 0:
        print("  OK!")
    else:
        for line in out.strip().split('\n')[-5:]:
            print(f"  {line}")

    # Test 3: Full zone with huge VIRTUAL AND huge TEMP
    print("\n=== Test 3: Full zone, VIRTUAL=1MB, TEMP=1MB ===")
    raw3 = bytearray(raw2)
    struct.pack_into('<I', raw3, 8 + BLOCK_TEMP * 4, 1024*1024)
    struct.pack_into('<I', raw3, 8 + BLOCK_VIRTUAL * 4, 1024*1024)
    raw3 = bytes(raw3)
    write_zone_file(raw3, "thundergun_xanims", ff1)
    out, rc = test_load(ff1)
    print(f"  RC={rc}")
    if "overflowed" in out.lower():
        print("  OVERFLOW!")
    elif rc == 0:
        print("  OK!")
    else:
        for line in out.strip().split('\n')[-5:]:
            print(f"  {line}")

    # Test 4: Full zone, ALL blocks = 1MB
    print("\n=== Test 4: Full zone, ALL blocks=1MB ===")
    raw4 = bytearray(raw2)
    for i in range(XFILE_BLOCK_COUNT):
        struct.pack_into('<I', raw4, 8 + i * 4, 1024*1024)
    raw4 = bytes(raw4)
    write_zone_file(raw4, "thundergun_xanims", ff1)
    out, rc = test_load(ff1)
    print(f"  RC={rc}")
    if "overflowed" in out.lower():
        print("  OVERFLOW!")
    elif rc == 0:
        print("  OK!")
    else:
        for line in out.strip().split('\n')[-10:]:
            print(f"  {line}")


if __name__ == "__main__":
    main()
