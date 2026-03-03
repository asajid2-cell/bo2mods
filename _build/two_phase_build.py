#!/usr/bin/env python3
"""Two-phase build to break circular image dependency in OAT Linker.

Phase 1: Build zone WITHOUT thundergun images/materials/models
          (so the deployed zone won't cache empty tg_*/rogue_tg_* images)
Phase 2: Build zone WITH thundergun images/materials/models
          (OAT reads IWI files from disk since loaded zone has no tg_/rogue_tg_*)
"""
import subprocess
import shutil
import os
import sys
import re
import json
import struct
import glob
import time
import hashlib
from datetime import datetime

ZONE_SOURCE = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\zone_source\so_zsurvival_zm_transit.zone"
OUTPUT_DIR = r"z:\Games\pluto_t6_full_game\_build\panzer_work\output"
DEPLOY_DIR = r"z:\Games\pluto_t6_full_game\zone\all"
DEPLOY_DIR_MOD = os.path.expandvars(r"%localappdata%\Plutonium\storage\t6\mods\zm_roguelike_panzer\zone\all")
WORK_DIR = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit"
FF_NAME = "so_zsurvival_zm_transit.ff"
IPAK_NAME = "so_zsurvival_zm_transit.ipak"
MOD_SCRIPT_SRC = r"z:\Games\pluto_t6_full_game\mods\zm_roguelike_panzer\scripts\mod_i_am_mod.gsc"
MOD_SCRIPT_SRC_DISABLED = r"z:\Games\pluto_t6_full_game\mods\__disabled__zm_roguelike_panzer\scripts\mod_i_am_mod.gsc"
MOD_SCRIPT_DST_DIR = os.path.expandvars(r"%localappdata%\Plutonium\storage\t6\mods\zm_roguelike_panzer\scripts")
RUNTIME_RESET_SCRIPT = r"z:\Games\pluto_t6_full_game\_build\runtime_reset.ps1"

# Runtime in this workspace resolves Transit map FFs from zone/all.
# Keep base deploy enabled by default so custom weapon assets are actually live in-game.
DEPLOY_TO_BASE = os.environ.get("ROGUE_DEPLOY_TO_BASE", "1") not in ("0", "false", "False")
DEPLOY_TO_MOD = os.environ.get("ROGUE_DEPLOY_TO_MOD", "1") not in ("0", "false", "False")

LINKER = r"z:\Games\pluto_t6_full_game\tools\oat\Linker.exe"
UNLINKER = r"z:\Games\pluto_t6_full_game\tools\oat\Unlinker.exe"
THUNDERGUN_WEAPON_BUILDER = r"z:\Games\pluto_t6_full_game\_build\build_thundergun_weapon.py"
THUNDERGUN_WEAPON_PROFILE = os.environ.get("ROGUE_TG_PROFILE", "stable")
# Gameplay lane: default to thundergun semantics now that carrier alias override is stable.
# Set ROGUE_TG_SEMANTICS=minigun if you need to fall back to a pure donor behavior probe.
THUNDERGUN_WEAPON_SEMANTICS = os.environ.get("ROGUE_TG_SEMANTICS", "thundergun")
# Visual sanity lane: default to rogue model swap so carrier overrides actually show BO3-ported models.
# Set ROGUE_TG_MODEL_MODE=base when you want a pure donor clone for registration debugging.
THUNDERGUN_WEAPON_MODEL_MODE = os.environ.get("ROGUE_TG_MODEL_MODE", "rogue")
THUNDERGUN_BASE_WPN_DEFAULT = r"z:\Games\pluto_t6_full_game\_build\runtime_unlink_zm_transit_full_1\weapons\ak74u_zm"
THUNDERGUN_BASE_WPN_FALLBACK = r"z:\Games\pluto_t6_full_game\_build\runtime_unlink_zm_transit_full_1\weapons\m14_zm"
THUNDERGUN_BASE_WPN_LEGACY = r"z:\Games\pluto_t6_full_game\_build\panzer_work\unlinked\weapons\minigun_zm"
THUNDERGUN_BASE_WPN = os.environ.get(
    "ROGUE_TG_BASE_WEAPON",
    (
        THUNDERGUN_BASE_WPN_DEFAULT
        if os.path.exists(THUNDERGUN_BASE_WPN_DEFAULT)
        else (
            THUNDERGUN_BASE_WPN_FALLBACK
            if os.path.exists(THUNDERGUN_BASE_WPN_FALLBACK)
            else THUNDERGUN_BASE_WPN_LEGACY
        )
    ),
)
THUNDERGUN_FORCE_AMMO_NAME = os.environ.get("ROGUE_TG_AMMO_NAME", "")
THUNDERGUN_FORCE_CLIP_NAME = os.environ.get("ROGUE_TG_CLIP_NAME", "")
THUNDERGUN_FORCE_HUD_ICON = os.environ.get("ROGUE_TG_HUD_ICON", "")
THUNDERGUN_FORCE_KILL_ICON = os.environ.get("ROGUE_TG_KILL_ICON", THUNDERGUN_FORCE_HUD_ICON)
# Default to clearing camo to avoid dragging in large base-game camo image chains
# (OAT can't always source them from loaded FFs and will try to build IPaks from disk IWIs).
THUNDERGUN_CLEAR_CAMO = os.environ.get("ROGUE_TG_CLEAR_CAMO", "1") not in ("0", "false", "False")
THUNDERGUN_TRUTH_ALIAS = os.environ.get("ROGUE_TG_TRUTH_ALIAS", "ak74u_zm")
THUNDERGUN_TRUTH_ALIAS_UPG = os.environ.get("ROGUE_TG_TRUTH_ALIAS_UPG", "ak74u_upgraded_zm")
USE_SO_SURVIVAL_LOAD_BASELINE = True

SO_SURVIVAL_LOAD_FF_VANILLA = r"z:\Games\pluto_t6_full_game\zone\all\so_zsurvival_zm_transit.ff.vanilla_save"
SO_SURVIVAL_LOAD_FF_CURRENT = r"z:\Games\pluto_t6_full_game\zone\all\so_zsurvival_zm_transit.ff"
SO_SURVIVAL_LOAD_FF_CLEAN_BUILT = r"z:\Games\pluto_t6_full_game\_build\panzer_work\output\so_zsurvival_zm_transit_single_test.ff"
SO_SURVIVAL_LOAD_FF_PRISTINE_COPY = r"z:\Games\pluto_t6_full_game\_build\ff_baseline\so_zsurvival_zm_transit_vanilla.ff"
SO_SURVIVAL_LOAD_FF_LOCAL_UNPATCHED = r"z:\Games\pluto_t6_full_game\_build\panzer_work\output\unpatched_so_zsurvival_zm_transit.ff"
SO_SURVIVAL_LOAD_FF_HARDFALLBACK = r"z:\Games\pluto_t6_full_game\_build\ff_backup\20260213-123213\so_zsurvival_zm_transit.ff"
# Deterministic baseline: pin to known-good stock backup for carrier-load builds.
# Local unpatched outputs can inherit prior experimental drift and reintroduce load hangs.
SO_SURVIVAL_LOAD_FF_FIXED = SO_SURVIVAL_LOAD_FF_HARDFALLBACK
SO_SURVIVAL_LOAD_FF = (
    SO_SURVIVAL_LOAD_FF_FIXED
    if (SO_SURVIVAL_LOAD_FF_FIXED and os.path.exists(SO_SURVIVAL_LOAD_FF_FIXED))
    else (
        SO_SURVIVAL_LOAD_FF_LOCAL_UNPATCHED
        if os.path.exists(SO_SURVIVAL_LOAD_FF_LOCAL_UNPATCHED)
        else (
            SO_SURVIVAL_LOAD_FF_CLEAN_BUILT
            if os.path.exists(SO_SURVIVAL_LOAD_FF_CLEAN_BUILT)
            else (SO_SURVIVAL_LOAD_FF_VANILLA if os.path.exists(SO_SURVIVAL_LOAD_FF_VANILLA) else SO_SURVIVAL_LOAD_FF_CURRENT)
        )
    )
)

# Control-group mode: compile standalone thundergun_xanims.ff and load it via --load.
# This bypasses in-place Phase 3 binary splicing entirely.
USE_CUSTOM_XANIM_FF = True
ENABLE_PHASE3_PATCH = False
CUSTOM_XANIM_FF = r"z:\Games\pluto_t6_full_game\_build\panzer_work\output\thundergun_xanims.ff"
XANIM_EXPORT_SRC_PRIMARY = r"z:\Games\pluto_t6_full_game\_build\asset_port_pipeline\thundergun_e2e\converted_anims"
XANIM_EXPORT_SRC_FALLBACK = r"z:\Games\pluto_t6_full_game\_build\asset_port_pipeline\thundergun_e2e\integration_ready\thundergun_town_full\zone_raw\thundergun_town_full\xanim_export\viewmodel"
XANIM_EXPORT_DST_ROOT = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\xanim_export"
XANIM_EXPORT_DST_VIEWMODEL = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\xanim_export\viewmodel"
XANIM_EXPORT_GLOB = "vm_thunder_gun_*.xanim_export"
PHASE3_PATCH_ONLY = [
    "vm_thunder_gun_idle",
]
THUNDERGUN_FORCE_ROOT_ONLY_XANIM = False
THUNDERGUN_VIEW_GLB = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\model_export\thundergun_view_lod0.glb"
THUNDERGUN_VIEW_GLB_FALLBACK = THUNDERGUN_VIEW_GLB + ".prescale_bak"
THUNDERGUN_VIEW_GLB_MASTER = THUNDERGUN_VIEW_GLB + ".bak"
NEUTRALIZE_ROOT_BONES = ["tag_player", "tag_camera", "tag_origin"]
# Carrier FF crypto seed must match the carrier zone seed used by linker load.
# Using the parent map seed causes inflate -3 when loading thundergun_xanims.ff.
CUSTOM_XANIM_CRYPTO_SEED = "thundergun_xanims"

