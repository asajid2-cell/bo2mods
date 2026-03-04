#!/usr/bin/env python3
"""Classify latest Plutonium runtime log into stable failure gates."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass


DEFAULT_LOG = os.path.expandvars(
    r"%LOCALAPPDATA%\Plutonium\storage\t6\main\console_zm.log"
)


@dataclass
class GateResult:
    id: str
    passed: bool
    detail: str


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def analyze(log_text: str, require_tg: bool = False) -> dict:
    gates: list[GateResult] = []

    com_errors = re.findall(r"COM_ERROR", log_text)
    missing_animtree = re.findall(r"Couldn't find animtree '([^']+)'", log_text)
    tg_give_fail = re.findall(r"\[ROGUE\] event=tg_give;[^\n]*has=0", log_text)
    tg_give_ok = re.findall(r"\[ROGUE\] event=tg_give;[^\n]*has=1", log_text)
    missing_rogue_weapon = re.findall(
        r'Could not load weapon "(rogue_thundergun(?:_upgraded)?_zm)"',
        log_text,
    )
    missing_weapons_all = re.findall(r'Could not load weapon "([^"]+)"', log_text)
    tg_try_fail = re.findall(
        r"\[ROGUE\] event=tg_step;[^\n]*stage=after_giveweapon;[^\n]*ok=0",
        log_text,
    )
    tg_try_ok = re.findall(
        r"\[ROGUE\] event=tg_step;[^\n]*stage=after_giveweapon;[^\n]*ok=1",
        log_text,
    )
    awaiting_gamestate = re.findall(r"Awaiting gamestate", log_text, flags=re.I)
    client_connected = re.findall(r"client '.*' connected", log_text)

    # Missing large swaths of weapon assets indicates a fundamentally broken FF/runtime
    # surface, not a single-weapon registration issue.
    core_weapon_meltdown = len(missing_weapons_all) >= 20

    gates.append(
        GateResult(
            id="no_com_error",
            passed=len(com_errors) == 0,
            detail=f"com_error_count={len(com_errors)}",
        )
    )
    gates.append(
        GateResult(
            id="no_missing_animtree",
            passed=len(missing_animtree) == 0,
            detail=(
                "missing_animtrees=none"
                if not missing_animtree
                else "missing_animtrees=" + ",".join(sorted(set(missing_animtree)))
            ),
        )
    )
    gates.append(
        GateResult(
            id="rogue_weapon_registered",
            passed=len(missing_rogue_weapon) == 0,
            detail=(
                "missing_rogue_weapon=none"
                if not missing_rogue_weapon
                else "missing_rogue_weapon="
                + ",".join(sorted(set(missing_rogue_weapon)))
            ),
        )
    )
    gates.append(
        GateResult(
            id="no_core_weapon_meltdown",
            passed=not core_weapon_meltdown,
            detail=f"missing_weapon_total={len(missing_weapons_all)} threshold=20",
        )
    )
    if require_tg:
        tg_passed = (len(tg_give_ok) > 0 and len(tg_give_fail) == 0)
    else:
        tg_passed = (len(tg_give_fail) == 0)
    gates.append(
        GateResult(
            id="tg_give_succeeds",
            passed=tg_passed,
            detail=(
                f"tg_give_ok={len(tg_give_ok)} tg_give_fail={len(tg_give_fail)} "
                f"require_tg={int(require_tg)}"
            ),
        )
    )
    gates.append(
        GateResult(
            id="tg_giveweapon_accepts_asset",
            passed=(len(tg_try_ok) > 0 or len(tg_try_fail) == 0),
            detail=f"tg_try_ok={len(tg_try_ok)} tg_try_fail={len(tg_try_fail)}",
        )
    )
    gates.append(
        GateResult(
            id="map_reaches_gameplay",
            passed=(len(client_connected) > 0 and len(awaiting_gamestate) == 0),
            detail=f"client_connected={len(client_connected)} awaiting_gamestate={len(awaiting_gamestate)}",
        )
    )

    passed_all = all(g.passed for g in gates)
    if len(missing_animtree) > 0:
        classification = "missing_animtree"
    elif core_weapon_meltdown:
        classification = "core_weapon_surface_broken"
    elif len(missing_rogue_weapon) > 0:
        classification = "rogue_weapon_not_registered"
    elif len(tg_try_fail) > 0 and len(tg_try_ok) == 0:
        classification = "tg_asset_rejected_by_giveweapon"
    elif len(awaiting_gamestate) > 0 and len(client_connected) == 0:
        classification = "startup_hang_awaiting_gamestate"
    elif len(com_errors) > 0:
        classification = "runtime_com_error"
    else:
        classification = "healthy_or_nonfatal_warnings"
    return {
        "passed_all": passed_all,
        "classification": classification,
        "counters": {
            "com_error_count": len(com_errors),
            "missing_animtree_count": len(missing_animtree),
            "missing_weapon_total": len(missing_weapons_all),
            "missing_rogue_weapon_count": len(missing_rogue_weapon),
            "tg_give_ok": len(tg_give_ok),
            "tg_give_fail": len(tg_give_fail),
            "tg_try_ok": len(tg_try_ok),
            "tg_try_fail": len(tg_try_fail),
            "awaiting_gamestate_hits": len(awaiting_gamestate),
            "client_connected_hits": len(client_connected),
        },
        "gates": [g.__dict__ for g in gates],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", default=DEFAULT_LOG, help="Path to console_zm.log")
    parser.add_argument("--json-out", default="", help="Optional report output path")
    parser.add_argument(
        "--require-tg",
        action="store_true",
        help="Fail if no successful TG give event is observed.",
    )
    args = parser.parse_args()

    if not os.path.exists(args.log):
        print(json.dumps({"error": f"log not found: {args.log}"}, indent=2))
        return 2

    report = analyze(_read_text(args.log), require_tg=args.require_tg)
    rendered = json.dumps(report, indent=2)
    print(rendered)

    if args.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)), exist_ok=True)
        with open(args.json_out, "w", encoding="ascii") as f:
            f.write(rendered + "\n")

    return 0 if report["passed_all"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
