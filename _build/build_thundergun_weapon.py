#!/usr/bin/env python3
"""Build thundergun weapon files from vanilla minigun base + thundergun gameplay.

Strategy: Start from vanilla minigun weapon (which has animation refs that resolve
to existing loaded assets), override ALL non-animation fields with thundergun values,
and set gunModel/worldModel to our custom thundergun models.

This avoids the garbling caused by references to non-existent xanim assets.
"""
import argparse
import os
import re
import sys

MINIGUN_WPN = r"z:\Games\pluto_t6_full_game\_build\runtime_unlink_zm_transit_full_1\weapons\ak74u_zm"
THUNDERGUN_WPN_BAK = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\weapons\rogue_thundergun_zm.bak_tg"
OUTPUT_WPN = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\weapons\rogue_thundergun_zm"
OUTPUT_WPN_UPG = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\weapons\rogue_thundergun_upgraded_zm"
OUTPUT_WPN_STOCK = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\weapons\thundergun_zm"
OUTPUT_WPN_STOCK_UPG = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\weapons\thundergun_upgraded_zm"
OUTPUT_WPN_PROBE = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\weapons\rogue_probe_wpn_zm"
OUTPUT_WPN_PROBE_UPG = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\weapons\rogue_probe_wpn_upgraded_zm"
OUTPUT_WEAPONS_DIR = os.path.dirname(OUTPUT_WPN_STOCK)

# All animation-related field names in T6 weapon files.
# These fields reference xanim asset names — we KEEP the minigun values
# because those resolve to real assets already loaded in the game.
ANIM_FIELDS = {
    "idleAnim", "idleAnimLeft", "emptyIdleAnim", "emptyIdleAnimLeft",
    "fireIntroAnim", "fireAnim", "fireAnimLeft", "holdFireAnim",
    "lastShotAnim", "lastShotAnimLeft", "flourishAnim", "flourishAnimLeft",
    "detonateAnim", "rechamberAnim",
    "meleeAnim", "meleeAnimEmpty", "meleeAnim1", "meleeAnim2", "meleeAnim3",
    "meleeChargeAnim", "meleeChargeAnimEmpty",
    "reloadAnim", "reloadAnimRight", "reloadAnimLeft",
    "reloadEmptyAnim", "reloadEmptyAnimLeft",
    "reloadStartAnim", "reloadEndAnim",
    "reloadQuickAnim", "reloadQuickEmptyAnim",
    "raiseAnim", "dropAnim", "firstRaiseAnim",
    "altRaiseAnim", "altDropAnim",
    "quickRaiseAnim", "quickDropAnim",
    "emptyRaiseAnim", "emptyDropAnim",
    "sprintInAnim", "sprintLoopAnim", "sprintOutAnim",
    "sprintInEmptyAnim", "sprintLoopEmptyAnim", "sprintOutEmptyAnim",
    "lowReadyInAnim", "lowReadyLoopAnim", "lowReadyOutAnim",
    "contFireInAnim", "contFireLoopAnim", "contFireOutAnim",
    "crawlInAnim", "crawlForwardAnim", "crawlBackAnim",
    "crawlRightAnim", "crawlLeftAnim", "crawlOutAnim",
    "crawlEmptyInAnim", "crawlEmptyForwardAnim", "crawlEmptyBackAnim",
    "crawlEmptyRightAnim", "crawlEmptyLeftAnim", "crawlEmptyOutAnim",
    "deployAnim", "nightVisionWearAnim", "nightVisionRemoveAnim",
    "adsFireAnim", "adsLastShotAnim", "adsRechamberAnim",
    "adsUpAnim", "adsDownAnim", "adsUpOtherScopeAnim", "adsFireIntroAnim",
    "breakdownAnim",
    "dtp_in", "dtp_loop", "dtp_out",
    "dtp_empty_in", "dtp_empty_loop", "dtp_empty_out",
    "slide_in", "mantleAnim",
    "sprintCameraAnim", "dtpInCameraAnim", "dtpLoopCameraAnim",
    "dtpOutCameraAnim", "mantleCameraAnim",
}