# Offline safety gate: run integrity check before deployment.
PRECHECK_ENABLED = True
PRECHECK_STRICT_COUNTS = False
PRECHECK_REPORT_DIR = r"z:\Games\pluto_t6_full_game\_build\reports"
PRECHECK_BASELINE_OVERRIDE = SO_SURVIVAL_LOAD_FF_HARDFALLBACK
TG_BUILD_MANIFEST_PATH = os.path.join(PRECHECK_REPORT_DIR, "last_tg_build_manifest.json")

# Critical mechz scripts must stay as text source files.
# If these are staged from unlinked binary script blobs (e.g. leading "€GSC"),
# #using_animtree directives do not register and Transit errors with:
# "Couldn't find animtree 'mechz_claw' on the server."
CRITICAL_TEXT_SCRIPTS = [
    r"clientscripts/mp/zombies/_rogue_mechz_animtree.csc",
    r"clientscripts/mp/zombies/_zm_ai_mechz.csc",
    r"aitype/clientscripts/zm_tomb_mech_zombie.csc",
    r"maps/mp/zombies/_zm_ai_mechz.gsc",
    r"maps/mp/zombies/_zm_ai_mechz_booster.gsc",
    r"maps/mp/zombies/_zm_ai_mechz_claw.gsc",
    r"maps/mp/zombies/_zm_ai_mechz_dev.gsc",
    r"maps/mp/zombies/_zm_ai_mechz_ffotd.gsc",
    r"maps/mp/zombies/_zm_ai_mechz_ft.gsc",
]

# Guardrail: keep core Transit FF dependencies on known-good hashes.
# We only build/deploy so_zsurvival_zm_transit, but stale/corrupted zm_transit*
# in zone/all can break map load around 75%.
CORE_TRANSIT_RESTORE_DIR = r"z:\Games\pluto_t6_full_game\_build\ff_backup\20260213-123213"
CORE_TRANSIT_EXPECTED_SHA256 = {
    "zm_transit.ff": "A77B22580D701C7206134003FC89468028E8F7F3AE520D5AA53B437AA2A7C38D",
    "zm_transit_patch.ff": "71668A58DD0AA278F6CF47A5A579588C92279B6D98E7D61DBC345C0DDE1F4D5B",
}

BASE_ARGS = [
    LINKER, "--verbose",
    "--base-folder", WORK_DIR,
    "--add-asset-search-path", WORK_DIR,
    "--add-source-search-path", WORK_DIR,
    "--output-folder", OUTPUT_DIR,
    "--load", r"z:\Games\pluto_t6_full_game\zone\all\patch_zm.ff",
    "--load", r"z:\Games\pluto_t6_full_game\zone\all\code_post_gfx_zm.ff",
    "--load", r"z:\Games\pluto_t6_full_game\zone\all\dlc4_load_zm.ff",
    "--load", r"z:\Games\pluto_t6_full_game\zone\english\en_dlc4_load_zm.ff",
    "--load", r"z:\Games\pluto_t6_full_game\zone\all\zm_tomb_patch.ff",
    "--load", r"z:\Games\pluto_t6_full_game\zone\all\zm_tomb.ff",
    "--load", r"z:\Games\pluto_t6_full_game\zone\all\common_zm.ff",
    "so_zsurvival_zm_transit"
]

def resolve_mod_script_source():
    """Resolve workspace script path: prefer active mod path, fall back to disabled path."""
    if os.path.exists(MOD_SCRIPT_SRC):
        return MOD_SCRIPT_SRC
    if os.path.exists(MOD_SCRIPT_SRC_DISABLED):
        return MOD_SCRIPT_SRC_DISABLED
    return MOD_SCRIPT_SRC


def _collect_load_ff_candidates():
    """Return ordered candidate list for the baseline so_zsurvival load FF."""
    candidates = []
    # Prefer deterministic local-unpatched layout first.
    for p in (
        SO_SURVIVAL_LOAD_FF_LOCAL_UNPATCHED,
        SO_SURVIVAL_LOAD_FF_CLEAN_BUILT,
        SO_SURVIVAL_LOAD_FF_PRISTINE_COPY,
        SO_SURVIVAL_LOAD_FF_VANILLA,
        SO_SURVIVAL_LOAD_FF_HARDFALLBACK,
        SO_SURVIVAL_LOAD_FF,
        SO_SURVIVAL_LOAD_FF_CURRENT,
    ):
        if p and os.path.exists(p):
            candidates.append(os.path.abspath(p))

    # Add ff_backup copies (oldest first tends to be cleaner baselines).
    backup_glob = r"z:\Games\pluto_t6_full_game\_build\ff_backup\*\so_zsurvival_zm_transit.ff"
    backup_files = sorted(glob.glob(backup_glob), key=lambda x: os.path.getmtime(x))
    for p in backup_files:
        ap = os.path.abspath(p)
        if ap not in candidates:
            candidates.append(ap)

    return candidates


def ensure_pristine_baseline_copy():
    """Create/refresh .ff-extension pristine baseline copy from .ff.vanilla_save."""
    src = SO_SURVIVAL_LOAD_FF_VANILLA
    dst = SO_SURVIVAL_LOAD_FF_PRISTINE_COPY
    if not os.path.exists(src):
        return False
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _baseline_is_contaminated(path):
    """
    Validate baseline FF structural sanity before using it as --load input.
    """
    try:
        from patch_zone_xanims import decrypt_zone
        _, raw = decrypt_zone(path, "so_zsurvival_zm_transit")
    except Exception:
        # If we cannot parse, treat as unusable.
        return True

    # Basic structural sanity: raw length must match header totalSize + 40.
    if len(raw) < 40:
        return True
    total_plus_40 = struct.unpack_from("<I", raw, 0)[0] + 40
    if total_plus_40 != len(raw):
        return True

    # Marker-based contamination checks caused false positives because baseline
    # layouts can legitimately contain vm_thunder_gun_* stubs. Structural
    # validity plus linker load retry is a more reliable gate.
    return False


def _set_so_survival_load_ff(path):
    """Update SO_SURVIVAL_LOAD_FF and mutate BASE_ARGS in-place."""
    global SO_SURVIVAL_LOAD_FF
    SO_SURVIVAL_LOAD_FF = os.path.abspath(path)

    # Try replacing an existing so_zsurvival load entry first.
    for i in range(len(BASE_ARGS) - 1):
        if BASE_ARGS[i] == "--load" and "so_zsurvival_zm_transit.ff" in BASE_ARGS[i + 1].lower():
            BASE_ARGS[i + 1] = SO_SURVIVAL_LOAD_FF
            return

    # Otherwise insert before zm_tomb_patch, or just before zone name.
    insert_at = len(BASE_ARGS) - 1
    for i in range(len(BASE_ARGS) - 1):
        if BASE_ARGS[i] == "--load" and "zm_tomb_patch.ff" in BASE_ARGS[i + 1].lower():
            insert_at = i
            break
    BASE_ARGS[insert_at:insert_at] = ["--load", SO_SURVIVAL_LOAD_FF]


def _is_inflate_failure(output):
    return "inflate of stream failed" in (output or "").lower()


def _is_load_ff_failure(output):
    text = (output or "").lower()
    return ("inflate of stream failed" in text) or ("loading fastfile failed" in text)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def ensure_core_transit_integrity():
    """
    Ensure base Transit dependency FFs in zone/all are known-good.
    If drift is detected, restore from pinned backup source.
    """
    drift = []
    for name, expected in CORE_TRANSIT_EXPECTED_SHA256.items():
        dst = os.path.join(DEPLOY_DIR, name)
        if not os.path.exists(dst):
            drift.append((name, "missing", expected))
            continue
        actual = _sha256(dst)
        if actual != expected:
            drift.append((name, actual, expected))

    if not drift:
        print("Prep: core transit dependency FFs are clean.")
        return True

    print("Prep: detected core transit FF drift; restoring pinned clean versions...")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    snap_dir = os.path.join(OUTPUT_DIR, "_live_snapshots", f"{stamp}_core_transit_repair")
    os.makedirs(snap_dir, exist_ok=True)

    for name, actual, expected in drift:
        dst = os.path.join(DEPLOY_DIR, name)
        src = os.path.join(CORE_TRANSIT_RESTORE_DIR, name)

        if os.path.exists(dst):
            shutil.copy2(dst, os.path.join(snap_dir, name + ".before_repair"))

        if not os.path.exists(src):
            print(f"  ERROR: missing restore source: {src}")
            return False
        shutil.copy2(src, dst)

        repaired = _sha256(dst) if os.path.exists(dst) else "missing"
        if repaired != expected:
            print(f"  ERROR: restore hash mismatch for {name}: got {repaired}, expected {expected}")
            return False
        print(f"  Restored {name}: {actual} -> {repaired}")

    print(f"  Core transit repair snapshot: {snap_dir}")
    return True

# Lines to comment out for Phase 1 (thundergun models, weapons, materials, images)
# These are the lines that reference tg_*/rogue_tg_* images either directly or indirectly
COMMENT_PATTERNS = [
    r'^>ipak,so_zsurvival_zm_transit',
    r'^xmodel,thundergun_',
    r'^xmodel,rogue_tg_',
    r'^weapon,thundergun_',
    r'^weapon,rogue_thundergun_',
    r'^material,mtl_wpn_t7_zmb_hd_thundergun_',
    r'^material,mtl_rogue_tg_',
    r'^image,tg_',
    r'^image,rogue_tg_',
    r'^xanim,,?vm_thunder_gun_',
]


