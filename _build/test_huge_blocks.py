#!/usr/bin/env python3
"""Test with huge block allocations to isolate size vs format issue."""
import struct
import os
import subprocess
from compile_xanim_zone import (
    XChunkWriter, T6_ZONE_MAGIC_UNSIGNED, T6_ZONE_VERSION,
    XFILE_BLOCK_COUNT, ASSET_TYPE_XANIMPARTS
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
        LINKER, "--verbose",
        "--base-folder", test_dir,
        "--output-folder", OUTPUT_DIR,
        "--load", zone_path,
        "load_test"
    ]
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    output = result.stdout + result.stderr
    for line in output.strip().split('\n'):
        if any(w in line.lower() for w in ['fail', 'error', 'overflow', 'loaded zone']):
            print(f"    {line.strip()}")
    if "overflowed" in output.lower():
        return "OVERFLOW"
    elif "failed" in output.lower():
        return "FAIL"
    elif result.returncode == 0:
        return "OK"
    return f"EXIT {result.returncode}"

HUGE = 0x1000000  # 16MB per block

def test_1():
    """1 string, huge blocks."""
    print("\n=== Test 1: 1 string, all blocks = 16MB ===")
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))  # totalSize
    buf.extend(struct.pack('<I', 0))  # externalSize
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', HUGE))  # ALL blocks huge
    content_start = len(buf)

    buf.extend(struct.pack('<i', 1))               # string count
    buf.extend(struct.pack('<I', PTR_FOLLOWING))    # strings ptr
    buf.extend(struct.pack('<I', PTR_FOLLOWING))    # strings[0]
    buf.extend(b'tag_view\x00')
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    raw = bytes(buf)
    ff = os.path.join(OUTPUT_DIR, "test_format.ff")
    write_zone(raw, "test_format", ff)
    return test_load(ff)


def test_2():
    """Try: totalSize = sum of all block sizes."""
    print("\n=== Test 2: totalSize = sum of block sizes (all huge) ===")
    buf = bytearray()
    buf.extend(struct.pack('<I', HUGE * XFILE_BLOCK_COUNT))  # totalSize = huge
    buf.extend(struct.pack('<I', 0))  # externalSize
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', HUGE))
    content_start = len(buf)

    buf.extend(struct.pack('<i', 1))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))
    buf.extend(b'tag_view\x00')
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))

    raw = bytes(buf)
    ff = os.path.join(OUTPUT_DIR, "test_format.ff")
    write_zone(raw, "test_format", ff)
    return test_load(ff)


def test_3():
    """Try: what if XAssetList has a different layout? Maybe it's {stringCount, strings*, assetCount, assets*} without depends?"""
    print("\n=== Test 3: XAssetList without depends (count, strings, count, assets) ===")
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<I', 0))
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', HUGE))
    content_start = len(buf)

    # Try: stringCount, strings, assetCount, assets (NO depends)
    buf.extend(struct.pack('<i', 0))               # string count
    buf.extend(struct.pack('<I', PTR_NULL))         # strings
    buf.extend(struct.pack('<i', 0))               # asset count (NO depends in between)
    buf.extend(struct.pack('<I', PTR_NULL))         # assets

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    raw = bytes(buf)
    ff = os.path.join(OUTPUT_DIR, "test_format.ff")
    write_zone(raw, "test_format", ff)
    return test_load(ff)


def test_4():
    """What if depends comes BEFORE strings?"""
    print("\n=== Test 4: depends before strings ===")
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<I', 0))
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', HUGE))
    content_start = len(buf)

    # Try: dependCount, depends, stringCount, strings, assetCount, assets
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    buf.extend(struct.pack('<i', 1))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))
    buf.extend(b'tag_view\x00')
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    raw = bytes(buf)
    ff = os.path.join(OUTPUT_DIR, "test_format.ff")
    write_zone(raw, "test_format", ff)
    return test_load(ff)


def test_5():
    """What if ScriptStringList is {count, strings} where strings is NOT a pointer but count entries INLINE?"""
    print("\n=== Test 5: ScriptStringList as inline struct (no pointer to array) ===")
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<I', 0))
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', HUGE))
    content_start = len(buf)

    # ScriptStringList: count=1, then inline: PTR_FOLLOWING, "tag_view\0"
    # No outer pointer to the array
    buf.extend(struct.pack('<i', 1))
    # Inline first (and only) string pointer + data
    buf.extend(struct.pack('<I', PTR_FOLLOWING))
    buf.extend(b'tag_view\x00')
    # pad to align
    while len(buf) % 4 != 0:
        buf.append(0)
    # depends
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    # assets
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    raw = bytes(buf)
    ff = os.path.join(OUTPUT_DIR, "test_format.ff")
    write_zone(raw, "test_format", ff)
    return test_load(ff)


def test_6():
    """0 strings, 0 assets with huge blocks (sanity check)."""
    print("\n=== Test 6: 0 strings, 0 assets, huge blocks (sanity) ===")
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<I', 0))
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', HUGE))
    content_start = len(buf)

    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    raw = bytes(buf)
    ff = os.path.join(OUTPUT_DIR, "test_format.ff")
    write_zone(raw, "test_format", ff)
    return test_load(ff)


def test_7():
    """Test: 1 xanim asset with 0 strings, huge blocks."""
    print("\n=== Test 7: 0 strings, 1 xanim, huge blocks ===")
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<I', 0))
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', HUGE))
    content_start = len(buf)

    # 0 strings
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    # 0 depends
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    # 1 asset
    buf.extend(struct.pack('<i', 1))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))

    # XAsset entry
    buf.extend(struct.pack('<i', ASSET_TYPE_XANIMPARTS))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))

    # XAnimParts header (104 bytes, all zeros except name and framerate)
    header = bytearray(104)
    struct.pack_into('<I', header, 0x00, PTR_FOLLOWING)  # name ptr
    struct.pack_into('<f', header, 0x30, 30.0)  # framerate
    struct.pack_into('<f', header, 0x34, 1.0)   # frequency
    # names ptr - PTR_NULL since 0 bones
    struct.pack_into('<I', header, 0x40, PTR_NULL)
    # All other ptrs = NULL (already zeros)
    buf.extend(header)

    # Name string
    buf.extend(b'test_idle\x00')

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    raw = bytes(buf)
    ff = os.path.join(OUTPUT_DIR, "test_format.ff")
    write_zone(raw, "test_format", ff)
    return test_load(ff)


if __name__ == "__main__":
    r6 = test_6()
    print(f"  Result: {r6}\n")

    r1 = test_1()
    print(f"  Result: {r1}\n")

    r2 = test_2()
    print(f"  Result: {r2}\n")

    r3 = test_3()
    print(f"  Result: {r3}\n")

    r4 = test_4()
    print(f"  Result: {r4}\n")

    r5 = test_5()
    print(f"  Result: {r5}\n")

    r7 = test_7()
    print(f"  Result: {r7}\n")
