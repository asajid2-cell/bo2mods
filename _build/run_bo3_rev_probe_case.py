#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "_build" / "build_bo3_rev_idg_probe.py"
DEFAULT_CUSTOM_GLB = ROOT / "_build" / "bo3_rev_idg_weapon_acceptance" / "bo3_rev_idg_weapon_only.glb"
ARCHIVE_ROOT = ROOT / "_build" / "bo3_rev_probe_cases"


CASES: dict[str, dict[str, str]] = {
    "raygun_stock_tiny": {
        "ROGUE_PROBE_SHELL": "ray_gun_zm",
        "ROGUE_STARTER_WEAPON": "m1911_zm",
        "ROGUE_GUN_MODEL_MODE": "literal",
        "ROGUE_GUN_MODEL_LITERAL": "viewmodel_usa_no_model",
        "ROGUE_USE_BO3_IDG_ANIMS": "0",
        "ROGUE_USE_CUSTOM_IDG_VIEWHANDS": "0",
        "ROGUE_FORCE_LOW_HANDMODEL": "1",
        "ROGUE_ALLOW_STRIPPED_SURVIVAL_FF": "1",
    },
    "raygun_custom_tiny": {
        "ROGUE_PROBE_SHELL": "ray_gun_zm",
        "ROGUE_STARTER_WEAPON": "m1911_zm",
        "ROGUE_GUN_MODEL_MODE": "custom",
        "ROGUE_IDG_VIEW_GLB": str(DEFAULT_CUSTOM_GLB),
        "ROGUE_USE_BO3_IDG_ANIMS": "0",
        "ROGUE_USE_CUSTOM_IDG_VIEWHANDS": "0",
        "ROGUE_FORCE_LOW_HANDMODEL": "1",
        "ROGUE_ALLOW_STRIPPED_SURVIVAL_FF": "1",
    },
    "raygun_stock_rpg": {
        "ROGUE_PROBE_SHELL": "ray_gun_zm",
        "ROGUE_STARTER_WEAPON": "m1911_zm",
        "ROGUE_GUN_MODEL_MODE": "literal",
        "ROGUE_GUN_MODEL_LITERAL": "t6_wpn_launch_usrpg_view",
        "ROGUE_USE_BO3_IDG_ANIMS": "0",
        "ROGUE_USE_CUSTOM_IDG_VIEWHANDS": "0",
        "ROGUE_FORCE_LOW_HANDMODEL": "1",
        "ROGUE_ALLOW_STRIPPED_SURVIVAL_FF": "1",
    },
    "m1911_custom_tiny": {
        "ROGUE_PROBE_SHELL": "m1911_zm",
        "ROGUE_STARTER_WEAPON": "m1911_zm",
        "ROGUE_GUN_MODEL_MODE": "custom",
        "ROGUE_IDG_VIEW_GLB": str(DEFAULT_CUSTOM_GLB),
        "ROGUE_USE_BO3_IDG_ANIMS": "0",
        "ROGUE_USE_CUSTOM_IDG_VIEWHANDS": "0",
        "ROGUE_FORCE_LOW_HANDMODEL": "1",
        "ROGUE_ALLOW_STRIPPED_SURVIVAL_FF": "1",
    },
    "m14_v2_bo3_weapon_only": {
        "ROGUE_PROBE_SHELL": "m14_zm",
        "ROGUE_STARTER_WEAPON": "m1911_zm",
        "ROGUE_GUN_MODEL_MODE": "custom",
        "ROGUE_IDG_VIEW_GLB": str(ROOT / "_build" / "bo3_rev_idg_weapon_only" / "bo3_rev_idg_weapon_only.glb"),
        "ROGUE_MODEL_ASSET_BASE": "bo3_rev_v2_idg_view",
        "ROGUE_USE_BO3_IDG_ANIMS": "0",
        "ROGUE_USE_CUSTOM_IDG_VIEWHANDS": "0",
        "ROGUE_FORCE_LOW_HANDMODEL": "1",
        "ROGUE_ALLOW_STRIPPED_SURVIVAL_FF": "0",
        "ROGUE_DEPLOY_TO_BASE": "1",
    },
    "mg08_v2_bo3_weapon_only": {
        "ROGUE_PROBE_SHELL": "mg08_zm",
        "ROGUE_STARTER_WEAPON": "mg08_zm",
        "ROGUE_GUN_MODEL_MODE": "custom",
        "ROGUE_IDG_VIEW_GLB": str(ROOT / "_build" / "bo3_rev_idg_weapon_only" / "bo3_rev_idg_weapon_only.glb"),
        "ROGUE_MODEL_ASSET_BASE": "bo3_rev_v2_idg_view",
        "ROGUE_USE_BO3_IDG_ANIMS": "0",
        "ROGUE_USE_CUSTOM_IDG_VIEWHANDS": "0",
        "ROGUE_FORCE_LOW_HANDMODEL": "1",
        "ROGUE_ALLOW_STRIPPED_SURVIVAL_FF": "0",
        "ROGUE_DEPLOY_TO_BASE": "1",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a named BO3 Rev probe case.")
    parser.add_argument("case", choices=sorted(CASES))
    parser.add_argument("--no-deploy", action="store_true", help="Build without deploying to the mod directories.")
    args = parser.parse_args()

    env = os.environ.copy()
    env.update(CASES[args.case])
    if args.no_deploy:
        env["ROGUE_DEPLOY_TO_MOD"] = "0"
        env["ROGUE_DEPLOY_TO_BASE"] = "0"

    result = subprocess.run([sys.executable, str(BUILD_SCRIPT)], cwd=str(ROOT), env=env)
    if result.returncode != 0:
        return result.returncode

    report_path = ROOT / "_build" / "bo3_rev_idg_probe" / "build_report.json"
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        archive_dir = ARCHIVE_ROOT / args.case
        archive_dir.mkdir(parents=True, exist_ok=True)
        tagged_report = archive_dir / f"build_report_{report.get('build_tag', 'unknown')}.json"
        shutil.copy2(report_path, tagged_report)
        print(f"Archived report -> {tagged_report}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
