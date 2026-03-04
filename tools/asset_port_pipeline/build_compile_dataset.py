from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent

import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import save_json  # noqa: E402
from linker_oracle import compile_xmodels, parse_load_zones, sanitize_name  # noqa: E402


QUOTED_RE = re.compile(r'"[^"]*"|\'[^\']*\'')
HEX_RE = re.compile(r"\b[0-9a-f]{8,}\b", flags=re.IGNORECASE)
NUMBER_RE = re.compile(r"\b\d+\b")
WS_RE = re.compile(r"\s+")


def find_xmodel_jsons(root: Path) -> List[Path]:
    if not root.exists():
        return []
    paths = sorted(root.rglob("*.json"))
    out: List[Path] = []
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("_type") == "xmodel":
            out.append(path)
    return out


def quick_descriptor_features(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    lods = payload.get("lods", [])
    return {
        "type": payload.get("type", ""),
        "lod_count": len(lods) if isinstance(lods, list) else 0,
        "has_armature_hint": str(payload.get("type", "")).lower() == "animated",
    }


def normalize_error_signature(errors: Iterable[str]) -> str:
    normalized_lines: List[str] = []
    for raw in list(errors)[:3]:
        line = str(raw).strip().lower()
        line = QUOTED_RE.sub('"<q>"', line)
        line = HEX_RE.sub("<hex>", line)
        line = NUMBER_RE.sub("<n>", line)
        line = WS_RE.sub(" ", line).strip()
        if line:
            normalized_lines.append(line)
    if not normalized_lines:
        return "no_error_message"
    return " | ".join(normalized_lines)


def collect_missing_assets(row: Dict[str, Any]) -> List[Tuple[str, str]]:
    oracle = row.get("oracle", {})
    attempts = oracle.get("attempts", [])
    out: List[Tuple[str, str]] = []
    seen = set()

    for attempt in attempts:
        for item in attempt.get("missing_assets", []):
            asset_name = str(item.get("asset_name", "")).strip()
            asset_type = str(item.get("asset_type", "")).strip().lower()
            key = (asset_name, asset_type)
            if asset_name and asset_type and key not in seen:
                seen.add(key)
                out.append(key)

    for item in oracle.get("missing_assets", []):
        asset_name = str(item.get("asset_name", "")).strip()
        asset_type = str(item.get("asset_type", "")).strip().lower()
        key = (asset_name, asset_type)
        if asset_name and asset_type and key not in seen:
            seen.add(key)
            out.append(key)

    return out


def build_failure_summary(rows: List[Dict[str, Any]], top_k: int = 25) -> Dict[str, Any]:
    fail_rows = [row for row in rows if int(row.get("label", 0)) == 0]

    exit_code_counts: Counter[int] = Counter()
    signature_counts: Counter[str] = Counter()
    signature_examples: Dict[str, Dict[str, Any]] = {}
    missing_type_counts: Counter[str] = Counter()
    missing_name_counts: Counter[str] = Counter()

    for row in fail_rows:
        oracle = row.get("oracle", {})
        exit_code = int(oracle.get("exit_code", -1))
        exit_code_counts[exit_code] += 1

        signature = normalize_error_signature(oracle.get("errors", []))
        signature_counts[signature] += 1
        if signature not in signature_examples:
            signature_examples[signature] = {
                "xmodel_path": row.get("xmodel_path", ""),
                "project_name": row.get("project_name", ""),
                "errors": oracle.get("errors", [])[:5],
            }

        for asset_name, asset_type in collect_missing_assets(row):
            missing_type_counts[asset_type] += 1
            missing_name_counts[f"{asset_type}:{asset_name}"] += 1

    top_signatures = []
    for signature, count in signature_counts.most_common(top_k):
        example = signature_examples.get(signature, {})
        top_signatures.append(
            {
                "signature": signature,
                "count": int(count),
                "example_xmodel_path": example.get("xmodel_path", ""),
                "example_project_name": example.get("project_name", ""),
                "example_errors": example.get("errors", []),
            }
        )

    top_missing_types = [
        {"asset_type": asset_type, "count": int(count)}
        for asset_type, count in missing_type_counts.most_common(top_k)
    ]
    top_missing_assets = [
        {"asset": asset, "count": int(count)}
        for asset, count in missing_name_counts.most_common(top_k)
    ]
    exit_codes = [
        {"exit_code": int(exit_code), "count": int(count)}
        for exit_code, count in exit_code_counts.most_common()
    ]

    return {
        "counts": {
            "rows": len(rows),
            "fail_rows": len(fail_rows),
            "unique_error_signatures": len(signature_counts),
            "unique_missing_asset_types": len(missing_type_counts),
            "unique_missing_assets": len(missing_name_counts),
        },
        "top_error_signatures": top_signatures,
        "top_missing_asset_types": top_missing_types,
        "top_missing_assets": top_missing_assets,
        "exit_code_counts": exit_codes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build linker pass/fail dataset from converted xmodel assets.")
    parser.add_argument("--xmodel-root", required=True, help="Root containing xmodel descriptors.")
    parser.add_argument("--workspace", default="_build/asset_port_pipeline/linker_oracle_batch", help="Workspace root.")
    parser.add_argument("--output-dir", default="_build/asset_port_pipeline/compile_dataset", help="Output dataset directory.")
    parser.add_argument("--linker", default="tools/oat/Linker.exe", help="Path to Linker.exe")
    parser.add_argument(
        "--load-zones",
        nargs="*",
        default=["zone/all/common_zm.ff"],
        help="FF zones to preload (supports semicolon-separated values).",
    )
    parser.add_argument("--auto-resolve-missing", action="store_true", help="Retry linker failures by staging missing dependencies.")
    parser.add_argument("--max-retries", type=int, default=2, help="Maximum retries when auto-resolve is enabled.")
    parser.add_argument(
        "--dependency-roots",
        nargs="*",
        default=["zone_dump/zone_raw", "_build/t6_asset_dump/zone_raw"],
        help="Roots scanned for missing assets (supports semicolon-separated values).",
    )
    parser.add_argument("--max-assets", type=int, default=0, help="Optional cap for quick runs.")
    parser.add_argument("--cluster-top-k", type=int, default=25, help="Top-N failure clusters to keep in summary outputs.")
    parser.add_argument("--resume", action="store_true", help="Skip entries already present in dataset.")
    parser.add_argument("--verbose", action="store_true", help="Verbose linker invocation.")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    xmodel_root = Path(args.xmodel_root)
    if not xmodel_root.is_absolute():
        xmodel_root = (repo_root / xmodel_root).resolve()
    if not xmodel_root.exists():
        raise FileNotFoundError(f"xmodel-root not found: {xmodel_root}")

    linker_path = Path(args.linker)
    if not linker_path.is_absolute():
        linker_path = (repo_root / linker_path).resolve()
    if not linker_path.exists():
        raise FileNotFoundError(f"Linker not found: {linker_path}")

    workspace = Path(args.workspace)
    if not workspace.is_absolute():
        workspace = (repo_root / workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = (repo_root / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    output_jsonl = output_dir / "compile_dataset.jsonl"
    output_meta = output_dir / "compile_dataset_meta.json"
    output_failures = output_dir / "compile_failure_summary.json"

    existing_paths: set[str] = set()
    if args.resume and output_jsonl.exists():
        with output_jsonl.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                existing_paths.add(str(row.get("xmodel_path", "")))

    xmodels = find_xmodel_jsons(xmodel_root)
    if args.max_assets > 0:
        xmodels = xmodels[: args.max_assets]
    if not xmodels:
        raise FileNotFoundError(f"No xmodel json files found in {xmodel_root}")

    load_zone_items = parse_load_zones(args.load_zones)
    load_zone_paths: List[Path] = []
    for item in load_zone_items:
        path = Path(item)
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Missing load zone: {path}")
        load_zone_paths.append(path)

    dependency_root_items = parse_load_zones(args.dependency_roots)
    dependency_roots: List[Path] = []
    for item in dependency_root_items:
        path = Path(item)
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        if path.exists():
            dependency_roots.append(path)
    if args.auto_resolve_missing and not dependency_roots:
        raise FileNotFoundError("auto-resolve requested but no dependency roots were found")

    mode = "a" if output_jsonl.exists() else "w"
    results_count = 0
    pass_count = 0
    fail_count = 0
    new_rows: List[Dict[str, Any]] = []

    with output_jsonl.open(mode, encoding="utf-8") as handle:
        for idx, xmodel_path in enumerate(xmodels, start=1):
            xmodel_key = str(xmodel_path.resolve())
            if args.resume and xmodel_key in existing_paths:
                continue

            project_name = sanitize_name(f"compile_{idx}_{xmodel_path.stem}")
            try:
                oracle = compile_xmodels(
                    xmodel_jsons=[xmodel_path],
                    project_name=project_name,
                    workspace=workspace,
                    linker_path=linker_path,
                    load_zones=load_zone_paths,
                    clean_workspace=True,
                    verbose=args.verbose,
                    auto_resolve_missing=args.auto_resolve_missing,
                    max_retries=max(0, args.max_retries),
                    dependency_roots=dependency_roots,
                )
                label = 1 if oracle["linker"]["status"] == "pass" else 0
                if label == 1:
                    pass_count += 1
                else:
                    fail_count += 1
                row = {
                    "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    "xmodel_path": xmodel_key,
                    "project_name": project_name,
                    "label": label,
                    "descriptor_features": quick_descriptor_features(xmodel_path),
                    "oracle": {
                        "status": oracle["linker"]["status"],
                        "exit_code": oracle["linker"]["exit_code"],
                        "errors": oracle["linker"]["errors"],
                        "warnings": oracle["linker"]["warnings"],
                        "missing_assets": oracle["linker"].get("missing_assets", []),
                        "attempts": [
                            {
                                "attempt": item.get("attempt", 0),
                                "status": item.get("status", ""),
                                "exit_code": item.get("exit_code", -1),
                                "errors": item.get("errors", []),
                                "warnings": item.get("warnings", []),
                                "missing_assets": item.get("missing_assets", []),
                                "added_load_zones": item.get("added_load_zones", []),
                            }
                            for item in oracle.get("linker_attempts", [])
                        ],
                    },
                }
            except Exception as exc:  # pragma: no cover - robustness for batch processing
                fail_count += 1
                row = {
                    "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    "xmodel_path": xmodel_key,
                    "project_name": project_name,
                    "label": 0,
                    "descriptor_features": {},
                    "oracle": {
                        "status": "error",
                        "exit_code": -1,
                        "errors": [str(exc)],
                        "warnings": [],
                    },
                }

            handle.write(json.dumps(row) + "\n")
            new_rows.append(row)
            results_count += 1
            if idx % 25 == 0:
                print(f"processed {idx}/{len(xmodels)}")

    failure_summary = build_failure_summary(new_rows, top_k=max(1, int(args.cluster_top_k)))
    failure_summary["generated_at_utc"] = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    failure_summary["dataset_jsonl"] = str(output_jsonl)
    save_json(output_failures, failure_summary)

    meta = {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "xmodel_root": str(xmodel_root),
        "workspace": str(workspace),
        "linker": str(linker_path),
        "load_zones": [str(item) for item in load_zone_paths],
        "auto_resolve_missing": args.auto_resolve_missing,
        "max_retries": max(0, args.max_retries),
        "dependency_roots": [str(item) for item in dependency_roots],
        "new_rows": results_count,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "dataset_jsonl": str(output_jsonl),
        "failure_summary_json": str(output_failures),
        "failure_clusters": {
            "unique_error_signatures": failure_summary["counts"]["unique_error_signatures"],
            "unique_missing_asset_types": failure_summary["counts"]["unique_missing_asset_types"],
            "unique_missing_assets": failure_summary["counts"]["unique_missing_assets"],
        },
    }
    save_json(output_meta, meta)

    print(f"Saved compile dataset rows: {output_jsonl}")
    print(f"Saved compile dataset meta: {output_meta}")
    print(f"Saved failure summary: {output_failures}")
    print(f"Rows={results_count} pass={pass_count} fail={fail_count}")


if __name__ == "__main__":
    main()
