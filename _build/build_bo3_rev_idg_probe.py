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
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "_build" / "bo3_rev_idg_probe"
OUTPUT = WORK / "output"
MODEL_EXPORT_DIR = WORK / "model_export"
XMODEL_DIR = WORK / "xmodel"
MATERIALS_DIR = WORK / "materials"
IMAGES_DIR = WORK / "images"
WEAPONS_DIR = WORK / "weapons"
FX_DIR = WORK / "fx"
XANIM_DIR = WORK / "xanim_export" / "viewmodel"
XANIM_REBAKED_DIR = WORK / "xanim_export_rebaked" / "viewmodel"
ZONE_SOURCE_DIR = WORK / "zone_source"
REPORT_PATH = WORK / "build_report.json"
PROBE_WATCHLIST_PATH = ROOT / "native" / "fx_runtime_probe" / "active_probe_watchlist.txt"
ZONE_RAW_ROOT = WORK / "zone_raw" / "so_zsurvival_zm_transit"
IDG_SURFACE_BUNDLE_ROOT = WORK / "idg_surface_bundle"
IDG_SURFACE_PROJECT_ROOT = WORK / "_tmp_idg_surface_project"
IDG_SURFACE_PROJECT_NAME = "bo3_rev_idg_surface"
IDG_SURFACE_TRANSLATION_REPORT = IDG_SURFACE_BUNDLE_ROOT / "material_translation_report.json"
IDG_SURFACE_BUNDLE_REPORT = IDG_SURFACE_BUNDLE_ROOT / "t7_bundle_report.json"
IDG_SURFACE_BLENDER_REPORT = IDG_SURFACE_BUNDLE_ROOT / "blender_material_report.json"
FX_SURFACE_BUNDLE_ROOT = WORK / "fx_surface_bundle"
FX_SURFACE_PROJECT_ROOT = WORK / "_tmp_fx_surface_project"
FX_SURFACE_PROJECT_NAME = "bo3_rev_fx_surface"
FX_SURFACE_TRANSLATION_REPORT = FX_SURFACE_BUNDLE_ROOT / "material_translation_report.json"
FX_SURFACE_BUNDLE_REPORT = FX_SURFACE_BUNDLE_ROOT / "t7_bundle_report.json"
FX_SURFACE_BLENDER_REPORT = FX_SURFACE_BUNDLE_ROOT / "blender_material_report.json"
FX_SURFACE_CLASSIFICATION_REPORT = FX_SURFACE_BUNDLE_ROOT / "fx_surface_classification_report.json"
FX_SURFACE_CONTRACT_REPORT = FX_SURFACE_BUNDLE_ROOT / "fx_surface_contract_report.json"
FX_SURFACE_IMAGE_POLICY_REPORT = FX_SURFACE_BUNDLE_ROOT / "fx_surface_image_policy_report.json"
FX_CONTRACT_CATALOG_REPORT = FX_SURFACE_BUNDLE_ROOT / "fx_contract_catalog.json"
FX_STRUCTURE_REWRITE_REPORT = FX_SURFACE_BUNDLE_ROOT / "fx_structure_rewrite_report.json"
FX_GRAPH_REPORT = ROOT / "_build" / "bo3_idgun_fx_graph.json"
FX_ANALYZER = ROOT / "_build" / "analyze_bo3_idgun_fx.py"
T7_TEXTURE_ASSET_ROOT = Path(r"Z:\Games\T7 Assets V2.5 (2)\T7 Assets V2.5\T7 Assets\texture_assets")

MOD_NAME = "bo3_rev"
MOD_ZONE_NAME = "mod"
MOD_LOAD_ZONE_NAME = "mod_load"
RUNTIME_ZONE_NAME = "so_zsurvival_zm_transit"
RUNTIME_FF_NAME = f"{RUNTIME_ZONE_NAME}.ff"
RUNTIME_IPAK_NAME = f"{RUNTIME_ZONE_NAME}.ipak"

SCRIPT_TEMPLATE = ROOT / "mods" / MOD_NAME / "scripts" / "mod_i_am_mod.gsc.in"
SCRIPT_OUTPUT = ROOT / "mods" / MOD_NAME / "scripts" / "mod_i_am_mod.gsc"
WORK_SCRIPT_OUTPUT = WORK / "scripts" / "mod_i_am_mod.gsc"
CLIENTSCRIPT_TEMPLATE = (
    ROOT / "mods" / MOD_NAME / "clientscripts" / "mp" / "zombies" / "_zm_weap_cymbal_monkey.csc.in"
)
CLIENTSCRIPT_OUTPUT = (
    ROOT / "mods" / MOD_NAME / "clientscripts" / "mp" / "zombies" / "_zm_weap_cymbal_monkey.csc"
)
WORK_CLIENTSCRIPT_OUTPUT = WORK / "clientscripts" / "mp" / "zombies" / "_zm_weap_cymbal_monkey.csc"
CLIENTSCRIPT_ASSET = "clientscripts/mp/zombies/_zm_weap_cymbal_monkey.csc"
TRANSIT_CLIENTSCRIPT_TEMPLATE = ROOT / "mods" / MOD_NAME / "clientscripts" / "mp" / "zm_transit.csc.in"
TRANSIT_CLIENTSCRIPT_OUTPUT = ROOT / "mods" / MOD_NAME / "clientscripts" / "mp" / "zm_transit.csc"
WORK_TRANSIT_CLIENTSCRIPT_OUTPUT = WORK / "clientscripts" / "mp" / "zm_transit.csc"
TRANSIT_CLIENTSCRIPT_ASSET = "clientscripts/mp/zm_transit.csc"
SERVANT_CLIENTSCRIPT_TEMPLATE = (
    ROOT / "mods" / MOD_NAME / "clientscripts" / "mp" / "zombies" / "_bo3_rev_servant_fx.csc.in"
)
SERVANT_CLIENTSCRIPT_OUTPUT = (
    ROOT / "mods" / MOD_NAME / "clientscripts" / "mp" / "zombies" / "_bo3_rev_servant_fx_v3.csc"
)
WORK_SERVANT_CLIENTSCRIPT_OUTPUT = (
    WORK / "clientscripts" / "mp" / "zombies" / "_bo3_rev_servant_fx_v3.csc"
)
SERVANT_CLIENTSCRIPT_ASSET = "clientscripts/mp/zombies/_bo3_rev_servant_fx_v3.csc"
VISIONSET_CLIENTSCRIPT_TEMPLATE = ROOT / "t6-scripts-official" / "ZM1" / "Core" / "clientscripts" / "mp" / "_visionset_mgr.csc"
VISIONSET_CLIENTSCRIPT_OUTPUT = ROOT / "mods" / MOD_NAME / "clientscripts" / "mp" / "_visionset_mgr.csc"
WORK_VISIONSET_CLIENTSCRIPT_OUTPUT = WORK / "clientscripts" / "mp" / "_visionset_mgr.csc"
VISIONSET_CLIENTSCRIPT_ASSET = "clientscripts/mp/_visionset_mgr.csc"

PROBE_SHELL_WEAPON = os.environ.get("ROGUE_PROBE_SHELL", "mg08_zm").strip() or "mg08_zm"
PROBE_STARTER_WEAPON = os.environ.get("ROGUE_STARTER_WEAPON", "m1911_zm").strip() or "m1911_zm"
GUN_MODEL_MODE = os.environ.get("ROGUE_GUN_MODEL_MODE", "custom").strip().lower() or "custom"
GUN_MODEL_LITERAL = os.environ.get("ROGUE_GUN_MODEL_LITERAL", "").strip()
MODEL_ASSET_BASE = os.environ.get("ROGUE_MODEL_ASSET_BASE", "bo3_rev_v2_idg_view").strip() or "bo3_rev_v2_idg_view"
IDG_VIEW_GLB_OVERRIDE = os.environ.get("ROGUE_IDG_VIEW_GLB", "").strip()
USE_T5_GERSH = os.environ.get("ROGUE_USE_T5_GERSH", "0") not in ("0", "false", "False")
USE_MANUAL_IDG_IMAGES = os.environ.get("ROGUE_USE_MANUAL_IDG_IMAGES", "0") not in ("0", "false", "False")
ALLOW_UNSUPPORTED_RAW_FX = os.environ.get("ROGUE_ALLOW_UNSUPPORTED_RAW_FX", "0") not in ("0", "false", "False")
USE_STOCK_FX_MATERIAL_PROBE = os.environ.get("ROGUE_USE_STOCK_FX_MATERIAL_PROBE", "0") not in ("0", "false", "False")
# Keep the stock-triplet transplant on by default until the BO3 FX path is proven visible.
# Earlier test builds silently exercised the original hole_md payload because these values
# defaulted to empty, which made the "forced visible" test invalid.
FX_TRANSPLANT_TARGET = os.environ.get("ROGUE_FX_TRANSPLANT_TARGET", "fx_idgun_hole_md_zod_zmb").strip().lower()
FX_TRANSPLANT_STAGE = os.environ.get("ROGUE_FX_TRANSPLANT_STAGE", "stock_triplet").strip().lower()

BUILD_TAG_SEED = "|".join(
    [
        "rawfxsafe_v1",
        PROBE_SHELL_WEAPON,
        PROBE_STARTER_WEAPON,
        "t5_gersh" if USE_T5_GERSH else "bo3_idg",
        GUN_MODEL_MODE,
        GUN_MODEL_LITERAL,
        IDG_VIEW_GLB_OVERRIDE,
        "bo3" if os.environ.get("ROGUE_USE_BO3_IDG_ANIMS", "1") not in ("0", "false", "False") else "donor",
        "lowhand" if os.environ.get("ROGUE_FORCE_LOW_HANDMODEL", "0") not in ("0", "false", "False") else "basehand",
        "stockfxprobe" if USE_STOCK_FX_MATERIAL_PROBE else "nofxprobe",
        f"servantscope:{os.environ.get('ROGUE_SERVANT_FX_SCOPE', 'full').strip().lower() or 'full'}",
        f"transplant:{FX_TRANSPLANT_TARGET or 'off'}:{FX_TRANSPLANT_STAGE or 'off'}",
    ]
)
BUILD_TAG_PREFIX = datetime.now(timezone.utc).strftime("%m%d%H%M%S")
BUILD_TAG = os.environ.get("ROGUE_BUILD_TAG", "").strip() or f"{BUILD_TAG_PREFIX}_{hashlib.sha1(BUILD_TAG_SEED.encode('utf-8')).hexdigest()[:6]}"
MODEL_ASSET = f"{MODEL_ASSET_BASE}_{BUILD_TAG}" if GUN_MODEL_MODE == "custom" else MODEL_ASSET_BASE
WORLD_MODEL_ASSET = f"{MODEL_ASSET}_world" if USE_T5_GERSH and GUN_MODEL_MODE == "custom" else ""
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
BO3_FX_LIBRARY_ROOT = Path(
    r"C:\Users\Ahmed\Downloads\hb21_elemental_bows_v1.0.0\hb21_black_ops_3_fx_library_v2.1.0"
)
BO3_FX_RAW_ROOT = BO3_FX_LIBRARY_ROOT / "share" / "raw" / "fx"
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
FX_LIT_TEMPLATE = ROOT / "_build" / "runtime_unlink_so_zsurvival_clean" / "materials" / "gfx_fxt_fire_anim_flicker_1.json"
FX_EMISSIVE_TEMPLATE = ROOT / "_build" / "runtime_unlink_so_zsurvival_clean" / "materials" / "gfx_fxt_fire_anim_flicker_1_add.json"
FX_CLOUD_TEMPLATE = ROOT / "_build" / "runtime_unlink_so_zsurvival_clean" / "materials" / "gfx_fxt_debris_fire_ember_cloud_01.json"
FX_DISTORT_TEMPLATE = ROOT / "_build" / "runtime_unlink_so_zsurvival_clean" / "materials" / "gfx_distortion_heat.json"
FX_GLOW_TEMPLATE = ROOT / "zone_dump" / "materials" / "gfx_fxt_light_glow_square_gr.json"
FX_GLOW_IMAGE_DDS = ROOT / "zone_dump" / "images" / "fxt_light_glow_square.dds"
STOCK_FMT0D_DEBUG_MATERIAL_NAME = "ffprobe_stock_fmt0d_glow"
STOCK_FMT0D_IMAGE_NAME = "fxt_debris_fire_ember_cloud_01"
STOCK_FMT0D_IMAGE_IWI = ROOT / "_build" / "stock_iwi_dump" / "images" / f"{STOCK_FMT0D_IMAGE_NAME}.iwi"
STOCK_FULLDDS_DEBUG_MATERIAL_NAME = "ffprobe_stock_fulldds_glow"
STOCK_FULLDDS_IMAGE_NAME = "fxt_light_fluorescent"
STOCK_FULLDDS_IMAGE_DDS = ROOT / "zone_dump" / "images" / f"{STOCK_FULLDDS_IMAGE_NAME}.dds"
PHOSPHOROUS_NATIVE_DEBUG_MATERIAL_NAME = "ffprobe_phosphorous_native_glow"
PHOSPHOROUS_NATIVE_IMAGE_NAME = "fxt_light_phosphorous_native"
PHOSPHOROUS_NATIVE_IMAGE_DDS = ROOT / "zone_dump" / "images" / "fxt_light_phosphorous.dds"
PHOSPHOROUS_SOFT_DEBUG_MATERIAL_NAME = "ffprobe_phosphorous_soft_glow"
PHOSPHOROUS_SOFT_IMAGE_NAME = "fxt_light_phosphorous_soft"
PHOSPHOROUS_BLOOM_DEBUG_MATERIAL_NAME = "ffprobe_phosphorous_bloom_glow"
PHOSPHOROUS_BLOOM_IMAGE_NAME = "fxt_light_phosphorous_bloom"
PHOSPHOROUS_MASK_DEBUG_MATERIAL_NAME = "ffprobe_phosphorous_mask_glow"
PHOSPHOROUS_MASK_IMAGE_NAME = "fxt_light_phosphorous_mask"
PHOSPHOROUS_VARIANT_PREVIEW_DIR = ROOT / "_build" / "source_fx_previews"
PHOSPHOROUS_VARIANTS: dict[str, dict[str, str]] = {
    "native": {
        "asset": "zombie/fx_ffprobe_debug_orb_phosphorous_native",
        "material": PHOSPHOROUS_NATIVE_DEBUG_MATERIAL_NAME,
        "image": PHOSPHOROUS_NATIVE_IMAGE_NAME,
        "mode": "dds_native",
    },
    "soft": {
        "asset": "zombie/fx_ffprobe_debug_orb_phosphorous_soft",
        "material": PHOSPHOROUS_SOFT_DEBUG_MATERIAL_NAME,
        "image": PHOSPHOROUS_SOFT_IMAGE_NAME,
        "mode": "phosphorous_soft",
    },
    "bloom": {
        "asset": "zombie/fx_ffprobe_debug_orb_phosphorous_bloom",
        "material": PHOSPHOROUS_BLOOM_DEBUG_MATERIAL_NAME,
        "image": PHOSPHOROUS_BLOOM_IMAGE_NAME,
        "mode": "phosphorous_bloom",
    },
    "hot": {
        "asset": "zombie/fx_ffprobe_debug_orb_phosphorous_hot",
        "material": "ffprobe_phosphorous_hot_glow",
        "image": "fxt_light_phosphorous_hot",
        "mode": "phosphorous_hot",
    },
    "mask": {
        "asset": "zombie/fx_ffprobe_debug_orb_phosphorous_mask",
        "material": PHOSPHOROUS_MASK_DEBUG_MATERIAL_NAME,
        "image": PHOSPHOROUS_MASK_IMAGE_NAME,
        "mode": "phosphorous_mask",
    },
}
FX_SMOKE_TEMPLATE = ROOT / "zone_dump" / "materials" / "gfx_fxt_smk_gen_eo2_fog.json"
FX_SIMPLE_ALPHA_TEMPLATE = ROOT / "zone_dump" / "materials" / "gfx_fxt_env_water_ripple.json"
FX_BURST_TEMPLATE = ROOT / "zone_dump" / "materials" / "gfx_fxt_exp_ember_omni.json"
FX_DECAL_TEMPLATE = ROOT / "zone_dump" / "materials" / "mc" / "mtl_fx_decal_burnt_paper.json"
FX_LIT_IMPACT_TEMPLATE = ROOT / "zone_dump" / "zone_raw" / "zm_tomb" / "materials" / "mc" / "gfx_impact_metal05_blend.json"
TRANSIT_OVERLAY_MATERIAL_NAME = "zombie_transporter_overlay"
TRANSIT_OVERLAY_IMAGE_NAME = "fxt_light_glow_square"
FX_FAMILY_SPECS: dict[str, dict[str, object]] = {
    "billboard_additive_glow": {
        "template": FX_GLOW_TEMPLATE,
        "camera_region": "emissiveFx",
        "default_technique_set": "effect_26z423jf",
        "image_policy": "preserve_translator_output",
        "stock_refs": ["gfx_fxt_light_glow_square_gr"],
        "notes": "Pure emissive additive glow cards and orb hotspots.",
    },
    "billboard_soft_smoke": {
        "template": FX_SMOKE_TEMPLATE,
        "camera_region": "emissiveFx",
        "default_technique_set": "effect_jz61190f",
        "image_policy": "preserve_translator_output",
        "stock_refs": ["gfx_fxt_smk_gen_eo2_fog", "gfx_flamethrower_smoke_add_z100"],
        "notes": "Soft-particle smoke, fog, and ember cloud sprites.",
    },
    "billboard_simple_alpha": {
        "template": FX_SIMPLE_ALPHA_TEMPLATE,
        "camera_region": "emissiveFx",
        "default_technique_set": "effect_842ee834",
        "image_policy": "preserve_translator_output",
        "stock_refs": ["gfx_fxt_env_water_ripple"],
        "notes": "Masked translucent sprites and ripple-style cards.",
    },
    "billboard_distortion": {
        "template": FX_DISTORT_TEMPLATE,
        "camera_region": "emissiveFx",
        "default_technique_set": "distortion_81587199",
        "image_policy": "preserve_translator_output",
        "stock_refs": ["gfx_distortion_heat"],
        "notes": "Heat-haze and refraction shells that need distortion semantics.",
    },
    "burst_emissive": {
        "template": FX_BURST_TEMPLATE,
        "camera_region": "emissiveFx",
        "default_technique_set": "effect_z0z25860",
        "image_policy": "preserve_translator_output",
        "stock_refs": ["gfx_fxt_exp_ember_omni"],
        "notes": "Short-lived flashes, ember bursts, and electric hits.",
    },
    "decal_surface_hit": {
        "template": FX_DECAL_TEMPLATE,
        "camera_region": "litTrans",
        "default_technique_set": "effect_842ee834",
        "image_policy": "preserve_translator_output",
        "stock_refs": ["mtl_fx_decal_burnt_paper", "gfx_impact_metal05_blend"],
        "notes": "Surface-projected decals and hit materials.",
    },
    "lit_debris_impact": {
        "template": FX_LIT_IMPACT_TEMPLATE,
        "camera_region": "emissiveFx",
        "default_technique_set": "effect_jz61190f",
        "image_policy": "preserve_translator_output",
        "stock_refs": ["gfx_impact_metal05_blend"],
        "notes": "Lit debris, impact shards, and dust-like sprite payloads.",
    },
}
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
STAGED_MODEL_IMAGE_NAMES: list[str] = []
STAGED_FX_IMAGE_NAMES: list[str] = []
STAGED_FX_NAMES: list[str] = []
STAGED_FX_MATERIAL_NAMES: list[str] = []
RAW_FX_COMPAT_REPORT: dict[str, object] = {}
BO3_FX_SURFACE_META: dict[str, dict[str, object]] = {}
RAW_FX_STRUCTURE_REPORT: dict[str, object] = {}

RAW_FX_STAGE_ORDER = {
    "off": 0,
    "muzzle": 1,
    "projectile": 2,
    "impact": 3,
    "full": 4,
}

BO3_ANIM_STAGES = {
    "off",
    "fireonly",
    "idleonly",
    "idlefire",
    "spawn",
    "full",
}

HB21_SOURCE_IMAGE_OVERRIDES = {
    "fxt_debri_trash_multiple": BO3_FX_LIBRARY_ROOT / "texture_assets" / "black_ops_3" / "gfx" / "fxt_debris_clump_dirt.tiff",
    "fxt_debris_trash_multiple": BO3_FX_LIBRARY_ROOT / "texture_assets" / "black_ops_3" / "gfx" / "fxt_debris_clump_dirt.tiff",
    "fxt_debris_clump": BO3_FX_LIBRARY_ROOT / "texture_assets" / "black_ops_3" / "gfx" / "fxt_debris_clump_dirt.tiff",
    "fxt_distort_ring_ripple": BO3_FX_LIBRARY_ROOT / "texture_assets" / "black_ops_3" / "gfx" / "fxt_distort_ring_hvy.tiff",
    "fxt_dust_gen": BO3_FX_LIBRARY_ROOT / "texture_assets" / "waw" / "fx" / "fxt_env_dust_mote.tif",
    "fxt_fire_flame_base": T7_TEXTURE_ASSET_ROOT / "_midgetblaster" / "t7_gfx" / "fxt_fire_flame_base_1_anim_hi_res.png",
    "fxt_fire_flame_base_2_anim": T7_TEXTURE_ASSET_ROOT / "_midgetblaster" / "t7_gfx" / "fxt_fire_flame_base_2_anim_hi_res.png",
    "fxt_fire_flame_base_2": T7_TEXTURE_ASSET_ROOT / "_midgetblaster" / "t7_gfx" / "fxt_fire_flame_base_2_anim_hi_res.png",
    "fxt_fog_slow_lg_anim": BO3_FX_LIBRARY_ROOT / "texture_assets" / "black_ops_3" / "gfx" / "fxt_smk_rolling_dense_lg_anim.tiff",
    "fxt_fog_slow_md_anim": BO3_FX_LIBRARY_ROOT / "texture_assets" / "black_ops_3" / "gfx" / "fxt_smk_trail_wispy.tiff",
    "fxt_fog_slow_sm_anim": BO3_FX_LIBRARY_ROOT / "texture_assets" / "black_ops_2" / "effect" / "i_fxt_smk_whisp_spiral.tiff",
    "fxt_gel_splat_side": BO3_FX_LIBRARY_ROOT / "texture_assets" / "black_ops_3" / "gfx" / "fxt_gel_splat_wide.tiff",
    "fxt_gel_splat_radial": BO3_FX_LIBRARY_ROOT / "texture_assets" / "black_ops_3" / "gfx" / "fxt_gel_splat_full.tiff",
    "fxt_gel_splat_spread": BO3_FX_LIBRARY_ROOT / "texture_assets" / "black_ops_3" / "gfx" / "fxt_gel_splat_wide.tiff",
    "fxt_light_phosphorous": BO3_FX_LIBRARY_ROOT / "texture_assets" / "waw" / "fx" / "fxt_light_phosphorous.tif",
    "fxt_shockwave_anim_1": BO3_FX_LIBRARY_ROOT / "texture_assets" / "black_ops_2" / "effect" / "i_fxt_fx_emp_ring_wave.tiff",
    "fxt_shockwave_elec_anim": BO3_FX_LIBRARY_ROOT / "texture_assets" / "black_ops_2" / "effect" / "i_fxt_fx_emp_ring_wave.tiff",
    "fxt_smk_cigar_whisp": BO3_FX_LIBRARY_ROOT / "texture_assets" / "black_ops_2" / "effect" / "i_fxt_smk_cigar.tiff",
    "fxt_smk_puff_light_varied": BO3_FX_LIBRARY_ROOT / "texture_assets" / "waw" / "fx" / "fxt_smk_light.tif",
    "fxt_smk_whisp_anim": BO3_FX_LIBRARY_ROOT / "texture_assets" / "black_ops_2" / "effect" / "i_fxt_smk_whisp_spiral.tiff",
    "fxt_spark_blink_anim": BO3_FX_LIBRARY_ROOT / "texture_assets" / "black_ops_3" / "gfx" / "fxt_spark_blink_anim_blue.tiff",
    "fxt_spark_omni": BO3_FX_LIBRARY_ROOT / "texture_assets" / "black_ops_3" / "gfx" / "fxt_spark_single.tiff",
    "fxt_water_bubble": T7_TEXTURE_ASSET_ROOT / "_midgetblaster" / "t7_gfx" / "fxt_water_bubble_pcloud.tiff",
    "fxt_water_splash": T7_TEXTURE_ASSET_ROOT / "_midgetblaster" / "t7_gfx" / "fxt_water_splash_gush_anim.tiff",
}

HB21_ASSET_ALIASES = {
    # The hb21 BO3 FX library references these explosion decal materials from
    # multiple .efx graphs, but does not expose matching material.gdf assets
    # under the same names. Use the closest shipped decal impact material so
    # the graph can stage and the raw-FX path can keep progressing.
    "gfx_decal_exp_blast_01": "gfx_decal_blast_white_01",
    "gfx_decal_exp_blast_03": "gfx_decal_blast_white_01",
}

T5_GERSH_BUNDLE_ROOT = ROOT / "_build" / "t5_gersh_bundle"
T5_GERSH_VIEW_GLB_SRC = T5_GERSH_BUNDLE_ROOT / "model_export" / "t5_bh_bomb_viewmodel_lod0.glb"
T5_GERSH_WORLD_GLB_SRC = T5_GERSH_BUNDLE_ROOT / "model_export" / "t5_bh_bomb_world_lod0.glb"
T5_GERSH_VIEW_JSON_SRC = T5_GERSH_BUNDLE_ROOT / "xmodel" / "t5_bh_bomb_viewmodel.json"
T5_GERSH_WORLD_JSON_SRC = T5_GERSH_BUNDLE_ROOT / "xmodel" / "t5_bh_bomb_world.json"
T5_GERSH_MATERIAL_LINE = "mc/mtl_t5_weapon_bh_bomb"
T5_GERSH_MATERIAL_JSON = MATERIALS_DIR / "mc" / "mtl_t5_weapon_bh_bomb.json"
T5_GERSH_MATERIAL_TEMPLATE = ROOT / "zone_dump" / "zone_raw" / "zm_tomb" / "materials" / "mc" / "mtl_t6_wpn_zmb_monkey_bomb.json"
T5_GERSH_VIEW_GLB_DST = MODEL_EXPORT_DIR / f"{MODEL_ASSET}_lod0.glb"
T5_GERSH_WORLD_GLB_DST = MODEL_EXPORT_DIR / f"{WORLD_MODEL_ASSET}_lod0.glb"

IWI_HEADER_SIZE = 64
IWI_MAGIC = b"IWi"
IWI_VERSION = 0x1B
IWI_FORMAT_DXT5 = 0x0D
IWI_FORMAT_DXN = 0x0E
DDS_MAGIC = b"DDS "
DDS_HEADER_SIZE = 124
DXGI_FORMAT_BC5_UNORM = 83
DXGI_FORMAT_BC5_SNORM = 84

IDG_SPEC_RGB_SCALE = 0.05
IDG_SPEC_ALPHA_SCALE = 0.02
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
IDG_SPEC_IMAGE_NAMES = [
    "i_wpn_t7_zmb_zod_tentacle_ambient_g",
    "i_wpn_t7_zmb_zod_tentacle_claw_g",
    "i_wpn_t7_zmb_zod_idg_ammo_s",
]

GAME_MOD_ZONE_DIR = ROOT / "mods" / MOD_NAME / "zone" / "all"
GAME_MOD_SCRIPT_DIR = ROOT / "mods" / MOD_NAME / "scripts"
STORAGE_MOD_ROOT = Path(os.path.expandvars(rf"%LOCALAPPDATA%\Plutonium\storage\t6\mods\{MOD_NAME}"))
STORAGE_MOD_ZONE_DIR = STORAGE_MOD_ROOT / "zone" / "all"
STORAGE_MOD_SCRIPT_DIR = STORAGE_MOD_ROOT / "scripts"
GAME_MOD_CLIENTSCRIPT_DIR = ROOT / "mods" / MOD_NAME / "clientscripts" / "mp" / "zombies"
STORAGE_MOD_CLIENTSCRIPT_DIR = STORAGE_MOD_ROOT / "clientscripts" / "mp" / "zombies"
STORAGE_LOOSE_IMAGE_DIR = Path(os.path.expandvars(r"%LOCALAPPDATA%\Plutonium\storage\t6\images"))
SKIP_LOOSE_RUNTIME_IMAGES = {"$identitynormalmap"}


def should_skip_loose_runtime_image(image_name: str) -> bool:
    if image_name in SKIP_LOOSE_RUNTIME_IMAGES:
        return True
    return image_name in set(STAGED_FX_IMAGE_NAMES or [])
BASE_ZONE_DIR = ROOT / "zone" / "all"

DEPLOY_TO_MOD = os.environ.get("ROGUE_DEPLOY_TO_MOD", "1") not in ("0", "false", "False")
# The client resolves `so_zsurvival_zm_transit.ff` from the base zone lane in
# practice, so mod-only deploys leave the server on the new build while the
# client keeps executing a stale fastfile script body.
DEPLOY_TO_BASE = os.environ.get("ROGUE_DEPLOY_TO_BASE", "1") not in ("0", "false", "False")
USE_BO3_IDG_ANIMS = os.environ.get("ROGUE_USE_BO3_IDG_ANIMS", "0") not in ("0", "false", "False")
BO3_ANIM_STAGE = os.environ.get("ROGUE_BO3_ANIM_STAGE", "full" if USE_BO3_IDG_ANIMS else "off").strip().lower()
BO3_ANIM_EMIT_MODE = os.environ.get("ROGUE_BO3_ANIM_EMIT_MODE", "bo3_frames").strip().lower() or "bo3_frames"
BO3_ANIM_FORCE_IDENTITY = os.environ.get("ROGUE_BO3_ANIM_FORCE_IDENTITY", "0") not in ("0", "false", "False")
USE_REBAKED_BO3_XANIMS = os.environ.get("ROGUE_USE_REBAKED_BO3_XANIMS", "1" if USE_BO3_IDG_ANIMS else "0") not in ("0", "false", "False")
BO3_ANIM_DONOR_FF_OVERRIDE = os.environ.get("ROGUE_BO3_ANIM_DONOR_FF", "").strip()
BO3_ANIM_DONOR_ZONE = os.environ.get("ROGUE_BO3_ANIM_DONOR_ZONE", "mod_load").strip() or "mod_load"
BO3_ANIM_DONOR_ASSET = os.environ.get("ROGUE_BO3_ANIM_DONOR_ASSET", "vm_zod_id_gun_idle").strip() or "vm_zod_id_gun_idle"
ALLOW_STRIPPED_SURVIVAL_FF = os.environ.get("ROGUE_ALLOW_STRIPPED_SURVIVAL_FF", "0") not in ("0", "false", "False")
STUB_ZM_VIEWHANDS = os.environ.get("ROGUE_STUB_ZM_VIEWHANDS", "0") not in ("0", "false", "False")
USE_CUSTOM_IDG_VIEWHANDS = os.environ.get("ROGUE_USE_CUSTOM_IDG_VIEWHANDS", "0") not in ("0", "false", "False")
FORCE_LOW_HANDMODEL = os.environ.get("ROGUE_FORCE_LOW_HANDMODEL", "0") not in ("0", "false", "False")
USE_BO3_RAW_FX = os.environ.get("ROGUE_USE_BO3_RAW_FX", "0") not in ("0", "false", "False")
RAW_FX_STAGE = os.environ.get("ROGUE_BO3_RAW_FX_STAGE", "full" if USE_BO3_RAW_FX else "off").strip().lower()
RAW_FX_STRICT = os.environ.get("ROGUE_BO3_RAW_FX_STRICT", "0") not in ("0", "false", "False")
USE_DEDICATED_BO3_FX_LOAD = os.environ.get("ROGUE_USE_BO3_FX_LOAD_FF", "1" if USE_BO3_RAW_FX else "0") not in (
    "0",
    "false",
    "False",
)
ALLOW_UNVERIFIED_DEDICATED_BO3_FX_LOAD = os.environ.get(
    "ROGUE_ALLOW_UNVERIFIED_BO3_FX_LOAD", "0"
) not in ("0", "false", "False")
ALLOW_UNVERIFIED_CUSTOM_LINKER_PROBE = os.environ.get(
    "ROGUE_ALLOW_UNVERIFIED_CUSTOM_LINKER_PROBE", "0"
) not in ("0", "false", "False")
BO3_FX_LOAD_ZONE_NAME = os.environ.get("ROGUE_BO3_FX_LOAD_ZONE", MOD_LOAD_ZONE_NAME).strip() or MOD_LOAD_ZONE_NAME
BO3_FX_LOAD_FF_NAME = f"{BO3_FX_LOAD_ZONE_NAME}.ff"
BO3_FX_LOAD_IPAK_NAME = f"{BO3_FX_LOAD_ZONE_NAME}.ipak"
USE_BO3_SERVANT_CLIENT_FX = os.environ.get("ROGUE_USE_BO3_SERVANT_CLIENT_FX", "1" if USE_BO3_RAW_FX else "0") not in (
    "0",
    "false",
    "False",
)
CLIENT_FFPROBE_ASSET = os.environ.get("ROGUE_CLIENT_FFPROBE_ASSET", "").strip()
INCLUDE_FX_DEBUG_PROBES = os.environ.get("ROGUE_INCLUDE_FX_DEBUG_PROBES", "0") not in ("0", "false", "False")
if RAW_FX_STAGE not in RAW_FX_STAGE_ORDER:
    RAW_FX_STAGE = "full" if USE_BO3_RAW_FX else "off"