def maybe_add_custom_xanim_load():
    """Optionally inject custom thundergun_xanims.ff into linker args."""
    if not USE_CUSTOM_XANIM_FF:
        return
    if not os.path.exists(CUSTOM_XANIM_FF):
        print(f"  WARNING: USE_CUSTOM_XANIM_FF=1 but missing {CUSTOM_XANIM_FF}")
        return
    BASE_ARGS.insert(-1, "--load")
    BASE_ARGS.insert(-1, CUSTOM_XANIM_FF)
    print(f"  Using custom xanim load: {CUSTOM_XANIM_FF}")


def build_custom_xanim_ff():
    """Compile standalone thundergun_xanims.ff from staged xanim_export files."""
    if not USE_CUSTOM_XANIM_FF:
        return True

    compiler_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compile_xanim_zone.py")
    if not os.path.exists(compiler_script):
        print(f"  ERROR: Missing compiler script: {compiler_script}")
        return False

    xanim_dir = XANIM_EXPORT_DST_ROOT
    if not glob.glob(os.path.join(xanim_dir, XANIM_EXPORT_GLOB)):
        xanim_dir = XANIM_EXPORT_SRC_PRIMARY
        if not glob.glob(os.path.join(xanim_dir, XANIM_EXPORT_GLOB)):
            print(f"  ERROR: No xanim exports found for custom xanim FF build")
            print(f"         checked: {XANIM_EXPORT_DST_ROOT}")
            print(f"         checked: {XANIM_EXPORT_SRC_PRIMARY}")
            return False

    cmd = [
        sys.executable, compiler_script,
        "--xanim-dir", xanim_dir,
        "--pattern", XANIM_EXPORT_GLOB,
        "--output-dir", OUTPUT_DIR,
        "--zone-name", "thundergun_xanims",
        "--crypto-seed", CUSTOM_XANIM_CRYPTO_SEED,
        "--emit-mode", "static_pose",
        "--neutralize-bones", *NEUTRALIZE_ROOT_BONES,
    ]
    print(f"  Building custom xanim FF from: {xanim_dir}")
    result = subprocess.run(cmd, timeout=600)
    if result.returncode != 0:
        print("  ERROR: compile_xanim_zone failed")
        return False

    if not os.path.exists(CUSTOM_XANIM_FF):
        print(f"  ERROR: custom xanim FF not produced: {CUSTOM_XANIM_FF}")
        return False

    print(f"  Built custom xanim FF: {CUSTOM_XANIM_FF} ({os.path.getsize(CUSTOM_XANIM_FF):,} bytes)")
    return True


def verify_custom_xanim_ff():
    """Offline validation for standalone custom xanim FF container + payload."""
    if not USE_CUSTOM_XANIM_FF:
        return True
    if not os.path.exists(CUSTOM_XANIM_FF):
        print(f"  ERROR: missing custom xanim FF for validation: {CUSTOM_XANIM_FF}")
        return False

    try:
        from patch_zone_xanims import decrypt_zone
    except Exception as e:
        print(f"  ERROR: failed importing decrypt_zone for custom FF validation: {e}")
        return False

    try:
        _, raw = decrypt_zone(CUSTOM_XANIM_FF, CUSTOM_XANIM_CRYPTO_SEED)
    except Exception as e:
        print(f"  ERROR: decrypt failed for custom xanim FF: {e}")
        return False

    if len(raw) < 40:
        print(f"  ERROR: custom xanim FF decrypted payload too small: {len(raw)} bytes")
        return False

    total_size = struct.unpack_from("<I", raw, 0)[0]
    external_size = struct.unpack_from("<I", raw, 4)[0]
    block_sizes = struct.unpack_from("<8I", raw, 8)
    expected_len = total_size + 40
    if expected_len != len(raw):
        print(
            "  ERROR: custom xanim FF payload size mismatch "
            f"(totalSize={total_size}, rawLen={len(raw)}, expected={expected_len})"
        )
        return False
    if external_size != 0:
        print(f"  ERROR: custom xanim FF externalSize must be 0, got {external_size}")
        return False
    if block_sizes[0] == 0 or block_sizes[5] == 0:
        print(f"  ERROR: custom xanim FF invalid block sizing: TEMP={block_sizes[0]} VIRTUAL={block_sizes[5]}")
        return False

    print(
        "  Custom xanim FF validation PASS: "
        f"raw={len(raw):,} totalSize={total_size:,} TEMP={block_sizes[0]:,} VIRTUAL={block_sizes[5]:,}"
    )
    return True


def run_preflight(candidate_ff, zone_name):
    """Run offline integrity checks before deployment."""
    if not PRECHECK_ENABLED:
        print("  Preflight: disabled")
        return True

    try:
        from ff_integrity_check import run_check
        from patch_zone_xanims import decrypt_zone, parse_string_table
    except Exception as e:
        print(f"  ERROR: failed importing ff_integrity_check: {e}")
        return False

    def _is_valid_baseline(path):
        if not path or not os.path.exists(path):
            return False
        try:
            _, raw = decrypt_zone(path, zone_name)
            if not raw or len(raw) < 44:
                return False
            parse_string_table(raw)
            return True
        except Exception:
            return False

    baseline_candidates = []
    for p in (
        PRECHECK_BASELINE_OVERRIDE,
        SO_SURVIVAL_LOAD_FF,
        SO_SURVIVAL_LOAD_FF_CURRENT,
        os.path.join(DEPLOY_DIR_MOD, FF_NAME),
        os.path.join(DEPLOY_DIR, FF_NAME),
    ):
        if not p:
            continue
        ap = os.path.abspath(p)
        if ap == os.path.abspath(candidate_ff):
            continue
        if ap not in baseline_candidates:
            baseline_candidates.append(ap)

    baseline = None
    for p in baseline_candidates:
        if _is_valid_baseline(p):
            baseline = p
            break

    if not baseline:
        print("  WARNING: Preflight skipped (no valid baseline FF found for comparison).")
        return True

    os.makedirs(PRECHECK_REPORT_DIR, exist_ok=True)
    report_path = os.path.join(
        PRECHECK_REPORT_DIR,
        f"preflight_{zone_name}_{int(time.time())}.json"
    )

    print(f"  Preflight baseline: {baseline}")
    print(f"  Preflight candidate: {candidate_ff}")
    ok, report = run_check(
        baseline_ff=baseline,
        candidate_ff=candidate_ff,
        zone_name=zone_name,
        name_prefix="vm_thunder_gun_",
        strict_counts=PRECHECK_STRICT_COUNTS,
    )

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"  Preflight report: {report_path}")

    if not ok:
        print("  ERROR: Preflight FAILED; refusing deployment.")
        for err in report.get("errors", []):
            print(f"    - {err}")
        return False

    print("  Preflight PASS")
    for w in report.get("warnings", []):
        print(f"    warning: {w}")
    return True


def stage_thundergun_xanim_exports():
    """
    Ensure vm_thunder_gun_*.xanim_export are available for native OAT compilation.
    """
    if USE_CUSTOM_XANIM_FF:
        print("  Skipping native xanim_export staging (custom xanim FF mode)")
        return

    def _read_numparts(path):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read()
        m = re.search(r"NUMPARTS\s+(\d+)", data)
        return int(m.group(1)) if m else -1

    def _collect_source(src_dir):
        if not os.path.isdir(src_dir):
            return []
        files = sorted(
            f for f in os.listdir(src_dir)
            if re.fullmatch(r"vm_thunder_gun_.*\.xanim_export", f)
        )
        out = []
        for name in files:
            full = os.path.join(src_dir, name)
            out.append((name, full, _read_numparts(full)))
        return out

    primary = _collect_source(XANIM_EXPORT_SRC_PRIMARY)
    fallback = _collect_source(XANIM_EXPORT_SRC_FALLBACK)

    def _is_compatible(file_rows):
        if not file_rows:
            return False
        counts = [row[2] for row in file_rows]
        # Allow up to 255 bones (T6 XAnimParts max). The 133-bone BO3 exports
        # already use T6 bone names and can be compiled directly by OAT.
        return all(1 <= c <= 255 for c in counts)

    if _is_compatible(primary):
        chosen = primary
        chosen_src = XANIM_EXPORT_SRC_PRIMARY
    elif _is_compatible(fallback):
        chosen = fallback
        chosen_src = XANIM_EXPORT_SRC_FALLBACK
    else:
        raise RuntimeError(
            "No compatible thundergun xanim source found. "
            f"Primary={XANIM_EXPORT_SRC_PRIMARY}, Fallback={XANIM_EXPORT_SRC_FALLBACK}"
        )

    os.makedirs(XANIM_EXPORT_DST_ROOT, exist_ok=True)
    os.makedirs(XANIM_EXPORT_DST_VIEWMODEL, exist_ok=True)

    # Remove old staged vm_thunder files first to avoid mixed-bone contamination.
    for dst_dir in (XANIM_EXPORT_DST_ROOT, XANIM_EXPORT_DST_VIEWMODEL):
        for name in os.listdir(dst_dir):
            if re.fullmatch(r"vm_thunder_gun_.*\.xanim_export", name):
                try:
                    os.remove(os.path.join(dst_dir, name))
                except OSError:
                    pass

    copied = 0
    counts = set()
    for name, src, nparts in chosen:
        dst_root = os.path.join(XANIM_EXPORT_DST_ROOT, name)
        dst_view = os.path.join(XANIM_EXPORT_DST_VIEWMODEL, name)
        shutil.copy2(src, dst_root)
        shutil.copy2(src, dst_view)
        counts.add(nparts)
        copied += 1

    print(
        f"  Staged {copied} xanim_export files from {chosen_src} "
        f"to {XANIM_EXPORT_DST_ROOT} and {XANIM_EXPORT_DST_VIEWMODEL} "
        f"(NUMPARTS={sorted(counts)})"
    )
    normalize_staged_thundergun_xanims()


