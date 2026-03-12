#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import struct
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools" / "asset_port_pipeline"
DEFAULT_OUT_DIR = ROOT / "_build" / "bo3_rev_idg_reduced"
DEFAULT_WEAPON_GLB = ROOT / "_build" / "asset_port_pipeline" / "tmp" / "idg_view.glb"
DEFAULT_HANDS_GLB = ROOT / "_build" / "asset_port_pipeline" / "tmp" / "bo3_richtofen_viewhands.glb"
DEFAULT_MANIFEST = TOOLS_DIR / "idg_reduced_rig_manifest.json"
DEFAULT_ANIM_DIR = ROOT / "_build" / "asset_port_pipeline" / "tmp"
DEFAULT_BLENDER_COD_ROOT = ROOT / "_tmp_tools" / "blender-cod-master" / "blender-cod-master"


def choose_blender_executable(configured: str) -> str:
    candidates = [configured]
    if configured.lower() == "blender":
        candidates += [
            "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe",
            "C:\\Program Files\\Blender Foundation\\Blender 4.1\\blender.exe",
            "C:\\Program Files\\Blender Foundation\\Blender 4.0\\blender.exe",
            "C:\\Program Files\\Blender Foundation\\Blender 3.6\\blender.exe",
        ]
    for candidate in candidates:
        candidate_path = Path(candidate)
        if candidate_path.exists():
            return str(candidate_path)
        if shutil.which(candidate):
            return candidate
    return configured


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and validate a reduced BO3 IDG rig for BO2/T6.")
    parser.add_argument("--weapon-glb", default=str(DEFAULT_WEAPON_GLB))
    parser.add_argument("--hands-glb", default=str(DEFAULT_HANDS_GLB))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--blender-exe", default="blender")
    parser.add_argument("--anim-dir", default=str(DEFAULT_ANIM_DIR))
    parser.add_argument("--anim-stems", default="vm_zod_id_gun_idle,vm_zod_id_gun_pullout,vm_zod_id_gun_fire")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    return parser.parse_args()


def read_glb_joint_names(path: Path) -> List[str]:
    with open(path, "rb") as handle:
        if handle.read(4) != b"glTF":
            raise RuntimeError(f"Not a GLB file: {path}")
        handle.read(4)
        total_len = struct.unpack("<I", handle.read(4))[0]
        json_len = struct.unpack("<I", handle.read(4))[0]
        if handle.read(4) != b"JSON":
            raise RuntimeError(f"Invalid JSON chunk in GLB: {path}")
        gltf = json.loads(handle.read(json_len).decode("utf-8"))
        if handle.tell() < total_len:
            pass
    nodes = gltf.get("nodes", [])
    skins = gltf.get("skins", [])
    if not skins:
        raise RuntimeError(f"No skin found in GLB: {path}")
    joints = skins[0].get("joints", [])
    return [str(nodes[index].get("name", "")) for index in joints]


def read_xanim_union(anim_paths: Iterable[Path]) -> List[str]:
    seen: Set[str] = set()
    ordered: List[str] = []
    for path in anim_paths:
        if not path.exists():
            raise FileNotFoundError(f"Missing animation export: {path}")
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped.startswith("PART ") and '"' in stripped:
                name = stripped.split('"')[1]
                if name not in seen:
                    seen.add(name)
                    ordered.append(name)
            if stripped.startswith("FRAMERATE"):
                break
    return ordered


def summarize_missing_bones(missing: Sequence[str]) -> Dict[str, int]:
    groups: Dict[str, int] = {}
    for name in missing:
        parts = name.split("_")
        if len(parts) >= 3 and parts[0] == "tag":
            key = "_".join(parts[:3])
        elif len(parts) >= 2 and parts[0] == "j":
            key = "_".join(parts[:2])
        else:
            key = parts[0]
        groups[key] = groups.get(key, 0) + 1
    return dict(sorted(groups.items()))


