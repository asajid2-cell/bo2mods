#!/usr/bin/env python3
"""Binary search for minimum VIRTUAL block size for the full 28-xanim zone."""
import struct
import os
import subprocess
import sys
import glob as globmod

sys.path.insert(0, os.path.dirname(__file__))
from compile_xanim_zone import (
    XChunkWriter, T6_ZONE_MAGIC_UNSIGNED, T6_ZONE_VERSION,
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
    return "overflowed" not in output.lower() and result.returncode == 0

def main():
    xanim_dir = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\xanim_export"
    pattern = os.path.join(xanim_dir, "vm_thunder_gun_*.xanim_export")
    files = sorted(globmod.glob(pattern))
    anims = [parse_xanim_export(f) for f in files]

    print(f"Building zone with {len(anims)} xanims...")
    raw = build_zone_data(anims, "thundergun_xanims")
    computed_virtual = struct.unpack_from('<I', raw, 8 + BLOCK_VIRTUAL * 4)[0]
    print(f"Computed VIRTUAL={computed_virtual}")

    ff = os.path.join(OUTPUT_DIR, "thundergun_xanims.ff")

    # Binary search: lo=computed_virtual, hi=1MB
    lo, hi = computed_virtual, 1024*1024

    # First verify computed fails
    write_zone_file(raw, "thundergun_xanims", ff)
    if test_load(ff):
        print(f"Computed VIRTUAL={computed_virtual} already works!")
        return

    print(f"Computed VIRTUAL={computed_virtual} FAILS. Binary searching [{lo}, {hi}]...")

    while lo < hi:
        mid = (lo + hi) // 2
        patched = bytearray(raw)
        struct.pack_into('<I', patched, 8 + BLOCK_VIRTUAL * 4, mid)
        write_zone_file(bytes(patched), "thundergun_xanims", ff)
        if test_load(ff):
            hi = mid
        else:
            lo = mid + 1
        print(f"  [{lo}, {hi}] mid={mid} -> {'OK' if hi == mid else 'FAIL'}")

    print(f"\nMinimum VIRTUAL = {lo}")
    print(f"Computed was     = {computed_virtual}")
    print(f"Shortfall        = {lo - computed_virtual}")

    # Analyze: how much per insert pointer and per string
    # From build: 185 insert ptrs, 43 strings, 28 assets
    # virtual_block_offset was the data part
    # Actual needed = lo
    # Per insert pointer overhead: (lo - virtual_data_only) / 185

if __name__ == "__main__":
    main()
