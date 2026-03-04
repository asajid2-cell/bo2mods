#!/usr/bin/env python3
"""Convert DDS files (DXT5/BC3 and BC5/DXN) to T6 IWI v0x1B format.

Handles both standard DDS headers and DX10 extended headers.
"""
import struct
import os
import glob
import shutil

# T6 IWI v0x1B header: 64 bytes
# offset 0-2:   "IWi" magic
# offset 3:     version (0x1B)
# offset 4:     format (0x0D = DXT5/BC3, 0x0E = DXN/BC5)
# offset 5:     flags (0x00)
# offset 6-7:   width (uint16 LE)
# offset 8-9:   height (uint16 LE)
# offset 10-11: depth (uint16 LE)
# offset 12-31: reserved/padding (20 bytes of zeros)
# offset 32-63: fileSizeForPicmip[8] (8 x int32 LE)

IWI_HEADER_SIZE = 64
IWI_MAGIC = b"IWi"
IWI_VERSION = 0x1B
IWI_FORMAT_DXT5 = 0x0D  # BC3
IWI_FORMAT_DXN = 0x0E   # BC5

# DDS header constants
DDS_MAGIC = b"DDS "
DDS_HEADER_SIZE = 124  # bytes after the 4-byte magic

# DXGI format IDs
DXGI_FORMAT_BC5_UNORM = 83
DXGI_FORMAT_BC5_SNORM = 84


def read_dds(path):
    """Read a DDS file, handling both standard and DX10 extended headers.

    Returns: (width, height, mips, iwi_format)
        mips: list of (w, h, pixel_data) tuples, largest-to-smallest
        iwi_format: 0x0D for DXT5/BC3, 0x0E for BC5/DXN
    """
    with open(path, "rb") as f:
        magic = f.read(4)
        assert magic == DDS_MAGIC, f"Not a DDS file: {path}"

        header = f.read(DDS_HEADER_SIZE)

        # Parse standard DDS header fields
        height = struct.unpack_from("<I", header, 8)[0]
        width = struct.unpack_from("<I", header, 12)[0]
        mip_count = struct.unpack_from("<I", header, 24)[0]

        # Pixel format FourCC at offset 80 of header (72 + 8 for pf_size + pf_flags)
        pf_fourcc = header[80:84]

        # Detect format and handle DX10 extended header
        if pf_fourcc == b"DX10":
            # Read 20-byte DX10 extension header
            dx10_header = f.read(20)
            dxgi_format = struct.unpack_from("<I", dx10_header, 0)[0]
            if dxgi_format in (DXGI_FORMAT_BC5_UNORM, DXGI_FORMAT_BC5_SNORM):
                iwi_format = IWI_FORMAT_DXN
            else:
                print(f"  WARNING: Unknown DXGI format {dxgi_format}, defaulting to DXT5")
                iwi_format = IWI_FORMAT_DXT5
        elif pf_fourcc == b"DXT5":
            iwi_format = IWI_FORMAT_DXT5
        elif pf_fourcc == b"DXT1":
            # DXT1 = BC1, 8 bytes per block instead of 16
            print(f"  WARNING: DXT1 format not fully supported, treating as DXT5 block size")
            iwi_format = IWI_FORMAT_DXT5
        else:
            print(f"  WARNING: Unknown FourCC {pf_fourcc!r}, defaulting to DXT5")
            iwi_format = IWI_FORMAT_DXT5

        # Read all remaining pixel data (after all headers)
        all_data = f.read()

    # Both DXT5 and BC5 use 16 bytes per 4x4 block
    # Mips stored largest to smallest in DDS
    mips = []
    offset = 0
    w, h = width, height
    for i in range(mip_count):
        bw = max(1, w // 4)
        bh = max(1, h // 4)
        mip_size = bw * bh * 16  # 16 bytes per block
        mip_data = all_data[offset:offset + mip_size]
        if len(mip_data) != mip_size:
            print(f"  WARNING: Mip {i} ({w}x{h}) expected {mip_size} bytes, got {len(mip_data)}")
        mips.append((w, h, mip_data))
        offset += mip_size
        w = max(1, w // 2)
        h = max(1, h // 2)

    remaining = len(all_data) - offset
    if remaining > 0:
        print(f"  WARNING: {remaining} extra bytes after all mips")

    return width, height, mips, iwi_format


def create_iwi(width, height, mips, iwi_format, output_path):
    """Create a T6 IWI file from mip data.

    Args:
        mips: list of (w, h, data) tuples, largest-to-smallest (DDS order)
        iwi_format: 0x0D (DXT5) or 0x0E (BC5/DXN)
    """
    num_mips = len(mips)

    # Calculate fileSizeForPicmip[8]
    # picmip[i] = header_size + sum of mip data from level i down to smallest
    picmip = [0] * 8
    for i in range(8):
        if i < num_mips:
            data_size = sum(len(mips[j][2]) for j in range(i, num_mips))
            picmip[i] = IWI_HEADER_SIZE + data_size
        else:
            picmip[i] = IWI_HEADER_SIZE + len(mips[-1][2])  # smallest mip

    # Build header
    header = bytearray(IWI_HEADER_SIZE)
    header[0:3] = IWI_MAGIC
    header[3] = IWI_VERSION
    header[4] = iwi_format
    header[5] = 0x00  # flags
    struct.pack_into("<H", header, 6, width)
    struct.pack_into("<H", header, 8, height)
    struct.pack_into("<H", header, 10, 1)  # depth
    for i in range(8):
        struct.pack_into("<I", header, 32 + i * 4, picmip[i])

    # Write file: header + mips (SMALLEST to LARGEST, reversed from DDS)
    with open(output_path, "wb") as f:
        f.write(header)
        for w, h, data in reversed(mips):
            f.write(data)

    total_size = IWI_HEADER_SIZE + sum(len(m[2]) for m in mips)
    fmt_name = "DXT5/BC3" if iwi_format == IWI_FORMAT_DXT5 else "BC5/DXN"
    print(f"  {os.path.basename(output_path):35s} {width}x{height} {num_mips} mips {fmt_name} -> {total_size:,} bytes")
    return total_size


def main():
    src_dir = r"z:\Games\pluto_t6_full_game\_build\panzer_work\unlinked\images"
    build_dir = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\images"
    plut_dir = os.path.expandvars(r"%localappdata%\Plutonium\storage\t6\images")

    os.makedirs(build_dir, exist_ok=True)
    os.makedirs(plut_dir, exist_ok=True)

    dds_files = sorted(glob.glob(os.path.join(src_dir, "tg_*.dds")))
    if not dds_files:
        print(f"No tg_*.dds files found in {src_dir}")
        return

    print(f"Converting {len(dds_files)} DDS files to T6 IWI v0x1B...")
    print(f"  Source:   {src_dir}")
    print(f"  Build:    {build_dir}")
    print(f"  Plutonium: {plut_dir}")
    print()

    total_bytes = 0
    for dds_path in dds_files:
        name = os.path.splitext(os.path.basename(dds_path))[0]
        iwi_name = f"{name}.iwi"

        build_path = os.path.join(build_dir, iwi_name)
        width, height, mips, iwi_format = read_dds(dds_path)
        sz = create_iwi(width, height, mips, iwi_format, build_path)
        total_bytes += sz

        # Also copy to Plutonium loose images
        plut_path = os.path.join(plut_dir, iwi_name)
        shutil.copy2(build_path, plut_path)

    print(f"\nDone! {len(dds_files)} IWI files created ({total_bytes:,} bytes total)")
    print(f"Files deployed to both build dir and Plutonium images dir.")


if __name__ == "__main__":
    main()