def _looks_binary_script(path):
    try:
        with open(path, "rb") as f:
            head = f.read(256)
    except Exception:
        return True
    if not head:
        return True
    # Binary compiled script blobs commonly start with UTF-8 euro sign + "GSC".
    if head.startswith(b"\xE2\x82\xACGSC") or head.startswith(b"\x80GSC"):
        return True
    # Text scripts should not contain NUL bytes in the header.
    return b"\x00" in head


def ensure_critical_text_scripts():
    missing = []
    binary = []
    for rel in CRITICAL_TEXT_SCRIPTS:
        p = os.path.join(WORK_DIR, rel.replace("/", os.sep))
        if not os.path.exists(p):
            missing.append(rel)
            continue
        if _looks_binary_script(p):
            binary.append(rel)

    if missing:
        print("ERROR: Missing critical mechz script sources:")
        for rel in missing:
            print(f"  - {rel}")
        return False
    if binary:
        print("ERROR: Critical mechz scripts are binary blobs, expected text source:")
        for rel in binary:
            print(f"  - {rel}")
        return False
    return True


def _format_vec3(v):
    return f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}"


def _quat_to_matrix_rows(q):
    x, y, z, w = q
    n = (x * x) + (y * y) + (z * z) + (w * w)
    if n <= 0.0:
        return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    inv = 1.0 / n
    xx = x * x * inv
    yy = y * y * inv
    zz = z * z * inv
    xy = x * y * inv
    xz = x * z * inv
    yz = y * z * inv
    wx = w * x * inv
    wy = w * y * inv
    wz = w * z * inv
    return [
        [1.0 - (2.0 * (yy + zz)), 2.0 * (xy - wz), 2.0 * (xz + wy)],
        [2.0 * (xy + wz), 1.0 - (2.0 * (xx + zz)), 2.0 * (yz - wx)],
        [2.0 * (xz - wy), 2.0 * (yz + wx), 1.0 - (2.0 * (xx + yy))],
    ]


def _extract_model_bind_pose_from_view_glb():
    gltf, _ = _load_glb_json_and_bin(THUNDERGUN_VIEW_GLB)
    nodes = gltf.get("nodes", [])
    skins = gltf.get("skins", [])
    if not skins:
        raise RuntimeError(f"Viewmodel GLB has no skins: {THUNDERGUN_VIEW_GLB}")
    joints = skins[0].get("joints", [])
    if not joints:
        raise RuntimeError(f"Viewmodel GLB skin has no joints: {THUNDERGUN_VIEW_GLB}")

    part_names = []
    bind_pose_by_name = {}
    for i, node_idx in enumerate(joints):
        if node_idx < 0 or node_idx >= len(nodes):
            raise RuntimeError(f"Invalid joint node index {node_idx} in {THUNDERGUN_VIEW_GLB}")
        node = nodes[node_idx]
        name = node.get("name", f"joint_{i}")
        part_names.append(name)
        offset = node.get("translation", [0.0, 0.0, 0.0])
        quat = node.get("rotation", [0.0, 0.0, 0.0, 1.0])
        bind_pose_by_name[name] = {
            "offset": [float(offset[0]), float(offset[1]), float(offset[2])],
            "rot": _quat_to_matrix_rows([float(quat[0]), float(quat[1]), float(quat[2]), float(quat[3])]),
        }
    return part_names, bind_pose_by_name


