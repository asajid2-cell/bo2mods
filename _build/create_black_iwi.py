"""
Create a tiny 4x4 solid black DXT5 IWI file for use as specular map.
T6 IWI v0x1B header layout (64 bytes):
  0x00-0x02: "IWi" magic
  0x03: version (0x1B)
  0x04: format (0x0D = DXT5/BC3)
  0x05: flags (0x00)
  0x06-0x07: width (uint16 LE)
  0x08-0x09: height (uint16 LE)
  0x0A-0x0B: depth (uint16 LE)
  0x0C-0x1F: zeros (padding/maxGloss/etc)
  0x20-0x3F: fileSizeForPicmip[0..7] (8 x uint32 LE)
"""
import struct
import os

output_dir = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\images"

header = bytearray(64)

# Magic + version
header[0:3] = b"IWi"
header[3] = 0x1B

# Format at byte 4 (0x0D = DXT5), flags at byte 5
header[4] = 0x0D  # DXT5/BC3 (matches working IWIs)
header[5] = 0x00  # flags

# Dimensions (uint16 LE)
struct.pack_into("<H", header, 6, 4)    # width = 4
struct.pack_into("<H", header, 8, 4)    # height = 4
struct.pack_into("<H", header, 10, 1)   # depth = 1

# Bytes 0x0C-0x1F: zeros (already zeroed)

# Mip data: 3 levels (4x4, 2x2, 1x1), stored smallest first
# Each DXT5 block = 16 bytes (min 4x4 block)
# 1x1 -> 1 block = 16 bytes
# 2x2 -> 1 block = 16 bytes
# 4x4 -> 1 block = 16 bytes
# Total mip data = 48 bytes, file = 112 bytes

# fileSizeForPicmip at offset 0x20
picmip = [
    64 + 48,  # [0] = 112 (all mips: 4x4 + 2x2 + 1x1)
    64 + 32,  # [1] = 96  (skip 4x4, include 2x2 + 1x1)
    64 + 16,  # [2] = 80  (only 1x1)
    64 + 16,  # [3] = 80
    64 + 16,  # [4] = 80
    64 + 16,  # [5] = 80
    64 + 16,  # [6] = 80
    64 + 16,  # [7] = 80
]
for i in range(8):
    struct.pack_into("<I", header, 0x20 + i * 4, picmip[i])

# DXT5 block for solid black (fully opaque):
# Alpha: alpha0=255, alpha1=0, all indices=0 (point to alpha0=255)
# Color: color0=0 (black), color1=0 (black), all indices=0
black_block = bytes([
    0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # alpha
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # color (black)
])

# Write: header + mip data (1x1, 2x2, 4x4 = 3 identical black blocks)
output_path = os.path.join(output_dir, "tg_specular_black.iwi")
with open(output_path, "wb") as f:
    f.write(header)
    f.write(black_block)  # 1x1 mip (smallest first)
    f.write(black_block)  # 2x2 mip
    f.write(black_block)  # 4x4 mip (largest last)

file_size = os.path.getsize(output_path)
print(f"Created: {output_path}")
print(f"Size: {file_size} bytes (expected 112)")

# Verify header
with open(output_path, "rb") as f:
    data = f.read()
    assert data[0:3] == b"IWi", "Bad magic"
    assert data[3] == 0x1B, "Bad version"
    assert data[4] == 0x0D, f"Bad format: {data[4]:#x}"
    w = struct.unpack_from("<H", data, 6)[0]
    h = struct.unpack_from("<H", data, 8)[0]
    assert w == 4 and h == 4, f"Bad dimensions: {w}x{h}"
    p0 = struct.unpack_from("<I", data, 0x20)[0]
    assert p0 == 112, f"Bad picmip[0]: {p0}"
    print(f"Verified: {w}x{h} DXT5 IWI v0x1B, format=0x{data[4]:02x}, picmip[0]={p0}")
