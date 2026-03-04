from __future__ import annotations

import argparse
import datetime as dt
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent

import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import save_json  # noqa: E402
from gameplay_common import (  # noqa: E402
    is_anim_field,
    is_model_field,
    is_numeric_string,
    parse_numeric,
    percentile,
    read_weaponfile,
    unique_non_empty,
)


def discover_weapon_files(roots: Iterable[Path]) -> List[Path]:
    files: List[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for weapons_dir in root.rglob("weapons"):
            if not weapons_dir.is_dir():
                continue
            for child in weapons_dir.iterdir():
                if child.is_file():
                    files.append(child)
    return sorted(set(files))


def discover_xmodel_names(roots: Iterable[Path]) -> List[str]:
    names: List[str] = []
    for root in roots:
        if not root.exists():
            continue
        for xmodel_dir in root.rglob("xmodel"):
            if not xmodel_dir.is_dir():
                continue
            for child in xmodel_dir.iterdir():
                if child.is_file():
                    names.append(child.stem)
    return unique_non_empty(names)


def summarize_numeric(values: List[float]) -> Dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        return {
            "count": 0.0,
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "std": 0.0,
            "p01": 0.0,
            "p05": 0.0,
            "p50": 0.0,
            "p95": 0.0,
            "p99": 0.0,
        }
    return {
        "count": float(len(ordered)),
        "min": float(ordered[0]),
        "max": float(ordered[-1]),
        "mean": float(statistics.fmean(ordered)),
        "std": float(statistics.pstdev(ordered)) if len(ordered) > 1 else 0.0,
        "p01": percentile(ordered, 0.01),
        "p05": percentile(ordered, 0.05),
        "p50": percentile(ordered, 0.50),
        "p95": percentile(ordered, 0.95),
        "p99": percentile(ordered, 0.99),
    }


def top_values(counter: Counter[str], k: int = 20) -> List[Dict[str, Any]]:
    return [{"value": value, "count": int(count)} for value, count in counter.most_common(k)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build BO2 gameplay baseline from dumped weapon files.")
    parser.add_argument(
        "--roots",
        nargs="+",
        default=["zone_dump/zone_raw", "_build/t6_asset_dump/zone_raw"],
        help="Zone roots to scan for weapons/xmodel data.",
    )
    parser.add_argument("--required-threshold", type=float, default=0.95, help="Field presence threshold for required fields.")
    parser.add_argument("--output", default="_build/asset_port_pipeline/bo2_gameplay_baseline.json", help="Baseline output path.")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    roots: List[Path] = []
    for raw in args.roots:
        path = Path(raw)
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        if path.exists():
            roots.append(path)
    if not roots:
        raise FileNotFoundError("No valid roots were found.")

    weapon_files = discover_weapon_files(roots)
    if not weapon_files:
        raise FileNotFoundError("No weapon files found under provided roots.")

    field_counts: Counter[str] = Counter()
    numeric_values: Dict[str, List[float]] = defaultdict(list)
    categorical_values: Dict[str, Counter[str]] = defaultdict(Counter)
    anim_values: Counter[str] = Counter()
    model_values: Counter[str] = Counter()

    processed = 0
    failed: List[str] = []
    for weapon_path in weapon_files:
        try:
            _, fields = read_weaponfile(weapon_path)
        except Exception as exc:
            failed.append(f"{weapon_path}: {exc}")
            continue

        processed += 1
        for field, raw_value in fields.items():
            value = str(raw_value)
            field_counts[field] += 1
            categorical_values[field][value] += 1
            if is_numeric_string(value):
                numeric_values[field].append(parse_numeric(value))
            if value and is_anim_field(field):
                anim_values[value] += 1
            if value and is_model_field(field):
                model_values[value] += 1

    if processed == 0:
        raise RuntimeError("All weapon files failed to parse.")

    required_threshold = max(0.0, min(1.0, float(args.required_threshold)))
    required_fields = sorted(
        [field for field, count in field_counts.items() if (count / processed) >= required_threshold]
    )

    field_defaults = {field: counts.most_common(1)[0][0] for field, counts in categorical_values.items() if counts}
    field_profiles: Dict[str, Any] = {}
    for field, counts in sorted(categorical_values.items()):
        numeric_stats = summarize_numeric(numeric_values.get(field, []))
        field_profiles[field] = {
            "present_count": int(field_counts[field]),
            "present_ratio": float(field_counts[field] / processed),
            "default": field_defaults.get(field, ""),
            "numeric": numeric_stats if numeric_values.get(field) else None,
            "top_values": top_values(counts, k=20),
        }

    known_models = unique_non_empty(list(model_values.keys()) + discover_xmodel_names(roots))
    known_anims = unique_non_empty(list(anim_values.keys()))

    baseline = {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "roots": [str(root) for root in roots],
        "counts": {
            "weapon_files_total": len(weapon_files),
            "weapon_files_processed": processed,
            "weapon_files_failed": len(failed),
            "fields": len(field_profiles),
            "known_models": len(known_models),
            "known_anims": len(known_anims),
        },
        "required_threshold": required_threshold,
        "required_fields": required_fields,
        "field_defaults": field_defaults,
        "field_profiles": field_profiles,
        "known_models": known_models,
        "known_anims": known_anims,
        "parse_failures_sample": failed[:200],
    }

    output = Path(args.output)
    if not output.is_absolute():
        output = (repo_root / output).resolve()
    save_json(output, baseline)

    print(f"Saved gameplay baseline: {output}")
    print(
        f"weapon_files={baseline['counts']['weapon_files_processed']}/"
        f"{baseline['counts']['weapon_files_total']} "
        f"fields={baseline['counts']['fields']} "
        f"known_models={baseline['counts']['known_models']} "
        f"known_anims={baseline['counts']['known_anims']}"
    )


if __name__ == "__main__":
    main()
