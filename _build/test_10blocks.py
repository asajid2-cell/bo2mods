#!/usr/bin/env python3
"""Test with 10 block sizes (T6 has DELAY_VIRTUAL + STREAMER_RESERVE)."""
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
T6_BLOCK_COUNT = 10  # T6 has 10 blocks, not 8!

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
        if any(w in line.lower() for w in ['fail', 'error', 'overflow', 'loaded zone', 'unloaded']):
            print(f"    {line.strip()}")
    if "loaded zone" in output.lower() and "failed" not in output.lower():
        return "OK"
    elif "overflowed" in output.lower():
        return "OVERFLOW"
    elif "failed" in output.lower():
        for l in output.strip().split('\n'):
            if "failed" in l.lower():
                return l.strip()[:100]
        return "FAIL"
    return f"EXIT {result.returncode}"


def test_empty_10blocks():
    """Test 1: Empty zone with 10 block sizes."""
    print("\n=== Test: Empty zone, 10 block sizes ===")
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))  # totalSize
    buf.extend(struct.pack('<I', 0))  # externalSize
    for _ in range(T6_BLOCK_COUNT):   # 10 blocks!
        buf.extend(struct.pack('<I', 0))
    content_start = len(buf)  # Should be 48 now

    # XAssetList (no depends in T6 serialization!)
    buf.extend(struct.pack('<i', 0))   # string count
    buf.extend(struct.pack('<I', PTR_NULL))  # strings
    buf.extend(struct.pack('<i', 0))   # asset count
    buf.extend(struct.pack('<I', PTR_NULL))  # assets

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    struct.pack_into('<I', buf, 8 + 3*4, total_size)  # VIRTUAL
    return bytes(buf)


def test_1string_10blocks():
    """Test 2: 1 string, 10 block sizes, no depends."""
    print("\n=== Test: 1 string, 10 blocks, no depends ===")
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<I', 0))
    for _ in range(T6_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))
    content_start = len(buf)

    # ScriptStringList
    buf.extend(struct.pack('<i', 1))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))  # strings[0]
    buf.extend(b'tag_view\x00')

    # Assets (no depends!)
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    struct.pack_into('<I', buf, 8 + 3*4, total_size)
    return bytes(buf)


def test_1xanim_10blocks():
    """Test 3: 1 xanim, 10 block sizes, no depends."""
    print("\n=== Test: 1 xanim, 10 blocks, no depends ===")
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<I', 0))
    block_pos = len(buf)
    for _ in range(T6_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))
    content_start = len(buf)

    virtual_start = len(buf)

    # ScriptStringList: 1 string
    buf.extend(struct.pack('<i', 1))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))
    buf.extend(b'tag_view\x00')

    # Assets (no depends!)
    buf.extend(struct.pack('<i', 1))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))
    buf.extend(struct.pack('<i', ASSET_TYPE_XANIMPARTS))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))

    virtual_size = len(buf) - virtual_start
    temp_start = len(buf)

    # XAnimParts (104 bytes)
    header = bytearray(104)
    struct.pack_into('<I', header, 0x00, PTR_FOLLOWING)  # name
    struct.pack_into('<H', header, 0x0E, 0)   # numframes = 0
    header[0x18 + 9] = 1  # 1 bone
    struct.pack_into('<f', header, 0x30, 30.0)
    struct.pack_into('<f', header, 0x34, 1.0)
    struct.pack_into('<I', header, 0x40, PTR_FOLLOWING)  # names
    struct.pack_into('<I', header, 0x44, PTR_NULL)
    struct.pack_into('<I', header, 0x48, PTR_NULL)
    struct.pack_into('<I', header, 0x4C, PTR_NULL)
    struct.pack_into('<I', header, 0x50, PTR_NULL)
    struct.pack_into('<I', header, 0x54, PTR_NULL)
    struct.pack_into('<I', header, 0x58, PTR_NULL)
    struct.pack_into('<I', header, 0x5C, PTR_NULL)
    struct.pack_into('<I', header, 0x60, PTR_NULL)
    struct.pack_into('<I', header, 0x64, PTR_NULL)
    buf.extend(header)

    # Name string
    buf.extend(b'test_idle\x00')

    # Align to 2
    if len(buf) % 2 != 0:
        buf.append(0)

    # Names array (1 entry, uint16 index 0)
    buf.extend(struct.pack('<H', 0))

    temp_size = len(buf) - temp_start

    # Patch
    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    struct.pack_into('<I', buf, block_pos + 0*4, temp_size)    # TEMP
    struct.pack_into('<I', buf, block_pos + 3*4, virtual_size)  # VIRTUAL

    print(f"  Header: 48 bytes, Content: {total_size} bytes")
    print(f"  VIRTUAL: {virtual_size}, TEMP: {temp_size}")
    return bytes(buf)


def main():
    tests = [
        ("Empty 10 blocks", test_empty_10blocks),
        ("1 string 10 blocks", test_1string_10blocks),
        ("1 xanim 10 blocks", test_1xanim_10blocks),
    ]

    for name, builder in tests:
        raw = builder()
        ff = os.path.join(OUTPUT_DIR, "test_format.ff")
        write_zone(raw, "test_format", ff)
        result = test_load(ff)
        print(f"  Result: {result}\n")


if __name__ == "__main__":
    main()
