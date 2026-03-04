from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

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
    summarize_xmodel,
)


def soft_threshold(summary: Dict[str, Any], key: str, multiplier: float = 1.2) -> float:
    stats = summary.get(key, {})
    p99 = float(stats.get("p99", 0.0))
    if p99 <= 0:
        return float(stats.get("max", 0.0))
    return p99 * multiplier


def detect_asset_type(path: Path) -> str:
    lower_name = path.name.lower()
    parent = path.parent.name.lower()
    if lower_name.endswith(".xmodel_export"):
        return "xmodel"
    if lower_name.endswith(".atr"):
        return "animtree"
    if lower_name.endswith(".asd"):
        return "animstate"
    if parent == "weapons":
        return "weapon"
    return "unknown"


def collect_inputs(inputs: List[Path]) -> List[Path]:
    output: List[Path] = []
    for item in inputs:
        if item.is_file():
            output.append(item)
            continue
        if item.is_dir():
            if item.name.lower() == "weapons":
                output.extend([path for path in item.rglob("*") if path.is_file()])
                continue
            output.extend(discover_files([item], "*.xmodel_export"))
            output.extend(discover_files([item], "*.atr"))
            output.extend(discover_files([item], "*.asd"))
            output.extend([path for path in item.rglob("weapons/*") if path.is_file()])
    unique = sorted({path.resolve() for path in output})
    return unique


