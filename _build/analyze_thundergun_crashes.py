#!/usr/bin/env python3
"""Summarize recent T6 crash dumps and current thundergun anim profile."""

import glob
import math
import os
import re
import struct
from typing import Dict, List, Optional, Tuple

import patch_zone_xanims as patch

ZONE_NAME = "so_zsurvival_zm_transit"
CUSTOM_XANIM_ZONE_NAME = os.environ.get("ROGUE_TG_ANALYZE_XANIM_ZONE", "")

DEFAULT_CRASH_GLOB = os.path.expandvars(
    r"%LOCALAPPDATA%\Plutonium\crashdumps\plutonium-r5246-t6zm-*.txt"
)
DEFAULT_FF = r"z:\Games\pluto_t6_full_game\zone\all\so_zsurvival_zm_transit.ff"
_CUSTOM_XANIM_CANDIDATES = [
    os.path.expandvars(
        r"%LOCALAPPDATA%\Plutonium\storage\t6\mods\zm_roguelike_panzer\zone\all\mod_load.ff"
    ),
    r"z:\Games\pluto_t6_full_game\_build\panzer_work\output\mod_load.ff",
    r"z:\Games\pluto_t6_full_game\_build\panzer_work\output\thundergun_xanims.ff",
]
DEFAULT_CUSTOM_XANIM_FF = os.environ.get("ROGUE_TG_ANALYZE_XANIM_FF", "")
if not DEFAULT_CUSTOM_XANIM_FF:
    DEFAULT_CUSTOM_XANIM_FF = next((p for p in _CUSTOM_XANIM_CANDIDATES if os.path.exists(p)), "")
if not CUSTOM_XANIM_ZONE_NAME:
    if DEFAULT_CUSTOM_XANIM_FF:
        CUSTOM_XANIM_ZONE_NAME = os.path.splitext(os.path.basename(DEFAULT_CUSTOM_XANIM_FF))[0]
    else:
        CUSTOM_XANIM_ZONE_NAME = os.environ.get("ROGUE_TG_XANIM_ZONE", "thundergun_xanims")
DEFAULT_WEAPON_ALIAS = os.environ.get("ROGUE_TG_TRUTH_ALIAS", "ak74u_zm")
DEFAULT_WEAPON = os.path.join(
    r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\weapons",
    DEFAULT_WEAPON_ALIAS,
)
DEFAULT_XANIM_DIR = (
    r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\xanim_export"
)
DEFAULT_GAMES_LOG = os.path.expandvars(
    r"%LOCALAPPDATA%\Plutonium\storage\t6\mods\zm_roguelike_panzer\games_mp.log"
)


def parse_crash(path: str) -> Dict[str, str]:
    text = open(path, "r", encoding="utf-8", errors="replace").read()
    out = {
        "file": os.path.basename(path),
        "exception_code": "",
        "exception_address": "",
        "gsc_error": "",
        "gsc_pos": "",
    }
    m = re.search(r"Exception Code:\s*(.+)", text)
    if m:
        out["exception_code"] = m.group(1).strip()
    m = re.search(r"Exception Address:\s*(.+)", text)
    if m:
        out["exception_address"] = m.group(1).strip()
    m = re.search(r"last gsc error message\s*'([^']*)'", text)
    if m:
        out["gsc_error"] = m.group(1).strip()
    m = re.search(r"last gsc pos\s*[^\n]*\s([a-zA-Z0-9_/]+::[a-zA-Z0-9_]+)", text)
    if m:
        out["gsc_pos"] = m.group(1).strip()
    return out


def parse_weapon(path: str) -> Dict[str, str]:
    raw = open(path, "r", encoding="utf-8", errors="replace").read()
    parts = raw.split("\\")
    out: Dict[str, str] = {}
    for i in range(1, len(parts) - 1, 2):
        out[parts[i]] = parts[i + 1]
    return out


