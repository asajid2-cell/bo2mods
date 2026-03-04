#!/usr/bin/env python3
"""Offline integrity checker for T6 fastfiles.

This rejects structurally risky builds before in-game testing by comparing a
candidate FF against a known-good baseline FF.
"""

import argparse
import json
import os
import struct
import sys
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(__file__))
from patch_zone_xanims import decrypt_zone, parse_string_table, find_empty_xanim_stubs  # noqa: E402


def _read_indexed_strings(raw: bytes, count: int, string_data_start: int) -> List[str]:
    out = []
    pos = string_data_start
    for _ in range(count):
        end = raw.index(b"\x00", pos)
        out.append(raw[pos:end].decode("ascii", errors="replace"))
        pos = end + 1
    return out


def _xfile_header_info(raw: bytes) -> Dict[str, int]:
    if len(raw) < 40:
        return {"ok": 0, "reason": "raw shorter than XFile header", "totalSize": -1}
    total_size = struct.unpack_from("<I", raw, 0)[0]
    return {
        "ok": 1,
        "totalSize": total_size,
        "expectedRawLen": total_size + 40,
        "actualRawLen": len(raw),
        "rawLenMatchesHeader": 1 if (len(raw) == total_size + 40) else 0,
    }


def _find_marker_offsets(raw: bytes, markers: List[str]) -> Dict[str, int]:
    out = {}
    for m in markers:
        b = m.encode("ascii") + b"\x00"
        out[m] = raw.find(b)
    return out