# Fields to force-clear.
# Keep empty by default so semantic donor fields (handModel/parentWeaponName/camo)
# are preserved when --semantics thundergun is selected.
FORCE_CLEAR = set()

def get_force_set(model_mode, gun_model_override=None, world_model_override=None):
    force = {}
    if model_mode == "base":
        # Keep donor weapon fields untouched for pure donor-clone probing.
        return force

    force["displayName"] = "WEAPON_THUNDERGUN"
    force["playerAnimType"] = "default"
    if model_mode == "minigun":
        # Diagnostic mode: keep rogue weapon name but use known-good BO2 minigun models.
        force["gunModel"] = "t6_wpn_minigun_view"
        force["worldModel"] = "t6_wpn_minigun_world"
    else:
        force["gunModel"] = "rogue_tg_view"
        force["worldModel"] = "rogue_tg_world"

    if gun_model_override is not None and gun_model_override != "":
        force["gunModel"] = gun_model_override
    if world_model_override is not None and world_model_override != "":
        force["worldModel"] = world_model_override
    return force

SAFE_ANIMS = {
    "idle": "viewmodel_minigun_t6_idle",
    "fire": "viewmodel_minigun_t6_fire",
    "pullout": "viewmodel_minigun_t6_pullout",
    "putaway": "viewmodel_minigun_t6_putaway",
    "pullout_quick": "viewmodel_minigun_t6_pullout_quick",
    "putaway_quick": "viewmodel_minigun_t6_putaway_quick",
    "sprint_in": "viewmodel_minigun_t6_sprint_in",
    "sprint_loop": "viewmodel_minigun_t6_sprint_loop",
    "sprint_out": "viewmodel_minigun_t6_sprint_out",
    "ads_up": "viewmodel_minigun_t6_ads_up",
    "ads_down": "viewmodel_minigun_t6_ads_down",
}

# BO3 thundergun names for a controlled core-state pass.
CORE_BO3_FIELDS = {
    "idleAnim": "vm_thunder_gun_idle",
    "emptyIdleAnim": "vm_thunder_gun_idle",
    "fireAnim": "vm_thunder_gun_fire",
    "lastShotAnim": "vm_thunder_gun_fire",
    "adsFireAnim": "vm_thunder_gun_fire_ads",
    "adsLastShotAnim": "vm_thunder_gun_fire_ads",
    "reloadAnim": "vm_thunder_gun_reload_empty",
    "reloadEmptyAnim": "vm_thunder_gun_reload_empty",
    "raiseAnim": "vm_thunder_gun_pullout",
    "dropAnim": "vm_thunder_gun_putaway",
    "firstRaiseAnim": "vm_thunder_gun_first_raise",
    "altRaiseAnim": "vm_thunder_gun_pullout",
    "altDropAnim": "vm_thunder_gun_putaway",
    "quickRaiseAnim": "vm_thunder_gun_pullout_quick",
    "quickDropAnim": "vm_thunder_gun_putaway_quick",
    "emptyRaiseAnim": "vm_thunder_gun_pullout",
    "emptyDropAnim": "vm_thunder_gun_putaway",
    "adsUpAnim": "vm_thunder_gun_ads_base_up",
    "adsDownAnim": "vm_thunder_gun_ads_base_down",
    # Movement/transition states: remove donor N/A refs and force vm_thunder_gun_*.
    "sprintInAnim": "vm_thunder_gun_sprint_in",
    "sprintLoopAnim": "vm_thunder_gun_sprint_loop",
    "sprintOutAnim": "vm_thunder_gun_sprint_out",
    "crawlInAnim": "vm_thunder_gun_crawl_in",
    "crawlForwardAnim": "vm_thunder_gun_crawl_f",
    "crawlBackAnim": "vm_thunder_gun_crawl_b",
    "crawlRightAnim": "vm_thunder_gun_crawl_r",
    "crawlLeftAnim": "vm_thunder_gun_crawl_l",
    "crawlOutAnim": "vm_thunder_gun_crawl_out",
    "dtp_in": "vm_thunder_gun_slide_in",
    "dtp_loop": "vm_thunder_gun_slide_loop",
    "dtp_out": "vm_thunder_gun_slide_out",
    "slide_in": "vm_thunder_gun_slide_in",
}

