#!/usr/bin/env python3
"""Revert thundergun weapon files back to minigun animations (known working)."""
import re
import os

WEAPONS_DIR = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\weapons"

# Revert to minigun animations (the known working state)
ANIM_MAP = {
    'idleAnim': 'viewmodel_minigun_t6_idle',
    'emptyIdleAnim': 'viewmodel_minigun_t6_idle',
    'fireAnim': 'viewmodel_minigun_t6_fire',
    'lastShotAnim': 'viewmodel_minigun_t6_fire',
    'adsFireAnim': 'viewmodel_minigun_t6_fire',
    'adsLastShotAnim': 'viewmodel_minigun_t6_fire',
    'reloadAnim': 'viewmodel_minigun_t6_idle',
    'reloadEmptyAnim': 'viewmodel_minigun_t6_idle',
    'raiseAnim': 'viewmodel_minigun_t6_pullout',
    'dropAnim': 'viewmodel_minigun_t6_putaway',
    'firstRaiseAnim': 'viewmodel_minigun_t6_pullout',
    'altRaiseAnim': 'viewmodel_minigun_t6_pullout',
    'altDropAnim': 'viewmodel_minigun_t6_putaway',
    'quickRaiseAnim': 'viewmodel_minigun_t6_pullout_quick',
    'quickDropAnim': 'viewmodel_minigun_t6_putaway_quick',
    'emptyRaiseAnim': 'viewmodel_minigun_t6_pullout',
    'emptyDropAnim': 'viewmodel_minigun_t6_putaway',
    'sprintInAnim': 'viewmodel_minigun_t6_sprint_in',
    'sprintLoopAnim': 'viewmodel_minigun_t6_sprint_loop',
    'sprintOutAnim': 'viewmodel_minigun_t6_sprint_out',
    'adsUpAnim': 'viewmodel_minigun_t6_ads_up',
    'adsDownAnim': 'viewmodel_minigun_t6_ads_down',
    # Clear crawl and DTP back to empty
    'crawlInAnim': '',
    'crawlForwardAnim': '',
    'crawlBackAnim': '',
    'crawlRightAnim': '',
    'crawlLeftAnim': '',
    'crawlOutAnim': '',
    'crawlEmptyInAnim': '',
    'dtp_in': '',
    'dtp_loop': '',
    'dtp_out': '',
}


def set_weapon_field(content, field, new_value):
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
    with open(path, 'w') as f:
        f.write(content)
    print(f"  {changed} fields changed. Saved.")


def main():
    for weapon_name in ['rogue_thundergun_zm', 'rogue_thundergun_upgraded_zm']:
        path = os.path.join(WEAPONS_DIR, weapon_name)
        if os.path.exists(path):
            update_weapon(path)
    print("\nDone! Reverted to minigun animations.")


if __name__ == "__main__":
    main()
