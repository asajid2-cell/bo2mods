from __future__ import annotations

import argparse
import datetime as dt
import difflib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent

import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import save_json  # noqa: E402
from gameplay_common import (  # noqa: E402
    format_like,
    is_anim_field,
    is_model_field,
    is_numeric_string,
    parse_numeric,
    read_weaponfile,
    write_weaponfile,
)
from linker_oracle import sanitize_name  # noqa: E402


def discover_weapon_inputs(path: Path, max_files: int) -> List[Path]:
    files: List[Path] = []
    if path.is_file():
        files = [path]
    elif path.is_dir():
        for child in path.rglob("*"):
            if child.is_file():
                files.append(child)
    files = sorted(files)
    if max_files > 0:
        files = files[:max_files]
    return files


def resolve_known_set(values: Sequence[str]) -> Tuple[Dict[str, str], List[str]]:
    lookup: Dict[str, str] = {}
    lowered: List[str] = []
    for raw in values:
        value = str(raw).strip()
        if not value:
            continue
        key = value.lower()
        if key not in lookup:
            lookup[key] = value
            lowered.append(key)
    return lookup, lowered


def find_reference_fallback(value: str, known_lookup: Dict[str, str], known_lowered: Sequence[str]) -> Optional[str]:
    if not value:
        return None
    low = value.lower()
    if low in known_lookup:
        return known_lookup[low]

    tail = low.split("/")[-1]
    if tail:
        for candidate_low in known_lowered:
            if candidate_low.endswith("/" + tail) or candidate_low == tail:
                return known_lookup[candidate_low]
        contains = [candidate_low for candidate_low in known_lowered if tail in candidate_low]
        if contains:
            return known_lookup[contains[0]]

    close = difflib.get_close_matches(low, known_lowered, n=1, cutoff=0.60)
    if close:
        return known_lookup[close[0]]
    return None


