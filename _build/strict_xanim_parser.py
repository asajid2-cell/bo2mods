#!/usr/bin/env python3
"""
Strict pointer-walk parser for serialized T6 XAnimParts blobs.

Purpose:
- Stop relying on broad "header-like" heuristics.
- Validate and extract exact XAnimParts byte ranges by actually walking
  the serialized pointer-follow order (including deltaPart substructures).

Notes:
- This parser operates on decrypted fastfile stream bytes.
- It expects serialized pointer markers (PTR_FOLLOWING / PTR_NULL).
- For ambiguous delta frame element sizing (UShortVec), it supports
  multiple parse variants and picks the first valid one.
"""

import argparse
import json
import os
import struct
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(__file__))
from patch_zone_xanims import decrypt_zone, parse_string_table  # noqa: E402


PTR_NULL = 0x00000000
PTR_FOLLOWING = 0xFFFFFFFF
XANIM_HEADER_SIZE = 104


class ParseError(Exception):
    """Raised when a strict parse walk fails."""


def _ensure(data: bytes, pos: int, n: int, what: str) -> None:
    if pos < 0 or pos + n > len(data):
        raise ParseError(f"out of bounds while reading {what} @0x{pos:X} (+{n})")


def _align(pos: int, alignment: int) -> int:
    if alignment <= 1:
        return pos
    return (pos + (alignment - 1)) & ~(alignment - 1)


def _align_rel(pos: int, base: int, alignment: int) -> int:
    """Align `pos` to `alignment` using a relative origin `base`."""
    rel = pos - base
    rel_aligned = _align(rel, alignment)
    return base + rel_aligned


def _read_cstr(data: bytes, pos: int, what: str) -> Tuple[str, int]:
    try:
        end = data.index(b"\x00", pos)
    except ValueError as exc:
        raise ParseError(f"missing null terminator for {what} @0x{pos:X}") from exc
    raw = data[pos:end]
    try:
        text = raw.decode("ascii", errors="replace")
    except Exception as exc:
        raise ParseError(f"failed decoding {what} @0x{pos:X}") from exc
    return text, end + 1


def parse_xanim_header(data: bytes, off: int) -> Dict:
    _ensure(data, off, XANIM_HEADER_SIZE, "XAnimParts header")
    h = data[off:off + XANIM_HEADER_SIZE]

    header = {
        "offset": off,
        "name_ptr": struct.unpack_from("<I", h, 0x00)[0],
        "dataByteCount": struct.unpack_from("<H", h, 0x04)[0],
        "dataShortCount": struct.unpack_from("<H", h, 0x06)[0],
        "dataIntCount": struct.unpack_from("<H", h, 0x08)[0],
        "randomDataByteCount": struct.unpack_from("<H", h, 0x0A)[0],
        "randomDataIntCount": struct.unpack_from("<H", h, 0x0C)[0],
        "numframes": struct.unpack_from("<H", h, 0x0E)[0],
        "bLoop": h[0x10],
        "bDelta": h[0x11],
        "bDelta3D": h[0x12],
        "bLeftHandGripIK": h[0x13],
        "streamedFileSize": struct.unpack_from("<I", h, 0x14)[0],
        "boneCount": [h[0x18 + i] for i in range(10)],
        "notifyCount": h[0x22],
        "assetType": struct.unpack_from("<b", h, 0x23)[0],
        "isDefault": h[0x24],
        "randomDataShortCount": struct.unpack_from("<I", h, 0x28)[0],
        "indexCount": struct.unpack_from("<I", h, 0x2C)[0],
        "framerate": struct.unpack_from("<f", h, 0x30)[0],
        "frequency": struct.unpack_from("<f", h, 0x34)[0],
        "primedLength": struct.unpack_from("<f", h, 0x38)[0],
        "loopEntryTime": struct.unpack_from("<f", h, 0x3C)[0],
        "names_ptr": struct.unpack_from("<I", h, 0x40)[0],
        "dataByte_ptr": struct.unpack_from("<I", h, 0x44)[0],
        "dataShort_ptr": struct.unpack_from("<I", h, 0x48)[0],
        "dataInt_ptr": struct.unpack_from("<I", h, 0x4C)[0],
        "randomDataShort_ptr": struct.unpack_from("<I", h, 0x50)[0],
        "randomDataByte_ptr": struct.unpack_from("<I", h, 0x54)[0],
        "randomDataInt_ptr": struct.unpack_from("<I", h, 0x58)[0],
        "indices_ptr": struct.unpack_from("<I", h, 0x5C)[0],
        "notify_ptr": struct.unpack_from("<I", h, 0x60)[0],
        "deltaPart_ptr": struct.unpack_from("<I", h, 0x64)[0],
    }
    return header


