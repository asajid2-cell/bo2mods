#!/usr/bin/env python3
"""Build and deploy a donor-shell Apothicon Servant probe for BO2.

This intentionally keeps the scope narrow:
- a stock BO2 donor shell that the engine already recognizes
- a BO3 IDG-derived first-person gun model
- donor anims by default, with BO3 anims kept opt-in for later tests

It does not attempt full gameplay parity yet. The goal is only to prove
whether a safe donor shell can carry the Servant content lane.

Current proof mode intentionally uses absurd scalar values so runtime logs can
prove whether the override won before any visual debugging:
- clipSize=7
- maxAmmo=77
- fireTime=50 ms
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageEnhance


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "_build" / "bo3_rev_idg_probe"
OUTPUT = WORK / "output"
MODEL_EXPORT_DIR = WORK / "model_export"
XMODEL_DIR = WORK / "xmodel"
MATERIALS_DIR = WORK / "materials"
IMAGES_DIR = WORK / "images"
WEAPONS_DIR = WORK / "weapons"
XANIM_DIR = WORK / "xanim_export" / "viewmodel"
ZONE_SOURCE_DIR = WORK / "zone_source"
REPORT_PATH = WORK / "build_report.json"
ZONE_RAW_ROOT = WORK / "zone_raw" / "so_zsurvival_zm_transit"
IDG_SURFACE_BUNDLE_ROOT = WORK / "idg_surface_bundle"
IDG_SURFACE_PROJECT_ROOT = WORK / "_tmp_idg_surface_project"
IDG_SURFACE_PROJECT_NAME = "bo3_rev_idg_surface"
IDG_SURFACE_TRANSLATION_REPORT = IDG_SURFACE_BUNDLE_ROOT / "material_translation_report.json"
IDG_SURFACE_BUNDLE_REPORT = IDG_SURFACE_BUNDLE_ROOT / "t7_bundle_report.json"
IDG_SURFACE_BLENDER_REPORT = IDG_SURFACE_BUNDLE_ROOT / "blender_material_report.json"

MOD_NAME = "bo3_rev"
MOD_ZONE_NAME = "mod"
MOD_LOAD_ZONE_NAME = "mod_load"
RUNTIME_ZONE_NAME = "so_zsurvival_zm_transit"
RUNTIME_FF_NAME = f"{RUNTIME_ZONE_NAME}.ff"
RUNTIME_IPAK_NAME = f"{RUNTIME_ZONE_NAME}.ipak"

SCRIPT_TEMPLATE = ROOT / "mods" / MOD_NAME / "scripts" / "mod_i_am_mod.gsc.in"
SCRIPT_OUTPUT = ROOT / "mods" / MOD_NAME / "scripts" / "mod_i_am_mod.gsc"

PROBE_SHELL_WEAPON = os.environ.get("ROGUE_PROBE_SHELL", "mg08_zm").strip() or "mg08_zm"
PROBE_STARTER_WEAPON = os.environ.get("ROGUE_STARTER_WEAPON", "m1911_zm").strip() or "m1911_zm"
GUN_MODEL_MODE = os.environ.get("ROGUE_GUN_MODEL_MODE", "custom").strip().lower() or "custom"
GUN_MODEL_LITERAL = os.environ.get("ROGUE_GUN_MODEL_LITERAL", "").strip()
MODEL_ASSET_BASE = os.environ.get("ROGUE_MODEL_ASSET_BASE", "bo3_rev_v2_idg_view").strip() or "bo3_rev_v2_idg_view"
IDG_VIEW_GLB_OVERRIDE = os.environ.get("ROGUE_IDG_VIEW_GLB", "").strip()

BUILD_TAG_SEED = "|".join(
    [
        PROBE_SHELL_WEAPON,
        PROBE_STARTER_WEAPON,
        GUN_MODEL_MODE,
        GUN_MODEL_LITERAL,
        IDG_VIEW_GLB_OVERRIDE,
        "bo3" if os.environ.get("ROGUE_USE_BO3_IDG_ANIMS", "1") not in ("0", "false", "False") else "donor",
        "lowhand" if os.environ.get("ROGUE_FORCE_LOW_HANDMODEL", "0") not in ("0", "false", "False") else "basehand",
    ]
)
BUILD_TAG_PREFIX = datetime.now(timezone.utc).strftime("%m%d%H%M%S")
BUILD_TAG = os.environ.get("ROGUE_BUILD_TAG", "").strip() or f"{BUILD_TAG_PREFIX}_{hashlib.sha1(BUILD_TAG_SEED.encode('utf-8')).hexdigest()[:6]}"
MODEL_ASSET = f"{MODEL_ASSET_BASE}_{BUILD_TAG}" if GUN_MODEL_MODE == "custom" else MODEL_ASSET_BASE
VIEWHANDS_ASSET = "bo3_rev_idg_viewhands"
BRIDGE_VIEWHANDS_ASSET = "bo3_rev_bridge_viewhands"
WEAPON_ASSET = PROBE_SHELL_WEAPON
MODEL_MATERIALS = [
    "mtl_wpn_t7_zmb_zod_idg_bone",
    "mtl_wpn_t7_zmb_zod_idg_body",
    "mtl_wpn_t7_zmb_zod_idg_eyes",
    "mtl_wpn_t7_zmb_zod_idg_sacks",
    "mtl_wpn_t7_zmb_zod_idg_tentacles",
]
IDG_SURFACE_IMAGE_ROOT = Path(
    r"Z:\Games\T7 Assets V2.5 (2)\T7 Assets V2.5\T7 Assets\model_export\_midgetblaster\weapons\t7\_images"
)
MATERIAL_TRANSLATOR = ROOT / "tools" / "asset_port_pipeline" / "translate_bo3_materials_to_bo2.py"
TEXCONV = ROOT / "tools" / "texconv.exe"
IDG_LIT_TECHSET = "mc_lit_sm_r0c0n0s0o0_3z86zq2z"
IDG_UNLIT_TECHSET = "mc_sw4_3d_model_unlit_cheap_zombie_eyes_jq3e7eqw"
IDG_LIT_TEMPLATE = ROOT / "zone_dump" / "zone_raw" / "zm_tomb" / "materials" / "mc" / "mtl_t6_wpn_zmb_mg08.json"
IDG_UNLIT_TEMPLATE = ROOT / "zone_dump" / "zone_raw" / "zm_tomb" / "materials" / "mc" / "mtl_c_zom_mech_head_unlit.json"
IDG_EMISSIVE_FX_TEMPLATE = ROOT / "zone_dump" / "zone_raw" / "zm_tomb" / "materials" / "gfx_fxt_env_dust_mote.json"
IDG_SURFACE_IMAGE_FILES = {
    "i_wpn_t7_zmb_zod_idg_ammo_c": "i_wpn_t7_zmb_zod_idg_ammo_c.png",
    "i_wpn_t7_zmb_zod_idg_ammo_n": "i_wpn_t7_zmb_zod_idg_ammo_n.png",
    "i_wpn_t7_zmb_zod_idg_ammo_o": "i_wpn_t7_zmb_zod_idg_ammo_o.png",
    "i_wpn_t7_zmb_zod_idg_ammo_s": "i_wpn_t7_zmb_zod_idg_ammo_s.png",
    "i_wpn_t7_zmb_zod_tentacle_ambient_c": "i_wpn_t7_zmb_zod_tentacle_ambient_c.png",
    "i_wpn_t7_zmb_zod_tentacle_ambient_g": "i_wpn_t7_zmb_zod_tentacle_ambient_g.png",
    "i_wpn_t7_zmb_zod_tentacle_ambient_n": "i_wpn_t7_zmb_zod_tentacle_ambient_n.png",
    "i_wpn_t7_zmb_zod_tentacle_ambient_t": "i_wpn_t7_zmb_zod_tentacle_ambient_t.png",
    "i_wpn_t7_zmb_zod_tentacle_claw_c": "i_wpn_t7_zmb_zod_tentacle_claw_c.png",
    "i_wpn_t7_zmb_zod_tentacle_claw_g": "i_wpn_t7_zmb_zod_tentacle_claw_g.png",
    "i_wpn_t7_zmb_zod_tentacle_claw_mask": "i_wpn_t7_zmb_zod_tentacle_claw_mask.png",
    "i_wpn_t7_zmb_zod_tentacle_claw_n": "i_wpn_t7_zmb_zod_tentacle_claw_n.png",
    "i_wpn_t7_zmb_zod_tentacle_claw_o": "i_wpn_t7_zmb_zod_tentacle_claw_o.png",
    "i_wpn_t7_zmb_zod_tentacle_electric_c": "i_wpn_t7_zmb_zod_tentacle_electric_c.png",
    "i_wpn_t7_zmb_zod_tentacle_electric_e": "i_wpn_t7_zmb_zod_tentacle_electric_e.png",
    "i_wpn_t7_zmb_zod_tentacle_electric_g": "i_wpn_t7_zmb_zod_tentacle_electric_g.png",
    "i_wpn_t7_zmb_zod_tentacle_electric_n": "i_wpn_t7_zmb_zod_tentacle_electric_n.png",
    "i_wpn_t7_zmb_zod_tentacle_electric_r": "i_wpn_t7_zmb_zod_tentacle_electric_r.png",
}
IDG_SURFACE_MATERIAL_SLOTS = {
    "mtl_wpn_t7_zmb_zod_idg_bone": {
        "colorMap": "i_wpn_t7_zmb_zod_tentacle_claw_c",
        "normalMap": "i_wpn_t7_zmb_zod_tentacle_claw_n",
        "specColorMap": "i_wpn_t7_zmb_zod_tentacle_claw_g",
        "occlusionMap": "i_wpn_t7_zmb_zod_tentacle_claw_o",
        "camoMaskMap": "i_wpn_t7_zmb_zod_tentacle_claw_mask",
    },
    "mtl_wpn_t7_zmb_zod_idg_body": {
        "colorMap": "i_wpn_t7_zmb_zod_tentacle_ambient_c",
        "normalMap": "i_wpn_t7_zmb_zod_tentacle_ambient_n",
        "specColorMap": "i_wpn_t7_zmb_zod_tentacle_ambient_g",
        "camoMaskMap": "i_wpn_t7_zmb_zod_tentacle_ambient_t",
    },
    "mtl_wpn_t7_zmb_zod_idg_eyes": {
        "colorMap": "i_wpn_t7_zmb_zod_tentacle_electric_e",
    },
    "mtl_wpn_t7_zmb_zod_idg_sacks": {
        "colorMap": "i_wpn_t7_zmb_zod_idg_ammo_c",
        "normalMap": "i_wpn_t7_zmb_zod_idg_ammo_n",
        "specColorMap": "i_wpn_t7_zmb_zod_idg_ammo_s",
        "occlusionMap": "i_wpn_t7_zmb_zod_idg_ammo_o",
    },
    "mtl_wpn_t7_zmb_zod_idg_tentacles": {
        "colorMap": "i_wpn_t7_zmb_zod_tentacle_ambient_c",
        "normalMap": "i_wpn_t7_zmb_zod_tentacle_ambient_n",
        "specColorMap": "i_wpn_t7_zmb_zod_tentacle_ambient_g",
        "camoMaskMap": "i_wpn_t7_zmb_zod_tentacle_ambient_t",
    },
}
IDG_SURFACE_FALLBACK_SLOTS = {
    "colorMap": "i_wpn_t7_zmb_zod_tentacle_ambient_c",
    "normalMap": "i_wpn_t7_zmb_zod_tentacle_ambient_n",
    "specColorMap": "i_wpn_t7_zmb_zod_tentacle_ambient_g",
}
STAGED_IMAGE_NAMES: list[str] = []

IWI_HEADER_SIZE = 64
IWI_MAGIC = b"IWi"
IWI_VERSION = 0x1B
IWI_FORMAT_DXT5 = 0x0D
IWI_FORMAT_DXN = 0x0E
DDS_MAGIC = b"DDS "
DDS_HEADER_SIZE = 124
DXGI_FORMAT_BC5_UNORM = 83
DXGI_FORMAT_BC5_SNORM = 84

IDG_SPEC_RGB_SCALE = 0.12
IDG_SPEC_ALPHA_SCALE = 0.06
IDG_DIFFUSE_GRADE_DEFAULT = {
    "brightness": 0.95,
    "contrast": 1.18,
    "saturation": 1.55,
    "red_scale": 1.08,
    "green_scale": 1.00,
    "blue_scale": 0.90,
}
IDG_DIFFUSE_GRADE_BY_IMAGE = {
    "i_wpn_t7_zmb_zod_tentacle_ambient_c": {
        "brightness": 0.94,
        "contrast": 1.20,
        "saturation": 1.65,
        "red_scale": 1.10,
        "green_scale": 1.00,
        "blue_scale": 0.88,
    },
    "i_wpn_t7_zmb_zod_tentacle_claw_c": {
        "brightness": 0.95,
        "contrast": 1.18,
        "saturation": 1.48,
        "red_scale": 1.08,
        "green_scale": 1.00,
        "blue_scale": 0.90,
    },
    "i_wpn_t7_zmb_zod_idg_ammo_c": {
        "brightness": 1.02,
        "contrast": 1.18,
        "saturation": 1.40,
        "red_scale": 1.06,
        "green_scale": 1.00,
        "blue_scale": 0.82,
    },
    "i_wpn_t7_zmb_zod_tentacle_electric_e": {
        "brightness": 1.10,
        "contrast": 1.25,
        "saturation": 1.00,
        "red_scale": 1.20,
        "green_scale": 0.72,
        "blue_scale": 0.24,
    },
}

IDG_IMAGE_PROCESS_PLAN = {
    "i_wpn_t7_zmb_zod_tentacle_ambient_c": "diffuse",
    "i_wpn_t7_zmb_zod_tentacle_claw_c": "diffuse",
    "i_wpn_t7_zmb_zod_idg_ammo_c": "emissive_color",
    "i_wpn_t7_zmb_zod_tentacle_electric_e": "emissive_mask",
    "i_wpn_t7_zmb_zod_tentacle_ambient_g": "spec_soft",
    "i_wpn_t7_zmb_zod_tentacle_claw_g": "spec_soft",
    "i_wpn_t7_zmb_zod_idg_ammo_s": "spec_soft",
}

GAME_MOD_ZONE_DIR = ROOT / "mods" / MOD_NAME / "zone" / "all"
STORAGE_MOD_ROOT = Path(os.path.expandvars(rf"%LOCALAPPDATA%\Plutonium\storage\t6\mods\{MOD_NAME}"))
STORAGE_MOD_ZONE_DIR = STORAGE_MOD_ROOT / "zone" / "all"
STORAGE_MOD_SCRIPT_DIR = STORAGE_MOD_ROOT / "scripts"
BASE_ZONE_DIR = ROOT / "zone" / "all"

DEPLOY_TO_MOD = os.environ.get("ROGUE_DEPLOY_TO_MOD", "1") not in ("0", "false", "False")
DEPLOY_TO_BASE = os.environ.get("ROGUE_DEPLOY_TO_BASE", "0") not in ("0", "false", "False")
USE_BO3_IDG_ANIMS = os.environ.get("ROGUE_USE_BO3_IDG_ANIMS", "0") not in ("0", "false", "False")
ALLOW_STRIPPED_SURVIVAL_FF = os.environ.get("ROGUE_ALLOW_STRIPPED_SURVIVAL_FF", "0") not in ("0", "false", "False")
STUB_ZM_VIEWHANDS = os.environ.get("ROGUE_STUB_ZM_VIEWHANDS", "0") not in ("0", "false", "False")
USE_CUSTOM_IDG_VIEWHANDS = os.environ.get("ROGUE_USE_CUSTOM_IDG_VIEWHANDS", "0") not in ("0", "false", "False")
FORCE_LOW_HANDMODEL = os.environ.get("ROGUE_FORCE_LOW_HANDMODEL", "0") not in ("0", "false", "False")
USE_FULL_ZONE_SOURCE = os.environ.get("ROGUE_USE_FULL_ZONE_SOURCE", "1" if DEPLOY_TO_BASE else "0") not in (
    "0",
    "false",
    "False",
)

# Live Servant tuning.
# User requested 1 round chambered and 9 in reserve for the BO2 donor shell.
# On this BO2 shell, maxAmmo behaves like the total pool including the chamber,
# so engine-side max must be 10 to show 1/9 on the HUD.
# BO3 black-hole timing is sourced separately from the grenade weapon/script path.
PROOF_CLIP_SIZE = "1"
PROOF_START_AMMO = "10"
PROOF_MAX_AMMO = "10"
PROOF_FIRE_TIME = "0.75"
PROOF_DAMAGE = "2000"
IDG_VIEW_GLB_SRC = (
    Path(IDG_VIEW_GLB_OVERRIDE).resolve()
    if IDG_VIEW_GLB_OVERRIDE
    else ROOT / "_build" / "bo3_rev_idg_weapon_only" / "bo3_rev_idg_weapon_only.glb"
)
IDG_VIEW_GLB_DST = MODEL_EXPORT_DIR / f"{MODEL_ASSET}_lod0.glb"
IDG_VIEWHANDS_GLB_DST = MODEL_EXPORT_DIR / "bo3_rev_idg_viewhands_lod0.glb"
BRIDGE_VIEWHANDS_GLB_DST = MODEL_EXPORT_DIR / "bo3_rev_bridge_viewhands_lod0.glb"

T7_ANIM_BIN_DIR = Path(
    r"Z:\Games\T7 Assets V2.5 (2)\T7 Assets V2.5\T7 Assets\xanim_export\_midgetblaster\black_ops_3"
)
PYCOD_ROOT = ROOT / "_tmp_tools" / "blender-cod-master" / "blender-cod-master" / "io_scene_cod"
LINKER = ROOT / "tools" / "oat" / "Linker.exe"
XANIM_COMPILER = ROOT / "_build" / "compile_xanim_zone.py"
SO_SURVIVAL_BASELINE_FF = ROOT / "_build" / "ff_backup" / "20260213-123213" / "so_zsurvival_zm_transit.ff"
FULL_RUNTIME_SOURCE_ROOT = ROOT / "_build" / "runtime_unlink_so_zsurvival_clean"
FULL_RUNTIME_ZONE_SOURCE = FULL_RUNTIME_SOURCE_ROOT / "zone_source" / f"{RUNTIME_ZONE_NAME}.zone"
ZONE_DUMP_SOURCE_ROOT = ROOT / "zone_dump" / "zone_raw" / "so_zsurvival_zm_transit"
ZONE_DUMP_TOMB_ROOT = ROOT / "zone_dump" / "zone_raw" / "zm_tomb"
TRANSIT_UNLINK_ROOT = ROOT / "_build" / "runtime_unlink_zm_transit_full_1"
WEAPON_SOURCE_ROOTS = [
    TRANSIT_UNLINK_ROOT,
    FULL_RUNTIME_SOURCE_ROOT,
    ZONE_DUMP_SOURCE_ROOT,
    ZONE_DUMP_TOMB_ROOT,
]
MIN_VIEWHANDS_TOOL = ROOT / "_build" / "rebuild_min_viewhands_glb.py"
STUB_VIEWHANDS_NAMES = ["c_zom_suit_viewhands", "c_zom_hazmat_viewhands"]

LOAD_FFS = [
    ROOT / "zone" / "all" / "patch_zm.ff",
    ROOT / "zone" / "all" / "code_post_gfx_zm.ff",
    ROOT / "zone" / "all" / "zm_transit.ff",
    ROOT / "zone" / "english" / "en_zm_transit.ff",
    ROOT / "zone" / "all" / "dlc4_load_zm.ff",
    ROOT / "zone" / "english" / "en_dlc4_load_zm.ff",
    ROOT / "zone" / "all" / "zm_tomb_patch.ff",
    ROOT / "zone" / "all" / "zm_tomb.ff",
    ROOT / "zone" / "all" / "common_zm.ff",
]

IDG_ANIMS = [
    "vm_zod_id_gun_ads_down",
    "vm_zod_id_gun_ads_up",
    "vm_zod_id_gun_crawl_b",
    "vm_zod_id_gun_crawl_f",
    "vm_zod_id_gun_crawl_in",
    "vm_zod_id_gun_crawl_l",
    "vm_zod_id_gun_crawl_out",
    "vm_zod_id_gun_crawl_r",
    "vm_zod_id_gun_fall",
    "vm_zod_id_gun_fire",
    "vm_zod_id_gun_fire_ads",
    "vm_zod_id_gun_first_raise",
    "vm_zod_id_gun_idle",
    "vm_zod_id_gun_jump",
    "vm_zod_id_gun_jump_land",
    "vm_zod_id_gun_pullout",
    "vm_zod_id_gun_putaway",
    "vm_zod_id_gun_reload_empty",
    "vm_zod_id_gun_slide_in",
    "vm_zod_id_gun_slide_loop",
    "vm_zod_id_gun_slide_out",
    "vm_zod_id_gun_sprint_in",
    "vm_zod_id_gun_sprint_loop",
    "vm_zod_id_gun_sprint_out",
    "vm_zod_id_gun_walk_f",
]

ANIM_FIELDS = {
    "idleAnim",
    "idleAnimLeft",
    "emptyIdleAnim",
    "emptyIdleAnimLeft",
    "fireIntroAnim",
    "fireAnim",
    "fireAnimLeft",
    "holdFireAnim",
    "lastShotAnim",
    "lastShotAnimLeft",
    "flourishAnim",
    "flourishAnimLeft",
    "detonateAnim",
    "rechamberAnim",
    "meleeAnim",
    "meleeAnimEmpty",
    "meleeAnim1",
    "meleeAnim2",
    "meleeAnim3",
    "meleeChargeAnim",
    "meleeChargeAnimEmpty",
    "reloadAnim",
    "reloadAnimRight",
    "reloadAnimLeft",
    "reloadEmptyAnim",
    "reloadEmptyAnimLeft",
    "reloadStartAnim",
    "reloadEndAnim",
    "reloadQuickAnim",
    "reloadQuickEmptyAnim",
    "raiseAnim",
    "dropAnim",
    "firstRaiseAnim",
    "altRaiseAnim",
    "altDropAnim",
    "quickRaiseAnim",
    "quickDropAnim",
    "emptyRaiseAnim",
    "emptyDropAnim",
    "sprintInAnim",
    "sprintLoopAnim",
    "sprintOutAnim",
    "sprintInEmptyAnim",
    "sprintLoopEmptyAnim",
    "sprintOutEmptyAnim",
    "lowReadyInAnim",
    "lowReadyLoopAnim",
    "lowReadyOutAnim",
    "contFireInAnim",
    "contFireLoopAnim",
    "contFireOutAnim",
    "crawlInAnim",
    "crawlForwardAnim",
    "crawlBackAnim",
    "crawlRightAnim",
    "crawlLeftAnim",
    "crawlOutAnim",
    "crawlEmptyInAnim",
    "crawlEmptyForwardAnim",
    "crawlEmptyBackAnim",
    "crawlEmptyRightAnim",
    "crawlEmptyLeftAnim",
    "crawlEmptyOutAnim",
    "deployAnim",
    "nightVisionWearAnim",
    "nightVisionRemoveAnim",
    "adsFireAnim",
    "adsLastShotAnim",
    "adsRechamberAnim",
    "adsUpAnim",
    "adsDownAnim",
    "adsUpOtherScopeAnim",
    "adsFireIntroAnim",
    "breakdownAnim",
    "dtp_in",
    "dtp_loop",
    "dtp_out",
    "dtp_empty_in",
    "dtp_empty_loop",
    "dtp_empty_out",
    "slide_in",
    "mantleAnim",
    "sprintCameraAnim",
    "dtpInCameraAnim",
    "dtpLoopCameraAnim",
    "dtpOutCameraAnim",
    "mantleCameraAnim",
}

DONOR_ANIM_PROFILE_OVERRIDES: dict[str, dict[str, str]] = {
    "mg08_zm": {
        "fireAnim": "viewmodel_zomb_staff_fire",
        "lastShotAnim": "viewmodel_zomb_staff_fire",
        "adsFireAnim": "viewmodel_zomb_staff_ads_fire",
        "reloadAnim": "viewmodel_pdw57_reload",
        "reloadEmptyAnim": "viewmodel_pdw57_reload_empty",
        # BO2 can run without explicit quick anim aliases here, but wiring them
        # to the same PDW reloads keeps Speed Cola / quick-reload paths from
        # falling back unpredictably to the donor MG08 behavior.
        "reloadQuickAnim": "viewmodel_pdw57_reload",
        "reloadQuickEmptyAnim": "viewmodel_pdw57_reload_empty",
        "reloadTime": "2.6",
        "reloadEmptyTime": "3.2",
        "reloadAddTime": "1.7",
        "reloadEmptyAddTime": "0",
        "reloadQuickTime": "2.6",
        "reloadQuickEmptyTime": "3.2",
        "reloadQuickAddTime": "1.05",
        "reloadQuickEmptyAddTime": "0",
    },
}


def ensure_dirs() -> None:
    for path in (
        WORK,
        OUTPUT,
        MODEL_EXPORT_DIR,
        XMODEL_DIR,
        MATERIALS_DIR,
        IMAGES_DIR,
        WEAPONS_DIR,
        XANIM_DIR,
        ZONE_SOURCE_DIR,
        ZONE_RAW_ROOT,
    ):
        path.mkdir(parents=True, exist_ok=True)


def donor_anim_profile_overrides() -> dict[str, str]:
    if USE_BO3_IDG_ANIMS:
        return {}
    return dict(DONOR_ANIM_PROFILE_OVERRIDES.get(WEAPON_ASSET, {}))


def donor_extra_runtime_xanims() -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for key, value in donor_anim_profile_overrides().items():
        if not key.lower().endswith("anim"):
            continue
        anim_name = str(value).strip()
        if not anim_name or anim_name in seen:
            continue
        seen.add(anim_name)
        names.append(anim_name)
    return names


def clean_output_artifacts() -> None:
    for artifact in (
        OUTPUT / RUNTIME_FF_NAME,
        OUTPUT / RUNTIME_IPAK_NAME,
        OUTPUT / f"{MOD_LOAD_ZONE_NAME}.ff",
        OUTPUT / f"{MOD_ZONE_NAME}.ff",
        OUTPUT / f"{MOD_ZONE_NAME}.ipak",
    ):
        try:
            if artifact.exists():
                artifact.unlink()
        except OSError as ex:
            print(f"WARNING: failed removing stale output artifact {artifact}: {ex}")


def parse_weapon(path: Path) -> list[tuple[str, str]]:
    data = path.read_text(encoding="utf-8").strip()
    parts = data.split("\\")
    if not parts or parts[0] != "WEAPONFILE":
        raise RuntimeError(f"Unexpected weapon file format: {path}")
    pairs: list[tuple[str, str]] = []
    for i in range(1, len(parts) - 1, 2):
        pairs.append((parts[i], parts[i + 1]))
    return pairs


def format_weapon(pairs: list[tuple[str, str]]) -> str:
    flat = ["WEAPONFILE"]
    for key, value in pairs:
        flat.extend([key, value])
    return "\\".join(flat)


def base_weapon_pairs() -> list[tuple[str, str]]:
    for root in WEAPON_SOURCE_ROOTS:
        for suffix in ("", ".weapon"):
            candidate = root / "weapons" / f"{WEAPON_ASSET}{suffix}"
            if candidate.exists():
                return parse_weapon(candidate)
    raise FileNotFoundError(
        "Missing base weapon source for "
        f"{WEAPON_ASSET}; looked in {[str(root / 'weapons') for root in WEAPON_SOURCE_ROOTS]}"
    )


def base_weapon_fields() -> dict[str, str]:
    return dict(base_weapon_pairs())


def uses_custom_model() -> bool:
    if GUN_MODEL_MODE in ("custom", "idg", ""):
        return True
    if GUN_MODEL_MODE in ("base", "literal"):
        return False
    raise RuntimeError(f"Unsupported ROGUE_GUN_MODEL_MODE: {GUN_MODEL_MODE}")


def resolved_gun_model(base_fields: dict[str, str]) -> str:
    if uses_custom_model():
        return MODEL_ASSET
    if GUN_MODEL_MODE == "base":
        return str(base_fields.get("gunModel", "")).strip()
    if GUN_MODEL_MODE == "literal":
        if not GUN_MODEL_LITERAL:
            raise RuntimeError("ROGUE_GUN_MODEL_LITERAL is required when ROGUE_GUN_MODEL_MODE=literal")
        return GUN_MODEL_LITERAL
    raise RuntimeError(f"Unhandled gun model mode: {GUN_MODEL_MODE}")


def anim_for_field(field_name: str) -> str:
    f = (field_name or "").lower()
    if f in ("idleanim", "idleanimleft", "emptyidleanim", "emptyidleanimleft", "flourishanim", "flourishanimleft"):
        return "vm_zod_id_gun_idle"
    if f in ("raiseanim", "altraiseanim", "emptyraiseanim", "quickraiseanim"):
        return "vm_zod_id_gun_pullout"
    if f in ("dropanim", "altdropanim", "emptydropanim", "quickdropanim"):
        return "vm_zod_id_gun_putaway"
    if f == "firstraiseanim":
        return "vm_zod_id_gun_first_raise"
    if "reload" in f:
        return "vm_zod_id_gun_reload_empty"
    if "adsfire" in f:
        return "vm_zod_id_gun_fire_ads"
    if f == "adsupanim" or f == "adsupotherscopeanim":
        return "vm_zod_id_gun_ads_up"
    if f == "adsdownanim":
        return "vm_zod_id_gun_ads_down"
    if f == "sprintinanim":
        return "vm_zod_id_gun_sprint_in"
    if f == "sprintloopanim":
        return "vm_zod_id_gun_sprint_loop"
    if f == "sprintoutanim":
        return "vm_zod_id_gun_sprint_out"
    if f == "crawlinanim":
        return "vm_zod_id_gun_crawl_in"
    if f == "crawlforwardanim":
        return "vm_zod_id_gun_crawl_f"
    if f == "crawlbackanim":
        return "vm_zod_id_gun_crawl_b"
    if f == "crawlrightanim":
        return "vm_zod_id_gun_crawl_r"
    if f == "crawlleftanim":
        return "vm_zod_id_gun_crawl_l"
    if f == "crawloutanim":
        return "vm_zod_id_gun_crawl_out"
    if f == "dtp_in" or f == "slide_in":
        return "vm_zod_id_gun_slide_in"
    if f == "dtp_loop":
        return "vm_zod_id_gun_slide_loop"
    if f == "dtp_out":
        return "vm_zod_id_gun_slide_out"
    if "fire" in f or "shot" in f:
        return "vm_zod_id_gun_fire"
    if "camera" in f or "mantle" in f or "deploy" in f or "nightvision" in f or "melee" in f:
        return "vm_zod_id_gun_idle"
    return "vm_zod_id_gun_idle"


def stage_model() -> None:
    if not uses_custom_model():
        return
    if not IDG_VIEW_GLB_SRC.exists():
        raise FileNotFoundError(f"Missing converted IDG viewmodel GLB: {IDG_VIEW_GLB_SRC}")
    shutil.copy2(IDG_VIEW_GLB_SRC, IDG_VIEW_GLB_DST)

    xmodel = {
        "$schema": "http://openassettools.dev/schema/xmodel.v1.json",
        "_game": "t6",
        "_type": "xmodel",
        "_version": 2,
        "flags": 4718592,
        "lightingOriginOffset": {"x": 0.0, "y": 0.0, "z": 0.5},
        "lightingOriginRange": 0.5,
        "lods": [{"distance": 374.03118896484375, "file": f"model_export/{MODEL_ASSET}_lod0.glb"}],
        "type": "animated",
    }
    (XMODEL_DIR / f"{MODEL_ASSET}.json").write_text(json.dumps(xmodel, indent=2) + "\n", encoding="utf-8")


def read_glb_material_names(path: Path) -> list[str]:
    with path.open("rb") as handle:
        if handle.read(4) != b"glTF":
            raise RuntimeError(f"Not a GLB file: {path}")
        handle.read(4)
        total_len = struct.unpack("<I", handle.read(4))[0]
        json_len = struct.unpack("<I", handle.read(4))[0]
        if handle.read(4) != b"JSON":
            raise RuntimeError(f"Invalid GLB JSON chunk: {path}")
        gltf = json.loads(handle.read(json_len).decode("utf-8"))
        if handle.tell() < total_len:
            pass
    names: list[str] = []
    seen: set[str] = set()
    for material in gltf.get("materials", []):
        name = str((material or {}).get("name", "")).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def read_glb_stats(path: Path) -> dict[str, object]:
    with path.open("rb") as handle:
        if handle.read(4) != b"glTF":
            raise RuntimeError(f"Not a GLB file: {path}")
        handle.read(4)
        handle.read(4)
        json_len = struct.unpack("<I", handle.read(4))[0]
        if handle.read(4) != b"JSON":
            raise RuntimeError(f"Invalid GLB JSON chunk: {path}")
        gltf = json.loads(handle.read(json_len).decode("utf-8"))

    nodes = gltf.get("nodes", [])
    skins = gltf.get("skins", [])
    joints = 0
    if skins:
        first_skin = skins[0] or {}
        joints = len(first_skin.get("joints", []) or [])

    return {
        "path": str(path),
        "nodes": len(nodes),
        "joints": joints,
        "skins": len(skins),
        "meshes": len(gltf.get("meshes", [])),
        "materials": len(gltf.get("materials", [])),
    }


def resolve_xmodel_json_path(asset_name: str) -> Path | None:
    candidates = [
        XMODEL_DIR / f"{asset_name}.json",
        TRANSIT_UNLINK_ROOT / "xmodel" / f"{asset_name}.json",
        ZONE_DUMP_SOURCE_ROOT / "xmodel" / f"{asset_name}.json",
        ZONE_DUMP_TOMB_ROOT / "xmodel" / f"{asset_name}.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def resolve_glb_from_xmodel(xmodel_json_path: Path, meta: dict[str, object]) -> Path | None:
    lods = meta.get("lods", [])
    if not isinstance(lods, list) or not lods:
        return None
    lod0 = lods[0] or {}
    rel = str(lod0.get("file", "")).strip()
    if not rel:
        return None

    if xmodel_json_path.parent == XMODEL_DIR:
        candidate = WORK / rel
        if candidate.exists():
            return candidate

    base_candidates = [
        xmodel_json_path.parent.parent / rel,
        TRANSIT_UNLINK_ROOT / rel,
        ZONE_DUMP_SOURCE_ROOT / rel,
        ZONE_DUMP_TOMB_ROOT / rel,
    ]
    for candidate in base_candidates:
        if candidate.exists():
            return candidate
    return None


def inspect_xmodel_asset(asset_name: str) -> dict[str, object] | None:
    if not asset_name:
        return None
    xmodel_json = resolve_xmodel_json_path(asset_name)
    if not xmodel_json:
        return {
            "asset": asset_name,
            "found": False,
        }

    meta = json.loads(xmodel_json.read_text(encoding="utf-8", errors="replace"))
    glb_path = resolve_glb_from_xmodel(xmodel_json, meta)
    glb_stats = read_glb_stats(glb_path) if glb_path and glb_path.exists() else None
    return {
        "asset": asset_name,
        "found": True,
        "xmodel_json": str(xmodel_json),
        "type": meta.get("type"),
        "flags": meta.get("flags"),
        "lod0_file": (meta.get("lods") or [{}])[0].get("file") if isinstance(meta.get("lods"), list) and meta.get("lods") else None,
        "glb": glb_stats,
    }


def sum_component_counts(components: list[dict[str, object] | None], key: str) -> int:
    total = 0
    for component in components:
        if not component:
            continue
        glb = component.get("glb")
        if not isinstance(glb, dict):
            continue
        value = glb.get(key)
        if isinstance(value, int):
            total += value
    return total


def staged_material_names() -> list[str]:
    if not uses_custom_model():
        return []
    names = list(MODEL_MATERIALS)
    for material_name in read_glb_material_names(IDG_VIEW_GLB_DST):
        if material_name not in names:
            names.append(material_name)
    return names


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def idg_image_semantic(image_name: str) -> str:
    lower = image_name.lower()
    if lower.endswith("_n"):
        return "normalMap"
    if lower.endswith("_o"):
        return "occlusionMap"
    if lower.endswith("_r") or lower.endswith("_mask") or lower.endswith("_t"):
        return "revealMap"
    if lower.endswith("_s") or lower.endswith("_g"):
        return "specularMap"
    return "diffuseMap"


def read_dds(path: Path) -> tuple[int, int, list[tuple[int, int, bytes]], int]:
    with path.open("rb") as f:
        if f.read(4) != DDS_MAGIC:
            raise RuntimeError(f"Not a DDS file: {path}")
        header = f.read(DDS_HEADER_SIZE)
        height = struct.unpack_from("<I", header, 8)[0]
        width = struct.unpack_from("<I", header, 12)[0]
        mip_count = struct.unpack_from("<I", header, 24)[0]
        pf_fourcc = header[80:84]
        if pf_fourcc == b"DX10":
            dx10_header = f.read(20)
            dxgi_format = struct.unpack_from("<I", dx10_header, 0)[0]
            iwi_format = IWI_FORMAT_DXN if dxgi_format in (DXGI_FORMAT_BC5_UNORM, DXGI_FORMAT_BC5_SNORM) else IWI_FORMAT_DXT5
        elif pf_fourcc == b"DXT5":
            iwi_format = IWI_FORMAT_DXT5
        else:
            iwi_format = IWI_FORMAT_DXT5
        all_data = f.read()

    mips: list[tuple[int, int, bytes]] = []
    offset = 0
    w, h = width, height
    for _ in range(max(1, mip_count)):
        bw = max(1, w // 4)
        bh = max(1, h // 4)
        mip_size = bw * bh * 16
        mip_data = all_data[offset : offset + mip_size]
        mips.append((w, h, mip_data))
        offset += mip_size
        w = max(1, w // 2)
        h = max(1, h // 2)
        if offset >= len(all_data):
            break
    return width, height, mips, iwi_format


def create_iwi(width: int, height: int, mips: list[tuple[int, int, bytes]], iwi_format: int, output_path: Path) -> None:
    num_mips = len(mips)
    picmip = [0] * 8
    for i in range(8):
        if i < num_mips:
            data_size = sum(len(mips[j][2]) for j in range(i, num_mips))
            picmip[i] = IWI_HEADER_SIZE + data_size
        else:
            picmip[i] = IWI_HEADER_SIZE + len(mips[-1][2])

    header = bytearray(IWI_HEADER_SIZE)
    header[0:3] = IWI_MAGIC
    header[3] = IWI_VERSION
    header[4] = iwi_format
    header[5] = 0x00
    struct.pack_into("<H", header, 6, width)
    struct.pack_into("<H", header, 8, height)
    struct.pack_into("<H", header, 10, 1)
    for i in range(8):
        struct.pack_into("<I", header, 32 + i * 4, picmip[i])

    with output_path.open("wb") as f:
        f.write(header)
        for _, _, data in reversed(mips):
            f.write(data)


def grade_diffuse_image(
    img: Image.Image,
    *,
    brightness: float,
    contrast: float,
    saturation: float,
    red_scale: float = 1.0,
    green_scale: float = 1.0,
    blue_scale: float = 1.0,
) -> Image.Image:
    rgba = img.convert("RGBA")
    rgb = Image.merge("RGB", rgba.split()[:3])
    rgb = ImageEnhance.Contrast(rgb).enhance(contrast)
    rgb = ImageEnhance.Color(rgb).enhance(saturation)
    rgb = ImageEnhance.Brightness(rgb).enhance(brightness)
    r, g, b = rgb.split()
    r = r.point(lambda v: min(255, int(v * red_scale)))
    g = g.point(lambda v: min(255, int(v * green_scale)))
    b = b.point(lambda v: min(255, int(v * blue_scale)))
    a = Image.new("L", rgba.size, 255)
    return Image.merge("RGBA", (r, g, b, a))


def build_emissive_color_image(img: Image.Image, *, brightness: float, contrast: float, saturation: float, red_scale: float, green_scale: float, blue_scale: float) -> Image.Image:
    rgba = grade_diffuse_image(
        img,
        brightness=brightness,
        contrast=contrast,
        saturation=saturation,
        red_scale=red_scale,
        green_scale=green_scale,
        blue_scale=blue_scale,
    )
    rgb = Image.merge("RGB", rgba.split()[:3])
    luma = rgb.convert("L")
    alpha = luma.point(lambda v: 0 if v < 10 else min(255, int(v * 1.10)))
    return Image.merge("RGBA", (*rgb.split(), alpha))


def build_emissive_mask_image(img: Image.Image, *, brightness: float, contrast: float, saturation: float, red_scale: float, green_scale: float, blue_scale: float) -> Image.Image:
    rgba = img.convert("RGBA")
    mask = rgba.convert("L")
    mask = ImageEnhance.Contrast(mask).enhance(contrast)
    mask = ImageEnhance.Brightness(mask).enhance(brightness)
    r = mask.point(lambda v: min(255, int(v * red_scale)))
    g = mask.point(lambda v: min(255, int(v * green_scale)))
    b = mask.point(lambda v: min(255, int(v * blue_scale)))
    a = mask.point(lambda v: 0 if v < 6 else min(255, int(v * 1.35)))
    return Image.merge("RGBA", (r, g, b, a))


def soften_spec_image(img: Image.Image, rgb_scale: float, alpha_scale: float) -> Image.Image:
    gray = img.convert("L")
    rgb = gray.point(lambda v: min(255, int(v * rgb_scale)))
    alpha = gray.point(lambda v: min(255, int(v * alpha_scale)))
    return Image.merge("RGBA", (rgb, rgb, rgb, alpha))


def write_processed_iwi_from_png(src_png: Path, dst_iwi: Path, mode: str, image_name: str) -> None:
    if not TEXCONV.exists():
        raise FileNotFoundError(f"Missing texconv: {TEXCONV}")

    img = Image.open(src_png)
    if mode == "diffuse":
        diffuse_grade = dict(IDG_DIFFUSE_GRADE_DEFAULT)
        diffuse_grade.update(IDG_DIFFUSE_GRADE_BY_IMAGE.get(image_name, {}))
        processed = grade_diffuse_image(img, **diffuse_grade)
    elif mode == "emissive_color":
        emissive_grade = dict(IDG_DIFFUSE_GRADE_DEFAULT)
        emissive_grade.update(IDG_DIFFUSE_GRADE_BY_IMAGE.get(image_name, {}))
        processed = build_emissive_color_image(img, **emissive_grade)
    elif mode == "emissive_mask":
        emissive_grade = dict(IDG_DIFFUSE_GRADE_DEFAULT)
        emissive_grade.update(IDG_DIFFUSE_GRADE_BY_IMAGE.get(image_name, {}))
        processed = build_emissive_mask_image(img, **emissive_grade)
    elif mode == "spec_soft":
        processed = soften_spec_image(img, IDG_SPEC_RGB_SCALE, IDG_SPEC_ALPHA_SCALE)
    else:
        raise RuntimeError(f"Unsupported image process mode: {mode}")

    with tempfile.TemporaryDirectory(prefix="idg_tex_") as tmp:
        tmp_root = Path(tmp)
        png_path = tmp_root / f"{dst_iwi.stem}.png"
        processed.save(png_path)
        result = subprocess.run(
            [str(TEXCONV), "-f", "BC3_UNORM", "-y", "-m", "0", "-o", str(tmp_root), str(png_path)],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"texconv failed for {src_png}:\n{result.stdout}\n{result.stderr}")
        dds_path = tmp_root / f"{dst_iwi.stem}.dds"
        if not dds_path.exists():
            raise FileNotFoundError(f"texconv did not produce DDS: {dds_path}")
        width, height, mips, iwi_format = read_dds(dds_path)
        create_iwi(width, height, mips, iwi_format, dst_iwi)


def build_idg_surface_bundle(material_names: list[str]) -> Path:
    if IDG_SURFACE_BUNDLE_ROOT.exists():
        shutil.rmtree(IDG_SURFACE_BUNDLE_ROOT)
    staged_root = IDG_SURFACE_BUNDLE_ROOT / "staged"
    manifest_dir = IDG_SURFACE_BUNDLE_ROOT / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    image_entries: list[dict[str, object]] = []
    copied_files: list[dict[str, str]] = []
    for image_name, file_name in sorted(IDG_SURFACE_IMAGE_FILES.items()):
        src = IDG_SURFACE_IMAGE_ROOT / file_name
        if not src.exists():
            raise FileNotFoundError(f"Missing BO3 IDG source image: {src}")
        relative = f"model_export/_midgetblaster/weapons/t7/_images/{file_name}"
        dst = staged_root / Path(relative)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        image_entries.append(
            {
                "name": image_name,
                "gdf": "image.gdf",
                "props": {
                    "baseImage": relative,
                    "clampU": "0",
                    "clampV": "0",
                    "matureContent": "0",
                    "noMipMaps": "0",
                    "semantic": idg_image_semantic(image_name),
                },
            }
        )
        copied_files.append(
            {
                "relative": relative,
                "destination": str(dst),
            }
        )

    material_entries: list[dict[str, object]] = []
    for material_name in material_names:
        slots = dict(IDG_SURFACE_FALLBACK_SLOTS)
        slots.update(IDG_SURFACE_MATERIAL_SLOTS.get(material_name, {}))
        material_entries.append(
            {
                "name": material_name,
                "gdf": "material.gdf",
                "props": slots,
            }
        )

    write_json(manifest_dir / "materials.json", material_entries)
    write_json(manifest_dir / "images.json", image_entries)
    write_json(
        IDG_SURFACE_BLENDER_REPORT,
        {
            "rows": [
                {
                    "status": "ok",
                    "metadata": {
                        "material_names": material_names,
                    },
                }
            ]
        },
    )
    write_json(
        IDG_SURFACE_BUNDLE_REPORT,
        {
            "output_root": str(IDG_SURFACE_BUNDLE_ROOT),
            "copied_files": copied_files,
            "counts": {
                "material_entries": len(material_entries),
                "image_entries": len(image_entries),
                "copied_unique_files": len(copied_files),
                "missing_refs": 0,
            },
        },
    )
    return IDG_SURFACE_BUNDLE_REPORT


def patch_translated_idg_material(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    debug_name = str(payload.get("debugName", "")).strip().lower()
    if debug_name.endswith("_eyes"):
        payload["techniqueSet"] = IDG_UNLIT_TECHSET
        payload["cameraRegion"] = "none"
    else:
        payload["techniqueSet"] = IDG_LIT_TECHSET
        payload["cameraRegion"] = "litOpaque"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def clone_material_template(
    template_path: Path,
    debug_name: str,
    textures_by_name: dict[str, str],
    *,
    technique_set: str | None = None,
    camera_region: str | None = None,
    double_sided: bool = False,
    alpha_cutout: bool = False,
) -> dict[str, object]:
    payload = json.loads(template_path.read_text(encoding="utf-8", errors="replace"))
    payload["debugName"] = debug_name
    if technique_set is not None:
        payload["techniqueSet"] = technique_set
    if camera_region is not None:
        payload["cameraRegion"] = camera_region

    textures = []
    for entry in payload.get("textures", []):
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        if not name:
            continue
        patched = dict(entry)
        if name in textures_by_name:
            patched["image"] = textures_by_name[name]
        textures.append(patched)
    payload["textures"] = textures
    if double_sided:
        for state in payload.get("stateBits", []):
            if isinstance(state, dict):
                state["cullFace"] = "none"
    if alpha_cutout:
        for state in payload.get("stateBits", []):
            if not isinstance(state, dict):
                continue
            if state.get("colorWriteRgb", False):
                state["alphaTest"] = "gt0"
    return payload


def build_safe_bo2_idg_materials(material_names: list[str]) -> None:
    lit_slots = {
        "mtl_wpn_t7_zmb_zod_idg_body": {
            "colorMap": "i_wpn_t7_zmb_zod_tentacle_ambient_c",
            "normalMap": "i_wpn_t7_zmb_zod_tentacle_ambient_n",
            "specularMap": "i_wpn_t7_zmb_zod_tentacle_ambient_g",
        },
        "mtl_wpn_t7_zmb_zod_idg_bone": {
            "colorMap": "i_wpn_t7_zmb_zod_tentacle_claw_c",
            "normalMap": "i_wpn_t7_zmb_zod_tentacle_claw_n",
            "specularMap": "i_wpn_t7_zmb_zod_tentacle_claw_g",
        },
        "mtl_wpn_t7_zmb_zod_idg_sacks": {
            "colorMap": "i_wpn_t7_zmb_zod_idg_ammo_c",
            "normalMap": "i_wpn_t7_zmb_zod_idg_ammo_n",
            "specularMap": "i_wpn_t7_zmb_zod_idg_ammo_s",
        },
        "mtl_wpn_t7_zmb_zod_idg_tentacles": {
            "colorMap": "i_wpn_t7_zmb_zod_tentacle_ambient_c",
            "normalMap": "i_wpn_t7_zmb_zod_tentacle_ambient_n",
            "specularMap": "i_wpn_t7_zmb_zod_tentacle_ambient_g",
        },
    }

    for material_name in material_names:
        dst = MATERIALS_DIR / f"{material_name}.json"
        if material_name == "mtl_wpn_t7_zmb_zod_idg_eyes":
            payload = clone_material_template(
                IDG_EMISSIVE_FX_TEMPLATE,
                material_name,
                {"colorMap": "i_wpn_t7_zmb_zod_idg_ammo_c"},
                technique_set=None,
                camera_region="emissiveFx",
                double_sided=True,
                alpha_cutout=False,
            )
        elif material_name == "mtl_wpn_t7_zmb_zod_idg_sacks":
            payload = clone_material_template(
                IDG_EMISSIVE_FX_TEMPLATE,
                material_name,
                {"colorMap": "i_wpn_t7_zmb_zod_idg_ammo_c"},
                technique_set=None,
                camera_region="emissiveFx",
                double_sided=True,
                alpha_cutout=False,
            )
        else:
            payload = clone_material_template(
                IDG_LIT_TEMPLATE,
                material_name,
                lit_slots.get(material_name, lit_slots["mtl_wpn_t7_zmb_zod_idg_body"]),
                technique_set=None,
                camera_region="litOpaque",
                double_sided=True,
            )
        dst.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sync_zone_raw_mirror() -> None:
    if ZONE_RAW_ROOT.exists():
        shutil.rmtree(ZONE_RAW_ROOT)
    ZONE_RAW_ROOT.mkdir(parents=True, exist_ok=True)

    mirror_dirs = {
        "images": IMAGES_DIR,
        "materials": MATERIALS_DIR,
        "model_export": MODEL_EXPORT_DIR,
        "weapons": WEAPONS_DIR,
        "xmodel": XMODEL_DIR,
        "zone_source": ZONE_SOURCE_DIR,
    }
    for name, src in mirror_dirs.items():
        if src.exists():
            shutil.copytree(src, ZONE_RAW_ROOT / name)


def stage_custom_idg_viewhands_asset() -> None:
    dst_json = XMODEL_DIR / f"{VIEWHANDS_ASSET}.json"
    if not USE_CUSTOM_IDG_VIEWHANDS:
        for path in (dst_json, IDG_VIEWHANDS_GLB_DST):
            try:
                if path.exists():
                    path.unlink()
            except OSError as ex:
                print(f"WARNING: failed removing staged custom IDG viewhands asset {path}: {ex}")
        return

    stock_json = ZONE_DUMP_SOURCE_ROOT / "xmodel" / "c_zom_suit_viewhands.json"
    flags = 786432
    lighting = {"x": 0.0, "y": 0.0, "z": 0.5}
    lighting_range = 0.5
    if stock_json.exists():
        try:
            meta = json.loads(stock_json.read_text(encoding="utf-8", errors="replace"))
            flags = int(meta.get("flags", flags))
            lighting = meta.get("lightingOriginOffset", lighting)
            lighting_range = float(meta.get("lightingOriginRange", lighting_range))
        except Exception:
            pass

    shutil.copy2(IDG_VIEW_GLB_SRC, IDG_VIEWHANDS_GLB_DST)
    out = {
        "$schema": "http://openassettools.dev/schema/xmodel.v1.json",
        "_game": "t6",
        "_type": "xmodel",
        "_version": 2,
        "flags": flags,
        "lightingOriginOffset": lighting,
        "lightingOriginRange": lighting_range,
        "lods": [{"distance": 900.0, "file": "model_export/bo3_rev_idg_viewhands_lod0.glb"}],
        "type": "viewhands",
    }
    dst_json.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"Staged custom IDG viewhands '{VIEWHANDS_ASSET}' -> {IDG_VIEWHANDS_GLB_DST}")


def stage_bridge_viewhands_asset() -> None:
    dst_json = XMODEL_DIR / f"{BRIDGE_VIEWHANDS_ASSET}.json"
    dst_glb = BRIDGE_VIEWHANDS_GLB_DST

    if not USE_CUSTOM_IDG_VIEWHANDS:
        for path in (dst_json, dst_glb):
            try:
                if path.exists():
                    path.unlink()
            except OSError as ex:
                print(f"WARNING: failed removing staged bridge viewhands asset {path}: {ex}")
        return

    if not MIN_VIEWHANDS_TOOL.exists():
        raise FileNotFoundError(f"Missing minimal viewhands tool: {MIN_VIEWHANDS_TOOL}")

    src_name = "c_zom_suit_viewhands"
    src_json = ZONE_DUMP_SOURCE_ROOT / "xmodel" / f"{src_name}.json"
    src_glb = ZONE_DUMP_SOURCE_ROOT / "model_export" / f"{src_name}_lod0.glb"
    if not src_json.exists() or not src_glb.exists():
        raise FileNotFoundError(
            f"Missing stock bridge viewhands source for {src_name}: json={src_json.exists()} glb={src_glb.exists()}"
        )

    meta = json.loads(src_json.read_text(encoding="utf-8", errors="replace"))
    cmd = [sys.executable, str(MIN_VIEWHANDS_TOOL), "--src-glb", str(src_glb), "--out-glb", str(dst_glb)]
    result = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        raise RuntimeError(f"Failed building bridge viewhands GLB: exit={result.returncode}")

    out = {
        "$schema": "http://openassettools.dev/schema/xmodel.v1.json",
        "_game": "t6",
        "_type": "xmodel",
        "_version": 2,
        "flags": int(meta.get("flags", 786432)),
        "lightingOriginOffset": meta.get("lightingOriginOffset", {"x": 0.0, "y": 0.0, "z": 0.5}),
        "lightingOriginRange": float(meta.get("lightingOriginRange", 0.5)),
        "lods": [{"distance": 900.0, "file": "model_export/bo3_rev_bridge_viewhands_lod0.glb"}],
        "type": "viewhands",
    }
    dst_json.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"Staged bridge viewhands '{BRIDGE_VIEWHANDS_ASSET}' -> {dst_glb}")


def stage_stub_zm_viewhands_assets() -> None:
    if not STUB_ZM_VIEWHANDS:
        removed = 0
        for name in STUB_VIEWHANDS_NAMES:
            for rel_path in (XMODEL_DIR / f"{name}.json", MODEL_EXPORT_DIR / f"{name}_lod0.glb"):
                try:
                    if rel_path.exists():
                        rel_path.unlink()
                        removed += 1
                except OSError as ex:
                    print(f"WARNING: failed removing staged stub viewhands {rel_path}: {ex}")
        print(f"Stub ZM viewhands disabled (purged {removed} staged overrides).")
        return

    if not MIN_VIEWHANDS_TOOL.exists():
        raise FileNotFoundError(f"Missing minimal viewhands tool: {MIN_VIEWHANDS_TOOL}")

    for name in STUB_VIEWHANDS_NAMES:
        src_json = ZONE_DUMP_SOURCE_ROOT / "xmodel" / f"{name}.json"
        src_glb = ZONE_DUMP_SOURCE_ROOT / "model_export" / f"{name}_lod0.glb"
        if not src_json.exists() or not src_glb.exists():
            raise FileNotFoundError(
                f"Missing stock viewhands source for {name}: json={src_json.exists()} glb={src_glb.exists()}"
            )

        dst_json = XMODEL_DIR / f"{name}.json"
        dst_glb = MODEL_EXPORT_DIR / f"{name}_lod0.glb"
        shutil.copy2(src_json, dst_json)
        cmd = [sys.executable, str(MIN_VIEWHANDS_TOOL), "--src-glb", str(src_glb), "--out-glb", str(dst_glb)]
        result = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
        if result.returncode != 0:
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
            raise RuntimeError(f"Failed building stub viewhands GLB for {name}: exit={result.returncode}")
        print(f"Staged stub viewhands '{name}' -> {dst_glb}")


def stage_weapon() -> None:
    pairs = base_weapon_pairs()
    base_fields = dict(pairs)
    updated: list[tuple[str, str]] = []
    seen: set[str] = set()
    base_hand_model = str(base_fields.get("handModel", "")).strip()
    forced_hand_model = "" if FORCE_LOW_HANDMODEL else ("viewmodel_usa_no_model" if USE_CUSTOM_IDG_VIEWHANDS else base_hand_model)
    forced = {
        "displayName": "WEAPON_APOTHICON_SERVANT",
        "gunModel": "viewmodel_usa_no_model" if USE_CUSTOM_IDG_VIEWHANDS else resolved_gun_model(base_fields),
        "handModel": forced_hand_model,
        "clipSize": PROOF_CLIP_SIZE,
        "startAmmo": PROOF_START_AMMO,
        "maxAmmo": PROOF_MAX_AMMO,
        "ammoCountClipRelative": "0",
        "camo": "",
        "fireTime": PROOF_FIRE_TIME,
        "damage": PROOF_DAMAGE,
    }
    forced.update(donor_anim_profile_overrides())
    for key, value in pairs:
        seen.add(key)
        if key in forced:
            updated.append((key, forced[key]))
            continue
        if USE_BO3_IDG_ANIMS and key in ANIM_FIELDS:
            updated.append((key, anim_for_field(key)))
            continue
        updated.append((key, value))

    for key, value in forced.items():
        if key not in seen:
            updated.append((key, value))

    data = format_weapon(updated)
    for suffix in ("", ".weapon"):
        (WEAPONS_DIR / f"{WEAPON_ASSET}{suffix}").write_text(data, encoding="utf-8")


def stage_materials() -> None:
    global STAGED_IMAGE_NAMES
    STAGED_IMAGE_NAMES = []
    if not uses_custom_model():
        return
    material_names = staged_material_names()
    bundle_report = build_idg_surface_bundle(material_names)

    if IDG_SURFACE_PROJECT_ROOT.exists():
        shutil.rmtree(IDG_SURFACE_PROJECT_ROOT)

    run_checked(
        [
            sys.executable,
            str(MATERIAL_TRANSLATOR),
            "--project-root",
            str(IDG_SURFACE_PROJECT_ROOT),
            "--project-name",
            IDG_SURFACE_PROJECT_NAME,
            "--blender-report",
            str(IDG_SURFACE_BLENDER_REPORT),
            "--default-techset",
            IDG_LIT_TECHSET,
            "--lit-techset",
            IDG_LIT_TECHSET,
            "--unlit-techset",
            IDG_UNLIT_TECHSET,
            "--bundle-report",
            str(bundle_report),
            "--report",
            str(IDG_SURFACE_TRANSLATION_REPORT),
        ],
        cwd=ROOT,
    )

    translation = json.loads(IDG_SURFACE_TRANSLATION_REPORT.read_text(encoding="utf-8"))
    translated_root = IDG_SURFACE_PROJECT_ROOT / "zone_raw" / IDG_SURFACE_PROJECT_NAME
    translated_materials = translated_root / "materials"
    translated_images = translated_root / "images"

    staged_images = sorted({str(item.get("image", "")).strip() for item in translation.get("staged_images", []) if str(item.get("image", "")).strip()})
    for image_name in staged_images:
        src = translated_images / f"{image_name}.iwi"
        if not src.exists():
            raise FileNotFoundError(f"Translated IDG image missing: {src}")
        shutil.copy2(src, IMAGES_DIR / src.name)

    # Re-author BO3 PBR source maps into BO2-safe diffuse/spec IWIs.
    for image_name, mode in IDG_IMAGE_PROCESS_PLAN.items():
        src_png_name = IDG_SURFACE_IMAGE_FILES.get(image_name)
        if not src_png_name:
            continue
        src_png = IDG_SURFACE_IMAGE_ROOT / src_png_name
        dst_iwi = IMAGES_DIR / f"{image_name}.iwi"
        if not src_png.exists():
            raise FileNotFoundError(f"Missing source PNG for processed image {image_name}: {src_png}")
        write_processed_iwi_from_png(src_png, dst_iwi, mode, image_name)

    build_safe_bo2_idg_materials(material_names)
    STAGED_IMAGE_NAMES = staged_images
    print(
        f"Staged translated IDG surfaces: materials={len(material_names)} "
        f"images={len(STAGED_IMAGE_NAMES)}"
    )


def convert_anim_bins_to_exports() -> None:
    if str(PYCOD_ROOT) not in sys.path:
        sys.path.insert(0, str(PYCOD_ROOT))
    from PyCoD import xanim as XAnim  # type: ignore

    converted = 0
    for stem in IDG_ANIMS:
        src = T7_ANIM_BIN_DIR / f"{stem}.xanim_bin"
        dst = XANIM_DIR / f"{stem}.xanim_export"
        if not src.exists():
            raise FileNotFoundError(f"Missing T7 anim bin: {src}")
        if dst.exists():
            continue
        anim = XAnim.Anim()
        anim.LoadFile_Bin(str(src))
        anim.WriteFile_Raw(str(dst), header_message="Generated for BO3 Rev IDG probe", embed_notes=False)
        converted += 1

    print(
        f"Staged xanim_export files: {len(IDG_ANIMS)} base "
        f"({converted} newly converted)"
    )


def write_zone_source() -> None:
    material_names = staged_material_names()
    image_names = list(STAGED_IMAGE_NAMES)
    donor_xanim_names = donor_extra_runtime_xanims()
    zone_path = ZONE_SOURCE_DIR / f"{RUNTIME_ZONE_NAME}.zone"
    ipak_directive = f">ipak,{RUNTIME_ZONE_NAME}"

    if USE_FULL_ZONE_SOURCE:
        if not FULL_RUNTIME_ZONE_SOURCE.exists():
            raise FileNotFoundError(f"Missing full runtime zone source: {FULL_RUNTIME_ZONE_SOURCE}")

        lines = [
            line
            for line in FULL_RUNTIME_ZONE_SOURCE.read_text(encoding="utf-8").splitlines()
            if not line.startswith("soundbank,")
        ]
        existing = {line.strip() for line in lines if line.strip()}
        if image_names and ipak_directive not in existing:
            lines.append(ipak_directive)
            existing.add(ipak_directive)
        additions = [
            *[f"image,{name}" for name in image_names],
            *[f"material,{name}" for name in material_names],
            *[f"xanim,{name}" for name in donor_xanim_names],
            *([f"xmodel,{MODEL_ASSET}"] if uses_custom_model() else []),
            *([f"xmodel,{VIEWHANDS_ASSET}"] if USE_CUSTOM_IDG_VIEWHANDS else []),
            *([f"xmodel,{BRIDGE_VIEWHANDS_ASSET}"] if USE_CUSTOM_IDG_VIEWHANDS else []),
            *([f"xmodel,{name}" for name in STUB_VIEWHANDS_NAMES] if STUB_ZM_VIEWHANDS else []),
            f"weapon,{WEAPON_ASSET}",
        ]

        for line in additions:
            if line not in existing:
                lines.append(line)
                existing.add(line)

        zone_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    out = [
        "// Call Of Duty: Black Ops II",
        ">game,T6",
        "",
        "// Auto-generated by _build/build_bo3_rev_idg_probe.py",
        *([ipak_directive] if image_names else []),
        *[f"image,{name}" for name in image_names],
        *[f"material,{name}" for name in material_names],
        *[f"xanim,{name}" for name in donor_xanim_names],
        *([f"xmodel,{MODEL_ASSET}"] if uses_custom_model() else []),
        *([f"xmodel,{VIEWHANDS_ASSET}"] if USE_CUSTOM_IDG_VIEWHANDS else []),
        *([f"xmodel,{BRIDGE_VIEWHANDS_ASSET}"] if USE_CUSTOM_IDG_VIEWHANDS else []),
        *([f"xmodel,{name}" for name in STUB_VIEWHANDS_NAMES] if STUB_ZM_VIEWHANDS else []),
        f"weapon,{WEAPON_ASSET}",
        "",
    ]
    zone_path.write_text("\n".join(out), encoding="utf-8")


def run_checked(args: list[str], cwd: Path | None = None) -> None:
    print("Running:", " ".join(args))
    result = subprocess.run(args, cwd=str(cwd) if cwd else None, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(args)}")


def run_capture(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=str(cwd) if cwd else None, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(args)}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def compile_mod_load() -> None:
    args = [
        sys.executable,
        str(XANIM_COMPILER),
        "--xanim-dir",
        str(XANIM_DIR),
        "--pattern",
        "vm_zod_id_gun_*.xanim_export",
        "--output-dir",
        str(OUTPUT),
        "--zone-name",
        MOD_LOAD_ZONE_NAME,
        "--crypto-seed",
        MOD_LOAD_ZONE_NAME,
        "--emit-mode",
        "bo3_frames",
        "--bo3-frames-targets",
        *IDG_ANIMS,
        "--bo3-fallback-mode",
        "static_pose",
        "--no-semantic-fill",
    ]
    run_checked(args, cwd=ROOT)


def build_runtime_ff() -> None:
    args = [
        str(LINKER),
        "--verbose",
        "--base-folder",
        str(WORK),
        "--add-asset-search-path",
        str(WORK),
        "--add-source-search-path",
        str(WORK),
        "--add-asset-search-path",
        str(ZONE_RAW_ROOT),
        "--add-source-search-path",
        str(ZONE_RAW_ROOT),
        "--output-folder",
        str(OUTPUT),
    ]
    if USE_FULL_ZONE_SOURCE:
        args.extend(
            [
                "--add-asset-search-path",
                str(FULL_RUNTIME_SOURCE_ROOT),
                "--add-source-search-path",
                str(FULL_RUNTIME_SOURCE_ROOT),
            ]
        )
    for ff in LOAD_FFS:
        args.extend(["--load", str(ff)])
    args.extend(["--load", str(SO_SURVIVAL_BASELINE_FF)])
    args.extend(["--load", str(OUTPUT / f"{MOD_LOAD_ZONE_NAME}.ff")])
    args.append(RUNTIME_ZONE_NAME)
    run_checked(args, cwd=ROOT)


def verify_runtime_ff_safety() -> None:
    runtime_ff = OUTPUT / RUNTIME_FF_NAME
    if not runtime_ff.exists():
        raise FileNotFoundError(f"Missing runtime FF: {runtime_ff}")

    assets = parse_unlinker_list(
        run_capture([str(ROOT / "tools" / "oat" / "Unlinker.exe"), "--list", str(runtime_ff)], cwd=ROOT)
    )
    baseline_size = SO_SURVIVAL_BASELINE_FF.stat().st_size if SO_SURVIVAL_BASELINE_FF.exists() else 0
    runtime_size = runtime_ff.stat().st_size

    has_keyvaluepairs = any(line.startswith("keyvaluepairs, so_zsurvival_zm_transit") for line in assets)
    has_any_scripts = any(line.startswith("script,") or line.startswith("scriptparsetree,") for line in assets)
    size_ok = baseline_size > 0 and runtime_size >= int(baseline_size * 0.90)

    if has_keyvaluepairs and has_any_scripts and size_ok:
        return

    if ALLOW_STRIPPED_SURVIVAL_FF:
        print(
            "WARNING: bypassing stripped survival FF safety gate "
            f"(has_keyvaluepairs={has_keyvaluepairs};has_any_scripts={has_any_scripts};"
            f"runtime_size={runtime_size};baseline_size={baseline_size})"
        )
        return

    raise RuntimeError(
        "Refusing to deploy stripped survival FF: "
        f"has_keyvaluepairs={has_keyvaluepairs};has_any_scripts={has_any_scripts};"
        f"runtime_size={runtime_size};baseline_size={baseline_size}"
    )


def verify_runtime_ipak() -> None:
    runtime_ipak = OUTPUT / RUNTIME_IPAK_NAME
    if not STAGED_IMAGE_NAMES:
        return
    if not runtime_ipak.exists():
        raise RuntimeError(
            "Custom images were staged but Linker did not emit a runtime IPAK: "
            f"{runtime_ipak}"
        )
    if runtime_ipak.stat().st_size <= 0:
        raise RuntimeError(f"Runtime IPAK is empty: {runtime_ipak}")


def purge_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def purge_live_mod_state() -> None:
    purge_targets: list[Path] = []
    if DEPLOY_TO_MOD:
        purge_targets.extend(
            [
                GAME_MOD_ZONE_DIR,
                STORAGE_MOD_ZONE_DIR,
                STORAGE_MOD_SCRIPT_DIR,
            ]
        )
    if DEPLOY_TO_BASE:
        purge_targets.extend(
            [
                BASE_ZONE_DIR / RUNTIME_FF_NAME,
                BASE_ZONE_DIR / RUNTIME_IPAK_NAME,
                BASE_ZONE_DIR / f"{MOD_LOAD_ZONE_NAME}.ff",
            ]
        )
    if DEPLOY_TO_MOD:
        purge_targets.extend(
            [
                GAME_MOD_ZONE_DIR / RUNTIME_IPAK_NAME,
                STORAGE_MOD_ZONE_DIR / RUNTIME_IPAK_NAME,
            ]
        )

    for target in purge_targets:
        purge_path(target)
        print(f"Purged stale deploy target -> {target}")


def render_probe_script() -> None:
    if not SCRIPT_TEMPLATE.exists():
        raise FileNotFoundError(f"Missing GSC template: {SCRIPT_TEMPLATE}")

    tokens = {
        "__BUILD_TAG__": BUILD_TAG,
        "__PROBE_WEAPON__": WEAPON_ASSET,
        "__STARTER_WEAPON__": PROBE_STARTER_WEAPON,
        "__PROBE_MODE__": GUN_MODEL_MODE,
        "__MODEL_ASSET__": resolved_gun_model(base_weapon_fields()),
    }
    rendered = SCRIPT_TEMPLATE.read_text(encoding="utf-8")
    for token, value in tokens.items():
        rendered = rendered.replace(token, value)

    SCRIPT_OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Rendered probe script -> {SCRIPT_OUTPUT}")


def deploy_outputs() -> None:
    deploy_targets: list[Path] = []
    if DEPLOY_TO_MOD:
        deploy_targets.extend([GAME_MOD_ZONE_DIR, STORAGE_MOD_ZONE_DIR])
    if DEPLOY_TO_BASE:
        deploy_targets.append(BASE_ZONE_DIR)

    if not deploy_targets:
        raise RuntimeError("Both deploy targets are disabled; enable ROGUE_DEPLOY_TO_MOD or ROGUE_DEPLOY_TO_BASE.")

    purge_live_mod_state()

    for dst_dir in deploy_targets:
        dst_dir.mkdir(parents=True, exist_ok=True)
        for ff_name in (RUNTIME_FF_NAME, f"{MOD_LOAD_ZONE_NAME}.ff", RUNTIME_IPAK_NAME):
            src = OUTPUT / ff_name
            if not src.exists():
                if ff_name == RUNTIME_IPAK_NAME:
                    continue
                raise FileNotFoundError(f"Missing build output: {src}")
            shutil.copy2(src, dst_dir / ff_name)
            print(f"Deployed {ff_name} -> {dst_dir}")

    src_script = ROOT / "mods" / MOD_NAME / "scripts" / "mod_i_am_mod.gsc"
    STORAGE_MOD_SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_script, STORAGE_MOD_SCRIPT_DIR / "mod_i_am_mod.gsc")
    print(f"Synced script -> {STORAGE_MOD_SCRIPT_DIR}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_unlinker_list(text: str) -> list[str]:
    lines = []
    in_content = False
    for raw in text.splitlines():
        line = raw.strip()
        if line == "Content:":
            in_content = True
            continue
        if not in_content or not line:
            continue
        lines.append(line)
    return lines


def build_debug_report() -> None:
    runtime_ff = OUTPUT / RUNTIME_FF_NAME
    runtime_ipak = OUTPUT / RUNTIME_IPAK_NAME
    mod_load_ff = OUTPUT / f"{MOD_LOAD_ZONE_NAME}.ff"

    runtime_ff_list = parse_unlinker_list(run_capture([str(ROOT / "tools" / "oat" / "Unlinker.exe"), "--list", str(runtime_ff)], cwd=ROOT))
    mod_load_ff_list = parse_unlinker_list(run_capture([str(ROOT / "tools" / "oat" / "Unlinker.exe"), "--list", str(mod_load_ff)], cwd=ROOT))

    staged_weapon_pairs = dict(parse_weapon(WEAPONS_DIR / WEAPON_ASSET))
    base_fields = base_weapon_fields()
    gun_model_name = str(staged_weapon_pairs.get("gunModel", "")).strip()
    hand_model_name = str(staged_weapon_pairs.get("handModel", "")).strip()
    gun_model_info = inspect_xmodel_asset(gun_model_name) if gun_model_name else None
    hand_model_info = inspect_xmodel_asset(hand_model_name) if hand_model_name else None
    suit_viewhands_info = inspect_xmodel_asset("c_zom_suit_viewhands")
    hazmat_viewhands_info = inspect_xmodel_asset("c_zom_hazmat_viewhands")

    suit_total_nodes = sum_component_counts([suit_viewhands_info, hand_model_info, gun_model_info], "nodes")
    suit_total_joints = sum_component_counts([suit_viewhands_info, hand_model_info, gun_model_info], "joints")
    hazmat_total_nodes = sum_component_counts([hazmat_viewhands_info, hand_model_info, gun_model_info], "nodes")
    hazmat_total_joints = sum_component_counts([hazmat_viewhands_info, hand_model_info, gun_model_info], "joints")
    report = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "build_tag": BUILD_TAG,
        "work_dir": str(WORK),
        "source_model": {
            "path": str(IDG_VIEW_GLB_SRC) if uses_custom_model() else None,
            "exists": IDG_VIEW_GLB_SRC.exists() if uses_custom_model() else None,
            "sha256": sha256(IDG_VIEW_GLB_SRC) if uses_custom_model() and IDG_VIEW_GLB_SRC.exists() else None,
        },
        "outputs": {
            "runtime_ff": {
                "path": str(runtime_ff),
                "sha256": sha256(runtime_ff),
                "assets": runtime_ff_list,
            },
            "runtime_ipak": {
                "path": str(runtime_ipak),
                "exists": runtime_ipak.exists(),
                "sha256": sha256(runtime_ipak) if runtime_ipak.exists() else None,
                "size": runtime_ipak.stat().st_size if runtime_ipak.exists() else 0,
            },
            "mod_load_ff": {
                "path": str(mod_load_ff),
                "sha256": sha256(mod_load_ff),
                "assets": mod_load_ff_list,
            },
        },
        "weapon_probe": {
            "asset": WEAPON_ASSET,
            "starter_weapon": PROBE_STARTER_WEAPON,
            "gun_model_mode": GUN_MODEL_MODE,
            "build_tag": BUILD_TAG,
            "use_bo3_idg_anims": USE_BO3_IDG_ANIMS,
            "use_custom_idg_viewhands": USE_CUSTOM_IDG_VIEWHANDS,
            "force_low_handmodel": FORCE_LOW_HANDMODEL,
            "proof_expectation": {
                "clipSize": PROOF_CLIP_SIZE,
                "startAmmo": PROOF_START_AMMO,
                "maxAmmo": PROOF_MAX_AMMO,
                "fireTime": PROOF_FIRE_TIME,
                "damage": PROOF_DAMAGE,
            },
            "staged_fields": {
                "displayName": staged_weapon_pairs.get("displayName"),
                "gunModel": staged_weapon_pairs.get("gunModel"),
                "handModel": staged_weapon_pairs.get("handModel"),
                "parentWeaponName": staged_weapon_pairs.get("parentWeaponName"),
                "clipSize": staged_weapon_pairs.get("clipSize"),
                "startAmmo": staged_weapon_pairs.get("startAmmo"),
                "maxAmmo": staged_weapon_pairs.get("maxAmmo"),
                "fireTime": staged_weapon_pairs.get("fireTime"),
                "damage": staged_weapon_pairs.get("damage"),
                "idleAnim": staged_weapon_pairs.get("idleAnim"),
                "fireAnim": staged_weapon_pairs.get("fireAnim"),
                "reloadAnim": staged_weapon_pairs.get("reloadAnim"),
                "reloadEmptyAnim": staged_weapon_pairs.get("reloadEmptyAnim"),
                "reloadQuickAnim": staged_weapon_pairs.get("reloadQuickAnim"),
                "reloadQuickEmptyAnim": staged_weapon_pairs.get("reloadQuickEmptyAnim"),
                "reloadTime": staged_weapon_pairs.get("reloadTime"),
                "reloadEmptyTime": staged_weapon_pairs.get("reloadEmptyTime"),
                "reloadQuickTime": staged_weapon_pairs.get("reloadQuickTime"),
                "reloadQuickEmptyTime": staged_weapon_pairs.get("reloadQuickEmptyTime"),
                "firstRaiseAnim": staged_weapon_pairs.get("firstRaiseAnim"),
                "sprintInAnim": staged_weapon_pairs.get("sprintInAnim"),
            },
            "base_fields": {
                "gunModel": base_fields.get("gunModel"),
                "handModel": base_fields.get("handModel"),
                "parentWeaponName": base_fields.get("parentWeaponName"),
                "viewFlashEffect": base_fields.get("viewFlashEffect"),
                "worldFlashEffect": base_fields.get("worldFlashEffect"),
                "ammoName": base_fields.get("ammoName"),
                "clipName": base_fields.get("clipName"),
            },
        },
        "first_person_composition": {
            "active_components": {
                "weapon_shell": WEAPON_ASSET,
                "gunModel": gun_model_info,
                "handModel": hand_model_info,
            },
            "zombie_viewhands_variants": {
                "c_zom_suit_viewhands": suit_viewhands_info,
                "c_zom_hazmat_viewhands": hazmat_viewhands_info,
            },
            "predicted_totals": {
                "c_zom_suit_viewhands": {
                    "nodes": suit_total_nodes,
                    "joints": suit_total_joints,
                    "over_160_nodes": suit_total_nodes > 160,
                    "over_160_joints": suit_total_joints > 160,
                },
                "c_zom_hazmat_viewhands": {
                    "nodes": hazmat_total_nodes,
                    "joints": hazmat_total_joints,
                    "over_160_nodes": hazmat_total_nodes > 160,
                    "over_160_joints": hazmat_total_joints > 160,
                },
            },
            "note": (
                "This is a build-side estimate of first-person DObj composition based on xmodel/glb inputs. "
                "It does not prove what the engine assembled at runtime, but it shows exactly what the weapon asset points at."
            ),
        },
        "script_probe": {
            "template": str(SCRIPT_TEMPLATE),
            "output": str(SCRIPT_OUTPUT),
        },
        "zone_source": str(ZONE_SOURCE_DIR / f"{RUNTIME_ZONE_NAME}.zone"),
        "surface_pipeline": {
            "bundle_report": str(IDG_SURFACE_BUNDLE_REPORT) if IDG_SURFACE_BUNDLE_REPORT.exists() else "",
            "translation_report": str(IDG_SURFACE_TRANSLATION_REPORT) if IDG_SURFACE_TRANSLATION_REPORT.exists() else "",
            "staged_images": STAGED_IMAGE_NAMES,
        },
        "zone_contract": {
            "runtime_zone_source": str(ZONE_SOURCE_DIR / f"{RUNTIME_ZONE_NAME}.zone"),
            "has_runtime_ipak_directive": (
                f">ipak,{RUNTIME_ZONE_NAME}"
                in (ZONE_SOURCE_DIR / f"{RUNTIME_ZONE_NAME}.zone").read_text(encoding="utf-8", errors="replace")
            ),
        },
        "deploy_mode": {
            "to_mod": DEPLOY_TO_MOD,
            "to_base": DEPLOY_TO_BASE,
            "allow_stripped_survival_ff": ALLOW_STRIPPED_SURVIVAL_FF,
            "stub_zm_viewhands": STUB_ZM_VIEWHANDS,
            "use_custom_idg_viewhands": USE_CUSTOM_IDG_VIEWHANDS,
            "force_low_handmodel": FORCE_LOW_HANDMODEL,
            "gun_model_mode": GUN_MODEL_MODE,
            "custom_model_asset": MODEL_ASSET if uses_custom_model() else None,
        },
        "deployed_to": [
            *([str(GAME_MOD_ZONE_DIR), str(STORAGE_MOD_ZONE_DIR)] if DEPLOY_TO_MOD else []),
            *([str(BASE_ZONE_DIR)] if DEPLOY_TO_BASE else []),
            str(STORAGE_MOD_SCRIPT_DIR),
        ],
        "current_blocker": (
            "This build isolates shell and gun-model selection independently. "
            "If the same crash reproduces across shell/model permutations, the failure is outside simple weapondef override priority."
        ),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote debug report -> {REPORT_PATH}")


def main() -> int:
    ensure_dirs()
    clean_output_artifacts()
    render_probe_script()
    stage_model()
    stage_custom_idg_viewhands_asset()
    stage_bridge_viewhands_asset()
    stage_stub_zm_viewhands_assets()
    stage_weapon()
    stage_materials()
    if USE_BO3_IDG_ANIMS:
        convert_anim_bins_to_exports()
    write_zone_source()
    sync_zone_raw_mirror()
    compile_mod_load()
    build_runtime_ff()
    verify_runtime_ff_safety()
    verify_runtime_ipak()
    deploy_outputs()
    build_debug_report()
    print("Apothicon Servant build complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
