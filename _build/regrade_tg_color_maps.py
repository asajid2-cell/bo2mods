#!/usr/bin/env python3
"""Regrade BO3 thundergun color maps to a BO2-friendly diffuse look.

Pipeline:
  source DDS (_build/panzer_work/unlinked/images/tg_*_c.dds)
    -> decode with Pillow
    -> color grade (boost saturation/contrast/brightness + warm bias)
    -> encode to DXT5 DDS via texconv
    -> convert DDS to T6 IWI
    -> deploy loose overrides as rogue_tg_*_c.iwi
"""

import glob
import os
import shutil
import struct
import subprocess
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps


ROOT = Path(r"z:\Games\pluto_t6_full_game")
BUILD = ROOT / "_build"
SRC_DDS_DIR = BUILD / "panzer_work" / "unlinked" / "images"
WORK_DIR = BUILD / "_tmp_tg_regrade"
TOOLS_TEXCONV = ROOT / "tools" / "texconv.exe"
PLUT_IMAGES = Path(os.path.expandvars(r"%localappdata%\Plutonium\storage\t6\images"))


def ensure_dirs() -> None:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    PLUT_IMAGES.mkdir(parents=True, exist_ok=True)


def grade_image(img: Image.Image) -> Image.Image:
    rgba = img.convert("RGBA")
    r, g, b, _a = rgba.split()
    rgb = Image.merge("RGB", (r, g, b))

    # Lift BO3 PBR-style dark albedo into BO2 diffuse-friendly range.
    rgb = ImageOps.autocontrast(rgb, cutoff=(1, 1))
    rgb = ImageEnhance.Color(rgb).enhance(2.1)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.08)
    rgb = ImageEnhance.Brightness(rgb).enhance(1.7)

    rr, gg, bb = rgb.split()

    # Gamma lift shadows/midtones.
    gamma = 0.72
    inv_255 = 1.0 / 255.0
    rr = rr.point(lambda x: min(255, int(((x * inv_255) ** gamma) * 255.0)))
    gg = gg.point(lambda x: min(255, int(((x * inv_255) ** gamma) * 255.0)))
    bb = bb.point(lambda x: min(255, int(((x * inv_255) ** gamma) * 255.0)))

    # Slight warm bias.
    rr = rr.point(lambda x: min(255, int(x * 1.06 + 6)))
    gg = gg.point(lambda x: min(255, int(x * 1.01 + 2)))
    bb = bb.point(lambda x: min(255, int(x * 0.93)))

    # Force fully opaque alpha for color maps.
    aa = Image.new("L", rgb.size, 255)
    return Image.merge("RGBA", (rr, gg, bb, aa))


def run_texconv(png_path: Path, out_dir: Path) -> Path:
    cmd = [
        str(TOOLS_TEXCONV),
        "-y",
        "-f",
        "DXT5",
        "-m",
        "0",
        "-o",
        str(out_dir),
        str(png_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"texconv failed for {png_path.name}: {res.stdout}\n{res.stderr}")
    return out_dir / (png_path.stem + ".DDS")


def read_dds(path: Path):
    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != b"DDS ":
            raise RuntimeError(f"Not DDS: {path}")
        header = f.read(124)
        h = struct.unpack_from("<I", header, 8)[0]
        w = struct.unpack_from("<I", header, 12)[0]
        mip_count = struct.unpack_from("<I", header, 24)[0]
        fourcc = header[80:84]
        if fourcc == b"DX10":
            dx10 = f.read(20)
            dxgi = struct.unpack_from("<I", dx10, 0)[0]
            iwi_fmt = 0x0E if dxgi in (83, 84) else 0x0D
        else:
            iwi_fmt = 0x0D
        all_data = f.read()

    mips = []
    off = 0
    mw, mh = w, h
    for _ in range(mip_count):
        bw = max(1, mw // 4)
        bh = max(1, mh // 4)
        sz = bw * bh * 16
        mips.append((mw, mh, all_data[off : off + sz]))
        off += sz
        mw = max(1, mw // 2)
        mh = max(1, mh // 2)
    return w, h, mips, iwi_fmt


def write_iwi(path: Path, w: int, h: int, mips, iwi_fmt: int) -> None:
    hdr = bytearray(64)
    hdr[0:3] = b"IWi"
    hdr[3] = 0x1B
    hdr[4] = iwi_fmt
    hdr[5] = 0
    struct.pack_into("<H", hdr, 6, w)
    struct.pack_into("<H", hdr, 8, h)
    struct.pack_into("<H", hdr, 10, 1)

    for i in range(8):
        if i < len(mips):
            data_sz = sum(len(mips[j][2]) for j in range(i, len(mips)))
            v = 64 + data_sz
        else:
            v = 64 + len(mips[-1][2])
        struct.pack_into("<I", hdr, 32 + i * 4, v)

    payload = b"".join(m[2] for m in reversed(mips))  # smallest->largest
    with open(path, "wb") as f:
        f.write(hdr)
        f.write(payload)


def main() -> None:
    ensure_dirs()
    src_dds = sorted(SRC_DDS_DIR.glob("tg_*_c.dds"))
    if not src_dds:
        raise RuntimeError(f"No tg_*_c.dds in {SRC_DDS_DIR}")

    print(f"Regrading {len(src_dds)} color maps...")
    for src in src_dds:
        base = src.stem  # tg_xxx_c
        rogue = f"rogue_{base}"  # rogue_tg_xxx_c

        png_path = WORK_DIR / f"{rogue}.png"
        dds_path = WORK_DIR / f"{rogue}.DDS"
        iwi_path = WORK_DIR / f"{rogue}.iwi"
        dst_loose = PLUT_IMAGES / f"{rogue}.iwi"

        # Decode + grade
        img = Image.open(src)
        graded = grade_image(img)
        graded.save(png_path)

        # Encode back to DXT5 DDS
        out_dds = run_texconv(png_path, WORK_DIR)
        if out_dds != dds_path and out_dds.exists():
            shutil.move(str(out_dds), str(dds_path))

        # DDS -> IWI
        w, h, mips, iwi_fmt = read_dds(dds_path)
        write_iwi(iwi_path, w, h, mips, iwi_fmt)

        # Deploy as loose override (backup once)
        backup = dst_loose.with_suffix(dst_loose.suffix + ".bak_before_regrade")
        if dst_loose.exists() and not backup.exists():
            shutil.copy2(dst_loose, backup)
        shutil.copy2(iwi_path, dst_loose)

        print(f"  {src.name} -> {dst_loose.name} ({w}x{h})")

    print("Done. Test in-game with loose rogue_tg_*_c overrides.")


if __name__ == "__main__":
    main()