def _consume(pos: int, size: int, data_len: int, what: str) -> int:
    if size < 0:
        raise ParseError(f"negative consume for {what}")
    if pos + size > data_len:
        raise ParseError(f"overflow consuming {what}: @0x{pos:X} +{size}")
    return pos + size


def _parse_delta_part_trans(
    data: bytes,
    pos: int,
    parent_numframes: int,
    align_mode: str,
    ushortvec_size: int,
    align_base: int,
) -> Tuple[int, Dict]:
    _ensure(data, pos, 4, "XAnimPartTrans preamble")
    size = struct.unpack_from("<H", data, pos)[0]
    small_trans = struct.unpack_from("<b", data, pos + 2)[0]

    # In-memory layout (x86):
    # uint16 size, char smallTrans, pad, union at +4
    # union size = max(sizeof(XAnimPartTransFrames)=32, sizeof(vec3)=12)
    # => sizeof(XAnimPartTrans) = 36 when serialized as struct bytes.
    # For size == 0 (single frame), effective payload still includes union.
    struct_size = 36 if size > 0 else 16
    _ensure(data, pos, struct_size, "XAnimPartTrans")
    cur = pos + struct_size

    info = {
        "offset": pos,
        "size": size,
        "smallTrans": small_trans,
        "struct_size": struct_size,
        "indices_bytes": 0,
        "frames_bytes": 0,
    }

    if size > 0:
        count = size + 1
        idx_elem = 1 if parent_numframes < 256 else 2
        if align_mode == "standard":
            cur = _align_rel(cur, align_base, idx_elem)
        idx_bytes = count * idx_elem
        cur = _consume(cur, idx_bytes, len(data), "XAnimPartTransFrames.indices")
        info["indices_bytes"] = idx_bytes

        if small_trans:
            frame_elem = 3  # ByteVec[3]
        else:
            # UShortVec[3] can be observed as 6 bytes payload; some compilers pad to 8.
            frame_elem = ushortvec_size
        frame_bytes = count * frame_elem
        cur = _consume(cur, frame_bytes, len(data), "XAnimPartTransFrames.frames")
        info["frames_bytes"] = frame_bytes

    return cur, info


def _parse_delta_part_quat2(
    data: bytes,
    pos: int,
    parent_numframes: int,
    align_mode: str,
    align_base: int,
) -> Tuple[int, Dict]:
    _ensure(data, pos, 4, "XAnimDeltaPartQuat2 preamble")
    size = struct.unpack_from("<H", data, pos)[0]

    # uint16 size, pad2, union(8) => 12
    struct_size = 12
    _ensure(data, pos, struct_size, "XAnimDeltaPartQuat2")
    cur = pos + struct_size
    info = {
        "offset": pos,
        "size": size,
        "struct_size": struct_size,
        "indices_bytes": 0,
        "frames_bytes": 0,
    }

    if size > 0:
        count = size + 1
        idx_elem = 1 if parent_numframes < 256 else 2
        if align_mode == "standard":
            cur = _align_rel(cur, align_base, idx_elem)
        idx_bytes = count * idx_elem
        cur = _consume(cur, idx_bytes, len(data), "XAnimDeltaPartQuatDataFrames2.indices")
        frame_bytes = count * 4  # XQuat2 (2 x int16)
        cur = _consume(cur, frame_bytes, len(data), "XAnimDeltaPartQuatDataFrames2.frames")
        info["indices_bytes"] = idx_bytes
        info["frames_bytes"] = frame_bytes

    return cur, info


