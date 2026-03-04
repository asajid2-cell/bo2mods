"""Wire thundergun animations into weapon files and zone source."""
import shutil
from pathlib import Path

ROOT = Path(r"z:\Games\pluto_t6_full_game")
WORK = ROOT / "_build/panzer_work/so_zsurvival_zm_transit"
XANIM_SRC = ROOT / "_build/asset_port_pipeline/thundergun_e2e/integration_ready/thundergun_town_full/zone_raw/thundergun_town_full/xanim_export/viewmodel"
ZONE_SRC = WORK / "zone_source/so_zsurvival_zm_transit.zone"

# All 28 thundergun animation names (matching xanim_export files)
THUNDERGUN_ANIMS = [
    "vm_thunder_gun_ads_base_down",
    "vm_thunder_gun_ads_base_up",
    "vm_thunder_gun_crawl_b",
    "vm_thunder_gun_crawl_f",
    "vm_thunder_gun_crawl_in",
    "vm_thunder_gun_crawl_l",
    "vm_thunder_gun_crawl_out",
    "vm_thunder_gun_crawl_r",
    "vm_thunder_gun_fall",
    "vm_thunder_gun_fire",
    "vm_thunder_gun_fire_ads",
    "vm_thunder_gun_first_raise",
    "vm_thunder_gun_idle",
    "vm_thunder_gun_jump",
    "vm_thunder_gun_jump_land",
    "vm_thunder_gun_pullout",
    "vm_thunder_gun_pullout_quick",
    "vm_thunder_gun_putaway",
    "vm_thunder_gun_putaway_quick",
    "vm_thunder_gun_reload_empty",
    "vm_thunder_gun_slide_air_in",
    "vm_thunder_gun_slide_in",
    "vm_thunder_gun_slide_loop",
    "vm_thunder_gun_slide_out",
    "vm_thunder_gun_sprint_in",
    "vm_thunder_gun_sprint_loop",
    "vm_thunder_gun_sprint_out",
    "vm_thunder_gun_walk_f",
]

# Field-specific replacements (applied first, order matters)
# These override general replacements for specific weapon file fields
FIELD_SPECIFIC = [
    (r"quickRaiseAnim\viewmodel_raygun_t6_pullout", r"quickRaiseAnim\vm_thunder_gun_pullout_quick"),
    (r"quickDropAnim\viewmodel_raygun_t6_putaway", r"quickDropAnim\vm_thunder_gun_putaway_quick"),
    (r"adsFireAnim\viewmodel_raygun_t6_fire", r"adsFireAnim\vm_thunder_gun_fire_ads"),
    (r"adsLastShotAnim\viewmodel_raygun_t6_fire", r"adsLastShotAnim\vm_thunder_gun_fire_ads"),
]

# General raygun -> thundergun animation name replacements
GENERAL_REPLACEMENTS = [
    ("viewmodel_raygun_t6_crawl_forward", "vm_thunder_gun_crawl_f"),
    ("viewmodel_raygun_t6_crawl_back", "vm_thunder_gun_crawl_b"),
    ("viewmodel_raygun_t6_crawl_right", "vm_thunder_gun_crawl_r"),
    ("viewmodel_raygun_t6_crawl_left", "vm_thunder_gun_crawl_l"),
    ("viewmodel_raygun_t6_crawl_in", "vm_thunder_gun_crawl_in"),
    ("viewmodel_raygun_t6_crawl_out", "vm_thunder_gun_crawl_out"),
    ("viewmodel_raygun_t6_first_raise", "vm_thunder_gun_first_raise"),
    ("viewmodel_raygun_t6_sprint_in", "vm_thunder_gun_sprint_in"),
    ("viewmodel_raygun_t6_sprint_loop", "vm_thunder_gun_sprint_loop"),
    ("viewmodel_raygun_t6_sprint_out", "vm_thunder_gun_sprint_out"),
    ("viewmodel_raygun_t6_ads_up", "vm_thunder_gun_ads_base_up"),
    ("viewmodel_raygun_t6_ads_down", "vm_thunder_gun_ads_base_down"),
    ("viewmodel_raygun_t6_d2p_in", "vm_thunder_gun_slide_in"),
    ("viewmodel_raygun_t6_d2p_loop", "vm_thunder_gun_slide_loop"),
    ("viewmodel_raygun_t6_d2p_out", "vm_thunder_gun_slide_out"),
    ("viewmodel_raygun_t6_idle", "vm_thunder_gun_idle"),
    ("viewmodel_raygun_t6_fire", "vm_thunder_gun_fire"),
    ("viewmodel_raygun_t6_reload", "vm_thunder_gun_reload_empty"),
    ("viewmodel_raygun_t6_pullout", "vm_thunder_gun_pullout"),
    ("viewmodel_raygun_t6_putaway", "vm_thunder_gun_putaway"),
]


