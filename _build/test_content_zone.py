#!/usr/bin/env python3
"""Test zone content variants to find exactly what breaks."""
import struct
import os
import subprocess
from compile_xanim_zone import (
    XChunkWriter, T6_ZONE_MAGIC_UNSIGNED, T6_ZONE_VERSION,
    PTR_FOLLOWING, PTR_NULL, ASSET_TYPE_XANIMPARTS, XFILE_BLOCK_COUNT
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
        lines = output.strip().split('\n')
        for l in lines:
            if "failed" in l.lower() or "error" in l.lower():
                return l.strip()
        return "FAIL: " + lines[-1]
    elif result.returncode == 0:
        return "OK"
    else:
        return f"EXIT {result.returncode}"


def make_zone(content_bytes, virtual_size=None, temp_size=0):
    """Build a zone file with given content and block sizes."""
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))  # totalSize
    buf.extend(struct.pack('<I', 0))  # externalSize
    block_pos = len(buf)
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))
    content_start = len(buf)
    buf.extend(content_bytes)
    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    if virtual_size is None:
        virtual_size = total_size
    struct.pack_into('<I', buf, block_pos + 0*4, temp_size)
    struct.pack_into('<I', buf, block_pos + 3*4, virtual_size)
    return bytes(buf)


def test_1_string_no_assets():
    """1 string, 0 assets - test script string serialization."""
    content = bytearray()

    # ScriptStringList: count=1, strings=PTR_FOLLOWING
    content.extend(struct.pack('<i', 1))
    content.extend(struct.pack('<I', PTR_FOLLOWING))

    # Format A: pointer array then string data
    content.extend(struct.pack('<I', PTR_FOLLOWING))  # strings[0]
    content.extend(b'tag_view\x00')

    # depends
    content.extend(struct.pack('<i', 0))
    content.extend(struct.pack('<I', PTR_NULL))
    # assets
    content.extend(struct.pack('<i', 0))
    content.extend(struct.pack('<I', PTR_NULL))

    return make_zone(bytes(content))


def test_1_string_flat():
    """1 string with FLAT format (no individual ptr per string)."""
    content = bytearray()

    # ScriptStringList: count=1, strings=PTR_FOLLOWING
    content.extend(struct.pack('<i', 1))
    content.extend(struct.pack('<I', PTR_FOLLOWING))

    # Format B: just the string data directly (no ptr per string)
    content.extend(b'tag_view\x00')

    # depends
    content.extend(struct.pack('<i', 0))
    content.extend(struct.pack('<I', PTR_NULL))
    # assets
    content.extend(struct.pack('<i', 0))
    content.extend(struct.pack('<I', PTR_NULL))

    return make_zone(bytes(content))


def test_1_string_null_ptr():
    """1 string, but strings pointer is NULL (empty list)."""
    content = bytearray()

    content.extend(struct.pack('<i', 1))
    content.extend(struct.pack('<I', PTR_NULL))  # strings = NULL despite count=1

    content.extend(struct.pack('<i', 0))
    content.extend(struct.pack('<I', PTR_NULL))
    content.extend(struct.pack('<i', 0))
    content.extend(struct.pack('<I', PTR_NULL))

    return make_zone(bytes(content))


