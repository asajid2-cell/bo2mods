#!/usr/bin/env python3
"""Create a minimal T6 zone with 1 xanim to test format correctness."""
import struct
import zlib
import hashlib
import os
from Crypto.Cipher import Salsa20

# Import from compile_xanim_zone
from compile_xanim_zone import (
    XChunkWriter, T6_ZONE_MAGIC_UNSIGNED, T6_ZONE_VERSION,
    PTR_FOLLOWING, PTR_NULL, ASSET_TYPE_XANIMPARTS, XFILE_BLOCK_COUNT
)

def build_minimal_zone():
    """Build the simplest possible zone: 1 xanim, 1 bone, 1 frame (idle pose)."""
    zone_name = "test_xanim"

    # Single bone name
    bone_name = "tag_view"

    # ---- Build XAnimParts header (104 bytes) ----
    header = bytearray(104)

    # name pointer
    struct.pack_into('<I', header, 0x00, PTR_FOLLOWING)

    # All data counts = 0 (minimal)
    struct.pack_into('<H', header, 0x04, 0)   # dataByteCount
    struct.pack_into('<H', header, 0x06, 0)   # dataShortCount
    struct.pack_into('<H', header, 0x08, 0)   # dataIntCount
    struct.pack_into('<H', header, 0x0A, 0)   # randomDataByteCount
    struct.pack_into('<H', header, 0x0C, 0)   # randomDataIntCount
    struct.pack_into('<H', header, 0x0E, 0)   # numframes (0 = single frame)

    header[0x10] = 0  # bLoop
    header[0x11] = 0  # bDelta
    header[0x12] = 0  # bDelta3D
    header[0x13] = 0  # bLeftHandGripIK
    struct.pack_into('<I', header, 0x14, 0)  # streamedFileSize

    # boneCount[10] - just 1 bone
    for i in range(10):
        header[0x18 + i] = 0
    header[0x18 + 9] = 1  # total bones = 1

    header[0x22] = 0   # notifyCount
    header[0x23] = 0   # assetType
    header[0x24] = 0   # isDefault

    struct.pack_into('<I', header, 0x28, 0)  # randomDataShortCount
    struct.pack_into('<I', header, 0x2C, 0)  # indexCount
    struct.pack_into('<f', header, 0x30, 30.0)  # framerate
    struct.pack_into('<f', header, 0x34, 1.0)   # frequency
    struct.pack_into('<f', header, 0x38, 0.0)   # primedLength
    struct.pack_into('<f', header, 0x3C, 0.0)   # loopEntryTime

    # Pointer fields - only name and names are non-null
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

    # ---- XAnimParts pointer data ----
    anim_data = bytearray()
    # 1. Name string
    anim_name = "test_idle"
    anim_data.extend(anim_name.encode('ascii') + b'\x00')
    # Align to 2
    while len(anim_data) % 2 != 0:
        anim_data.append(0)
    # 2. Names array (1 entry, uint16 index)
    anim_data.extend(struct.pack('<H', 0))  # string index 0

    # ---- Build zone ----
    buf = bytearray()

    # XFile header
    total_size_pos = len(buf)
    buf.extend(struct.pack('<I', 0))  # totalSize placeholder
    buf.extend(struct.pack('<I', 0))  # externalSize

    block_sizes_pos = len(buf)
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))

    content_start = len(buf)
    virtual_start = len(buf)

    # ScriptStringList
    buf.extend(struct.pack('<i', 1))             # count = 1
    buf.extend(struct.pack('<I', PTR_FOLLOWING))  # strings ptr
    buf.extend(struct.pack('<I', PTR_FOLLOWING))  # strings[0] ptr
    buf.extend(bone_name.encode('ascii') + b'\x00')  # "tag_view\0"

    # Depends
    buf.extend(struct.pack('<i', 0))
    buf.extend(struct.pack('<I', PTR_NULL))

    # Assets
    buf.extend(struct.pack('<i', 1))             # count = 1
    buf.extend(struct.pack('<I', PTR_FOLLOWING))  # assets ptr
    buf.extend(struct.pack('<i', ASSET_TYPE_XANIMPARTS))
    buf.extend(struct.pack('<I', PTR_FOLLOWING))  # header ptr

    virtual_size = len(buf) - virtual_start
    temp_start = len(buf)

    # XAnimParts data (TEMP block)
    buf.extend(header)
    buf.extend(anim_data)

    temp_size = len(buf) - temp_start

    # Patch sizes
    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, total_size_pos, total_size)

    block_sizes = [0] * XFILE_BLOCK_COUNT
    block_sizes[0] = temp_size
    block_sizes[3] = virtual_size
    for i in range(XFILE_BLOCK_COUNT):
        struct.pack_into('<I', buf, block_sizes_pos + i * 4, block_sizes[i])

    print(f"Zone content: {total_size} bytes")
    print(f"  VIRTUAL: {virtual_size}, TEMP: {temp_size}, sum: {virtual_size + temp_size}")
    print(f"  Sum == total: {total_size == virtual_size + temp_size}")

    # Hex dump of the raw zone
    print(f"\nFull raw zone hex dump ({len(buf)} bytes):")
    for i in range(0, len(buf), 16):
        hex_bytes = ' '.join(f'{buf[i + j]:02X}' for j in range(min(16, len(buf) - i)))
        ascii_chars = ''.join(chr(buf[i + j]) if 32 <= buf[i + j] < 127 else '.' for j in range(min(16, len(buf) - i)))
        print(f"  {i:04X}: {hex_bytes:<48} {ascii_chars}")

    return bytes(buf), zone_name


def main():
    raw_data, zone_name = build_minimal_zone()

    output_dir = r"z:\Games\pluto_t6_full_game\_build\panzer_work\output"
    output_ff = os.path.join(output_dir, f"{zone_name}.ff")

    # Write with XChunk encryption
    xchunk = XChunkWriter(zone_name)
    xchunk.write_data(raw_data)
    encrypted = xchunk.get_output()

    with open(output_ff, 'wb') as f:
        f.write(T6_ZONE_MAGIC_UNSIGNED)
        f.write(struct.pack('<I', T6_ZONE_VERSION))
        f.write(encrypted)
        padding = 0x40 - (f.tell() % 0x40)
        if padding < 0x40:
            padding += 0x40
        f.write(b'\x00' * padding)

    print(f"\nWrote {os.path.getsize(output_ff)} bytes to {output_ff}")

    # Test with OAT linker - just try to load it
    import subprocess
    linker = r"z:\Games\pluto_t6_full_game\tools\oat\Linker.exe"

    # Create a minimal zone source that just loads our test zone
    test_zone_dir = os.path.join(output_dir, "test_zone")
    os.makedirs(os.path.join(test_zone_dir, "zone_source"), exist_ok=True)

    # Write a dummy zone source
    with open(os.path.join(test_zone_dir, "zone_source", "empty_test.zone"), 'w') as f:
        f.write("// Empty zone to test loading\n")
        f.write("xanim,test_idle\n")

    args = [
        linker, "--verbose",
        "--base-folder", test_zone_dir,
        "--output-folder", output_dir,
        "--load", output_ff,
        "empty_test"
    ]

    print(f"\nTesting load with OAT...")
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    print(result.stdout)
    print(result.stderr)


if __name__ == "__main__":
    main()
