#!/usr/bin/env python3
"""Test different pointer encoding values to find the correct one for T6."""
import struct
import os
import subprocess
from compile_xanim_zone import (
    XChunkWriter, T6_ZONE_MAGIC_UNSIGNED, T6_ZONE_VERSION,
    XFILE_BLOCK_COUNT
)

LINKER = r"z:\Games\pluto_t6_full_game\tools\oat\Linker.exe"
OUTPUT_DIR = r"z:\Games\pluto_t6_full_game\_build\panzer_work\output"

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
    if "overflowed" in output.lower():
        return "OVERFLOW"
    elif "failed" in output.lower():
        for l in output.strip().split('\n'):
            if "failed" in l.lower() or "error" in l.lower():
                return l.strip()[:80]
        return "FAIL"
    elif result.returncode == 0:
        return "OK"
    else:
        return f"EXIT {result.returncode}"


def build_1string_zone(ptr_following_value):
    """Build zone with 1 string using the given pointer value for 'following'."""
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))  # totalSize
    buf.extend(struct.pack('<I', 0))  # externalSize
    block_pos = len(buf)
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))
    content_start = len(buf)

    # XAssetList with 1 string
    buf.extend(struct.pack('<i', 1))
    buf.extend(struct.pack('<I', ptr_following_value))  # strings ptr
    buf.extend(struct.pack('<I', ptr_following_value))  # strings[0] ptr
    buf.extend(b'tag_view\x00')

    # depends
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', 0))
    # assets
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', 0))

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    struct.pack_into('<I', buf, block_pos + 3*4, total_size)  # All VIRTUAL
    return bytes(buf)


def build_1string_flat(ptr_following_value):
    """Build zone with 1 string, FLAT format (no per-string ptr)."""
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<I', 0))
    block_pos = len(buf)
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))
    content_start = len(buf)

    buf.extend(struct.pack('<i', 1))
    buf.extend(struct.pack('<I', ptr_following_value))  # strings ptr
    # Flat: just the string data, no per-string pointer
    buf.extend(b'tag_view\x00')

    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', 0))

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    struct.pack_into('<I', buf, block_pos + 3*4, total_size)
    return bytes(buf)


def main():
    # Test different pointer values for "following"
    ptr_values = [
        (0xFFFFFFFE, "-2 (0xFFFFFFFE)"),
        (0xFFFFFFFF, "-1 (0xFFFFFFFF)"),
        (0x00000001, "1"),
        (0xFDFDFDFD, "0xFDFDFDFD"),
        (0xFFFFFFFD, "-3 (0xFFFFFFFD)"),
    ]

    print("=== Format: ptr array (strings ptr + per-string ptr) ===")
    for val, name in ptr_values:
        raw = build_1string_zone(val)
        ff = os.path.join(OUTPUT_DIR, "test_format.ff")
        write_zone(raw, "test_format", ff)
        result = test_load(ff)
        print(f"  PTR={name:20s} -> {result}")

    print("\n=== Format: flat strings (strings ptr only, no per-string ptr) ===")
    for val, name in ptr_values:
        raw = build_1string_flat(val)
        ff = os.path.join(OUTPUT_DIR, "test_format.ff")
        write_zone(raw, "test_format", ff)
        result = test_load(ff)
        print(f"  PTR={name:20s} -> {result}")

    # Also test: what if "strings" is an array of OFFSETS, not pointers?
    print("\n=== Special: No following marker, just count + offsets ===")
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<I', 0))
    block_pos = len(buf)
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))
    content_start = len(buf)

    # Try: count, then just packed strings with no pointer at all
    buf.extend(struct.pack('<i', 1))
    # What if there's NO pointer field for strings, just direct data?
    buf.extend(b'tag_view\x00')
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', 0))

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    struct.pack_into('<I', buf, block_pos + 3*4, total_size)
    raw = bytes(buf)
    ff = os.path.join(OUTPUT_DIR, "test_format.ff")
    write_zone(raw, "test_format", ff)
    result = test_load(ff)
    print(f"  No ptr field at all          -> {result}")


if __name__ == "__main__":
    main()
