#!/usr/bin/env python3
"""
Compare a surviving donor-clone XAnimParts payload against locally emitted payloads.

This is a diagnostics tool for the BO3->T6 xanim lane. The donor-clone path has
proven that:

  1. loading mod_load.ff works
  2. binding an alias like vm_zod_id_gun_idle can work
  3. the native AV only happens on our custom emitted XAnimParts payloads

So the useful next step is to compare the exact binary contract we emit against a
known-good payload that survives under the same alias.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
from pathlib import Path

import compile_xanim_zone as cxz  # type: ignore
import strict_xanim_parser as strict_xanim  # type: ignore
from patch_zone_xanims import decrypt_zone, parse_string_table  # type: ignore


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DONOR_FF = ROOT / "zone_dump" / "raw_test" / "mod_load.ff"
DEFAULT_DONOR_ZONE = "mod_load"


def read_indexed_strings(data: bytes, count: int, string_data_start: int) -> list[str]:
    out: list[str] = []
    pos = string_data_start
    for _ in range(int(count)):
        end = data.index(b"\x00", pos)
        out.append(data[pos:end].decode("ascii", errors="replace"))
        pos = end + 1
    return out


def parse_header(header_bytes: bytes) -> dict[str, object]:
    return {
        "dataByteCount": struct.unpack_from("<H", header_bytes, 0x04)[0],
        "dataShortCount": struct.unpack_from("<H", header_bytes, 0x06)[0],
        "dataIntCount": struct.unpack_from("<H", header_bytes, 0x08)[0],
        "randomDataByteCount": struct.unpack_from("<H", header_bytes, 0x0A)[0],
        "randomDataIntCount": struct.unpack_from("<H", header_bytes, 0x0C)[0],
        "numframes": struct.unpack_from("<H", header_bytes, 0x0E)[0],
        "flags": {
            "bLoop": header_bytes[0x10],
            "bDelta": header_bytes[0x11],
            "bDelta3D": header_bytes[0x12],
            "bLeftHandGripIK": header_bytes[0x13],
            "assetType": header_bytes[0x23],
            "isDefault": header_bytes[0x24],
        },
        "boneCount": list(header_bytes[0x18:0x22]),
        "notifyCount": header_bytes[0x22],
        "randomDataShortCount": struct.unpack_from("<I", header_bytes, 0x28)[0],
        "indexCount": struct.unpack_from("<I", header_bytes, 0x2C)[0],
        "framerate": struct.unpack_from("<f", header_bytes, 0x30)[0],
        "frequency": struct.unpack_from("<f", header_bytes, 0x34)[0],
        "primedLength": struct.unpack_from("<f", header_bytes, 0x38)[0],
        "loopEntryTime": struct.unpack_from("<f", header_bytes, 0x3C)[0],
        "pointers": {
            "name": struct.unpack_from("<I", header_bytes, 0x00)[0],
            "names": struct.unpack_from("<I", header_bytes, 0x40)[0],
            "dataByte": struct.unpack_from("<I", header_bytes, 0x44)[0],
            "dataShort": struct.unpack_from("<I", header_bytes, 0x48)[0],
            "dataInt": struct.unpack_from("<I", header_bytes, 0x4C)[0],
            "randomDataShort": struct.unpack_from("<I", header_bytes, 0x50)[0],
            "randomDataByte": struct.unpack_from("<I", header_bytes, 0x54)[0],
            "randomDataInt": struct.unpack_from("<I", header_bytes, 0x58)[0],
            "indices": struct.unpack_from("<I", header_bytes, 0x5C)[0],
            "notify": struct.unpack_from("<I", header_bytes, 0x60)[0],
            "deltaPart": struct.unpack_from("<I", header_bytes, 0x64)[0],
        },
    }


def find_payload(ff_path: Path, zone_name: str, asset_name: str) -> dict[str, object]:
    _, raw = decrypt_zone(str(ff_path), zone_name)
    result = parse_string_table(raw)
    asset_data_offset = result[3]
    string_count = result[1]
    string_data_start = result[5]
    index_to_string = read_indexed_strings(raw, string_count, string_data_start)
    matches = strict_xanim.find_xanim_by_name(raw, asset_name, min_offset=asset_data_offset)
    if not matches:
        raise RuntimeError(f"xanim asset not found: {asset_name} in {ff_path}")
    parsed = matches[0]
    return {
        "raw": raw,
        "parsed": parsed,
        "index_to_string": index_to_string,
    }


def summarize_sections(parsed: dict[str, object]) -> dict[str, object]:
    sections = {}
    for key, meta in (parsed.get("sections") or {}).items():
        sections[str(key)] = {
            "offset": int(meta["offset"]),
            "size": int(meta["size"]),
        }
    return sections


def compare_dicts(a: dict[str, object], b: dict[str, object]) -> dict[str, object]:
    keys = sorted(set(a) | set(b))
    out = {}
    for key in keys:
        av = a.get(key)
        bv = b.get(key)
        if av != bv:
            out[key] = {"donor": av, "emitted": bv}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare donor-clone vs emitted XAnimParts contracts")
    ap.add_argument("--donor-ff", default=str(DEFAULT_DONOR_FF))
    ap.add_argument("--donor-zone", default=DEFAULT_DONOR_ZONE)
    ap.add_argument("--donor-asset", required=True)
    ap.add_argument("--source-export", required=True, help="xanim_export source to emit from")
    ap.add_argument("--target-name", required=True)
    ap.add_argument(
        "--emit-mode",
        choices=["static_pose", "bo3_frames", "donor_clone", "donor_template_static_pose", "donor_semantic_static_pose"],
        default="static_pose",
    )
    ap.add_argument("--keep-bones-file")
    ap.add_argument("--bo3-frames-target", action="append", default=[])
    ap.add_argument("--bo3-fallback-mode", choices=["donor_clone", "static_pose", "stub"], default="donor_clone")
    ap.add_argument("--out-json")
    args = ap.parse_args()

    donor = find_payload(Path(args.donor_ff), args.donor_zone, args.donor_asset)
    donor_parsed = donor["parsed"]
    donor_header_off = donor_parsed["header_offset"]
    donor_header_bytes = donor["raw"][donor_header_off: donor_header_off + 104]

    anim = cxz.parse_xanim_export(args.source_export)
    anim["name"] = args.target_name

    removed_tracks = 0
    if args.keep_bones_file:
        keep = cxz.load_keep_bones_from_file(args.keep_bones_file)
        removed_tracks = cxz.prune_anim_to_bones(anim, keep)

    string_table = {}

    if args.emit_mode == "donor_clone":
        cxz.DONOR_FF = args.donor_ff
        cxz.DONOR_ZONE_NAME = args.donor_zone
        cxz.DONOR_DEFAULT_ASSET = args.donor_asset
        cxz.DONOR_OVERRIDE_MAP = {args.target_name: args.donor_asset}
        cxz.DONOR_CONTEXT = cxz._load_donor_context(args.donor_ff, args.donor_zone, [args.donor_asset])
        emitted_header_bytes, emitted_data = cxz._build_donor_clone_xanimparts_data(anim, string_table)
    elif args.emit_mode == "donor_template_static_pose":
        cxz.DONOR_FF = args.donor_ff
        cxz.DONOR_ZONE_NAME = args.donor_zone
        cxz.DONOR_DEFAULT_ASSET = args.donor_asset
        cxz.DONOR_OVERRIDE_MAP = {args.target_name: args.donor_asset}
        cxz.DONOR_CONTEXT = cxz._load_donor_context(args.donor_ff, args.donor_zone, [args.donor_asset])
        emitted_header_bytes, emitted_data = cxz._build_donor_template_static_pose_xanimparts_data(anim, string_table)
    elif args.emit_mode == "donor_semantic_static_pose":
        cxz.DONOR_FF = args.donor_ff
        cxz.DONOR_ZONE_NAME = args.donor_zone
        cxz.DONOR_DEFAULT_ASSET = args.donor_asset
        cxz.DONOR_OVERRIDE_MAP = {args.target_name: args.donor_asset}
        cxz.DONOR_CONTEXT = cxz._load_donor_context(args.donor_ff, args.donor_zone, [args.donor_asset])
        emitted_header_bytes, emitted_data = cxz._build_donor_semantic_static_pose_xanimparts_data(anim, string_table)
    elif args.emit_mode == "bo3_frames":
        cxz.BO3_FRAMES_TARGETS = set(str(x).strip() for x in (args.bo3_frames_target or []) if str(x).strip())
        cxz.BO3_FRAMES_FALLBACK_MODE = str(args.bo3_fallback_mode).strip()
        if cxz.BO3_FRAMES_FALLBACK_MODE == "donor_clone":
            cxz.DONOR_FF = args.donor_ff
            cxz.DONOR_ZONE_NAME = args.donor_zone
            cxz.DONOR_DEFAULT_ASSET = args.donor_asset
            cxz.DONOR_OVERRIDE_MAP = {args.target_name: args.donor_asset}
            cxz.DONOR_CONTEXT = cxz._load_donor_context(args.donor_ff, args.donor_zone, [args.donor_asset])
        emitted_header_bytes, emitted_data = cxz._build_bo3_frames_xanimparts_data(anim, string_table)
    else:
        emitted_header_bytes, emitted_data = cxz._build_static_pose_xanimparts_data(anim, string_table)

    report = {
        "donor_asset": args.donor_asset,
        "target_name": args.target_name,
        "emit_mode": args.emit_mode,
        "removed_tracks": removed_tracks,
        "bo3_frames_target": list(args.bo3_frames_target),
        "bo3_fallback_mode": args.bo3_fallback_mode,
        "donor_header": parse_header(donor_header_bytes),
        "emitted_header": parse_header(emitted_header_bytes),
        "header_diff": compare_dicts(parse_header(donor_header_bytes), parse_header(emitted_header_bytes)),
        "donor_sections": summarize_sections(donor_parsed),
        "emitted_payload": {
            "data_size": len(emitted_data),
            "string_table_size": len(string_table),
        },
        "emitted_string_table_preview": list(string_table.items())[:16],
    }

    if args.out_json:
        out_path = Path(args.out_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {out_path}")
    else:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
