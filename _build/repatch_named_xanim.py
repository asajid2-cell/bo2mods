#!/usr/bin/env python3
"""
Rewrite an existing XAnimParts asset in a T6 fastfile by name.

Use-case:
- Existing FF already has vm_thunder_gun_idle (no empty stubs left).
- Need to swap that one payload with a regenerated blob from xanim_export,
  while updating XFile totalSize/VIRTUAL when replacement size differs.
"""

import argparse
import os
import struct

import patch_zone_xanims as pz
import strict_xanim_parser as sx


def build_replacement_blob(target_name, xanim_dir, pattern, string_table):
    anims = {}
    for fp in sorted(pz.glob.glob(os.path.join(xanim_dir, pattern))):
        anim = pz.parse_xanim_export(fp)
        anims[anim["name"]] = anim
    if target_name not in anims:
        raise RuntimeError(f"Animation '{target_name}' not found in {xanim_dir}\\{pattern}")

    # gap_bytes is irrelevant for generated names (comma artifact removed).
    return pz.build_replacement_data(
        anims[target_name],
        string_table,
        b"",
        target_name=target_name,
    )


def main():
    ap = argparse.ArgumentParser(description="Repatch one named XAnimParts payload in-place.")
    ap.add_argument("--input-ff", required=True)
    ap.add_argument("--output-ff", required=True)
    ap.add_argument("--zone-name", required=True)
    ap.add_argument("--xanim-dir", required=True)
    ap.add_argument("--xanim-pattern", default="vm_thunder_gun_*.xanim_export")
    ap.add_argument("--xanim-name", required=True)
    args = ap.parse_args()

    magic, raw = pz.decrypt_zone(args.input_ff, args.zone_name)
    (string_table, _string_count, _asset_count, asset_data_offset,
     _ptr_array_start, _string_data_start, _string_data_end) = pz.parse_string_table(raw)

    matches = sx.find_xanim_by_name(raw, args.xanim_name, min_offset=asset_data_offset)
    if not matches:
        raise RuntimeError(f"XAnim '{args.xanim_name}' not found in candidate ff")
    parsed = matches[0]
    old_start = parsed["header_offset"]
    old_end = parsed["end_offset"]
    old_size = old_end - old_start

    replacement = build_replacement_blob(
        target_name=args.xanim_name,
        xanim_dir=args.xanim_dir,
        pattern=args.xanim_pattern,
        string_table=string_table,
    )
    new_size = len(replacement)
    delta = new_size - old_size

    patched = bytearray(raw)
    patched[old_start:old_end] = replacement

    if delta != 0:
        old_total = struct.unpack_from("<I", patched, 0)[0]
        struct.pack_into("<I", patched, 0, old_total + delta)

        # VIRTUAL block tracks pointer-following payload stream footprint.
        virtual_off = 8 + (pz.BLOCK_VIRTUAL * 4)
        old_virtual = struct.unpack_from("<I", patched, virtual_off)[0]
        struct.pack_into("<I", patched, virtual_off, old_virtual + delta)
        print(f"Updated XFile header totalSize {old_total} -> {old_total + delta}")
        print(f"Updated XFile header VIRTUAL  {old_virtual} -> {old_virtual + delta}")

    out_size = pz.write_patched_zone(bytes(patched), args.zone_name, magic, args.output_ff)

    # Verify replacement exists and parseable.
    _, out_raw = pz.decrypt_zone(args.output_ff, args.zone_name)
    out_matches = sx.find_xanim_by_name(out_raw, args.xanim_name, min_offset=asset_data_offset)
    if not out_matches:
        raise RuntimeError("Post-write verification failed: named xanim missing")

    h = out_matches[0]["header"]
    print(f"Repatched '{args.xanim_name}': {old_size} -> {new_size} bytes (delta {delta:+d})")
    print(
        f"Header: numframes={h['numframes']} bones={h['boneCount'][9]} "
        f"db/ds/di={h['dataByteCount']}/{h['dataShortCount']}/{h['dataIntCount']} "
        f"deltaPtr=0x{h['deltaPart_ptr']:X}"
    )
    print(f"Wrote: {args.output_ff} ({out_size:,} bytes)")


if __name__ == "__main__":
    raise SystemExit(main())

