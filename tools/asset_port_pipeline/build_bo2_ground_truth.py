from __future__ import annotations

import argparse
import datetime as dt
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent

import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import (  # noqa: E402
    discover_files,
    parse_animstate_asd,
    parse_animtree_atr,
    parse_weapon_file,
    save_json,
    summarize_numeric,
    summarize_xmodel,
)


def add_numeric(summary: Dict[str, List[float]], key: str, value: Any) -> None:
    if value is None:
        return
    try:
        summary.setdefault(key, []).append(float(value))
    except (TypeError, ValueError):
        return


def summarize_numeric_map(values_map: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
    return {key: summarize_numeric(values) for key, values in sorted(values_map.items())}


def build_ground_truth(roots: List[Path], max_files: int = 0, verbose: bool = False) -> Dict[str, Any]:
    roots = [root for root in roots if root.exists()]
    if not roots:
        raise FileNotFoundError("No valid dump roots found")

    xmodel_files = discover_files(roots, "*.xmodel_export")
    weapon_files = [path for root in roots for path in (root.rglob("weapons/*")) if path.is_file()]
    atr_files = discover_files(roots, "*.atr")
    asd_files = discover_files(roots, "*.asd")

    if max_files > 0:
        xmodel_files = xmodel_files[:max_files]
        weapon_files = weapon_files[:max_files]
        atr_files = atr_files[:max_files]
        asd_files = asd_files[:max_files]

    errors: List[str] = []

    xmodel_summaries: List[Dict[str, Any]] = []
    xmodel_numeric: Dict[str, List[float]] = {}
    versions = Counter()
    bone_names = Counter()
    for idx, path in enumerate(xmodel_files, start=1):
        try:
            summary = summarize_xmodel(path)
            xmodel_summaries.append(summary)
            versions[str(summary["version"])] += 1
            for name in summary.get("bone_names", []):
                bone_names[name] += 1
            for key in (
                "num_bones",
                "num_verts",
                "num_faces",
                "num_materials",
                "max_vertex_influences",
                "avg_vertex_influences",
                "invalid_weight_sums",
                "vertices_without_bones",
                "bbox_diag",
                "bbox_size_x",
                "bbox_size_y",
                "bbox_size_z",
            ):
                add_numeric(xmodel_numeric, key, summary.get(key))
        except Exception as exc:  # pragma: no cover - guardrail parsing
            errors.append(f"xmodel:{path}: {exc}")
        if verbose and idx % 500 == 0:
            print(f"[xmodel] parsed {idx}/{len(xmodel_files)}")

    weapon_summaries: List[Dict[str, Any]] = []
    weapon_numeric: Dict[str, List[float]] = {}
    weapon_types = Counter()
    inventory_types = Counter()
    weapon_fields = Counter()
    for idx, path in enumerate(weapon_files, start=1):
        try:
            summary = parse_weapon_file(path)
            weapon_summaries.append(summary)
            weapon_types[summary.get("weapon_type", "")] += 1
            inventory_types[summary.get("inventory_type", "")] += 1
            for key in summary.get("fields", {}):
                weapon_fields[key] += 1
            for key, value in summary.get("numeric_values", {}).items():
                add_numeric(weapon_numeric, key, value)
            add_numeric(weapon_numeric, "field_count", summary.get("field_count"))
            add_numeric(weapon_numeric, "model_ref_count", summary.get("model_ref_count"))
            add_numeric(weapon_numeric, "anim_ref_count", summary.get("anim_ref_count"))
        except Exception as exc:  # pragma: no cover - guardrail parsing
            errors.append(f"weapon:{path}: {exc}")
        if verbose and idx % 500 == 0:
            print(f"[weapon] parsed {idx}/{len(weapon_files)}")

    atr_summaries: List[Dict[str, Any]] = []
    atr_numeric: Dict[str, List[float]] = {}
    for idx, path in enumerate(atr_files, start=1):
        try:
            summary = parse_animtree_atr(path)
            atr_summaries.append(summary)
            add_numeric(atr_numeric, "entry_count", summary.get("entry_count"))
            add_numeric(atr_numeric, "unique_entry_count", summary.get("unique_entry_count"))
        except Exception as exc:  # pragma: no cover - guardrail parsing
            errors.append(f"atr:{path}: {exc}")
        if verbose and idx % 500 == 0:
            print(f"[atr] parsed {idx}/{len(atr_files)}")

    asd_summaries: List[Dict[str, Any]] = []
    asd_numeric: Dict[str, List[float]] = {}
    for idx, path in enumerate(asd_files, start=1):
        try:
            summary = parse_animstate_asd(path)
            asd_summaries.append(summary)
            add_numeric(asd_numeric, "state_count", summary.get("state_count"))
            add_numeric(asd_numeric, "anim_ref_count", summary.get("anim_ref_count"))
            add_numeric(asd_numeric, "unique_anim_ref_count", summary.get("unique_anim_ref_count"))
        except Exception as exc:  # pragma: no cover - guardrail parsing
            errors.append(f"asd:{path}: {exc}")
        if verbose and idx % 500 == 0:
            print(f"[asd] parsed {idx}/{len(asd_files)}")

    baseline = {
        "meta": {
            "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "roots": [str(root) for root in roots],
            "counts": {
                "xmodel_files": len(xmodel_summaries),
                "weapon_files": len(weapon_summaries),
                "animtree_files": len(atr_summaries),
                "animstate_files": len(asd_summaries),
            },
            "errors_count": len(errors),
        },
        "xmodel": {
            "numeric_summary": summarize_numeric_map(xmodel_numeric),
            "observed_versions": sorted(int(v) for v in versions.keys()),
            "top_bone_names": [{"name": name, "count": count} for name, count in bone_names.most_common(128)],
            "engine_hard_limits": {
                "allowed_versions": [6],
                "max_vertex_influences": 4,
                "max_bones_recommended": 128,
                "max_vertices_recommended": 32767,
            },
        },
        "weapon": {
            "numeric_summary": summarize_numeric_map(weapon_numeric),
            "top_weapon_types": [{"value": key, "count": count} for key, count in weapon_types.most_common(32)],
            "top_inventory_types": [{"value": key, "count": count} for key, count in inventory_types.most_common(16)],
            "top_fields": [{"field": key, "count": count} for key, count in weapon_fields.most_common(256)],
        },
        "animtree": {
            "numeric_summary": summarize_numeric_map(atr_numeric),
        },
        "animstate": {
            "numeric_summary": summarize_numeric_map(asd_numeric),
        },
        "errors": errors[:2000],
    }
    return baseline


def main() -> None:
    parser = argparse.ArgumentParser(description="Build BO2 ground-truth stats from dumped assets.")
    parser.add_argument(
        "--roots",
        nargs="+",
        default=["_build/t6_asset_dump/zone_raw", "zone_dump/zone_raw"],
        help="One or more BO2 dump roots.",
    )
    parser.add_argument(
        "--output",
        default="_build/asset_port_pipeline/bo2_ground_truth.json",
        help="Output JSON file.",
    )
    parser.add_argument("--max-files", type=int, default=0, help="Optional cap per asset type for quick tests.")
    parser.add_argument("--verbose", action="store_true", help="Print progress while parsing.")
    args = parser.parse_args()

    roots = [Path(root).resolve() for root in args.roots]
    output = Path(args.output).resolve()

    baseline = build_ground_truth(roots=roots, max_files=args.max_files, verbose=args.verbose)
    save_json(output, baseline)

    counts = baseline["meta"]["counts"]
    print(f"Saved baseline: {output}")
    print(
        "Parsed files: "
        f"xmodel={counts['xmodel_files']}, "
        f"weapon={counts['weapon_files']}, "
        f"atr={counts['animtree_files']}, "
        f"asd={counts['animstate_files']}"
    )
    print(f"Parse errors: {baseline['meta']['errors_count']}")


if __name__ == "__main__":
    main()