def run_reducer(
    blender_exe: str,
    worker_path: Path,
    weapon_glb: Path,
    hands_glb: Path,
    manifest_path: Path,
    output_glb: Path,
    metadata_out: Path,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        blender_exe,
        "-b",
        "--python-exit-code",
        "1",
        "--factory-startup",
        "--python",
        str(worker_path),
        "--",
        "--weapon-glb",
        str(weapon_glb),
        "--hands-glb",
        str(hands_glb),
        "--manifest",
        str(manifest_path),
        "--output",
        str(output_glb),
        "--metadata-out",
        str(metadata_out),
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def run_preview(
    blender_exe: str,
    preview_worker: Path,
    input_glb: Path,
    output_blend: Path,
    blender_cod_root: Path,
    anim_dir: Path,
    anim_stems: str,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        blender_exe,
        "-b",
        "--python-exit-code",
        "1",
        "--factory-startup",
        "--python",
        str(preview_worker),
        "--",
        "--input",
        str(input_glb),
        "--output",
        str(output_blend),
        "--blender-cod-root",
        str(blender_cod_root),
        "--anim-dir",
        str(anim_dir),
        "--anim-stems",
        anim_stems,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    output_glb = out_dir / "bo3_rev_idg_view_reduced.glb"
    metadata_out = out_dir / "reduced_rig_metadata.json"
    report_out = out_dir / "reduced_rig_report.json"
    preview_out = out_dir / "bo3_rev_idg_reduced_preview.blend"
    stdout_log = out_dir / "reduced_rig.stdout.log"
    stderr_log = out_dir / "reduced_rig.stderr.log"

    weapon_glb = Path(args.weapon_glb).resolve()
    hands_glb = Path(args.hands_glb).resolve()
    manifest_path = Path(args.manifest).resolve()
    anim_dir = Path(args.anim_dir).resolve()
    worker_path = (TOOLS_DIR / "blender_idg_reduce_worker.py").resolve()
    preview_worker = (TOOLS_DIR / "blender_idg_preview_worker.py").resolve()
    blender_cod_root = DEFAULT_BLENDER_COD_ROOT.resolve()

    blender_exe = choose_blender_executable(args.blender_exe)
    if not args.skip_build:
        if not (Path(blender_exe).exists() or shutil.which(blender_exe)):
            raise FileNotFoundError(f"Blender executable not found: {blender_exe}")
        proc = run_reducer(
            blender_exe=blender_exe,
            worker_path=worker_path,
            weapon_glb=weapon_glb,
            hands_glb=hands_glb,
            manifest_path=manifest_path,
            output_glb=output_glb,
            metadata_out=metadata_out,
        )
        stdout_log.write_text(proc.stdout or "", encoding="utf-8")
        stderr_log.write_text(proc.stderr or "", encoding="utf-8")
        if proc.returncode != 0:
            raise RuntimeError(f"Reduced rig Blender worker failed: exit={proc.returncode}")
    elif not output_glb.exists():
        raise FileNotFoundError(f"--skip-build was set but output is missing: {output_glb}")

    joint_names = read_glb_joint_names(output_glb)
    anim_stems = [stem.strip() for stem in args.anim_stems.split(",") if stem.strip()]
    anim_union = read_xanim_union(anim_dir / f"{stem}.xanim_export" for stem in anim_stems)
    missing = sorted(set(anim_union) - set(joint_names))
    present = sorted(set(anim_union) & set(joint_names))
    metadata = {}
    if metadata_out.exists():
        metadata = json.loads(metadata_out.read_text(encoding="utf-8"))
    report = {
        "output_glb": str(output_glb),
        "metadata_path": str(metadata_out),
        "joint_count": len(joint_names),
        "joint_names": joint_names,
        "anim_stems": anim_stems,
        "anim_union_count": len(anim_union),
        "present_anim_bones": present,
        "present_anim_bone_count": len(present),
        "missing_anim_bones": missing,
        "missing_anim_bone_count": len(missing),
        "missing_anim_groups": summarize_missing_bones(missing),
        "worker_metadata": metadata,
    }
    report_out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.preview:
        if not (Path(blender_exe).exists() or shutil.which(blender_exe)):
            raise FileNotFoundError(f"Blender executable not found for preview: {blender_exe}")
        preview_proc = run_preview(
            blender_exe=blender_exe,
            preview_worker=preview_worker,
            input_glb=output_glb,
            output_blend=preview_out,
            blender_cod_root=blender_cod_root,
            anim_dir=anim_dir,
            anim_stems=",".join(anim_stems),
        )
        (out_dir / "preview.stdout.log").write_text(preview_proc.stdout or "", encoding="utf-8")
        (out_dir / "preview.stderr.log").write_text(preview_proc.stderr or "", encoding="utf-8")
        if preview_proc.returncode != 0:
            raise RuntimeError(f"Reduced rig preview failed: exit={preview_proc.returncode}")

    print(f"Reduced rig GLB: {output_glb}")
    print(f"Reduced rig report: {report_out}")
    if args.preview:
        print(f"Preview blend: {preview_out}")


if __name__ == "__main__":
    main()