def _parse_delta_part_quat(
    data: bytes,
    pos: int,
    parent_numframes: int,
    align_mode: str,
    align_base: int,
) -> Tuple[int, Dict]:
    _ensure(data, pos, 4, "XAnimDeltaPartQuat preamble")
    size = struct.unpack_from("<H", data, pos)[0]

    # uint16 size, pad2, union(8) => 12
    struct_size = 12
    _ensure(data, pos, struct_size, "XAnimDeltaPartQuat")
    cur = pos + struct_size
    info = {
        "offset": pos,
        "size": size,
        "struct_size": struct_size,
        "indices_bytes": 0,
        "frames_bytes": 0,
    }

    if size > 0:
        count = size + 1
        idx_elem = 1 if parent_numframes < 256 else 2
        if align_mode == "standard":
            cur = _align_rel(cur, align_base, idx_elem)
        idx_bytes = count * idx_elem
        cur = _consume(cur, idx_bytes, len(data), "XAnimDeltaPartQuatDataFrames.indices")
        frame_bytes = count * 8  # XQuat (4 x int16)
        cur = _consume(cur, frame_bytes, len(data), "XAnimDeltaPartQuatDataFrames.frames")
        info["indices_bytes"] = idx_bytes
        info["frames_bytes"] = frame_bytes

    return cur, info


def _parse_delta_part(
    data: bytes,
    pos: int,
    header: Dict,
    align_mode: str,
    ushortvec_size: int,
    align_base: int,
) -> Tuple[int, Dict]:
    _ensure(data, pos, 12, "XAnimDeltaPart")
    trans_ptr = struct.unpack_from("<I", data, pos + 0)[0]
    quat2_ptr = struct.unpack_from("<I", data, pos + 4)[0]
    quat_ptr = struct.unpack_from("<I", data, pos + 8)[0]
    cur = pos + 12

    info = {
        "offset": pos,
        "trans_ptr": trans_ptr,
        "quat2_ptr": quat2_ptr,
        "quat_ptr": quat_ptr,
        "trans": None,
        "quat2": None,
        "quat": None,
    }

    for label, ptr_val in (("trans", trans_ptr), ("quat2", quat2_ptr), ("quat", quat_ptr)):
        if ptr_val not in (PTR_NULL, PTR_FOLLOWING):
            raise ParseError(f"deltaPart.{label} ptr not null/following: 0x{ptr_val:08X}")

    if trans_ptr == PTR_FOLLOWING:
        cur, t_info = _parse_delta_part_trans(
            data, cur, header["numframes"], align_mode, ushortvec_size, align_base
        )
        info["trans"] = t_info
    if quat2_ptr == PTR_FOLLOWING:
        cur, q2_info = _parse_delta_part_quat2(
            data, cur, header["numframes"], align_mode, align_base
        )
        info["quat2"] = q2_info
    if quat_ptr == PTR_FOLLOWING:
        cur, q_info = _parse_delta_part_quat(
            data, cur, header["numframes"], align_mode, align_base
        )
        info["quat"] = q_info

    return cur, info


