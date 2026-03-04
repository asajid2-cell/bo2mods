from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent

import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import save_json  # noqa: E402
from linker_oracle import sanitize_name  # noqa: E402


def run_cmd(args: List[str]) -> Tuple[int, str]:
    proc = subprocess.run(args, capture_output=True, text=True, check=False)
    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, out


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Iteratively increase map bootstrap size and track compilable coverage.")
    parser.add_argument("--plan", required=True, help="Input map port plan JSON.")
    parser.add_argument("--project-base", required=True, help="Base project name for trial projects.")
    parser.add_argument("--output-root", default="_build/asset_port_pipeline/map_port_projects", help="Trial project output root.")
    parser.add_argument("--start-assets", type=int, default=200, help="Initial max-assets per trial.")
    parser.add_argument("--step-assets", type=int, default=200, help="Asset increment per trial.")
    parser.add_argument("--max-assets", type=int, default=2000, help="Max max-assets to attempt.")
    parser.add_argument("--max-trials", type=int, default=8, help="Upper bound on trial count.")
    parser.add_argument("--map-retries", type=int, default=20, help="Map remediation retries per trial.")
    parser.add_argument("--load-zones", nargs="*", default=["zone/all/common_zm.ff", "zone/all/zm_tomb.ff"], help="Load zones for remediation.")
    parser.add_argument("--dependency-roots", nargs="*", default=["zone_dump/zone_raw", "_build/t6_asset_dump/zone_raw"], help="Dependency roots for remediation.")
    parser.add_argument("--output", default="_build/asset_port_pipeline/map_bootstrap_iteration_report.json", help="Iteration report output path.")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    plan = Path(args.plan)
    if not plan.is_absolute():
        plan = (repo_root / plan).resolve()
    if not plan.exists():
        raise FileNotFoundError(f"Plan not found: {plan}")

    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = (repo_root / output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    start_assets = max(1, int(args.start_assets))
    step_assets = max(1, int(args.step_assets))
    max_assets = max(start_assets, int(args.max_assets))
    max_trials = max(1, int(args.max_trials))

    trial_rows: List[Dict[str, Any]] = []
    best_pass: Optional[Dict[str, Any]] = None

    trial_index = 0
    assets = start_assets
    while assets <= max_assets and trial_index < max_trials:
        trial_index += 1
        trial_name = sanitize_name(f"{args.project_base}_{assets}")
        bootstrap_report = repo_root / "_build" / "asset_port_pipeline" / f"map_bootstrap_{trial_name}.json"
        rem_report = repo_root / "_build" / "asset_port_pipeline" / f"map_remediate_{trial_name}.json"

        bootstrap_cmd = [
            sys.executable,
            str((SCRIPT_DIR / "bootstrap_map_port_project.py").resolve()),
            "--plan",
            str(plan),
            "--project-name",
            trial_name,
            "--output-root",
            str(output_root),
            "--include-phases",
            "core_map",
            "render_assets",
            "gameplay_assets",
            "scripts",
            "--max-assets",
            str(assets),
            "--output-report",
            str(bootstrap_report),
        ]
        boot_exit, boot_log = run_cmd(bootstrap_cmd)
        if boot_exit != 0 or not bootstrap_report.exists():
            trial_rows.append(
                {
                    "trial": trial_index,
                    "project": trial_name,
                    "assets_requested": assets,
                    "status": "bootstrap_error",
                    "bootstrap_exit": boot_exit,
                    "bootstrap_log": boot_log[-8000:],
                }
            )
            assets += step_assets
            continue

        bootstrap_payload = load_json(bootstrap_report)
        project_root = output_root / trial_name

        remediate_cmd = [
            sys.executable,
            str((SCRIPT_DIR / "remediate_map_project.py").resolve()),
            "--project-root",
            str(project_root),
            "--project-name",
            trial_name,
            "--load-zones",
        ] + list(args.load_zones) + [
            "--dependency-roots",
        ] + list(args.dependency_roots) + [
            "--max-retries",
            str(args.map_retries),
            "--prune-unresolved",
            "--output",
            str(rem_report),
        ]

        rem_exit, rem_log = run_cmd(remediate_cmd)
        if rem_exit != 0 or not rem_report.exists():
            trial_rows.append(
                {
                    "trial": trial_index,
                    "project": trial_name,
                    "assets_requested": assets,
                    "status": "remediation_error",
                    "bootstrap_counts": bootstrap_payload.get("counts", {}),
                    "remediation_exit": rem_exit,
                    "remediation_log": rem_log[-8000:],
                }
            )
            assets += step_assets
            continue

        rem_payload = load_json(rem_report)
        final = rem_payload.get("final", {})
        final_status = str(final.get("status", "fail"))
        row = {
            "trial": trial_index,
            "project": trial_name,
            "assets_requested": assets,
            "status": final_status,
            "bootstrap_counts": bootstrap_payload.get("counts", {}),
            "remediation_attempts": len(rem_payload.get("attempts", [])),
            "remediation_errors": len(final.get("errors", [])),
            "final_zone_lines": sum(
                1
                for line in (project_root / "zone_source" / f"{trial_name}.zone").read_text(encoding="utf-8", errors="ignore").splitlines()
                if line.strip() and not line.strip().startswith("//") and not line.strip().startswith(">")
            ),
            "bootstrap_report": str(bootstrap_report),
            "remediation_report": str(rem_report),
        }
        trial_rows.append(row)

        if final_status == "pass":
            if best_pass is None or int(row["final_zone_lines"]) > int(best_pass["final_zone_lines"]):
                best_pass = row

        assets += step_assets

    report = {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "plan": str(plan),
        "project_base": sanitize_name(args.project_base),
        "output_root": str(output_root),
        "range": {
            "start_assets": start_assets,
            "step_assets": step_assets,
            "max_assets": max_assets,
            "max_trials": max_trials,
        },
        "counts": {
            "trials": len(trial_rows),
            "passes": sum(1 for row in trial_rows if row.get("status") == "pass"),
            "fails": sum(1 for row in trial_rows if row.get("status") == "fail"),
            "errors": sum(1 for row in trial_rows if row.get("status", "").endswith("_error")),
        },
        "best_pass": best_pass or {},
        "rows": trial_rows,
    }

    output = Path(args.output)
    if not output.is_absolute():
        output = (repo_root / output).resolve()
    save_json(output, report)
    print(f"Saved map bootstrap iteration report: {output}")
    if best_pass:
        print(
            f"best_pass_project={best_pass['project']} "
            f"assets_requested={best_pass['assets_requested']} "
            f"zone_lines={best_pass['final_zone_lines']}"
        )
    else:
        print("No passing iteration found.")


if __name__ == "__main__":
    main()
