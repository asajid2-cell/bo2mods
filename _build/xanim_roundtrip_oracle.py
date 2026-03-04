#!/usr/bin/env python3
"""Strict roundtrip oracle for T6 XAnimParts serialized blobs.

This validates parse/rebuild determinism for a known-good donor animation
before BO3->T6 per-frame encoding work.
"""

import argparse
import os
import sys
from typing import Dict, List

sys.path.insert(0, os.path.dirname(__file__))

from patch_zone_xanims import decrypt_zone, parse_string_table  # noqa: E402
import strict_xanim_parser as strict_xanim  # noqa: E402


SECTION_ORDER = [
    "name",
    "names",
    "notify",
    "deltaPart",
    "dataByte",
    "dataShort",
    "dataInt",
    "randomDataShort",
    "randomDataByte",
    "randomDataInt",
    "indices",
]

HEADER_COMPARE_KEYS = [
    "numframes",
    "framerate",
    "dataByteCount",
    "dataShortCount",
    "dataIntCount",
    "randomDataShortCount",
    "randomDataByteCount",
    "randomDataIntCount",
    "indexCount",
    "notifyCount",
    "assetType",
    "isDefault",
    "boneCount",
]


def _rebuild_from_sections(data: bytes, parsed: Dict) -> bytes:
    out = bytearray()
    h0 = int(parsed["header_offset"])
    h1 = int(parsed["end_offset"])
    out.extend(data[h0:h0 + 104])  # fixed XAnimParts header
    sections = parsed.get("sections", {})
    for key in SECTION_ORDER:
        s = sections.get(key)
        if not s:
            continue
        off = int(s.get("offset", 0))
        size = int(s.get("size", 0))
        out.extend(data[off:off + size])
    if len(out) != (h1 - h0):
        raise RuntimeError(
            f"rebuild size mismatch: rebuilt={len(out)} expected={h1 - h0}"
        )
    return bytes(out)


def _section_signature(parsed: Dict) -> Dict[str, int]:
    sig: Dict[str, int] = {}
    sections = parsed.get("sections", {})
    for key in SECTION_ORDER:
        s = sections.get(key)
        if s:
            sig[key] = int(s.get("size", 0))
    return sig


def _header_signature(parsed: Dict) -> Dict:
    h = parsed["header"]
    return {k: h.get(k) for k in HEADER_COMPARE_KEYS}


def run(ff_path: str, zone_name: str, asset_name: str) -> int:
    if not os.path.exists(ff_path):
        print(f"ERROR: ff not found: {ff_path}")
        return 2

    _, raw = decrypt_zone(ff_path, zone_name)
    parse_meta = parse_string_table(raw)
    asset_data_offset = int(parse_meta[3])

    matches = strict_xanim.find_xanim_by_name(raw, asset_name, min_offset=asset_data_offset)
    if not matches:
        print(f"ERROR: asset not found: {asset_name}")
        return 3

    parsed = matches[0]
    blob = raw[parsed["header_offset"]:parsed["end_offset"]]
    rebuilt = _rebuild_from_sections(raw, parsed)
    rebuilt_parsed = strict_xanim.parse_xanim_blob_auto(rebuilt, 0)

    byte_exact = blob == rebuilt
    hdr_a = _header_signature(parsed)
    hdr_b = _header_signature(rebuilt_parsed)
    sec_a = _section_signature(parsed)
    sec_b = _section_signature(rebuilt_parsed)
    header_ok = hdr_a == hdr_b
    sections_ok = sec_a == sec_b

    print(f"asset={asset_name}")
    print(f"ff={ff_path}")
    print(f"zone={zone_name}")
    print(f"blob_bytes={len(blob)}")
    print(f"byte_exact={1 if byte_exact else 0}")
    print(f"header_match={1 if header_ok else 0}")
    print(f"sections_match={1 if sections_ok else 0}")
    print(f"numframes={parsed['header']['numframes']}")
    print(f"framerate={parsed['header']['framerate']}")
    print(
        "RESULT: PASS"
        if (byte_exact and header_ok and sections_ok)
        else "RESULT: FAIL"
    )

    if not byte_exact:
        return 4
    if not header_ok:
        print("Header mismatch:")
        print(f"  donor={hdr_a}")
        print(f"  rebuilt={hdr_b}")
        return 5
    if not sections_ok:
        print("Section mismatch:")
        print(f"  donor={sec_a}")
        print(f"  rebuilt={sec_b}")
        return 6
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Roundtrip oracle for donor XAnimParts blobs.")
    ap.add_argument("--ff", required=True, help="Donor fastfile path.")
    ap.add_argument("--zone-name", required=True, help="Donor zone name.")
    ap.add_argument("--asset", required=True, help="Donor xanim asset name.")
    args = ap.parse_args()
    return run(args.ff, args.zone_name, args.asset)


if __name__ == "__main__":
    raise SystemExit(main())