def parse_xanim_blob(
    data: bytes,
    header_off: int,
    align_mode: str = "none",
    ushortvec_size: int = 6,
) -> Dict:
    header = parse_xanim_header(data, header_off)
    stream_base = header_off + XANIM_HEADER_SIZE
    cur = stream_base

    if header["name_ptr"] != PTR_FOLLOWING:
        raise ParseError(f"name ptr is not PTR_FOLLOWING @0x{header_off:X}")
    raw_name, cur = _read_cstr(data, cur, "XAnimParts.name")

    # Keep raw + normalized view for callers.
    norm_name = raw_name.lstrip(",")

    sections = {
        "name": {
            "offset": header_off + XANIM_HEADER_SIZE,
            "raw": raw_name,
            "normalized": norm_name,
            "size": len(raw_name.encode("ascii", errors="replace")) + 1,
        }
    }

    total_bones = header["boneCount"][9]

    # names: scriptstring uint16[boneCount[9]]
    if header["names_ptr"] == PTR_FOLLOWING:
        if align_mode == "standard":
            cur = _align_rel(cur, stream_base, 2)
        names_bytes = total_bones * 2
        names_off = cur
        cur = _consume(cur, names_bytes, len(data), "names")
        sections["names"] = {"offset": names_off, "size": names_bytes, "count": total_bones}
    elif header["names_ptr"] != PTR_NULL:
        raise ParseError(f"names ptr not null/following: 0x{header['names_ptr']:08X}")

    # notify: XAnimNotifyInfo[notifyCount] (8 bytes each)
    if header["notify_ptr"] == PTR_FOLLOWING:
        if align_mode == "standard":
            cur = _align_rel(cur, stream_base, 4)
        notify_bytes = header["notifyCount"] * 8
        notify_off = cur
        cur = _consume(cur, notify_bytes, len(data), "notify")
        sections["notify"] = {
            "offset": notify_off,
            "size": notify_bytes,
            "count": header["notifyCount"],
        }
    elif header["notify_ptr"] != PTR_NULL:
        raise ParseError(f"notify ptr not null/following: 0x{header['notify_ptr']:08X}")

    # deltaPart
    if header["deltaPart_ptr"] == PTR_FOLLOWING:
        if align_mode == "standard":
            cur = _align_rel(cur, stream_base, 4)
        d_off = cur
        cur, d_info = _parse_delta_part(
            data,
            cur,
            header,
            align_mode,
            ushortvec_size,
            stream_base,
        )
        sections["deltaPart"] = {"offset": d_off, "size": cur - d_off, "detail": d_info}
    elif header["deltaPart_ptr"] != PTR_NULL:
        raise ParseError(f"deltaPart ptr not null/following: 0x{header['deltaPart_ptr']:08X}")

    # dataByte
    if header["dataByte_ptr"] == PTR_FOLLOWING:
        db_off = cur
        cur = _consume(cur, header["dataByteCount"], len(data), "dataByte")
        sections["dataByte"] = {"offset": db_off, "size": header["dataByteCount"]}
    elif header["dataByte_ptr"] != PTR_NULL:
        raise ParseError(f"dataByte ptr not null/following: 0x{header['dataByte_ptr']:08X}")

    # dataShort
    if header["dataShort_ptr"] == PTR_FOLLOWING:
        if align_mode == "standard":
            cur = _align_rel(cur, stream_base, 2)
        ds_off = cur
        ds_bytes = header["dataShortCount"] * 2
        cur = _consume(cur, ds_bytes, len(data), "dataShort")
        sections["dataShort"] = {"offset": ds_off, "size": ds_bytes, "count": header["dataShortCount"]}
    elif header["dataShort_ptr"] != PTR_NULL:
        raise ParseError(f"dataShort ptr not null/following: 0x{header['dataShort_ptr']:08X}")

    # dataInt
    if header["dataInt_ptr"] == PTR_FOLLOWING:
        if align_mode == "standard":
            cur = _align_rel(cur, stream_base, 4)
        di_off = cur
        di_bytes = header["dataIntCount"] * 4
        cur = _consume(cur, di_bytes, len(data), "dataInt")
        sections["dataInt"] = {"offset": di_off, "size": di_bytes, "count": header["dataIntCount"]}
    elif header["dataInt_ptr"] != PTR_NULL:
        raise ParseError(f"dataInt ptr not null/following: 0x{header['dataInt_ptr']:08X}")

    # randomDataShort
    if header["randomDataShort_ptr"] == PTR_FOLLOWING:
        if align_mode == "standard":
            cur = _align_rel(cur, stream_base, 2)
        rs_off = cur
        rs_bytes = header["randomDataShortCount"] * 2
        cur = _consume(cur, rs_bytes, len(data), "randomDataShort")
        sections["randomDataShort"] = {
            "offset": rs_off,
            "size": rs_bytes,
            "count": header["randomDataShortCount"],
        }
    elif header["randomDataShort_ptr"] != PTR_NULL:
        raise ParseError(f"randomDataShort ptr not null/following: 0x{header['randomDataShort_ptr']:08X}")

    # randomDataByte
    if header["randomDataByte_ptr"] == PTR_FOLLOWING:
        rb_off = cur
        cur = _consume(cur, header["randomDataByteCount"], len(data), "randomDataByte")
        sections["randomDataByte"] = {"offset": rb_off, "size": header["randomDataByteCount"]}
    elif header["randomDataByte_ptr"] != PTR_NULL:
        raise ParseError(f"randomDataByte ptr not null/following: 0x{header['randomDataByte_ptr']:08X}")

    # randomDataInt
    if header["randomDataInt_ptr"] == PTR_FOLLOWING:
        if align_mode == "standard":
            cur = _align_rel(cur, stream_base, 4)
        ri_off = cur
        ri_bytes = header["randomDataIntCount"] * 4
        cur = _consume(cur, ri_bytes, len(data), "randomDataInt")
        sections["randomDataInt"] = {
            "offset": ri_off,
            "size": ri_bytes,
            "count": header["randomDataIntCount"],
        }
    elif header["randomDataInt_ptr"] != PTR_NULL:
        raise ParseError(f"randomDataInt ptr not null/following: 0x{header['randomDataInt_ptr']:08X}")

    # indices
    if header["indices_ptr"] == PTR_FOLLOWING:
        idx_elem = 1 if header["numframes"] < 256 else 2
        if align_mode == "standard":
            cur = _align_rel(cur, stream_base, idx_elem)
        idx_off = cur
        idx_bytes = header["indexCount"] * idx_elem
        cur = _consume(cur, idx_bytes, len(data), "indices")
        sections["indices"] = {
            "offset": idx_off,
            "size": idx_bytes,
            "count": header["indexCount"],
            "elem_size": idx_elem,
        }
    elif header["indices_ptr"] != PTR_NULL:
        raise ParseError(f"indices ptr not null/following: 0x{header['indices_ptr']:08X}")

    return {
        "header_offset": header_off,
        "end_offset": cur,
        "total_size": cur - header_off,
        "name": raw_name,
        "name_normalized": norm_name,
        "header": header,
        "sections": sections,
        "options": {"align_mode": align_mode, "ushortvec_size": ushortvec_size},
    }


