"""Blank out all vm_thunder_gun_* animation references in weapon files."""
import re, os

WEAPONS_DIR = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\weapons"

for wf in ['thundergun_zm', 'thundergun_upgraded_zm']:
    path = os.path.join(WEAPONS_DIR, wf)
    with open(path, 'r') as f:
        data = f.read()

    # The weapon file is backslash-delimited: key\value\key\value
    # We want to replace \vm_thunder_gun_xxx with \ (empty value, keep separator)
    pattern = r'\\vm_thunder_gun_[a-z0-9_]+'
    matches = re.findall(pattern, data)
    new_data = re.sub(pattern, r'\\', data)

    with open(path, 'w') as f:
        f.write(new_data)

    print(f"{wf}: blanked {len(matches)} animation references")
    for m in matches:
        print(f"  {m[1:]}")  # strip leading backslash for display