def find_anim_header(
    data: bytes, name: str
) -> Optional[Tuple[int, int, int, int, int, int, int, int]]:
    target = name.encode("ascii") + b"\x00"
    start = 0
    while True:
        idx = data.find(target, start)
        if idx < 0:
            return None
        for gap in range(0, 5):
            h = idx - gap - 104
            if h < 0:
                continue
            if struct.unpack_from("<I", data, h)[0] != 0xFFFFFFFF:
                continue
            fps = struct.unpack_from("<f", data, h + 0x30)[0]
            names_ptr = struct.unpack_from("<I", data, h + 0x40)[0]
            if not math.isfinite(fps) or fps < 0.0 or fps > 240.0:
                continue
            if names_ptr not in (0, 0xFFFFFFFF):
                continue
            dbc = struct.unpack_from("<H", data, h + 0x04)[0]
            dsc = struct.unpack_from("<H", data, h + 0x06)[0]
            dic = struct.unpack_from("<H", data, h + 0x08)[0]
            nf = struct.unpack_from("<H", data, h + 0x0E)[0]
            asset = data[h + 0x23]
            is_def = data[h + 0x24]
            return (h, dbc, dsc, dic, nf, asset, is_def, names_ptr)
        start = idx + 1


def parse_xanim_export_numframes(path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                s = line.strip()
                if s.startswith("NUMFRAMES "):
                    try:
                        return int(s.split()[1])
                    except Exception:
                        pass
                if s.startswith("NUMKEYS "):
                    try:
                        return int(s.split()[1])
                    except Exception:
                        pass
    except Exception:
        pass
    return 0


def collect_source_numframes(xanim_dir: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for p in glob.glob(os.path.join(xanim_dir, "vm_thunder_gun_*.xanim_export")):
        name = os.path.splitext(os.path.basename(p))[0]
        out[name] = parse_xanim_export_numframes(p)
    return out


def collect_anim_status(ff_path: str, zone_name: str, xanim_dir: str) -> Dict[str, str]:
    _, data = patch.decrypt_zone(ff_path, zone_name)
    names = [
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob(os.path.join(xanim_dir, "vm_thunder_gun_*.xanim_export"))
    ]
    out: Dict[str, str] = {}
    for n in sorted(names):
        header = find_anim_header(data, n)
        if not header:
            out[n] = "MISSING"
            continue
        _h, dbc, dsc, dic, _nf, _asset, _is_def, names_ptr = header
        if names_ptr == 0xFFFFFFFF and (dbc or dsc or dic):
            out[n] = "REAL"
        else:
            out[n] = "STUB"
    return out


def collect_anim_numframes(ff_path: str, zone_name: str, xanim_dir: str) -> Dict[str, int]:
    _, data = patch.decrypt_zone(ff_path, zone_name)
    names = [
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob(os.path.join(xanim_dir, "vm_thunder_gun_*.xanim_export"))
    ]
    out: Dict[str, int] = {}
    for n in sorted(names):
        header = find_anim_header(data, n)
        out[n] = int(header[4]) if header else 0
    return out


def main() -> None:
    crash_files = sorted(glob.glob(DEFAULT_CRASH_GLOB), key=os.path.getmtime)[-8:]
    crashes = [parse_crash(p) for p in crash_files]

    print("Recent Crashes")
    for c in crashes:
        print(
            f"- {c['file']}: code={c['exception_code']} addr={c['exception_address']} "
            f"gsc='{c['gsc_error']}' pos='{c['gsc_pos']}'"
        )

    if crashes:
        addrs = sorted(set(c["exception_address"] for c in crashes if c["exception_address"]))
        print(f"\nUnique Exception Addresses: {addrs}")

    weapon_path = DEFAULT_WEAPON
    if not os.path.exists(weapon_path):
        fallback = (
            r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\weapons"
            r"\rogue_thundergun_zm"
        )
        if os.path.exists(fallback):
            weapon_path = fallback
    weapon = parse_weapon(weapon_path)
    source_numframes = collect_source_numframes(DEFAULT_XANIM_DIR)
    anim_status_base = collect_anim_status(DEFAULT_FF, ZONE_NAME, DEFAULT_XANIM_DIR)
    anim_numframes_base = collect_anim_numframes(DEFAULT_FF, ZONE_NAME, DEFAULT_XANIM_DIR)
    anim_status = dict(anim_status_base)
    anim_numframes = dict(anim_numframes_base)
    anim_source = {k: "map_ff" for k in anim_status_base.keys()}
    frame_source = {k: "map_ff" for k in anim_numframes_base.keys()}

    if DEFAULT_CUSTOM_XANIM_FF and os.path.exists(DEFAULT_CUSTOM_XANIM_FF):
        try:
            anim_status_custom = collect_anim_status(
                DEFAULT_CUSTOM_XANIM_FF,
                CUSTOM_XANIM_ZONE_NAME,
                DEFAULT_XANIM_DIR,
            )
            anim_numframes_custom = collect_anim_numframes(
                DEFAULT_CUSTOM_XANIM_FF,
                CUSTOM_XANIM_ZONE_NAME,
                DEFAULT_XANIM_DIR,
            )
            for k, v in anim_status_custom.items():
                # Runtime lane truth: prefer custom xanim FF status/frame data over map FF.
                anim_status[k] = v
                anim_source[k] = "custom_xanim_ff"
                anim_numframes[k] = anim_numframes_custom.get(k, 0)
                frame_source[k] = "custom_xanim_ff"
        except Exception as e:
            print(f"\nCustom xanim status read failed: {e}")

    print(f"\nWeapon File: {weapon_path}")
    if DEFAULT_CUSTOM_XANIM_FF:
        print(
            f"Custom XAnim Source: {DEFAULT_CUSTOM_XANIM_FF} "
            f"(zone={CUSTOM_XANIM_ZONE_NAME})"
        )

    watch_fields = [
        "idleAnim",
        "fireAnim",
        "adsFireAnim",
        "reloadEmptyAnim",
        "raiseAnim",
        "dropAnim",
        "firstRaiseAnim",
        "sprintInAnim",
        "sprintLoopAnim",
        "sprintOutAnim",
        "crawlInAnim",
        "crawlForwardAnim",
        "crawlBackAnim",
        "crawlRightAnim",
        "crawlLeftAnim",
        "crawlOutAnim",
        "dtp_in",
        "dtp_loop",
        "dtp_out",
        "slide_in",
    ]
    print("\nActive Weapon Anim Refs")
    for f in watch_fields:
        v = weapon.get(f, "")
        if not v:
            print(f"- {f}: <empty>")
            continue
        state = anim_status.get(v, "N/A")
        src = anim_source.get(v, "-")
        if state == "N/A":
            print(f"- {f}: {v} [{state}; {src}]")
            continue
        runtime_nf = anim_numframes.get(v, 0)
        runtime_src = frame_source.get(v, src)
        source_nf = source_numframes.get(v, 0)
        print(
            f"- {f}: {v} [{state}; {src}; "
            f"frames runtime={runtime_nf}({runtime_src}) source={source_nf}]"
        )

    real_count = sum(1 for v in anim_status.values() if v == "REAL")
    stub_count = sum(1 for v in anim_status.values() if v == "STUB")
    real_count_base = sum(1 for v in anim_status_base.values() if v == "REAL")
    stub_count_base = sum(1 for v in anim_status_base.values() if v == "STUB")
    print(f"\nCurrent Zone Anim Status: REAL={real_count}, STUB={stub_count}")
    print(f"Map FF only: REAL={real_count_base}, STUB={stub_count_base}")

    mismatch = []
    missing_runtime = []
    for anim_name in sorted(source_numframes.keys()):
        src_nf = source_numframes.get(anim_name, 0)
        run_nf = anim_numframes.get(anim_name, 0)
        if run_nf <= 0:
            missing_runtime.append((anim_name, src_nf))
            continue
        if src_nf > 0 and run_nf != src_nf:
            mismatch.append((anim_name, run_nf, src_nf))

    print(
        f"\nFrame Parity Summary: "
        f"source={len(source_numframes)} "
        f"runtime_present={len(source_numframes) - len(missing_runtime)} "
        f"mismatch={len(mismatch)}"
    )
    if mismatch:
        print("Frame Count Mismatches (runtime != source)")
        for name, run_nf, src_nf in mismatch:
            print(f"- {name}: runtime={run_nf} source={src_nf}")
    if missing_runtime:
        print("Missing Runtime Frame Data")
        for name, src_nf in missing_runtime:
            print(f"- {name}: runtime=0 source={src_nf}")

    if os.path.exists(DEFAULT_GAMES_LOG):
        lines = open(DEFAULT_GAMES_LOG, "r", encoding="utf-8", errors="replace").read().splitlines()
        dbg = [ln for ln in lines if "[ROGUE_BOOL]" in ln]
        if dbg:
            print("\nRecent [ROGUE_BOOL] Traces")
            for ln in dbg[-30:]:
                print(f"- {ln}")


if __name__ == "__main__":
    main()