def _sample_script_markers(script_names: List[str], limit: int = 24) -> List[str]:
    # deterministic sample for stable reports
    picks = sorted(script_names)
    if len(picks) <= limit:
        return picks
    stride = max(1, len(picks) // limit)
    sampled = picks[::stride][:limit]
    return sampled


def _compare_shifted_windows(
    baseline_raw: bytes,
    candidate_raw: bytes,
    markers: List[str],
    base_off: Dict[str, int],
    cand_off: Dict[str, int],
    delta: int,
    window: int = 64,
) -> List[str]:
    mismatches = []
    for m in markers:
        b_off = base_off.get(m, -1)
        c_off = cand_off.get(m, -1)
        if b_off < 0 or c_off < 0:
            continue
        # compare a small neighborhood with expected uniform shift
        exp = b_off + delta
        if c_off != exp:
            mismatches.append(f"{m}: offset mismatch (actual {c_off}, expected {exp})")
            continue
        b_start = max(0, b_off - window)
        b_end = min(len(baseline_raw), b_off + len(m) + 1 + window)
        c_start = max(0, c_off - window)
        c_end = min(len(candidate_raw), c_off + len(m) + 1 + window)
        if (b_end - b_start) != (c_end - c_start):
            mismatches.append(f"{m}: unequal compare window sizes")
            continue
        if baseline_raw[b_start:b_end] != candidate_raw[c_start:c_end]:
            mismatches.append(f"{m}: shifted neighborhood differs")
    return mismatches


def run_check(
    baseline_ff: str,
    candidate_ff: str,
    zone_name: str,
    name_prefix: str,
    strict_counts: bool,
) -> Tuple[bool, Dict]:
    report: Dict = {
        "inputs": {
            "baseline_ff": baseline_ff,
            "candidate_ff": candidate_ff,
            "zone_name": zone_name,
            "name_prefix": name_prefix,
        },
        "checks": {},
        "warnings": [],
        "errors": [],
    }

    # Decrypt both files first
    try:
        _, baseline_raw = decrypt_zone(baseline_ff, zone_name)
        _, candidate_raw = decrypt_zone(candidate_ff, zone_name)
    except Exception as e:
        report["errors"].append(f"decrypt failed: {e}")
        return False, report

    base_hdr = _xfile_header_info(baseline_raw)
    cand_hdr = _xfile_header_info(candidate_raw)
    report["checks"]["baseline_xfile"] = base_hdr
    report["checks"]["candidate_xfile"] = cand_hdr
    if not cand_hdr.get("rawLenMatchesHeader", 0):
        report["errors"].append(
            "candidate raw length mismatch vs XFile totalSize header "
            f"({cand_hdr.get('actualRawLen')} != {cand_hdr.get('expectedRawLen')})"
        )

    # Parse string tables
    try:
        base_info = parse_string_table(baseline_raw)
        cand_info = parse_string_table(candidate_raw)
        (base_map, base_sc, base_ac, _base_asset_off,
         _base_ptr, base_sstart, _base_send) = base_info
        (cand_map, cand_sc, cand_ac, _cand_asset_off,
         _cand_ptr, cand_sstart, _cand_send) = cand_info
    except Exception as e:
        report["errors"].append(f"parse_string_table failed: {e}")
        return False, report

    report["checks"]["string_counts"] = {
        "baseline": base_sc,
        "candidate": cand_sc,
        "match": (base_sc == cand_sc),
    }
    report["checks"]["asset_counts"] = {
        "baseline": base_ac,
        "candidate": cand_ac,
        "match": (base_ac == cand_ac),
    }
    if base_sc != cand_sc:
        msg = "string_count differs from baseline"
        if strict_counts:
            report["errors"].append(msg)
        else:
            report["warnings"].append(msg)
    if base_ac != cand_ac:
        msg = "asset_count differs from baseline"
        if strict_counts:
            report["errors"].append(msg)
        else:
            report["warnings"].append(msg)

    base_strings = _read_indexed_strings(baseline_raw, base_sc, base_sstart)
    cand_strings = _read_indexed_strings(candidate_raw, cand_sc, cand_sstart)
    base_set = set(base_strings)
    cand_set = set(cand_strings)

    # Script inventory parity check
    base_scripts = sorted(s for s in base_set if s.endswith(".gsc") and s.startswith("maps/"))
    missing_scripts = [s for s in base_scripts if s not in cand_set]
    report["checks"]["scripts"] = {
        "baseline_count": len(base_scripts),
        "missing_in_candidate": missing_scripts[:80],
        "missing_count": len(missing_scripts),
    }
    if missing_scripts:
        report["errors"].append(f"{len(missing_scripts)} baseline script names missing in candidate")

    # Marker-shift consistency check around critical scripts
    critical = [
        "maps/mp/zm_transit.gsc",
        "maps/mp/zombies/_zm_powerups.gsc",
        "maps/mp/_visionset_mgr.gsc",
        "maps/mp/zombies/_zm.gsc",
        "maps/mp/zombies/_zm_playerhealth.gsc",
    ]
    sampled = _sample_script_markers(base_scripts, limit=20)
    marker_list = []
    for m in critical + sampled:
        if m not in marker_list:
            marker_list.append(m)

    base_off = _find_marker_offsets(baseline_raw, marker_list)
    cand_off = _find_marker_offsets(candidate_raw, marker_list)
    deltas = {}
    for m in marker_list:
        bo = base_off.get(m, -1)
        co = cand_off.get(m, -1)
        if bo >= 0 and co >= 0:
            deltas[m] = co - bo
    unique_deltas = sorted(set(deltas.values()))
    report["checks"]["marker_deltas"] = {
        "count": len(deltas),
        "unique_deltas": unique_deltas,
        "examples": {k: deltas[k] for k in list(deltas.keys())[:12]},
    }
    if len(unique_deltas) > 1:
        report["errors"].append(
            f"script marker deltas are not uniform ({len(unique_deltas)} unique)"
        )

    if len(unique_deltas) == 1:
        delta = unique_deltas[0]
        mismatches = _compare_shifted_windows(
            baseline_raw, candidate_raw, marker_list, base_off, cand_off, delta, window=64
        )
        report["checks"]["shifted_window_compare"] = {
            "delta": delta,
            "mismatch_count": len(mismatches),
            "mismatches": mismatches[:80],
        }
        if mismatches:
            report["errors"].append(
                f"{len(mismatches)} shifted script-marker neighborhoods differ from baseline"
            )

    # XAnim stub/footprint visibility
    try:
        _, _, _, base_asset_off, _, _, _ = base_info
        _, _, _, cand_asset_off, _, _, _ = cand_info
        base_stubs = find_empty_xanim_stubs(baseline_raw, name_prefix, min_search_offset=base_asset_off)
        cand_stubs = find_empty_xanim_stubs(candidate_raw, name_prefix, min_search_offset=cand_asset_off)
        report["checks"]["xanim_stubs"] = {
            "baseline_stub_count": len(base_stubs),
            "candidate_stub_count": len(cand_stubs),
            "candidate_names_sample": [s["name"] for s in cand_stubs[:16]],
        }
    except Exception as e:
        report["warnings"].append(f"xanim stub scan failed: {e}")

    ok = len(report["errors"]) == 0
    return ok, report


def main() -> int:
    ap = argparse.ArgumentParser(description="Offline integrity checker for T6 FF builds.")
    ap.add_argument("--baseline-ff", required=True)
    ap.add_argument("--candidate-ff", required=True)
    ap.add_argument("--zone-name", required=True)
    ap.add_argument("--name-prefix", default="vm_thunder_gun_")
    ap.add_argument("--report-json", default=None)
    ap.add_argument(
        "--strict-counts",
        action="store_true",
        help="Fail if string_count or asset_count differ from baseline.",
    )
    args = ap.parse_args()

    ok, report = run_check(
        baseline_ff=args.baseline_ff,
        candidate_ff=args.candidate_ff,
        zone_name=args.zone_name,
        name_prefix=args.name_prefix,
        strict_counts=args.strict_counts,
    )

    print("=" * 72)
    print("FF Integrity Check")
    print("=" * 72)
    print(f"Baseline : {args.baseline_ff}")
    print(f"Candidate: {args.candidate_ff}")
    print(f"ZoneName : {args.zone_name}")
    print()
    print(f"Result   : {'PASS' if ok else 'FAIL'}")
    if report["errors"]:
        print("Errors:")
        for e in report["errors"]:
            print(f"  - {e}")
    if report["warnings"]:
        print("Warnings:")
        for w in report["warnings"]:
            print(f"  - {w}")

    if args.report_json:
        with open(args.report_json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nWrote report: {args.report_json}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
