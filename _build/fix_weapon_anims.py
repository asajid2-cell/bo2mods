#!/usr/bin/env python3
"""Replace raygun animations with proper thundergun animations in weapon files."""
import shutil
from pathlib import Path

# Animation name mapping (longer strings first to avoid partial matches)
ANIM_MAP = [
    # ADS fire must come before regular fire
    ("viewmodel_raygun_t6_fire_ads", "vm_thunder_gun_fire_ads"),
    ("viewmodel_raygun_t6_fire", "vm_thunder_gun_fire"),
    # Quick variants before regular
    ("viewmodel_raygun_t6_pullout_quick", "vm_thunder_gun_pullout_quick"),
    ("viewmodel_raygun_t6_putaway_quick", "vm_thunder_gun_putaway_quick"),
    ("viewmodel_raygun_t6_pullout", "vm_thunder_gun_pullout"),
    ("viewmodel_raygun_t6_putaway", "vm_thunder_gun_putaway"),
    # Other animations
    ("viewmodel_raygun_t6_idle", "vm_thunder_gun_idle"),
    ("viewmodel_raygun_t6_reload", "vm_thunder_gun_reload_empty"),
    ("viewmodel_raygun_t6_first_raise", "vm_thunder_gun_first_raise"),
    ("viewmodel_raygun_t6_sprint_in", "vm_thunder_gun_sprint_in"),
    ("viewmodel_raygun_t6_sprint_loop", "vm_thunder_gun_sprint_loop"),
    ("viewmodel_raygun_t6_sprint_out", "vm_thunder_gun_sprint_out"),
    # Crawl animations (raygun uses _forward/_back, thundergun uses _f/_b)
    ("viewmodel_raygun_t6_crawl_forward", "vm_thunder_gun_crawl_f"),
    ("viewmodel_raygun_t6_crawl_back", "vm_thunder_gun_crawl_b"),
    ("viewmodel_raygun_t6_crawl_right", "vm_thunder_gun_crawl_r"),
    ("viewmodel_raygun_t6_crawl_left", "vm_thunder_gun_crawl_l"),
    ("viewmodel_raygun_t6_crawl_in", "vm_thunder_gun_crawl_in"),
    ("viewmodel_raygun_t6_crawl_out", "vm_thunder_gun_crawl_out"),
    # ADS up/down
    ("viewmodel_raygun_t6_ads_up", "vm_thunder_gun_ads_base_up"),
    ("viewmodel_raygun_t6_ads_down", "vm_thunder_gun_ads_base_down"),
    # Dive-to-prone -> slide (closest thundergun equivalent)
    ("viewmodel_raygun_t6_d2p_in", "vm_thunder_gun_slide_in"),
    ("viewmodel_raygun_t6_d2p_loop", "vm_thunder_gun_slide_loop"),
    ("viewmodel_raygun_t6_d2p_out", "vm_thunder_gun_slide_out"),
]


def fix_weapon_file(weapon_path: Path):
    """Replace raygun anim names with thundergun anim names."""
    # Backup
    bak = weapon_path.with_suffix(".weapon_raygun_anims_bak")
    if not bak.exists():
        shutil.copy2(weapon_path, bak)
        print(f"  Backed up to {bak.name}")

    data = weapon_path.read_text(encoding="ascii")
    total_replacements = 0

    for old, new in ANIM_MAP:
        count = data.count(old)
        if count > 0:
            data = data.replace(old, new)
            total_replacements += count
            print(f"  {old} -> {new} ({count}x)")

    weapon_path.write_text(data, encoding="ascii")
    print(f"  Total: {total_replacements} replacements")

    # Verify no raygun references remain
    remaining = data.count("viewmodel_raygun_t6_")
    if remaining:
        print(f"  WARNING: {remaining} raygun references still remain!")
        import re
        for m in re.finditer(r"viewmodel_raygun_t6_\w+", data):
            print(f"    Remaining: {m.group()}")
    else:
        print(f"  All raygun animation references replaced!")


def main():
    weapons_dir = Path(r"z:\Games\pluto_t6_full_game\mods\zm_roguelike_panzer\weapons")

    for name in ["thundergun_zm", "thundergun_upgraded_zm"]:
        weapon_path = weapons_dir / name
        if weapon_path.exists():
            print(f"\nProcessing {name}:")
            fix_weapon_file(weapon_path)
        else:
            print(f"\n{name}: NOT FOUND")


if __name__ == "__main__":
    main()
