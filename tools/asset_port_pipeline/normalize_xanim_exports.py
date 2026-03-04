from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from retarget_xanim_exports import parse_xanim_export, write_xanim_export


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


def normalize_name(value: str) -> str:
    return value.strip().lower()


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    return float(a[0] * b[0] + a[1] * b[1] + a[2] * b[2])


def cross(a: Sequence[float], b: Sequence[float]) -> Tuple[float, float, float]:
    return (
        float(a[1] * b[2] - a[2] * b[1]),
        float(a[2] * b[0] - a[0] * b[2]),
        float(a[0] * b[1] - a[1] * b[0]),
    )


def normalize_vec(v: Sequence[float], fallback: Sequence[float]) -> Tuple[float, float, float]:
    length = math.sqrt(max(0.0, dot(v, v)))
    if length <= 1e-8:
        return float(fallback[0]), float(fallback[1]), float(fallback[2])
    return float(v[0] / length), float(v[1] / length), float(v[2] / length)


def orthonormalize_rot(rot: Sequence[Sequence[float]]) -> Tuple[Tuple[float, float, float], ...]:
    try:
        x_raw = (float(rot[0][0]), float(rot[0][1]), float(rot[0][2]))
        y_raw = (float(rot[1][0]), float(rot[1][1]), float(rot[1][2]))
    except Exception:
        return IDENTITY_ROT

    x = normalize_vec(x_raw, (1.0, 0.0, 0.0))
    y_proj = dot(y_raw, x)
    y_tmp = (float(y_raw[0] - y_proj * x[0]), float(y_raw[1] - y_proj * x[1]), float(y_raw[2] - y_proj * x[2]))
    y = normalize_vec(y_tmp, (0.0, 1.0, 0.0))
    z = normalize_vec(cross(x, y), (0.0, 0.0, 1.0))
    return (x, y, z)


def clamp_offset(offset: Sequence[float], limit: float) -> Tuple[Tuple[float, float, float], bool]:
    changed = False
    out: List[float] = []
    for value in offset:
        f = float(value)
        clamped = max(-limit, min(limit, f))
        if clamped != f:
            changed = True
        out.append(clamped)
    return (float(out[0]), float(out[1]), float(out[2])), changed


def load_skeleton_map(path: Path | None) -> Dict[str, str]:
    if not path or not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    mapping = payload.get("bone_map", {})
    out: Dict[str, str] = {}
    if isinstance(mapping, dict):
        for source, target in mapping.items():
            src = normalize_name(str(source))
            dst = str(target).strip()
            if src and dst:
                out[src] = dst
    return out


