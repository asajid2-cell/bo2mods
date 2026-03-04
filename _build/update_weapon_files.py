#!/usr/bin/env python3
"""Update thundergun weapon files: add effects, differentiate upgraded variant."""
import re
import os

WEAPONS_DIR = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\weapons"


def set_weapon_field(content, field, new_value):
    """Replace a field's value in a T6 weapon file (backslash-separated)."""
    # In the file: \field\value\nextfield
    # We match: \field\ then capture everything until the next \
    escaped_field = re.escape(field)
    pattern = re.compile(r'\\' + escaped_field + r'\\([^\\]*)')
    match = pattern.search(content)
    if match:
        old_val = match.group(1)
        replacement = '\\' + field + '\\' + new_value
        content = content[:match.start()] + replacement + content[match.end():]
        return content, old_val
    return content, None


def main():
    # ---- BASE WEAPON ----
    base_path = os.path.join(WEAPONS_DIR, "rogue_thundergun_zm")
    with open(base_path, 'r') as f:
        base = f.read()

    print("=== BASE WEAPON (rogue_thundergun_zm) ===")

    base_changes = {
        'viewFlashEffect': 'weapon/muzzleflashes/fx_raygun_view',
        'worldFlashEffect': 'weapon/muzzleflashes/fx_raygun_world',
    }

    for field, new_val in base_changes.items():
        base, old = set_weapon_field(base, field, new_val)
        print(f"  {field}: '{old}' -> '{new_val}'")

    with open(base_path, 'w') as f:
        f.write(base)
    print("  Saved.\n")

    # ---- UPGRADED WEAPON ----
    upg_path = os.path.join(WEAPONS_DIR, "rogue_thundergun_upgraded_zm")
    with open(upg_path, 'r') as f:
        upg = f.read()

    print("=== UPGRADED WEAPON (rogue_thundergun_upgraded_zm) ===")

    upg_changes = {
        'displayName': 'WEAPON_THUNDERGUN_UPGRADED',
        'viewFlashEffect': 'weapon/muzzleflashes/fx_raygun_view',
        'worldFlashEffect': 'weapon/muzzleflashes/fx_raygun_world',
        'maxAmmo': '24',
        'clipSize': '4',
        'damage': '2000',
        'fireTime': '0.5',
        'startAmmo': '200',
    }

    for field, new_val in upg_changes.items():
        upg, old = set_weapon_field(upg, field, new_val)
        print(f"  {field}: '{old}' -> '{new_val}'")

    with open(upg_path, 'w') as f:
        f.write(upg)
    print("  Saved.\n")

    print("Done! Both weapon files updated.")


if __name__ == "__main__":
    main()
