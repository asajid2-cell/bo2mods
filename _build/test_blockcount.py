#!/usr/bin/env python3
"""Systematically test block counts and block sizes."""
import struct
import os
import subprocess
from compile_xanim_zone import (
    XChunkWriter, T6_ZONE_MAGIC_UNSIGNED, T6_ZONE_VERSION,
    ASSET_TYPE_XANIMPARTS
)

LINKER = r"z:\Games\pluto_t6_full_game\tools\oat\Linker.exe"
OUTPUT_DIR = r"z:\Games\pluto_t6_full_game\_build\panzer_work\output"
PTR_FOLLOWING = 0xFFFFFFFE
PTR_NULL = 0x00000000

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
        LINKER,
        "--base-folder", test_dir,
        "--output-folder", OUTPUT_DIR,
        "--load", zone_path,
        "load_test"
    ]
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    output = result.stdout + result.stderr
    if "loaded zone" in output.lower() and "failed" not in output.lower():
        return "OK"
    elif "overflowed" in output.lower():
        return "OVERFLOW"
    elif "failed" in output.lower():
        for l in output.strip().split('\n'):
            if "failed" in l.lower():
                return l.strip()[:120]
    return f"EXIT {result.returncode}"


def build_1string(block_count, virtual_size_override=None):
    """Build zone with 1 string, given block count."""
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))  # totalSize
    buf.extend(struct.pack('<I', 0))  # externalSize
    block_pos = len(buf)
    for _ in range(block_count):
        buf.extend(struct.pack('<I', 0))
    content_start = len(buf)

    # XAssetList (no depends)
    buf.extend(struct.pack('<i', 1))                # string count
    buf.extend(struct.pack('<I', PTR_FOLLOWING))     # strings ptr
    buf.extend(struct.pack('<I', PTR_FOLLOWING))     # strings[0]
    buf.extend(b'tag_view\x00')
    # Pad to 4-byte align
    while len(buf) % 4 != 0:
        buf.append(0)
    buf.extend(struct.pack('<i', 0))                # asset count
    buf.extend(struct.pack('<I', PTR_NULL))           # assets ptr

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    vs = virtual_size_override if virtual_size_override else total_size
    struct.pack_into('<I', buf, block_pos + 3*4, vs)  # VIRTUAL
    return bytes(buf)


def main():
    print("=== Test 1: Block count sweep with 1 string ===")
    for bc in [8, 9, 10, 11, 12, 13, 14]:
        raw = build_1string(bc)
        ff = os.path.join(OUTPUT_DIR, "test_format.ff")
        write_zone(raw, "test_format", ff)
        result = test_load(ff)
        print(f"  {bc} blocks: {result}")

    print("\n=== Test 2: 10 blocks, huge VIRTUAL (1MB) ===")
    raw = build_1string(10, virtual_size_override=0x100000)
    ff = os.path.join(OUTPUT_DIR, "test_format.ff")
    write_zone(raw, "test_format", ff)
    result = test_load(ff)
    print(f"  10 blocks, 1MB VIRTUAL: {result}")

    print("\n=== Test 3: 10 blocks, ALL blocks = 64KB ===")
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<I', 0))
    block_pos = len(buf)
    for _ in range(10):
        buf.extend(struct.pack('<I', 0x10000))  # 64KB per block
    content_start = len(buf)
    buf.extend(struct.pack('<i', 1))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))
    buf.extend(b'tag_view\x00')
    while len(buf) % 4 != 0:
        buf.append(0)
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    raw = bytes(buf)
    ff = os.path.join(OUTPUT_DIR, "test_format.ff")
    write_zone(raw, "test_format", ff)
    result = test_load(ff)
    print(f"  10 blocks, all 64KB: {result}")

    print("\n=== Test 4: Various block counts, ALL blocks = 64KB ===")
    for bc in [8, 9, 10, 11, 12]:
        buf = bytearray()
        buf.extend(struct.pack('<I', 0))
        buf.extend(struct.pack('<I', 0))
        for _ in range(bc):
            buf.extend(struct.pack('<I', 0x10000))
        content_start = len(buf)
        buf.extend(struct.pack('<i', 1))
        buf.extend(struct.pack('<I', PTR_FOLLOWING))
        buf.extend(struct.pack('<I', PTR_FOLLOWING))
        buf.extend(b'tag_view\x00')
        while len(buf) % 4 != 0:
            buf.append(0)
        buf.extend(struct.pack('<i', 0))
        buf.extend(struct.pack('<I', PTR_NULL))
        total_size = len(buf) - content_start
        struct.pack_into('<I', buf, 0, total_size)
        raw = bytes(buf)
        ff = os.path.join(OUTPUT_DIR, "test_format.ff")
        write_zone(raw, "test_format", ff)
        result = test_load(ff)
        print(f"  {bc} blocks, all 64KB: {result}")

    print("\n=== Test 5: 10 blocks, flat string format (no per-string ptr) ===")
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<I', 0))
    for _ in range(10):
        buf.extend(struct.pack('<I', 0x10000))
    content_start = len(buf)
    buf.extend(struct.pack('<i', 1))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))
    # NO per-string pointer, just the string data directly
    buf.extend(b'tag_view\x00')
    while len(buf) % 4 != 0:
        buf.append(0)
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    raw = bytes(buf)
    ff = os.path.join(OUTPUT_DIR, "test_format.ff")
    write_zone(raw, "test_format", ff)
    result = test_load(ff)
    print(f"  10 blocks, flat strings: {result}")


if __name__ == "__main__":
    main()
