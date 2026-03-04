#!/usr/bin/env python3
"""Find exact VIRTUAL block size needed."""
import struct
import os
import subprocess
from compile_xanim_zone import (
    XChunkWriter, T6_ZONE_MAGIC_UNSIGNED, T6_ZONE_VERSION,
    ASSET_TYPE_XANIMPARTS
)

LINKER = r"z:\Games\pluto_t6_full_game\tools\oat\Linker.exe"
OUTPUT_DIR = r"z:\Games\pluto_t6_full_game\_build\panzer_work\output"

PTR_FOLLOWING = 0xFFFFFFFF
PTR_NULL = 0x00000000
XFILE_BLOCK_COUNT = 8
BLOCK_VIRTUAL = 5
BLOCK_TEMP = 0

def write_zone(raw_data, zone_name, output_path):
    xchunk = XChunkWriter(zone_name)
    xchunk.write_data(raw_data)
    encrypted = xchunk.get_output()
    with open(output_path, 'wb') as f:
        f.write(T6_ZONE_MAGIC_UNSIGNED)
        f.write(struct.pack('<I', T6_ZONE_VERSION))
        f.write(encrypted)
        padding = 0x40 - (f.tell() % 0x40)
        if padding < 0x40:
            padding += 0x40
        f.write(b'\x00' * padding)

def test_load(zone_path):
    test_dir = os.path.join(OUTPUT_DIR, "test_zone")
    os.makedirs(os.path.join(test_dir, "zone_source"), exist_ok=True)
    with open(os.path.join(test_dir, "zone_source", "load_test.zone"), 'w') as f:
        f.write("// Empty\n")
    args = [LINKER, "--base-folder", test_dir, "--output-folder", OUTPUT_DIR, "--load", zone_path, "load_test"]
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    output = result.stdout + result.stderr
    if "loaded zone" in output.lower() and "failed" not in output.lower():
        return True
    return False

def build_1xanim(virtual_block_size):
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<I', 0))
    block_pos = len(buf)
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))
    content_start = len(buf)

    buf.extend(struct.pack('<i', 1))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    buf.extend(struct.pack('<i', 1))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))

    buf.extend(struct.pack('<I', PTR_FOLLOWING))
    buf.extend(b'tag_view\x00')
    buf.extend(struct.pack('<i', ASSET_TYPE_XANIMPARTS))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))

    header = bytearray(104)
    struct.pack_into('<I', header, 0x00, PTR_FOLLOWING)
    struct.pack_into('<H', header, 0x0E, 0)
    header[0x18 + 9] = 1
    struct.pack_into('<f', header, 0x30, 30.0)
    struct.pack_into('<f', header, 0x34, 1.0)
    struct.pack_into('<I', header, 0x40, PTR_FOLLOWING)
    for off in [0x44, 0x48, 0x4C, 0x50, 0x54, 0x58, 0x5C, 0x60, 0x64]:
        struct.pack_into('<I', header, off, PTR_NULL)
    buf.extend(header)
    buf.extend(b'test_idle\x00')
    buf.extend(struct.pack('<H', 0))

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    struct.pack_into('<I', buf, block_pos + BLOCK_TEMP * 4, 116)
    struct.pack_into('<I', buf, block_pos + BLOCK_VIRTUAL * 4, virtual_block_size)
    return bytes(buf)

def main():
    # Binary search for exact minimum VIRTUAL size
    lo, hi = 24, 48
    while lo < hi:
        mid = (lo + hi) // 2
        raw = build_1xanim(mid)
        ff = os.path.join(OUTPUT_DIR, "test_format.ff")
        write_zone(raw, "test_format", ff)
        if test_load(ff):
            hi = mid
        else:
            lo = mid + 1

    print(f"Minimum VIRTUAL block size for 1 xanim with 1 bone: {lo}")

    # Analysis:
    # Stream VIRTUAL data: 4 (strings[0] ptr) + 9 (string) + 8 (XAsset entry) = 21 bytes
    # Block data: 4 + 9 + 3 (align) + 8 = 24 bytes
    # Insert pointers: each PTR_FOLLOWING adds 4 bytes
    # Overhead = lo - 24 = insert pointer overhead
    print(f"  Stream VIRTUAL data: 21 bytes")
    print(f"  Block VIRTUAL data (with alignment): 24 bytes")
    print(f"  Insert pointer overhead: {lo - 24} bytes ({(lo-24)//4} pointers × 4 bytes)")

if __name__ == "__main__":
    main()