if BO3_ANIM_STAGE not in BO3_ANIM_STAGES:
    BO3_ANIM_STAGE = "full" if USE_BO3_IDG_ANIMS else "off"
SKIP_LOOSE_IMAGE_DEPLOY = os.environ.get("ROGUE_SKIP_LOOSE_IMAGE_DEPLOY", "0") not in ("0", "false", "False")
SKIP_SCRIPT_SYNC = os.environ.get("ROGUE_SKIP_SCRIPT_SYNC", "0") not in ("0", "false", "False")
REQUIRE_APPDATA_SYNC = os.environ.get("ROGUE_REQUIRE_APPDATA_SYNC", "0") not in ("0", "false", "False")
USE_PROCESSED_IDG_IMAGES = os.environ.get("ROGUE_USE_PROCESSED_IDG_IMAGES", "0") not in ("0", "false", "False")
USE_STOCK_IDG_IMAGES = os.environ.get("ROGUE_USE_STOCK_IDG_IMAGES", "0") not in ("0", "false", "False")
USE_FULL_ZONE_SOURCE = os.environ.get("ROGUE_USE_FULL_ZONE_SOURCE", "1" if DEPLOY_TO_BASE else "0") not in (
    "0",
    "false",
    "False",
)
USE_MAP_FULL_ZONE_SOURCE = os.environ.get("ROGUE_USE_MAP_FULL_ZONE_SOURCE", "0") not in (
    "0",
    "false",
    "False",
)
SAFE_FULL_SERVANT_SURFACE_DOWNGRADE = os.environ.get(
    "ROGUE_SAFE_FULL_SERVANT_SURFACE_DOWNGRADE", "1"
) not in ("0", "false", "False")
SERVANT_FX_SCOPE = os.environ.get("ROGUE_SERVANT_FX_SCOPE", "full").strip().lower() or "full"
SERVANT_VORTEX_DEBUG_MARKERS = os.environ.get(
    "ROGUE_SERVANT_VORTEX_DEBUG_MARKERS", "0"
) not in ("0", "false", "False")
if SERVANT_FX_SCOPE not in {"full", "vortex_core"}:
    SERVANT_FX_SCOPE = "full"

if USE_DEDICATED_BO3_FX_LOAD and USE_BO3_IDG_ANIMS and BO3_FX_LOAD_ZONE_NAME == MOD_LOAD_ZONE_NAME:
    raise RuntimeError(
        "BO3 raw FX dedicated load lane currently collides with the runtime xanim lane on mod_load.ff. "
        "Disable ROGUE_USE_BO3_IDG_ANIMS or set ROGUE_BO3_FX_LOAD_ZONE to a different zone while implementing a merged lane."
    )


def choose_blender_executable(configured: str) -> str:
    candidates = [configured]
    if configured.lower() == "blender":
        candidates += [
            r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
        ]
    for candidate in candidates:
        candidate_path = Path(candidate)
        if candidate_path.exists():
            return str(candidate_path)
        if shutil.which(candidate):
            return candidate
    return configured


def active_script_output() -> Path:
    if DEPLOY_TO_MOD or DEPLOY_TO_BASE:
        return SCRIPT_OUTPUT
    return WORK_SCRIPT_OUTPUT


def probe_only_fast_path_enabled() -> bool:
    if not client_ffprobe_enabled():
        return False
    return os.environ.get("ROGUE_PROBE_ONLY_FAST_PATH", "1") not in ("0", "false", "False")


def clientscript_override_enabled() -> bool:
    return (USE_BO3_SERVANT_CLIENT_FX and USE_BO3_RAW_FX) or bool(CLIENT_FFPROBE_ASSET)


def client_ffprobe_enabled() -> bool:
    return bool(CLIENT_FFPROBE_ASSET)


def phosphorous_variant_spec_for_asset(asset: str) -> dict[str, str] | None:
    for spec in PHOSPHOROUS_VARIANTS.values():
        if spec["asset"] == asset:
            return spec
    return None


def requested_client_ffprobe_bo3_fx_asset() -> str:
    if not client_ffprobe_enabled():
        return ""
    if not CLIENT_FFPROBE_ASSET.startswith("zombie/"):
        return ""
    return CLIENT_FFPROBE_ASSET


