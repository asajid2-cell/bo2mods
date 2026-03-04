#!/usr/bin/env python3
"""Test multiple zone format variations to find what OAT accepts."""
import struct
import os
import subprocess
from compile_xanim_zone import (
    XChunkWriter, T6_ZONE_MAGIC_UNSIGNED, T6_ZONE_VERSION,
    PTR_FOLLOWING, PTR_NULL, XFILE_BLOCK_COUNT
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
    return os.path.getsize(output_path)

def test_load(zone_path, zone_name):
    """Try to load the zone with OAT."""
    # Create a dummy zone source that references nothing
    test_dir = os.path.join(OUTPUT_DIR, "test_zone")
    os.makedirs(os.path.join(test_dir, "zone_source"), exist_ok=True)
    with open(os.path.join(test_dir, "zone_source", "load_test.zone"), 'w') as f:
        f.write("// Empty test zone\n")

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
        return False, "OVERFLOW"
    elif "failed" in output.lower():
        return False, output.strip().split('\n')[-1]
    elif result.returncode != 0:
        return False, output.strip().split('\n')[-1] if output.strip() else f"exit code {result.returncode}"
    else:
        return True, "OK"


def build_variant_A():
    """Variant A: Everything in VIRTUAL block only."""
    buf = bytearray()

    # XFile header
    buf.extend(struct.pack('<I', 0))  # totalSize placeholder
    buf.extend(struct.pack('<I', 0))  # externalSize
    block_pos = len(buf)
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))

    content_start = len(buf)

    # XAssetList: 0 strings, 0 depends, 0 assets
    buf.extend(struct.pack('<i', 0))   # string count
    buf.extend(struct.pack('<I', PTR_NULL))  # strings ptr
    buf.extend(struct.pack('<i', 0))   # depend count
    buf.extend(struct.pack('<I', PTR_NULL))  # depends ptr
    buf.extend(struct.pack('<i', 0))   # asset count
    buf.extend(struct.pack('<I', PTR_NULL))  # assets ptr

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    struct.pack_into('<I', buf, block_pos + 3*4, total_size)  # VIRTUAL only
    return bytes(buf)


def build_variant_B():
    """Variant B: Everything in TEMP block only."""
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<I', 0))
    block_pos = len(buf)
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))

    content_start = len(buf)
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    struct.pack_into('<I', buf, block_pos + 0*4, total_size)  # TEMP only
    return bytes(buf)


def build_variant_C():
    """Variant C: Both TEMP and VIRTUAL = totalSize (over-allocate)."""
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<I', 0))
    block_pos = len(buf)
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))

    content_start = len(buf)
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    struct.pack_into('<I', buf, block_pos + 0*4, total_size)  # TEMP
    struct.pack_into('<I', buf, block_pos + 3*4, total_size)  # VIRTUAL
    return bytes(buf)


def build_variant_D():
    """Variant D: totalSize includes the header."""
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<I', 0))
    block_pos = len(buf)
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))

    content_start = len(buf)
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))

    content_size = len(buf) - content_start
    total_with_header = len(buf)  # Include header in totalSize
    struct.pack_into('<I', buf, 0, total_with_header)
    struct.pack_into('<I', buf, block_pos + 3*4, total_with_header)
    return bytes(buf)


def build_variant_E():
    """Variant E: 9 block sizes instead of 8 (maybe T6 has 9?)."""
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))  # totalSize
    buf.extend(struct.pack('<I', 0))  # externalSize
    block_pos = len(buf)
    for _ in range(9):  # 9 blocks!
        buf.extend(struct.pack('<I', 0))

    content_start = len(buf)
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    struct.pack_into('<I', buf, block_pos + 3*4, total_size)
    return bytes(buf)


def build_variant_F():
    """Variant F: Auth hash (32 bytes of zeros) before XFile header."""
    buf = bytearray()

    # Auth hash section (32 bytes)
    buf.extend(b'\x00' * 32)

    # XFile header
    total_pos = len(buf)
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<I', 0))
    block_pos = len(buf)
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))

    content_start = len(buf)
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, total_pos, total_size)
    struct.pack_into('<I', buf, block_pos + 3*4, total_size)
    return bytes(buf)


def build_variant_G():
    """Variant G: Auth hash (256 bytes) before XFile header."""
    buf = bytearray()
    buf.extend(b'\x00' * 256)

    total_pos = len(buf)
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<I', 0))
    block_pos = len(buf)
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))

    content_start = len(buf)
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, total_pos, total_size)
    struct.pack_into('<I', buf, block_pos + 3*4, total_size)
    return bytes(buf)


def main():
    variants = [
        ("A: All VIRTUAL", build_variant_A),
        ("B: All TEMP", build_variant_B),
        ("C: Both = totalSize", build_variant_C),
        ("D: totalSize includes header", build_variant_D),
        ("E: 9 block sizes", build_variant_E),
        ("F: 32-byte auth prefix", build_variant_F),
        ("G: 256-byte auth prefix", build_variant_G),
    ]

    for name, builder in variants:
        zone_name = "test_format"
        raw_data = builder()
        ff_path = os.path.join(OUTPUT_DIR, f"{zone_name}.ff")
        write_zone(raw_data, zone_name, ff_path)
        success, msg = test_load(ff_path, zone_name)
        status = "OK" if success else "FAIL"
        print(f"  {status}: {name:40s} -> {msg}")


if __name__ == "__main__":
    main()
