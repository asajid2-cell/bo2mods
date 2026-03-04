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

from common import save_json  # noqa: E402
from map_port_common import (  # noqa: E402
    build_asset_index,
    find_asset_path,
    parse_zone_file,
    phase_for_asset_type,
    sanitize_name,
)


def resolve_source_map(source_zone_root: Path, source_map: str) -> str:
    if source_map:
        return sanitize_name(source_map)
    return sanitize_name(source_zone_root.name)


def resolve_zone_file(source_zone_root: Path, source_map: str) -> Path:
    zone_source = source_zone_root / "zone_source"
    if source_map:
        explicit = zone_source / f"{source_map}.zone"
        if explicit.exists():
            return explicit
    candidates = sorted(zone_source.glob("*.zone"))
    if not candidates:
        raise FileNotFoundError(f"No zone file found in {zone_source}")
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build map-level BO3->BO2 parity plan from zone file.")
    parser.add_argument("--source-zone-root", required=True, help="Source zone_raw/<map> directory.")
    parser.add_argument("--source-map", default="", help="Source map name (defaults to source-zone-root name).")
    parser.add_argument(
        "--bo2-reference-roots",
        nargs="*",
        default=["zone_dump/zone_raw", "_build/t6_asset_dump/zone_raw"],
        help="BO2 roots used to check target-side coverage.",
    )
    parser.add_argument("--output", default="_build/asset_port_pipeline/map_port_plan.json", help="Output plan JSON path.")
    parser.add_argument("--top-k", type=int, default=40, help="Top-N missing groups in summary.")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    source_zone_root = Path(args.source_zone_root)
    if not source_zone_root.is_absolute():
        source_zone_root = (repo_root / source_zone_root).resolve()
    if not source_zone_root.exists():
        raise FileNotFoundError(f"source-zone-root not found: {source_zone_root}")

    source_map = resolve_source_map(source_zone_root, args.source_map)
    zone_file = resolve_zone_file(source_zone_root, source_map)
    entries, ipaks = parse_zone_file(zone_file)
    if not entries:
        raise RuntimeError(f"No asset entries found in zone file: {zone_file}")

    bo2_roots: List[Path] = []
    for raw in args.bo2_reference_roots:
        path = Path(raw)
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        if path.exists():
            bo2_roots.append(path)
    if not bo2_roots:
        raise FileNotFoundError("No valid BO2 reference roots were found.")

    source_indexes: Dict[str, Dict[str, str]] = {}
    bo2_indexes: Dict[str, Dict[str, str]] = {}
    all_types = sorted({item["asset_type"] for item in entries})
    for asset_type in all_types:
        source_indexes[asset_type] = build_asset_index([source_zone_root], asset_type=asset_type)
        bo2_indexes[asset_type] = build_asset_index(bo2_roots, asset_type=asset_type)

    planned_entries: List[Dict[str, Any]] = []
    counts_by_type: Counter[str] = Counter()
    missing_by_type: Counter[str] = Counter()
    missing_by_phase: Counter[str] = Counter()
    missing_assets: Counter[str] = Counter()
    counts_by_phase: Counter[str] = Counter()

    for item in entries:
        asset_type = item["asset_type"]
        asset_name = item["asset_name"]
        phase = phase_for_asset_type(asset_type)
        counts_by_type[asset_type] += 1
        counts_by_phase[phase] += 1

        source_path = find_asset_path(
            asset_type=asset_type,
            asset_name=asset_name,
            indexes=source_indexes,
            source_map_name=source_map,
            source_root=source_zone_root,
        )
        bo2_path = find_asset_path(
            asset_type=asset_type,
            asset_name=asset_name,
            indexes=bo2_indexes,
            source_map_name=source_map,
            source_root=None,
        )
        bo2_found = bool(bo2_path)
        if not bo2_found:
            missing_by_type[asset_type] += 1
            missing_by_phase[phase] += 1
            missing_assets[f"{asset_type}:{asset_name}"] += 1

        planned_entries.append(
            {
                "asset_type": asset_type,
                "asset_name": asset_name,
                "phase": phase,
                "source_found": bool(source_path),
                "source_path": source_path or "",
                "bo2_found": bo2_found,
                "bo2_path": bo2_path or "",
            }
        )

    top_k = max(1, int(args.top_k))
    summary = {
        "counts_by_type": {key: int(value) for key, value in counts_by_type.most_common()},
        "counts_by_phase": {key: int(value) for key, value in counts_by_phase.most_common()},
        "missing_by_type": {key: int(value) for key, value in missing_by_type.most_common()},
        "missing_by_phase": {key: int(value) for key, value in missing_by_phase.most_common()},
        "top_missing_assets": [
            {"asset": key, "count": int(value)} for key, value in missing_assets.most_common(top_k)
        ],
    }

    recommended_actions = [
        "Phase 1: bootstrap core_map assets (mapents/rawfile/stringtable) into BO2 project.",
        "Phase 2: run mesh/material conversion and linker remediation for render_assets.",
        "Phase 3: run weapon gameplay translator and boss/script generators for gameplay_assets/scripts.",
        "After each phase, compile with Linker and patch missing assets from reported clusters.",
    ]

    plan = {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "source_zone_root": str(source_zone_root),
        "source_map": source_map,
        "zone_file": str(zone_file),
        "bo2_reference_roots": [str(path) for path in bo2_roots],
        "ipak_reads": ipaks,
        "summary": summary,
        "recommended_actions": recommended_actions,
        "entries": planned_entries,
    }

    output = Path(args.output)
    if not output.is_absolute():
        output = (repo_root / output).resolve()
    save_json(output, plan)

    print(f"Saved map port plan: {output}")
    print(
        f"entries={len(planned_entries)} "
        f"types={len(counts_by_type)} "
        f"missing={sum(missing_by_type.values())} "
        f"ipaks={len(ipaks)}"
    )


if __name__ == "__main__":
    main()
