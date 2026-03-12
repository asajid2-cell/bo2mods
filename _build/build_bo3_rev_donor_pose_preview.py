#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "asset_port_pipeline"
WORKER = TOOLS / "blender_donor_pose_preview_worker.py"
DEFAULT_CUSTOM = ROOT / "_build" / "bo3_rev_idg_weapon_only" / "bo3_rev_idg_weapon_only.glb"
DEFAULT_DONOR = ROOT / "_build" / "runtime_unlink_zm_transit_full_1" / "model_export" / "t6_wpn_ar_m14_view_lod0.glb"
DEFAULT_VIEWHANDS = ROOT / "zone_dump" / "zone_raw" / "so_zsurvival_zm_transit" / "model_export" / "c_zom_hazmat_viewhands_lod0.glb"
DEFAULT_OUTPUT = ROOT / "_build" / "bo3_rev_m14_donor_pose_preview.blend"


def choose_blender_executable(configured: str) -> str:
    candidates = [configured]
    if configured.lower() == "blender":
        candidates += [
            r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
        ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return configured


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Blender donor-pose preview for the BO3 Rev weapon.")
    parser.add_argument("--blender-exe", default="blender")
    parser.add_argument("--custom-glb", default=str(DEFAULT_CUSTOM))
    parser.add_argument("--donor-glb", default=str(DEFAULT_DONOR))
    parser.add_argument("--viewhands-glb", default=str(DEFAULT_VIEWHANDS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--hide-donor", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    blender = choose_blender_executable(args.blender_exe)
    cmd = [
        blender,
        "-b",
        "--factory-startup",
        "--python-exit-code",
        "1",
        "--python",
        str(WORKER),
        "--",
        "--custom-glb",
        str(Path(args.custom_glb).resolve()),
        "--donor-glb",
        str(Path(args.donor_glb).resolve()),
        "--viewhands-glb",
        str(Path(args.viewhands_glb).resolve()),
        "--output",
        str(Path(args.output).resolve()),
    ]
    if args.hide_donor:
        cmd.append("--hide-donor")
    result = subprocess.run(cmd, cwd=str(ROOT))
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