def stage_xanim_exports():
    """Copy xanim_export files to work directory."""
    dest = WORK / "xanim_export" / "viewmodel"
    dest.mkdir(parents=True, exist_ok=True)

    count = 0
    for name in THUNDERGUN_ANIMS:
        src = XANIM_SRC / f"{name}.xanim_export"
        dst = dest / f"{name}.xanim_export"
        if src.exists():
            shutil.copy2(str(src), str(dst))
            count += 1
        else:
            print(f"  WARNING: Missing {src.name}")

    print(f"Staged {count}/{len(THUNDERGUN_ANIMS)} xanim_export files")
    return count


def update_weapon_file(path: Path):
    """Replace raygun animation references with thundergun ones."""
    data = path.read_text(encoding="utf-8")
    original = data

    # Apply field-specific replacements first
    for old, new in FIELD_SPECIFIC:
        data = data.replace(old, new)

    # Apply general replacements
    for old, new in GENERAL_REPLACEMENTS:
        data = data.replace(old, new)

    # Verify no raygun anim refs remain
    remaining = data.count("viewmodel_raygun_t6_")
    if remaining > 0:
        print(f"  WARNING: {remaining} raygun anim refs still in {path.name}")
        # Find them
        parts = data.split("\\")
        for i, p in enumerate(parts):
            if "viewmodel_raygun_t6_" in p:
                field = parts[i-1] if i > 0 else "?"
                print(f"    field={field} value={p}")

    changes = sum(1 for a, b in zip(original.split("\\"), data.split("\\")) if a != b)
    path.write_text(data, encoding="utf-8")
    print(f"  Updated {path.name}: {changes} fields changed, {remaining} raygun refs remaining")


def update_zone_source():
    """Add xanim entries to zone source."""
    data = ZONE_SRC.read_text(encoding="utf-8")

    # Check if xanim entries already exist
    if "vm_thunder_gun_" in data:
        print("  xanim entries already present in zone source, skipping")
        return

    # Build xanim block
    lines = ["\n// --- Thundergun animations ---"]
    for name in THUNDERGUN_ANIMS:
        lines.append(f"xanim,,{name}")

    block = "\n".join(lines) + "\n"

    # Append after the last thundergun image entry
    marker = "image,i_wpn_t7_zmb_hd_thundergun_stock_n"
    if marker in data:
        data = data.replace(marker, marker + block)
    else:
        # Fallback: append at end
        data += block

    ZONE_SRC.write_text(data, encoding="utf-8")
    print(f"  Added {len(THUNDERGUN_ANIMS)} xanim entries to zone source")


def main():
    print("=== Wiring Thundergun Animations ===\n")

    print("1. Staging xanim_export files...")
    stage_xanim_exports()

    print("\n2. Updating weapon files...")
    for name in ["thundergun_zm", "thundergun_upgraded_zm"]:
        wpn_path = WORK / "weapons" / name
        if wpn_path.exists():
            update_weapon_file(wpn_path)
        else:
            print(f"  ERROR: {wpn_path} not found!")

    print("\n3. Updating zone source...")
    update_zone_source()

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