def resolve_fx_source_path(fx_name: str) -> Path | None:
    if not fx_name.startswith("zombie/"):
        return None
    rel = fx_name.split("/", 1)[1] + ".efx"
    candidates = [
        FX_DIR / "zombie" / Path(rel).name,
        BO3_FX_RAW_ROOT / "zombie" / Path(rel).name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def client_ffprobe_bo3_fx_asset() -> str:
    probe_name = requested_client_ffprobe_bo3_fx_asset()
    if not probe_name:
        return ""
    if resolve_fx_source_path(probe_name) is None:
        return ""
    return probe_name


def active_client_ffprobe_asset() -> str:
    return CLIENT_FFPROBE_ASSET.strip()


def client_ffprobe_uses_custom_debug_orb() -> bool:
    probe_name = requested_client_ffprobe_bo3_fx_asset()
    return probe_name.startswith("zombie/fx_ffprobe_debug_orb_")


def active_fx_surface_source_names() -> list[str]:
    probe_name = requested_client_ffprobe_bo3_fx_asset()
    if client_ffprobe_uses_custom_debug_orb() and probe_name:
        return [probe_name]

    names = list(bo3_servant_raw_fx_staged_names())
    if probe_name and probe_name not in names:
        names.append(probe_name)
    return names


def client_ffprobe_runtime_dependencies() -> dict[str, list[str]]:
    asset = CLIENT_FFPROBE_ASSET.strip()
    deps: dict[str, list[str]] = {
        "fx": [],
        "materials": [],
        "images": [],
    }
    if asset.startswith("zombie/"):
        deps["fx"].append(asset)

    phosphorous_spec = phosphorous_variant_spec_for_asset(asset)
    if phosphorous_spec is not None:
        deps["materials"].append(phosphorous_spec["material"])
        deps["images"].append(phosphorous_spec["image"])
    elif asset == "zombie/fx_ffprobe_debug_orb_stock":
        deps["materials"].append("bo3_rev_debug_stock_glow")
        deps["images"].append("fxt_light_glow_square")
    elif asset == "zombie/fx_ffprobe_debug_orb_phosphorous":
        deps["materials"].append("gfx_light_phosphorous_em")
        deps["images"].append("fxt_light_phosphorous")
    elif asset == "zombie/fx_ffprobe_debug_orb_stock_fmt0d":
        deps["materials"].append(STOCK_FMT0D_DEBUG_MATERIAL_NAME)
        deps["images"].append(STOCK_FMT0D_IMAGE_NAME)
    elif asset == "zombie/fx_ffprobe_debug_orb_stock_fulldds":
        deps["materials"].append(STOCK_FULLDDS_DEBUG_MATERIAL_NAME)
        deps["images"].append(STOCK_FULLDDS_IMAGE_NAME)
    return deps


def client_ffprobe_watch_entries() -> list[tuple[str, str]]:
    if not client_ffprobe_enabled():
        return []

    asset = CLIENT_FFPROBE_ASSET.strip()
    entries: list[tuple[str, str]] = [
        ("build", BUILD_TAG),
        ("asset", asset),
        ("file", RUNTIME_FF_NAME),
        ("file", f"{MOD_LOAD_ZONE_NAME}.ff"),
        ("file", f"{MOD_LOAD_ZONE_NAME}.ipak"),
    ]
    deps = client_ffprobe_runtime_dependencies()
    entries.extend(("material", name) for name in deps["materials"])
    entries.extend(("image", name) for name in deps["images"])
    if deps["materials"] or deps["images"]:
        entries.append(("techset", "effect_26z423jf"))

    seen: set[tuple[str, str]] = set()
    deduped: list[tuple[str, str]] = []
    for entry in entries:
        if entry in seen:
            continue
        seen.add(entry)
        deduped.append(entry)
    return deduped


def full_servant_watch_entries() -> list[tuple[str, str]]:
    if client_ffprobe_enabled():
        return []
    if not clientscript_override_enabled() or not USE_BO3_RAW_FX:
        return []

    entries: list[tuple[str, str]] = [
        ("build", BUILD_TAG),
        ("mode", f"servant_{SERVANT_FX_SCOPE}"),
        ("file", RUNTIME_FF_NAME),
        ("file", f"{MOD_LOAD_ZONE_NAME}.ff"),
        ("file", f"{MOD_LOAD_ZONE_NAME}.ipak"),
    ]
    entries.extend(("fx", name) for name in STAGED_FX_NAMES)
    entries.extend(("material", name) for name in STAGED_FX_MATERIAL_NAMES)
    entries.extend(("image", name) for name in STAGED_FX_IMAGE_NAMES)
    entries.extend(("techset", name) for name in staged_fx_techset_names())

    seen: set[tuple[str, str]] = set()
    deduped: list[tuple[str, str]] = []
    for entry in entries:
        if entry in seen:
            continue
        seen.add(entry)
        deduped.append(entry)
    return deduped


def probe_watch_entries() -> list[tuple[str, str]]:
    if client_ffprobe_enabled():
        return client_ffprobe_watch_entries()
    return full_servant_watch_entries()


def staged_fx_techset_names() -> list[str]:
    names: list[str] = []
    for material_name in sorted(set(STAGED_FX_MATERIAL_NAMES)):
        material_path = MATERIALS_DIR / f"{material_name}.json"
        if not material_path.exists():
            continue
        try:
            material_data = json.loads(material_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        techset = str(material_data.get("techniqueSet") or "").strip()
        if techset and techset not in names:
            names.append(techset)
    return names


def write_probe_watchlist() -> None:
    entries = probe_watch_entries()
    PROBE_WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not entries:
        PROBE_WATCHLIST_PATH.write_text("", encoding="utf-8")
        return

    lines = [f"{kind}={value}" for kind, value in entries if value]
    PROBE_WATCHLIST_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote probe watchlist -> {PROBE_WATCHLIST_PATH}")


def render_client_ffprobe_script() -> str:
    return f"""// Minimal clientside FF probe helper rendered by build_bo3_rev_idg_probe.py.
// Uses the proven full so_zsurvival_zm_transit ownership path instead of mod_patch.

init()
{{
    println( "[ffprobe][csc] helper init reached build=__BUILD_TAG__" );
    if ( isdefined( level.ffprobe_client_init ) )
        return;

    level.ffprobe_client_init = 1;
    level.ffprobe_asset_name = "{CLIENT_FFPROBE_ASSET}";
    level.ffprobe_bo3_fx = loadfx( "{CLIENT_FFPROBE_ASSET}" );
    level.ffprobe_original_entityspawned_override = level._entityspawned_override;
    level._entityspawned_override = ::ffprobe_entityspawned_override;

    println(
        "[ffprobe][csc] init asset=" + level.ffprobe_asset_name
        + ";bo3=" + ffprobe_fx_ok( level.ffprobe_bo3_fx )
        + ";build=__BUILD_TAG__"
    );
}}

ffprobe_fx_ok( fx )
{{
    return isdefined( fx ) && fx;
}}

ffprobe_entityspawned_override( localclientnum )
{{
    println(
        "[ffprobe][csc] entityspawned type=" + ffprobe_safe_str( self.type )
        + ";localclient=" + localclientnum
    );

    if ( isdefined( level.ffprobe_original_entityspawned_override ) )
        self thread [[ level.ffprobe_original_entityspawned_override ]]( localclientnum );

    if ( isdefined( self.type ) && self.type == "player" )
        self thread ffprobe_play_on_spawn( localclientnum );
}}

ffprobe_play_on_spawn( localclientnum )
{{
    self endon( "disconnect" );

    while ( !clienthassnapshot( localclientnum ) )
        wait 0.05;

    wait 1.0;

    bo3_origin = self.origin + vectorscale( anglestoforward( self.angles ), 144 );
    bo3_origin = bo3_origin + ( 0, 0, 64 );

    println(
        "[ffprobe][csc] spawn play asset=" + level.ffprobe_asset_name
        + ";bo3=" + ffprobe_fx_ok( level.ffprobe_bo3_fx )
        + ";localclient=" + localclientnum
        + ";bo3_origin=" + bo3_origin
    );

    if ( ffprobe_fx_ok( level.ffprobe_bo3_fx ) )
    {{
        playfx( localclientnum, level.ffprobe_bo3_fx, bo3_origin );
        wait 0.25;
        playfx( localclientnum, level.ffprobe_bo3_fx, bo3_origin );
        wait 0.25;
        playfx( localclientnum, level.ffprobe_bo3_fx, bo3_origin );
    }}
}}

ffprobe_safe_str( value )
{{
    if ( !isdefined( value ) )
        return "<undef>";

    return value;
}}
"""


def active_clientscript_assets() -> list[str]:
    if not clientscript_override_enabled():
        return []
    assets = [
        TRANSIT_CLIENTSCRIPT_ASSET,
        SERVANT_CLIENTSCRIPT_ASSET,
    ]
    if client_ffprobe_enabled():
        assets.append(VISIONSET_CLIENTSCRIPT_ASSET)
    return assets


def render_client_ffprobe_visionset_mgr() -> str:
    if not VISIONSET_CLIENTSCRIPT_TEMPLATE.exists():
        raise FileNotFoundError(f"Missing visionset manager template: {VISIONSET_CLIENTSCRIPT_TEMPLATE}")
    rendered = VISIONSET_CLIENTSCRIPT_TEMPLATE.read_text(encoding="utf-8", errors="replace")
    rendered = rendered.replace(
        "overlay_update_cb( localclientnum, type )\n{",
        'overlay_update_cb( localclientnum, type )\n{\n    println( "[ffprobe][vsmgr] overlay_update_cb localclient=" + localclientnum );',
        1,
    )
    rendered = rendered.replace(
        "                setburn( localclientnum, 0 );",
        '                println( "[ffprobe][vsmgr] suppress clear burn prev=" + prev_info.name + ";localclient=" + localclientnum );',
    )
    rendered = rendered.replace(
        "                setburn( localclientnum, curr_info.duration * state.curr_lerp );",
        '                println( "[ffprobe][vsmgr] suppress apply burn curr=" + curr_info.name + ";localclient=" + localclientnum + ";lerp=" + state.curr_lerp );',
    )
    return rendered


def active_server_script_assets() -> list[str]:
    return []


def full_zone_source_root() -> Path:
    if USE_MAP_FULL_ZONE_SOURCE:
        return TRANSIT_UNLINK_ROOT
    return FULL_RUNTIME_SOURCE_ROOT


def full_zone_source_path() -> Path:
    if USE_MAP_FULL_ZONE_SOURCE:
        return FULL_MAP_ZONE_SOURCE
    return FULL_RUNTIME_ZONE_SOURCE


def raw_fx_stage_level() -> int:
    return RAW_FX_STAGE_ORDER.get(RAW_FX_STAGE, 0)


def raw_fx_stage_enabled(name: str) -> bool:
    return raw_fx_stage_level() >= RAW_FX_STAGE_ORDER[name]


def bo3_anim_field_group(field_name: str) -> str:
    f = (field_name or "").lower()
    if f in (
        "fireintroanim",
        "fireanim",
        "fireanimleft",
        "holdfireanim",
        "lastshotanim",
        "lastshotanimleft",
        "adsfireanim",
        "adslastshotanim",
        "adsfireintroanim",
        "contfireinanim",
        "contfireloopanim",
        "contfireoutanim",
    ):
        return "fire"
    if f in (
        "idleanim",
        "idleanimleft",
        "emptyidleanim",
        "emptyidleanimleft",
    ):
        return "idle"
    if f in (
        "raiseanim",
        "dropanim",
        "firstraiseanim",
        "altraiseanim",
        "altdropanim",
        "quickraiseanim",
        "quickdropanim",
        "emptyraiseanim",
        "emptydropanim",
    ):
        return "equip"
    return "other"


def bo3_anim_field_enabled(field_name: str) -> bool:
    if not USE_BO3_IDG_ANIMS:
        return False
    if BO3_ANIM_STAGE == "full":
        return True
    group = bo3_anim_field_group(field_name)
    if BO3_ANIM_STAGE == "off":
        return False
    if BO3_ANIM_STAGE == "fireonly":
        return group == "fire"
    if BO3_ANIM_STAGE == "idleonly":
        return group == "idle"
    if BO3_ANIM_STAGE == "idlefire":
        return group in ("idle", "fire")
    if BO3_ANIM_STAGE == "spawn":
        return group in ("idle", "fire", "equip")
    return False


def bo3_servant_raw_fx_zone_names() -> list[str]:
    if not USE_BO3_RAW_FX:
        return []

    if SERVANT_FX_SCOPE == "vortex_core":
        return [
            "zombie/fx_idgun_ground_displace_zod_zmb",
            "zombie/fx_idgun_vortex_explo_zod_zmb",
            "zombie/fx_idgun_vortex_zod_zmb",
            "zombie/fx_idgun_hole_lg_zod_zmb",
            "zombie/fx_idgun_hole_sm_zod_zmb",
            "zombie/fx_idgun_hole_xsm_zod_zmb",
            "zombie/fx_idgun_hole_xl_zod_zmb",
        ]

    names: list[str] = []
    if INCLUDE_FX_DEBUG_PROBES:
        names.extend(
            [
                "zombie/fx_bo3_rev_debug_orb",
                "zombie/fx_bo3_rev_debug_orb_os",
                "zombie/fx_bo3_rev_debug_orb_stock",
                "zombie/fx_bo3_rev_debug_orb_stock_os",
                "zombie/fx_bo3_rev_probe_phosphorous_i1024_os",
                "zombie/fx_bo3_rev_probe_shockwave_i2048_os",
                "zombie/fx_bo3_rev_contract_test",
                "zombie/fx_bo3_rev_hole_md_stock_probe",
                "zombie/fx_bo3_rev_hole_md_custom_probe",
            ]
        )
    if raw_fx_stage_enabled("muzzle"):
        names.append("zombie/fx_idgun_muz_1p_zmb")
    if raw_fx_stage_enabled("projectile"):
        names.append("zombie/fx_idgun_projectile_zod_zmb")
    if raw_fx_stage_enabled("impact"):
        names.append("zombie/fx_idgun_vortex_explo_zod_zmb")
    if raw_fx_stage_enabled("full"):
        names.append("zombie/fx_idgun_vortex_zod_zmb")
    return names


def bo3_servant_raw_fx_staged_names() -> list[str]:
    if not USE_BO3_RAW_FX:
        return []

    if SERVANT_FX_SCOPE == "vortex_core":
        names: list[str] = []
        if INCLUDE_FX_DEBUG_PROBES:
            names.extend(
                [
                    "zombie/fx_bo3_rev_debug_orb",
                    "zombie/fx_bo3_rev_debug_orb_os",
                    "zombie/fx_bo3_rev_debug_orb_stock",
                    "zombie/fx_bo3_rev_debug_orb_stock_os",
                    "zombie/fx_bo3_rev_probe_phosphorous_i1024_os",
                    "zombie/fx_bo3_rev_probe_shockwave_i2048_os",
                    "zombie/fx_bo3_rev_contract_test",
                    "zombie/fx_bo3_rev_hole_md_stock_probe",
                    "zombie/fx_bo3_rev_hole_md_custom_probe",
                ]
            )
        names.extend(
            [
                "zombie/fx_idgun_ground_displace_zod_zmb",
                "zombie/fx_idgun_vortex_explo_zod_zmb",
                "zombie/fx_idgun_vortex_zod_zmb",
                "zombie/fx_idgun_hole_lg_zod_zmb",
                "zombie/fx_idgun_hole_sm_zod_zmb",
                "zombie/fx_idgun_hole_xsm_zod_zmb",
                "zombie/fx_idgun_hole_xl_zod_zmb",
            ]
        )
        return names

    names: list[str] = []
    if INCLUDE_FX_DEBUG_PROBES:
        names.extend(
            [
                "zombie/fx_bo3_rev_debug_orb",
                "zombie/fx_bo3_rev_debug_orb_os",
                "zombie/fx_bo3_rev_debug_orb_stock",
                "zombie/fx_bo3_rev_debug_orb_stock_os",
                "zombie/fx_bo3_rev_probe_phosphorous_i1024_os",
                "zombie/fx_bo3_rev_probe_shockwave_i2048_os",
                "zombie/fx_bo3_rev_contract_test",
                "zombie/fx_bo3_rev_hole_md_stock_probe",
                "zombie/fx_bo3_rev_hole_md_custom_probe",
            ]
        )
    if raw_fx_stage_enabled("muzzle"):
        names.append("zombie/fx_idgun_muz_1p_zmb")
    if raw_fx_stage_enabled("projectile"):
        names.append("zombie/fx_idgun_projectile_zod_zmb")
    if raw_fx_stage_enabled("impact"):
        names.extend(
            [
                "zombie/fx_idgun_ground_displace_zod_zmb",
                "zombie/fx_idgun_vortex_explo_zod_zmb",
            ]
        )
    if raw_fx_stage_enabled("full"):
        names.extend(
            [
                "zombie/fx_idgun_vortex_zod_zmb",
                "zombie/fx_idgun_hole_lg_zod_zmb",
                "zombie/fx_idgun_hole_md_zod_zmb",
                "zombie/fx_idgun_hole_sm_zod_zmb",
                "zombie/fx_idgun_hole_xsm_zod_zmb",
                "zombie/fx_idgun_hole_xl_zod_zmb",
            ]
        )
    return names


def write_debug_raw_fx() -> None:
    zombie_root = FX_DIR / "zombie"
    zombie_root.mkdir(parents=True, exist_ok=True)
    debug_template = """iwfx 2

{
\tname "{name}";
\teditorFlags looping;
\tflags spawnRelative spawnFrustumCull runRelToEffect;
\textraFlags;
\tspawnRange 0.000000 600.000000;
\tfadeInRange 100.000000 500.000000;
\tfadeOutRange 0.000000 80.000000;
\tspawnFrustumCullRadius 30.000000;
\tspawnLooping 1 0;
\tspawnLoopingSpawnCount 2147483647 0;
\tspawnOneShot 0 0;
\tspawnDelayMsec 0 0;
\tlifeSpanMsec 1 0;
\tspawnOrgX -10.000000 0.000000;
\tspawnOrgY 0.000000 0.000000;
\tspawnOrgZ 0.000000 0.000000;
\tspawnOffsetRadius 0.000000 0.000000;
\tspawnOffsetHeight 0.000000 0.000000;
\tspawnOffsetCylindricalAxis 0.000000;
\tspawnAnglePitch 0.000000 0.000000;
\tspawnAngleYaw 0.000000 0.000000;
\tspawnAngleRoll 0.000000 0.000000;
\tangleVelPitch 0.000000 0.000000;
\tangleVelYaw 0.000000 0.000000;
\tangleVelRoll 0.000000 0.000000;
\tinitialRot 0.000000 0.000000;
\trotationAxis 0.000000 0.000000 0.000000 1.000000;
\tgravity 0.000000 0.000000;
\telasticity 1.000000 0.000000;
\twindinfluence 0.000000;
\tatlasBehavior startFixed;
\tatlasIndex 0;
\tatlasFps 1;
\tatlasLoopCount 1;
\tatlasColIndexBits 0;
\tatlasRowIndexBits 0;
\tatlasEntryCount 1;
\tatlasIndexRange 0;
\tvelGraph0X 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tvelGraph0Y 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tvelGraph0Z 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tvelGraph1X 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tvelGraph1Y 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tvelGraph1Z 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\trotGraph 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tsizeGraph0 220.000000
\t{
\t\t{
\t\t\t0.000000 1.000000
\t\t\t1.000000 1.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tsizeGraph1 220.000000
\t{
\t\t{
\t\t\t0.000000 1.000000
\t\t\t1.000000 1.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tscaleGraph 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tchildSizeScaleGraph 1.000000
\t{
\t\t{
\t\t\t0.000000 1.000000
\t\t\t1.000000 1.000000
\t\t}
\t\t{
\t\t\t0.000000 1.000000
\t\t\t1.000000 1.000000
\t\t}
\t};
\tcolorGraph 1
\t{
\t\t{
\t\t\t0.000000 1.000000 1.000000 1.000000
\t\t\t1.000000 1.000000 1.000000 1.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000 0.000000 0.000000
\t\t\t1.000000 0.000000 0.000000 0.000000
\t\t}
\t};
\talphaGraph 1
\t{
\t\t{
\t\t\t0.000000 1.000000
\t\t\t1.000000 0.850000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tlightIntensityGraph 1.000000
\t{
\t\t{
\t\t\t0.000000 1.000000
\t\t\t1.000000 1.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tlightRadiusGraph 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tlightFovGraph 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tinheritParentMovementGraph 1.000000
\t{
\t\t{
\t\t\t0.000000 1.000000
\t\t\t1.000000 1.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tattractorGraph 1.000000
\t{
\t\t{
\t\t\t0.000000 1.000000
\t\t\t1.000000 1.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tattractorLocalPosition 0.000000 0.000000 0.000000;
\tlightingFrac 0.000000;
\tcollOffset 0.000000 0.000000 0.000000;
\tcollRadius 0.000000;
\tfxOnImpact "";
\tfxOnDeath "";
\tdisplacement 0;
\temission "";
\temitDist 1.000000 0.000000;
\temitDistVariance 0.000000 0.000000;
\temitDensity 1.000000 0.000000;
\temitSizeForDensity 1.000000;
\tattachment "";
\tattachmentDensity 1.000000 0.000000;
\tattachmentSizeForDensity 1.000000;
\ttrailSplitDist 0;
\ttrailScrollTime 0.000000;
\ttrailRepeatDist 0;
\ttrailFadeInDist 0.000000;
\ttrailFadeOutDist 0.000000;
\talphafadetimemsec 0;
\tmaxwind_mag 0;
\tmaxwind_life 0;
\tmaxwind_interval 1;
\tbillboardTopWidth 1.000000;
\tbillboardBottomWidth 1.000000;
\telemSpawnSound
\t{
\t};
\telemFollowSound
\t{
\t};
\tcloudDensity 1024 0;
\tspotLightFovInnerFraction 0;
\tspotLightStartRadius 0;
\tspotLightEndRadius 0;
\talphaDissolve 1.000000;
\tzFeather 0.000000;
\tfalloffBeginAngle 65;
\tfalloffEndAngle 85;
\tlfSourceDir 0 0 0;
\tlfSourceSize 0;
\tbillboardPivot 0.000000 -0.000000;
\tlevelOfDetail 0;
\tbillboardSprite
\t{
\t\t"{material_name}"
\t};
}
"""
    (zombie_root / "fx_bo3_rev_debug_orb.efx").write_text(
        debug_template.replace("{name}", "bo3_rev_debug_orb")
        .replace("{material_name}", "gfx_light_phosphorous_em"),
        encoding="utf-8",
    )
    normalize_staged_raw_fx(zombie_root / "fx_bo3_rev_debug_orb.efx")
    stock_minimal_template = """iwfx 2

{
\tname "{name}";
\teditorFlags looping;
\tflags spawnRelative spawnFrustumCull runRelToEffect;
\textraFlags;
\tspawnRange 0.000000 600.000000;
\tfadeInRange 100.000000 500.000000;
\tfadeOutRange 0.000000 80.000000;
\tspawnFrustumCullRadius 30.000000;
\tspawnLooping 1 0;
\tspawnLoopingSpawnCount 2147483647 0;
\tspawnOneShot 0 0;
\tspawnDelayMsec 0 0;
\tlifeSpanMsec 1 0;
\tspawnOrgX -10.000000 0.000000;
\tspawnOrgY 0.000000 0.000000;
\tspawnOrgZ 0.000000 0.000000;
\tspawnOffsetRadius 0.000000 0.000000;
\tspawnOffsetHeight 0.000000 0.000000;
\tspawnOffsetCylindricalAxis 0.000000;
\tspawnAnglePitch 0.000000 0.000000;
\tspawnAngleYaw 0.000000 0.000000;
\tspawnAngleRoll 0.000000 0.000000;
\tangleVelPitch 0.000000 0.000000;
\tangleVelYaw 0.000000 0.000000;
\tangleVelRoll 0.000000 0.000000;
\tinitialRot 0.000000 0.000000;
\trotationAxis 0.000000 0.000000 0.000000 1.000000;
\tgravity 0.000000 0.000000;
\telasticity 1.000000 0.000000;
\twindinfluence 0.000000;
\tatlasBehavior startFixed;
\tatlasIndex 0;
\tatlasFps 1;
\tatlasLoopCount 1;
\tatlasColIndexBits 0;
\tatlasRowIndexBits 0;
\tatlasEntryCount 1;
\tatlasIndexRange 0;
\tvelGraph0X 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tvelGraph0Y 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tvelGraph0Z 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tvelGraph1X 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tvelGraph1Y 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tvelGraph1Z 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\trotGraph 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tsizeGraph0 32.500000
\t{
\t\t{
\t\t\t0.000000 1.000000
\t\t\t1.000000 1.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tsizeGraph1 32.500000
\t{
\t\t{
\t\t\t0.000000 1.000000
\t\t\t1.000000 1.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tscaleGraph 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tchildSizeScaleGraph 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tcolorGraph 1
\t{
\t\t{
\t\t\t0.000000 1.000000 1.000000 1.000000
\t\t\t1.000000 1.000000 1.000000 1.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000 0.000000 0.000000
\t\t\t1.000000 0.000000 0.000000 0.000000
\t\t}
\t};
\talphaGraph 1
\t{
\t\t{
\t\t\t0.000000 1.000000
\t\t\t1.000000 1.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tlightIntensityGraph 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tlightRadiusGraph 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tlightFovGraph 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tinheritParentMovementGraph 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tattractorGraph 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tattractorLocalPosition 0.000000 0.000000 0.000000;
\tlightingFrac 0.000000;
\tcollOffset 0.000000 0.000000 0.000000;
\tcollRadius 0.000000;
\tfxOnImpact "";
\tfxOnDeath "";
\tdisplacement 0;
\temission "";
\temitDist 1.000000 0.000000;
\temitDistVariance 0.000000 0.000000;
\temitDensity 1.000000 0.000000;
\temitSizeForDensity 1.000000;
\tattachment "";
\tattachmentDensity 1.000000 0.000000;
\tattachmentSizeForDensity 1.000000;
\ttrailSplitDist 0;
\ttrailScrollTime 0.000000;
\ttrailRepeatDist 0;
\ttrailFadeInDist 0.000000;
\ttrailFadeOutDist 0.000000;
\talphafadetimemsec 0;
\tmaxwind_mag 0;
\tmaxwind_life 0;
\tmaxwind_interval 0;
\tbillboardTopWidth 1.000000;
\tbillboardBottomWidth 1.000000;
\telemSpawnSound
\t{
\t};
\telemFollowSound
\t{
\t};
\tcloudDensity 1024 0;
\tspotLightFovInnerFraction 0;
\tspotLightStartRadius 0;
\tspotLightEndRadius 0;
\talphaDissolve 1.000000;
\tzFeather 0.000000;
\tfalloffBeginAngle 65;
\tfalloffEndAngle 85;
\tlfSourceDir 0 0 0;
\tlfSourceSize 0;
\tbillboardPivot 0.000000 -0.000000;
\tlevelOfDetail 0;
\tbillboardSprite
\t{
\t\t"bo3_rev_debug_stock_glow"
\t};
}
"""
    (zombie_root / "fx_bo3_rev_debug_orb_stock.efx").write_text(
        stock_minimal_template.replace("{name}", "bo3_rev_debug_orb_stock"),
        encoding="utf-8",
    )
    normalize_staged_raw_fx(zombie_root / "fx_bo3_rev_debug_orb_stock.efx")
    (zombie_root / "fx_ffprobe_debug_orb_stock.efx").write_text(
        stock_minimal_template.replace("{name}", "fx_ffprobe_debug_orb_stock"),
        encoding="utf-8",
    )
    normalize_staged_raw_fx(zombie_root / "fx_ffprobe_debug_orb_stock.efx")
    (zombie_root / "fx_ffprobe_debug_orb_phosphorous.efx").write_text(
        stock_minimal_template
        .replace("{name}", "fx_ffprobe_debug_orb_phosphorous")
        .replace('"bo3_rev_debug_stock_glow"', '"gfx_light_phosphorous_em"', 1),
        encoding="utf-8",
    )
    normalize_staged_raw_fx(zombie_root / "fx_ffprobe_debug_orb_phosphorous.efx")
    (zombie_root / "fx_ffprobe_debug_orb_stock_fmt0d.efx").write_text(
        stock_minimal_template
        .replace("{name}", "fx_ffprobe_debug_orb_stock_fmt0d")
        .replace('"bo3_rev_debug_stock_glow"', f'"{STOCK_FMT0D_DEBUG_MATERIAL_NAME}"', 1),
        encoding="utf-8",
    )
    normalize_staged_raw_fx(zombie_root / "fx_ffprobe_debug_orb_stock_fmt0d.efx")
    (zombie_root / "fx_ffprobe_debug_orb_stock_fulldds.efx").write_text(
        stock_minimal_template
        .replace("{name}", "fx_ffprobe_debug_orb_stock_fulldds")
        .replace('"bo3_rev_debug_stock_glow"', f'"{STOCK_FULLDDS_DEBUG_MATERIAL_NAME}"', 1),
        encoding="utf-8",
    )
    normalize_staged_raw_fx(zombie_root / "fx_ffprobe_debug_orb_stock_fulldds.efx")
    for spec in PHOSPHOROUS_VARIANTS.values():
        fx_name = spec["asset"].split("/", 1)[1]
        (zombie_root / f"{fx_name}.efx").write_text(
            stock_minimal_template
            .replace("{name}", fx_name)
            .replace('"bo3_rev_debug_stock_glow"', f'"{spec["material"]}"', 1),
            encoding="utf-8",
        )
        normalize_staged_raw_fx(zombie_root / f"{fx_name}.efx")
    debug_template_os = """iwfx 2

{
\tname "{name}";
\teditorFlags;
\tflags spawnRelative spawnFrustumCull runRelToEffect;
\textraFlags;
\tspawnRange 0.000000 0.000000;
\tfadeInRange 0.000000 0.000000;
\tfadeOutRange 0.000000 0.000000;
\tspawnFrustumCullRadius 256.000000;
\tspawnLooping 0 0;
\tspawnLoopingSpawnCount 0 0;
\tspawnOneShot 1 0;
\tspawnDelayMsec 0 0;
\tlifeSpanMsec 1200 0;
\tspawnOrgX 0.000000 0.000000;
\tspawnOrgY 0.000000 0.000000;
\tspawnOrgZ 0.000000 0.000000;
\tspawnOffsetRadius 0.000000 0.000000;
\tspawnOffsetHeight 0.000000 0.000000;
\tspawnOffsetCylindricalAxis 0.000000;
\tspawnAnglePitch 0.000000 0.000000;
\tspawnAngleYaw 0.000000 0.000000;
\tspawnAngleRoll 0.000000 0.000000;
\tangleVelPitch 0.000000 0.000000;
\tangleVelYaw 0.000000 0.000000;
\tangleVelRoll 0.000000 0.000000;
\tinitialRot 0.000000 0.000000;
\trotationAxis 0.000000 0.000000 0.000000 1.000000;
\tgravity 0.000000 0.000000;
\telasticity 0.000000 0.000000;
\twindinfluence 0.000000;
\tatlasBehavior startFixed playOverLife;
\tatlasIndex 0;
\tatlasFps 0;
\tatlasLoopCount 1;
\tatlasColIndexBits 0;
\tatlasRowIndexBits 0;
\tatlasEntryCount 1;
\tatlasIndexRange 0;
\tvelGraph0X 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tvelGraph0Y 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tvelGraph0Z 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tvelGraph1X 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tvelGraph1Y 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tvelGraph1Z 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\trotGraph 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tsizeGraph0 260.000000
\t{
\t\t{
\t\t\t0.000000 1.000000
\t\t\t1.000000 1.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tsizeGraph1 260.000000
\t{
\t\t{
\t\t\t0.000000 1.000000
\t\t\t1.000000 1.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tscaleGraph 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tchildSizeScaleGraph 1.000000
\t{
\t\t{
\t\t\t0.000000 1.000000
\t\t\t1.000000 1.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tcolorGraph 1
\t{
\t\t{
\t\t\t0.000000 1.000000 1.000000 1.000000
\t\t\t1.000000 1.000000 1.000000 1.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000 0.000000 0.000000
\t\t\t1.000000 0.000000 0.000000 0.000000
\t\t}
\t};
\talphaGraph 1
\t{
\t\t{
\t\t\t0.000000 1.000000
\t\t\t1.000000 0.850000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tlightIntensityGraph 1.000000
\t{
\t\t{
\t\t\t0.000000 1.000000
\t\t\t1.000000 1.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tlightRadiusGraph 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tlightFovGraph 0.000000
\t{
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tinheritParentMovementGraph 1.000000
\t{
\t\t{
\t\t\t0.000000 1.000000
\t\t\t1.000000 1.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tattractorGraph 1.000000
\t{
\t\t{
\t\t\t0.000000 1.000000
\t\t\t1.000000 1.000000
\t\t}
\t\t{
\t\t\t0.000000 0.000000
\t\t\t1.000000 0.000000
\t\t}
\t};
\tattractorLocalPosition 0.000000 0.000000 0.000000;
\tlightingFrac 0.000000;
\tcollOffset 0.000000 0.000000 0.000000;
\tcollRadius 0.000000;
\tfxOnImpact "";
\tfxOnDeath "";
\tdisplacement 0;
\temission "";
\temitDist 0.000000 0.000000;
\temitDistVariance 0.000000 0.000000;
\temitDensity 1.000000 0.000000;
\temitSizeForDensity 1.000000;
\tattachment "";
\tattachmentDensity 1.000000 0.000000;
\tattachmentSizeForDensity 1.000000;
\ttrailSplitDist 0;
\ttrailScrollTime 0.000000;
\ttrailRepeatDist 0;
\ttrailFadeInDist 0.000000;
\ttrailFadeOutDist 0.000000;
\talphafadetimemsec 0;
\tmaxwind_mag 0;
\tmaxwind_life 0;
\tmaxwind_interval 1;
\tbillboardTopWidth 0.000000;
\tbillboardBottomWidth 0.000000;
\telemSpawnSound
\t{
\t};
\telemFollowSound
\t{
\t};
\tcloudDensity 1024 0;
\tspotLightFovInnerFraction 0;
\tspotLightStartRadius 0;
\tspotLightEndRadius 0;
\talphaDissolve 1.000000;
\tzFeather 0.000000;
\tfalloffBeginAngle 65;
\tfalloffEndAngle 85;
\tlfSourceDir 0 0 0;
\tlfSourceSize 0;
\tbillboardPivot 0.000000 -0.000000;
\tlevelOfDetail 0;
\tbillboardSprite
\t{
\t\t"{material_name}"
\t};
}
"""
    (zombie_root / "fx_bo3_rev_debug_orb_os.efx").write_text(
        debug_template_os.replace("{name}", "bo3_rev_debug_orb_os")
        .replace("{material_name}", "gfx_light_phosphorous_em"),
        encoding="utf-8",
    )
    normalize_staged_raw_fx(zombie_root / "fx_bo3_rev_debug_orb_os.efx")
    (zombie_root / "fx_bo3_rev_debug_orb_stock_os.efx").write_text(
        stock_minimal_template.replace('name "{name}";', 'name "bo3_rev_debug_orb_stock_os";', 1)
        .replace("\teditorFlags looping;\n", "\teditorFlags;\n", 1)
        .replace("\tspawnLooping 1 0;\n", "\tspawnLooping 0 0;\n", 1)
        .replace("\tspawnLoopingSpawnCount 1 0;\n", "\tspawnLoopingSpawnCount 0 0;\n", 1)
        .replace("\tspawnOneShot 0 0;\n", "\tspawnOneShot 1 0;\n", 1),
        encoding="utf-8",
    )
    normalize_staged_raw_fx(zombie_root / "fx_bo3_rev_debug_orb_stock_os.efx")
    (zombie_root / "fx_bo3_rev_probe_phosphorous_i1024_os.efx").write_text(
        debug_template_os.replace('{name}', 'bo3_rev_probe_phosphorous_i1024_os')
        .replace('{material_name}', 'gfx_light_phosphorous_em_i1024'),
        encoding="utf-8",
    )
    normalize_staged_raw_fx(zombie_root / "fx_bo3_rev_probe_phosphorous_i1024_os.efx")
    (zombie_root / "fx_bo3_rev_probe_shockwave_i2048_os.efx").write_text(
        debug_template_os.replace('{name}', 'bo3_rev_probe_shockwave_i2048_os')
        .replace('{material_name}', 'gfx_shockwave_elec_anim_em_i2048'),
        encoding="utf-8",
    )
    normalize_staged_raw_fx(zombie_root / "fx_bo3_rev_probe_shockwave_i2048_os.efx")
    (zombie_root / "fx_bo3_rev_contract_test.efx").write_text(
        stock_minimal_template
        .replace('{name}', 'bo3_rev_contract_test')
        .replace('"gfx_spark_blink_anim_em"', '"gfx_fxt_light_glow_square_gr"', 1),
        encoding="utf-8",
    )
    normalize_staged_raw_fx(zombie_root / "fx_bo3_rev_contract_test.efx")


def normalize_placeholder_scale_graphs(raw_text: str) -> str:
    # A zero-valued scaleGraph is valid in native T6 effects and is used by stock
    # sprite_billboard controls such as fx_zmb_tranzit_marker_glow. Earlier builds
    # "normalized" scaleGraph 0 -> 1.0 under the assumption that it was a placeholder,
    # but that mutates legitimate stock-like FX contracts into non-stock semantics.
    return raw_text


def normalize_staged_raw_fx(path: Path) -> None:
    if not path.exists():
        return
    raw_text = path.read_text(encoding="utf-8", errors="replace")
    normalized = normalize_placeholder_scale_graphs(raw_text)
    if normalized != raw_text:
        path.write_text(normalized, encoding="utf-8")


RAW_FX_SAFE_EDITOR_FLAGS = {
    "looping",
}

RAW_FX_SAFE_NATIVE_FLAGS = {
    "spawnRelative",
    "spawnFrustumCull",
    "spawnOffsetSphere",
    "spawnOffsetCylinder",
    "spawnOffsetNone",
    "runRelToSpawn",
    "runRelToEffect",
    "runRelToWorld",
    "useCollision",
    "dieOnTouch",
    "drawPastFog",
    "drawWithViewmodel",
    "drawWithViewModel",
    "blockSight",
    "drawInThermalViewOnly",
    "trailOrientByVelocity",
    "emitOrientByElem",
    "useBillboardPivot",
    "playAttached",
    "nonUniformScale",
}

RAW_FX_TIMING_RULES: dict[str, dict[str, float]] = {
    "billboard_additive_glow": {"fade_in_ratio": 0.25, "fade_out_ratio": 0.6, "spawn_ratio": 1.0},
    "billboard_soft_smoke": {"fade_in_ratio": 0.5, "fade_out_ratio": 0.75, "spawn_ratio": 1.5},
    "billboard_simple_alpha": {"fade_in_ratio": 0.25, "fade_out_ratio": 0.5, "spawn_ratio": 1.0},
    "billboard_distortion": {"fade_in_ratio": 0.25, "fade_out_ratio": 0.5, "spawn_ratio": 1.0},
    "burst_emissive": {"fade_in_ratio": 0.2, "fade_out_ratio": 0.4, "spawn_ratio": 0.75},
    "decal_surface_hit": {"fade_in_ratio": 0.15, "fade_out_ratio": 0.5, "spawn_ratio": 0.5},
    "lit_debris_impact": {"fade_in_ratio": 0.25, "fade_out_ratio": 0.5, "spawn_ratio": 1.0},
}

RAW_FX_STOCK_MATERIAL_PROBE_MAP: dict[str, dict[str, str]] = {
    "fx_idgun_projectile_zod_zmb": {
        "gfx_light_phosphorous_em_i1024": "gfx_fxt_light_glow_square_gr",
        "gfx_light_phosphorous_em": "gfx_fxt_light_glow_square_gr",
    },
    "fx_idgun_vortex_explo_zod_zmb": {
        "gfx_light_phosphorous_em_i1024": "gfx_fxt_light_glow_square_gr",
        "gfx_light_phosphorous_em": "gfx_fxt_light_glow_square_gr",
    },
    "fx_idgun_hole_xsm_zod_zmb": {
        "gfx_dust_gen_lit": "gfx_fxt_light_glow_square_gr",
        "gfx_dust_gen_em": "gfx_fxt_light_glow_square_gr",
        "gfx_debris_clump_em": "gfx_fxt_light_glow_square_gr",
    },
    "fx_idgun_hole_sm_zod_zmb": {
        "gfx_dust_gen_lit": "gfx_fxt_light_glow_square_gr",
        "gfx_dust_gen_em": "gfx_fxt_light_glow_square_gr",
        "gfx_debris_clump_em": "gfx_fxt_light_glow_square_gr",
    },
    "fx_idgun_hole_md_zod_zmb": {
        "gfx_dust_gen_lit": "gfx_fxt_light_glow_square_gr",
        "gfx_dust_gen_em": "gfx_fxt_light_glow_square_gr",
        "gfx_debris_clump_em": "gfx_fxt_light_glow_square_gr",
    },
    "fx_idgun_hole_lg_zod_zmb": {
        "gfx_dust_gen_lit": "gfx_fxt_light_glow_square_gr",
        "gfx_dust_gen_em": "gfx_fxt_light_glow_square_gr",
        "gfx_debris_clump_em": "gfx_fxt_light_glow_square_gr",
    },
    "fx_idgun_hole_xl_zod_zmb": {
        "gfx_dust_gen_lit": "gfx_fxt_light_glow_square_gr",
        "gfx_dust_gen_em": "gfx_fxt_light_glow_square_gr",
        "gfx_debris_clump_em": "gfx_fxt_light_glow_square_gr",
    },
}

FX_TRANSPLANT_SUPPORTED_STAGES = {
    "",
    "stock_triplet",
    "bo3_graphs",
    "bo3_timing",
    "bo3_atlas",
    "bo3_materials",
}


def _split_raw_fx_top_level_blocks(text: str) -> tuple[str, list[str]]:
    blocks: list[str] = []
    start = None
    brace_depth = 0
    header_end = None
    idx = 0
    while idx < len(text):
        ch = text[idx]
        if ch == "{":
            if brace_depth == 0:
                start = idx
                if header_end is None:
                    header_end = idx
            brace_depth += 1
        elif ch == "}":
            if brace_depth > 0:
                brace_depth -= 1
                if brace_depth == 0 and start is not None:
                    end = idx + 1
                    while end < len(text) and text[end] in " \t":
                        end += 1
                    if end < len(text) and text[end] == ";":
                        end += 1
                    while end < len(text) and text[end] in "\r\n":
                        end += 1
                    blocks.append(text[start:end])
                    start = None
        idx += 1

    header = text[: header_end if header_end is not None else len(text)]
    return header, blocks


def _raw_fx_find_visual_block(block: str) -> tuple[str, list[str]]:
    match = re.search(
        r"(billboardSprite|orientedSprite|rotatedSprite|line|tail|trail|cloud|decal)\s*\{(.*?)\};",
        block,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return "", []
    elem_type = match.group(1).strip().lower()
    materials = [value.strip() for value in re.findall(r'"([^"]+)"', match.group(2)) if value.strip()]
    return elem_type, materials


def _raw_fx_effect_name(block: str) -> str:
    match = re.search(r'name\s+"([^"]+)"\s*;', block)
    return match.group(1).strip() if match else "<unnamed>"


def _raw_fx_replace_material_refs(block: str, replacements: dict[str, str], rewrite_log: list[str]) -> str:
    updated = block
    for src_name, dst_name in replacements.items():
        if f'"{src_name}"' not in updated:
            continue
        updated = updated.replace(f'"{src_name}"', f'"{dst_name}"')
        rewrite_log.append(f"material:{src_name}->{dst_name}")
    return updated


def _raw_fx_replace_statement_block(block: str, key: str, new_statement: str) -> str:
    pattern = re.compile(rf"(?ms)^\s*{re.escape(key)}\s+.*?^\s*\}};\s*$")
    return pattern.sub(new_statement.rstrip(), block, count=1)


def _raw_fx_get_visual_statement_block(block: str) -> str:
    match = re.search(
        r"(?ms)^\s*(billboardSprite|orientedSprite|rotatedSprite|line|tail|trail|cloud|decal)\s*\{.*?^\s*\};\s*$",
        block,
    )
    return match.group(0).strip() if match else ""


def _raw_fx_replace_visual_statement_block(block: str, new_statement: str) -> str:
    pattern = re.compile(
        r"(?ms)^\s*(billboardSprite|orientedSprite|rotatedSprite|line|tail|trail|cloud|decal)\s*\{.*?^\s*\};\s*$"
    )
    return pattern.sub(new_statement.rstrip(), block, count=1)


def _raw_fx_insert_line_statement(block: str, statement: str) -> str:
    insert_at = len(block)
    depth = 0
    started = False
    for idx, char in enumerate(block):
        if char == "{":
            depth += 1
            started = True
        elif char == "}":
            if started:
                depth -= 1
                if depth == 0:
                    insert_at = idx
                    break
    statement = statement.rstrip()
    if not statement.startswith("\t"):
        statement = "\t" + statement.lstrip()
    return block[:insert_at] + statement + "\n" + block[insert_at:]


def _raw_fx_constant_scalar_graph_statement(key: str, base: float, value: float, *, stock_points: bool = False) -> str:
    if stock_points:
        return (
            f"\t{key} {base:.6f}\n"
            "\t{\n"
            "\t\t{\n"
            f"\t\t\t0.000000 {value:.6f}\n"
            f"\t\t\t1.000000 {value:.6f}\n"
            "\t\t}\n"
            "\t\t{\n"
            "\t\t\t0.000000 0.000000\n"
            "\t\t\t1.000000 0.000000\n"
            "\t\t}\n"
            "\t};"
        )
    return (
        f"\t{key} {base:.6f}\n"
        "\t{\n"
        "\t\t{\n"
        f"\t\t\t0.000000 {value:.6f}\n"
        f"\t\t\t0.500000 {value:.6f}\n"
        f"\t\t\t1.000000 {value:.6f}\n"
        "\t\t}\n"
        "\t\t{\n"
        "\t\t\t0.000000 0.000000\n"
        "\t\t\t0.500000 0.000000\n"
        "\t\t\t1.000000 0.000000\n"
        "\t\t}\n"
        "\t};"
    )


def _raw_fx_present_zero_scalar_graph_statement(key: str, base: float = 0.0, epsilon: float = 0.0002) -> str:
    return (
        f"\t{key} {base:.6f}\n"
        "\t{\n"
        "\t\t{\n"
        "\t\t\t0.000000 0.000000\n"
        "\t\t\t1.000000 0.000000\n"
        "\t\t}\n"
        "\t\t{\n"
        f"\t\t\t0.000000 {epsilon:.6f}\n"
        f"\t\t\t1.000000 {epsilon:.6f}\n"
        "\t\t}\n"
        "\t};"
    )


def _raw_fx_constant_color_graph_statement(
    key: str, rgba: tuple[float, float, float, float], *, stock_points: bool = False
) -> str:
    r, g, b, a = rgba
    if stock_points:
        return (
            f"\t{key} 1\n"
            "\t{\n"
            "\t\t{\n"
            f"\t\t\t0.000000 {r:.6f} {g:.6f} {b:.6f} {a:.6f}\n"
            f"\t\t\t1.000000 {r:.6f} {g:.6f} {b:.6f} {a:.6f}\n"
            "\t\t}\n"
            "\t\t{\n"
            "\t\t\t0.000000 0.000000 0.000000 0.000000\n"
            "\t\t\t1.000000 0.000000 0.000000 0.000000\n"
            "\t\t}\n"
            "\t};"
        )
    return (
        f"\t{key} 1\n"
        "\t{\n"
        "\t\t{\n"
        f"\t\t\t0.000000 {r:.6f} {g:.6f} {b:.6f} {a:.6f}\n"
        f"\t\t\t0.500000 {r:.6f} {g:.6f} {b:.6f} {a:.6f}\n"
        f"\t\t\t1.000000 {r:.6f} {g:.6f} {b:.6f} {a:.6f}\n"
        "\t\t}\n"
        "\t\t{\n"
        "\t\t\t0.000000 0.000000 0.000000 0.000000\n"
        "\t\t\t0.500000 0.000000 0.000000 0.000000\n"
        "\t\t\t1.000000 0.000000 0.000000 0.000000\n"
        "\t\t}\n"
        "\t};"
    )


def _raw_fx_extract_block_statement(block: str, key: str) -> str:
    statement = _raw_fx_get_statement_block(block, key)
    if statement:
        return statement
    return ""


def _raw_fx_copy_block_statement(block: str, original_block: str, key: str) -> str:
    original_statement = _raw_fx_extract_block_statement(original_block, key)
    if not original_statement:
        return block
    return _raw_fx_replace_statement_block(block, key, original_statement)


def _raw_fx_copy_line_statement(block: str, original_block: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s+.*?;\s*$", original_block)
    if not match:
        return block
    original_statement = match.group(0).strip()
    pattern = re.compile(rf"(?m)^\s*{re.escape(key)}\s+.*?;\s*$")
    return pattern.sub(original_statement, block, count=1)


def _raw_fx_hole_md_stock_triplet_profile(effect_index: int) -> dict[str, object]:
    profiles = [
        {
            "size": 32.5,
            "size_y": 32.5,
            "alpha": 137.0 / 255.0,
            "color": (1.0, 1.0, 91.0 / 255.0, 1.0),
            "delay": 0,
            "sort": 5,
            "cull": 30.0,
            "spawn_origin": (-10.0, 0.0, 0.0),
            "spawn_range": (0.0, 600.0),
            "fade_in": (100.0, 500.0),
            "fade_out": (0.0, 80.0),
            "life": (1, 0),
            "atlas_fps": 1,
            "atlas_entry_count": 1,
            "atlas_index_range": 2,
            "material": "gfx_fxt_light_glow_square_gr",
            "elasticity": 1.0,
            "emit_dist": 1.0,
            "scale": 0.0,
        },
        {
            "size": 32.5,
            "size_y": 32.5,
            "alpha": 89.0 / 255.0,
            "color": (1.0, 1.0, 128.0 / 255.0, 1.0),
            "delay": 0,
            "sort": 5,
            "cull": 35.0,
            "spawn_origin": (-25.0, 0.0, 0.0),
            "spawn_range": (0.0, 600.0),
            "fade_in": (100.0, 500.0),
            "fade_out": (0.0, 80.0),
            "life": (1, 0),
            "atlas_fps": 1,
            "atlas_entry_count": 1,
            "atlas_index_range": 2,
            "material": "gfx_fxt_light_glow_square_gr",
            "elasticity": 1.0,
            "emit_dist": 1.0,
            "scale": 0.0,
        },
        {
            "size": 0.25,
            "size_y": 0.4,
            "alpha": 1.0,
            "color": (4.0 / 255.0, 4.0 / 255.0, 4.0 / 255.0, 1.0),
            "delay": 0,
            "sort": 10,
            "cull": 20.0,
            "spawn_origin": (-50.0, 0.0, -10.0),
            "spawn_origin_amp": (0.0, 0.0, 20.0),
            "spawn_range": (0.0, 300.0),
            "fade_in": (240.0, 160.0),
            "fade_out": (0.0, 0.0),
            "life": (1000, 1000),
            "spawn_looping": 500,
            "spawn_delay": (0, 680),
            "atlas_fps": 0,
            "atlas_col_bits": 1,
            "atlas_row_bits": 1,
            "atlas_entry_count": 4,
            "atlas_index_range": 2,
            "material": "gfx_fxt_env_dust_mote_add",
            "elasticity": 1.0,
            "emit_dist": 1.0,
            "scale": 0.0,
        },
    ]
    return profiles[min(max(effect_index, 0), len(profiles) - 1)]


def _raw_fx_apply_hole_md_transplant_stage(
    block: str,
    original_block: str,
    stage: str,
    rewrite_log: list[str],
) -> str:
    effect_name = _raw_fx_effect_name(block)
    match = re.search(r"(\d+)$", effect_name)
    effect_index = int(match.group(1)) if match else 0
    profile = _raw_fx_hole_md_stock_triplet_profile(effect_index)

    block = _raw_fx_replace_material_refs(
        block,
        {
            "gfx_dust_gen_lit": str(profile["material"]),
            "gfx_dust_gen_em": str(profile["material"]),
            "gfx_debris_clump_em": str(profile["material"]),
            "gfx_fxt_light_glow_square_gr": str(profile["material"]),
        },
        rewrite_log,
    )
    visual_statement = (
        '\tbillboardSprite\n'
        '\t{\n'
        f'\t\t"{profile["material"]}"\n'
        '\t};'
    )
    block = _raw_fx_replace_visual_statement_block(block, visual_statement)
    block = _raw_fx_upsert_tokens(block, "editorFlags", [])
    block = _raw_fx_upsert_tokens(block, "flags", ["spawnRelative", "spawnFrustumCull", "runRelToEffect"])
    # Force a truly anchored, persistent stock-visible baseline.
    block = _raw_fx_upsert_pair(
        block,
        "spawnRange",
        float(profile["spawn_range"][0]),
        float(profile["spawn_range"][1]),
    )
    block = _raw_fx_upsert_pair(
        block,
        "fadeInRange",
        float(profile["fade_in"][0]),
        float(profile["fade_in"][1]),
    )
    block = _raw_fx_upsert_pair(
        block,
        "fadeOutRange",
        float(profile["fade_out"][0]),
        float(profile["fade_out"][1]),
    )
    block = _raw_fx_upsert_pair(
        block,
        "spawnLooping",
        int(profile.get("spawn_looping", 1)),
        0,
        integer=True,
    )
    block = _raw_fx_upsert_pair(block, "spawnLoopingSpawnCount", 2147483647, 0, integer=True)
    block = _raw_fx_upsert_pair(block, "spawnOneShot", 0, 0, integer=True)
    spawn_delay_base, spawn_delay_amp = profile.get("spawn_delay", (int(profile["delay"]), 0))
    block = _raw_fx_upsert_pair(block, "spawnDelayMsec", int(spawn_delay_base), int(spawn_delay_amp), integer=True)
    life_base, life_amp = profile["life"]
    block = _raw_fx_upsert_pair(block, "lifeSpanMsec", int(life_base), int(life_amp), integer=True)
    block = _raw_fx_upsert_single(block, "spawnFrustumCullRadius", float(profile["cull"]))
    spawn_origin = profile["spawn_origin"]
    spawn_origin_amp = profile.get("spawn_origin_amp", (0.0, 0.0, 0.0))
    block = _raw_fx_upsert_pair(block, "spawnOrgX", float(spawn_origin[0]), float(spawn_origin_amp[0]))
    block = _raw_fx_upsert_pair(block, "spawnOrgY", float(spawn_origin[1]), float(spawn_origin_amp[1]))
    block = _raw_fx_upsert_pair(block, "spawnOrgZ", float(spawn_origin[2]), float(spawn_origin_amp[2]))
    block = _raw_fx_upsert_pair(block, "initialRot", 0.0, 0.0)
    block = _raw_fx_upsert_pair(block, "emitDist", float(profile.get("emit_dist", 0.0)), 0.0)
    block = _raw_fx_upsert_pair(block, "emitDistVariance", 0.0, 0.0)
    block = _raw_fx_upsert_pair(block, "elasticity", float(profile["elasticity"]), 0.0)
    block = _raw_fx_upsert_single(block, "billboardTopWidth", 1.0)
    block = _raw_fx_upsert_single(block, "billboardBottomWidth", 1.0)
    block = _raw_fx_upsert_single(block, "sortOrder", int(profile["sort"]), integer=True)
    block = _raw_fx_upsert_tokens(block, "atlasBehavior", ["startFixed"])
    block = _raw_fx_upsert_single(block, "atlasIndex", 0, integer=True)
    block = _raw_fx_upsert_single(block, "atlasFps", int(profile["atlas_fps"]), integer=True)
    block = _raw_fx_upsert_single(block, "atlasLoopCount", 1, integer=True)
    block = _raw_fx_upsert_single(block, "atlasColIndexBits", int(profile.get("atlas_col_bits", 0)), integer=True)
    block = _raw_fx_upsert_single(block, "atlasRowIndexBits", int(profile.get("atlas_row_bits", 0)), integer=True)
    block = _raw_fx_upsert_single(block, "atlasEntryCount", int(profile["atlas_entry_count"]), integer=True)
    block = _raw_fx_upsert_single(block, "atlasIndexRange", int(profile["atlas_index_range"]), integer=True)
    block = _raw_fx_replace_billboard_pivot(block, 0.0, 0.0)
    block = _raw_fx_replace_statement_block(
        block,
        "sizeGraph0",
        _raw_fx_constant_scalar_graph_statement("sizeGraph0", float(profile["size"]), 1.0, stock_points=True),
    )
    block = _raw_fx_replace_statement_block(
        block,
        "sizeGraph1",
        _raw_fx_constant_scalar_graph_statement(
            "sizeGraph1",
            float(profile.get("size_y", profile["size"])),
            1.0,
            stock_points=True,
        ),
    )
    block = _raw_fx_replace_statement_block(
        block,
        "scaleGraph",
        _raw_fx_present_zero_scalar_graph_statement("scaleGraph", float(profile["scale"])),
    )
    block = _raw_fx_replace_statement_block(
        block,
        "rotGraph",
        _raw_fx_constant_scalar_graph_statement("rotGraph", 0.0, 0.0, stock_points=True),
    )
    block = _raw_fx_replace_statement_block(
        block,
        "colorGraph",
        _raw_fx_constant_color_graph_statement("colorGraph", profile["color"], stock_points=True),
    )
    block = _raw_fx_replace_statement_block(
        block,
        "alphaGraph",
        _raw_fx_constant_scalar_graph_statement("alphaGraph", 1.0, float(profile["alpha"]), stock_points=True),
    )
    rewrite_log.append(f"transplant_stage:{stage}")

    if stage in {"bo3_graphs", "bo3_timing", "bo3_atlas", "bo3_materials"}:
        for key in ("sizeGraph0", "sizeGraph1", "colorGraph", "alphaGraph"):
            block = _raw_fx_copy_block_statement(block, original_block, key)
        block = _raw_fx_copy_line_statement(block, original_block, "initialRot")
        rewrite_log.append("transplant_restore:graphs")

    if stage in {"bo3_timing", "bo3_atlas", "bo3_materials"}:
        for key in (
            "spawnRange",
            "fadeInRange",
            "fadeOutRange",
            "spawnLooping",
            "spawnLoopingSpawnCount",
            "spawnOneShot",
            "spawnDelayMsec",
            "lifeSpanMsec",
            "spawnFrustumCullRadius",
            "initialRot",
        ):
            block = _raw_fx_copy_line_statement(block, original_block, key)
        rewrite_log.append("transplant_restore:timing")

    if stage in {"bo3_atlas", "bo3_materials"}:
        for key in (
            "atlasBehavior",
            "atlasIndex",
            "atlasFps",
            "atlasLoopCount",
            "atlasColIndexBits",
            "atlasRowIndexBits",
            "atlasEntryCount",
            "atlasIndexRange",
        ):
            block = _raw_fx_copy_line_statement(block, original_block, key)
        rewrite_log.append("transplant_restore:atlas")

    if stage == "bo3_materials":
        original_visual = _raw_fx_get_visual_statement_block(original_block)
        if original_visual:
            block = _raw_fx_replace_visual_statement_block(block, original_visual)
            rewrite_log.append("transplant_restore:materials")

    return block


def _raw_fx_clone_hole_md_probe(
    source_path: Path,
    dest_path: Path,
    probe_name: str,
    material_name: str,
) -> None:
    text = source_path.read_text(encoding="utf-8", errors="replace")
    header, blocks = _split_raw_fx_top_level_blocks(text)
    out_blocks: list[str] = []
    for effect_index, block in enumerate(blocks):
        size = 192.0 + (effect_index * 64.0)
        delay = effect_index * 60
        block = re.sub(
            r'(?m)^(\s*name\s+")([^"]+)(";\s*$)',
            rf'\1{probe_name}_def{effect_index}\3',
            block,
            count=1,
        )
        block = _raw_fx_replace_visual_statement_block(
            block,
            '\tbillboardSprite\n'
            '\t{\n'
            f'\t\t"{material_name}"\n'
            '\t};',
        )
        block = _raw_fx_replace_tokens(block, "editorFlags", ["looping"])
        block = _raw_fx_replace_tokens(block, "flags", ["spawnRelative", "spawnFrustumCull", "spawnOffsetNone", "runRelToEffect"])
        block = _raw_fx_replace_pair(block, "spawnRange", 0.0, 0.0)
        block = _raw_fx_replace_pair(block, "fadeInRange", 0.0, 0.0)
        block = _raw_fx_replace_pair(block, "fadeOutRange", 0.0, 0.0)
        block = _raw_fx_replace_single(block, "spawnFrustumCullRadius", 512.0)
        block = _raw_fx_replace_pair(block, "spawnLooping", 1, 0, integer=True)
        block = _raw_fx_replace_pair(block, "spawnLoopingSpawnCount", 2147483647, 0, integer=True)
        block = _raw_fx_replace_pair(block, "spawnOneShot", 0, 0, integer=True)
        block = _raw_fx_replace_pair(block, "spawnDelayMsec", delay, 0, integer=True)
        block = _raw_fx_replace_pair(block, "lifeSpanMsec", 1500, 0, integer=True)
        block = _raw_fx_replace_pair(block, "initialRot", 0.0, 0.0)
        block = _raw_fx_replace_pair(block, "emitDist", 0.0, 0.0)
        block = _raw_fx_replace_pair(block, "emitDistVariance", 0.0, 0.0)
        block = _raw_fx_replace_pair(block, "elasticity", 0.0, 0.0)
        block = _raw_fx_replace_single(block, "billboardTopWidth", 1.0)
        block = _raw_fx_replace_single(block, "billboardBottomWidth", 1.0)
        block = _raw_fx_replace_single(block, "sortOrder", 6, integer=True)
        block = _raw_fx_replace_tokens(block, "atlasBehavior", ["startFixed"])
        block = _raw_fx_replace_single(block, "atlasIndex", 0, integer=True)
        block = _raw_fx_replace_single(block, "atlasFps", 0, integer=True)
        block = _raw_fx_replace_single(block, "atlasLoopCount", 1, integer=True)
        block = _raw_fx_replace_single(block, "atlasColIndexBits", 0, integer=True)
        block = _raw_fx_replace_single(block, "atlasRowIndexBits", 0, integer=True)
        block = _raw_fx_replace_single(block, "atlasEntryCount", 1, integer=True)
        block = _raw_fx_replace_single(block, "atlasIndexRange", 0, integer=True)
        block = _raw_fx_replace_billboard_pivot(block, 0.0, 0.0)
        block = _raw_fx_replace_statement_block(
            block,
            "sizeGraph0",
            _raw_fx_constant_scalar_graph_statement("sizeGraph0", size, 1.0),
        )
        block = _raw_fx_replace_statement_block(
            block,
            "sizeGraph1",
            _raw_fx_constant_scalar_graph_statement("sizeGraph1", size, 1.0),
        )
        block = _raw_fx_replace_statement_block(
            block,
            "colorGraph",
            _raw_fx_constant_color_graph_statement("colorGraph", (1.0, 1.0, 1.0, 1.0)),
        )
        block = _raw_fx_replace_statement_block(
            block,
            "alphaGraph",
            _raw_fx_constant_scalar_graph_statement("alphaGraph", 1.0, 1.0),
        )
        out_blocks.append(block.strip() + "\n")

    dest_path.write_text(header.rstrip() + "\n\n" + "\n\n".join(out_blocks), encoding="utf-8")
    normalize_staged_raw_fx(dest_path)


def _raw_fx_apply_transplant_stage(path_stem: str, block: str, original_block: str, rewrite_log: list[str]) -> str:
    if not FX_TRANSPLANT_TARGET or not FX_TRANSPLANT_STAGE:
        return block
    if FX_TRANSPLANT_STAGE not in FX_TRANSPLANT_SUPPORTED_STAGES:
        return block
    if path_stem.lower() != FX_TRANSPLANT_TARGET:
        return block
    if FX_TRANSPLANT_TARGET == "fx_idgun_hole_md_zod_zmb":
        return _raw_fx_apply_hole_md_transplant_stage(block, original_block, FX_TRANSPLANT_STAGE, rewrite_log)
    return block


def _raw_fx_get_tokens(block: str, key: str) -> list[str]:
    match = re.search(rf"(?m)^(\s*){re.escape(key)}\s*(.*?)\s*;\s*$", block)
    if not match:
        return []
    remainder = match.group(2).strip()
    return [token for token in remainder.split() if token]


def _raw_fx_replace_tokens(block: str, key: str, tokens: list[str]) -> str:
    pattern = re.compile(rf"(?m)^(\s*){re.escape(key)}\s*.*?\s*;\s*$")

    def repl(match: re.Match[str]) -> str:
        indent = match.group(1)
        if tokens:
            return f"{indent}{key} {' '.join(tokens)};"
        return f"{indent}{key};"

    return pattern.sub(repl, block, count=1)


def _raw_fx_upsert_tokens(block: str, key: str, tokens: list[str]) -> str:
    if re.search(rf"(?m)^(\s*){re.escape(key)}\s*.*?\s*;\s*$", block):
        return _raw_fx_replace_tokens(block, key, tokens)
    if tokens:
        return _raw_fx_insert_line_statement(block, f"{key} {' '.join(tokens)};")
    return _raw_fx_insert_line_statement(block, f"{key};")


def _raw_fx_get_pair(block: str, key: str, *, integer: bool = False) -> tuple[float, float] | None:
    match = re.search(
        rf"(?m)^\s*{re.escape(key)}\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*;\s*$",
        block,
    )
    if not match:
        return None
    values = (float(match.group(1)), float(match.group(2)))
    if integer:
        return float(int(values[0])), float(int(values[1]))
    return values


def _raw_fx_replace_pair(block: str, key: str, first: float, second: float, *, integer: bool = False) -> str:
    pattern = re.compile(
        rf"(?m)^(\s*){re.escape(key)}\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*;\s*$"
    )

    def repl(match: re.Match[str]) -> str:
        indent = match.group(1)
        if integer:
            return f"{indent}{key} {int(round(first))} {int(round(second))};"
        return f"{indent}{key} {first:.6f} {second:.6f};"

    return pattern.sub(repl, block, count=1)


def _raw_fx_upsert_pair(block: str, key: str, first: float, second: float, *, integer: bool = False) -> str:
    if re.search(
        rf"(?m)^(\s*){re.escape(key)}\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*;\s*$",
        block,
    ):
        return _raw_fx_replace_pair(block, key, first, second, integer=integer)
    if integer:
        return _raw_fx_insert_line_statement(block, f"{key} {int(round(first))} {int(round(second))};")
    return _raw_fx_insert_line_statement(block, f"{key} {first:.6f} {second:.6f};")


def _raw_fx_get_single(block: str, key: str, *, integer: bool = False) -> float | None:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s+(-?\d+(?:\.\d+)?)\s*;\s*$", block)
    if not match:
        return None
    value = float(match.group(1))
    if integer:
        return float(int(value))
    return value


def _raw_fx_replace_single(block: str, key: str, value: float, *, integer: bool = False) -> str:
    pattern = re.compile(rf"(?m)^(\s*){re.escape(key)}\s+(-?\d+(?:\.\d+)?)\s*;\s*$")

    def repl(match: re.Match[str]) -> str:
        indent = match.group(1)
        if integer:
            return f"{indent}{key} {int(round(value))};"
        return f"{indent}{key} {value:.6f};"

    return pattern.sub(repl, block, count=1)


def _raw_fx_upsert_single(block: str, key: str, value: float, *, integer: bool = False) -> str:
    if re.search(rf"(?m)^(\s*){re.escape(key)}\s+(-?\d+(?:\.\d+)?)\s*;\s*$", block):
        return _raw_fx_replace_single(block, key, value, integer=integer)
    if integer:
        return _raw_fx_insert_line_statement(block, f"{key} {int(round(value))};")
    return _raw_fx_insert_line_statement(block, f"{key} {value:.6f};")


def _raw_fx_normalize_billboard_widths(block: str, elem_type: str, rewrite_log: list[str]) -> str:
    if elem_type not in {"billboardsprite", "orientedsprite", "rotatedsprite"}:
        return block

    top_width = _raw_fx_get_single(block, "billboardTopWidth")
    bottom_width = _raw_fx_get_single(block, "billboardBottomWidth")
    if top_width is None or bottom_width is None:
        return block

    if abs(top_width) > 0.0001 or abs(bottom_width) > 0.0001:
        return block

    block = _raw_fx_replace_single(block, "billboardTopWidth", 1.0)
    block = _raw_fx_replace_single(block, "billboardBottomWidth", 1.0)
    rewrite_log.append("billboardWidth:0->1")
    return block


def _raw_fx_get_statement_block(block: str, key: str) -> str:
    match = re.search(
        rf"(?ms)^\s*{re.escape(key)}\s+.*?^\s*\}};\s*$",
        block,
    )
    return match.group(0).strip() if match else ""


def _raw_fx_replace_billboard_pivot(block: str, x: float, y: float) -> str:
    pattern = re.compile(
        r"(?m)^(\s*)billboardPivot\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*;\s*$"
    )

    def repl(match: re.Match[str]) -> str:
        indent = match.group(1)
        return f"{indent}billboardPivot {x:.6f} {y:.6f};"

    return pattern.sub(repl, block, count=1)


def _raw_fx_family_for_materials(elem_type: str, materials: list[str]) -> str:
    for material in materials:
        meta = BO3_FX_SURFACE_META.get(material)
        if meta:
            family = str(meta.get("family", "")).strip()
            if family:
                return family
    if elem_type == "decal":
        return "decal_surface_hit"
    return "billboard_additive_glow"


def _raw_fx_has_effect_refs(block: str) -> bool:
    for key in ("fxOnImpact", "fxOnDeath", "emission", "attachment"):
        match = re.search(rf'(?m)^\s*{re.escape(key)}\s+"([^"]*)"\s*;\s*$', block)
        if match and match.group(1).strip():
            return True
    return False


def _raw_fx_rewrite_editor_flags(tokens: list[str], is_looping: bool, family: str, effect_ref_only: bool) -> list[str]:
    del family  # reserved for future family-specific editor flag tuning
    safe = [token for token in tokens if token in RAW_FX_SAFE_EDITOR_FLAGS]
    if effect_ref_only:
        safe = [token for token in safe if token == "looping"]
    if is_looping and "looping" not in safe:
        safe.insert(0, "looping")
    if not is_looping:
        safe = [token for token in safe if token != "looping"]
    return list(dict.fromkeys(safe))


def _raw_fx_rewrite_native_flags(
    tokens: list[str],
    elem_type: str,
    family: str,
    use_pivot: bool,
    effect_ref_only: bool,
    allow_nonuniform_scale: bool,
    spawn_offset_has_volume: bool,
) -> list[str]:
    normalized_tokens = [("runRelToSpawn" if token == "runRelToOffset" else token) for token in tokens]
    if effect_ref_only:
        return ["runRelToEffect"]
    safe = [token for token in normalized_tokens if token in RAW_FX_SAFE_NATIVE_FLAGS]
    if not use_pivot:
        safe = [token for token in safe if token != "useBillboardPivot"]
    if elem_type in {"tail", "trail"}:
        allowed = {"spawnRelative", "spawnFrustumCull", "spawnOffsetNone", "runRelToSpawn", "runRelToEffect", "runRelToWorld", "trailOrientByVelocity", "drawPastFog", "playAttached"}
        safe = [token for token in safe if token in allowed]
        if allow_nonuniform_scale and "nonUniformScale" not in safe:
            safe.append("nonUniformScale")
    elif elem_type == "decal":
        allowed = {"spawnRelative", "spawnFrustumCull", "spawnOffsetNone", "runRelToSpawn", "runRelToEffect", "runRelToWorld", "dieOnTouch", "drawPastFog", "playAttached"}
        safe = [token for token in safe if token in allowed]
        if "runRelToSpawn" in safe:
            safe = [token for token in safe if token != "runRelToSpawn"]
            if spawn_offset_has_volume:
                safe = [token for token in safe if token != "spawnOffsetNone"]
                if "spawnOffsetCylinder" not in safe:
                    safe.append("spawnOffsetCylinder")
    elif elem_type in {"billboardsprite", "orientedsprite", "rotatedsprite"}:
        visual_safe = {
            "spawnRelative",
            "spawnFrustumCull",
            "spawnOffsetNone",
            "spawnOffsetSphere",
            "spawnOffsetCylinder",
            "runRelToSpawn",
            "runRelToEffect",
            "runRelToWorld",
            "drawPastFog",
            "emitOrientByElem",
            "useBillboardPivot",
            "playAttached",
        }
        if family in {"billboard_additive_glow", "billboard_soft_smoke", "billboard_simple_alpha", "billboard_distortion", "burst_emissive"}:
            safe = [token for token in safe if token in visual_safe]
        if "runRelToWorld" in safe:
            safe = [token for token in safe if token != "runRelToWorld"]
            replacement = "runRelToEffect" if elem_type == "rotatedsprite" else "runRelToSpawn"
            if replacement not in safe:
                safe.append(replacement)
        if family == "burst_emissive" and "spawnFrustumCull" not in safe:
            safe.append("spawnFrustumCull")
        if family == "burst_emissive":
            safe = [token for token in safe if token != "nonUniformScale"]
    return list(dict.fromkeys(safe))


def _raw_fx_rewrite_atlas(block: str, elem_type: str, rewrite_log: list[str]) -> str:
    tokens = _raw_fx_get_tokens(block, "atlasBehavior")
    entry_count = _raw_fx_get_single(block, "atlasEntryCount", integer=True)
    index = _raw_fx_get_single(block, "atlasIndex", integer=True)
    fps = _raw_fx_get_single(block, "atlasFps", integer=True)

    if entry_count is None:
        return block

    start_token = "startFixed"
    for token in tokens:
        if token in {"startRandom", "startIndexed", "startFixed", "startIndexedRange", "startFixedRange"}:
            start_token = token
            break

    if entry_count <= 1:
        new_tokens = ["startFixed"]
        block = _raw_fx_replace_tokens(block, "atlasBehavior", new_tokens)
        block = _raw_fx_replace_single(block, "atlasIndex", 0, integer=True)
        block = _raw_fx_replace_single(block, "atlasFps", 0, integer=True)
        block = _raw_fx_replace_single(block, "atlasLoopCount", 1, integer=True)
        block = _raw_fx_replace_single(block, "atlasColIndexBits", 0, integer=True)
        block = _raw_fx_replace_single(block, "atlasRowIndexBits", 0, integer=True)
        block = _raw_fx_replace_single(block, "atlasEntryCount", 1, integer=True)
        block = _raw_fx_replace_single(block, "atlasIndexRange", 0, integer=True)
        if tokens != new_tokens or (index or 0) != 0 or (fps or 0) != 0:
            rewrite_log.append("atlas->single_frame")
        return block

    canonical_start = {"startIndexedRange": "startIndexed", "startFixedRange": "startFixed"}.get(start_token, start_token)
    if canonical_start not in {"startRandom", "startIndexed", "startFixed"}:
        canonical_start = "startFixed"

    keep_play_over_life = "playOverLife" in tokens
    keep_loop_n = "loopOnlyNTimes" in tokens
    if elem_type in {"tail", "trail"} and keep_loop_n and (fps or 0) <= 0:
        keep_loop_n = False
    new_tokens = [canonical_start]
    if keep_play_over_life:
        new_tokens.append("playOverLife")
    if keep_loop_n:
        new_tokens.append("loopOnlyNTimes")
    if elem_type in {"line", "rotatedsprite"} and "playOverLife" in new_tokens:
        new_tokens = ["startRandom" if entry_count > 1 else "startFixed"]
    if new_tokens != tokens:
        rewrite_log.append(f"atlas:{'/'.join(tokens) or 'none'}->{'/'.join(new_tokens)}")
        block = _raw_fx_replace_tokens(block, "atlasBehavior", new_tokens)
    return block


def _raw_fx_clamp_timing(block: str, family: str, is_looping: bool, rewrite_log: list[str]) -> str:
    life_pair = _raw_fx_get_pair(block, "lifeSpanMsec", integer=True)
    if not life_pair:
        return block
    life_base = max(int(life_pair[0]), 1)
    rules = RAW_FX_TIMING_RULES.get(family, RAW_FX_TIMING_RULES["billboard_additive_glow"])

    fade_in = _raw_fx_get_pair(block, "fadeInRange")
    if fade_in:
        max_fade_in = max(0.0, float(life_base) * float(rules["fade_in_ratio"]))
        if fade_in[0] > max_fade_in:
            new_amp = min(fade_in[1], max_fade_in)
            block = _raw_fx_replace_pair(block, "fadeInRange", 0.0, new_amp)
            rewrite_log.append(f"fadeInRange:{fade_in[0]:.1f},{fade_in[1]:.1f}->0,{new_amp:.1f}")

    fade_out = _raw_fx_get_pair(block, "fadeOutRange")
    if fade_out:
        max_fade_out = max(0.0, float(life_base) * float(rules["fade_out_ratio"]))
        if fade_out[0] > max_fade_out:
            new_amp = min(fade_out[1], max_fade_out)
            block = _raw_fx_replace_pair(block, "fadeOutRange", max_fade_out, new_amp)
            rewrite_log.append(f"fadeOutRange:{fade_out[0]:.1f},{fade_out[1]:.1f}->{max_fade_out:.1f},{new_amp:.1f}")

    spawn_range = _raw_fx_get_pair(block, "spawnRange")
    if spawn_range:
        max_spawn_amp = max(float(life_base) * float(rules["spawn_ratio"]), 1.0)
        if spawn_range[1] > max_spawn_amp:
            block = _raw_fx_replace_pair(block, "spawnRange", 0.0, max_spawn_amp)
            rewrite_log.append(f"spawnRange:{spawn_range[0]:.1f},{spawn_range[1]:.1f}->0,{max_spawn_amp:.1f}")

    if is_looping:
        spawn_one_shot = _raw_fx_get_pair(block, "spawnOneShot", integer=True)
        if spawn_one_shot and (int(spawn_one_shot[0]) != 0 or int(spawn_one_shot[1]) != 0):
            block = _raw_fx_replace_pair(block, "spawnOneShot", 0, 0, integer=True)
            rewrite_log.append("spawnOneShot->0")
    else:
        spawn_looping = _raw_fx_get_pair(block, "spawnLooping", integer=True)
        spawn_loop_count = _raw_fx_get_pair(block, "spawnLoopingSpawnCount", integer=True)
        spawn_one_shot = _raw_fx_get_pair(block, "spawnOneShot", integer=True)
        if spawn_looping and (int(spawn_looping[0]) != 0 or int(spawn_looping[1]) != 0):
            block = _raw_fx_replace_pair(block, "spawnLooping", 0, 0, integer=True)
            rewrite_log.append("spawnLooping->0")
        if spawn_loop_count and (int(spawn_loop_count[0]) != 0 or int(spawn_loop_count[1]) != 0):
            block = _raw_fx_replace_pair(block, "spawnLoopingSpawnCount", 0, 0, integer=True)
            rewrite_log.append("spawnLoopingSpawnCount->0")
        if spawn_one_shot and int(spawn_one_shot[0]) == 0 and int(spawn_one_shot[1]) == 0:
            block = _raw_fx_replace_pair(block, "spawnOneShot", 1, 0, integer=True)
            rewrite_log.append("spawnOneShot->1")

    return block


def rewrite_bo3_servant_raw_fx(path: Path) -> None:
    if not path.exists():
        return

    raw_text = path.read_text(encoding="utf-8", errors="replace")
    normalized = normalize_placeholder_scale_graphs(raw_text)
    header, blocks = _split_raw_fx_top_level_blocks(normalized)
    if not blocks:
        if normalized != raw_text:
            path.write_text(normalized, encoding="utf-8")
        return

    file_report: dict[str, object] = {"path": str(path), "effects": []}
    rewritten_blocks: list[str] = []

    for block in blocks:
        original_block = block
        rewrite_log: list[str] = []

        if USE_STOCK_FX_MATERIAL_PROBE:
            material_probe_replacements = RAW_FX_STOCK_MATERIAL_PROBE_MAP.get(path.stem)
            if material_probe_replacements:
                block = _raw_fx_replace_material_refs(block, material_probe_replacements, rewrite_log)

        elem_type, materials = _raw_fx_find_visual_block(block)
        family = _raw_fx_family_for_materials(elem_type, materials)
        has_effect_refs = _raw_fx_has_effect_refs(block)
        effect_ref_only = has_effect_refs and not materials
        size0 = _raw_fx_get_single(block, "sizeGraph0")
        size1 = _raw_fx_get_single(block, "sizeGraph1")
        size0_block = _raw_fx_get_statement_block(block, "sizeGraph0")
        size1_block = _raw_fx_get_statement_block(block, "sizeGraph1")
        allow_nonuniform_scale = (
            elem_type in {"tail", "trail"}
            and (
                (size0 is not None and size1 is not None and abs(size0 - size1) > 0.01)
                or (
                    size0_block
                    and size1_block
                    and size0_block.replace("sizeGraph0", "sizeGraphX", 1)
                    != size1_block.replace("sizeGraph1", "sizeGraphX", 1)
                )
            )
        )
        spawn_offset_radius = _raw_fx_get_pair(block, "spawnOffsetRadius")
        spawn_offset_height = _raw_fx_get_pair(block, "spawnOffsetHeight")
        spawn_offset_has_volume = bool(
            (spawn_offset_radius and (abs(spawn_offset_radius[0]) > 0.0 or abs(spawn_offset_radius[1]) > 0.0))
            or (spawn_offset_height and (abs(spawn_offset_height[0]) > 0.0 or abs(spawn_offset_height[1]) > 0.0))
        )
        gravity_pair = _raw_fx_get_pair(block, "gravity")
        has_gravity = bool(gravity_pair and (abs(gravity_pair[0]) > 0.0 or abs(gravity_pair[1]) > 0.0))

        dynamic_light_pattern = re.compile(r"(?ms)^\s*dynamicLight2\s*\n\s*\{.*?^\s*\};\s*")
        if dynamic_light_pattern.search(block):
            block = dynamic_light_pattern.sub("", block)
            rewrite_log.append("removed_dynamicLight2")

        pivot_pair = _raw_fx_get_pair(block, "billboardPivot")
        use_pivot = False
        if pivot_pair:
            if abs(pivot_pair[0]) < 0.05 and abs(pivot_pair[1]) < 0.05:
                if abs(pivot_pair[0]) > 0.0 or abs(pivot_pair[1]) > 0.0:
                    block = _raw_fx_replace_billboard_pivot(block, 0.0, 0.0)
                    rewrite_log.append("billboardPivot->0")
            else:
                use_pivot = True

        editor_tokens = _raw_fx_get_tokens(block, "editorFlags")
        is_looping = "looping" in editor_tokens
        if not is_looping:
            spawn_looping = _raw_fx_get_pair(block, "spawnLooping", integer=True)
            spawn_loop_count = _raw_fx_get_pair(block, "spawnLoopingSpawnCount", integer=True)
            is_looping = bool(
                spawn_looping
                and spawn_loop_count
                and (int(spawn_looping[0]) > 0 and int(spawn_loop_count[0]) > 0)
            )
        new_editor_tokens = _raw_fx_rewrite_editor_flags(editor_tokens, is_looping, family, effect_ref_only)
        if new_editor_tokens != editor_tokens:
            block = _raw_fx_replace_tokens(block, "editorFlags", new_editor_tokens)
            rewrite_log.append(f"editorFlags:{' '.join(editor_tokens) or '<none>'}->{ ' '.join(new_editor_tokens) or '<none>' }")

        native_tokens = _raw_fx_get_tokens(block, "flags")
        new_native_tokens = _raw_fx_rewrite_native_flags(
            native_tokens,
            elem_type,
            family,
            use_pivot,
            effect_ref_only,
            allow_nonuniform_scale,
            spawn_offset_has_volume,
        )
        if new_native_tokens != native_tokens:
            block = _raw_fx_replace_tokens(block, "flags", new_native_tokens)
            rewrite_log.append(f"flags:{' '.join(native_tokens) or '<none>'}->{ ' '.join(new_native_tokens) or '<none>' }")

        if (
            elem_type in {"billboardsprite", "orientedsprite", "rotatedsprite"}
            and has_gravity
            and "spawnFrustumCull" not in new_native_tokens
        ):
            new_native_tokens = list(dict.fromkeys([*new_native_tokens, "spawnFrustumCull"]))
            block = _raw_fx_replace_tokens(block, "flags", new_native_tokens)
            rewrite_log.append("flags:+spawnFrustumCull_for_gravity")

        block = _raw_fx_rewrite_atlas(block, elem_type, rewrite_log)
        block = _raw_fx_clamp_timing(block, family, is_looping, rewrite_log)
        block = _raw_fx_normalize_billboard_widths(block, elem_type, rewrite_log)
        block = _raw_fx_apply_transplant_stage(path.stem, block, original_block, rewrite_log)

        file_report["effects"].append(
            {
                "name": _raw_fx_effect_name(block),
                "elem_type": elem_type,
                "family": family,
                "materials": materials,
                "rewrites": rewrite_log,
            }
        )
        rewritten_blocks.append(block.strip() + "\n")

    rebuilt = header.rstrip() + "\n\n" + "\n\n".join(rewritten_blocks)
    if not rebuilt.endswith("\n"):
        rebuilt += "\n"
    if rebuilt != raw_text:
        path.write_text(rebuilt, encoding="utf-8")
    RAW_FX_STRUCTURE_REPORT[path.stem] = file_report

# Live tuning.
if USE_T5_GERSH:
    PROOF_CLIP_SIZE = "3"
    PROOF_START_AMMO = "3"
    PROOF_MAX_AMMO = "3"
    PROOF_FIRE_TIME = "0.3"
    PROOF_DAMAGE = "0"
    EXPECTED_HUD_RESERVE = "0"
else:
    # User requested 1 round chambered and 9 in reserve for the BO2 donor shell.
    # On this BO2 shell, maxAmmo behaves like the total pool including the chamber,
    # so engine-side max must be 10 to show 1/9 on the HUD.
    PROOF_CLIP_SIZE = "1"
    PROOF_START_AMMO = "10"
    PROOF_MAX_AMMO = "10"
    PROOF_FIRE_TIME = "0.75"
    PROOF_DAMAGE = "2000"
    EXPECTED_HUD_RESERVE = "9"

EXPECTED_CLIP = PROOF_CLIP_SIZE
EXPECTED_ENGINE_MAX = PROOF_MAX_AMMO
IDG_VIEW_GLB_SRC = (
    Path(IDG_VIEW_GLB_OVERRIDE).resolve()
    if IDG_VIEW_GLB_OVERRIDE
    else ROOT / "_build" / "bo3_rev_idg_weapon_only" / "bo3_rev_idg_weapon_only.glb"
)
IDG_WEAPON_ONLY_RIG_REPORT = ROOT / "_build" / "bo3_rev_idg_weapon_only" / "weapon_only_rig_report.json"
IDG_VIEW_GLB_DST = MODEL_EXPORT_DIR / f"{MODEL_ASSET}_lod0.glb"
IDG_VIEWHANDS_GLB_DST = MODEL_EXPORT_DIR / "bo3_rev_idg_viewhands_lod0.glb"
BRIDGE_VIEWHANDS_GLB_DST = MODEL_EXPORT_DIR / "bo3_rev_bridge_viewhands_lod0.glb"

T7_ANIM_BIN_DIR = Path(
    r"Z:\Games\T7 Assets V2.5 (2)\T7 Assets V2.5\T7 Assets\xanim_export\_midgetblaster\black_ops_3"
)
PYCOD_ROOT = ROOT / "_tmp_tools" / "blender-cod-master" / "blender-cod-master" / "io_scene_cod"
BLENDER_COD_PARENT = ROOT / "tools" / "external" / "blender-cod-src"
BLENDER_REBAKE_WORKER = ROOT / "tools" / "asset_port_pipeline" / "blender_rebake_xanim_worker.py"
OAT_RELEASE_DIR = ROOT / "_build" / "oat_release" / "unzipped"
USE_RELEASE_LINKER = os.environ.get("ROGUE_USE_RELEASE_LINKER", "0") not in ("0", "false", "False")
# The local dev Linker still handles this project's custom material/techset mix
# better than the stable release build. The stable Unlinker, however, is more
# reliable for listing/validating the emitted fastfile contents. Keep those roles
# separate by default, but allow explicit opt-in to the release Linker for
# simpler stock-only test builds where we want the stricter writer.
LINKER = (
    OAT_RELEASE_DIR / "Linker.exe"
    if USE_RELEASE_LINKER and (OAT_RELEASE_DIR / "Linker.exe").exists()
    else ROOT / "tools" / "oat" / "Linker.exe"
)
DEV_LINKER = ROOT / "tools" / "oat" / "Linker.exe"
DEV_UNLINKER = ROOT / "tools" / "oat" / "Unlinker.exe"
UNLINKER = (
    OAT_RELEASE_DIR / "Unlinker.exe"
    if (OAT_RELEASE_DIR / "Unlinker.exe").exists()
    else ROOT / "tools" / "oat" / "Unlinker.exe"
)
PE_MACHINE_X86 = 0x14C
PE_MACHINE_X64 = 0x8664
GSC_TOOL = ROOT / "tools" / "gsc-tool.exe"
XANIM_COMPILER = ROOT / "_build" / "compile_xanim_zone.py"
XANIM_ORACLE_DIR = ROOT / "_build" / "xanim_oracles"
XANIM_IDLE_ORACLE_FF = XANIM_ORACLE_DIR / "vm_zod_idle_donorclone_mod_load.ff"
SO_SURVIVAL_BASELINE_FF = ROOT / "_build" / "ff_backup" / "20260213-123213" / "so_zsurvival_zm_transit.ff"
ZM_TRANSIT_BASELINE_FF = ROOT / "_build" / "ff_backup" / "20260213-123213" / "zm_transit.ff"
FULL_RUNTIME_SOURCE_ROOT = ROOT / "_build" / "runtime_unlink_so_zsurvival_clean"
FULL_RUNTIME_ZONE_SOURCE = FULL_RUNTIME_SOURCE_ROOT / "zone_source" / f"{RUNTIME_ZONE_NAME}.zone"
ZONE_DUMP_SOURCE_ROOT = ROOT / "zone_dump" / "zone_raw" / "so_zsurvival_zm_transit"
ZONE_DUMP_TOMB_ROOT = ROOT / "zone_dump" / "zone_raw" / "zm_tomb"
TRANSIT_UNLINK_ROOT = ROOT / "_build" / "runtime_unlink_zm_transit_full_1"
FX_RUNTIME_SUPPORT_ROOTS = [
    ROOT / "_build" / "runtime_unlink_debug",
    ROOT / "_build" / "runtime_unlink_zm_transit_clean2",
    ROOT / "_build" / "runtime_unlink_zm_transit_patch_2",
    ROOT / "zone_dump",
    WORK / "unlinked_runtime",
]
FX_RUNTIME_SUPPORT_IMAGE_CANDIDATES: dict[str, list[Path]] = {
    "fxt_light_glow_square": [
        ROOT / "_build" / "stock_iwi_dump" / "images" / "fxt_light_glow_square.iwi",
        ROOT / "_build" / "dds_check_live" / "fxt_light_glow_square.iwi",
        ROOT / "zone_dump" / "images" / "fxt_light_glow_square.dds",
    ],
    "$identitynormalmap": [
        ROOT / "_build" / "runtime_unlink_debug" / "images" / "$identitynormalmap.dds",
        WORK / "unlinked_runtime" / "images" / "$identitynormalmap.dds",
    ],
    "fxt_env_dust_mote_atlas": [
        ROOT / "zone_dump" / "zone_raw" / "zm_tomb" / "images" / "fxt_env_dust_mote_atlas.dds",
        ROOT / "_build" / "zone_dump_full_tomb" / "images" / "fxt_env_dust_mote_atlas.dds",
    ],
}
FULL_MAP_ZONE_SOURCE = TRANSIT_UNLINK_ROOT / "zone_source" / "zm_transit.zone"
WEAPON_SOURCE_ROOTS = [
    TRANSIT_UNLINK_ROOT,
    FULL_RUNTIME_SOURCE_ROOT,
    ZONE_DUMP_SOURCE_ROOT,
    ZONE_DUMP_TOMB_ROOT,
]
MIN_VIEWHANDS_TOOL = ROOT / "_build" / "rebuild_min_viewhands_glb.py"
STUB_VIEWHANDS_NAMES = ["c_zom_suit_viewhands", "c_zom_hazmat_viewhands"]


def runtime_linker_path() -> Path:
    if using_dedicated_bo3_fx_load_lane() and (OAT_RELEASE_DIR / "Linker.exe").exists():
        return OAT_RELEASE_DIR / "Linker.exe"
    return LINKER


def read_pe_machine(path: Path) -> int:
    with path.open("rb") as handle:
        mz_header = handle.read(64)
        if len(mz_header) < 64:
            raise RuntimeError(f"PE header too small: {path}")
        pe_offset = struct.unpack_from("<I", mz_header, 0x3C)[0]
        handle.seek(pe_offset + 4)
        machine_bytes = handle.read(2)
        if len(machine_bytes) < 2:
            raise RuntimeError(f"PE machine field missing: {path}")
        return struct.unpack("<H", machine_bytes)[0]


def pe_machine_label(machine: int) -> str:
    if machine == PE_MACHINE_X86:
        return "x86"
    if machine == PE_MACHINE_X64:
        return "x64"
    return hex(machine)


def verify_t6_oat_binary_architectures() -> dict[str, str]:
    """T6 DB asset code is 32-bit-layout-sensitive; runtime-safe OAT binaries must stay x86."""
    tool_paths = {
        "runtime_linker": runtime_linker_path(),
        "stable_unlinker": UNLINKER,
    }
    if using_dedicated_bo3_fx_load_lane():
        tool_paths["dev_linker"] = DEV_LINKER
        tool_paths["dev_unlinker"] = DEV_UNLINKER

    out: dict[str, str] = {}
    for label, path in tool_paths.items():
        if not path.exists():
            raise RuntimeError(f"Missing required OAT binary for {label}: {path}")
        machine = read_pe_machine(path)
        out[label] = pe_machine_label(machine)
        if machine != PE_MACHINE_X86:
            raise RuntimeError(
                f"T6 runtime packaging requires x86 OAT binaries for 32-bit DB layouts; "
                f"{label} is {pe_machine_label(machine)} at {path}"
            )
    return out

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

IDG_ANIM_SUBSET_RAW = os.environ.get("ROGUE_BO3_ANIM_SUBSET", "").strip()
if IDG_ANIM_SUBSET_RAW:
    requested = [name.strip() for name in IDG_ANIM_SUBSET_RAW.split(",") if name.strip()]
    if requested:
        requested_set = set(requested)
        IDG_ANIMS = [name for name in IDG_ANIMS if name in requested_set]

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
    "emp_grenade_zm": {
        "idleAnim": "viewmodel_zombie_monkeybomb_idle",
        "emptyIdleAnim": "viewmodel_zombie_monkeybomb_idle",
        "fireAnim": "viewmodel_zombie_monkeybomb_throw",
        "holdFireAnim": "viewmodel_zombie_monkeybomb_pullpin",
        "lastShotAnim": "viewmodel_zombie_monkeybomb_throw",
        "raiseAnim": "viewmodel_zombie_monkeybomb_idle",
        "dropAnim": "viewmodel_zombie_monkeybomb_idle",
        "altRaiseAnim": "viewmodel_zombie_monkeybomb_throw",
        "altDropAnim": "viewmodel_zombie_monkeybomb_idle",
        "quickRaiseAnim": "viewmodel_zombie_monkeybomb_idle",
        "quickDropAnim": "viewmodel_zombie_monkeybomb_idle",
        "emptyRaiseAnim": "viewmodel_zombie_monkeybomb_idle",
        "emptyDropAnim": "viewmodel_zombie_monkeybomb_idle",
        "firstRaiseSound": "zmb_monkey_raise",
        "firstRaiseSoundPlayer": "zmb_monkey_raise_plr",
        "fireSound": "zmb_monkey_throw",
        "fireSoundPlayer": "zmb_monkey_throw",
        "bounceSound": "zmb_monkey_land",
        "offhandClass": "Smoke Grenade",
        "hudIcon": "hud_cymbal_monkey",
        "killIcon": "hud_cymbal_monkey",
        "dpadIcon": "hud_cymbal_monkey",
        "holdFireTime": "1.9",
        "fireTime": "0.7",
        "raiseTime": "0.25",
        "altRaiseTime": "0.05",
        "quickRaiseTime": "0.5",
        "firstRaiseTime": "0.5",
        "emptyRaiseTime": "0.5",
        "sprintInTime": "0.08",
        "sprintOutTime": "0.08",
        "projectileSpeed": "800",
        "projectileSpeedUp": "100",
        "explodeOnGround": "0",
        "rotate": "0",
        "isRollingGrenade": "0",
    },
    "mg08_zm": {
        "fireAnim": "viewmodel_zomb_staff_fire_reload",
        "lastShotAnim": "viewmodel_zomb_staff_fire_reload",
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
        FX_DIR,
        XANIM_DIR,
        ZONE_SOURCE_DIR,
        ZONE_RAW_ROOT,
    ):
        path.mkdir(parents=True, exist_ok=True)


def reset_work_dirs() -> None:
    for path in (
        OUTPUT,
        MODEL_EXPORT_DIR,
        XMODEL_DIR,
        MATERIALS_DIR,
        IMAGES_DIR,
        WEAPONS_DIR,
        FX_DIR,
        XANIM_DIR,
        ZONE_SOURCE_DIR,
        ZONE_RAW_ROOT,
        IDG_SURFACE_BUNDLE_ROOT,
        IDG_SURFACE_PROJECT_ROOT,
        FX_SURFACE_BUNDLE_ROOT,
        FX_SURFACE_PROJECT_ROOT,
    ):
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    ensure_dirs()


def donor_anim_profile_overrides() -> dict[str, str]:
    if USE_BO3_IDG_ANIMS:
        return {}
    return dict(DONOR_ANIM_PROFILE_OVERRIDES.get(WEAPON_ASSET, {}))


def donor_extra_runtime_xanims() -> list[str]:
    if probe_only_fast_path_enabled():
        return []
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
    if probe_only_fast_path_enabled():
        return False
    if GUN_MODEL_MODE in ("custom", "idg", ""):
        return True
    if GUN_MODEL_MODE in ("base", "literal"):
        return False
    raise RuntimeError(f"Unsupported ROGUE_GUN_MODEL_MODE: {GUN_MODEL_MODE}")


def uses_t5_gersh_assets() -> bool:
    return USE_T5_GERSH


def use_custom_idg_viewhands() -> bool:
    return USE_CUSTOM_IDG_VIEWHANDS and not probe_only_fast_path_enabled()


def resolved_gun_model(base_fields: dict[str, str]) -> str:
    if uses_custom_model():
        return MODEL_ASSET
    if probe_only_fast_path_enabled():
        return str(base_fields.get("gunModel", "")).strip()
    if GUN_MODEL_MODE == "base":
        return str(base_fields.get("gunModel", "")).strip()
    if GUN_MODEL_MODE == "literal":
        if not GUN_MODEL_LITERAL:
            raise RuntimeError("ROGUE_GUN_MODEL_LITERAL is required when ROGUE_GUN_MODEL_MODE=literal")
        return GUN_MODEL_LITERAL
    raise RuntimeError(f"Unhandled gun model mode: {GUN_MODEL_MODE}")


def resolved_world_model(base_fields: dict[str, str]) -> str:
    if uses_t5_gersh_assets() and uses_custom_model():
        return WORLD_MODEL_ASSET
    return str(base_fields.get("worldModel", "")).strip()


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
    if uses_t5_gersh_assets():
        if not T5_GERSH_VIEW_GLB_SRC.exists() or not T5_GERSH_WORLD_GLB_SRC.exists():
            raise FileNotFoundError(
                "Missing T5 Gersh GLBs: "
                f"view={T5_GERSH_VIEW_GLB_SRC.exists()} world={T5_GERSH_WORLD_GLB_SRC.exists()}"
            )
        if not T5_GERSH_VIEW_JSON_SRC.exists() or not T5_GERSH_WORLD_JSON_SRC.exists():
            raise FileNotFoundError(
                "Missing T5 Gersh xmodel JSON: "
                f"view={T5_GERSH_VIEW_JSON_SRC.exists()} world={T5_GERSH_WORLD_JSON_SRC.exists()}"
            )

        copy_glb_with_t5_joint_fix(T5_GERSH_VIEW_GLB_SRC, T5_GERSH_VIEW_GLB_DST)
        copy_glb_with_t5_joint_fix(T5_GERSH_WORLD_GLB_SRC, T5_GERSH_WORLD_GLB_DST)

        view_meta = json.loads(T5_GERSH_VIEW_JSON_SRC.read_text(encoding="utf-8", errors="replace"))
        world_meta = json.loads(T5_GERSH_WORLD_JSON_SRC.read_text(encoding="utf-8", errors="replace"))

        view_out = {
            "$schema": "http://openassettools.dev/schema/xmodel.v1.json",
            "_game": "t6",
            "_type": "xmodel",
            "_version": 2,
            "flags": int(view_meta.get("flags", 524288)),
            "lightingOriginOffset": {"x": 0.0, "y": 0.0, "z": 0.5},
            "lightingOriginRange": 0.5,
            "lods": [{"distance": float((view_meta.get("lods") or [{}])[0].get("distance", 4426.533203125)), "file": f"model_export/{MODEL_ASSET}_lod0.glb"}],
            "type": "rigid",
        }
        world_out = {
            "$schema": "http://openassettools.dev/schema/xmodel.v1.json",
            "_game": "t6",
            "_type": "xmodel",
            "_version": 2,
            "flags": int(world_meta.get("flags", 0)),
            "lightingOriginOffset": {"x": 0.0, "y": 0.0, "z": 0.5},
            "lightingOriginRange": 0.5,
            "lods": [{"distance": float((world_meta.get("lods") or [{}])[0].get("distance", 2500.0)), "file": f"model_export/{WORLD_MODEL_ASSET}_lod0.glb"}],
            "type": "rigid",
        }
        (XMODEL_DIR / f"{MODEL_ASSET}.json").write_text(json.dumps(view_out, indent=2) + "\n", encoding="utf-8")
        (XMODEL_DIR / f"{WORLD_MODEL_ASSET}.json").write_text(json.dumps(world_out, indent=2) + "\n", encoding="utf-8")
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


def copy_glb_with_t5_joint_fix(src: Path, dst: Path) -> None:
    data = src.read_bytes()
    if data[:4] != b"glTF":
        raise RuntimeError(f"Not a GLB file: {src}")

    version = data[4:8]
    total_len = struct.unpack("<I", data[8:12])[0]
    if total_len != len(data):
        raise RuntimeError(f"Unexpected GLB length for {src}")

    offset = 12
    chunks: list[tuple[bytes, bytes]] = []
    while offset < len(data):
        chunk_len = struct.unpack("<I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_data = data[offset + 8 : offset + 8 + chunk_len]
        chunks.append((chunk_type, chunk_data))
        offset += 8 + chunk_len

    if not chunks or chunks[0][0] != b"JSON":
        raise RuntimeError(f"Invalid GLB JSON chunk: {src}")

    gltf = json.loads(chunks[0][1].decode("utf-8"))
    skins = gltf.get("skins", [])
    nodes = gltf.get("nodes", [])

    if skins and nodes:
        skin = skins[0] or {}
        joints = list(skin.get("joints", []) or [])
        if joints:
            parents: dict[int, int] = {}
            for node_index, node in enumerate(nodes):
                for child in node.get("children", []) or []:
                    parents[int(child)] = node_index

            roots = [joint for joint in joints if parents.get(int(joint)) not in joints]
            if len(roots) > 1 and 0 in joints and 1 in joints:
                root_children = list((nodes[0] or {}).get("children", []) or [])
                if 1 not in root_children:
                    root_children.append(1)
                    nodes[0]["children"] = root_children
                    gltf["nodes"] = nodes

    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_padded = json_bytes + (b" " * ((4 - (len(json_bytes) % 4)) % 4))

    out = bytearray()
    out.extend(b"glTF")
    out.extend(version)
    out.extend(b"\x00\x00\x00\x00")
    out.extend(struct.pack("<I", len(json_padded)))
    out.extend(b"JSON")
    out.extend(json_padded)

    for chunk_type, chunk_data in chunks[1:]:
        padded = chunk_data + (b"\x00" * ((4 - (len(chunk_data) % 4)) % 4))
        out.extend(struct.pack("<I", len(chunk_data)))
        out.extend(chunk_type)
        out.extend(padded)

    out[8:12] = struct.pack("<I", len(out))
    dst.write_bytes(bytes(out))


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
        return list(STAGED_FX_MATERIAL_NAMES)
    names = staged_model_material_names()
    for material_name in STAGED_FX_MATERIAL_NAMES:
        if material_name not in names:
            names.append(material_name)
    return names


def staged_model_material_names() -> list[str]:
    if not uses_custom_model():
        return []
    names = list(MODEL_MATERIALS)
    for material_name in read_glb_material_names(IDG_VIEW_GLB_DST):
        if material_name not in names:
            names.append(material_name)
    return names


def using_dedicated_bo3_fx_load_lane() -> bool:
    return USE_BO3_RAW_FX and USE_DEDICATED_BO3_FX_LOAD


def runtime_zone_image_names() -> list[str]:
    probe_images = client_ffprobe_runtime_dependencies()["images"]
    if using_dedicated_bo3_fx_load_lane():
        names = list(STAGED_MODEL_IMAGE_NAMES)
    else:
        names = list(STAGED_IMAGE_NAMES)
        for image_name in probe_images:
            if image_name not in names:
                names.append(image_name)
    return names


def runtime_zone_material_names() -> list[str]:
    probe_materials = client_ffprobe_runtime_dependencies()["materials"]
    if uses_t5_gersh_assets():
        names = [T5_GERSH_MATERIAL_LINE]
    elif using_dedicated_bo3_fx_load_lane():
        names = staged_model_material_names()
    else:
        names = staged_material_names()
    if client_ffprobe_enabled() and TRANSIT_OVERLAY_MATERIAL_NAME not in names:
        names.append(TRANSIT_OVERLAY_MATERIAL_NAME)
    if not using_dedicated_bo3_fx_load_lane():
        for material_name in probe_materials:
            if material_name not in names:
                names.append(material_name)
    return names


def runtime_zone_fx_names() -> list[str]:
    probe_fx = client_ffprobe_runtime_dependencies()["fx"]
    if using_dedicated_bo3_fx_load_lane():
        names = []
    else:
        names = list(STAGED_FX_NAMES)
        for fx_name in probe_fx:
            if fx_name not in names:
                names.append(fx_name)
    return names


def fx_load_zone_image_names() -> list[str]:
    return list(STAGED_FX_IMAGE_NAMES)


def fx_load_zone_material_names() -> list[str]:
    return list(STAGED_FX_MATERIAL_NAMES)


def fx_load_zone_fx_names() -> list[str]:
    return list(STAGED_FX_NAMES)


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


HB21_GDT_ASSET_RE = re.compile(r'^\s*"([^"]+)"\s+\(\s*"([^"]+)"\s*\)\s*$')
HB21_GDT_ALIAS_RE = re.compile(r'^\s*"([^"]+)"\s+\[\s*"([^"]+)"\s*\]\s*$')
HB21_GDT_PROP_RE = re.compile(r'^\s*"([^"]+)"\s+"([^"]*)"\s*$')


def parse_hb21_gdt(gdt_path: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    current: dict[str, object] | None = None

    for raw_line in gdt_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.rstrip("\r\n")
        if not line.strip():
            continue

        asset_match = HB21_GDT_ASSET_RE.match(line)
        if asset_match:
            current = {
                "name": asset_match.group(1),
                "gdf": asset_match.group(2),
                "alias": "",
                "props": {},
            }
            continue

        alias_match = HB21_GDT_ALIAS_RE.match(line)
        if alias_match:
            current = {
                "name": alias_match.group(1),
                "gdf": "",
                "alias": alias_match.group(2),
                "props": {},
            }
            continue

        if line.strip() == "}":
            if current is not None:
                entries.append(current)
            current = None
            continue

        if current is None:
            continue

        prop_match = HB21_GDT_PROP_RE.match(line)
        if not prop_match:
            continue

        props = current["props"]
        assert isinstance(props, dict)
        props[prop_match.group(1)] = prop_match.group(2)

    return entries


def build_hb21_gdt_index() -> dict[str, dict[str, object]]:
    index: dict[str, dict[str, object]] = {}
    gdt_paths: list[Path] = []
    for root in (BO3_FX_LIBRARY_ROOT / "texture_assets", BO3_FX_LIBRARY_ROOT / "source_data"):
        if not root.exists():
            continue
        gdt_paths.extend(sorted(root.rglob("*.gdt")))
    for gdt_path in gdt_paths:
        if not gdt_path.exists():
            continue
        for entry in parse_hb21_gdt(gdt_path):
            entry["source_gdt"] = str(gdt_path)
            index[str(entry["name"])] = entry
    return index


def resolve_hb21_entry(
    entry_name: str,
    index: dict[str, dict[str, object]],
    stack: set[str] | None = None,
) -> dict[str, object]:
    lookup_name = HB21_ASSET_ALIASES.get(entry_name, entry_name)
    entry = index.get(lookup_name)
    if entry is None:
        raise KeyError(f"HB21 asset not found: {entry_name}")

    stack = set() if stack is None else set(stack)
    if lookup_name in stack:
        raise RuntimeError(f"HB21 alias loop detected: {' -> '.join([*stack, lookup_name])}")
    stack.add(lookup_name)

    props: dict[str, str] = {}
    alias_name = str(entry.get("alias", "")).strip()
    gdf = str(entry.get("gdf", "")).strip()
    if alias_name:
        base = resolve_hb21_entry(alias_name, index, stack)
        gdf = gdf or str(base.get("gdf", "")).strip()
        props.update(base.get("props", {}))

    own_props = entry.get("props", {})
    if isinstance(own_props, dict):
        props.update({str(k): str(v) for k, v in own_props.items()})

    return {
        "name": entry_name,
        "gdf": gdf,
        "props": props,
        "source_gdt": entry.get("source_gdt", ""),
        "alias": alias_name or (lookup_name if lookup_name != entry_name else ""),
    }


def iter_bo3_servant_fx_blocks() -> list[dict[str, object]]:
    block_pattern = re.compile(
        r"(billboardSprite|orientedSprite|rotatedSprite|line|tail|trail|cloud|decal)\s*\{(.*?)\};",
        re.IGNORECASE | re.DOTALL,
    )
    quoted_pattern = re.compile(r'"([^"]+)"')
    rows: list[dict[str, object]] = []
    for fx_name in active_fx_surface_source_names():
        src = resolve_fx_source_path(fx_name)
        if src is None:
            continue
        text = src.read_text(encoding="utf-8", errors="ignore")
        for match in block_pattern.finditer(text):
            quoted_values = [value.strip() for value in quoted_pattern.findall(match.group(2)) if value.strip()]
            rows.append(
                {
                    "fx_name": fx_name,
                    "elem_type": match.group(1).strip().lower(),
                    "quoted_values": quoted_values,
                }
            )
    if rows:
        return rows
    return []


def load_bo3_servant_fx_material_names() -> list[str]:
    rows = iter_bo3_servant_fx_blocks()
    if rows:
        names: set[str] = set()
        for row in rows:
            for value in row.get("quoted_values", []):
                value_str = str(value).strip()
                if value_str:
                    names.add(value_str)
        if names:
            return sorted(names)
    if active_fx_surface_source_names():
        return []
    if FX_GRAPH_REPORT.exists():
        payload = json.loads(FX_GRAPH_REPORT.read_text(encoding="utf-8", errors="replace"))
        names = [str(name).strip() for name in payload.get("all_visual_materials", []) if str(name).strip()]
        if names:
            return sorted(dict.fromkeys(names))
    return [
        "gfx_debris_clump_em",
        "gfx_distort_ring_hvy",
        "gfx_distort_ring_ripple",
        "gfx_dust_gen_em",
        "gfx_dust_gen_lit",
        "gfx_fire_flame_base_1_anim_em_i1024",
        "gfx_fire_flame_base_2_anim_em_i1024",
        "gfx_fog_slow_lg_anim_em",
        "gfx_fog_slow_lg_anim_em_i1024",
        "gfx_fog_slow_md_anim_lit",
        "gfx_fog_slow_sm_anim_lit",
        "gfx_decal_exp_blast_01",
        "gfx_decal_exp_blast_03",
        "gfx_gel_splat_radial_em",
        "gfx_gel_splat_side_em",
        "gfx_gel_splat_spread_em",
        "gfx_gel_splat_wide_em",
        "gfx_gib_metal_01_lit",
        "gfx_gib_metal_02_lit",
        "gfx_light_phosphorous_em",
        "gfx_light_phosphorous_em_i1024",
        "gfx_shockwave_anim_em",
        "gfx_shockwave_elec_anim_em_i2048",
        "gfx_smk_puff_light_varied",
        "gfx_smk_whisp_anim_em",
        "gfx_water_bubble_em",
        "gfx_water_splash_em",
    ]


def scan_bo3_servant_fx_surface_usage() -> dict[str, dict[str, object]]:
    usage: dict[str, dict[str, object]] = {}
    for row in iter_bo3_servant_fx_blocks():
        fx_name = str(row.get("fx_name", "")).strip()
        elem_type = str(row.get("elem_type", "")).strip().lower()
        for value in row.get("quoted_values", []):
            material_name = str(value).strip()
            if not material_name:
                continue
            entry = usage.setdefault(
                material_name,
                {
                    "material_name": material_name,
                    "fx_names": [],
                    "elem_types": [],
                    "usage_count": 0,
                    "looping_uses": 0,
                    "oneshot_uses": 0,
                    "distortion_hints": 0,
                    "cloud_hints": 0,
                },
            )
            entry["usage_count"] = int(entry.get("usage_count", 0)) + 1
            if fx_name and fx_name not in entry["fx_names"]:
                entry["fx_names"].append(fx_name)
            if elem_type and elem_type not in entry["elem_types"]:
                entry["elem_types"].append(elem_type)
            if elem_type == "cloud":
                entry["cloud_hints"] = int(entry.get("cloud_hints", 0)) + 1
            if elem_type in {"billboardsprite", "orientedsprite", "rotatedsprite"}:
                entry["looping_uses"] = int(entry.get("looping_uses", 0)) + 1
            if elem_type in {"trail", "tail", "line", "decal"}:
                entry["oneshot_uses"] = int(entry.get("oneshot_uses", 0)) + 1
            lowered = material_name.lower()
            if "distort" in lowered or "shockwave" in lowered:
                entry["distortion_hints"] = int(entry.get("distortion_hints", 0)) + 1
    return usage


def fx_contract_catalog_payload() -> dict[str, object]:
    rows = []
    for family, spec in FX_FAMILY_SPECS.items():
        template = Path(spec["template"])
        try:
            template_label = template.relative_to(ROOT).as_posix()
        except ValueError:
            template_label = str(template)
        rows.append(
            {
                "family": family,
                "template": template_label,
                "cameraRegion": spec["camera_region"],
                "techniqueSet": spec["default_technique_set"],
                "imagePolicy": spec["image_policy"],
                "stockRefs": list(spec.get("stock_refs", [])),
                "notes": spec.get("notes", ""),
            }
        )
    return {"rows": rows}


def classify_fx_surface(meta: dict[str, object]) -> dict[str, object]:
    material_name = str(meta.get("materialName", meta.get("material_name", ""))).strip()
    material_type = str(meta.get("materialType", "")).strip().lower()
    color_map = str(meta.get("colorMap", "")).strip().lower()
    usage = meta.get("usage", {})
    assert isinstance(usage, dict)
    elem_types = [str(elem).strip().lower() for elem in usage.get("elem_types", []) if str(elem).strip()]
    tokens = " ".join([material_name.lower(), material_type, color_map, " ".join(elem_types)])
    reasons: list[str] = []
    family = "lit_debris_impact"
    confidence = 0.45

    def any_token(*parts: str) -> list[str]:
        return [part for part in parts if part and part in tokens]

    matched = any_token("decal")
    if matched or "decal" in elem_types:
        family = "decal_surface_hit"
        reasons.extend([f"matched:{part}" for part in matched] or ["elem_type:decal"])
        confidence = 0.97
    else:
        matched = any_token("distort", "refract")
        if matched or int(usage.get("distortion_hints", 0)) > 0:
            family = "billboard_distortion"
            reasons.extend([f"matched:{part}" for part in matched] or ["usage:distortion_hint"])
            confidence = 0.95
        else:
            matched = any_token("fog", "smk", "smoke", "cloud", "puff", "whisp")
            if matched or "cloud" in elem_types or int(usage.get("cloud_hints", 0)) > 0:
                family = "billboard_soft_smoke"
                reasons.extend([f"matched:{part}" for part in matched] or ["elem_type:cloud"])
                confidence = 0.93
            else:
                matched = any_token("water", "bubble", "splash", "ripple")
                if matched:
                    family = "billboard_simple_alpha"
                    reasons.extend(f"matched:{part}" for part in matched)
                    confidence = 0.9
                else:
                    matched = any_token("blast", "ember", "lightning", "flame", "fire", "shockwave", "explo")
                    if matched:
                        family = "burst_emissive"
                        reasons.extend(f"matched:{part}" for part in matched)
                        confidence = 0.88
                    else:
                        matched = any_token("glow", "light", "phosphorous", "spark", "blink", "gel")
                        if matched or "emissive" in material_type:
                            family = "billboard_additive_glow"
                            reasons.extend([f"matched:{part}" for part in matched] or ["materialType:emissive"])
                            confidence = 0.85
                        else:
                            matched = any_token("debris", "gib", "metal", "dust")
                            if matched or "lit" in material_type:
                                family = "lit_debris_impact"
                                reasons.extend([f"matched:{part}" for part in matched] or ["materialType:lit"])
                                confidence = 0.78

    spec = FX_FAMILY_SPECS[family]
    template = Path(spec["template"])
    try:
        template_label = template.relative_to(ROOT).as_posix()
    except ValueError:
        template_label = str(template)

    enriched = dict(meta)
    enriched["family"] = family
    enriched["familyConfidence"] = round(confidence, 2)
    enriched["familyReasons"] = reasons or ["fallback:lit_debris_impact"]
    enriched["templatePath"] = template_label
    enriched["cameraRegion"] = spec["camera_region"]
    enriched["techniqueSet"] = spec["default_technique_set"]
    enriched["imagePolicy"] = spec["image_policy"]
    return enriched


def classify_all_fx_surfaces(
    material_meta: dict[str, dict[str, object]],
    usage: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    classified: dict[str, dict[str, object]] = {}
    for material_name, meta in material_meta.items():
        enriched = dict(meta)
        enriched["materialName"] = material_name
        enriched["usage"] = dict(usage.get(material_name, {"material_name": material_name, "fx_names": [], "elem_types": []}))
        classified[material_name] = classify_fx_surface(enriched)
    return classified


def apply_safe_full_servant_surface_overrides(
    material_meta: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    if client_ffprobe_enabled():
        return material_meta
    if not (USE_BO3_RAW_FX and clientscript_override_enabled() and SAFE_FULL_SERVANT_SURFACE_DOWNGRADE):
        return material_meta

    override_families = {"billboard_soft_smoke", "lit_debris_impact"}
    spec = FX_FAMILY_SPECS["billboard_additive_glow"]
    template = Path(spec["template"])
    try:
        template_label = template.relative_to(ROOT).as_posix()
    except ValueError:
        template_label = str(template)

    rewritten: dict[str, dict[str, object]] = {}
    for material_name, meta in material_meta.items():
        updated = dict(meta)
        family = str(updated.get("family", "")).strip()
        if family in override_families:
            reasons = list(updated.get("familyReasons", []))
            reasons.append("safe_full_servant_override:billboard_additive_glow")
            updated["family"] = "billboard_additive_glow"
            updated["familyReasons"] = reasons
            updated["templatePath"] = template_label
            updated["cameraRegion"] = spec["camera_region"]
            updated["techniqueSet"] = spec["default_technique_set"]
            updated["imagePolicy"] = spec["image_policy"]
        rewritten[material_name] = updated
    return rewritten


def write_fx_surface_classification_report(material_meta: dict[str, dict[str, object]]) -> None:
    rows = []
    for material_name in sorted(material_meta):
        meta = material_meta[material_name]
        usage = meta.get("usage", {})
        assert isinstance(usage, dict)
        rows.append(
            {
                "material": material_name,
                "family": meta.get("family", ""),
                "confidence": meta.get("familyConfidence", 0.0),
                "reasons": list(meta.get("familyReasons", [])),
                "materialType": meta.get("materialType", ""),
                "colorMap": meta.get("colorMap", ""),
                "usage": {
                    "elem_types": list(usage.get("elem_types", [])),
                    "fx_names": list(usage.get("fx_names", [])),
                    "usage_count": usage.get("usage_count", 0),
                },
            }
        )
    write_json(FX_SURFACE_CLASSIFICATION_REPORT, {"rows": rows})


def write_fx_surface_contract_report(material_meta: dict[str, dict[str, object]]) -> None:
    rows = []
    for material_name in sorted(material_meta):
        meta = material_meta[material_name]
        rows.append(
            {
                "material": material_name,
                "family": meta.get("family", ""),
                "template": meta.get("templatePath", ""),
                "cameraRegion": meta.get("cameraRegion", ""),
                "techniqueSet": meta.get("techniqueSet", None),
                "colorMap": meta.get("colorMap", ""),
                "materialType": meta.get("materialType", ""),
                "imagePolicy": meta.get("imagePolicy", ""),
            }
        )
    write_json(FX_SURFACE_CONTRACT_REPORT, {"rows": rows})


def write_fx_surface_image_policy_report(material_meta: dict[str, dict[str, object]]) -> None:
    image_rows: dict[str, dict[str, object]] = {}
    for material_name, meta in material_meta.items():
        image_name = str(meta.get("colorMap", "")).strip()
        if not image_name:
            continue
        if image_name in image_rows:
            continue
        image_rows[image_name] = {
            "image": image_name,
            "family": meta.get("family", ""),
            "policy": meta.get("imagePolicy", ""),
            "normalizeHeader": meta.get("imagePolicy", "") == "normalize_bc3_header_if_present",
            "reasons": list(meta.get("familyReasons", [])),
            "material": material_name,
        }
    write_json(FX_SURFACE_IMAGE_POLICY_REPORT, {"rows": [image_rows[name] for name in sorted(image_rows)]})


def select_images_requiring_header_fix(
    material_meta: dict[str, dict[str, object]],
    staged_images: list[str],
) -> list[str]:
    normalize_images = {
        str(meta.get("colorMap", "")).strip()
        for meta in material_meta.values()
        if str(meta.get("imagePolicy", "")).strip() == "normalize_bc3_header_if_present"
        and str(meta.get("colorMap", "")).strip()
    }
    return sorted(image_name for image_name in staged_images if image_name in normalize_images)


def resolve_hb21_file_path(base_image: str) -> tuple[Path, str]:
    normalized = base_image.replace("\\", "/").strip().lstrip("/")
    direct = BO3_FX_LIBRARY_ROOT / Path(normalized)
    candidates = [direct]

    path_obj = Path(normalized)
    override = HB21_SOURCE_IMAGE_OVERRIDES.get(path_obj.stem)
    if override and override.exists():
        if override.is_relative_to(BO3_FX_LIBRARY_ROOT):
            return override, override.relative_to(BO3_FX_LIBRARY_ROOT).as_posix()
        return override, f"external_fx/{override.name}"

    if path_obj.parts[:2] == ("texture_assets", "gfx"):
        tail = Path(*path_obj.parts[2:])
        candidates.append(BO3_FX_LIBRARY_ROOT / "texture_assets" / "black_ops_3" / "gfx" / tail)

    for candidate in candidates:
        if candidate.exists():
            return candidate, candidate.relative_to(BO3_FX_LIBRARY_ROOT).as_posix()

    stem = path_obj.stem
    search_roots = [
        BO3_FX_LIBRARY_ROOT / "texture_assets",
        BO3_FX_LIBRARY_ROOT / "source_data",
    ]
    for search_root in search_roots:
        if not search_root.exists():
            continue
        matches = sorted(search_root.rglob(f"{stem}*"))
        if matches:
            files = [match for match in matches if match.is_file()]
            if not files:
                continue
            match = sorted(files, key=lambda item: (len(item.name), item.name.lower()))[0]
            return match, match.relative_to(BO3_FX_LIBRARY_ROOT).as_posix()

    raise FileNotFoundError(f"Missing HB21 source file for ref '{base_image}'")


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


def write_iwi_from_dds(src_dds: Path, dst_iwi: Path) -> None:
    width, height, mips, iwi_format = read_dds(src_dds)
    create_iwi(width, height, mips, iwi_format, dst_iwi)


def write_iwi_from_image(img: Image.Image, dst_iwi: Path, *, force_format: int = IWI_FORMAT_DXT5) -> None:
    if not TEXCONV.exists():
        raise FileNotFoundError(f"Missing texconv: {TEXCONV}")

    with tempfile.TemporaryDirectory(prefix="idg_tex_raw_") as tmp:
        tmp_root = Path(tmp)
        png_path = tmp_root / f"{dst_iwi.stem}.png"
        img.save(png_path)
        result = subprocess.run(
            [str(TEXCONV), "-f", "BC3_UNORM", "-y", "-m", "0", "-o", str(tmp_root), str(png_path)],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"texconv failed for {dst_iwi}:\n{result.stdout}\n{result.stderr}")
        dds_path = tmp_root / f"{dst_iwi.stem}.dds"
        if not dds_path.exists():
            raise FileNotFoundError(f"texconv did not produce DDS: {dds_path}")
        width, height, mips, iwi_format = read_dds(dds_path)
        create_iwi(width, height, mips, force_format if force_format is not None else iwi_format, dst_iwi)


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


def build_phosphorous_variant_image(img: Image.Image, mode: str) -> Image.Image:
    rgba = img.convert("RGBA")
    rgb = Image.merge("RGB", rgba.split()[:3])

    if mode == "phosphorous_soft":
        rgb = ImageEnhance.Color(rgb).enhance(1.10)
        rgb = ImageEnhance.Contrast(rgb).enhance(1.12)
        rgb = ImageEnhance.Brightness(rgb).enhance(1.18)
        rgb = rgb.filter(ImageFilter.GaussianBlur(radius=1.5))
        luma = rgb.convert("L").filter(ImageFilter.GaussianBlur(radius=2.8))
        alpha = luma.point(lambda v: 0 if v < 10 else min(255, int(v * 1.45)))
        return Image.merge("RGBA", (*rgb.split(), alpha))

    if mode == "phosphorous_bloom":
        rgb = ImageEnhance.Color(rgb).enhance(1.18)
        rgb = ImageEnhance.Contrast(rgb).enhance(1.06)
        rgb = ImageEnhance.Brightness(rgb).enhance(1.28)
        rgb = rgb.filter(ImageFilter.GaussianBlur(radius=2.3))
        luma = rgb.convert("L")
        alpha = luma.filter(ImageFilter.GaussianBlur(radius=4.8)).point(
            lambda v: 0 if v < 8 else min(255, int(v * 1.85))
        )
        return Image.merge("RGBA", (*rgb.split(), alpha))

    if mode == "phosphorous_hot":
        rgb = ImageEnhance.Color(rgb).enhance(1.22)
        rgb = ImageEnhance.Contrast(rgb).enhance(1.10)
        rgb = ImageEnhance.Brightness(rgb).enhance(1.34)
        rgb = rgb.filter(ImageFilter.GaussianBlur(radius=1.75))
        base_alpha = rgba.getchannel("A")
        luma_alpha = rgb.convert("L").filter(ImageFilter.GaussianBlur(radius=3.1)).point(
            lambda v: 0 if v < 6 else min(255, int(v * 2.05))
        )
        alpha = ImageChops.lighter(base_alpha, luma_alpha)
        alpha = alpha.point(lambda v: 0 if v < 8 else min(255, int(v * 1.20)))
        return Image.merge("RGBA", (*rgb.split(), alpha))

    if mode == "phosphorous_mask":
        mask_rgba = build_emissive_mask_image(
            rgba,
            brightness=1.20,
            contrast=1.20,
            saturation=1.0,
            red_scale=1.25,
            green_scale=1.05,
            blue_scale=0.82,
        )
        rgb_mask = Image.merge("RGB", mask_rgba.split()[:3]).filter(ImageFilter.GaussianBlur(radius=2.2))
        alpha = mask_rgba.getchannel("A").filter(ImageFilter.GaussianBlur(radius=3.6)).point(
            lambda v: 0 if v < 8 else min(255, int(v * 1.60))
        )
        return Image.merge("RGBA", (*rgb_mask.split(), alpha))

    raise RuntimeError(f"Unsupported phosphorous image process mode: {mode}")


def soften_spec_image(img: Image.Image, rgb_scale: float, alpha_scale: float) -> Image.Image:
    gray = img.convert("L")
    rgb = gray.point(lambda v: min(255, int(v * rgb_scale)))
    alpha = gray.point(lambda v: min(255, int(v * alpha_scale)))
    return Image.merge("RGBA", (rgb, rgb, rgb, alpha))


def write_processed_iwi_from_dds(src_dds: Path, dst_iwi: Path, mode: str, image_name: str) -> None:
    img = Image.open(src_dds)
    if mode in {"phosphorous_soft", "phosphorous_bloom", "phosphorous_hot", "phosphorous_mask"}:
        processed = build_phosphorous_variant_image(img, mode)
        PHOSPHOROUS_VARIANT_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
        processed.save(PHOSPHOROUS_VARIANT_PREVIEW_DIR / f"{image_name}.png")
        write_iwi_from_image(processed, dst_iwi)
        return
    raise RuntimeError(f"Unsupported DDS image process mode: {mode}")


def write_processed_iwi_from_png(src_png: Path, dst_iwi: Path, mode: str, image_name: str) -> None:
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
    write_iwi_from_image(processed, dst_iwi)


def write_manual_idg_iwi(src_png: Path, dst_iwi: Path, image_name: str) -> None:
    suffix = image_name.rsplit("_", 1)[-1].lower()
    if suffix == "c":
        write_processed_iwi_from_png(src_png, dst_iwi, "diffuse", image_name)
        return
    if suffix == "e":
        write_processed_iwi_from_png(src_png, dst_iwi, "emissive_color", image_name)
        return
    if suffix in {"g", "s"}:
        write_processed_iwi_from_png(src_png, dst_iwi, "spec_soft", image_name)
        return

    img = Image.open(src_png).convert("RGBA")
    write_iwi_from_image(img, dst_iwi)


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
    seen_texture_names: set[str] = set()
    for entry in payload.get("textures", []):
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        if not name:
            continue
        patched = dict(entry)
        if name in textures_by_name:
            patched["image"] = textures_by_name[name]
        seen_texture_names.add(name)
        textures.append(patched)
    for name, image_name in textures_by_name.items():
        if name in seen_texture_names:
            continue
        textures.append(
            {
                "image": image_name,
                "isMatureContent": False,
                "name": name,
                "samplerState": {
                    "clampU": True,
                    "clampV": True,
                    "clampW": True,
                    "filter": "linear",
                    "mipMap": "nearest",
                },
                "semantic": name if name.endswith("Map") else "colorMap",
            }
        )
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


def normalize_t6_iwi_headers(image_names: list[str]) -> None:
    for image_name in image_names:
        path = IMAGES_DIR / f"{image_name}.iwi"
        if not path.exists():
            continue
        data = bytearray(path.read_bytes())
        if len(data) < IWI_HEADER_SIZE:
            continue
        if data[0:3] != IWI_MAGIC or data[3] != IWI_VERSION:
            continue
        # The older working T6 texture pipeline in this repo expects 0x0E for
        # BC3/DXT5 payloads. ImageConverter is currently emitting 0x0D for these
        # custom IDG images, which matches the black-texture regression.
        if data[4] == 0x0D:
            data[4] = 0x0E
            path.write_bytes(data)


def build_safe_bo2_idg_materials(material_names: list[str]) -> None:
    if USE_STOCK_IDG_IMAGES:
        stock_slots = {
            "colorMap": "~-gmtl_t6_wpn_zmb_mg08_col",
            "normalMap": "mtl_t6_wpn_zmb_mg08_nml",
            "specularMap": "~~-gmtl_t6_wpn_zmb_mg08_spc-r~1143a0cb",
        }
        for material_name in material_names:
            dst = MATERIALS_DIR / f"{material_name}.json"
            payload = clone_material_template(
                IDG_LIT_TEMPLATE,
                material_name,
                stock_slots,
                technique_set=None,
                camera_region="litOpaque",
                double_sided=True,
            )
            dst.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return

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


def build_bo3_fx_surface_bundle(material_names: list[str]) -> tuple[Path, dict[str, dict[str, object]]]:
    if FX_SURFACE_BUNDLE_ROOT.exists():
        shutil.rmtree(FX_SURFACE_BUNDLE_ROOT)
    staged_root = FX_SURFACE_BUNDLE_ROOT / "staged"
    manifest_dir = FX_SURFACE_BUNDLE_ROOT / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    index = build_hb21_gdt_index()
    copied_files: list[dict[str, str]] = []
    material_entries: list[dict[str, object]] = []
    image_entries: list[dict[str, object]] = []
    image_names: list[str] = []
    material_meta: dict[str, dict[str, object]] = {}
    image_meta_by_name: dict[str, dict[str, object]] = {}

    for material_name in material_names:
        if material_name == "gfx_debug_missing_fx":
            material_entries.append(
                {
                    "name": material_name,
                    "gdf": "material.gdf",
                    "props": {"colorMap": "fxt_debris_clump"},
                }
            )
            material_meta[material_name] = {
                "materialName": material_name,
                "materialType": "effect_lit_blend",
                "colorMap": "fxt_debris_clump",
                "sourceGdt": "material.gdf",
                "hb21MaterialProps": {"colorMap": "fxt_debris_clump"},
            }
            if "fxt_debris_clump" not in image_names:
                image_names.append("fxt_debris_clump")
            continue
        resolved = resolve_hb21_entry(material_name, index)
        if str(resolved.get("gdf", "")).lower() != "material.gdf":
            raise RuntimeError(f"HB21 FX material '{material_name}' did not resolve to material.gdf")
        props = resolved.get("props", {})
        assert isinstance(props, dict)
        color_map = str(props.get("colorMap", "")).strip()
        if not color_map or color_map.startswith("$"):
            raise RuntimeError(f"HB21 FX material '{material_name}' has no usable colorMap")
        material_entries.append(
            {
                "name": material_name,
                "gdf": "material.gdf",
                "props": {"colorMap": color_map},
            }
        )
        material_meta[material_name] = {
            "materialName": material_name,
            "materialType": str(props.get("materialType", "")).strip(),
            "colorMap": color_map,
            "sourceGdt": str(resolved.get("source_gdt", "")),
            "hb21MaterialProps": {str(key): str(value) for key, value in props.items()},
        }
        if color_map not in image_names:
            image_names.append(color_map)

    for image_name in image_names:
        resolved = resolve_hb21_entry(image_name, index)
        if str(resolved.get("gdf", "")).lower() != "image.gdf":
            raise RuntimeError(f"HB21 FX image '{image_name}' did not resolve to image.gdf")
        props = resolved.get("props", {})
        assert isinstance(props, dict)
        base_image = str(props.get("baseImage", "")).strip()
        if not base_image:
            raise RuntimeError(f"HB21 FX image '{image_name}' missing baseImage")
        src, relative = resolve_hb21_file_path(base_image)
        dst = staged_root / Path(relative)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied_files.append({"relative": relative, "destination": str(dst)})
        image_entries.append(
            {
                "name": image_name,
                "gdf": "image.gdf",
                "props": {
                    "baseImage": relative,
                    "clampU": str(props.get("clampU", "0")),
                    "clampV": str(props.get("clampV", "0")),
                    "matureContent": str(props.get("matureContent", "0")),
                    "noMipMaps": str(props.get("noMipMaps", "0")),
                    "semantic": "colorMap",
                },
            }
        )
        image_meta_by_name[image_name] = {
            "hb21ImageProps": {str(key): str(value) for key, value in props.items()},
            "baseImageRelative": relative,
            "sourceGdt": str(resolved.get("source_gdt", "")),
        }

    for material_name, meta in material_meta.items():
        color_map = str(meta.get("colorMap", "")).strip()
        image_meta = image_meta_by_name.get(color_map, {})
        meta["hb21ImageProps"] = dict(image_meta.get("hb21ImageProps", {}))
        meta["baseImageRelative"] = str(image_meta.get("baseImageRelative", ""))

    write_json(manifest_dir / "materials.json", material_entries)
    write_json(manifest_dir / "images.json", image_entries)
    write_json(
        FX_SURFACE_BLENDER_REPORT,
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
        FX_SURFACE_BUNDLE_REPORT,
        {
            "output_root": str(FX_SURFACE_BUNDLE_ROOT),
            "copied_files": copied_files,
            "counts": {
                "material_entries": len(material_entries),
                "image_entries": len(image_entries),
                "copied_unique_files": len(copied_files),
                "missing_refs": 0,
            },
        },
    )
    return FX_SURFACE_BUNDLE_REPORT, material_meta


def choose_fx_template(material_meta: dict[str, object]) -> Path:
    family = str(material_meta.get("family", "")).strip()
    spec = FX_FAMILY_SPECS.get(family)
    if spec is not None:
        return Path(spec["template"])
    material_type = str(material_meta.get("materialType", "")).strip().lower()
    if "distort" in material_type:
        return FX_DISTORT_TEMPLATE
    if "cloud" in material_type:
        return FX_CLOUD_TEMPLATE
    if "emissive" in material_type:
        return FX_EMISSIVE_TEMPLATE
    return FX_LIT_TEMPLATE


def build_safe_bo2_fx_materials(material_meta: dict[str, dict[str, object]]) -> None:
    for material_name, meta in material_meta.items():
        color_map = str(meta.get("colorMap", "")).strip()
        if not color_map:
            continue
        template = choose_fx_template(meta)
        payload = clone_material_template(
            template,
            material_name,
            {"colorMap": color_map},
            technique_set=meta.get("techniqueSet", None),
            camera_region=str(meta.get("cameraRegion", "emissiveFx")),
        )
        dst = MATERIALS_DIR / f"{material_name}.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def stage_stock_fx_debug_material() -> None:
    if active_client_ffprobe_asset() != "zombie/fx_ffprobe_debug_orb_stock":
        return
    src = FULL_RUNTIME_SOURCE_ROOT / "materials" / "gfx_fxt_light_glow_square_gr.json"
    if not src.exists():
        raise FileNotFoundError(f"Missing stock FX debug material template: {src}")
    payload = json.loads(src.read_text(encoding="utf-8"))
    payload["debugName"] = "bo3_rev_debug_stock_glow"
    dst = MATERIALS_DIR / "bo3_rev_debug_stock_glow.json"
    dst.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    # Keep the stock glow surface available for the dedicated BO3 FX load lane.
    # Earlier builds deleted this loose IWI override unconditionally, which made
    # the donor stock material impossible to resolve in the isolated FF build.
    if not using_dedicated_bo3_fx_load_lane():
        stale_override = IMAGES_DIR / "fxt_light_glow_square.iwi"
        if stale_override.exists():
            stale_override.unlink()


def stage_stock_fmt0d_debug_material() -> None:
    if active_client_ffprobe_asset() != "zombie/fx_ffprobe_debug_orb_stock_fmt0d":
        return
    src = FULL_RUNTIME_SOURCE_ROOT / "materials" / "gfx_fxt_light_glow_square_gr.json"
    if not src.exists():
        raise FileNotFoundError(f"Missing stock FX debug material template: {src}")
    if not STOCK_FMT0D_IMAGE_IWI.exists():
        raise FileNotFoundError(f"Missing stock fmt0d image source: {STOCK_FMT0D_IMAGE_IWI}")
    payload = json.loads(src.read_text(encoding="utf-8"))
    payload["debugName"] = STOCK_FMT0D_DEBUG_MATERIAL_NAME
    if payload.get("textures"):
        payload["textures"][0]["image"] = STOCK_FMT0D_IMAGE_NAME
    dst = MATERIALS_DIR / f"{STOCK_FMT0D_DEBUG_MATERIAL_NAME}.json"
    dst.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(STOCK_FMT0D_IMAGE_IWI, IMAGES_DIR / STOCK_FMT0D_IMAGE_IWI.name)


def stage_stock_fulldds_debug_material() -> None:
    if active_client_ffprobe_asset() != "zombie/fx_ffprobe_debug_orb_stock_fulldds":
        return
    src = FULL_RUNTIME_SOURCE_ROOT / "materials" / "gfx_fxt_light_glow_square_gr.json"
    if not src.exists():
        raise FileNotFoundError(f"Missing stock FX debug material template: {src}")
    if not STOCK_FULLDDS_IMAGE_DDS.exists():
        raise FileNotFoundError(f"Missing stock full-DDS image source: {STOCK_FULLDDS_IMAGE_DDS}")
    payload = json.loads(src.read_text(encoding="utf-8"))
    payload["debugName"] = STOCK_FULLDDS_DEBUG_MATERIAL_NAME
    if payload.get("textures"):
        payload["textures"][0]["image"] = STOCK_FULLDDS_IMAGE_NAME
    dst = MATERIALS_DIR / f"{STOCK_FULLDDS_DEBUG_MATERIAL_NAME}.json"
    dst.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_iwi_from_dds(STOCK_FULLDDS_IMAGE_DDS, IMAGES_DIR / f"{STOCK_FULLDDS_IMAGE_NAME}.iwi")


def stage_phosphorous_debug_material_variants() -> None:
    global STAGED_IMAGE_NAMES, STAGED_FX_IMAGE_NAMES
    active_asset = active_client_ffprobe_asset()
    active_spec = phosphorous_variant_spec_for_asset(active_asset)
    if active_spec is None:
        return
    src = FULL_RUNTIME_SOURCE_ROOT / "materials" / "gfx_fxt_light_glow_square_gr.json"
    if not src.exists():
        raise FileNotFoundError(f"Missing phosphorous-native material template: {src}")
    if not PHOSPHOROUS_NATIVE_IMAGE_DDS.exists():
        raise FileNotFoundError(f"Missing phosphorous-native DDS source: {PHOSPHOROUS_NATIVE_IMAGE_DDS}")
    template_payload = json.loads(src.read_text(encoding="utf-8"))
    spec = active_spec
    payload = json.loads(json.dumps(template_payload))
    payload["debugName"] = spec["material"]
    if payload.get("textures"):
        payload["textures"][0]["image"] = spec["image"]
    dst = MATERIALS_DIR / f'{spec["material"]}.json'
    dst.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    dst_iwi = IMAGES_DIR / f'{spec["image"]}.iwi'
    if spec["mode"] == "dds_native":
        write_iwi_from_dds(PHOSPHOROUS_NATIVE_IMAGE_DDS, dst_iwi)
    else:
        write_processed_iwi_from_dds(PHOSPHOROUS_NATIVE_IMAGE_DDS, dst_iwi, spec["mode"], spec["image"])
    if spec["image"] not in STAGED_FX_IMAGE_NAMES:
        STAGED_FX_IMAGE_NAMES.append(spec["image"])
    if spec["image"] not in STAGED_IMAGE_NAMES:
        STAGED_IMAGE_NAMES.append(spec["image"])


def stage_client_probe_runtime_dependencies() -> None:
    global STAGED_IMAGE_NAMES
    if not client_ffprobe_enabled():
        return

    if not FX_GLOW_TEMPLATE.exists():
        raise FileNotFoundError(f"Missing stock glow material template: {FX_GLOW_TEMPLATE}")
    if not FX_GLOW_IMAGE_DDS.exists():
        raise FileNotFoundError(f"Missing stock glow DDS source: {FX_GLOW_IMAGE_DDS}")

    payload = clone_material_template(
        FX_GLOW_TEMPLATE,
        TRANSIT_OVERLAY_MATERIAL_NAME,
        {"colorMap": TRANSIT_OVERLAY_IMAGE_NAME},
        technique_set="effect_26z423jf",
        camera_region="emissiveFx",
    )
    dst_material = MATERIALS_DIR / f"{TRANSIT_OVERLAY_MATERIAL_NAME}.json"
    dst_material.parent.mkdir(parents=True, exist_ok=True)
    dst_material.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    dst_image = IMAGES_DIR / f"{TRANSIT_OVERLAY_IMAGE_NAME}.iwi"
    if not dst_image.exists():
        write_iwi_from_dds(FX_GLOW_IMAGE_DDS, dst_image)

    if TRANSIT_OVERLAY_IMAGE_NAME not in STAGED_IMAGE_NAMES:
        STAGED_IMAGE_NAMES.append(TRANSIT_OVERLAY_IMAGE_NAME)


def stage_fx_runtime_support_images() -> None:
    for image_name, candidates in FX_RUNTIME_SUPPORT_IMAGE_CANDIDATES.items():
        dst = IMAGES_DIR / f"{image_name}.iwi"
        if dst.exists():
            if image_name not in STAGED_FX_IMAGE_NAMES:
                STAGED_FX_IMAGE_NAMES.append(image_name)
            if image_name not in STAGED_IMAGE_NAMES:
                STAGED_IMAGE_NAMES.append(image_name)
            continue

        src = next((candidate for candidate in candidates if candidate.exists()), None)
        if src is None:
            raise FileNotFoundError(
                f"Missing runtime support image source for {image_name}. Tried: "
                + ", ".join(str(candidate) for candidate in candidates)
            )

        if image_name == "$identitynormalmap":
            # The stock DDS is a tiny degenerate identity normal. Repacking it
            # directly produced an invalid 68-byte IWI, so generate a clean
            # neutral normal-map texture explicitly.
            neutral = Image.new("RGBA", (4, 4), (128, 128, 255, 255))
            write_iwi_from_image(neutral, dst, force_format=IWI_FORMAT_DXT5)
        elif src.suffix.lower() == ".iwi":
            shutil.copy2(src, dst)
        elif src.suffix.lower() == ".dds":
            write_iwi_from_dds(src, dst)
        else:
            raise RuntimeError(f"Unsupported runtime support image source for {image_name}: {src}")

        if image_name not in STAGED_FX_IMAGE_NAMES:
            STAGED_FX_IMAGE_NAMES.append(image_name)
        if image_name not in STAGED_IMAGE_NAMES:
            STAGED_IMAGE_NAMES.append(image_name)


def fx_passthrough_material_roots() -> list[Path]:
    return [
        WORK,
        ROOT / "_build" / "stock_iwi_dump",
        FULL_RUNTIME_SOURCE_ROOT,
        ZONE_DUMP_SOURCE_ROOT,
        ROOT / "zone_dump",
        ROOT / "zone_dump" / "zone_raw" / "zm_tomb",
    ]


def fx_passthrough_image_roots() -> list[Path]:
    return [
        WORK,
        ROOT / "_build" / "stock_iwi_dump",
        FULL_RUNTIME_SOURCE_ROOT,
        ZONE_DUMP_SOURCE_ROOT,
        ROOT / "zone_dump",
        ROOT / "zone_dump" / "zone_raw" / "zm_tomb",
    ]


def find_material_json(material_name: str, roots: list[Path]) -> Path | None:
    rel = Path("materials") / f"{material_name}.json"
    for root in roots:
        candidate = root / rel
        if candidate.exists():
            return candidate
    return None


def find_image_iwi(image_name: str, roots: list[Path]) -> Path | None:
    rel = Path("images") / f"{image_name}.iwi"
    for root in roots:
        candidate = root / rel
        if candidate.exists():
            return candidate
    return None


def stage_passthrough_fx_material_images(material_names: list[str]) -> None:
    material_roots = fx_passthrough_material_roots()
    image_roots = fx_passthrough_image_roots()
    for material_name in material_names:
        material_path = find_material_json(material_name, material_roots)
        if material_path is None:
            continue
        payload = json.loads(material_path.read_text(encoding="utf-8"))
        for texture in payload.get("textures", []):
            image_name = str(texture.get("image", "")).strip()
            if not image_name:
                continue
            dst = IMAGES_DIR / f"{image_name}.iwi"
            if not dst.exists():
                src_iwi = find_image_iwi(image_name, image_roots)
                if src_iwi is not None:
                    shutil.copy2(src_iwi, dst)
                else:
                    dds_candidates = [
                        ROOT / "zone_dump" / "images" / f"{image_name}.dds",
                        ZONE_DUMP_SOURCE_ROOT / "images" / f"{image_name}.dds",
                        FULL_RUNTIME_SOURCE_ROOT / "images" / f"{image_name}.dds",
                    ]
                    src_dds = next((candidate for candidate in dds_candidates if candidate.exists()), None)
                    if src_dds is not None:
                        write_iwi_from_dds(src_dds, dst)
            if dst.exists():
                if image_name not in STAGED_FX_IMAGE_NAMES:
                    STAGED_FX_IMAGE_NAMES.append(image_name)
                if image_name not in STAGED_IMAGE_NAMES:
                    STAGED_IMAGE_NAMES.append(image_name)


def stage_bo3_servant_fx_surfaces() -> None:
    global STAGED_IMAGE_NAMES, STAGED_FX_IMAGE_NAMES, STAGED_FX_MATERIAL_NAMES, BO3_FX_SURFACE_META

    STAGED_FX_IMAGE_NAMES = []
    STAGED_FX_MATERIAL_NAMES = []
    BO3_FX_SURFACE_META = {}
    if uses_t5_gersh_assets() or not USE_BO3_RAW_FX:
        return

    stage_stock_fx_debug_material()
    stage_stock_fmt0d_debug_material()
    stage_stock_fulldds_debug_material()
    stage_phosphorous_debug_material_variants()
    material_names = load_bo3_servant_fx_material_names()
    translated_material_names: list[str] = []
    passthrough_material_names: list[str] = []
    passthrough_roots = fx_passthrough_material_roots()
    for material_name in material_names:
        if material_name in ("bo3_rev_debug_stock_glow", STOCK_FMT0D_DEBUG_MATERIAL_NAME):
            passthrough_material_names.append(material_name)
            continue
        if (MATERIALS_DIR / f"{material_name}.json").exists():
            passthrough_material_names.append(material_name)
            continue
        if find_material_json(material_name, passthrough_roots) is not None:
            passthrough_material_names.append(material_name)
            continue
        translated_material_names.append(material_name)
    usage = scan_bo3_servant_fx_surface_usage()
    bundle_report, material_meta = build_bo3_fx_surface_bundle(translated_material_names)
    write_json(FX_CONTRACT_CATALOG_REPORT, fx_contract_catalog_payload())
    material_meta = classify_all_fx_surfaces(material_meta, usage)
    material_meta = apply_safe_full_servant_surface_overrides(material_meta)
    BO3_FX_SURFACE_META = dict(material_meta)
    write_fx_surface_classification_report(material_meta)
    write_fx_surface_contract_report(material_meta)
    write_fx_surface_image_policy_report(material_meta)

    if FX_SURFACE_PROJECT_ROOT.exists():
        shutil.rmtree(FX_SURFACE_PROJECT_ROOT)

    run_checked(
        [
            sys.executable,
            str(MATERIAL_TRANSLATOR),
            "--project-root",
            str(FX_SURFACE_PROJECT_ROOT),
            "--project-name",
            FX_SURFACE_PROJECT_NAME,
            "--blender-report",
            str(FX_SURFACE_BLENDER_REPORT),
            "--default-techset",
            "effect_z0z25860",
            "--lit-techset",
            "effect_z0z25860",
            "--unlit-techset",
            "effect_z0z25860",
            "--bundle-report",
            str(bundle_report),
            "--contract-report",
            str(FX_SURFACE_CONTRACT_REPORT),
            "--stage-images",
            "--stage-images-as-iwi",
            "--report",
            str(FX_SURFACE_TRANSLATION_REPORT),
        ],
        cwd=ROOT,
    )

    translation = json.loads(FX_SURFACE_TRANSLATION_REPORT.read_text(encoding="utf-8"))
    translated_root = FX_SURFACE_PROJECT_ROOT / "zone_raw" / FX_SURFACE_PROJECT_NAME
    translated_images = translated_root / "images"
    staged_images = sorted(
        {
            str(item.get("image", "")).strip()
            for item in translation.get("staged_images", [])
            if str(item.get("image", "")).strip()
        }
    )
    for image_name in staged_images:
        src = translated_images / f"{image_name}.iwi"
        if not src.exists():
            raise FileNotFoundError(f"Translated FX image missing: {src}")
        shutil.copy2(src, IMAGES_DIR / src.name)
        STAGED_FX_IMAGE_NAMES.append(image_name)
        if image_name not in STAGED_IMAGE_NAMES:
            STAGED_IMAGE_NAMES.append(image_name)

    # Apply the header fix only to families that still rely on the BC3 compatibility path.
    header_fix_images = select_images_requiring_header_fix(material_meta, staged_images)
    if header_fix_images:
        normalize_t6_iwi_headers(header_fix_images)

    build_safe_bo2_fx_materials(material_meta)
    stage_passthrough_fx_material_images(passthrough_material_names)
    stage_fx_runtime_support_images()
    STAGED_FX_IMAGE_NAMES = sorted(set(STAGED_FX_IMAGE_NAMES))
    STAGED_FX_MATERIAL_NAMES = sorted(set(material_meta) | set(passthrough_material_names))
    print(
        f"Staged BO3 Servant FX surfaces: translated_materials={len(translated_material_names)} "
        f"passthrough_materials={len(passthrough_material_names)} images={len(staged_images)}"
    )


def stage_t5_gersh_materials() -> None:
    material_dir = MATERIALS_DIR / "mc"
    material_dir.mkdir(parents=True, exist_ok=True)
    payload = clone_material_template(
        T5_GERSH_MATERIAL_TEMPLATE,
        T5_GERSH_MATERIAL_LINE,
        {},
        technique_set=None,
        camera_region="litOpaque",
        double_sided=True,
    )
    T5_GERSH_MATERIAL_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sync_zone_raw_mirror() -> None:
    if ZONE_RAW_ROOT.exists():
        shutil.rmtree(ZONE_RAW_ROOT)
    ZONE_RAW_ROOT.mkdir(parents=True, exist_ok=True)

    mirror_dirs = {
        "fx": FX_DIR,
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


def stage_bo3_servant_fx() -> None:
    global STAGED_FX_NAMES, RAW_FX_COMPAT_REPORT, RAW_FX_STRUCTURE_REPORT
    STAGED_FX_NAMES = []
    RAW_FX_COMPAT_REPORT = {}
    RAW_FX_STRUCTURE_REPORT = {}

    if uses_t5_gersh_assets() or not USE_BO3_RAW_FX:
        return

    zombie_fx_root = BO3_FX_RAW_ROOT / "zombie"
    if not zombie_fx_root.exists():
        raise FileNotFoundError(f"Missing BO3 FX raw root: {zombie_fx_root}")

    dst_root = FX_DIR / "zombie"
    if dst_root.exists():
        shutil.rmtree(dst_root)
    dst_root.mkdir(parents=True, exist_ok=True)
    write_debug_raw_fx()

    probe_fx_name = client_ffprobe_bo3_fx_asset()
    if client_ffprobe_uses_custom_debug_orb() and probe_fx_name:
        STAGED_FX_NAMES = [probe_fx_name]
        print(f"Staged BO3/custom probe FX defs: {len(STAGED_FX_NAMES)}")
        return

    RAW_FX_COMPAT_REPORT = validate_bo3_servant_fx_graph()

    for fx_name in bo3_servant_raw_fx_staged_names():
        if fx_name in (
            "zombie/fx_bo3_rev_debug_orb",
            "zombie/fx_bo3_rev_debug_orb_os",
            "zombie/fx_bo3_rev_debug_orb_stock",
            "zombie/fx_bo3_rev_debug_orb_stock_os",
            "zombie/fx_bo3_rev_probe_phosphorous_i1024_os",
            "zombie/fx_bo3_rev_probe_shockwave_i2048_os",
            "zombie/fx_bo3_rev_contract_test",
            "zombie/fx_bo3_rev_hole_md_stock_probe",
            "zombie/fx_bo3_rev_hole_md_custom_probe",
        ):
            continue
        rel = fx_name.split("/", 1)[1] + ".efx"
        src = zombie_fx_root / rel
        if not src.exists():
            raise FileNotFoundError(f"Missing BO3 FX raw file: {src}")
        dst_path = dst_root / src.name
        shutil.copy2(src, dst_path)
        rewrite_bo3_servant_raw_fx(dst_path)

    hole_md_path = dst_root / "fx_idgun_hole_md_zod_zmb.efx"
    if hole_md_path.exists():
        _raw_fx_clone_hole_md_probe(
            hole_md_path,
            dst_root / "fx_bo3_rev_hole_md_stock_probe.efx",
            "bo3_rev_hole_md_stock_probe",
            "gfx_fxt_light_glow_square_gr",
        )
        _raw_fx_clone_hole_md_probe(
            hole_md_path,
            dst_root / "fx_bo3_rev_hole_md_custom_probe.efx",
            "bo3_rev_hole_md_custom_probe",
            "gfx_light_phosphorous_em",
        )

    # The runtime clientscript loads several subordinate Servant layers directly
    # (the hole_xsm/sm/md/lg/xl family), and some root FX also reference staged
    # child effects such as ground_displace. Keep the linked manifest aligned
    # with the full staged set instead of only the root entry points.
    STAGED_FX_NAMES = list(bo3_servant_raw_fx_staged_names())
    if probe_fx_name and probe_fx_name not in STAGED_FX_NAMES:
        STAGED_FX_NAMES.append(probe_fx_name)
    if RAW_FX_STRUCTURE_REPORT:
        write_json(FX_STRUCTURE_REWRITE_REPORT, RAW_FX_STRUCTURE_REPORT)
    print(f"Staged BO3 Servant FX defs: {len(STAGED_FX_NAMES)}")


def verify_servant_clientscript_fx_manifest_alignment() -> None:
    if not clientscript_override_enabled():
        return
    if not USE_BO3_RAW_FX:
        return
    if not using_dedicated_bo3_fx_load_lane():
        return
    if SERVANT_FX_SCOPE != "full":
        return
    if not SERVANT_CLIENTSCRIPT_OUTPUT.exists():
        raise FileNotFoundError(
            "Missing rendered servant clientscript output for FX manifest audit: "
            f"{SERVANT_CLIENTSCRIPT_OUTPUT}"
        )

    script_text = SERVANT_CLIENTSCRIPT_OUTPUT.read_text(encoding="utf-8", errors="replace")
    referenced_fx = {
        match.group(1).strip()
        for match in re.finditer(
            r'(?:\w+_)?loadfx(?:_safe)?\(\s*"([^"]+)"',
            script_text,
            flags=re.IGNORECASE,
        )
    }
    referenced_bo3_fx = sorted(name for name in referenced_fx if name.startswith("zombie/"))
    staged_bo3_fx = set(STAGED_FX_NAMES)
    probe_fx_name = client_ffprobe_bo3_fx_asset()
    if probe_fx_name:
        staged_bo3_fx.add(probe_fx_name)
    missing_bo3_fx = [name for name in referenced_bo3_fx if name not in staged_bo3_fx]
    if missing_bo3_fx:
        raise RuntimeError(
            "Servant clientscript references BO3 FX that are not present in the dedicated "
            "BO3 FX load lane.\n"
            f"Script: {SERVANT_CLIENTSCRIPT_OUTPUT}\n"
            f"Missing FX: {', '.join(missing_bo3_fx)}"
        )


def verify_safe_full_servant_surface_contract() -> None:
    if client_ffprobe_enabled():
        return
    if not (USE_BO3_RAW_FX and clientscript_override_enabled() and SAFE_FULL_SERVANT_SURFACE_DOWNGRADE):
        return

    forbidden_techset = "effect_jz61190f"
    offenders: list[str] = []
    for material_name in STAGED_FX_MATERIAL_NAMES:
        material_path = MATERIALS_DIR / f"{material_name}.json"
        if not material_path.exists():
            continue
        payload = json.loads(material_path.read_text(encoding="utf-8", errors="replace"))
        if str(payload.get("techniqueSet", "")).strip() == forbidden_techset:
            offenders.append(material_name)

    if offenders:
        raise RuntimeError(
            "Safe full Servant surface downgrade failed; staged FX materials still reference "
            f"the crashing technique family '{forbidden_techset}'.\n"
            f"Offending materials: {', '.join(sorted(offenders))}"
        )


def verify_full_servant_probe_isolation() -> None:
    if client_ffprobe_enabled():
        return
    if not (USE_BO3_RAW_FX and clientscript_override_enabled()):
        return

    forbidden_prefixes = ("ffprobe_", "zombie/fx_ffprobe_")
    forbidden_images = {
        STOCK_FULLDDS_IMAGE_NAME,
        *[str(spec["image"]) for spec in PHOSPHOROUS_VARIANTS.values()],
    }

    offenders: list[str] = []
    for fx_name in STAGED_FX_NAMES:
        if fx_name.startswith(forbidden_prefixes[1]):
            offenders.append(f"fx:{fx_name}")
    for material_name in STAGED_FX_MATERIAL_NAMES:
        if material_name.startswith(forbidden_prefixes[0]) or material_name == "bo3_rev_debug_stock_glow":
            offenders.append(f"material:{material_name}")
    for image_name in STAGED_FX_IMAGE_NAMES:
        if image_name in forbidden_images:
            offenders.append(f"image:{image_name}")

    if offenders:
        raise RuntimeError(
            "Full Servant runtime build still includes ffprobe-only debug assets.\n"
            f"Offending staged assets: {', '.join(sorted(offenders))}"
        )


def stage_custom_idg_viewhands_asset() -> None:
    dst_json = XMODEL_DIR / f"{VIEWHANDS_ASSET}.json"
    if not use_custom_idg_viewhands():
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

    if not use_custom_idg_viewhands():
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
    forced_hand_model = "" if FORCE_LOW_HANDMODEL else ("viewmodel_usa_no_model" if use_custom_idg_viewhands() else base_hand_model)
    forced = {
        "displayName": "WEAPON_BLACK_HOLE_BOMB" if uses_t5_gersh_assets() else "WEAPON_APOTHICON_SERVANT",
        "gunModel": "viewmodel_usa_no_model" if use_custom_idg_viewhands() else resolved_gun_model(base_fields),
        "handModel": forced_hand_model,
        "worldModel": resolved_world_model(base_fields),
        "clipSize": PROOF_CLIP_SIZE,
        "startAmmo": PROOF_START_AMMO,
        "maxAmmo": PROOF_MAX_AMMO,
        "ammoCountClipRelative": "0",
        "camo": "",
        "fireTime": PROOF_FIRE_TIME,
        "damage": PROOF_DAMAGE,
    }
    if uses_t5_gersh_assets():
        forced.update(
            {
                "projectileModel": resolved_world_model(base_fields),
                "hudIcon": str(base_fields.get("hudIcon", "hud_empgrenade")),
                "killIcon": str(base_fields.get("killIcon", "hud_empgrenade")),
                "explosionRadius": "0",
                "explosionInnerDamage": "0",
                "explosionOuterDamage": "0",
                "projExplosionEffect": "",
                "projExplosionSound": "",
                "fuseTime": "1.0",
                "aifuseTime": "1.0",
                "timedDetonation": "1",
                "isRollingGrenade": "1",
                "holdButtonToThrow": "0",
            }
        )
    else:
        forced.update(
            {
                "viewFlashEffect": "",
                "worldFlashEffect": "",
                "projTrailEffect": "",
                "projExplosionEffect": "",
            }
        )
    forced.update(donor_anim_profile_overrides())
    for key, value in pairs:
        seen.add(key)
        if key in forced:
            updated.append((key, forced[key]))
            continue
        if bo3_anim_field_enabled(key) and key in ANIM_FIELDS:
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
    global STAGED_IMAGE_NAMES, STAGED_MODEL_IMAGE_NAMES
    STAGED_IMAGE_NAMES = []
    STAGED_MODEL_IMAGE_NAMES = []
    if not uses_custom_model():
        stage_bo3_servant_fx_surfaces()
        return
    if uses_t5_gersh_assets():
        stage_t5_gersh_materials()
        return
    model_material_names = staged_model_material_names()
    bundle_report = build_idg_surface_bundle(model_material_names)

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

    if not USE_STOCK_IDG_IMAGES:
        for image_name in IDG_SPEC_IMAGE_NAMES:
            src_png_name = IDG_SURFACE_IMAGE_FILES.get(image_name)
            if not src_png_name:
                continue
            src_png = IDG_SURFACE_IMAGE_ROOT / src_png_name
            if not src_png.exists():
                continue
            write_processed_iwi_from_png(src_png, IMAGES_DIR / f"{image_name}.iwi", "spec_soft", image_name)

    if USE_MANUAL_IDG_IMAGES and not USE_STOCK_IDG_IMAGES:
        for image_name in staged_images:
            src_png_name = IDG_SURFACE_IMAGE_FILES.get(image_name)
            if not src_png_name:
                continue
            src_png = IDG_SURFACE_IMAGE_ROOT / src_png_name
            if not src_png.exists():
                continue
            write_manual_idg_iwi(src_png, IMAGES_DIR / f"{image_name}.iwi", image_name)
        normalize_t6_iwi_headers(staged_images)

    if USE_PROCESSED_IDG_IMAGES:
        # Keep the image-grade experiments opt-in. The translator/ImageConverter
        # output is the safest baseline when tracking down black-texture regressions.
        for image_name, mode in IDG_IMAGE_PROCESS_PLAN.items():
            src_png_name = IDG_SURFACE_IMAGE_FILES.get(image_name)
            if not src_png_name:
                continue
            src_png = IDG_SURFACE_IMAGE_ROOT / src_png_name
            dst_iwi = IMAGES_DIR / f"{image_name}.iwi"
            if not src_png.exists():
                raise FileNotFoundError(f"Missing source PNG for processed image {image_name}: {src_png}")
            write_processed_iwi_from_png(src_png, dst_iwi, mode, image_name)

    build_safe_bo2_idg_materials(model_material_names)
    STAGED_MODEL_IMAGE_NAMES = list(staged_images)
    STAGED_IMAGE_NAMES = staged_images
    stage_bo3_servant_fx_surfaces()
    print(
        f"Staged translated IDG surfaces: materials={len(model_material_names)} "
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


def active_xanim_source_dir() -> Path:
    if USE_REBAKED_BO3_XANIMS and any(XANIM_REBAKED_DIR.glob("vm_zod_id_gun_*.xanim_export")):
        return XANIM_REBAKED_DIR
    return XANIM_DIR


def rebake_bo3_xanim_exports() -> None:
    if not USE_BO3_IDG_ANIMS or not USE_REBAKED_BO3_XANIMS:
        return
    if not IDG_VIEW_GLB_SRC.exists():
        raise FileNotFoundError(f"Missing reduced Servant GLB for xanim rebake: {IDG_VIEW_GLB_SRC}")
    if not BLENDER_REBAKE_WORKER.exists():
        raise FileNotFoundError(f"Missing Blender xanim rebake worker: {BLENDER_REBAKE_WORKER}")
    if not BLENDER_COD_PARENT.exists():
        raise FileNotFoundError(f"Missing blender-cod source root: {BLENDER_COD_PARENT}")

    blender_exe = choose_blender_executable(os.environ.get("ROGUE_BLENDER_EXE", "blender"))
    if not Path(blender_exe).exists() and shutil.which(blender_exe) is None:
        raise FileNotFoundError(f"Blender executable not found: {blender_exe}")

    if XANIM_REBAKED_DIR.exists():
        shutil.rmtree(XANIM_REBAKED_DIR)
    XANIM_REBAKED_DIR.mkdir(parents=True, exist_ok=True)

    rebaked = 0
    for stem in IDG_ANIMS:
        src = XANIM_DIR / f"{stem}.xanim_export"
        dst = XANIM_REBAKED_DIR / f"{stem}.xanim_export"
        if not src.exists():
            raise FileNotFoundError(f"Missing source xanim_export for rebake: {src}")
        cmd = [
            blender_exe,
            "-b",
            "--factory-startup",
            "--python-exit-code",
            "1",
            "--python",
            str(BLENDER_REBAKE_WORKER),
            "--",
            "--input-glb",
            str(IDG_VIEW_GLB_SRC),
            "--input-anim",
            str(src),
            "--output-anim",
            str(dst),
            "--blender-cod-root",
            str(BLENDER_COD_PARENT),
        ]
        run_checked(cmd, cwd=ROOT)
        if not dst.exists():
            raise FileNotFoundError(f"Blender rebake did not produce output xanim_export: {dst}")
        rebaked += 1

    print(f"Rebaked xanim_export files through Blender: {rebaked}")


def write_zone_source() -> None:
    material_names = runtime_zone_material_names()
    image_names = runtime_zone_image_names()
    fx_names = runtime_zone_fx_names()
    donor_xanim_names = donor_extra_runtime_xanims()
    zone_path = ZONE_SOURCE_DIR / f"{RUNTIME_ZONE_NAME}.zone"
    ipak_directive = f">ipak,{RUNTIME_ZONE_NAME}"

    if USE_FULL_ZONE_SOURCE:
        template_zone = full_zone_source_path()
        if not template_zone.exists():
            raise FileNotFoundError(f"Missing full runtime zone source: {template_zone}")

        lines = template_zone.read_text(encoding="utf-8").splitlines()
        if USE_MAP_FULL_ZONE_SOURCE:
            rewritten: list[str] = []
            for line in lines:
                if line.startswith(">level.ipak_write,"):
                    rewritten.append(f">level.ipak_write,{RUNTIME_ZONE_NAME}")
                else:
                    rewritten.append(line)
            lines = rewritten
        existing = {line.strip() for line in lines if line.strip()}
        if image_names and ipak_directive not in existing:
            lines.append(ipak_directive)
            existing.add(ipak_directive)
        additions = [
            *[f"fx,{name}" for name in fx_names],
            *[f"image,{name}" for name in image_names],
            *[f"material,{name}" for name in material_names],
            *[f"script,{name}" for name in active_clientscript_assets()],
            *[f"script,{name}" for name in active_server_script_assets()],
            *[f"xanim,{name}" for name in donor_xanim_names],
            *([f"xmodel,{MODEL_ASSET}"] if uses_custom_model() else []),
            *([f"xmodel,{WORLD_MODEL_ASSET}"] if uses_t5_gersh_assets() and uses_custom_model() else []),
            *([f"xmodel,{VIEWHANDS_ASSET}"] if use_custom_idg_viewhands() else []),
            *([f"xmodel,{BRIDGE_VIEWHANDS_ASSET}"] if use_custom_idg_viewhands() else []),
            *([f"xmodel,{name}" for name in STUB_VIEWHANDS_NAMES] if STUB_ZM_VIEWHANDS else []),
            f"weapon,{WEAPON_ASSET}",
        ]

        for line in additions:
            if line not in existing:
                lines.append(line)
                existing.add(line)

        template_entries = {
            (
                f">level.ipak_write,{RUNTIME_ZONE_NAME}"
                if USE_MAP_FULL_ZONE_SOURCE and line.startswith(">level.ipak_write,")
                else line
            )
            for line in template_zone.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("//")
        }
        generated_entries = {
            line
            for line in lines
            if line.strip() and not line.startswith("//")
        }
        missing_template_entries = sorted(template_entries - generated_entries)
        if missing_template_entries:
            preview = ", ".join(missing_template_entries[:8])
            raise RuntimeError(
                "Rebuilt runtime zone source dropped stock entries; "
                f"first missing entries: {preview}"
            )

        zone_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    out = [
        "// Call Of Duty: Black Ops II",
        ">game,T6",
        "",
        "// Auto-generated by _build/build_bo3_rev_idg_probe.py",
        *([ipak_directive] if image_names else []),
        *[f"fx,{name}" for name in fx_names],
        *[f"image,{name}" for name in image_names],
        *[f"material,{name}" for name in material_names],
        *[f"script,{name}" for name in active_clientscript_assets()],
        *[f"script,{name}" for name in active_server_script_assets()],
        *[f"xanim,{name}" for name in donor_xanim_names],
        *([f"xmodel,{MODEL_ASSET}"] if uses_custom_model() else []),
        *([f"xmodel,{WORLD_MODEL_ASSET}"] if uses_t5_gersh_assets() and uses_custom_model() else []),
        *([f"xmodel,{VIEWHANDS_ASSET}"] if use_custom_idg_viewhands() else []),
        *([f"xmodel,{BRIDGE_VIEWHANDS_ASSET}"] if use_custom_idg_viewhands() else []),
        *([f"xmodel,{name}" for name in STUB_VIEWHANDS_NAMES] if STUB_ZM_VIEWHANDS else []),
        f"weapon,{WEAPON_ASSET}",
        "",
    ]
    zone_path.write_text("\n".join(out), encoding="utf-8")


def write_fx_load_zone_source() -> None:
    zone_path = ZONE_SOURCE_DIR / f"{BO3_FX_LOAD_ZONE_NAME}.zone"
    if not using_dedicated_bo3_fx_load_lane():
        if zone_path.exists():
            zone_path.unlink()
        return

    material_names = fx_load_zone_material_names()
    image_names = fx_load_zone_image_names()
    fx_names = fx_load_zone_fx_names()
    if not fx_names and not material_names and not image_names:
        if zone_path.exists():
            zone_path.unlink()
        return

    out = [
        "// Call Of Duty: Black Ops II",
        ">game,T6",
        "",
        "// Auto-generated BO3 FX load lane for standalone runtime packaging",
        *([f">ipak,{BO3_FX_LOAD_ZONE_NAME}"] if image_names else []),
        *[f"fx,{name}" for name in fx_names],
        *[f"image,{name}" for name in image_names],
        *[f"material,{name}" for name in material_names],
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


def analyze_bo3_servant_fx_graph() -> dict[str, object]:
    if not FX_ANALYZER.exists():
        raise FileNotFoundError(f"Missing FX analyzer script: {FX_ANALYZER}")
    run_checked(
        [
            sys.executable,
            str(FX_ANALYZER),
            "--raw-fx-root",
            str(BO3_FX_RAW_ROOT),
            "--out",
            str(FX_GRAPH_REPORT),
        ],
        cwd=ROOT,
    )
    return json.loads(FX_GRAPH_REPORT.read_text(encoding="utf-8"))


def validate_bo3_servant_fx_graph() -> dict[str, object]:
    report = analyze_bo3_servant_fx_graph()
    compat = report.get("t6_compatibility", {})
    fatal_effects = compat.get("fatal_effects", [])
    warning_effects = compat.get("warning_effects", [])

    if warning_effects:
        print("BO3 raw FX compatibility warnings:")
        for issue in warning_effects:
            effect = str(issue.get("effect", "")).strip() or "<unknown>"
            reasons = issue.get("reasons", [])
            print(f"  WARN {effect}: {'; '.join(str(reason) for reason in reasons)}")

    if fatal_effects and not ALLOW_UNSUPPORTED_RAW_FX:
        lines = [
            "BO3 raw FX graph is not T6-safe with the current OAT loader.",
            "Fatal compatibility blockers:",
        ]
        for issue in fatal_effects:
            effect = str(issue.get("effect", "")).strip() or "<unknown>"
            reasons = issue.get("reasons", [])
            lines.append(f"  - {effect}: {'; '.join(str(reason) for reason in reasons)}")
        lines.append("Set ROGUE_ALLOW_UNSUPPORTED_RAW_FX=1 to bypass this guard for debugging only.")
        raise RuntimeError("\n".join(lines))

    return report


def run_capture(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=str(cwd) if cwd else None, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(args)}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def compile_mod_load() -> None:
    xanim_source_dir = active_xanim_source_dir()
    donor_ff = None
    if BO3_ANIM_DONOR_FF_OVERRIDE:
        donor_ff = Path(BO3_ANIM_DONOR_FF_OVERRIDE).resolve()
    elif XANIM_IDLE_ORACLE_FF.exists():
        donor_ff = XANIM_IDLE_ORACLE_FF
    elif (OUTPUT / f"{MOD_LOAD_ZONE_NAME}.ff").exists():
        donor_ff = OUTPUT / f"{MOD_LOAD_ZONE_NAME}.ff"

    args = [
        sys.executable,
        str(XANIM_COMPILER),
        "--xanim-dir",
        str(xanim_source_dir),
        "--pattern",
        "vm_zod_id_gun_*.xanim_export",
        "--output-dir",
        str(OUTPUT),
        "--zone-name",
        MOD_LOAD_ZONE_NAME,
        "--crypto-seed",
        MOD_LOAD_ZONE_NAME,
        "--emit-mode",
        BO3_ANIM_EMIT_MODE,
        "--bo3-frames-targets",
        *IDG_ANIMS,
        "--bo3-fallback-mode",
        "static_pose",
        "--no-semantic-fill",
    ]
    if BO3_ANIM_FORCE_IDENTITY:
        args.append("--force-identity-pose")
    if BO3_ANIM_EMIT_MODE in ("donor_clone", "donor_template_static_pose", "donor_semantic_static_pose"):
        if donor_ff is None or not donor_ff.exists():
            raise FileNotFoundError(
                "Missing donor oracle FF for custom anim compile. "
                "Set ROGUE_BO3_ANIM_DONOR_FF or populate _build/xanim_oracles/vm_zod_idle_donorclone_mod_load.ff."
            )
        args.extend(
            [
                "--donor-ff",
                str(donor_ff),
                "--donor-zone-name",
                BO3_ANIM_DONOR_ZONE,
                "--donor-asset",
                BO3_ANIM_DONOR_ASSET,
                "--donor-override",
                f"vm_zod_id_gun_idle={BO3_ANIM_DONOR_ASSET}",
            ]
        )
    if IDG_WEAPON_ONLY_RIG_REPORT.exists():
        args.extend(["--keep-bones-file", str(IDG_WEAPON_ONLY_RIG_REPORT)])
    run_checked(args, cwd=ROOT)


def build_dedicated_bo3_fx_load_ff() -> None:
    if not using_dedicated_bo3_fx_load_lane():
        return

    zone_path = ZONE_SOURCE_DIR / f"{BO3_FX_LOAD_ZONE_NAME}.zone"
    if not zone_path.exists():
        raise FileNotFoundError(f"Missing BO3 FX load zone source: {zone_path}")

    if not DEV_LINKER.exists():
        raise FileNotFoundError(f"Missing dev Linker for raw BO3 FX load lane: {DEV_LINKER}")

    args = [
        str(DEV_LINKER),
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
        "--add-asset-search-path",
        str(full_zone_source_root()),
        "--add-source-search-path",
        str(full_zone_source_root()),
        "--add-asset-search-path",
        str(ZONE_DUMP_SOURCE_ROOT),
        "--add-source-search-path",
        str(ZONE_DUMP_SOURCE_ROOT),
    ]
    for support_root in FX_RUNTIME_SUPPORT_ROOTS:
        if not support_root.exists():
            continue
        args.extend(
            [
                "--add-asset-search-path",
                str(support_root),
                "--add-source-search-path",
                str(support_root),
            ]
        )
    args.extend(
        [
            "--output-folder",
            str(OUTPUT),
            BO3_FX_LOAD_ZONE_NAME,
        ]
    )
    run_checked(args, cwd=ROOT)


def build_runtime_ff() -> None:
    args = [
        str(runtime_linker_path()),
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
    # Do not feed the unlinked full-runtime donor tree back into the runtime linker
    # as a live search root. It contains partial dumped stock assets (notably
    # soundbank CSVs) that can override loaded stock fastfile assets and force
    # regeneration instead of reuse, which breaks startup fidelity.
    for ff in LOAD_FFS:
        args.extend(["--load", str(ff)])
    args.extend(["--load", str(SO_SURVIVAL_BASELINE_FF)])
    args.append(RUNTIME_ZONE_NAME)
    run_checked(args, cwd=ROOT)


def verify_runtime_ff_safety() -> None:
    if not DEPLOY_TO_MOD and not DEPLOY_TO_BASE:
        return

    runtime_ff = OUTPUT / RUNTIME_FF_NAME
    if not runtime_ff.exists():
        raise FileNotFoundError(f"Missing runtime FF: {runtime_ff}")

    assets = parse_unlinker_list(run_capture([str(UNLINKER), "--list", str(runtime_ff)], cwd=ROOT))
    baseline_ff = ZM_TRANSIT_BASELINE_FF if USE_MAP_FULL_ZONE_SOURCE else SO_SURVIVAL_BASELINE_FF
    baseline_size = baseline_ff.stat().st_size if baseline_ff.exists() else 0
    runtime_size = runtime_ff.stat().st_size

    has_keyvaluepairs = any(line.startswith("keyvaluepairs, so_zsurvival_zm_transit") for line in assets)
    has_any_scripts = any(line.startswith("script,") or line.startswith("scriptparsetree,") for line in assets)
    size_ok = baseline_size > 0 and runtime_size >= int(baseline_size * 0.50)

    if USE_MAP_FULL_ZONE_SOURCE:
        if has_any_scripts and size_ok:
            return
    elif has_keyvaluepairs and has_any_scripts and size_ok:
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
        f"runtime_size={runtime_size};baseline_size={baseline_size};"
        f"use_map_full_zone_source={USE_MAP_FULL_ZONE_SOURCE}"
    )


def verify_runtime_ipak() -> None:
    runtime_ipak = OUTPUT / RUNTIME_IPAK_NAME
    if not runtime_zone_image_names():
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
    if not SKIP_LOOSE_IMAGE_DEPLOY:
        purge_targets.extend(STORAGE_LOOSE_IMAGE_DIR / f"{image_name}.iwi" for image_name in STAGED_IMAGE_NAMES)
        purge_targets.extend(STORAGE_LOOSE_IMAGE_DIR / f"{alias_name}.iwi" for alias_name in loose_image_alias_map())

    for target in purge_targets:
        purge_path(target)
        print(f"Purged stale deploy target -> {target}")


def copy2_atomic(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp_copy")
    if tmp.exists():
        tmp.unlink()
    shutil.copy2(src, tmp)
    os.replace(tmp, dst)


def is_optional_deploy_target(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except Exception:
        resolved = path
    optional_roots = [STORAGE_MOD_ROOT]
    if not SKIP_LOOSE_IMAGE_DEPLOY:
        optional_roots.append(STORAGE_LOOSE_IMAGE_DIR)
    for root in optional_roots:
        try:
            if resolved.is_relative_to(root.resolve()):
                return True
        except Exception:
            if str(resolved).lower().startswith(str(root).lower()):
                return True
    return False


SKIPPED_OPTIONAL_DEPLOY_TARGETS: list[Path] = []


def safe_copy2_atomic(src: Path, dst: Path) -> bool:
    try:
        copy2_atomic(src, dst)
        return True
    except PermissionError:
        if is_optional_deploy_target(dst):
            print(f"WARNING: optional deploy target locked, skipped -> {dst}")
            SKIPPED_OPTIONAL_DEPLOY_TARGETS.append(dst)
            return False
        raise


def safe_unlink_optional(path: Path) -> bool:
    try:
        path.unlink()
        return True
    except PermissionError:
        if is_optional_deploy_target(path) or path.name.lower() in (f"{MOD_LOAD_ZONE_NAME}.ff", f"{MOD_LOAD_ZONE_NAME}.ipak"):
            print(f"WARNING: optional stale target locked, skipped -> {path}")
            SKIPPED_OPTIONAL_DEPLOY_TARGETS.append(path)
            return False
        raise


def render_probe_script() -> None:
    if not SCRIPT_TEMPLATE.exists():
        raise FileNotFoundError(f"Missing GSC template: {SCRIPT_TEMPLATE}")

    tokens = {
        "__BUILD_TAG__": BUILD_TAG,
        "__PROBE_WEAPON__": WEAPON_ASSET,
        "__STARTER_WEAPON__": PROBE_STARTER_WEAPON,
        "__PROBE_MODE__": GUN_MODEL_MODE,
        "__MODEL_ASSET__": resolved_gun_model(base_weapon_fields()),
        "__WORLD_MODEL_ASSET__": resolved_world_model(base_weapon_fields()),
        "__IS_TACTICAL__": "1" if uses_t5_gersh_assets() else "0",
        "__EXPECTED_CLIP__": EXPECTED_CLIP,
        "__EXPECTED_ENGINE_MAX__": EXPECTED_ENGINE_MAX,
        "__EXPECTED_HUD_RESERVE__": EXPECTED_HUD_RESERVE,
        "__RAW_FX_STAGE__": RAW_FX_STAGE,
        "__RAW_FX_ENABLED__": "1" if USE_BO3_RAW_FX else "0",
        "__RAW_FX_MUZZLE__": "1" if raw_fx_stage_enabled("muzzle") else "0",
        "__RAW_FX_PROJECTILE__": "1" if raw_fx_stage_enabled("projectile") else "0",
        "__RAW_FX_IMPACT__": "1" if raw_fx_stage_enabled("impact") else "0",
        "__RAW_FX_VORTEX__": "1" if raw_fx_stage_enabled("full") else "0",
        "__RAW_FX_STRICT__": "1" if RAW_FX_STRICT else "0",
        "__CLIENT_FX_ENABLED__": "1" if clientscript_override_enabled() else "0",
    }
    rendered = SCRIPT_TEMPLATE.read_text(encoding="utf-8")
    for token, value in tokens.items():
        rendered = rendered.replace(token, value)
    if client_ffprobe_enabled():
        precache_snippet = (
            '    bo3_rev_ffprobe_server_precache();\n'
            '    bo3_rev_start();'
        )
        rendered = rendered.replace('    bo3_rev_start();', precache_snippet, 2)
        rendered += (
            "\n\n"
            "bo3_rev_ffprobe_server_precache()\n"
            "{\n"
            "    if ( isdefined( level.bo3_rev_ffprobe_server_precache_done ) )\n"
            "        return;\n\n"
            "    level.bo3_rev_ffprobe_server_precache_done = 1;\n"
            f'    level.bo3_rev_ffprobe_server_fx = loadfx( "{CLIENT_FFPROBE_ASSET}" );\n'
            '    println( "[ffprobe][gsc] precache asset=' + CLIENT_FFPROBE_ASSET + '"'
            ' + ";ok=" + ( isdefined( level.bo3_rev_ffprobe_server_fx ) && level.bo3_rev_ffprobe_server_fx )'
            ' + ";build=__BUILD_TAG__" );\n'
            "}\n"
        )

    script_output = active_script_output()
    script_output.parent.mkdir(parents=True, exist_ok=True)
    script_output.write_text(rendered, encoding="utf-8")
    print(f"Rendered probe script -> {script_output}")


def render_clientscript_template(template: Path, output: Path, work_output: Path) -> None:
    if not template.exists():
        raise FileNotFoundError(f"Missing clientscript template: {template}")

    if template == SERVANT_CLIENTSCRIPT_TEMPLATE and client_ffprobe_enabled():
        rendered = render_client_ffprobe_script()
    elif template == VISIONSET_CLIENTSCRIPT_TEMPLATE and client_ffprobe_enabled():
        rendered = render_client_ffprobe_visionset_mgr()
    else:
        rendered = template.read_text(encoding="utf-8")
    rendered = rendered.replace("__BUILD_TAG__", BUILD_TAG)
    rendered = rendered.replace("__MODEL_ASSET__", resolved_gun_model(base_weapon_fields()))
    rendered = rendered.replace("__WORLD_MODEL_ASSET__", resolved_world_model(base_weapon_fields()))
    rendered = rendered.replace("__SERVANT_ENABLE_PROJECTILE__", "0" if SERVANT_FX_SCOPE == "vortex_core" else "1")
    rendered = rendered.replace("__SERVANT_VORTEX_DEBUG_MARKERS__", "1" if SERVANT_VORTEX_DEBUG_MARKERS else "0")
    rendered = rendered.replace("__SERVANT_VORTEX_Z_OFFSET__", "0" if SERVANT_FX_SCOPE == "vortex_core" else "-72")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    work_output.parent.mkdir(parents=True, exist_ok=True)
    work_output.write_text(rendered, encoding="utf-8")
    print(f"Rendered probe clientscript -> {output}")


def render_probe_clientscripts() -> None:
    for stale in (
        WORK / "clientscripts" / "mp" / "zombies" / "_bo3_rev_servant_fx.csc",
        WORK / "clientscripts" / "mp" / "zombies" / "_bo3_rev_servant_fx_v2.csc",
        ROOT / "mods" / MOD_NAME / "clientscripts" / "mp" / "zombies" / "_bo3_rev_servant_fx_v2.csc",
    ):
        if stale.exists():
            stale.unlink()
            print(f"Removed stale rendered clientscript -> {stale}")

    render_clientscript_template(
        TRANSIT_CLIENTSCRIPT_TEMPLATE,
        TRANSIT_CLIENTSCRIPT_OUTPUT,
        WORK_TRANSIT_CLIENTSCRIPT_OUTPUT,
    )
    render_clientscript_template(
        SERVANT_CLIENTSCRIPT_TEMPLATE,
        SERVANT_CLIENTSCRIPT_OUTPUT,
        WORK_SERVANT_CLIENTSCRIPT_OUTPUT,
    )
    if client_ffprobe_enabled():
        render_clientscript_template(
            VISIONSET_CLIENTSCRIPT_TEMPLATE,
            VISIONSET_CLIENTSCRIPT_OUTPUT,
            WORK_VISIONSET_CLIENTSCRIPT_OUTPUT,
        )


def sync_loose_probe_scripts() -> None:
    src_script = active_script_output()
    if SKIP_SCRIPT_SYNC:
        return

    for script_dir in (GAME_MOD_SCRIPT_DIR, STORAGE_MOD_SCRIPT_DIR):
        script_dir.mkdir(parents=True, exist_ok=True)
        if safe_copy2_atomic(src_script, script_dir / "mod_i_am_mod.gsc"):
            print(f"Synced script -> {script_dir}")

    if clientscript_override_enabled():
        client_targets = (
            (TRANSIT_CLIENTSCRIPT_OUTPUT, GAME_MOD_CLIENTSCRIPT_DIR.parent / "zm_transit.csc"),
            (TRANSIT_CLIENTSCRIPT_OUTPUT, STORAGE_MOD_CLIENTSCRIPT_DIR.parent / "zm_transit.csc"),
            (SERVANT_CLIENTSCRIPT_OUTPUT, GAME_MOD_CLIENTSCRIPT_DIR / "_bo3_rev_servant_fx_v3.csc"),
            (SERVANT_CLIENTSCRIPT_OUTPUT, STORAGE_MOD_CLIENTSCRIPT_DIR / "_bo3_rev_servant_fx_v3.csc"),
            *(
                [
                    (VISIONSET_CLIENTSCRIPT_OUTPUT, GAME_MOD_CLIENTSCRIPT_DIR.parent / "_visionset_mgr.csc"),
                    (VISIONSET_CLIENTSCRIPT_OUTPUT, STORAGE_MOD_CLIENTSCRIPT_DIR.parent / "_visionset_mgr.csc"),
                ]
                if client_ffprobe_enabled()
                else []
            ),
        )
        for src, dst in client_targets:
            if not src.exists():
                raise FileNotFoundError(f"Missing rendered clientscript: {src}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            if safe_copy2_atomic(src, dst):
                print(f"Synced clientscript -> {dst}")
        for stale in (
            GAME_MOD_CLIENTSCRIPT_DIR / "_bo3_rev_servant_fx.csc",
            STORAGE_MOD_CLIENTSCRIPT_DIR / "_bo3_rev_servant_fx.csc",
            GAME_MOD_CLIENTSCRIPT_DIR / "_bo3_rev_servant_fx_v2.csc",
            STORAGE_MOD_CLIENTSCRIPT_DIR / "_bo3_rev_servant_fx_v2.csc",
        ):
            if stale.exists():
                if safe_unlink_optional(stale):
                    print(f"Removed stale clientscript -> {stale}")
        for stale in (
            GAME_MOD_CLIENTSCRIPT_DIR / "_zm_weap_cymbal_monkey.csc",
            STORAGE_MOD_CLIENTSCRIPT_DIR / "_zm_weap_cymbal_monkey.csc",
        ):
            if stale.exists():
                stale.unlink()
                print(f"Removed stale monkey clientscript override -> {stale}")
    for stale in (
        ROOT / "mods" / MOD_NAME / "maps" / "mp" / "zombies" / "_bo3_rev_servant_bridge.gsc",
        STORAGE_MOD_ROOT / "maps" / "mp" / "zombies" / "_bo3_rev_servant_bridge.gsc",
    ):
        if stale.exists():
            stale.unlink()
            print(f"Removed stale raw server bridge -> {stale}")


def deploy_outputs() -> None:
    SKIPPED_OPTIONAL_DEPLOY_TARGETS.clear()
    deploy_targets = deployed_output_targets()

    if not deploy_targets:
        print("Deploy skipped: both deploy targets are disabled.")
        return

    # Sync the loose script lane first. The live runtime is willing to load these
    # from AppData mod storage even when a later base-zone FF/IPAK copy fails, so
    # copying them up front prevents stale build ownership after a partial deploy.
    sync_loose_probe_scripts()

    for dst_dir in deploy_targets:
        dst_dir.mkdir(parents=True, exist_ok=True)
        output_names = [RUNTIME_FF_NAME, RUNTIME_IPAK_NAME]
        if USE_BO3_IDG_ANIMS or using_dedicated_bo3_fx_load_lane():
            output_names.insert(1, BO3_FX_LOAD_FF_NAME if using_dedicated_bo3_fx_load_lane() else f"{MOD_LOAD_ZONE_NAME}.ff")
        if using_dedicated_bo3_fx_load_lane():
            output_names.insert(2, BO3_FX_LOAD_IPAK_NAME)
        for ff_name in output_names:
            src = OUTPUT / ff_name
            if not src.exists():
                if ff_name in (RUNTIME_IPAK_NAME, BO3_FX_LOAD_IPAK_NAME):
                    continue
                raise FileNotFoundError(f"Missing build output: {src}")
            if safe_copy2_atomic(src, dst_dir / ff_name):
                print(f"Deployed {ff_name} -> {dst_dir}")
        if not USE_BO3_IDG_ANIMS and not using_dedicated_bo3_fx_load_lane():
            for stale_name in (f"{MOD_LOAD_ZONE_NAME}.ff", f"{MOD_LOAD_ZONE_NAME}.ipak"):
                stale_mod_load = dst_dir / stale_name
                if stale_mod_load.exists():
                    if safe_unlink_optional(stale_mod_load):
                        print(f"Removed stale {stale_name} -> {dst_dir}")

    if STAGED_IMAGE_NAMES and not USE_STOCK_IDG_IMAGES and not SKIP_LOOSE_IMAGE_DEPLOY:
        STORAGE_LOOSE_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        for image_name in STAGED_IMAGE_NAMES:
            if should_skip_loose_runtime_image(image_name):
                stale_dst = STORAGE_LOOSE_IMAGE_DIR / f"{image_name}.iwi"
                if stale_dst.exists() and safe_unlink_optional(stale_dst):
                    print(f"Removed skipped loose image override -> {stale_dst}")
                continue
            src = IMAGES_DIR / f"{image_name}.iwi"
            if not src.exists():
                raise FileNotFoundError(f"Missing staged image for loose deploy: {src}")
            dst = STORAGE_LOOSE_IMAGE_DIR / src.name
            if safe_copy2_atomic(src, dst):
                print(f"Deployed loose image override -> {dst}")
        for alias_name, source_name in loose_image_alias_map().items():
            if should_skip_loose_runtime_image(source_name):
                stale_alias = STORAGE_LOOSE_IMAGE_DIR / f"{alias_name}.iwi"
                if stale_alias.exists() and safe_unlink_optional(stale_alias):
                    print(f"Removed skipped loose image alias -> {stale_alias}")
                continue
            src = IMAGES_DIR / f"{source_name}.iwi"
            if not src.exists():
                raise FileNotFoundError(
                    f"Missing staged image for loose alias deploy: {src} (alias {alias_name})"
                )
            dst = STORAGE_LOOSE_IMAGE_DIR / f"{alias_name}.iwi"
            if safe_copy2_atomic(src, dst):
                print(f"Deployed loose image alias -> {dst} (source {source_name}.iwi)")

    if REQUIRE_APPDATA_SYNC:
        stale_storage_targets = [path for path in SKIPPED_OPTIONAL_DEPLOY_TARGETS if is_optional_deploy_target(path)]
        if stale_storage_targets:
            lines = [
                "Required AppData mod sync did not complete.",
                "Close Plutonium/BO2 completely and rebuild so the live AppData mod copy is updated.",
                "Locked targets:",
            ]
            lines.extend(f"  - {path}" for path in stale_storage_targets)
            raise RuntimeError("\n".join(lines))


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


def try_parse_unlinker_list(path: Path) -> tuple[list[str], str | None]:
    try:
        return parse_unlinker_list(run_capture([str(UNLINKER), "--list", str(path)], cwd=ROOT)), None
    except RuntimeError as exc:
        text = str(exc)
        known_unlinker_limits = (
            "T6::XFILE_BLOCK_STREAMER_RESERVE",
            "T6::XFILE_BLOCK_DELAY_VIRTUAL",
        )
        if any(token in text for token in known_unlinker_limits):
            return [], text
        raise


def verify_dedicated_bo3_fx_load_ff() -> None:
    if not using_dedicated_bo3_fx_load_lane():
        return

    fx_load_ff = OUTPUT / BO3_FX_LOAD_FF_NAME
    if not fx_load_ff.exists():
        raise FileNotFoundError(f"Missing BO3 FX load FF: {fx_load_ff}")

    try:
        assets, warning = try_parse_unlinker_list(fx_load_ff)
        if warning is not None:
            raise RuntimeError(warning)
        asset_set = set(assets)
        expected = {
            *{f"fx, {name}" for name in fx_load_zone_fx_names()},
            *{f"image, {name}" for name in fx_load_zone_image_names()},
            *{f"material, {name}" for name in fx_load_zone_material_names()},
        }
        missing = sorted(expected - asset_set)
        if missing:
            raise RuntimeError(
                "BO3 FX load FF manifest is incomplete.\n"
                f"FF: {fx_load_ff}\n"
                + "\n".join(f"  - missing {line}" for line in missing[:50])
            )
    except RuntimeError as exc:
        text = str(exc)
        known_unlinker_limits = (
            "T6::XFILE_BLOCK_STREAMER_RESERVE",
            "T6::XFILE_BLOCK_DELAY_VIRTUAL",
        )
        if not any(token in text for token in known_unlinker_limits):
            raise
        if not ALLOW_UNVERIFIED_DEDICATED_BO3_FX_LOAD:
            raise RuntimeError(
                "Dedicated BO3 FX load FF could not be verified by the stable Unlinker.\n"
                f"FF: {fx_load_ff}\n"
                "The build will not deploy this lane by default because an unverifiable "
                "custom fastfile has already proven capable of crashing the retail runtime.\n"
                "If you intentionally want to bypass this safety gate for debugging only, set "
                "ROGUE_ALLOW_UNVERIFIED_BO3_FX_LOAD=1."
            ) from exc
        print(
            "Warning: Unlinker could not enumerate the dedicated BO3 FX load FF due to "
            "streamed-block parsing limits; falling back to output-only verification because "
            "ROGUE_ALLOW_UNVERIFIED_BO3_FX_LOAD=1 is set."
        )

    if fx_load_zone_image_names():
        fx_load_ipak = OUTPUT / BO3_FX_LOAD_IPAK_NAME
        if not fx_load_ipak.exists():
            raise RuntimeError(
                "BO3 FX load lane staged images but did not emit a matching IPAK: "
                f"{fx_load_ipak}"
            )
        if fx_load_ipak.stat().st_size <= 0:
            raise RuntimeError(f"BO3 FX load IPAK is empty: {fx_load_ipak}")


def verify_custom_linker_contract_probe() -> None:
    if not using_dedicated_bo3_fx_load_lane():
        return

    probe_script = ROOT / "_build" / "build_t6_ff_contract_probe.py"
    probe_report = ROOT / "_build" / "ff_contract_probe" / "ff_contract_probe_report.json"
    if not probe_script.exists():
        raise FileNotFoundError(f"Missing custom-linker contract probe: {probe_script}")

    subprocess.run([sys.executable, "-u", str(probe_script)], cwd=ROOT, check=True)

    if not probe_report.exists():
        raise RuntimeError(f"Custom-linker contract probe did not emit a report: {probe_report}")

    report = json.loads(probe_report.read_text(encoding="utf-8"))
    cases = {case["name"]: case for case in report.get("cases", [])}

    release_stock = cases.get("release_stock_marker")
    dev_custom = cases.get("dev_custom_orb_stock_surface")
    if not release_stock or not dev_custom:
        raise RuntimeError(
            "Custom-linker contract probe report is missing required cases.\n"
            f"Report: {probe_report}"
        )

    release_ok = bool(
        release_stock.get("build_ok")
        and release_stock.get("unlink_ok")
        and release_stock.get("dev_unlink_ok")
    )
    custom_ok = bool(
        dev_custom.get("build_ok")
        and dev_custom.get("unlink_ok")
        and dev_custom.get("dev_unlink_ok")
    )

    if release_ok and custom_ok:
        return

    if ALLOW_UNVERIFIED_CUSTOM_LINKER_PROBE:
        print(
            "Warning: custom-linker contract probe did not pass, but "
            "ROGUE_ALLOW_UNVERIFIED_CUSTOM_LINKER_PROBE=1 is set."
        )
        return

    failure_lines = [
        "Custom-linker contract probe failed.",
        f"Report: {probe_report}",
    ]
    if not release_ok:
        failure_lines.extend(
            [
                "Release baseline did not stay self-consistent:",
                f"  build_ok={release_stock.get('build_ok')}",
                f"  stable_unlink_ok={release_stock.get('unlink_ok')}",
                f"  dev_unlink_ok={release_stock.get('dev_unlink_ok')}",
            ]
        )
    if not custom_ok:
        failure_lines.extend(
            [
                "Minimal custom raw-FX lane is not structurally safe:",
                f"  build_ok={dev_custom.get('build_ok')}",
                f"  stable_unlink_ok={dev_custom.get('unlink_ok')}",
                f"  dev_unlink_ok={dev_custom.get('dev_unlink_ok')}",
            ]
        )
        for line in (dev_custom.get("build_problems") or [])[:10]:
            failure_lines.append(f"  build_problem={line}")
        unlink_output = str(dev_custom.get("unlink_output") or "").strip()
        if unlink_output:
            failure_lines.append("  stable_unlink_output:")
            failure_lines.extend(f"    {line}" for line in unlink_output.splitlines()[:10])
        dev_unlink_output = str(dev_custom.get("dev_unlink_output") or "").strip()
        if dev_unlink_output:
            failure_lines.append("  dev_unlink_output:")
            failure_lines.extend(f"    {line}" for line in dev_unlink_output.splitlines()[:10])

    raise RuntimeError("\n".join(failure_lines))


def deployed_output_targets() -> list[Path]:
    targets: list[Path] = []
    if DEPLOY_TO_MOD:
        targets.extend([GAME_MOD_ZONE_DIR, STORAGE_MOD_ZONE_DIR])
    if DEPLOY_TO_BASE:
        targets.append(BASE_ZONE_DIR)
        targets.extend([GAME_MOD_ZONE_DIR, STORAGE_MOD_ZONE_DIR])

    deduped: list[Path] = []
    seen: set[Path] = set()
    for target in targets:
        if target in seen:
            continue
        seen.add(target)
        deduped.append(target)
    return deduped


def loose_image_alias_map() -> dict[str, str]:
    aliases: dict[str, str] = {}
    watched_names = sorted(set(STAGED_FX_IMAGE_NAMES or STAGED_IMAGE_NAMES))

    for image_name in watched_names:
        if not image_name:
            continue
        aliases[f",{image_name}"] = image_name

    if "fxt_debris_clump" in watched_names:
        aliases.setdefault("fxt_debris_clump_dirt", "fxt_debris_clump")
        aliases.setdefault(",fxt_debris_clump_dirt", "fxt_debris_clump")

    if "$identitynormalmap" in watched_names:
        aliases.setdefault(",$identitynormalmap", "$identitynormalmap")

    return aliases


def collect_output_meta(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "sha256": sha256(path) if path.exists() else "",
        "size": path.stat().st_size if path.exists() else 0,
    }


def verify_deployed_output_hashes() -> None:
    built_outputs = {
        RUNTIME_FF_NAME: OUTPUT / RUNTIME_FF_NAME,
        RUNTIME_IPAK_NAME: OUTPUT / RUNTIME_IPAK_NAME,
        BO3_FX_LOAD_FF_NAME: OUTPUT / BO3_FX_LOAD_FF_NAME,
        BO3_FX_LOAD_IPAK_NAME: OUTPUT / BO3_FX_LOAD_IPAK_NAME,
    }

    expected_names = {RUNTIME_FF_NAME}
    if built_outputs[RUNTIME_IPAK_NAME].exists():
        expected_names.add(RUNTIME_IPAK_NAME)
    if USE_BO3_IDG_ANIMS or using_dedicated_bo3_fx_load_lane():
        expected_names.add(BO3_FX_LOAD_FF_NAME)
    if using_dedicated_bo3_fx_load_lane() and built_outputs[BO3_FX_LOAD_IPAK_NAME].exists():
        expected_names.add(BO3_FX_LOAD_IPAK_NAME)

    for target_dir in deployed_output_targets():
        mismatches: list[str] = []
        for name in expected_names:
            src = built_outputs[name]
            dst = target_dir / name
            if not src.exists():
                mismatches.append(f"{name}: built output missing")
                continue
            if not dst.exists():
                mismatches.append(f"{name}: deploy target missing")
                continue
            src_hash = sha256(src)
            dst_hash = sha256(dst)
            if src_hash != dst_hash:
                mismatches.append(f"{name}: hash mismatch {src_hash[:12]} != {dst_hash[:12]}")
        if mismatches:
            raise RuntimeError(
                f"Deployed output hash verification failed for {target_dir}:\n"
                + "\n".join(f"  - {line}" for line in mismatches)
            )


def build_debug_report() -> None:
    oat_tool_architectures = verify_t6_oat_binary_architectures()
    runtime_ff = OUTPUT / RUNTIME_FF_NAME
    runtime_ipak = OUTPUT / RUNTIME_IPAK_NAME
    mod_load_ff = OUTPUT / BO3_FX_LOAD_FF_NAME
    mod_load_ipak = OUTPUT / BO3_FX_LOAD_IPAK_NAME

    runtime_ff_list = parse_unlinker_list(run_capture([str(UNLINKER), "--list", str(runtime_ff)], cwd=ROOT))
    mod_load_ff_list: list[str] = []
    mod_load_ff_list_warning: str | None = None
    if mod_load_ff.exists():
        mod_load_ff_list, mod_load_ff_list_warning = try_parse_unlinker_list(mod_load_ff)

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
    active_source_model = T5_GERSH_VIEW_GLB_SRC if uses_t5_gersh_assets() else IDG_VIEW_GLB_SRC
    report = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "build_tag": BUILD_TAG,
        "work_dir": str(WORK),
        "oat_tool_architectures": oat_tool_architectures,
        "source_model": {
            "path": str(active_source_model) if uses_custom_model() else None,
            "exists": active_source_model.exists() if uses_custom_model() else None,
            "sha256": sha256(active_source_model) if uses_custom_model() and active_source_model.exists() else None,
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
                "exists": mod_load_ff.exists(),
                "sha256": sha256(mod_load_ff) if mod_load_ff.exists() else "",
                "assets": mod_load_ff_list,
                "list_warning": mod_load_ff_list_warning,
            },
            "mod_load_ipak": {
                "path": str(mod_load_ipak),
                "exists": mod_load_ipak.exists(),
                "sha256": sha256(mod_load_ipak) if mod_load_ipak.exists() else "",
                "size": mod_load_ipak.stat().st_size if mod_load_ipak.exists() else 0,
            },
        },
        "weapon_probe": {
            "asset": WEAPON_ASSET,
            "starter_weapon": PROBE_STARTER_WEAPON,
            "gun_model_mode": GUN_MODEL_MODE,
            "build_tag": BUILD_TAG,
            "use_bo3_idg_anims": USE_BO3_IDG_ANIMS,
            "bo3_anim_stage": BO3_ANIM_STAGE,
            "bo3_anim_force_identity": BO3_ANIM_FORCE_IDENTITY,
            "use_custom_idg_viewhands": use_custom_idg_viewhands(),
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
                "worldModel": staged_weapon_pairs.get("worldModel"),
                "projectileModel": staged_weapon_pairs.get("projectileModel"),
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
                "worldModel": base_fields.get("worldModel"),
                "projectileModel": base_fields.get("projectileModel"),
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
            "output": str(active_script_output()),
            "watchlist": str(PROBE_WATCHLIST_PATH),
            "watch_entries": probe_watch_entries(),
            "servant_fx_scope": SERVANT_FX_SCOPE,
            "clientscript_templates": [
                str(TRANSIT_CLIENTSCRIPT_TEMPLATE),
                str(SERVANT_CLIENTSCRIPT_TEMPLATE),
            ],
            "clientscript_outputs": [
                str(TRANSIT_CLIENTSCRIPT_OUTPUT),
                str(SERVANT_CLIENTSCRIPT_OUTPUT),
            ],
        },
        "zone_source": str(ZONE_SOURCE_DIR / f"{RUNTIME_ZONE_NAME}.zone"),
        "surface_pipeline": {
            "bundle_report": str(IDG_SURFACE_BUNDLE_REPORT) if IDG_SURFACE_BUNDLE_REPORT.exists() else "",
            "translation_report": str(IDG_SURFACE_TRANSLATION_REPORT) if IDG_SURFACE_TRANSLATION_REPORT.exists() else "",
            "staged_images": STAGED_IMAGE_NAMES,
            "staged_model_images": STAGED_MODEL_IMAGE_NAMES,
            "staged_fx_images": STAGED_FX_IMAGE_NAMES,
            "loose_image_aliases": loose_image_alias_map(),
            "staged_fx": STAGED_FX_NAMES,
            "raw_fx_compatibility": RAW_FX_COMPAT_REPORT.get("t6_compatibility", {}) if RAW_FX_COMPAT_REPORT else {},
        },
        "fx_load_lane": {
            "enabled": using_dedicated_bo3_fx_load_lane(),
            "zone_name": BO3_FX_LOAD_ZONE_NAME,
            "ff_name": BO3_FX_LOAD_FF_NAME,
            "ipak_name": BO3_FX_LOAD_IPAK_NAME,
            "expected_manifest": {
                "fx": fx_load_zone_fx_names(),
                "materials": fx_load_zone_material_names(),
                "images": fx_load_zone_image_names(),
            },
        },
        "zone_contract": {
            "runtime_zone_source": str(ZONE_SOURCE_DIR / f"{RUNTIME_ZONE_NAME}.zone"),
            "has_runtime_ipak_directive": (
                f">ipak,{RUNTIME_ZONE_NAME}"
                in (ZONE_SOURCE_DIR / f"{RUNTIME_ZONE_NAME}.zone").read_text(encoding="utf-8", errors="replace")
            ),
            "fx_load_zone_source": str(ZONE_SOURCE_DIR / f"{BO3_FX_LOAD_ZONE_NAME}.zone"),
        },
        "deploy_mode": {
            "to_mod": DEPLOY_TO_MOD,
            "to_base": DEPLOY_TO_BASE,
            "allow_stripped_survival_ff": ALLOW_STRIPPED_SURVIVAL_FF,
            "stub_zm_viewhands": STUB_ZM_VIEWHANDS,
            "use_custom_idg_viewhands": use_custom_idg_viewhands(),
            "force_low_handmodel": FORCE_LOW_HANDMODEL,
            "use_bo3_raw_fx": USE_BO3_RAW_FX,
            "use_dedicated_bo3_fx_load_ff": USE_DEDICATED_BO3_FX_LOAD,
            "bo3_fx_load_zone": BO3_FX_LOAD_ZONE_NAME,
            "raw_fx_stage": RAW_FX_STAGE,
            "raw_fx_strict": RAW_FX_STRICT,
            "use_bo3_servant_client_fx": clientscript_override_enabled(),
            "skip_loose_image_deploy": SKIP_LOOSE_IMAGE_DEPLOY,
            "skip_script_sync": SKIP_SCRIPT_SYNC,
            "gun_model_mode": GUN_MODEL_MODE,
            "custom_model_asset": MODEL_ASSET if uses_custom_model() else None,
        },
        "deployed_to": [
            *([str(GAME_MOD_ZONE_DIR), str(STORAGE_MOD_ZONE_DIR)] if DEPLOY_TO_MOD else []),
            *([str(BASE_ZONE_DIR)] if DEPLOY_TO_BASE else []),
            str(STORAGE_MOD_SCRIPT_DIR),
            str(STORAGE_MOD_CLIENTSCRIPT_DIR),
        ],
        "deployed_outputs": {
            str(target): {
                RUNTIME_FF_NAME: collect_output_meta(target / RUNTIME_FF_NAME),
                RUNTIME_IPAK_NAME: collect_output_meta(target / RUNTIME_IPAK_NAME),
                BO3_FX_LOAD_FF_NAME: collect_output_meta(target / BO3_FX_LOAD_FF_NAME),
                BO3_FX_LOAD_IPAK_NAME: collect_output_meta(target / BO3_FX_LOAD_IPAK_NAME),
            }
            for target in deployed_output_targets()
        },
        "current_blocker": (
            "This build isolates shell and gun-model selection independently. "
            "If the same crash reproduces across shell/model permutations, the failure is outside simple weapondef override priority."
        ),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote debug report -> {REPORT_PATH}")


def main() -> int:
    verify_t6_oat_binary_architectures()
    reset_work_dirs()
    clean_output_artifacts()
    render_probe_script()
    if clientscript_override_enabled():
        render_probe_clientscripts()
    stage_model()
    stage_custom_idg_viewhands_asset()
    stage_bridge_viewhands_asset()
    stage_stub_zm_viewhands_assets()
    stage_weapon()
    stage_bo3_servant_fx()
    stage_materials()
    stage_client_probe_runtime_dependencies()
    write_probe_watchlist()
    verify_servant_clientscript_fx_manifest_alignment()
    verify_safe_full_servant_surface_contract()
    verify_full_servant_probe_isolation()
    if USE_BO3_IDG_ANIMS:
        convert_anim_bins_to_exports()
        rebake_bo3_xanim_exports()
    write_zone_source()
    write_fx_load_zone_source()
    sync_zone_raw_mirror()
    if USE_BO3_IDG_ANIMS:
        compile_mod_load()
    if using_dedicated_bo3_fx_load_lane():
        verify_custom_linker_contract_probe()
        build_dedicated_bo3_fx_load_ff()
        verify_dedicated_bo3_fx_load_ff()
    build_runtime_ff()
    verify_runtime_ff_safety()
    verify_runtime_ipak()
    deploy_outputs()
    verify_deployed_output_hashes()
    build_debug_report()
    print("Apothicon Servant build complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