def validate_xmodel(summary: Dict[str, Any], baseline: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    xb = baseline.get("xmodel", {})
    limits = xb.get("engine_hard_limits", {})
    allowed_versions = set(limits.get("allowed_versions", [6]))
    max_inf = int(limits.get("max_vertex_influences", 4))
    max_bones = int(limits.get("max_bones_recommended", 128))
    max_verts = int(limits.get("max_vertices_recommended", 32767))

    if int(summary.get("version", -1)) not in allowed_versions:
        errors.append(f"version={summary.get('version')} not in allowed_versions={sorted(allowed_versions)}")
    if int(summary.get("max_vertex_influences", 0)) > max_inf:
        errors.append(
            f"max_vertex_influences={summary.get('max_vertex_influences')} exceeds limit={max_inf}"
        )
    if int(summary.get("num_bones", 0)) > max_bones:
        errors.append(f"num_bones={summary.get('num_bones')} exceeds recommended hard limit={max_bones}")
    if int(summary.get("num_verts", 0)) > max_verts:
        errors.append(f"num_verts={summary.get('num_verts')} exceeds recommended hard limit={max_verts}")
    if int(summary.get("vertices_without_bones", 0)) > 0:
        errors.append(f"vertices_without_bones={summary.get('vertices_without_bones')}")
    if int(summary.get("invalid_weight_sums", 0)) > 0:
        errors.append(f"invalid_weight_sums={summary.get('invalid_weight_sums')}")

    ns = xb.get("numeric_summary", {})
    num_bones_soft = soft_threshold(ns, "num_bones")
    num_verts_soft = soft_threshold(ns, "num_verts")
    num_faces_soft = soft_threshold(ns, "num_faces")
    bbox_diag_soft = soft_threshold(ns, "bbox_diag", multiplier=1.5)
    if num_bones_soft > 0 and float(summary.get("num_bones", 0)) > num_bones_soft:
        warnings.append(f"num_bones above BO2 p99 envelope ({summary.get('num_bones')} > {num_bones_soft:.2f})")
    if num_verts_soft > 0 and float(summary.get("num_verts", 0)) > num_verts_soft:
        warnings.append(f"num_verts above BO2 p99 envelope ({summary.get('num_verts')} > {num_verts_soft:.2f})")
    if num_faces_soft > 0 and float(summary.get("num_faces", 0)) > num_faces_soft:
        warnings.append(f"num_faces above BO2 p99 envelope ({summary.get('num_faces')} > {num_faces_soft:.2f})")
    if bbox_diag_soft > 0 and float(summary.get("bbox_diag", 0.0)) > bbox_diag_soft:
        warnings.append(f"bbox_diag above BO2 envelope ({summary.get('bbox_diag'):.3f} > {bbox_diag_soft:.3f})")

    return errors, warnings


def validate_weapon(summary: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    fields = summary.get("fields", {})
    required = ("weaponType", "inventoryType", "gunModel", "worldModel", "clipSize", "maxAmmo")
    missing = [key for key in required if not fields.get(key)]
    if missing:
        errors.append("missing required fields: " + ", ".join(missing))

    numeric = summary.get("numeric_values", {})
    weapon_type = str(fields.get("weaponType", "")).lower()
    inventory_type = str(fields.get("inventoryType", "")).lower()
    is_melee_like = weapon_type in {"melee"} or inventory_type in {"offhand", "item"}
    if "clipSize" in numeric and numeric["clipSize"] <= 0 and not is_melee_like:
        errors.append("clipSize must be > 0")
    if "maxAmmo" in numeric and numeric["maxAmmo"] < 0:
        errors.append("maxAmmo must be >= 0")
    if "damage" in numeric and numeric["damage"] < 0:
        errors.append("damage must be >= 0")
    if fields.get("gunModel") and not str(fields["gunModel"]).startswith("t6_"):
        warnings.append(f"gunModel '{fields['gunModel']}' is not t6_* (likely needs remap)")
    if fields.get("worldModel") and not str(fields["worldModel"]).startswith("t6_"):
        warnings.append(f"worldModel '{fields['worldModel']}' is not t6_* (likely needs remap)")
    if summary.get("anim_ref_count", 0) == 0:
        warnings.append("no animation references detected")

    return errors, warnings


def weapon_report_view(summary: Dict[str, Any]) -> Dict[str, Any]:
    fields = summary.get("fields", {})
    numeric = summary.get("numeric_values", {})
    keep_numeric = {
        key: numeric[key]
        for key in (
            "clipSize",
            "maxAmmo",
            "startAmmo",
            "damage",
            "playerDamage",
            "fireTime",
            "reloadTime",
            "projectileSpeed",
            "explosionRadius",
        )
        if key in numeric
    }
    return {
        "path": summary.get("path", ""),
        "field_count": summary.get("field_count", 0),
        "weapon_type": summary.get("weapon_type", ""),
        "inventory_type": summary.get("inventory_type", ""),
        "fire_type": summary.get("fire_type", ""),
        "gunModel": fields.get("gunModel", ""),
        "worldModel": fields.get("worldModel", ""),
        "anim_ref_count": summary.get("anim_ref_count", 0),
        "model_ref_count": summary.get("model_ref_count", 0),
        "numeric_values": keep_numeric,
    }


def validate_animtree(summary: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    if int(summary.get("entry_count", 0)) <= 0:
        errors.append("no animation entries found")
    return errors, warnings


def validate_animstate(summary: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    if int(summary.get("state_count", 0)) <= 0:
        errors.append("no states found")
    if int(summary.get("anim_ref_count", 0)) <= 0:
        warnings.append("no anim refs found")
    return errors, warnings


def validate_asset(path: Path, baseline: Dict[str, Any], forced_type: str) -> Dict[str, Any]:
    asset_type = forced_type if forced_type != "auto" else detect_asset_type(path)
    parsed: Dict[str, Any]
    errors: List[str]
    warnings: List[str]

    try:
        if asset_type == "xmodel":
            parsed = summarize_xmodel(path)
            errors, warnings = validate_xmodel(parsed, baseline)
        elif asset_type == "weapon":
            parsed = parse_weapon_file(path)
            errors, warnings = validate_weapon(parsed)
            parsed = weapon_report_view(parsed)
        elif asset_type == "animtree":
            parsed = parse_animtree_atr(path)
            errors, warnings = validate_animtree(parsed)
        elif asset_type == "animstate":
            parsed = parse_animstate_asd(path)
            errors, warnings = validate_animstate(parsed)
        else:
            return {
                "path": str(path),
                "asset_type": asset_type,
                "status": "skipped",
                "errors": ["unknown asset type"],
                "warnings": [],
            }
    except Exception as exc:  # pragma: no cover - guardrail parsing
        return {
            "path": str(path),
            "asset_type": asset_type,
            "status": "error",
            "errors": [f"parse/validate failed: {exc}"],
            "warnings": [],
        }

    status = "pass" if not errors else "fail"
    return {
        "path": str(path),
        "asset_type": asset_type,
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "parsed": parsed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate candidate assets against BO2 baseline.")
    parser.add_argument(
        "--baseline",
        default="_build/asset_port_pipeline/bo2_ground_truth.json",
        help="Path to baseline json produced by build_bo2_ground_truth.py",
    )
    parser.add_argument("--inputs", nargs="+", required=True, help="One or more files/directories to validate.")
    parser.add_argument(
        "--type",
        choices=("auto", "xmodel", "weapon", "animtree", "animstate"),
        default="auto",
        help="Force validation type. Default auto-detect.",
    )
    parser.add_argument(
        "--output",
        default="_build/asset_port_pipeline/validation_report.json",
        help="Output report json path.",
    )
    args = parser.parse_args()

    baseline_path = Path(args.baseline).resolve()
    inputs = [Path(item).resolve() for item in args.inputs]
    output = Path(args.output).resolve()

    if not baseline_path.exists():
        raise FileNotFoundError(f"Baseline not found: {baseline_path}")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    files = collect_inputs(inputs)
    if not files:
        raise FileNotFoundError("No input files resolved from --inputs")

    results = [validate_asset(path, baseline=baseline, forced_type=args.type) for path in files]

    report = {
        "meta": {
            "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "baseline": str(baseline_path),
            "input_count": len(files),
        },
        "summary": {
            "pass": sum(1 for result in results if result["status"] == "pass"),
            "fail": sum(1 for result in results if result["status"] == "fail"),
            "error": sum(1 for result in results if result["status"] == "error"),
            "skipped": sum(1 for result in results if result["status"] == "skipped"),
        },
        "results": results,
    }
    save_json(output, report)

    print(f"Saved validation report: {output}")
    print(
        "Summary: "
        f"pass={report['summary']['pass']} "
        f"fail={report['summary']['fail']} "
        f"error={report['summary']['error']} "
        f"skipped={report['summary']['skipped']}"
    )


if __name__ == "__main__":
    main()
