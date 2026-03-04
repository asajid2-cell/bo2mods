from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def default_blender_exe() -> str:
    candidates = [
        Path(r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return "blender"


def default_blender_cod_root(repo_root: Path) -> Path:
    candidates = [
        repo_root / "tools" / "external" / "blender-cod-src",
        repo_root / "tools" / "external" / "blender-cod-master" / "blender-cod-master",
        repo_root / "_tmp_tools" / "blender-cod-master" / "blender-cod-master",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def run(args: argparse.Namespace) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    worker_script = repo_root / "tools" / "asset_port_pipeline" / "blender_cod_bin_worker.py"
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    blender_cod_root = Path(args.blender_cod_root).resolve() if args.blender_cod_root else default_blender_cod_root(repo_root)
    blender_exe = args.blender_exe or default_blender_exe()

    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")
    if not worker_script.exists():
        raise FileNotFoundError(f"Missing worker script: {worker_script}")
    if not blender_cod_root.exists():
        raise FileNotFoundError(
            "blender-cod source not found. Expected: "
            f"{blender_cod_root} (or pass --blender-cod-root)."
        )

    cmd = [
        blender_exe,
        "--background",
        "--factory-startup",
        "--python",
        str(worker_script),
        "--",
        "--asset-kind",
        args.asset_kind,
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--blender-cod-root",
        str(blender_cod_root),
        "--scale",
        str(args.scale),
    ]

    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)
    if args.verbose:
        print("[cmd]", " ".join(cmd))
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip(), file=sys.stderr)
    if proc.returncode != 0:
        return proc.returncode
    if not output_path.exists():
        print(f"Expected output missing after conversion: {output_path}", file=sys.stderr)
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert CoD .XMODEL_BIN/.xanim_bin assets using Blender + blender-cod parser."
    )
    parser.add_argument("--asset-kind", choices=["xmodel", "xanim"], required=True)
    parser.add_argument("--input", required=True, help="Input .XMODEL_BIN/.XMODEL_EXPORT or .xanim_bin/.xanim_export file")
    parser.add_argument("--output", required=True, help="Output file path (.glb for xmodel, .xanim_export for xanim)")
    parser.add_argument("--blender-exe", default="", help="Blender executable path")
    parser.add_argument("--blender-cod-root", default="", help="Path containing io_scene_cod package")
    parser.add_argument("--scale", type=float, default=1.0, help="Scale multiplier for xmodel conversion")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    code = run(args)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
