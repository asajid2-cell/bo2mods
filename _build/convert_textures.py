"""Convert BO3 Thundergun PNG textures to T6 IWI via DDS intermediate."""
import struct
import sys
import os
import subprocess
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)


def write_dds_bgra(img: Image.Image, out_path: str):
    """Write an uncompressed BGRA8888 DDS file from a PIL Image."""
    img = img.convert("RGBA")
    w, h = img.size

    # DDS constants
    DDS_MAGIC = b"DDS "
    DDSD_CAPS = 0x1
    DDSD_HEIGHT = 0x2
    DDSD_WIDTH = 0x4
    DDSD_PIXELFORMAT = 0x1000
    DDSD_LINEARSIZE = 0x80000
    DDPF_ALPHAPIXELS = 0x1
    DDPF_RGB = 0x40
    DDSCAPS_TEXTURE = 0x1000

    flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_LINEARSIZE
    pitch = w * 4  # 4 bytes per pixel (BGRA)

    # DDS_PIXELFORMAT (32 bytes)
    pf_size = 32
    pf_flags = DDPF_RGB | DDPF_ALPHAPIXELS
    pf_fourcc = 0
    pf_bitcount = 32
    pf_rmask = 0x00FF0000  # R
    pf_gmask = 0x0000FF00  # G
    pf_bmask = 0x000000FF  # B
    pf_amask = 0xFF000000  # A

    pixelformat = struct.pack("<IIIIIIII",
        pf_size, pf_flags, pf_fourcc, pf_bitcount,
        pf_rmask, pf_gmask, pf_bmask, pf_amask)

    # DDS_HEADER (124 bytes)
    header = struct.pack("<III", flags, h, w)
    header += struct.pack("<I", pitch)  # pitchOrLinearSize
    header += struct.pack("<I", 0)      # depth
    header += struct.pack("<I", 0)      # mipMapCount
    header += b"\x00" * 44             # reserved1[11]
    header += pixelformat
    header += struct.pack("<I", DDSCAPS_TEXTURE)  # caps
    header += struct.pack("<I", 0)      # caps2
    header += struct.pack("<I", 0)      # caps3
    header += struct.pack("<I", 0)      # caps4
    header += struct.pack("<I", 0)      # reserved2

    # Pixel data: BGRA order (DDS convention)
    pixels = img.tobytes("raw", "BGRA")

    with open(out_path, "wb") as f:
        f.write(DDS_MAGIC)
        f.write(struct.pack("<I", 124))  # header size
        f.write(header)
        f.write(pixels)


def main():
    root = Path(r"z:\Games\pluto_t6_full_game")
    png_dir = root / "_build/asset_port_pipeline/thundergun_bo2_transfer/t7_bundle/staged/model_export/_midgetblaster/weapons/t7/_images"
    dds_dir = root / "_build/img_test/dds"
    iwi_dir = root / "_build/panzer_work/so_zsurvival_zm_transit/images"
    converter = root / "tools/oat/ImageConverter.exe"

    dds_dir.mkdir(parents=True, exist_ok=True)
    iwi_dir.mkdir(parents=True, exist_ok=True)

    # Only convert _c (color) and _n (normal) textures - these are what T6 materials use
    pngs = sorted(png_dir.glob("*.png"))
    if not pngs:
        print("ERROR: No PNG files found")
        sys.exit(1)

    converted = []
    for png_path in pngs:
        stem = png_path.stem  # e.g., i_wpn_t7_zmb_hd_thundergun_back_body_a_c
        suffix = stem.rsplit("_", 1)[-1]  # e.g., c, n, s, g, o, r, e

        # Only process color maps for now (essential for visibility)
        if suffix not in ("c", "n"):
            continue

        dds_path = dds_dir / f"{stem}.dds"
        iwi_path = iwi_dir / f"{stem}.iwi"

        print(f"  PNG -> DDS: {stem}")
        img = Image.open(png_path)
        write_dds_bgra(img, str(dds_path))

        print(f"  DDS -> IWI: {stem}")
        proc = subprocess.run(
            [str(converter), str(dds_path)],
            input=b"5\n",  # Select T6
            capture_output=True, timeout=30
        )

        # ImageConverter writes IWI next to the DDS
        produced_iwi = dds_path.with_suffix(".iwi")
        if produced_iwi.exists():
            # Move to work dir images/
            if iwi_path.exists():
                iwi_path.unlink()
            produced_iwi.rename(iwi_path)
            converted.append(stem)
            print(f"    OK -> {iwi_path.name}")
        else:
            print(f"    FAILED - no IWI produced")
            if proc.stderr:
                print(f"    stderr: {proc.stderr.decode(errors='replace')[:200]}")

    print(f"\nConverted {len(converted)} images to IWI")
    for name in converted:
        print(f"  {name}")


if __name__ == "__main__":
    main()