def _read_notetrack_tail(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.read().splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("NOTETRACKS"):
            return lines[i:]
    return []


def _write_full_xanim(path, source_header_line, part_names, framerate, frame_count, frame_values_by_name, notetrack_tail):
    out = []
    if source_header_line:
        out.append(source_header_line.rstrip("\n"))
        out.append("")
    out.append("ANIMATION")
    out.append("VERSION 3")
    out.append("")
    out.append(f"NUMPARTS {len(part_names)}")
    for i, name in enumerate(part_names):
        out.append(f'PART {i} "{name}"')
    out.append("")
    out.append(f"FRAMERATE {int(round(framerate))}")
    out.append(f"NUMFRAMES {frame_count}")

    for frame in range(frame_count):
        out.append(f"FRAME {frame}")
        values = frame_values_by_name[frame]
        for idx, name in enumerate(part_names):
            bone = values[name]
            out.append(f"PART {idx}")
            out.append(f"OFFSET {_format_vec3(bone['offset'])}")
            out.append("SCALE 1.000000 1.000000 1.000000")
            out.append(f"X {_format_vec3(bone['rot'][0])}")
            out.append(f"Y {_format_vec3(bone['rot'][1])}")
            out.append(f"Z {_format_vec3(bone['rot'][2])}")
            out.append("")

    if notetrack_tail:
        out.extend(notetrack_tail)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")


def _normalize_thundergun_xanims_in_dir(xanim_dir):
    from compile_xanim_zone import parse_xanim_export

    # Weapon viewmodel in T6 expects animation channels to match weapon model rig,
    # not BO3 hand rig. Rebuild all vm_thunder_gun xanims to the thundergun model's
    # own joint set and static bind pose to avoid bone-index mismatch distortion.
    canonical_parts, bind_pose_by_name = _extract_model_bind_pose_from_view_glb()
    if THUNDERGUN_FORCE_ROOT_ONLY_XANIM:
        canonical_parts = ["tag_weapon_right"]
        bind_pose_by_name = {
            "tag_weapon_right": {
                "offset": [0.0, 0.0, 0.0],
                "rot": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            }
        }

    files = sorted(glob.glob(os.path.join(xanim_dir, "vm_thunder_gun_*.xanim_export")))
    if not files:
        raise RuntimeError(f"No staged vm_thunder_gun xanim exports found in {xanim_dir}")

    changed = 0
    for path in files:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            src_lines = f.read().splitlines()
        source_header_line = src_lines[0] if src_lines else ""
        notetrack_tail = _read_notetrack_tail(path)

        anim = parse_xanim_export(path)
        part_names = list(anim.get("parts", []))
        framerate = anim.get("framerate", 30) or 30
        frame_keys = sorted(anim.get("frames", {}).keys())
        frame_count = anim.get("numframes", 0)
        if frame_count <= 0:
            frame_count = (frame_keys[-1] + 1) if frame_keys else 1
        # Keep at least 2 frames so all consumers see a stable looping clip.
        frame_count = max(2, frame_count)
        frame_values_by_name = []
        for _ in range(frame_count):
            full_frame = {}
            for name in canonical_parts:
                pose = bind_pose_by_name[name]
                full_frame[name] = {
                    "offset": list(pose["offset"]),
                    "rot": [list(pose["rot"][0]), list(pose["rot"][1]), list(pose["rot"][2])],
                }
            frame_values_by_name.append(full_frame)

        needs_rewrite = (
            part_names != canonical_parts
            or anim.get("numparts", 0) != len(canonical_parts)
            or anim.get("numframes", 0) != frame_count
            or any(len(anim["frames"].get(f, {})) != len(canonical_parts) for f in range(anim.get("numframes", 0)))
        )
        if not needs_rewrite:
            continue

        _write_full_xanim(
            path=path,
            source_header_line=source_header_line,
            part_names=canonical_parts,
            framerate=framerate,
            frame_count=frame_count,
            frame_values_by_name=frame_values_by_name,
            notetrack_tail=notetrack_tail,
        )
        changed += 1

    return changed, len(files), len(canonical_parts)


def normalize_staged_thundergun_xanims():
    """
    Normalize staged vm_thunder_gun xanim exports.

    When THUNDERGUN_FORCE_ROOT_ONLY_XANIM is False, the original 133-bone
    animations (which already use T6 bone names) are kept as-is. The engine
    matches animation bones to model bones by name; unmatched bones are
    ignored for mesh deformation but still drive tags like tag_camera.
    """
    if not THUNDERGUN_FORCE_ROOT_ONLY_XANIM:
        print("  Skipping normalization (THUNDERGUN_FORCE_ROOT_ONLY_XANIM=False)")
        print("  Original 133-bone animations preserved with full motion data")
        return

    changed_root, total_root, part_count = _normalize_thundergun_xanims_in_dir(XANIM_EXPORT_DST_ROOT)
    changed_view, total_view, _ = _normalize_thundergun_xanims_in_dir(XANIM_EXPORT_DST_VIEWMODEL)
    print(
        "  Normalized staged xanim exports: "
        f"root {changed_root}/{total_root}, viewmodel {changed_view}/{total_view} "
        f"(full {part_count}-part set)"
    )


def ensure_thundergun_viewmodel_glb():
    """
    Guard against accidental regression to rigid/no-skin GLB variants.
    A no-skin variant causes severe first-person stretch/distortion in-game.
    """
    if not os.path.exists(THUNDERGUN_VIEW_GLB):
        raise RuntimeError(f"Missing viewmodel GLB: {THUNDERGUN_VIEW_GLB}")

    # Always reset from the original captured master before applying fixes.
    # This avoids cumulative transform drift from iterative experiments.
    if os.path.exists(THUNDERGUN_VIEW_GLB_MASTER):
        shutil.copy2(THUNDERGUN_VIEW_GLB_MASTER, THUNDERGUN_VIEW_GLB)
        print(f"  Reset viewmodel GLB from master: {os.path.basename(THUNDERGUN_VIEW_GLB_MASTER)}")

    with open(THUNDERGUN_VIEW_GLB, "rb") as f:
        header = f.read(20)
        if len(header) < 20 or header[:4] != b"glTF":
            raise RuntimeError(f"Invalid GLB header: {THUNDERGUN_VIEW_GLB}")
        json_len = struct.unpack("<I", header[12:16])[0]
        json_bytes = f.read(json_len)

    try:
        gltf = json.loads(json_bytes.decode("utf-8"))
    except Exception as ex:
        raise RuntimeError(f"Failed parsing GLB JSON: {THUNDERGUN_VIEW_GLB} ({ex})")

    node_count = len(gltf.get("nodes", []))
    skin_count = len(gltf.get("skins", []))
    if skin_count > 0:
        print(f"  Viewmodel GLB OK: nodes={node_count}, skins={skin_count}")
        return

    if not os.path.exists(THUNDERGUN_VIEW_GLB_FALLBACK):
        raise RuntimeError(
            f"Viewmodel GLB has skins=0 and no fallback found: {THUNDERGUN_VIEW_GLB_FALLBACK}"
        )

    shutil.copy2(THUNDERGUN_VIEW_GLB_FALLBACK, THUNDERGUN_VIEW_GLB)
    print(
        "  Replaced no-skin viewmodel GLB with fallback "
        f"({os.path.basename(THUNDERGUN_VIEW_GLB_FALLBACK)})"
    )
    # Keep fallback as-is; do not force rigid skinning.


def _load_glb_json_and_bin(path):
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 20 or data[:4] != b"glTF":
        raise RuntimeError(f"Invalid GLB header: {path}")
    json_len = struct.unpack_from("<I", data, 12)[0]
    json_type = data[16:20]
    if json_type != b"JSON":
        raise RuntimeError(f"Invalid GLB JSON chunk type: {path}")
    json_start = 20
    json_end = json_start + json_len
    gltf = json.loads(data[json_start:json_end].decode("utf-8"))
    bin_hdr = json_end
    if len(data) < bin_hdr + 8:
        raise RuntimeError(f"Missing GLB BIN chunk: {path}")
    bin_len = struct.unpack_from("<I", data, bin_hdr)[0]
    bin_type = data[bin_hdr + 4:bin_hdr + 8]
    if bin_type != b"BIN\x00":
        raise RuntimeError(f"Invalid GLB BIN chunk type: {path}")
    bin_start = bin_hdr + 8
    bin_end = bin_start + bin_len
    blob = bytearray(data[bin_start:bin_end])
    return gltf, blob


def _save_glb_json_and_bin(path, gltf, blob):
    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4:
        json_bytes += b" "
    bin_bytes = bytes(blob)
    while len(bin_bytes) % 4:
        bin_bytes += b"\x00"
    total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
    out = bytearray()
    out.extend(b"glTF")
    out.extend(struct.pack("<I", 2))
    out.extend(struct.pack("<I", total_len))
    out.extend(struct.pack("<I", len(json_bytes)))
    out.extend(b"JSON")
    out.extend(json_bytes)
    out.extend(struct.pack("<I", len(bin_bytes)))
    out.extend(b"BIN\x00")
    out.extend(bin_bytes)
    with open(path, "wb") as f:
        f.write(out)


def _pack_component_u(v, component_type):
    if component_type == 5121:
        return struct.pack("<B", max(0, min(255, int(v))))
    if component_type == 5123:
        return struct.pack("<H", max(0, min(65535, int(v))))
    if component_type == 5125:
        return struct.pack("<I", max(0, int(v)))
    raise RuntimeError(f"Unsupported JOINTS componentType: {component_type}")


def _pack_component_w(v, component_type):
    if component_type == 5126:
        return struct.pack("<f", float(v))
    if component_type == 5121:
        return struct.pack("<B", max(0, min(255, int(round(v * 255.0)))))
    if component_type == 5123:
        return struct.pack("<H", max(0, min(65535, int(round(v * 65535.0)))))
    raise RuntimeError(f"Unsupported WEIGHTS componentType: {component_type}")


def rigidify_thundergun_viewmodel_skin():
    """
    Force viewmodel vertices to bind to root weapon joint only.
    This prevents large rogue triangles from bad per-bone deformation when
    BO3-converted skin weights don't map cleanly to the T6 runtime.
    """
    gltf, blob = _load_glb_json_and_bin(THUNDERGUN_VIEW_GLB)
    skins = gltf.get("skins", [])
    if not skins:
        return

    nodes = gltf.get("nodes", [])
    skin = skins[0]
    joints = skin.get("joints", [])
    if not joints:
        return

    root_joint = 0
    root_joint_node = joints[0]
    for i, node_idx in enumerate(joints):
        name = nodes[node_idx].get("name", "") if 0 <= node_idx < len(nodes) else ""
        if name == "tag_weapon_right":
            root_joint = i
            root_joint_node = node_idx
            break

    # Keep the full joint list for loader compatibility, but force identity
    # bind behavior by dropping inverse bind matrices.
    skin["skeleton"] = root_joint_node
    if "inverseBindMatrices" in skin:
        del skin["inverseBindMatrices"]

    joint_acc = set()
    weight_acc = set()
    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            attrs = prim.get("attributes", {})
            if "JOINTS_0" in attrs:
                joint_acc.add(attrs["JOINTS_0"])
            if "WEIGHTS_0" in attrs:
                weight_acc.add(attrs["WEIGHTS_0"])

    accessors = gltf.get("accessors", [])
    buffer_views = gltf.get("bufferViews", [])

    for ai in sorted(joint_acc):
        a = accessors[ai]
        bv = buffer_views[a["bufferView"]]
        comps = 4
        ctype = a["componentType"]
        csize = {5121: 1, 5123: 2, 5125: 4}.get(ctype)
        if csize is None:
            raise RuntimeError(f"Unsupported JOINTS accessor componentType={ctype} at {ai}")
        stride = bv.get("byteStride") or (comps * csize)
        base = (bv.get("byteOffset") or 0) + (a.get("byteOffset") or 0)
        packed = _pack_component_u(root_joint, ctype) + _pack_component_u(0, ctype) + _pack_component_u(0, ctype) + _pack_component_u(0, ctype)
        for i in range(a["count"]):
            off = base + i * stride
            blob[off:off + len(packed)] = packed

    for ai in sorted(weight_acc):
        a = accessors[ai]
        bv = buffer_views[a["bufferView"]]
        comps = 4
        ctype = a["componentType"]
        csize = {5126: 4, 5121: 1, 5123: 2}.get(ctype)
        if csize is None:
            raise RuntimeError(f"Unsupported WEIGHTS accessor componentType={ctype} at {ai}")
        stride = bv.get("byteStride") or (comps * csize)
        base = (bv.get("byteOffset") or 0) + (a.get("byteOffset") or 0)
        packed = _pack_component_w(1.0, ctype) + _pack_component_w(0.0, ctype) + _pack_component_w(0.0, ctype) + _pack_component_w(0.0, ctype)
        for i in range(a["count"]):
            off = base + i * stride
            blob[off:off + len(packed)] = packed

    _save_glb_json_and_bin(THUNDERGUN_VIEW_GLB, gltf, blob)
    print(
        "  Rigidified thundergun view skin "
        f"(joint_accessors={len(joint_acc)}, weight_accessors={len(weight_acc)}, "
        f"root_joint={root_joint}, root_node={root_joint_node}, joints={len(skin.get('joints', []))})"
    )


def comment_out_lines(zone_path, patterns):
    """Comment out lines matching patterns. Returns original content."""
    with open(zone_path, 'r') as f:
        original = f.read()

    lines = original.split('\n')
    modified = []
    count = 0
    for line in lines:
        stripped = line.strip()
        if any(re.match(p, stripped) for p in patterns):
            modified.append(f"// PHASE1_DISABLED: {line}")
            count += 1
        else:
            modified.append(line)

    with open(zone_path, 'w') as f:
        f.write('\n'.join(modified))

    print(f"  Commented out {count} lines")
    return original


def restore_content(zone_path, original):
    """Restore original zone source content."""
    with open(zone_path, 'w') as f:
        f.write(original)
    print("  Restored original zone source")


def build_zone():
    """Run the OAT Linker."""
    result = subprocess.run(BASE_ARGS, capture_output=True, text=True, timeout=300)
    output = result.stdout + result.stderr
    print(output)
    return result.returncode == 0, output


def deploy_ff():
    """Copy the built .ff to the zone directory and mod directory."""
    src = os.path.join(OUTPUT_DIR, FF_NAME)
    deployed_any = False
    if DEPLOY_TO_BASE:
        dst = os.path.join(DEPLOY_DIR, FF_NAME)
        shutil.copy2(src, dst)
        size = os.path.getsize(dst)
        print(f"  Deployed {FF_NAME} to base zone/all ({size:,} bytes)")
        deployed_any = True
    if DEPLOY_TO_MOD:
        os.makedirs(DEPLOY_DIR_MOD, exist_ok=True)
        dst_mod = os.path.join(DEPLOY_DIR_MOD, FF_NAME)
        shutil.copy2(src, dst_mod)
        print(f"  Deployed {FF_NAME} to mod directory")
        deployed_any = True
    if not deployed_any:
        print(f"  WARNING: {FF_NAME} not deployed (DEPLOY_TO_BASE={DEPLOY_TO_BASE}, DEPLOY_TO_MOD={DEPLOY_TO_MOD})")


def deploy_ipak():
    """Copy the .ipak if it exists to zone directory and mod directory."""
    src = os.path.join(OUTPUT_DIR, IPAK_NAME)
    if os.path.exists(src):
        deployed_any = False
        if DEPLOY_TO_BASE:
            dst = os.path.join(DEPLOY_DIR, IPAK_NAME)
            shutil.copy2(src, dst)
            size = os.path.getsize(dst)
            print(f"  Deployed {IPAK_NAME} to base zone/all ({size:,} bytes)")
            deployed_any = True
        if DEPLOY_TO_MOD:
            os.makedirs(DEPLOY_DIR_MOD, exist_ok=True)
            dst_mod = os.path.join(DEPLOY_DIR_MOD, IPAK_NAME)
            shutil.copy2(src, dst_mod)
            print(f"  Deployed {IPAK_NAME} to mod directory")
            deployed_any = True
        if not deployed_any:
            print(f"  WARNING: {IPAK_NAME} build exists but deployment targets are disabled/missing")
        return deployed_any
    else:
        print(f"  WARNING: No {IPAK_NAME} found in output!")
        return False


def _ff_has_weapon_entries(ff_path, weapon_names):
    """Return True if Unlinker list output contains all required weapon aliases."""
    if not os.path.exists(ff_path):
        return False, f"missing ff: {ff_path}"
    if not os.path.exists(UNLINKER):
        return False, f"missing unlinker: {UNLINKER}"

    cmd = [UNLINKER, "--list", "--include-assets", "weapon", ff_path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        return False, f"unlinker failed rc={result.returncode}"

    out = (result.stdout or "") + (result.stderr or "")
    missing = []
    for wpn in weapon_names:
        needle = f"weapon, {wpn}"
        if needle not in out:
            missing.append(wpn)
    if missing:
        return False, "missing weapons: " + ",".join(missing)
    return True, "ok"


def _find_dumped_weapon_file(dump_root, weapon_name):
    """Locate a dumped weapon file from Unlinker output."""
    if not os.path.isdir(dump_root):
        return None

    target_names = {weapon_name, weapon_name + ".weapon"}
    for root, _, files in os.walk(dump_root):
        for name in files:
            if name in target_names:
                return os.path.join(root, name)
    return None


def _unlink_dump_weapons(ff_path, lane_tag):
    """Dump weapon assets from a deployed FF for field-level verification."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    dump_root = os.path.join(OUTPUT_DIR, "_runtime_verify", f"{lane_tag}_{stamp}")
    os.makedirs(dump_root, exist_ok=True)

    cmd = [UNLINKER, "--output-folder", dump_root, "--include-assets", "weapon", ff_path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        out = (result.stdout or "") + (result.stderr or "")
        reason = f"unlinker dump failed rc={result.returncode}"
        if out.strip():
            reason += f" ({out.strip().splitlines()[-1]})"
        return None, reason

    return dump_root, "ok"


def _load_expected_runtime_weapon_fields():
    """Load expected field set for runtime verification (manifest-first)."""
    expected = {}
    wanted = ["thundergun_zm", "thundergun_upgraded_zm"]
    if THUNDERGUN_TRUTH_ALIAS and THUNDERGUN_TRUTH_ALIAS not in wanted:
        wanted.append(THUNDERGUN_TRUTH_ALIAS)
    if THUNDERGUN_TRUTH_ALIAS_UPG and THUNDERGUN_TRUTH_ALIAS_UPG not in wanted:
        wanted.append(THUNDERGUN_TRUTH_ALIAS_UPG)
    fields = ("displayName", "parentWeaponName", "ammoName", "clipName", "gunModel", "worldModel")

    manifest = None
    if os.path.exists(TG_BUILD_MANIFEST_PATH):
        try:
            with open(TG_BUILD_MANIFEST_PATH, "r", encoding="utf-8", errors="replace") as f:
                manifest = json.load(f)
        except Exception:
            manifest = None

    for weapon_name in wanted:
        entry = {}
        if manifest and isinstance(manifest, dict):
            wf = manifest.get("weapondefs", {}).get(weapon_name, {})
            if isinstance(wf, dict):
                for key in fields:
                    if key in wf:
                        entry[key] = wf.get(key, "")

        # Fallback to current workspace weapondef if manifest missing/incomplete.
        if not entry:
            src = os.path.join(WORK_DIR, "weapons", weapon_name)
            wf = _read_weapon_manifest_fields(src)
            for key in fields:
                entry[key] = wf.get(key, "")

        expected[weapon_name] = entry

    return expected


def _verify_runtime_weapon_fields(ff_path, lane_tag, expected):
    """Verify dumped runtime weapondefs match expected key fields."""
    dump_root, dump_reason = _unlink_dump_weapons(ff_path, lane_tag)
    if not dump_root:
        return False, dump_reason

    mismatches = []
    for weapon_name, exp_map in expected.items():
        dumped_path = _find_dumped_weapon_file(dump_root, weapon_name)
        if not dumped_path:
            mismatches.append(f"{weapon_name}: dumped weapon file not found")
            continue

        dumped = _read_weapon_manifest_fields(dumped_path)
        for key, exp_val in exp_map.items():
            got_val = dumped.get(key, "")
            if got_val != exp_val:
                mismatches.append(
                    f"{weapon_name}.{key}: expected='{exp_val}' got='{got_val}'"
                )

    if mismatches:
        return False, "; ".join(mismatches[:6])
    return True, "ok"


def verify_deployed_runtime_ff():
    """Confirm deployed runtime FF(s) contain and correctly define truth weapon aliases."""
    required = ["thundergun_zm", "thundergun_upgraded_zm"]
    if THUNDERGUN_TRUTH_ALIAS and THUNDERGUN_TRUTH_ALIAS not in required:
        required.append(THUNDERGUN_TRUTH_ALIAS)
    if THUNDERGUN_TRUTH_ALIAS_UPG and THUNDERGUN_TRUTH_ALIAS_UPG not in required:
        required.append(THUNDERGUN_TRUTH_ALIAS_UPG)
    expected = _load_expected_runtime_weapon_fields()
    checks = []
    if DEPLOY_TO_BASE:
        checks.append(("base", os.path.join(DEPLOY_DIR, FF_NAME)))
    if DEPLOY_TO_MOD:
        checks.append(("mod", os.path.join(DEPLOY_DIR_MOD, FF_NAME)))

    all_ok = True
    for lane, ff_path in checks:
        alias_ok, alias_reason = _ff_has_weapon_entries(ff_path, required)
        if not alias_ok:
            print(f"  Runtime FF verify ({lane}): FAIL ({alias_reason})")
            all_ok = False
            continue

        fields_ok, fields_reason = _verify_runtime_weapon_fields(ff_path, lane, expected)
        if fields_ok:
            print(f"  Runtime FF verify ({lane}): PASS ({ff_path})")
        else:
            print(f"  Runtime FF verify ({lane}): FAIL ({fields_reason})")
            all_ok = False
    return all_ok


def _extract_weapon_field(raw_text, field_name):
    match = re.search(r"(?:^|\\)" + re.escape(field_name) + r"\\([^\\]*)", raw_text)
    if not match:
        return ""
    return match.group(1)


def _read_weapon_manifest_fields(path):
    entry = {
        "path": path,
        "exists": os.path.exists(path),
    }
    if not entry["exists"]:
        entry["error"] = "missing"
        return entry

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()
    except Exception as ex:
        entry["error"] = str(ex)
        return entry

    for field_name in (
        "displayName",
        "parentWeaponName",
        "ammoName",
        "clipName",
        "gunModel",
        "worldModel",
    ):
        entry[field_name] = _extract_weapon_field(raw, field_name)
    return entry


def _collect_tg_build_context():
    return {
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "effective": {
            "ROGUE_TG_PROFILE": THUNDERGUN_WEAPON_PROFILE,
            "ROGUE_TG_SEMANTICS": THUNDERGUN_WEAPON_SEMANTICS,
            "ROGUE_TG_MODEL_MODE": THUNDERGUN_WEAPON_MODEL_MODE,
            "ROGUE_TG_BASE_WEAPON": THUNDERGUN_BASE_WPN,
            "ROGUE_TG_AMMO_NAME": THUNDERGUN_FORCE_AMMO_NAME,
            "ROGUE_TG_CLIP_NAME": THUNDERGUN_FORCE_CLIP_NAME,
            "ROGUE_TG_HUD_ICON": THUNDERGUN_FORCE_HUD_ICON,
            "ROGUE_TG_KILL_ICON": THUNDERGUN_FORCE_KILL_ICON,
            "ROGUE_TG_CLEAR_CAMO": THUNDERGUN_CLEAR_CAMO,
            "ROGUE_TG_TRUTH_ALIAS": THUNDERGUN_TRUTH_ALIAS,
            "ROGUE_TG_TRUTH_ALIAS_UPG": THUNDERGUN_TRUTH_ALIAS_UPG,
        },
    }


def _write_tg_build_manifest(manifest):
    os.makedirs(os.path.dirname(TG_BUILD_MANIFEST_PATH), exist_ok=True)
    with open(TG_BUILD_MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    print(f"  Wrote TG build manifest: {TG_BUILD_MANIFEST_PATH}")


def _append_tg_weapon_manifest_and_guardrails(manifest):
    weapon_paths = {
        "thundergun_zm": os.path.join(WORK_DIR, "weapons", "thundergun_zm"),
        "thundergun_upgraded_zm": os.path.join(WORK_DIR, "weapons", "thundergun_upgraded_zm"),
        "rogue_thundergun_zm": os.path.join(WORK_DIR, "weapons", "rogue_thundergun_zm"),
        "rogue_thundergun_upgraded_zm": os.path.join(WORK_DIR, "weapons", "rogue_thundergun_upgraded_zm"),
        "rogue_probe_wpn_zm": os.path.join(WORK_DIR, "weapons", "rogue_probe_wpn_zm"),
        "rogue_probe_wpn_upgraded_zm": os.path.join(WORK_DIR, "weapons", "rogue_probe_wpn_upgraded_zm"),
    }
    if THUNDERGUN_TRUTH_ALIAS:
        weapon_paths[f"truth_alias::{THUNDERGUN_TRUTH_ALIAS}"] = os.path.join(
            WORK_DIR, "weapons", THUNDERGUN_TRUTH_ALIAS
        )
    if THUNDERGUN_TRUTH_ALIAS_UPG:
        weapon_paths[f"truth_alias::{THUNDERGUN_TRUTH_ALIAS_UPG}"] = os.path.join(
            WORK_DIR, "weapons", THUNDERGUN_TRUTH_ALIAS_UPG
        )

    manifest["weapondefs"] = {}
    guardrail_errors = []
    reject_parent_names = {"type95"}

    for name, path in weapon_paths.items():
        entry = _read_weapon_manifest_fields(path)
        manifest["weapondefs"][name] = entry
        if not entry.get("exists"):
            guardrail_errors.append(f"{name}: missing generated weapon file")
            continue
        parent_name = (entry.get("parentWeaponName") or "").strip().lower()
        if parent_name in reject_parent_names:
            guardrail_errors.append(
                f"{name}: parentWeaponName={entry.get('parentWeaponName')} rejected in proxy cycle"
            )

    manifest["guardrails"] = {
        "proxy_cycle_reject_parentWeaponName": sorted(reject_parent_names),
        "ok": len(guardrail_errors) == 0,
        "errors": guardrail_errors,
    }
    return len(guardrail_errors) == 0


def _extract_mod_build_id(path):
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception:
        return ""
    match = re.search(r'rogue_log_event\(\s*"build"\s*,\s*"id=([^"]+)"\s*\)', text)
    if not match:
        return ""
    return match.group(1)


def _file_sha256(path):
    if not path or not os.path.exists(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def prepare_thundergun_weapondefs():
    """Rebuild rogue thundergun weapondefs before linking."""
    if not os.path.exists(THUNDERGUN_WEAPON_BUILDER):
        print(f"  WARNING: missing thundergun weapon builder: {THUNDERGUN_WEAPON_BUILDER}")
        return False

    cmd = [
        sys.executable,
        THUNDERGUN_WEAPON_BUILDER,
        "--profile", THUNDERGUN_WEAPON_PROFILE,
        "--semantics", THUNDERGUN_WEAPON_SEMANTICS,
        "--model-mode", THUNDERGUN_WEAPON_MODEL_MODE,
        "--base-weapon-path", THUNDERGUN_BASE_WPN,
    ]
    if THUNDERGUN_FORCE_AMMO_NAME:
        cmd.extend(["--ammo-name", THUNDERGUN_FORCE_AMMO_NAME])
    if THUNDERGUN_FORCE_CLIP_NAME:
        cmd.extend(["--clip-name", THUNDERGUN_FORCE_CLIP_NAME])
    if THUNDERGUN_FORCE_HUD_ICON:
        cmd.extend(["--hud-icon", THUNDERGUN_FORCE_HUD_ICON])
    if THUNDERGUN_FORCE_KILL_ICON:
        cmd.extend(["--kill-icon", THUNDERGUN_FORCE_KILL_ICON])
    if THUNDERGUN_CLEAR_CAMO:
        cmd.append("--clear-camo")
    if THUNDERGUN_TRUTH_ALIAS:
        cmd.extend(["--truth-alias", THUNDERGUN_TRUTH_ALIAS])
    if THUNDERGUN_TRUTH_ALIAS_UPG:
        cmd.extend(["--truth-alias-upg", THUNDERGUN_TRUTH_ALIAS_UPG])

    manifest = _collect_tg_build_context()
    manifest["builder_cmd"] = cmd
    _write_tg_build_manifest(manifest)
    print(
        "Prep: rebuilding thundergun weapondefs "
        f"(profile={THUNDERGUN_WEAPON_PROFILE}, semantics={THUNDERGUN_WEAPON_SEMANTICS}, "
        f"model_mode={THUNDERGUN_WEAPON_MODEL_MODE}, base={THUNDERGUN_BASE_WPN})..."
    )
    result = subprocess.run(cmd, timeout=180)
    manifest["builder_returncode"] = result.returncode
    manifest["builder_ok"] = result.returncode == 0
    if result.returncode != 0:
        _write_tg_build_manifest(manifest)
        return False

    guardrails_ok = _append_tg_weapon_manifest_and_guardrails(manifest)
    _write_tg_build_manifest(manifest)
    if not guardrails_ok:
        print("ERROR: TG weapon guardrail failure:")
        for err in manifest.get("guardrails", {}).get("errors", []):
            print(f"  - {err}")
        return False
    return True


def ensure_truth_alias_zone_entries():
    """Ensure zone source explicitly includes truth alias weapon assets."""
    aliases = []
    if THUNDERGUN_TRUTH_ALIAS:
        aliases.append(THUNDERGUN_TRUTH_ALIAS)
    if THUNDERGUN_TRUTH_ALIAS_UPG:
        aliases.append(THUNDERGUN_TRUTH_ALIAS_UPG)
    aliases = [a for a in aliases if a]
    if not aliases:
        return True

    if not os.path.exists(ZONE_SOURCE):
        print(f"ERROR: zone source missing: {ZONE_SOURCE}")
        return False

    with open(ZONE_SOURCE, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    changed = 0
    for alias in aliases:
        needle = f"weapon,{alias}"
        if not any(line.strip() == needle for line in lines):
            lines.append(needle)
            changed += 1

    if changed:
        with open(ZONE_SOURCE, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Prep: appended {changed} truth alias weapon entries to zone source.")
    else:
        print("Prep: truth alias weapon entries already present in zone source.")
    return True


def sync_mod_runtime_script():
    """Keep active Plutonium storage script in sync with workspace mod script."""
    mod_script_src = resolve_mod_script_source()
    if not os.path.exists(mod_script_src):
        print(f"  WARNING: missing mod script source: {mod_script_src}")
        return False

    os.makedirs(MOD_SCRIPT_DST_DIR, exist_ok=True)
    dst = os.path.join(MOD_SCRIPT_DST_DIR, os.path.basename(mod_script_src))
    shutil.copy2(mod_script_src, dst)
    print(f"  Synced runtime script: {dst} (src={mod_script_src})")
    return True


def ensure_mod_runtime_script_alignment():
    """Require runtime script content hash to match workspace script before test/build loop."""
    mod_script_src = resolve_mod_script_source()
    runtime_path = os.path.join(MOD_SCRIPT_DST_DIR, os.path.basename(mod_script_src))
    workspace_id = _extract_mod_build_id(mod_script_src)
    runtime_id = _extract_mod_build_id(runtime_path)
    workspace_hash = _file_sha256(mod_script_src)
    runtime_hash = _file_sha256(runtime_path)

    if workspace_hash and runtime_hash and workspace_hash == runtime_hash:
        print(f"  Script hash aligned: {workspace_hash[:12]} (build_id={workspace_id or '<missing>'})")
        return True

    print(
        "  Script mismatch between workspace/runtime copy "
        f"(workspace_id={workspace_id or '<missing>'}, runtime_id={runtime_id or '<missing>'}, "
        f"workspace_hash={workspace_hash[:12] if workspace_hash else '<missing>'}, "
        f"runtime_hash={runtime_hash[:12] if runtime_hash else '<missing>'}, src={mod_script_src})."
    )
    if not sync_mod_runtime_script():
        return False

    runtime_id_after = _extract_mod_build_id(runtime_path)
    runtime_hash_after = _file_sha256(runtime_path)
    if workspace_hash and runtime_hash_after == workspace_hash:
        print(
            f"  Script hash aligned after sync: {workspace_hash[:12]} "
            f"(build_id={workspace_id or '<missing>'})"
        )
        return True

    print(
        "ERROR: runtime script still mismatched after sync "
        f"(workspace_id={workspace_id or '<missing>'}, runtime_id={runtime_id_after or '<missing>'}, "
        f"workspace_hash={workspace_hash[:12] if workspace_hash else '<missing>'}, "
        f"runtime_hash={runtime_hash_after[:12] if runtime_hash_after else '<missing>'})"
    )
    return False


def enforce_deploy_lane():
    """Ensure at least one deploy target is active and print effective lane."""
    if not DEPLOY_TO_BASE and not DEPLOY_TO_MOD:
        print("ERROR: both deploy targets are disabled (ROGUE_DEPLOY_TO_BASE=0 and ROGUE_DEPLOY_TO_MOD=0).")
        return False
    print(
        "Deploy lane: "
        f"base={'on' if DEPLOY_TO_BASE else 'off'}, "
        f"mod={'on' if DEPLOY_TO_MOD else 'off'}"
    )
    return True


def run_runtime_lane_reset_sequence():
    """Enforce clean -> dev runtime lane before each build iteration."""
    if not os.path.exists(RUNTIME_RESET_SCRIPT):
        print(f"ERROR: runtime reset script missing: {RUNTIME_RESET_SCRIPT}")
        return False

    print("Prep: reset order is clean -> dev -> build -> deploy (clean restores base lane FF).")

    steps = [
        ("clean", [RUNTIME_RESET_SCRIPT, "-Mode", "clean"]),
        ("dev", [RUNTIME_RESET_SCRIPT, "-Mode", "dev", "-DevMod", "zm_roguelike_panzer"]),
    ]
    for lane_name, tail in steps:
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", *tail]
        print(f"Prep: runtime lane reset -> {lane_name}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        output = (result.stdout or "") + (result.stderr or "")
        if output.strip():
            print(output)
        if result.returncode != 0:
            print(f"ERROR: runtime reset step failed ({lane_name}), exit={result.returncode}")
            return False
    return True


def snapshot_live_ff():
    """Snapshot currently deployed FFs so failures can roll back cleanly."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    snap_dir = os.path.join(OUTPUT_DIR, "_live_snapshots")
    os.makedirs(snap_dir, exist_ok=True)

    main_src = os.path.join(DEPLOY_DIR, FF_NAME) if DEPLOY_TO_BASE else None
    mod_src = os.path.join(DEPLOY_DIR_MOD, FF_NAME) if (DEPLOY_TO_MOD and os.path.isdir(DEPLOY_DIR_MOD)) else None
    main_snap = None
    mod_snap = None

    if main_src and os.path.exists(main_src):
        main_snap = os.path.join(snap_dir, f"{stamp}_zone_all_{FF_NAME}")
        shutil.copy2(main_src, main_snap)
        print(f"  Snapshot main FF: {main_snap}")
    if mod_src and os.path.exists(mod_src):
        mod_snap = os.path.join(snap_dir, f"{stamp}_mod_{FF_NAME}")
        shutil.copy2(mod_src, mod_snap)
        print(f"  Snapshot mod FF:  {mod_snap}")

    return main_snap, mod_snap


def restore_live_ff(main_snap, mod_snap):
    """Restore deployed FFs from snapshots."""
    main_dst = os.path.join(DEPLOY_DIR, FF_NAME)
    if DEPLOY_TO_BASE and main_snap and os.path.exists(main_snap):
        shutil.copy2(main_snap, main_dst)
        print(f"  Restored main FF from snapshot")

    if DEPLOY_TO_MOD and os.path.isdir(DEPLOY_DIR_MOD):
        mod_dst = os.path.join(DEPLOY_DIR_MOD, FF_NAME)
        if mod_snap and os.path.exists(mod_snap):
            shutil.copy2(mod_snap, mod_dst)
            print(f"  Restored mod FF from snapshot")


def phase3_patch_xanims():
    """Phase 3: Binary-patch empty XAnimParts stubs with real animation data."""
    input_ff = os.path.join(OUTPUT_DIR, FF_NAME)
    zone_name = os.path.splitext(FF_NAME)[0]
    patcher_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patch_zone_xanims.py")

    if not os.path.exists(patcher_script):
        print(f"  ERROR: Patcher script not found: {patcher_script}")
        return False
    if not os.path.exists(input_ff):
        print(f"  ERROR: Zone file not found: {input_ff}")
        return False

    # Find xanim_export files (prefer staged directory)
    xanim_dir = XANIM_EXPORT_DST_ROOT
    test_pattern = os.path.join(xanim_dir, XANIM_EXPORT_GLOB)
    if not glob.glob(test_pattern):
        # Try primary source
        xanim_dir = XANIM_EXPORT_SRC_PRIMARY
        test_pattern = os.path.join(xanim_dir, XANIM_EXPORT_GLOB)
        if not glob.glob(test_pattern):
            print(f"  ERROR: No xanim_export files found in {XANIM_EXPORT_DST_ROOT}")
            print(f"         or {XANIM_EXPORT_SRC_PRIMARY}")
            return False

    cmd = [
        sys.executable, patcher_script,
        "--input-ff", input_ff,
        "--zone-name", zone_name,
        "--xanim-dir", xanim_dir,
        "--xanim-pattern", XANIM_EXPORT_GLOB,
        "--name-prefix", "vm_thunder_gun_",
    ]
    if PHASE3_PATCH_ONLY:
        cmd.extend(["--patch-only", *PHASE3_PATCH_ONLY])
        print(f"  Patch-only set: {len(PHASE3_PATCH_ONLY)} core thundergun anims")
    print(f"  Running: {' '.join(cmd[-6:])}")
    result = subprocess.run(cmd, timeout=600)
    return result.returncode == 0


def main():
    if not enforce_deploy_lane():
        return False
    if not run_runtime_lane_reset_sequence():
        return False
    if not ensure_mod_runtime_script_alignment():
        return False
    if not prepare_thundergun_weapondefs():
        return False
    if not ensure_truth_alias_zone_entries():
        return False
    if not ensure_core_transit_integrity():
        return False
    if not ensure_critical_text_scripts():
        return False
    if not ensure_mod_runtime_script_alignment():
        return False

    live_main_snap, live_mod_snap = snapshot_live_ff()

    load_candidates = []
    if USE_SO_SURVIVAL_LOAD_BASELINE:
        if ensure_pristine_baseline_copy():
            print(f"Prep: refreshed pristine baseline copy: {SO_SURVIVAL_LOAD_FF_PRISTINE_COPY}")
        else:
            print("Prep: pristine baseline copy unavailable (missing .ff.vanilla_save)")

        raw_candidates = []
        if SO_SURVIVAL_LOAD_FF_FIXED and os.path.exists(SO_SURVIVAL_LOAD_FF_FIXED):
            raw_candidates.append(os.path.abspath(SO_SURVIVAL_LOAD_FF_FIXED))
        raw_candidates.extend(_collect_load_ff_candidates())

        # De-dup while preserving order.
        seen = set()
        deduped = []
        for cand in raw_candidates:
            ap = os.path.abspath(cand)
            if ap not in seen:
                seen.add(ap)
                deduped.append(ap)

        load_candidates = []
        fixed_ap = os.path.abspath(SO_SURVIVAL_LOAD_FF_FIXED) if SO_SURVIVAL_LOAD_FF_FIXED else None
        if fixed_ap and os.path.exists(fixed_ap):
            # Keep the pinned baseline first even if strict decrypt-based checks reject it.
            # Some historical but linker-loadable baselines fail offline contamination probes.
            load_candidates.append(fixed_ap)

        for cand in deduped:
            ap = os.path.abspath(cand)
            if ap in load_candidates:
                continue
            if _baseline_is_contaminated(ap):
                continue
            load_candidates.append(ap)
        if not load_candidates:
            print("ERROR: No usable baseline FF candidate found.")
            restore_live_ff(live_main_snap, live_mod_snap)
            return False

        _set_so_survival_load_ff(load_candidates[0])
        print(f"Prep: baseline FF for linker: {SO_SURVIVAL_LOAD_FF}")
    else:
        print("Prep: so_zsurvival baseline --load disabled (building against stock shared FF loads only)")
    if USE_CUSTOM_XANIM_FF:
        print("Prep: building standalone custom xanim FF...")
        if not build_custom_xanim_ff():
            return False
        if not verify_custom_xanim_ff():
            return False
    maybe_add_custom_xanim_load()

    print("Prep: verifying thundergun viewmodel GLB...")
    ensure_thundergun_viewmodel_glb()
    # Keep xanim inputs deterministic between runs.
    print("\nPrep: staging thundergun xanim exports...")
    stage_thundergun_xanim_exports()

    print("=" * 60)
    print("PHASE 1: Build clean zone WITHOUT thundergun images")
    print("=" * 60)

    # Comment out thundergun assets
    print("\nStep 1.1: Commenting out thundergun assets...")
    original = comment_out_lines(ZONE_SOURCE, COMMENT_PATTERNS)

    # Build
    print("\nStep 1.2: Building clean zone...")
    success, output = build_zone()
    if USE_SO_SURVIVAL_LOAD_BASELINE and (not success) and _is_load_ff_failure(output):
        print("  Detected baseline load FF failure; trying fallback candidates...")
        for cand in load_candidates[1:]:
            if os.path.abspath(cand) == os.path.abspath(SO_SURVIVAL_LOAD_FF):
                continue
            _set_so_survival_load_ff(cand)
            print(f"  Retrying with baseline FF: {cand}")
            success, output = build_zone()
            if success:
                print(f"  Baseline FF fallback selected: {cand}")
                break
            if not _is_load_ff_failure(output):
                break
    if not success:
        print("ERROR: Phase 1 build failed!")
        restore_content(ZONE_SOURCE, original)
        return False

    # Deploy clean zone
    print("\nStep 1.3: Deploying clean zone...")
    deploy_ff()
    phase1_ff = os.path.join(OUTPUT_DIR, FF_NAME)
    phase1_size = os.path.getsize(phase1_ff) if os.path.exists(phase1_ff) else -1

    # Restore zone source
    print("\nStep 1.4: Restoring zone source...")
    restore_content(ZONE_SOURCE, original)

    print("\n" + "=" * 60)
    print("PHASE 2: Build full zone WITH thundergun images")
    print("=" * 60)

    # Build with images
    print("\nStep 2.1: Building full zone (OAT should read IWI files)...")
    success, output = build_zone()
    if not success:
        print("ERROR: Phase 2 build failed!")
        restore_live_ff(live_main_snap, live_mod_snap)
        return False
    phase2_ff = os.path.join(OUTPUT_DIR, FF_NAME)
    phase2_size = os.path.getsize(phase2_ff) if os.path.exists(phase2_ff) else -1
    print(f"  Phase size check: phase1={phase1_size:,} phase2={phase2_size:,}")
    if phase1_size > 0 and phase2_size > 0 and phase2_size <= phase1_size:
        print(
            "ERROR: Phase 2 FF is not larger than phase 1 FF; "
            "thundergun assets likely not present in final output."
        )
        restore_live_ff(live_main_snap, live_mod_snap)
        return False

    if USE_CUSTOM_XANIM_FF:
        print("\n" + "=" * 60)
        print("PHASE 3: Skipped (using standalone custom xanim FF via --load)")
        print("=" * 60)
        patch_ok = True
    elif not ENABLE_PHASE3_PATCH:
        print("\n" + "=" * 60)
        print("PHASE 3: Skipped (stable checkpoint: no xanim binary patching)")
        print("=" * 60)
        patch_ok = True
    else:
        print("\n" + "=" * 60)
        print("PHASE 3: Patch empty XAnimParts stubs with real animation data")
        print("=" * 60)
        print("\nStep 3.1: Patching zone xanims...")
        patch_ok = phase3_patch_xanims()

    # Preflight before deployment.
    candidate_ff = os.path.join(OUTPUT_DIR, FF_NAME)
    print("\nPreflight integrity check...")
    if not run_preflight(candidate_ff, os.path.splitext(FF_NAME)[0]):
        print("\nERROR: Build output rejected by preflight.")
        restore_live_ff(live_main_snap, live_mod_snap)
        return False

    # Deploy
    print("\nDeploying zone...")
    deploy_ff()
    if not verify_deployed_runtime_ff():
        print("ERROR: deployed runtime FF is missing required thundergun weapon aliases.")
        restore_live_ff(live_main_snap, live_mod_snap)
        return False
    has_ipak = deploy_ipak()

    # Check output directory for all files
    print("\nChecking output directory...")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        path = os.path.join(OUTPUT_DIR, f)
        size = os.path.getsize(path)
        print(f"  {f}: {size:,} bytes")

    if has_ipak and patch_ok:
        print("\n SUCCESS: Zone + IPak built, patched, and deployed!")
    elif has_ipak:
        print("\n PARTIAL: Zone + IPak built and deployed (xanims NOT patched)")
    else:
        print("\n WARNING: Zone built but NO IPak generated.")

    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
