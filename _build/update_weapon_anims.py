#!/usr/bin/env python3
"""Update thundergun weapon files: switch from minigun to thundergun animations."""
import re
import os

WEAPONS_DIR = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\weapons"

# Animation mapping: weapon field -> thundergun xanim name
ANIM_MAP = {
    'idleAnim': 'vm_thunder_gun_idle',
    'emptyIdleAnim': 'vm_thunder_gun_idle',
    'fireAnim': 'vm_thunder_gun_fire',
    'lastShotAnim': 'vm_thunder_gun_fire',
    'adsFireAnim': 'vm_thunder_gun_fire_ads',
    'adsLastShotAnim': 'vm_thunder_gun_fire_ads',
    'reloadAnim': 'vm_thunder_gun_reload_empty',
    'reloadEmptyAnim': 'vm_thunder_gun_reload_empty',
    'raiseAnim': 'vm_thunder_gun_pullout',
    'dropAnim': 'vm_thunder_gun_putaway',
    'firstRaiseAnim': 'vm_thunder_gun_first_raise',
    'altRaiseAnim': 'vm_thunder_gun_pullout',
    'altDropAnim': 'vm_thunder_gun_putaway',
    'quickRaiseAnim': 'vm_thunder_gun_pullout_quick',
    'quickDropAnim': 'vm_thunder_gun_putaway_quick',
    'emptyRaiseAnim': 'vm_thunder_gun_pullout',
    'emptyDropAnim': 'vm_thunder_gun_putaway',
    'sprintInAnim': 'vm_thunder_gun_sprint_in',
    'sprintLoopAnim': 'vm_thunder_gun_sprint_loop',
    'sprintOutAnim': 'vm_thunder_gun_sprint_out',
    'adsUpAnim': 'vm_thunder_gun_ads_base_up',
    'adsDownAnim': 'vm_thunder_gun_ads_base_down',
    'crawlInAnim': 'vm_thunder_gun_crawl_in',
    'crawlForwardAnim': 'vm_thunder_gun_crawl_f',
    'crawlBackAnim': 'vm_thunder_gun_crawl_b',
    'crawlRightAnim': 'vm_thunder_gun_crawl_r',
    'crawlLeftAnim': 'vm_thunder_gun_crawl_l',
    'crawlOutAnim': 'vm_thunder_gun_crawl_out',
    'crawlEmptyInAnim': 'vm_thunder_gun_crawl_in',
    'dtp_in': 'vm_thunder_gun_slide_in',
    'dtp_loop': 'vm_thunder_gun_slide_loop',
    'dtp_out': 'vm_thunder_gun_slide_out',
}


def set_weapon_field(content, field, new_value):
    """Replace a field's value in a T6 weapon file (backslash-separated)."""
    escaped_field = re.escape(field)
    pattern = re.compile(r'\\' + escaped_field + r'\\([^\\]*)')
    match = pattern.search(content)
    if match:
        old_val = match.group(1)
        replacement = '\\' + field + '\\' + new_value
        content = content[:match.start()] + replacement + content[match.end():]
        return content, old_val
    return content, None


def update_weapon(path):
    """Update a weapon file's animation references."""
    name = os.path.basename(path)
    print(f"\n=== {name} ===")

    with open(path, 'r') as f:
        content = f.read()

    changed = 0
    for field, new_val in ANIM_MAP.items():
        content, old_val = set_weapon_field(content, field, new_val)
        if old_val is not None and old_val != new_val:
            print(f"  {field}: '{old_val}' -> '{new_val}'")
            changed += 1
        elif old_val == new_val:
            pass  # Already correct
        else:
            print(f"  {field}: NOT FOUND in weapon file")

    with open(path, 'w') as f:
        f.write(content)
    print(f"  {changed} fields changed. Saved.")


def main():
    for weapon_name in ['rogue_thundergun_zm', 'rogue_thundergun_upgraded_zm']:
        path = os.path.join(WEAPONS_DIR, weapon_name)
        if os.path.exists(path):
            update_weapon(path)
        else:
            print(f"WARNING: {path} not found!")

    print("\nDone! Both weapon files updated with thundergun animations.")


if __name__ == "__main__":
    main()