def test_0_strings_1_xanim():
    """0 strings, 1 dummy xanim - test asset without strings."""
    content = bytearray()

    # ScriptStringList: empty
    content.extend(struct.pack('<i', 0))
    content.extend(struct.pack('<I', PTR_NULL))
    content.extend(struct.pack('<i', 0))
    content.extend(struct.pack('<I', PTR_NULL))

    virtual_size = len(content)

    # 1 asset
    content.extend(struct.pack('<i', 1))
    content.extend(struct.pack('<I', PTR_FOLLOWING))
    # XAsset entry
    content.extend(struct.pack('<i', ASSET_TYPE_XANIMPARTS))
    content.extend(struct.pack('<I', PTR_FOLLOWING))

    virtual_size = len(content)  # All of this is VIRTUAL

    # XAnimParts header (104 bytes, minimal)
    temp_start = len(content)
    header = bytearray(104)
    struct.pack_into('<I', header, 0x00, PTR_FOLLOWING)  # name
    struct.pack_into('<H', header, 0x0E, 0)   # numframes
    header[0x18 + 9] = 0  # 0 bones
    struct.pack_into('<f', header, 0x30, 30.0)
    struct.pack_into('<f', header, 0x34, 1.0)
    struct.pack_into('<I', header, 0x40, PTR_NULL)  # names (no bones)
    struct.pack_into('<I', header, 0x44, PTR_NULL)  # dataByte
    struct.pack_into('<I', header, 0x48, PTR_NULL)  # dataShort
    struct.pack_into('<I', header, 0x4C, PTR_NULL)  # dataInt
    struct.pack_into('<I', header, 0x50, PTR_NULL)  # randomDataShort
    struct.pack_into('<I', header, 0x54, PTR_NULL)  # randomDataByte
    struct.pack_into('<I', header, 0x58, PTR_NULL)  # randomDataInt
    struct.pack_into('<I', header, 0x5C, PTR_NULL)  # indices
    struct.pack_into('<I', header, 0x60, PTR_NULL)  # notify
    struct.pack_into('<I', header, 0x64, PTR_NULL)  # deltaPart
    content.extend(header)

    # Name string
    content.extend(b'test_idle\x00')

    temp_size = len(content) - temp_start

    return make_zone(bytes(content), virtual_size=virtual_size, temp_size=temp_size)


def test_0_strings_1_xanim_all_virtual():
    """0 strings, 1 dummy xanim - ALL data in VIRTUAL."""
    content = bytearray()

    content.extend(struct.pack('<i', 0))
    content.extend(struct.pack('<I', PTR_NULL))
    content.extend(struct.pack('<i', 0))
    content.extend(struct.pack('<I', PTR_NULL))

    content.extend(struct.pack('<i', 1))
    content.extend(struct.pack('<I', PTR_FOLLOWING))
    content.extend(struct.pack('<i', ASSET_TYPE_XANIMPARTS))
    content.extend(struct.pack('<I', PTR_FOLLOWING))

    header = bytearray(104)
    struct.pack_into('<I', header, 0x00, PTR_FOLLOWING)
    struct.pack_into('<H', header, 0x0E, 0)
    struct.pack_into('<f', header, 0x30, 30.0)
    struct.pack_into('<f', header, 0x34, 1.0)
    struct.pack_into('<I', header, 0x40, PTR_NULL)
    struct.pack_into('<I', header, 0x44, PTR_NULL)
    struct.pack_into('<I', header, 0x48, PTR_NULL)
    struct.pack_into('<I', header, 0x4C, PTR_NULL)
    struct.pack_into('<I', header, 0x50, PTR_NULL)
    struct.pack_into('<I', header, 0x54, PTR_NULL)
    struct.pack_into('<I', header, 0x58, PTR_NULL)
    struct.pack_into('<I', header, 0x5C, PTR_NULL)
    struct.pack_into('<I', header, 0x60, PTR_NULL)
    struct.pack_into('<I', header, 0x64, PTR_NULL)
    content.extend(header)
    content.extend(b'test_idle\x00')

    return make_zone(bytes(content))  # All in VIRTUAL by default


def main():
    tests = [
        ("1 string (ptr array format)", test_1_string_no_assets),
        ("1 string (flat format)", test_1_string_flat),
        ("1 string (null ptr)", test_1_string_null_ptr),
        ("0 str, 1 xanim (VIRT+TEMP)", test_0_strings_1_xanim),
        ("0 str, 1 xanim (all VIRT)", test_0_strings_1_xanim_all_virtual),
    ]

    for name, builder in tests:
        zone_name = "test_format"
        raw_data = builder()
        ff_path = os.path.join(OUTPUT_DIR, f"{zone_name}.ff")
        write_zone(raw_data, zone_name, ff_path)
        result = test_load(ff_path)
        print(f"  {name:40s} -> {result}")


if __name__ == "__main__":
    main()