def parse_xanim_blob_auto(data: bytes, header_off: int) -> Dict:
    attempts: List[Tuple[str, int]] = [
        ("none", 6),
        ("none", 8),
        ("standard", 6),
        ("standard", 8),
    ]
    errors: List[str] = []
    for align_mode, ushortvec_size in attempts:
        try:
            return parse_xanim_blob(
                data,
                header_off,
                align_mode=align_mode,
                ushortvec_size=ushortvec_size,
            )
        except ParseError as exc:
            errors.append(f"{align_mode}/ushortvec={ushortvec_size}: {exc}")
    raise ParseError("all parse variants failed:\n  " + "\n  ".join(errors))


def _find_occurrences(haystack: bytes, needle: bytes) -> List[int]:
    out = []
    pos = 0
    while True:
        i = haystack.find(needle, pos)
        if i < 0:
            return out
        out.append(i)
        pos = i + 1


def find_xanim_by_name(
    data: bytes,
    name: str,
    min_offset: int = 0,
    max_gap: int = 8,
) -> List[Dict]:
    # Search for exact "name\\0" occurrences and validate backward candidates.
    hits = _find_occurrences(data, name.encode("ascii") + b"\x00")
    results = []
    seen = set()

    for name_off in hits:
        for gap in range(max_gap + 1):
            header_off = name_off - XANIM_HEADER_SIZE - gap
            if header_off < min_offset or header_off in seen:
                continue
            seen.add(header_off)
            try:
                h = parse_xanim_header(data, header_off)
            except ParseError:
                continue
            if h["name_ptr"] != PTR_FOLLOWING:
                continue
            try:
                parsed = parse_xanim_blob_auto(data, header_off)
            except ParseError:
                continue
            if parsed["name_normalized"] != name:
                continue
            results.append(parsed)

    return sorted(results, key=lambda r: r["header_offset"])


