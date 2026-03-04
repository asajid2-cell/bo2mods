#!/usr/bin/env python3
"""Create a small dark grey specular IWI texture for the thundergun materials."""
import struct
from pathlib import Path

# DXT5 (BC3) block for dark grey (RGB ~30,30,30, alpha=255)
# Alpha block: alpha0=255, alpha1=255, all indices=0 (means all pixels = 255 alpha)
# Color block: color0 and color1 both dark grey in RGB565
# RGB(30,30,30) in RGB565: R=30>>3=3, G=30>>2=7, B=30>>3=3
# RGB565 = (3 << 11) | (7 << 5) | 3 = 0x18E3
# Both colors same, all indices = 0

def make_rgb565(r, g, b):
    """Convert RGB888 to RGB565."""
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)

GREY_VALUE = 30  # Dark grey for subtle specular
color565 = make_rgb565(GREY_VALUE, GREY_VALUE, GREY_VALUE)

# DXT5 block: 8 bytes alpha + 8 bytes color = 16 bytes
# Alpha: alpha0=0xFF, alpha1=0xFF, 6 bytes of indices (all 0)
alpha_block = struct.pack('<BB6s', 0xFF, 0xFF, b'\x00' * 6)
# Color: color0=color1=grey, 4 bytes of indices (all 0 = use color0)
color_block = struct.pack('<HH4s', color565, color565, b'\x00' * 4)
dxt5_block = alpha_block + color_block  # 16 bytes total

def make_dds_dxt5(width, height, block_data):
    """Create a DDS file with DXT5 format."""
    # DDS header (128 bytes)
    magic = b'DDS '
    # dwSize=124, dwFlags=CAPS|HEIGHT|WIDTH|PIXELFORMAT|MIPMAPCOUNT|LINEARSIZE
    flags = 0x1 | 0x2 | 0x4 | 0x1000 | 0x20000 | 0x80000
    # Pixel format for DXT5
    pf_size = 32
    pf_flags = 0x4  # DDPF_FOURCC
    fourcc = b'DXT5'

    num_blocks_x = max(1, width // 4)
    num_blocks_y = max(1, height // 4)
    linear_size = num_blocks_x * num_blocks_y * 16

    header = struct.pack('<4sIIIIII44sIIII8sII20sII16s',
        magic,           # magic
        124,             # dwSize
        flags,           # dwFlags
        height,          # dwHeight
        width,           # dwWidth
        linear_size,     # dwPitchOrLinearSize
        0,               # dwDepth
        b'\x00' * 44,    # dwMipMapCount(=1) + reserved
        pf_size,         # ddspf.dwSize
        pf_flags,        # ddspf.dwFlags
        fourcc[0] | (fourcc[1] << 8) | (fourcc[2] << 16) | (fourcc[3] << 24),  # dwFourCC
        0,               # dwRGBBitCount
        b'\x00' * 8,     # R/G masks (unused for DXT)
        0, 0,            # B/A masks
        b'\x00' * 20,    # padding
        0x1000,          # dwCaps = TEXTURE
        0,               # dwCaps2
        b'\x00' * 16     # padding
    )

    return header[:128] + block_data


def make_iwi_t6(width, height, dxt5_data):
    """Create a T6 IWI v0x1B file from DXT5 data."""
    MAGIC = b'IWi'
    VERSION = 0x1B
    FORMAT = 0x0E  # DXT5/BC3
    FLAGS = 0x00

    mip_data = dxt5_data
    data_size = len(mip_data)
    header_size = 64
    total_size = header_size + data_size

    # fileSizeForPicmip[8]: entry[0] = total file size, rest = same for single mip
    picmip = [total_size] + [total_size] * 7

    header = MAGIC
    header += struct.pack('<B', VERSION)
    header += struct.pack('<B', FORMAT)
    header += struct.pack('<B', FLAGS)
    header += struct.pack('<HHH', width, height, 1)  # width, height, depth
    header += b'\x00' * 20  # padding
    for p in picmip:
        header += struct.pack('<i', p)

    assert len(header) == 64
    return header + mip_data


def main():
    # Create a 4x4 DXT5 texture (single block)
    width, height = 4, 4

    print(f"Creating {width}x{height} dark grey specular texture (value={GREY_VALUE})")

    # Single DXT5 block for 4x4
    dxt5_data = dxt5_block

    output_dir = Path(r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\images")
    pluto_dir = Path.home() / "AppData" / "Local" / "Plutonium" / "storage" / "t6" / "images"

    # Create IWI
    iwi_data = make_iwi_t6(width, height, dxt5_data)

    iwi_name = "tg_default_spec"
    iwi_path = output_dir / f"{iwi_name}.iwi"
    iwi_path.write_bytes(iwi_data)
    print(f"Created {iwi_path} ({len(iwi_data)} bytes)")

    # Also copy to Plutonium images folder
    pluto_path = pluto_dir / f"{iwi_name}.iwi"
    pluto_path.write_bytes(iwi_data)
    print(f"Copied to {pluto_path}")

    # Create DDS too (for IPak building)
    dds_data = make_dds_dxt5(width, height, dxt5_data)
    dds_path = output_dir / f"{iwi_name}.dds"
    dds_path.write_bytes(dds_data)
    print(f"Created {dds_path} ({len(dds_data)} bytes)")

    print(f"\nDone! Use image name '{iwi_name}' as specularMap in all materials.")


if __name__ == "__main__":
    main()