IDLE_BO3_FIELDS = {
    "idleAnim": "vm_thunder_gun_idle",
    "emptyIdleAnim": "vm_thunder_gun_idle",
}


def parse_weapon(path):
    """Parse T6 weapon file into ordered list of (key, value) pairs."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read().strip()
    parts = data.split("\\")
    if parts[0] != "WEAPONFILE":
        raise ValueError(f"Not a weapon file: {path}")
    pairs = []
    i = 1
    while i + 1 < len(parts):
        pairs.append((parts[i], parts[i + 1]))
        i += 2
    return pairs


def build_weapon(base_pairs, override_pairs, semantics_mode, force_set):
    """Build merged weapon from minigun base with selectable non-anim semantics.

    semantics_mode:
      - "thundergun": copy non-animation fields from thundergun donor
      - "minigun": keep non-animation fields from minigun base
    """
    # Index override values by field name
    override_map = {}
    for k, v in override_pairs:
        override_map[k] = v

    # Build result using base structure (preserves field order)
    result = []
    seen = set()
    for k, v in base_pairs:
        seen.add(k)
        if k in force_set:
            result.append((k, force_set[k]))
        elif k in FORCE_CLEAR:
            result.append((k, ""))
        elif k in ANIM_FIELDS:
            # Keep base (minigun) animation reference
            result.append((k, v))
        elif semantics_mode == "thundergun" and k in override_map:
            # Use thundergun gameplay value
            result.append((k, override_map[k]))
        else:
            # Keep base value
            result.append((k, v))

    # Check for thundergun fields not in minigun (add them if non-animation)
    added = 0
    if semantics_mode == "thundergun":
        for k, v in override_pairs:
            if k not in seen and k not in ANIM_FIELDS and k not in FORCE_CLEAR:
                if k in force_set:
                    result.append((k, force_set[k]))
                else:
                    result.append((k, v))
                added += 1
    if added:
        print(f"  Added {added} fields from thundergun not present in minigun base")

    return result


def serialize_weapon(pairs):
    """Serialize weapon pairs back to T6 format."""
    parts = ["WEAPONFILE"]
    for k, v in pairs:
        parts.append(k)
        parts.append(v)
    return "\\".join(parts)


def _is_safe_weapon_alias(alias):
    return bool(re.match(r"^[A-Za-z0-9_]+$", alias or ""))


def _pick_safe_anim(field_name):
    f = field_name.lower()
    if "sprintin" in f:
        return SAFE_ANIMS["sprint_in"]
    if "sprintloop" in f:
        return SAFE_ANIMS["sprint_loop"]
    if "sprintout" in f:
        return SAFE_ANIMS["sprint_out"]
    if "adsup" in f:
        return SAFE_ANIMS["ads_up"]
    if "adsdown" in f:
        return SAFE_ANIMS["ads_down"]
    if "quickraise" in f:
        return SAFE_ANIMS["pullout_quick"]
    if "quickdrop" in f:
        return SAFE_ANIMS["putaway_quick"]
    if "raise" in f:
        return SAFE_ANIMS["pullout"]
    if "drop" in f:
        return SAFE_ANIMS["putaway"]
    if "fire" in f:
        return SAFE_ANIMS["fire"]
    if "lastshot" in f:
        return SAFE_ANIMS["fire"]
    # Everything else should stay safe and non-null.
    return SAFE_ANIMS["idle"]


def fill_empty_anim_fields(pairs):
    """Force-fill empty anim fields with safe existing minigun anim refs."""
    out = []
    filled = 0
    for k, v in pairs:
        if k in ANIM_FIELDS and not v:
            out.append((k, _pick_safe_anim(k)))
            filled += 1
        else:
            out.append((k, v))
    return out, filled


def apply_probe_profile(pairs):
    """Map states to visibly distinct but safe minigun clips for state-path probing."""
    out = []
    changed = 0

    def probe_for(k):
        f = k.lower()
        if "adsup" in f:
            return SAFE_ANIMS["ads_up"]
        if "adsdown" in f:
            return SAFE_ANIMS["ads_down"]
        if "ads" in f and "fire" in f:
            return SAFE_ANIMS["fire"]
        if "sprintin" in f:
            return SAFE_ANIMS["sprint_in"]
        if "sprintloop" in f:
            return SAFE_ANIMS["sprint_loop"]
        if "sprintout" in f:
            return SAFE_ANIMS["sprint_out"]
        if "crawl" in f:
            return SAFE_ANIMS["sprint_loop"]
        if "slide" in f or "dtp" in f or "mantle" in f:
            return SAFE_ANIMS["pullout_quick"]
        if "reload" in f:
            return SAFE_ANIMS["putaway"]
        if "raise" in f:
            return SAFE_ANIMS["pullout"]
        if "drop" in f or "putaway" in f:
            return SAFE_ANIMS["putaway"]
        if "quickraise" in f:
            return SAFE_ANIMS["pullout_quick"]
        if "quickdrop" in f:
            return SAFE_ANIMS["putaway_quick"]
        if "fire" in f or "shot" in f:
            return SAFE_ANIMS["fire"]
        return SAFE_ANIMS["idle"]

    for k, v in pairs:
        if k in ANIM_FIELDS:
            nv = probe_for(k)
            if nv != v:
                changed += 1
            out.append((k, nv))
        else:
            out.append((k, v))
    return out, changed


def apply_hybrid_core_profile(pairs):
    """Apply BO3 thundergun refs to core weapon states; keep safe fallbacks for everything else."""
    out = []
    changed = 0
    for k, v in pairs:
        if k in CORE_BO3_FIELDS:
            nv = CORE_BO3_FIELDS[k]
            if nv != v:
                changed += 1
            out.append((k, nv))
        else:
            out.append((k, v))
    return out, changed


def apply_hybrid_idle_profile(pairs):
    """Apply BO3 thundergun refs only to idle states; keep safe minigun fallbacks for everything else."""
    out = []
    changed = 0
    for k, v in pairs:
        if k in IDLE_BO3_FIELDS:
            nv = IDLE_BO3_FIELDS[k]
            if nv != v:
                changed += 1
            out.append((k, nv))
        else:
            out.append((k, v))
    return out, changed


def apply_optional_field_overrides(
    pairs,
    ammo_name=None,
    clip_name=None,
    hud_icon=None,
    kill_icon=None,
    hand_model=None,
    clear_camo=False,
):
    out = []
    changed = 0
    for k, v in pairs:
        if k == "ammoName" and ammo_name is not None:
            if v != ammo_name:
                changed += 1
            out.append((k, ammo_name))
        elif k == "clipName" and clip_name is not None:
            if v != clip_name:
                changed += 1
            out.append((k, clip_name))
        elif k == "hudIcon" and hud_icon is not None:
            if v != hud_icon:
                changed += 1
            out.append((k, hud_icon))
        elif k == "ammoCounterIcon" and hud_icon is not None:
            if v != hud_icon:
                changed += 1
            out.append((k, hud_icon))
        elif k == "killIcon" and kill_icon is not None:
            if v != kill_icon:
                changed += 1
            out.append((k, kill_icon))
        elif k == "handModel" and hand_model is not None:
            if v != hand_model:
                changed += 1
            out.append((k, hand_model))
        elif k == "camo" and clear_camo:
            if v != "":
                changed += 1
            out.append((k, ""))
        else:
            out.append((k, v))
    return out, changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        choices=["stable", "probe", "hybrid_core", "hybrid_idle"],
        default="stable",
        help=(
            "stable: safe minigun refs + fill empties; "
            "probe: visibly distinct safe refs by state; "
            "hybrid_core: BO3 refs for core gun states, safe fallback for movement; "
            "hybrid_idle: BO3 refs only for idle states."
        ),
    )
    parser.add_argument(
        "--semantics",
        choices=["minigun", "thundergun"],
        default="minigun",
        help=(
            "minigun: keep non-animation semantics from minigun base (recommended for stability); "
            "thundergun: copy non-animation semantics from thundergun donor."
        ),
    )
    parser.add_argument(
        "--model-mode",
        choices=["rogue", "minigun", "base"],
        default="rogue",
        help=(
            "rogue: use BO3-ported rogue_tg_view/world models; "
            "minigun: diagnostic mode using known-good BO2 minigun models; "
            "base: keep donor weapon models/identity fields untouched."
        ),
    )
    parser.add_argument(
        "--base-weapon-path",
        default=MINIGUN_WPN,
        help="Path to base T6 weapon file used as structural/semantic donor."
    )
    parser.add_argument(
        "--ammo-name",
        default=None,
        help="Optional forced ammoName override."
    )
    parser.add_argument(
        "--clip-name",
        default=None,
        help="Optional forced clipName override."
    )
    parser.add_argument(
        "--hud-icon",
        default=None,
        help="Optional forced hudIcon/ammoCounterIcon override."
    )
    parser.add_argument(
        "--kill-icon",
        default=None,
        help="Optional forced killIcon override."
    )
    parser.add_argument(
        "--hand-model",
        default=None,
        help="Optional forced handModel override (e.g. viewmodel_usa_no_model).",
    )
    parser.add_argument(
        "--gun-model",
        default=None,
        help="Optional forced gunModel override (e.g. viewmodel_usa_no_model).",
    )
    parser.add_argument(
        "--world-model",
        default=None,
        help="Optional forced worldModel override.",
    )
    parser.add_argument(
        "--clear-camo",
        action="store_true",
        help="Force camo field to empty string."
    )
    parser.add_argument(
        "--truth-alias",
        default=None,
        help="Optional extra output alias name to overwrite a known grantable weapon (e.g. ak74u_zm).",
    )
    parser.add_argument(
        "--truth-alias-upg",
        default=None,
        help="Optional upgraded alias paired with --truth-alias (e.g. ak74u_upgraded_zm).",
    )
    args = parser.parse_args()

    base_weapon_path = args.base_weapon_path
    if not os.path.exists(base_weapon_path):
        raise FileNotFoundError(f"Base weapon file not found: {base_weapon_path}")

    print(f"Loading base weapon from {base_weapon_path}...")
    minigun = parse_weapon(base_weapon_path)
    print(f"  {len(minigun)} fields")

    # Use the backup of the original thundergun weapon
    tg_src = THUNDERGUN_WPN_BAK
    if not os.path.exists(tg_src):
        # Fall back to current file
        tg_src = OUTPUT_WPN
    print(f"Loading thundergun weapon from {tg_src}...")
    thundergun = parse_weapon(tg_src)
    print(f"  {len(thundergun)} fields")

    # Count animation fields in thundergun
    tg_anim_count = sum(1 for k, v in thundergun if k in ANIM_FIELDS and v)
    print(f"  Thundergun has {tg_anim_count} non-empty animation references (will be SKIPPED)")

    # Count animation fields in minigun
    mini_anim_count = sum(1 for k, v in minigun if k in ANIM_FIELDS and v)
    print(f"  Minigun has {mini_anim_count} non-empty animation references (will be KEPT)")

    print("\nBuilding merged weapon...")
    force_set = get_force_set(args.model_mode, gun_model_override=args.gun_model, world_model_override=args.world_model)
    merged = build_weapon(minigun, thundergun, args.semantics, force_set)
    merged, filled = fill_empty_anim_fields(merged)
    print(f"  Result: {len(merged)} fields")
    print(f"  Filled empty anim fields: {filled}")
    merged, forced_changed = apply_optional_field_overrides(
        merged,
        ammo_name=args.ammo_name,
        clip_name=args.clip_name,
        hud_icon=args.hud_icon,
        kill_icon=args.kill_icon,
        hand_model=args.hand_model,
        clear_camo=args.clear_camo,
    )
    if forced_changed:
        print(f"  Optional field overrides applied: {forced_changed}")
    if args.profile == "probe":
        merged, probe_changed = apply_probe_profile(merged)
        print(f"  Probe profile overrides: {probe_changed}")
    elif args.profile == "hybrid_core":
        merged, core_changed = apply_hybrid_core_profile(merged)
        print(f"  Hybrid core BO3 overrides: {core_changed}")
    elif args.profile == "hybrid_idle":
        merged, idle_changed = apply_hybrid_idle_profile(merged)
        print(f"  Hybrid idle BO3 overrides: {idle_changed}")

    # Verify: list animation fields that have values
    print("\n  Animation references in output:")
    for k, v in merged:
        if k in ANIM_FIELDS and v:
            print(f"    {k} = {v}")

    # Verify: list key gameplay overrides
    print("\n  Key gameplay fields:")
    for key in ["displayName", "gunModel", "worldModel", "playerAnimType",
                "weaponClass", "fireType", "clipSize", "maxAmmo", "damage",
                "fireTime", "ammoName", "handModel", "parentWeaponName", "camo"]:
        for k, v in merged:
            if k == key:
                print(f"    {k} = {v!r}")
                break

    data = serialize_weapon(merged)

    out_targets = [
        OUTPUT_WPN,
        OUTPUT_WPN + ".weapon",
        OUTPUT_WPN_UPG,
        OUTPUT_WPN_UPG + ".weapon",
        OUTPUT_WPN_STOCK,
        OUTPUT_WPN_STOCK + ".weapon",
        OUTPUT_WPN_STOCK_UPG,
        OUTPUT_WPN_STOCK_UPG + ".weapon",
        OUTPUT_WPN_PROBE,
        OUTPUT_WPN_PROBE + ".weapon",
        OUTPUT_WPN_PROBE_UPG,
        OUTPUT_WPN_PROBE_UPG + ".weapon",
    ]

    if args.truth_alias:
        if not _is_safe_weapon_alias(args.truth_alias):
            raise ValueError(f"Invalid --truth-alias: {args.truth_alias!r}")
        truth_base = os.path.join(OUTPUT_WEAPONS_DIR, args.truth_alias)
        out_targets.extend([truth_base, truth_base + ".weapon"])

    if args.truth_alias_upg:
        if not _is_safe_weapon_alias(args.truth_alias_upg):
            raise ValueError(f"Invalid --truth-alias-upg: {args.truth_alias_upg!r}")
        truth_upg = os.path.join(OUTPUT_WEAPONS_DIR, args.truth_alias_upg)
        out_targets.extend([truth_upg, truth_upg + ".weapon"])

    # Preserve order but avoid duplicate writes.
    seen_targets = set()
    out_targets = [t for t in out_targets if not (t in seen_targets or seen_targets.add(t))]

    for target in out_targets:
        print(f"\nWriting {target}...")
        with open(target, "w", encoding="utf-8") as f:
            f.write(data)
        print(f"  {len(data):,} bytes")

    print(
        f"\nDone! Weapon files built with profile='{args.profile}', semantics='{args.semantics}', "
        f"model_mode='{args.model_mode}', "
        f"base='{base_weapon_path}', "
        f"truth_alias='{args.truth_alias or ''}', truth_alias_upg='{args.truth_alias_upg or ''}'."
    )


if __name__ == "__main__":
    main()