def print_summary(parsed: Dict) -> None:
    h = parsed["header"]
    print("=" * 72)
    print(f"name:         {parsed['name']}  (normalized={parsed['name_normalized']})")
    print(f"header:       0x{parsed['header_offset']:X}")
    print(f"end:          0x{parsed['end_offset']:X}")
    print(f"total bytes:  {parsed['total_size']}")
    print(f"mode:         align={parsed['options']['align_mode']}, "
          f"ushortvec={parsed['options']['ushortvec_size']}")
    print("-" * 72)
    print(f"numframes={h['numframes']}  boneCount={h['boneCount']}  "
          f"notifyCount={h['notifyCount']}  indexCount={h['indexCount']}")
    print(f"counts: dataByte={h['dataByteCount']} dataShort={h['dataShortCount']} "
          f"dataInt={h['dataIntCount']} randShort={h['randomDataShortCount']} "
          f"randByte={h['randomDataByteCount']} randInt={h['randomDataIntCount']}")
    print(f"flags: bLoop={h['bLoop']} bDelta={h['bDelta']} bDelta3D={h['bDelta3D']} "
          f"assetType={h['assetType']} isDefault={h['isDefault']}")
    print("sections:")
    for key, val in parsed["sections"].items():
        off = val.get("offset", 0)
        size = val.get("size", 0)
        print(f"  {key:14s} @0x{off:08X}  size={size}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Strict pointer-walk parser for T6 XAnimParts blobs.")
    ap.add_argument("--ff", required=True, help="Input fastfile path.")
    ap.add_argument("--zone-name", required=True, help="Zone name for decryption hash chain.")
    ap.add_argument("--offset", default=None, help="XAnimParts header offset (hex or dec).")
    ap.add_argument("--name", default=None, help="Find and parse asset by exact animation name.")
    ap.add_argument("--min-offset", default=None, help="Minimum offset for name search.")
    ap.add_argument("--extract", default=None, help="Write parsed blob bytes to this output path.")
    ap.add_argument("--json", default=None, help="Write parsed metadata JSON to this path.")
    args = ap.parse_args()

    if not args.offset and not args.name:
        print("ERROR: provide --offset or --name")
        return 2

    print(f"Decrypting: {args.ff}")
    _, data = decrypt_zone(args.ff, args.zone_name)
    print(f"  decrypted bytes: {len(data):,}")

    # Use parsed asset_data_offset as practical minimum search floor.
    parsed_list = parse_string_table(data)
    asset_data_offset = parsed_list[3]
    min_off = asset_data_offset
    if args.min_offset:
        min_off = int(args.min_offset, 0)

    parsed: Optional[Dict] = None

    if args.offset:
        off = int(args.offset, 0)
        parsed = parse_xanim_blob_auto(data, off)
    else:
        matches = find_xanim_by_name(data, args.name, min_offset=min_off)
        if not matches:
            print(f"ERROR: no strict-parse matches for '{args.name}'")
            return 3
        if len(matches) > 1:
            print(f"WARNING: multiple matches for '{args.name}', using first:")
            for m in matches:
                print(f"  0x{m['header_offset']:X} size={m['total_size']} name={m['name']}")
        parsed = matches[0]

    print_summary(parsed)

    if args.extract:
        out_path = args.extract
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        blob = data[parsed["header_offset"]:parsed["end_offset"]]
        with open(out_path, "wb") as f:
            f.write(blob)
        print(f"wrote blob: {out_path} ({len(blob):,} bytes)")

    if args.json:
        out_json = args.json
        os.makedirs(os.path.dirname(out_json), exist_ok=True)
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2)
        print(f"wrote json: {out_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
