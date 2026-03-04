from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List


def resolve_path(path_value: str, repo_root: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    return path


def severity_rank(value: str) -> int:
    order = {"info": 0, "warn": 1, "fail": 2}
    return order.get(value, 1)


def add_issue(issues: List[Dict[str, str]], severity: str, message: str, asset: str = "") -> None:
    payload = {"severity": severity, "message": message}
    if asset:
        payload["asset"] = asset
    issues.append(payload)


def analyze_row(
    row: Dict[str, Any],
    submesh_limit: int,
    warn_scale_low: float,
    warn_scale_high: float,
    fail_scale_low: float,
    fail_scale_high: float,
    min_bo2_bone_ratio: float,
) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    asset = str(row.get("asset_name", "") or row.get("source", ""))
    metadata = row.get("metadata") or {}
    has_armature = bool(metadata.get("has_armature", False))
    source_has_armature = bool(metadata.get("source_has_armature", has_armature))
    bo2_ratio = float(metadata.get("bo2_bone_name_ratio", 0.0) or 0.0)
    bbox_ratio = float(metadata.get("bbox_ratio_max_dim", 1.0) or 1.0)
    split_stats = metadata.get("split_stats") or {}
    max_submesh = int(split_stats.get("max_submesh_vertices", 0) or 0)
    over_limit = int(split_stats.get("submesh_over_limit", 0) or 0)
    vertex_groups = int(metadata.get("vertex_group_count", 0) or 0)
    mesh_vertices = int(metadata.get("mesh_vertices", 0) or 0)
    fallback_copy_mode = bool(metadata.get("fallback_copy_mode", False))

    if fallback_copy_mode:
        add_issue(issues, "warn", "fallback_copy_mode enabled; audit depth reduced", asset)
        return issues

    if source_has_armature and not has_armature:
        add_issue(issues, "fail", "armature dropped during conversion (risk: t-pose/crunch)", asset)
    if has_armature and bo2_ratio < float(min_bo2_bone_ratio):
        add_issue(issues, "warn", f"low BO2 bone/tag naming ratio: {bo2_ratio:.3f}", asset)
    if bbox_ratio < float(fail_scale_low) or bbox_ratio > float(fail_scale_high):
        add_issue(issues, "fail", f"severe scale drift detected (bbox_ratio_max_dim={bbox_ratio:.3f})", asset)
    elif bbox_ratio < float(warn_scale_low) or bbox_ratio > float(warn_scale_high):
        add_issue(issues, "warn", f"moderate scale drift detected (bbox_ratio_max_dim={bbox_ratio:.3f})", asset)

    if over_limit > 0:
        add_issue(
            issues,
            "fail",
            f"submesh vertex limit exceeded ({over_limit} submeshes over {submesh_limit}; max={max_submesh})",
            asset,
        )
    elif max_submesh > int(submesh_limit):
        add_issue(issues, "warn", f"max_submesh_vertices still over target: {max_submesh}", asset)

    if has_armature and vertex_groups <= 0:
        add_issue(issues, "fail", "armature present but vertex groups are empty", asset)
    if mesh_vertices <= 16:
        add_issue(issues, "fail", f"mesh vertex count too low ({mesh_vertices})", asset)

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Run conversion fidelity audit checks.")
    parser.add_argument("--blender-report", required=True, help="Path to blender_convert report JSON.")
    parser.add_argument("--output", default="_build/asset_port_pipeline/fidelity_audit_report.json", help="Output report path.")
    parser.add_argument("--submesh-limit", type=int, default=2400, help="Expected BO2-friendly submesh vertex cap.")
    parser.add_argument("--warn-scale-low", type=float, default=0.70, help="Warn when output/input max-dim ratio is below this.")
    parser.add_argument("--warn-scale-high", type=float, default=1.50, help="Warn when output/input max-dim ratio is above this.")
    parser.add_argument("--fail-scale-low", type=float, default=0.35, help="Fail when output/input max-dim ratio is below this.")
    parser.add_argument("--fail-scale-high", type=float, default=2.85, help="Fail when output/input max-dim ratio is above this.")
    parser.add_argument("--min-bo2-bone-ratio", type=float, default=0.70, help="Minimum recommended BO2-style bone/tag ratio.")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    blender_report = resolve_path(args.blender_report, repo_root)
    output = resolve_path(args.output, repo_root)
    output.parent.mkdir(parents=True, exist_ok=True)

    payload = json.loads(blender_report.read_text(encoding="utf-8"))
    rows = [row for row in payload.get("rows", []) if row.get("status") == "ok"]
    issues: List[Dict[str, str]] = []
    for row in rows:
        issues.extend(
            analyze_row(
                row=row,
                submesh_limit=max(1, int(args.submesh_limit)),
                warn_scale_low=float(args.warn_scale_low),
                warn_scale_high=float(args.warn_scale_high),
                fail_scale_low=float(args.fail_scale_low),
                fail_scale_high=float(args.fail_scale_high),
                min_bo2_bone_ratio=float(args.min_bo2_bone_ratio),
            )
        )

    final_status = "pass"
    if any(item["severity"] == "fail" for item in issues):
        final_status = "fail"
    elif any(item["severity"] == "warn" for item in issues):
        final_status = "warn"

    issues_sorted = sorted(issues, key=lambda item: severity_rank(item.get("severity", "warn")), reverse=True)
    report = {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "blender_report": str(blender_report),
        "counts": {
            "rows_ok": len(rows),
            "issues_total": len(issues_sorted),
            "fail": sum(1 for item in issues_sorted if item.get("severity") == "fail"),
            "warn": sum(1 for item in issues_sorted if item.get("severity") == "warn"),
            "info": sum(1 for item in issues_sorted if item.get("severity") == "info"),
        },
        "final_status": final_status,
        "issues": issues_sorted,
    }
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved fidelity audit report: {output}")
    print(f"status={final_status} rows_ok={len(rows)} issues={len(issues_sorted)}")


if __name__ == "__main__":
    main()
