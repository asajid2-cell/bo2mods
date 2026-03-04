#!/usr/bin/env python3
"""Test with larger VIRTUAL block to account for insert pointers."""
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
    args = [
        LINKER, "--verbose",
        "--base-folder", test_dir,
        "--output-folder", OUTPUT_DIR,
        "--load", zone_path,
        "load_test"
    ]
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    output = result.stdout + result.stderr
    for line in output.strip().split('\n'):
        if any(w in line.lower() for w in ['fail', 'error', 'overflow', 'loaded zone', 'unloaded', 'missing']):
            print(f"    {line.strip()}")
    if "loaded zone" in output.lower() and "failed" not in output.lower():
        return "OK"
    elif "overflowed" in output.lower():
        return "OVERFLOW"
    elif "failed" in output.lower():
        for l in output.strip().split('\n'):
            if "failed" in l.lower():
                return l.strip()[:120]
    return f"EXIT {result.returncode}"

def build_1xanim(virtual_block_size):
    """Build 1 xanim zone with specified VIRTUAL block size."""
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<I', 0))
    block_pos = len(buf)
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))
    content_start = len(buf)

    # RAW XAssetList (24 bytes)
    buf.extend(struct.pack('<i', 1))                # stringList.count
    buf.extend(struct.pack('<I', PTR_FOLLOWING))     # stringList.strings
    buf.extend(struct.pack('<i', 0))                # dependCount
    buf.extend(struct.pack('<I', PTR_NULL))           # depends
    buf.extend(struct.pack('<i', 1))                # assetCount
    buf.extend(struct.pack('<I', PTR_FOLLOWING))     # assets

    # VIRTUAL: strings + asset array (no stream padding!)
    buf.extend(struct.pack('<I', PTR_FOLLOWING))  # strings[0]
    buf.extend(b'tag_view\x00')
    # NO stream padding for alignment
    buf.extend(struct.pack('<i', ASSET_TYPE_XANIMPARTS))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))

    # TEMP: XAnimParts
    header = bytearray(104)
    struct.pack_into('<I', header, 0x00, PTR_FOLLOWING)  # name
    struct.pack_into('<H', header, 0x0E, 0)
    header[0x18 + 9] = 1
    struct.pack_into('<f', header, 0x30, 30.0)
    struct.pack_into('<f', header, 0x34, 1.0)
    struct.pack_into('<I', header, 0x40, PTR_FOLLOWING)  # names
    for off in [0x44, 0x48, 0x4C, 0x50, 0x54, 0x58, 0x5C, 0x60, 0x64]:
        struct.pack_into('<I', header, off, PTR_NULL)
    buf.extend(header)
    buf.extend(b'test_idle\x00')
    buf.extend(struct.pack('<H', 0))  # names[0]

    temp_block_size = 116  # 104 + 10 + 2

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    struct.pack_into('<I', buf, block_pos + BLOCK_TEMP * 4, temp_block_size)
    struct.pack_into('<I', buf, block_pos + BLOCK_VIRTUAL * 4, virtual_block_size)

    return bytes(buf)


def main():
    # Test with increasing VIRTUAL block sizes
    for vs in [24, 32, 48, 64, 128, 256, 512, 1024, 4096]:
        raw = build_1xanim(vs)
        ff = os.path.join(OUTPUT_DIR, "test_format.ff")
        write_zone(raw, "test_format", ff)
        result = test_load(ff)
        print(f"  VIRTUAL={vs:5d}: {result}\n")
        if result == "OK":
            break


if __name__ == "__main__":
    main()
