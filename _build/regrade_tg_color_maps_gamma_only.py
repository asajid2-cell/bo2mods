#!/usr/bin/env python3
"""Gamma-only BO3 -> BO2 color-map adaptation for thundergun.

Uses only a gamma lift on original color maps (no hue/saturation shifts).
This targets the likely sRGB/linear mismatch that causes dark results.
"""

import glob
import os
import shutil
import struct
import subprocess
from pathlib import Path

from PIL import Image


ROOT = Path(r"z:\Games\pluto_t6_full_game")
BUILD = ROOT / "_build"
SRC_DDS_DIR = BUILD / "panzer_work" / "unlinked" / "images"
WORK_DIR = BUILD / "_tmp_tg_gamma_only"
TEXCONV = ROOT / "tools" / "texconv.exe"
PLUT_IMAGES = Path(os.path.expandvars(r"%localappdata%\Plutonium\storage\t6\images"))


def read_dds(path: Path):
    with open(path, "rb") as f:
        if f.read(4) != b"DDS ":
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
        payload = f.read()

    mips = []
    off = 0
    mw, mh = w, h
    for _ in range(mip_count):
        bw = max(1, mw // 4)
        bh = max(1, mh // 4)
        sz = bw * bh * 16
        mips.append((mw, mh, payload[off : off + sz]))
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
    with open(path, "wb") as f:
        f.write(hdr)
        for _mw, _mh, data in reversed(mips):  # smallest->largest
            f.write(data)


def to_dxt5(png_path: Path, out_dir: Path) -> Path:
    cmd = [
        str(TEXCONV),
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
        raise RuntimeError(f"texconv failed for {png_path.name}\n{res.stdout}\n{res.stderr}")
    return out_dir / f"{png_path.stem}.DDS"


def gamma_lift_rgba(img: Image.Image, gamma: float = 0.45) -> Image.Image:
    # gamma < 1 brightens. Pure channel lift only.
    rgba = img.convert("RGBA")
    r, g, b, _a = rgba.split()
    lut = [min(255, max(0, int(((i / 255.0) ** gamma) * 255.0 + 0.5))) for i in range(256)]
    r = r.point(lut)
    g = g.point(lut)
    b = b.point(lut)
    a = Image.new("L", rgba.size, 255)
    return Image.merge("RGBA", (r, g, b, a))


def main() -> None:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    PLUT_IMAGES.mkdir(parents=True, exist_ok=True)

    files = sorted(SRC_DDS_DIR.glob("tg_*_c.dds"))
    if not files:
        raise RuntimeError(f"No tg_*_c.dds found in {SRC_DDS_DIR}")

    print(f"Gamma-only regrade for {len(files)} maps...")
    for src in files:
        base = src.stem
        rogue = f"rogue_{base}"

        png = WORK_DIR / f"{rogue}.png"
        dds = WORK_DIR / f"{rogue}.DDS"
        iwi = WORK_DIR / f"{rogue}.iwi"
        loose = PLUT_IMAGES / f"{rogue}.iwi"

        img = Image.open(src)
        out = gamma_lift_rgba(img, gamma=0.45)
        out.save(png)

        made = to_dxt5(png, WORK_DIR)
        if made != dds and made.exists():
            shutil.move(str(made), str(dds))

        w, h, mips, iwi_fmt = read_dds(dds)
        write_iwi(iwi, w, h, mips, iwi_fmt)

        bak = loose.with_suffix(loose.suffix + ".bak_before_gamma_only")
        if loose.exists() and not bak.exists():
            shutil.copy2(loose, bak)
        shutil.copy2(iwi, loose)
        print(f"  {src.name} -> {loose.name} ({w}x{h})")

    print("Done.")


if __name__ == "__main__":
    main()
