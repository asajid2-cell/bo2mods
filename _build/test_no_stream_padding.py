#!/usr/bin/env python3
"""Test WITHOUT alignment padding in the stream."""
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


def test_1xanim_no_pad():
    """1 xanim, NO stream padding for alignment."""
    print("\n=== Test: 1 xanim, NO stream alignment padding ===")
    buf = bytearray()
    buf.extend(struct.pack('<I', 0))  # totalSize
    buf.extend(struct.pack('<I', 0))  # externalSize
    block_pos = len(buf)
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))
    content_start = len(buf)  # 40

    # ---- RAW: XAssetList (24 bytes, no block) ----
    buf.extend(struct.pack('<i', 1))                # stringList.count
    buf.extend(struct.pack('<I', PTR_FOLLOWING))     # stringList.strings
    buf.extend(struct.pack('<i', 0))                # dependCount
    buf.extend(struct.pack('<I', PTR_NULL))           # depends
    buf.extend(struct.pack('<i', 1))                # assetCount
    buf.extend(struct.pack('<I', PTR_FOLLOWING))     # assets

    # ---- VIRTUAL block data (no stream padding for alignment!) ----
    virtual_stream_start = len(buf)

    # Script strings: Alloc(align=4) → no padding needed (offset 0 is aligned)
    # strings[0] = PTR_FOLLOWING
    buf.extend(struct.pack('<I', PTR_FOLLOWING))
    # Alloc(align=1), LoadNullTerminated
    buf.extend(b'tag_view\x00')
    # Block offset is now 13 (4 + 9). Alloc(align=4) for assets → block aligns to 16
    # BUT: no padding in stream! The alignment is block-only.

    # XAsset array: [type, header_ptr]
    buf.extend(struct.pack('<i', ASSET_TYPE_XANIMPARTS))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))

    virtual_stream_size = len(buf) - virtual_stream_start
    # VIRTUAL block size must account for alignment: 4+9=13 → align to 16 → +3 then +8 = 24
    virtual_block_size = 4 + 9 + 3 + 8  # 24 (includes alignment padding in block memory)

    # ---- TEMP block data (XAnimParts) ----
    temp_stream_start = len(buf)

    # XAnimParts header (104 bytes)
    header = bytearray(104)
    struct.pack_into('<I', header, 0x00, PTR_FOLLOWING)  # name
    struct.pack_into('<H', header, 0x0E, 0)   # numframes = 0
    header[0x18 + 9] = 1  # 1 bone total
    struct.pack_into('<f', header, 0x30, 30.0)  # framerate
    struct.pack_into('<f', header, 0x34, 1.0)   # frequency
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

    # Resolved pointer data:
    # 1. Name (Alloc align=1): "test_idle\0"
    buf.extend(b'test_idle\x00')
    # 2. Names array (Alloc align=2): 1 uint16
    # No stream padding for align=2, but block pads. Stream just has the data.
    # Wait - name is 10 bytes. Block offset = 104 + 10 = 114. Align(2) → 114 (already even).
    buf.extend(struct.pack('<H', 0))  # bone index 0

    temp_stream_size = len(buf) - temp_stream_start
    # TEMP block size: 104 + 10 + 2 = 116 (no alignment padding needed)
    temp_block_size = temp_stream_size

    # Patch header
    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    struct.pack_into('<I', buf, block_pos + BLOCK_TEMP * 4, temp_block_size)
    struct.pack_into('<I', buf, block_pos + BLOCK_VIRTUAL * 4, virtual_block_size)

    print(f"  totalSize={total_size}")
    print(f"  VIRTUAL: stream={virtual_stream_size}, block={virtual_block_size}")
    print(f"  TEMP: stream={temp_stream_size}, block={temp_block_size}")

    return bytes(buf)


def test_1xanim_with_pad():
    """For comparison: WITH stream padding."""
    print("\n=== Test: 1 xanim, WITH stream alignment padding ===")
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

    virtual_start = len(buf)
    buf.extend(struct.pack('<I', PTR_FOLLOWING))
    buf.extend(b'tag_view\x00')
    # WITH padding
    while (len(buf) - virtual_start) % 4 != 0:
        buf.append(0)
    buf.extend(struct.pack('<i', ASSET_TYPE_XANIMPARTS))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))
    virtual_size = len(buf) - virtual_start

    temp_start = len(buf)
    header = bytearray(104)
    struct.pack_into('<I', header, 0x00, PTR_FOLLOWING)
    struct.pack_into('<H', header, 0x0E, 0)
    header[0x18 + 9] = 1
    struct.pack_into('<f', header, 0x30, 30.0)
    struct.pack_into('<f', header, 0x34, 1.0)
    struct.pack_into('<I', header, 0x40, PTR_FOLLOWING)
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
    buf.extend(b'test_idle\x00')
    buf.extend(struct.pack('<H', 0))
    temp_size = len(buf) - temp_start

    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, 0, total_size)
    struct.pack_into('<I', buf, block_pos + BLOCK_TEMP * 4, temp_size)
    struct.pack_into('<I', buf, block_pos + BLOCK_VIRTUAL * 4, virtual_size)

    print(f"  totalSize={total_size}, VIRTUAL={virtual_size}, TEMP={temp_size}")
    return bytes(buf)


def main():
    raw1 = test_1xanim_no_pad()
    ff = os.path.join(OUTPUT_DIR, "test_format.ff")
    write_zone(raw1, "test_format", ff)
    print(f"  Result: {test_load(ff)}\n")

    raw2 = test_1xanim_with_pad()
    write_zone(raw2, "test_format", ff)
    print(f"  Result: {test_load(ff)}\n")


if __name__ == "__main__":
    main()
