#!/usr/bin/env python3
"""Test with CORRECTED T6 zone format based on OAT source analysis."""
import struct
import os
import subprocess
from compile_xanim_zone import (
    XChunkWriter, T6_ZONE_MAGIC_UNSIGNED, T6_ZONE_VERSION,
    ASSET_TYPE_XANIMPARTS
)

LINKER = r"z:\Games\pluto_t6_full_game\tools\oat\Linker.exe"
OUTPUT_DIR = r"z:\Games\pluto_t6_full_game\_build\panzer_work\output"

# CORRECTED values!
PTR_FOLLOWING = 0xFFFFFFFF  # -1, NOT -2!
PTR_NULL = 0x00000000
XFILE_BLOCK_COUNT = 8  # 8 blocks in T6
# Block indices:
# 0=TEMP, 1=RUNTIME_VIRTUAL, 2=RUNTIME_PHYSICAL,
# 3=DELAY_VIRTUAL, 4=DELAY_PHYSICAL,
# 5=VIRTUAL, 6=PHYSICAL, 7=STREAMER_RESERVE
BLOCK_VIRTUAL = 5  # NOT 3!
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

def test_load(zone_path, verbose=True):
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
    if verbose:
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
                return l.strip()[:120]
    return f"EXIT {result.returncode}"


def test_empty():
    """Empty zone with corrected format."""
    print("\n=== Test: Empty zone (corrected) ===")
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))  # totalSize
    buf.extend(struct.pack('<I', 0))  # externalSize
    block_pos = len(buf)
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))
    content_start = len(buf)  # 40 bytes

    # XAssetList RAW (24 bytes, not in any block)
    buf.extend(struct.pack('<i', 0))          # stringList.count
    buf.extend(struct.pack('<I', PTR_NULL))    # stringList.strings
    buf.extend(struct.pack('<i', 0))          # dependCount
    buf.extend(struct.pack('<I', PTR_NULL))    # depends
    buf.extend(struct.pack('<i', 0))          # assetCount
    buf.extend(struct.pack('<I', PTR_NULL))    # assets

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    # No blocks needed for empty zone

    raw = bytes(buf)
    ff = os.path.join(OUTPUT_DIR, "test_format.ff")
    write_zone(raw, "test_format", ff)
    return test_load(ff)


def test_1string():
    """1 string with corrected PTR_FOLLOWING and block index."""
    print("\n=== Test: 1 string (corrected: PTR=0xFFFFFFFF, VIRTUAL=block 5) ===")
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))  # totalSize
    buf.extend(struct.pack('<I', 0))  # externalSize
    block_pos = len(buf)
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))
    content_start = len(buf)  # 40

    # XAssetList RAW (24 bytes)
    buf.extend(struct.pack('<i', 1))                # stringList.count = 1
    buf.extend(struct.pack('<I', PTR_FOLLOWING))     # stringList.strings
    buf.extend(struct.pack('<i', 0))                # dependCount
    buf.extend(struct.pack('<I', PTR_NULL))           # depends
    buf.extend(struct.pack('<i', 0))                # assetCount
    buf.extend(struct.pack('<I', PTR_NULL))           # assets

    # VIRTUAL block data starts here (after PushBlock(VIRTUAL))
    virtual_start = len(buf)

    # strings pointer array (1 entry)
    buf.extend(struct.pack('<I', PTR_FOLLOWING))     # strings[0] ptr
    # string data
    buf.extend(b'tag_view\x00')
    # Align to 4
    while (len(buf) - virtual_start) % 4 != 0:
        buf.append(0)

    virtual_size = len(buf) - virtual_start

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    # VIRTUAL is block index 5!
    struct.pack_into('<I', buf, block_pos + BLOCK_VIRTUAL * 4, virtual_size)

    print(f"  totalSize={total_size}, VIRTUAL(block 5)={virtual_size}")
    raw = bytes(buf)
    ff = os.path.join(OUTPUT_DIR, "test_format.ff")
    write_zone(raw, "test_format", ff)
    return test_load(ff)


