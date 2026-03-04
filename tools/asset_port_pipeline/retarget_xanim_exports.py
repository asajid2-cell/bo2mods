from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


IDENTITY_ROT = (
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
)
ZERO_OFFSET = (0.0, 0.0, 0.0)


def resolve_path(path_value: str, repo_root: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    return path


def normalize_name(name: str) -> str:
    return name.strip().lower()


def safe_float(value: str) -> float:
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        return 0.0
    return out


def parse_xanim_export(path: Path) -> Dict[str, Any]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    payload: Dict[str, Any] = {
        "name": path.stem,
        "path": str(path),
        "framerate": 30,
        "numframes": 0,
        "parts": [],
        "frames": {},
    }

    part_name_by_index: Dict[int, str] = {}
    frame_re = re.compile(r"^FRAME\s+(\d+)$")
    part_header_re = re.compile(r'^PART\s+(\d+)\s+"([^"]+)"$')
    part_frame_re = re.compile(r"^PART\s+(\d+)$")

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        if line.startswith("FRAMERATE"):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    payload["framerate"] = int(float(parts[1]))
                except ValueError:
                    payload["framerate"] = 30
            i += 1
            continue

        if line.startswith("NUMFRAMES") or line.startswith("NUMKEYS"):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    payload["numframes"] = int(parts[1])
                except ValueError:
                    payload["numframes"] = 0
            i += 1
            continue

        mh = part_header_re.match(line)
        if mh:
            idx = int(mh.group(1))
            name = mh.group(2).strip()
            part_name_by_index[idx] = name
            i += 1
            continue

        mf = frame_re.match(line)
        if mf:
            frame_idx = int(mf.group(1))
            frame_map: Dict[int, Dict[str, Any]] = {}
            i += 1
            while i < len(lines):
                sub = lines[i].strip()
                if not sub:
                    i += 1
                    continue
                if frame_re.match(sub):
                    break
                mp = part_frame_re.match(sub)
                if not mp:
                    i += 1
                    continue
                pidx = int(mp.group(1))
                transform = {
                    "offset": ZERO_OFFSET,
                    "rot": IDENTITY_ROT,
                }
                i += 1
                while i < len(lines):
                    entry = lines[i].strip()
                    if not entry:
                        i += 1
                        continue
                    if part_frame_re.match(entry) or frame_re.match(entry):
                        break
                    fields = entry.split()
                    key = fields[0]
                    if key == "OFFSET" and len(fields) >= 4:
                        transform["offset"] = (
                            safe_float(fields[1]),
                            safe_float(fields[2]),
                            safe_float(fields[3]),
                        )
                    elif key == "X" and len(fields) >= 4:
                        transform["rot"] = (
                            (safe_float(fields[1]), safe_float(fields[2]), safe_float(fields[3])),
                            transform["rot"][1],
                            transform["rot"][2],
                        )
                    elif key == "Y" and len(fields) >= 4:
                        transform["rot"] = (
                            transform["rot"][0],
                            (safe_float(fields[1]), safe_float(fields[2]), safe_float(fields[3])),
                            transform["rot"][2],
                        )
                    elif key == "Z" and len(fields) >= 4:
                        transform["rot"] = (
                            transform["rot"][0],
                            transform["rot"][1],
                            (safe_float(fields[1]), safe_float(fields[2]), safe_float(fields[3])),
                        )
                    i += 1
                frame_map[pidx] = transform
            payload["frames"][frame_idx] = frame_map
            continue

        i += 1

    if part_name_by_index:
        payload["parts"] = [part_name_by_index[idx] for idx in sorted(part_name_by_index)]
    else:
        payload["parts"] = []

    if not payload["numframes"] and payload["frames"]:
        payload["numframes"] = max(payload["frames"].keys()) + 1
    return payload


def write_xanim_export(path: Path, anim_name: str, framerate: int, parts: List[str], frames: Dict[int, Dict[int, Dict[str, Any]]]) -> None:
    lines: List[str] = []
    lines.append("Generated by retarget_xanim_exports.py")
    lines.append("")
    lines.append("ANIMATION")
    lines.append("VERSION 3")
    lines.append("")
    lines.append(f"NUMPARTS {len(parts)}")
    for idx, name in enumerate(parts):
        lines.append(f'PART {idx} "{name}"')
    lines.append("")
    lines.append(f"FRAMERATE {int(framerate)}")
    frame_count = 0
    if frames:
        frame_count = max(frames.keys()) + 1
    lines.append(f"NUMFRAMES {frame_count}")
    for frame_idx in sorted(frames.keys()):
        lines.append(f"FRAME {frame_idx}")
        frame_parts = frames[frame_idx]
        for part_idx in range(len(parts)):
            transform = frame_parts.get(part_idx) or {
                "offset": ZERO_OFFSET,
                "rot": IDENTITY_ROT,
            }
            off = transform["offset"]
            rot = transform["rot"]
            lines.append(f"PART {part_idx}")
            lines.append(f"OFFSET {off[0]:.6f} {off[1]:.6f} {off[2]:.6f}")
            lines.append("SCALE 1.000000 1.000000 1.000000")
            lines.append(f"X {rot[0][0]:.6f} {rot[0][1]:.6f} {rot[0][2]:.6f}")
            lines.append(f"Y {rot[1][0]:.6f} {rot[1][1]:.6f} {rot[1][2]:.6f}")
            lines.append(f"Z {rot[2][0]:.6f} {rot[2][1]:.6f} {rot[2][2]:.6f}")
            lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def load_skeleton_map(path: Path | None) -> Dict[str, str]:
    if path is None:
        return {}
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    mapping = payload.get("bone_map", {})
    out: Dict[str, str] = {}
    if isinstance(mapping, dict):
        for source, target in mapping.items():
            src = normalize_name(str(source))
            dst = str(target).strip()
            if not src or not dst:
                continue
            out[src] = dst
    return out


def remap_source_names(parts: Iterable[str], mapping: Dict[str, str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for name in parts:
        src = str(name).strip()
        key = normalize_name(src)
        out[src] = mapping.get(key, src)
    return out


def retarget_anim(
    source: Dict[str, Any],
    donor_parts: List[str],
    skeleton_map: Dict[str, str],
) -> Tuple[Dict[int, Dict[int, Dict[str, Any]]], Dict[str, Any]]:
    source_parts = list(source.get("parts", []))
    renamed = remap_source_names(source_parts, skeleton_map)
    source_index_by_name: Dict[str, int] = {}
    for idx, name in enumerate(source_parts):
        target_name = renamed.get(name, name)
        source_index_by_name.setdefault(target_name, idx)
        source_index_by_name.setdefault(name, idx)

    source_frames = source.get("frames", {})
    donor_index_by_name = {name: idx for idx, name in enumerate(donor_parts)}
    out_frames: Dict[int, Dict[int, Dict[str, Any]]] = {}
    matched_by_name = 0
    matched_by_map = 0

    frame_ids = sorted(source_frames.keys())
    for frame_id in frame_ids:
        src_frame: Dict[int, Dict[str, Any]] = source_frames.get(frame_id, {})
        out_frame: Dict[int, Dict[str, Any]] = {}
        for donor_name, donor_idx in donor_index_by_name.items():
            src_idx = source_index_by_name.get(donor_name)
            if src_idx is not None and src_idx in src_frame:
                source_name = source_parts[src_idx] if src_idx < len(source_parts) else donor_name
                if normalize_name(source_name) == normalize_name(donor_name):
                    matched_by_name += 1
                else:
                    matched_by_map += 1
                out_frame[donor_idx] = src_frame[src_idx]
            else:
                out_frame[donor_idx] = {"offset": ZERO_OFFSET, "rot": IDENTITY_ROT}
        out_frames[int(frame_id)] = out_frame

    total_target_samples = max(1, len(frame_ids) * max(1, len(donor_parts)))
    stats = {
        "source_parts": len(source_parts),
        "target_parts": len(donor_parts),
        "frames": len(frame_ids),
        "matched_by_name": matched_by_name,
        "matched_by_map": matched_by_map,
        "missing_samples": max(0, total_target_samples - matched_by_name - matched_by_map),
        "match_ratio": float((matched_by_name + matched_by_map) / total_target_samples),
    }
    return out_frames, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Retarget BO3 xanim_export files onto a donor BO2 skeleton/order.")
    parser.add_argument("--input-root", required=True, help="Input file or folder containing .xanim_export files.")
    parser.add_argument("--donor", required=True, help="Donor xanim_export with target skeleton/order.")
    parser.add_argument("--output-root", required=True, help="Output folder for retargeted .xanim_export files.")
    parser.add_argument("--pattern", default="vm_*.xanim_export", help="Glob pattern when --input-root is a directory.")
    parser.add_argument(
        "--skeleton-map",
        default="tools/asset_port_pipeline/skeleton_map_bo3_to_bo2.json",
        help="Optional skeleton remap JSON.",
    )
    parser.add_argument("--min-match-ratio", type=float, default=0.35, help="Minimum acceptable sample match ratio.")
    parser.add_argument("--strict", action="store_true", help="Fail with non-zero exit when any anim is below --min-match-ratio.")
    parser.add_argument(
        "--report",
        default="_build/asset_port_pipeline/retarget_xanim_report.json",
        help="Output report JSON path.",
    )
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    input_root = resolve_path(args.input_root, repo_root)
    donor_path = resolve_path(args.donor, repo_root)
    output_root = resolve_path(args.output_root, repo_root)
    report_path = resolve_path(args.report, repo_root)
    skeleton_map_path = resolve_path(args.skeleton_map, repo_root) if args.skeleton_map else None

    if not donor_path.exists():
        raise FileNotFoundError(f"Donor xanim_export not found: {donor_path}")
    if not input_root.exists():
        raise FileNotFoundError(f"Input root not found: {input_root}")

    if input_root.is_file():
        sources = [input_root]
    else:
        sources = sorted(input_root.rglob(args.pattern))
    sources = [path for path in sources if path.suffix.lower() == ".xanim_export"]
    if not sources:
        raise FileNotFoundError(f"No xanim_export files found under: {input_root}")

    donor = parse_xanim_export(donor_path)
    donor_parts = list(donor.get("parts", []))
    if not donor_parts:
        raise RuntimeError(f"Donor xanim has no PART list: {donor_path}")

    skeleton_map = load_skeleton_map(skeleton_map_path)
    output_root.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    failures: List[str] = []
    for source_path in sources:
        parsed = parse_xanim_export(source_path)
        out_frames, stats = retarget_anim(parsed, donor_parts=donor_parts, skeleton_map=skeleton_map)
        out_name = source_path.name
        out_path = output_root / out_name
        write_xanim_export(
            path=out_path,
            anim_name=parsed.get("name", source_path.stem),
            framerate=int(parsed.get("framerate", donor.get("framerate", 30))),
            parts=donor_parts,
            frames=out_frames,
        )
        status = "ok"
        if float(stats.get("match_ratio", 0.0)) < float(args.min_match_ratio):
            status = "warn"
            failures.append(source_path.name)
        rows.append(
            {
                "status": status,
                "source": str(source_path),
                "output": str(out_path),
                "stats": stats,
            }
        )

    final_status = "pass" if not failures else "warn"
    report = {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "input_root": str(input_root),
        "donor": str(donor_path),
        "output_root": str(output_root),
        "skeleton_map": str(skeleton_map_path) if skeleton_map_path else "",
        "counts": {
            "input_files": len(sources),
            "ok": sum(1 for row in rows if row.get("status") == "ok"),
            "warn": sum(1 for row in rows if row.get("status") == "warn"),
            "donor_parts": len(donor_parts),
        },
        "min_match_ratio": float(args.min_match_ratio),
        "strict": bool(args.strict),
        "final_status": final_status,
        "rows": rows,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved xanim retarget report: {report_path}")
    print(f"retargeted={len(sources)} donor_parts={len(donor_parts)} warn={len(failures)}")

    if args.strict and failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