def build_source_index(parts: Sequence[str], skeleton_map: Dict[str, str]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for idx, source_name in enumerate(parts):
        source = str(source_name).strip()
        if not source:
            continue
        source_key = normalize_name(source)
        mapped = skeleton_map.get(source_key, source)
        mapped_key = normalize_name(mapped)
        out.setdefault(source, idx)
        out.setdefault(source_key, idx)
        out.setdefault(mapped, idx)
        out.setdefault(mapped_key, idx)
    return out


def normalize_anim(
    parsed: Dict[str, Any],
    target_parts: Sequence[str],
    skeleton_map: Dict[str, str],
    fill_mode: str,
    max_offset: float,
    do_orthonormalize: bool,
) -> Tuple[Dict[int, Dict[int, Dict[str, Any]]], Dict[str, Any]]:
    source_parts = [str(item) for item in (parsed.get("parts") or [])]
    source_index = build_source_index(source_parts, skeleton_map=skeleton_map)
    source_frames: Dict[int, Dict[int, Dict[str, Any]]] = parsed.get("frames") or {}

    frame_count = int(parsed.get("numframes", 0) or 0)
    if frame_count <= 0 and source_frames:
        frame_count = max(source_frames.keys()) + 1
    frame_ids = list(range(max(0, frame_count)))
    if not frame_ids and source_frames:
        frame_ids = sorted(source_frames.keys())

    out_frames: Dict[int, Dict[int, Dict[str, Any]]] = {}
    prev_frame: Dict[int, Dict[str, Any]] = {}
    filled_samples = 0
    clamped_samples = 0

    for frame_id in frame_ids:
        src_frame = source_frames.get(frame_id, {})
        out_frame: Dict[int, Dict[str, Any]] = {}
        for target_idx, target_name in enumerate(target_parts):
            src_idx = source_index.get(target_name)
            transform = src_frame.get(src_idx) if src_idx is not None else None
            if transform is None:
                if fill_mode == "hold_previous" and target_idx in prev_frame:
                    transform = prev_frame[target_idx]
                else:
                    transform = {"offset": ZERO_OFFSET, "rot": IDENTITY_ROT}
                filled_samples += 1

            raw_offset = transform.get("offset", ZERO_OFFSET)
            raw_rot = transform.get("rot", IDENTITY_ROT)

            safe_offset, was_clamped = clamp_offset(raw_offset, limit=max(0.0, float(max_offset)))
            if was_clamped:
                clamped_samples += 1

            if do_orthonormalize:
                safe_rot = orthonormalize_rot(raw_rot)
            else:
                safe_rot = (
                    (float(raw_rot[0][0]), float(raw_rot[0][1]), float(raw_rot[0][2])),
                    (float(raw_rot[1][0]), float(raw_rot[1][1]), float(raw_rot[1][2])),
                    (float(raw_rot[2][0]), float(raw_rot[2][1]), float(raw_rot[2][2])),
                )

            baked = {"offset": safe_offset, "rot": safe_rot}
            out_frame[target_idx] = baked
            prev_frame[target_idx] = baked
        out_frames[int(frame_id)] = out_frame

    total_samples = len(frame_ids) * len(target_parts)
    stats = {
        "source_parts": len(source_parts),
        "target_parts": len(target_parts),
        "frame_count": len(frame_ids),
        "total_samples": int(total_samples),
        "filled_samples": int(filled_samples),
        "clamped_samples": int(clamped_samples),
    }
    return out_frames, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize and bake xanim_export files for BO2-safe staging.")
    parser.add_argument("--input-root", required=True, help="Input file/folder containing .xanim_export files.")
    parser.add_argument("--output-root", required=True, help="Output folder for normalized .xanim_export files.")
    parser.add_argument("--pattern", default="*.xanim_export", help="Glob pattern when input is a folder.")
    parser.add_argument("--donor", default="", help="Optional donor xanim_export to force part order.")
    parser.add_argument(
        "--skeleton-map",
        default="tools/asset_port_pipeline/skeleton_map_bo3_to_bo2.json",
        help="Optional skeleton map JSON for source->target name remap.",
    )
    parser.add_argument(
        "--fill-mode",
        choices=["identity", "hold_previous"],
        default="hold_previous",
        help="How missing part transforms are filled.",
    )
    parser.add_argument("--max-offset", type=float, default=4096.0, help="Clamp abs(offset axis) to this value.")
    parser.add_argument("--orthonormalize", action=argparse.BooleanOptionalAction, default=True, help="Orthonormalize rotation basis vectors.")
    parser.add_argument("--strict", action="store_true", help="Fail if output frame/part coverage is empty.")
    parser.add_argument(
        "--report",
        default="_build/asset_port_pipeline/xanim_normalize_report.json",
        help="Output report JSON path.",
    )
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    input_root = resolve_path(args.input_root, repo_root)
    output_root = resolve_path(args.output_root, repo_root)
    report_path = resolve_path(args.report, repo_root)
    donor_path = resolve_path(args.donor, repo_root) if args.donor else None
    skeleton_map_path = resolve_path(args.skeleton_map, repo_root) if args.skeleton_map else None

    if not input_root.exists():
        raise FileNotFoundError(f"input-root not found: {input_root}")
    if donor_path and not donor_path.exists():
        raise FileNotFoundError(f"donor not found: {donor_path}")

    if input_root.is_file():
        sources = [input_root]
    else:
        sources = sorted(path for path in input_root.rglob(args.pattern) if path.suffix.lower() == ".xanim_export")
    if not sources:
        raise FileNotFoundError(f"No .xanim_export files found under: {input_root}")

    donor_parts: List[str] = []
    if donor_path:
        donor = parse_xanim_export(donor_path)
        donor_parts = [str(item) for item in (donor.get("parts") or [])]
        if not donor_parts:
            raise RuntimeError(f"Donor has no PART list: {donor_path}")

    skeleton_map = load_skeleton_map(skeleton_map_path)
    output_root.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    failures: List[str] = []

    for source_path in sources:
        parsed = parse_xanim_export(source_path)
        target_parts = donor_parts or [str(item) for item in (parsed.get("parts") or [])]
        out_frames, stats = normalize_anim(
            parsed=parsed,
            target_parts=target_parts,
            skeleton_map=skeleton_map,
            fill_mode=args.fill_mode,
            max_offset=float(args.max_offset),
            do_orthonormalize=bool(args.orthonormalize),
        )
        out_path = output_root / source_path.name
        write_xanim_export(
            path=out_path,
            anim_name=parsed.get("name", source_path.stem),
            framerate=int(parsed.get("framerate", 30) or 30),
            parts=target_parts,
            frames=out_frames,
        )

        status = "ok"
        if stats["frame_count"] <= 0 or stats["target_parts"] <= 0:
            status = "error"
            failures.append(source_path.name)
        rows.append(
            {
                "status": status,
                "source": str(source_path),
                "output": str(out_path),
                "stats": stats,
            }
        )

    report = {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "input_root": str(input_root),
        "output_root": str(output_root),
        "donor": str(donor_path) if donor_path else "",
        "skeleton_map": str(skeleton_map_path) if skeleton_map_path else "",
        "fill_mode": args.fill_mode,
        "max_offset": float(args.max_offset),
        "orthonormalize": bool(args.orthonormalize),
        "strict": bool(args.strict),
        "counts": {
            "input_files": len(sources),
            "ok": sum(1 for row in rows if row.get("status") == "ok"),
            "error": sum(1 for row in rows if row.get("status") == "error"),
            "donor_parts": len(donor_parts),
        },
        "rows": rows,
        "final_status": "pass" if not failures else "fail",
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved xanim normalize report: {report_path}")
    print(
        f"normalized={len(rows)} "
        f"errors={len(failures)} "
        f"donor_parts={len(donor_parts)}"
    )

    if args.strict and failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
