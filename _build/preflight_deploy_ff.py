#!/usr/bin/env python3
"""Preflight + deploy helper for so_zsurvival_zm_transit.ff.

Refuses deployment if structural integrity checks fail.
"""

import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ff_integrity_check import run_check  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Preflight-check and deploy a candidate FF.")
    ap.add_argument("--baseline-ff", required=True)
    ap.add_argument("--candidate-ff", required=True)
    ap.add_argument("--zone-name", default="so_zsurvival_zm_transit")
    ap.add_argument("--strict-counts", action="store_true")
    ap.add_argument("--deploy-game-ff", required=True)
    ap.add_argument("--deploy-mod-ff", required=True)
    ap.add_argument("--report-json", default="_build/reports/preflight_deploy_report.json")
    args = ap.parse_args()

    ok, report = run_check(
        baseline_ff=args.baseline_ff,
        candidate_ff=args.candidate_ff,
        zone_name=args.zone_name,
        name_prefix="vm_thunder_gun_",
        strict_counts=args.strict_counts,
    )

    os.makedirs(os.path.dirname(args.report_json), exist_ok=True)
    with open(args.report_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    if not ok:
        print("Preflight FAIL. Deployment aborted.")
        for e in report.get("errors", []):
            print(f"  - {e}")
        print(f"Report: {args.report_json}")
        return 1

    os.makedirs(os.path.dirname(args.deploy_game_ff), exist_ok=True)
    os.makedirs(os.path.dirname(args.deploy_mod_ff), exist_ok=True)
    shutil.copy2(args.candidate_ff, args.deploy_game_ff)
    shutil.copy2(args.candidate_ff, args.deploy_mod_ff)

    print("Preflight PASS. Deployed candidate FF:")
    print(f"  game: {args.deploy_game_ff} ({os.path.getsize(args.deploy_game_ff):,} bytes)")
    print(f"  mod : {args.deploy_mod_ff} ({os.path.getsize(args.deploy_mod_ff):,} bytes)")
    print(f"Report: {args.report_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
