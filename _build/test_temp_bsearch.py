#!/usr/bin/env python3
"""Binary search for minimum TEMP block size, with VIRTUAL fixed at 1MB."""
import struct
import os
import subprocess
import sys
import glob as globmod

sys.path.insert(0, os.path.dirname(__file__))
from compile_xanim_zone import (
    XFILE_BLOCK_COUNT, BLOCK_TEMP, BLOCK_VIRTUAL,
    parse_xanim_export, build_zone_data, write_zone_file
)

LINKER = r"z:\Games\pluto_t6_full_game\tools\oat\Linker.exe"
OUTPUT_DIR = r"z:\Games\pluto_t6_full_game\_build\panzer_work\output"

def test_load(zone_path):
    test_dir = os.path.join(OUTPUT_DIR, "test_zone")
    os.makedirs(os.path.join(test_dir, "zone_source"), exist_ok=True)
    with open(os.path.join(test_dir, "zone_source", "load_test.zone"), 'w') as f:
        f.write("// Empty\n")
    args = [LINKER, "--base-folder", test_dir, "--output-folder", OUTPUT_DIR,
            "--load", zone_path, "load_test"]
    result = subprocess.run(args, capture_output=True, text=True, timeout=60)
    output = result.stdout + result.stderr
    return "overflowed" not in output.lower() and "failed" not in output.lower() and result.returncode == 0

def main():
    xanim_dir = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\xanim_export"
    pattern = os.path.join(xanim_dir, "vm_thunder_gun_*.xanim_export")
    files = sorted(globmod.glob(pattern))
    anims = [parse_xanim_export(f) for f in files]

    raw = build_zone_data(anims, "thundergun_xanims")
    computed_temp = struct.unpack_from('<I', raw, 8 + BLOCK_TEMP * 4)[0]
    total_size = struct.unpack_from('<I', raw, 0)[0]
    print(f"Computed TEMP={computed_temp}, totalSize={total_size}")

    ff = os.path.join(OUTPUT_DIR, "thundergun_xanims.ff")

    # Test with TEMP=0, VIRTUAL=1MB
    print("\n--- Test TEMP=0, VIRTUAL=1MB ---")
    patched = bytearray(raw)
    struct.pack_into('<I', patched, 8 + BLOCK_TEMP * 4, 0)
    struct.pack_into('<I', patched, 8 + BLOCK_VIRTUAL * 4, 1024*1024)
    write_zone_file(bytes(patched), "thundergun_xanims", ff)
    if test_load(ff):
        print("  TEMP=0 works! XAnimParts goes entirely to VIRTUAL.")
    else:
        print("  TEMP=0 fails. XAnimParts needs TEMP space.")

        # Binary search for minimum TEMP
        lo, hi = 0, computed_temp
        while lo < hi:
            mid = (lo + hi) // 2
            p = bytearray(raw)
            struct.pack_into('<I', p, 8 + BLOCK_TEMP * 4, mid)
            struct.pack_into('<I', p, 8 + BLOCK_VIRTUAL * 4, 1024*1024)
            write_zone_file(bytes(p), "thundergun_xanims", ff)
            if test_load(ff):
                hi = mid
            else:
                lo = mid + 1
            print(f"  [{lo}, {hi}]")
        print(f"\n  Minimum TEMP = {lo}")

    # Now try TEMP=computed, VIRTUAL=totalSize
    print(f"\n--- Test VIRTUAL=totalSize({total_size}) ---")
    patched = bytearray(raw)
    struct.pack_into('<I', patched, 8 + BLOCK_VIRTUAL * 4, total_size)
    write_zone_file(bytes(patched), "thundergun_xanims", ff)
    if test_load(ff):
        print(f"  VIRTUAL=totalSize works!")
    else:
        print(f"  VIRTUAL=totalSize fails.")

if __name__ == "__main__":
    main()
