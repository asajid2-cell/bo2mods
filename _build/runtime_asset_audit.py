#!/usr/bin/env python3
"""
Runtime asset audit for TG debugging.

Purpose:
- show exactly which FF files exist in each lane
- show size/hash/mtime for those files
- show whether key TG assets are present in those FFs
- dump and report key weapondef fields for thundergun aliases
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Tuple


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UNLINKER = os.path.join(REPO_ROOT, "tools", "oat", "Unlinker.exe")
REPORTS_DIR = os.path.join(REPO_ROOT, "_build", "reports")
TMP_DIR = os.path.join(REPO_ROOT, "_build", "panzer_work", "output", "_runtime_verify")


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _iso_utc(ts: float) -> str:
    return _dt.datetime.utcfromtimestamp(ts).isoformat() + "Z"


def _ff_meta(path: str) -> Dict[str, object]:
    out: Dict[str, object] = {"path": path, "exists": os.path.exists(path)}
    if not out["exists"]:
        return out
    st = os.stat(path)
    out["size"] = st.st_size
    out["mtime_utc"] = _iso_utc(st.st_mtime)
    out["sha256"] = _sha256(path)
    return out


def _run(cmd: List[str], timeout: int = 180) -> Tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out


def _list_ff_assets(ff_path: str) -> Dict[str, object]:
    out: Dict[str, object] = {"ok": False, "asset_count": 0, "interesting": {}, "errors": ""}
    if not os.path.exists(UNLINKER):
        out["errors"] = f"missing unlinker: {UNLINKER}"
        return out
    rc, txt = _run([UNLINKER, "--list", ff_path], timeout=240)
    if rc != 0:
        out["errors"] = txt.strip()[-500:]
        return out

    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    assets = [ln for ln in lines if re.match(r"^[A-Za-z0-9_]+,\s", ln)]
    out["ok"] = True
    out["asset_count"] = len(assets)

    interesting = {
        "weapon, thundergun_zm": False,
        "weapon, thundergun_upgraded_zm": False,
        "weapon, ak74u_zm": False,
        "xmodel, rogue_tg_view": False,
        "xmodel, rogue_tg_world": False,
        "xmodel, rogue_tg_viewhands": False,
    }
    for key in list(interesting.keys()):
        interesting[key] = any(a.lower() == key.lower() for a in assets)

    vm_xanim = [a for a in assets if a.lower().startswith("xanim, vm_thunder_gun_")]
    interesting["xanim_vm_thunder_count"] = len(vm_xanim)
    interesting["xanim_vm_thunder_sample"] = vm_xanim[:8]
    out["interesting"] = interesting
    return out


def _extract_weapon_field(raw_text: str, field_name: str) -> str:
    m = re.search(r"(?:^|\\)" + re.escape(field_name) + r"\\([^\\]*)", raw_text)
    return m.group(1) if m else ""


def _find_dumped_weapon(root: str, weapon_name: str) -> str:
    direct = os.path.join(root, "weapons", weapon_name)
    if os.path.exists(direct):
        return direct
    for r, _d, files in os.walk(root):
        for fn in files:
            if fn.lower() == weapon_name.lower():
                return os.path.join(r, fn)
    return ""


def _dump_weapon_fields(ff_path: str, lane_tag: str, wanted: List[str]) -> Dict[str, object]:
    out: Dict[str, object] = {"ok": False, "dump_root": "", "weapons": {}, "errors": ""}
    if not os.path.exists(UNLINKER):
        out["errors"] = f"missing unlinker: {UNLINKER}"
        return out
    stamp = _dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
    dump_root = os.path.join(TMP_DIR, f"audit_{lane_tag}_{stamp}")
    os.makedirs(dump_root, exist_ok=True)
    rc, txt = _run([UNLINKER, "--output-folder", dump_root, "--include-assets", "weapon", ff_path], timeout=360)
    if rc != 0:
        out["errors"] = txt.strip()[-500:]
        return out
    out["ok"] = True
    out["dump_root"] = dump_root
    fields = [
        "displayName",
        "weaponType",
        "weaponClass",
        "inventoryType",
        "fireType",
        "ammoName",
        "clipName",
        "clipSize",
        "maxAmmo",
        "startAmmo",
        "damage",
        "fireTime",
        "shellCasing",
        "fireSound",
        "fireSoundPlayer",
        "gunModel",
        "handModel",
        "worldModel",
        "parentWeaponName",
    ]
    for w in wanted:
        wp = _find_dumped_weapon(dump_root, w)
        ent: Dict[str, object] = {"path": wp, "exists": bool(wp)}
        if wp:
            raw = open(wp, "r", encoding="utf-8", errors="replace").read()
            for f in fields:
                ent[f] = _extract_weapon_field(raw, f)
        out["weapons"][w] = ent
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod-name", default="zm_roguelike_panzer")
    ap.add_argument(
        "--output",
        default=os.path.join(REPORTS_DIR, "last_runtime_asset_audit.json"),
    )
    args = ap.parse_args()

    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)

    localapp = os.environ.get("LOCALAPPDATA", "")
    storage_root = os.path.join(localapp, "Plutonium", "storage", "t6") if localapp else ""

    targets = {
        "game_mod_ff": os.path.join(REPO_ROOT, "mods", args.mod_name, "zone", "all", "mod.ff"),
        "storage_mod_ff": os.path.join(storage_root, "mods", args.mod_name, "zone", "all", "mod.ff"),
        "game_mod_load_ff": os.path.join(REPO_ROOT, "mods", args.mod_name, "zone", "all", "mod_load.ff"),
        "storage_mod_load_ff": os.path.join(storage_root, "mods", args.mod_name, "zone", "all", "mod_load.ff"),
        "base_so_ff": os.path.join(REPO_ROOT, "zone", "all", "so_zsurvival_zm_transit.ff"),
    }

    report: Dict[str, object] = {
        "timestamp_utc": _dt.datetime.utcnow().isoformat() + "Z",
        "repo_root": REPO_ROOT,
        "unlinker": UNLINKER,
        "mod_name": args.mod_name,
        "files": {},
        "comparisons": {},
    }

    for key, path in targets.items():
        meta = _ff_meta(path)
        if meta.get("exists"):
            meta["list"] = _list_ff_assets(path)
        report["files"][key] = meta

    gm = report["files"]["game_mod_ff"]
    sm = report["files"]["storage_mod_ff"]
    if gm.get("exists") and sm.get("exists"):
        report["comparisons"]["mod_ff_same_hash"] = gm.get("sha256") == sm.get("sha256")

    if gm.get("exists"):
        report["weapon_dump_game_mod_ff"] = _dump_weapon_fields(
            targets["game_mod_ff"],
            "game_modff",
            ["thundergun_zm", "thundergun_upgraded_zm", "ak74u_zm"],
        )
    if sm.get("exists"):
        report["weapon_dump_storage_mod_ff"] = _dump_weapon_fields(
            targets["storage_mod_ff"],
            "storage_modff",
            ["thundergun_zm", "thundergun_upgraded_zm", "ak74u_zm"],
        )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    def _brief(name: str) -> None:
        m = report["files"].get(name, {})
        if not m.get("exists"):
            print(f"[AUDIT] {name}: MISSING")
            return
        sha = str(m.get("sha256", ""))[:12]
        print(
            f"[AUDIT] {name}: size={m.get('size')} sha256={sha} mtime={m.get('mtime_utc')} path={m.get('path')}"
        )
        lst = m.get("list", {})
        if lst.get("ok"):
            it = lst.get("interesting", {})
            print(
                "[AUDIT]   assets:"
                f" tg={int(bool(it.get('weapon, thundergun_zm')))}"
                f" tg_upg={int(bool(it.get('weapon, thundergun_upgraded_zm')))}"
                f" ak={int(bool(it.get('weapon, ak74u_zm')))}"
                f" tg_view={int(bool(it.get('xmodel, rogue_tg_view')))}"
                f" tg_viewhands={int(bool(it.get('xmodel, rogue_tg_viewhands')))}"
                f" vm_xanim={it.get('xanim_vm_thunder_count', 0)}"
                f" total={lst.get('asset_count', 0)}"
            )
        else:
            print(f"[AUDIT]   list_error: {lst.get('errors', '')}")

    _brief("game_mod_ff")
    _brief("storage_mod_ff")
    _brief("game_mod_load_ff")
    _brief("storage_mod_load_ff")

    dump = report.get("weapon_dump_game_mod_ff", {})
    w = ((dump.get("weapons") or {}).get("thundergun_zm") or {})
    if w:
        print(
            "[AUDIT] thundergun_zm fields:"
            f" clip={w.get('clipSize', '')}"
            f" max={w.get('maxAmmo', '')}"
            f" start={w.get('startAmmo', '')}"
            f" fireType={w.get('fireType', '')}"
            f" weaponClass={w.get('weaponClass', '')}"
            f" gunModel={w.get('gunModel', '')}"
            f" handModel={w.get('handModel', '')}"
            f" parent={w.get('parentWeaponName', '')}"
        )

    same = report.get("comparisons", {}).get("mod_ff_same_hash")
    if same is not None:
        print(f"[AUDIT] game/storage mod.ff hash_match={same}")
    print(f"[AUDIT] report={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

