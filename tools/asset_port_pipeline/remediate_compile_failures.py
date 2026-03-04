from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

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


def infer_zone_from_xmodel_path(path: Path) -> Optional[str]:
    parts = [part.lower() for part in path.parts]
    for idx, part in enumerate(parts):
        if part == "zone_raw" and idx + 1 < len(parts):
            return path.parts[idx + 1]
    return None


def load_dataset_rows(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def read_failure_priority(path: Optional[Path]) -> Dict[str, int]:
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    out: Dict[str, int] = {}
    for item in payload.get("top_error_signatures", []):
        signature = str(item.get("signature", "")).strip()
        count = int(item.get("count", 0))
        if signature and count > 0:
            out[signature] = count
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Requeue failed compile-dataset rows through linker oracle remediation.")
    parser.add_argument("--dataset-jsonl", required=True, help="Input compile dataset jsonl path.")
    parser.add_argument("--failure-summary", default="", help="Optional compile_failure_summary.json for cluster-priority ordering.")
    parser.add_argument("--workspace", default="_build/asset_port_pipeline/linker_oracle_remediation", help="Workspace root.")
    parser.add_argument("--output-dir", default="_build/asset_port_pipeline/compile_remediation", help="Output directory.")
    parser.add_argument("--linker", default="tools/oat/Linker.exe", help="Path to Linker.exe")
    parser.add_argument(
        "--load-zones",
        nargs="*",
        default=["zone/all/common_zm.ff"],
        help="Base preload zones (supports semicolon-separated values).",
    )
    parser.add_argument("--max-assets", type=int, default=0, help="Optional cap for remediation attempts.")
    parser.add_argument("--max-retries", type=int, default=6, help="Max linker retries per remediation attempt.")
    parser.add_argument(
        "--dependency-roots",
        nargs="*",
        default=["zone_dump/zone_raw", "_build/t6_asset_dump/zone_raw"],
        help="Roots scanned for missing assets (supports semicolon-separated values).",
    )
    parser.add_argument("--replace-all-attempted", action="store_true", help="Replace attempted rows in patched dataset even when still failing.")
    parser.add_argument("--verbose", action="store_true", help="Verbose linker invocations.")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()

    dataset_jsonl = Path(args.dataset_jsonl)
    if not dataset_jsonl.is_absolute():
        dataset_jsonl = (repo_root / dataset_jsonl).resolve()
    if not dataset_jsonl.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_jsonl}")

    failure_summary = Path(args.failure_summary) if args.failure_summary else None
    if failure_summary and not failure_summary.is_absolute():
        failure_summary = (repo_root / failure_summary).resolve()

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

    load_zone_items = parse_load_zones(args.load_zones)
    base_load_zones: List[Path] = []
    for item in load_zone_items:
        path = Path(item)
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Missing load zone: {path}")
        base_load_zones.append(path)

    dependency_root_items = parse_load_zones(args.dependency_roots)
    dependency_roots: List[Path] = []
    for item in dependency_root_items:
        path = Path(item)
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        if path.exists():
            dependency_roots.append(path)
    if not dependency_roots:
        raise FileNotFoundError("No valid dependency roots were found.")

    rows = load_dataset_rows(dataset_jsonl)
    fail_rows = [row for row in rows if int(row.get("label", 0)) == 0]
    cluster_priority = read_failure_priority(failure_summary)

    def priority_key(row: Dict[str, Any]) -> tuple[int, str]:
        sig = normalize_error_signature(row.get("oracle", {}).get("errors", []))
        return (-int(cluster_priority.get(sig, 0)), str(row.get("xmodel_path", "")))

    fail_rows = sorted(fail_rows, key=priority_key)
    if args.max_assets > 0:
        fail_rows = fail_rows[: args.max_assets]

    remediated_rows: List[Dict[str, Any]] = []
    patched_by_xmodel: Dict[str, Dict[str, Any]] = {}

    improved_count = 0
    still_fail_count = 0
    error_count = 0

    for idx, row in enumerate(fail_rows, start=1):
        xmodel_path = Path(str(row.get("xmodel_path", "")))
        if not xmodel_path.is_absolute():
            xmodel_path = (repo_root / xmodel_path).resolve()

        result_row: Dict[str, Any] = {
            "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "xmodel_path": str(xmodel_path),
            "previous_label": int(row.get("label", 0)),
            "previous_status": str(row.get("oracle", {}).get("status", "unknown")),
            "previous_errors": row.get("oracle", {}).get("errors", []),
            "previous_signature": normalize_error_signature(row.get("oracle", {}).get("errors", [])),
        }

        if not xmodel_path.exists():
            result_row.update(
                {
                    "status": "error",
                    "label": 0,
                    "oracle": {"status": "error", "exit_code": -1, "errors": [f"xmodel not found: {xmodel_path}"], "warnings": []},
                }
            )
            remediated_rows.append(result_row)
            patched_by_xmodel[str(xmodel_path)] = result_row
            error_count += 1
            continue

        zone_hint = infer_zone_from_xmodel_path(xmodel_path)
        requested_load_zones = [path.resolve() for path in base_load_zones]
        if zone_hint:
            zone_ff = (repo_root / "zone" / "all" / f"{zone_hint}.ff").resolve()
            if zone_ff.exists() and zone_ff not in requested_load_zones:
                requested_load_zones.append(zone_ff)

        project_name = sanitize_name(f"remediate_{idx}_{xmodel_path.stem}")
        try:
            oracle = compile_xmodels(
                xmodel_jsons=[xmodel_path],
                project_name=project_name,
                workspace=workspace,
                linker_path=linker_path,
                load_zones=requested_load_zones,
                clean_workspace=True,
                verbose=args.verbose,
                auto_resolve_missing=True,
                max_retries=max(0, args.max_retries),
                dependency_roots=dependency_roots,
            )
            label = 1 if oracle["linker"]["status"] == "pass" else 0
            status = "improved_pass" if label == 1 else "still_fail"
            if label == 1:
                improved_count += 1
            else:
                still_fail_count += 1

            result_row.update(
                {
                    "status": status,
                    "label": label,
                    "project_name": project_name,
                    "load_zones_requested": [str(path) for path in requested_load_zones],
                    "load_zones_final": oracle.get("load_zones", []),
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
            )
        except Exception as exc:  # pragma: no cover - batch robustness
            result_row.update(
                {
                    "status": "error",
                    "label": 0,
                    "project_name": project_name,
                    "oracle": {"status": "error", "exit_code": -1, "errors": [str(exc)], "warnings": []},
                }
            )
            error_count += 1

        remediated_rows.append(result_row)
        patched_by_xmodel[str(xmodel_path)] = result_row

    remediated_jsonl = output_dir / "compile_remediation.jsonl"
    with remediated_jsonl.open("w", encoding="utf-8") as handle:
        for row in remediated_rows:
            handle.write(json.dumps(row) + "\n")

    signature_counts = Counter(
        normalize_error_signature(row.get("oracle", {}).get("errors", []))
        for row in remediated_rows
        if int(row.get("label", 0)) == 0
    )

    patched_dataset = output_dir / "compile_dataset_remediated.jsonl"
    with patched_dataset.open("w", encoding="utf-8") as handle:
        for row in rows:
            xmodel_path = str(Path(str(row.get("xmodel_path", ""))).resolve())
            replacement = patched_by_xmodel.get(xmodel_path)
            if replacement:
                if replacement.get("label", 0) == 1 or args.replace_all_attempted:
                    patched_row = {
                        "generated_at_utc": replacement.get("generated_at_utc", row.get("generated_at_utc", "")),
                        "xmodel_path": xmodel_path,
                        "project_name": replacement.get("project_name", row.get("project_name", "")),
                        "label": int(replacement.get("label", row.get("label", 0))),
                        "descriptor_features": row.get("descriptor_features", {}),
                        "oracle": replacement.get("oracle", row.get("oracle", {})),
                        "remediation": {
                            "status": replacement.get("status", ""),
                            "previous_signature": replacement.get("previous_signature", ""),
                        },
                    }
                    handle.write(json.dumps(patched_row) + "\n")
                    continue
            handle.write(json.dumps(row) + "\n")

    report = {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "input_dataset_jsonl": str(dataset_jsonl),
        "input_failure_summary": str(failure_summary) if failure_summary else "",
        "workspace": str(workspace),
        "linker": str(linker_path),
        "base_load_zones": [str(path) for path in base_load_zones],
        "dependency_roots": [str(path) for path in dependency_roots],
        "counts": {
            "total_rows": len(rows),
            "fail_rows_in_input": sum(1 for row in rows if int(row.get("label", 0)) == 0),
            "attempted": len(remediated_rows),
            "improved_pass": improved_count,
            "still_fail": still_fail_count,
            "error": error_count,
        },
        "top_post_failure_signatures": [
            {"signature": signature, "count": int(count)}
            for signature, count in signature_counts.most_common(25)
        ],
        "outputs": {
            "remediation_jsonl": str(remediated_jsonl),
            "patched_dataset_jsonl": str(patched_dataset),
        },
        "rows": remediated_rows,
    }

    report_path = output_dir / "compile_remediation_report.json"
    save_json(report_path, report)

    print(f"Saved remediation rows: {remediated_jsonl}")
    print(f"Saved remediated dataset: {patched_dataset}")
    print(f"Saved remediation report: {report_path}")
    print(
        f"attempted={report['counts']['attempted']} "
        f"improved={report['counts']['improved_pass']} "
        f"still_fail={report['counts']['still_fail']} "
        f"errors={report['counts']['error']}"
    )


if __name__ == "__main__":
    main()