def clamp_numeric_field(field: str, value: str, profile: Dict[str, Any], use_p95: bool) -> Tuple[str, Optional[Dict[str, Any]]]:
    numeric = profile.get("numeric")
    if not isinstance(numeric, dict) or not is_numeric_string(value):
        return value, None
    raw = parse_numeric(value)
    low = float(numeric.get("p01", numeric.get("min", raw)))
    high = float(numeric.get("p99" if not use_p95 else "p95", numeric.get("max", raw)))
    clamped = min(max(raw, low), high)
    if clamped == raw:
        return value, None
    return format_like(clamped, value), {"field": field, "from": value, "to": format_like(clamped, value), "low": low, "high": high}


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate weapon gameplay fields toward BO2 baseline envelopes.")
    parser.add_argument("--input", required=True, help="Input weapon file or directory.")
    parser.add_argument(
        "--baseline",
        default="_build/asset_port_pipeline/bo2_gameplay_baseline.json",
        help="Path to BO2 gameplay baseline JSON.",
    )
    parser.add_argument("--output-root", default="_build/asset_port_pipeline/converted_gameplay", help="Output root.")
    parser.add_argument("--project-name", default="bo3_gameplay_port", help="Output project name.")
    parser.add_argument("--max-files", type=int, default=0, help="Optional file cap for quick runs.")
    parser.add_argument("--no-reference-remap", action="store_true", help="Disable missing model/anim remap.")
    parser.add_argument("--strict-numeric-p95", action="store_true", help="Clamp to p95 instead of p99 upper bound.")
    parser.add_argument("--report", default="_build/asset_port_pipeline/weapon_gameplay_translation_report.json", help="Output report path.")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = (repo_root / input_path).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    baseline_path = Path(args.baseline)
    if not baseline_path.is_absolute():
        baseline_path = (repo_root / baseline_path).resolve()
    if not baseline_path.exists():
        raise FileNotFoundError(f"Baseline not found: {baseline_path}")

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    field_profiles: Dict[str, Dict[str, Any]] = baseline.get("field_profiles", {})
    field_defaults: Dict[str, str] = baseline.get("field_defaults", {})
    required_fields: List[str] = baseline.get("required_fields", [])

    known_models_lookup, known_models_lower = resolve_known_set(baseline.get("known_models", []))
    known_anims_lookup, known_anims_lower = resolve_known_set(baseline.get("known_anims", []))

    inputs = discover_weapon_inputs(input_path, max_files=max(0, args.max_files))
    if not inputs:
        raise FileNotFoundError(f"No files found in {input_path}")

    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = (repo_root / output_root).resolve()
    project_name = sanitize_name(args.project_name)
    output_weapons = output_root / project_name / "weapons"
    output_weapons.mkdir(parents=True, exist_ok=True)

    report_rows: List[Dict[str, Any]] = []

    for source in inputs:
        row: Dict[str, Any] = {
            "source": str(source),
            "status": "ok",
            "numeric_clamps": [],
            "required_fills": [],
            "reference_remaps": [],
            "unresolved_references": [],
        }
        try:
            ordered_keys, data = read_weaponfile(source)
            translated = dict(data)

            for field, raw_value in list(translated.items()):
                profile = field_profiles.get(field, {})
                new_value, clamp_info = clamp_numeric_field(
                    field=field,
                    value=str(raw_value),
                    profile=profile,
                    use_p95=bool(args.strict_numeric_p95),
                )
                translated[field] = new_value
                if clamp_info:
                    row["numeric_clamps"].append(clamp_info)

                if args.no_reference_remap:
                    continue

                if is_model_field(field):
                    fallback = find_reference_fallback(str(translated[field]), known_models_lookup, known_models_lower)
                    if fallback is None:
                        if translated[field]:
                            row["unresolved_references"].append({"field": field, "value": translated[field], "kind": "model"})
                    elif fallback != translated[field]:
                        row["reference_remaps"].append({"field": field, "from": translated[field], "to": fallback, "kind": "model"})
                        translated[field] = fallback

                elif is_anim_field(field):
                    fallback = find_reference_fallback(str(translated[field]), known_anims_lookup, known_anims_lower)
                    if fallback is None:
                        if translated[field]:
                            row["unresolved_references"].append({"field": field, "value": translated[field], "kind": "anim"})
                    elif fallback != translated[field]:
                        row["reference_remaps"].append({"field": field, "from": translated[field], "to": fallback, "kind": "anim"})
                        translated[field] = fallback

            for field in required_fields:
                if field in translated:
                    continue
                default_value = str(field_defaults.get(field, ""))
                translated[field] = default_value
                row["required_fills"].append({"field": field, "value": default_value})

            target_name = source.name
            target_path = output_weapons / target_name
            write_weaponfile(target_path, ordered_keys=ordered_keys, data=translated)
            row["output"] = str(target_path)

        except Exception as exc:
            row["status"] = "error"
            row["error"] = str(exc)

        report_rows.append(row)

    summary = {
        "files": len(report_rows),
        "ok": sum(1 for item in report_rows if item.get("status") == "ok"),
        "error": sum(1 for item in report_rows if item.get("status") == "error"),
        "numeric_clamps": sum(len(item.get("numeric_clamps", [])) for item in report_rows),
        "required_fills": sum(len(item.get("required_fills", [])) for item in report_rows),
        "reference_remaps": sum(len(item.get("reference_remaps", [])) for item in report_rows),
        "unresolved_references": sum(len(item.get("unresolved_references", [])) for item in report_rows),
    }

    report = {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "input": str(input_path),
        "baseline": str(baseline_path),
        "output_project_root": str(output_root / project_name),
        "summary": summary,
        "rows": report_rows,
    }

    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = (repo_root / report_path).resolve()
    save_json(report_path, report)

    print(f"Saved weapon gameplay translation report: {report_path}")
    print(
        f"files={summary['files']} ok={summary['ok']} error={summary['error']} "
        f"clamps={summary['numeric_clamps']} remaps={summary['reference_remaps']} "
        f"unresolved={summary['unresolved_references']}"
    )


if __name__ == "__main__":
    main()
