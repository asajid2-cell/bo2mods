#!/usr/bin/env python3
"""
Batch BO3 conversion driver:
1) read unresolved anims from analyzer logic
2) add next N unresolved names to cumulative bo3 target set
3) run two_phase_build.py with bo3_frames + fallback=stub
4) re-analyze and print before/after deltas
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Dict, List, Sequence, Tuple


ROOT = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(ROOT, "reports")
TARGET_STATE_PATH = os.path.join(REPORT_DIR, "bo3_frames_target_accumulator.json")


def _load_analyzer_module():
    sys.path.insert(0, ROOT)
    import analyze_thundergun_crashes as az  # type: ignore

    return az


def _collect_unresolved(az) -> Tuple[List[Tuple[str, int, int]], List[Tuple[str, int]], Dict[str, int]]:
    source_numframes = az.collect_source_numframes(az.DEFAULT_XANIM_DIR)
    anim_numframes = az.collect_anim_numframes(az.DEFAULT_FF, az.ZONE_NAME, az.DEFAULT_XANIM_DIR)

    if az.DEFAULT_CUSTOM_XANIM_FF and os.path.exists(az.DEFAULT_CUSTOM_XANIM_FF):
        try:
            anim_numframes_custom = az.collect_anim_numframes(
                az.DEFAULT_CUSTOM_XANIM_FF,
                az.CUSTOM_XANIM_ZONE_NAME,
                az.DEFAULT_XANIM_DIR,
            )
            for k, v in anim_numframes_custom.items():
                anim_numframes[k] = v
        except Exception:
            pass

    mismatch: List[Tuple[str, int, int]] = []
    missing: List[Tuple[str, int]] = []
    for anim_name in sorted(source_numframes.keys()):
        src_nf = int(source_numframes.get(anim_name, 0))
        run_nf = int(anim_numframes.get(anim_name, 0))
        if run_nf <= 0:
            missing.append((anim_name, src_nf))
            continue
        if src_nf > 0 and run_nf != src_nf:
            mismatch.append((anim_name, run_nf, src_nf))
    return mismatch, missing, source_numframes


def _load_accumulated_targets(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        arr = data.get("targets", [])
        if isinstance(arr, list):
            return [str(x).strip() for x in arr if str(x).strip()]
    except Exception:
        return []
    return []


def _save_accumulated_targets(path: str, targets: Sequence[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"targets": list(targets)}, f, indent=2)


def _run_build(targets: Sequence[str], keep_game_closed: bool = True) -> int:
    env = os.environ.copy()
    env["ROGUE_TG_XANIM_EMIT_MODE"] = "bo3_frames"
    env["ROGUE_TG_XANIM_BO3_TARGETS"] = ",".join(targets)
    env["ROGUE_TG_XANIM_BO3_FALLBACK_MODE"] = "stub"
    env["ROGUE_TG_RIG_STRICT"] = "1"
    env["ROGUE_TG_XANIM_VERIFY_NAMES"] = ",".join(targets)
    # Keep linker lane stable for bo3_frames payloads.
    env["ROGUE_TG_LINKER_LOAD_CUSTOM_XANIM"] = "0"
    if keep_game_closed:
        # Helps avoid locked output copy failures; safe no-op when game is already closed.
        env["ROGUE_TG_RUNTIME_XANIM_TO_BASE"] = "1"
        env["ROGUE_TG_RUNTIME_XANIM_TO_MOD"] = "1"

    cmd = [sys.executable, os.path.join(ROOT, "two_phase_build.py")]
    return subprocess.run(cmd, env=env, timeout=3600).returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=4, help="How many new unresolved anims to add this cycle.")
    ap.add_argument(
        "--state-file",
        default=TARGET_STATE_PATH,
        help="Path to cumulative bo3 target-state JSON.",
    )
    args = ap.parse_args()

    batch_size = max(1, min(8, int(args.batch_size)))
    state_path = os.path.abspath(args.state_file)

    az = _load_analyzer_module()
    mismatch_before, missing_before, _ = _collect_unresolved(az)
    unresolved_before = [name for name, _r, _s in mismatch_before] + [name for name, _s in missing_before]
    unresolved_set = set(unresolved_before)

    acc = _load_accumulated_targets(state_path)
    acc_set = set(acc)
    candidates = [n for n in unresolved_before if n not in acc_set]
    batch = candidates[:batch_size]

    print(
        f"before: mismatch={len(mismatch_before)} missing={len(missing_before)} "
        f"unresolved={len(unresolved_before)} accumulated={len(acc)}"
    )
    if not batch:
        print("no new unresolved targets to add; nothing to do")
        return 0

    new_targets = sorted(acc_set | set(batch))
    print(f"batch add ({len(batch)}): {batch}")
    print(f"targets total ({len(new_targets)}): {new_targets}")

    rc = _run_build(new_targets)
    if rc != 0:
        print(f"build failed rc={rc}")
        return rc

    _save_accumulated_targets(state_path, new_targets)

    mismatch_after, missing_after, _ = _collect_unresolved(az)
    unresolved_after = [name for name, _r, _s in mismatch_after] + [name for name, _s in missing_after]
    resolved_this_batch = [n for n in batch if n in unresolved_set and n not in set(unresolved_after)]
    print(
        f"after: mismatch={len(mismatch_after)} missing={len(missing_after)} "
        f"unresolved={len(unresolved_after)}"
    )
    print(f"resolved from batch ({len(resolved_this_batch)}): {resolved_this_batch}")

    if mismatch_after:
        print("remaining mismatch names:")
        for name, run_nf, src_nf in mismatch_after:
            print(f"  - {name}: runtime={run_nf} source={src_nf}")
    if missing_after:
        print("remaining missing runtime names:")
        for name, src_nf in missing_after:
            print(f"  - {name}: runtime=0 source={src_nf}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