def test_1xanim():
    """1 xanim with corrected format."""
    print("\n=== Test: 1 string + 1 xanim (corrected) ===")
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))
    buf.extend(struct.pack('<I', 0))
    block_pos = len(buf)
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))
    content_start = len(buf)

    # XAssetList RAW (24 bytes)
    buf.extend(struct.pack('<i', 1))                # 1 string
    buf.extend(struct.pack('<I', PTR_FOLLOWING))
    buf.extend(struct.pack('<i', 0))                # 0 depends
    buf.extend(struct.pack('<I', PTR_NULL))
    buf.extend(struct.pack('<i', 1))                # 1 asset
    buf.extend(struct.pack('<I', PTR_FOLLOWING))

    # VIRTUAL block data
    virtual_start = len(buf)

    # Script strings (in VIRTUAL)
    buf.extend(struct.pack('<I', PTR_FOLLOWING))     # strings[0]
    buf.extend(b'tag_view\x00')
    while (len(buf) - virtual_start) % 4 != 0:
        buf.append(0)

    # (depends would go here if any)

    # XAsset array (in VIRTUAL)
    buf.extend(struct.pack('<i', ASSET_TYPE_XANIMPARTS))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))

    virtual_size = len(buf) - virtual_start

    # TEMP block data (for XAnimParts)
    temp_start = len(buf)

    # XAnimParts header (104 bytes)
    header = bytearray(104)
    struct.pack_into('<I', header, 0x00, PTR_FOLLOWING)  # name
    struct.pack_into('<H', header, 0x0E, 0)   # numframes = 0
    header[0x18 + 9] = 1  # 1 bone total
    struct.pack_into('<f', header, 0x30, 30.0)
    struct.pack_into('<f', header, 0x34, 1.0)
    struct.pack_into('<I', header, 0x40, PTR_FOLLOWING)  # names
    struct.pack_into('<I', header, 0x44, PTR_NULL)  # dataByte
    struct.pack_into('<I', header, 0x48, PTR_NULL)  # dataShort
    struct.pack_into('<I', header, 0x4C, PTR_NULL)  # dataInt
    struct.pack_into('<I', header, 0x50, PTR_NULL)  # randomDataShort
    struct.pack_into('<I', header, 0x54, PTR_NULL)  # randomDataByte
    struct.pack_into('<I', header, 0x58, PTR_NULL)  # randomDataInt
    struct.pack_into('<I', header, 0x5C, PTR_NULL)  # indices
    struct.pack_into('<I', header, 0x60, PTR_NULL)  # notify
    struct.pack_into('<I', header, 0x64, PTR_NULL)  # deltaPart
    buf.extend(header)

    # Pointer-resolved data (in TEMP):
    # 1. Name string
    buf.extend(b'test_idle\x00')
    # Align to 2
    while (len(buf) - temp_start) % 2 != 0:
        buf.append(0)
    # 2. Names array (1 uint16 for bone 0)
    buf.extend(struct.pack('<H', 0))

    temp_size = len(buf) - temp_start

    # Patch header
    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    struct.pack_into('<I', buf, block_pos + BLOCK_TEMP * 4, temp_size)
    struct.pack_into('<I', buf, block_pos + BLOCK_VIRTUAL * 4, virtual_size + 256)  # Extra for insert ptrs

    print(f"  totalSize={total_size}, TEMP={temp_size}, VIRTUAL={virtual_size}+padding")

    raw = bytes(buf)
    ff = os.path.join(OUTPUT_DIR, "test_format.ff")
    write_zone(raw, "test_format", ff)
    return test_load(ff)


def main():
    r = test_empty()
    print(f"  Result: {r}\n")

    r = test_1string()
    print(f"  Result: {r}\n")

    r = test_1xanim()
    print(f"  Result: {r}\n")


if __name__ == "__main__":
    main()
