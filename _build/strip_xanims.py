"""
Strip BO3 thundergun xanim_export files to only include bones that exist in the T6 viewmodel skeleton.
This removes the 90 incompatible bones (sleeve, wristcrease, gun tags, etc.) that cause stretching.
"""
import os
import glob
import re

# The 43 bones that exist in BOTH BO3 thundergun xanims AND T6 viewmodel skeleton
T6_MATCHING_BONES = {
    # Core chain
    "tag_torso",
    "j_shoulder_le", "j_shoulder_ri",
    "j_elbow_le", "j_elbow_ri",
    "tag_weapon",
    "j_wrist_le", "j_wrist_ri",
    "j_wristtwist_le", "j_wristtwist_ri",
    # Camera/misc
    "tag_cambone", "tag_camera", "tag_gasmask",
    # Left hand fingers (1,2,3 joints each)
    "j_thumb_le_1", "j_thumb_le_2", "j_thumb_le_3",
    "j_index_le_1", "j_index_le_2", "j_index_le_3",
    "j_mid_le_1", "j_mid_le_2", "j_mid_le_3",
    "j_ring_le_1", "j_ring_le_2", "j_ring_le_3",
    "j_pinky_le_1", "j_pinky_le_2", "j_pinky_le_3",
    # Right hand fingers
    "j_thumb_ri_1", "j_thumb_ri_2", "j_thumb_ri_3",
    "j_index_ri_1", "j_index_ri_2", "j_index_ri_3",
    "j_mid_ri_1", "j_mid_ri_2", "j_mid_ri_3",
    "j_ring_ri_1", "j_ring_ri_2", "j_ring_ri_3",
    "j_pinky_ri_1", "j_pinky_ri_2", "j_pinky_ri_3",
}

def strip_xanim(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    lines = content.split('\n')

    # Phase 1: Parse the PART list and identify which indices to keep
    old_parts = {}  # old_index -> bone_name
    keep_indices = set()

    for line in lines:
        m = re.match(r'^PART\s+(\d+)\s+"([^"]+)"', line)
        if m:
            idx = int(m.group(1))
            name = m.group(2)
            old_parts[idx] = name
            if name in T6_MATCHING_BONES:
                keep_indices.add(idx)

    if not old_parts:
        print(f"  WARNING: No PART entries found in {os.path.basename(filepath)}")
        return False

    # Build old->new index mapping
    sorted_keep = sorted(keep_indices)
    old_to_new = {old: new for new, old in enumerate(sorted_keep)}
    new_count = len(sorted_keep)

    # Phase 2: Rebuild the file
    output_lines = []
    in_frame = False
    skip_part_data = False
    current_frame_part = None

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Update NUMPARTS
        if stripped.startswith('NUMPARTS'):
            output_lines.append(f'NUMPARTS {new_count}')
            i += 1
            continue

        # Update PART declarations (header section)
        m = re.match(r'^PART\s+(\d+)\s+"([^"]+)"', stripped)
        if m and not in_frame:
            idx = int(m.group(1))
            name = m.group(2)
            if idx in keep_indices:
                new_idx = old_to_new[idx]
                output_lines.append(f'PART {new_idx} "{name}"')
            i += 1
            continue

        # Track FRAME sections
        if stripped.startswith('FRAME '):
            in_frame = True
            output_lines.append(line)
            i += 1
            continue

        # Handle PART references inside FRAME data
        if in_frame and stripped.startswith('PART '):
            m2 = re.match(r'^PART\s+(\d+)', stripped)
            if m2:
                idx = int(m2.group(1))
                if idx in keep_indices:
                    new_idx = old_to_new[idx]
                    output_lines.append(f'PART {new_idx}')
                    skip_part_data = False
                else:
                    skip_part_data = True
                i += 1
                continue

        # Skip data lines for removed parts (OFFSET, SCALE, X, Y, Z)
        if skip_part_data:
            if stripped.startswith(('OFFSET', 'SCALE', 'X ', 'Y ', 'Z ')):
                i += 1
                continue
            elif stripped == '':
                # Empty line after part data - skip it too
                i += 1
                continue
            else:
                # Hit something else (next PART, FRAME, etc.) - stop skipping
                skip_part_data = False
                # Don't increment i, re-process this line
                continue

        # Keep all other lines (header, FRAMERATE, NUMFRAMES, NOTETRACKS, etc.)
        output_lines.append(line)
        i += 1

    # Write the stripped file
    with open(filepath, 'w') as f:
        f.write('\n'.join(output_lines))

    return True

# Process all xanim files
xanim_dir = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\xanim_export\viewmodel"
files = sorted(glob.glob(os.path.join(xanim_dir, "vm_thunder_gun_*.xanim_export")))

print(f"T6 matching bones: {len(T6_MATCHING_BONES)}")
print(f"Xanim files to process: {len(files)}")
print()

for filepath in files:
    name = os.path.basename(filepath)

    # Read original part count
    with open(filepath, 'r') as f:
        content = f.read()
    orig_match = re.search(r'NUMPARTS\s+(\d+)', content)
    orig_count = int(orig_match.group(1)) if orig_match else 0

    success = strip_xanim(filepath)

    if success:
        # Verify new part count
        with open(filepath, 'r') as f:
            new_content = f.read()
        new_match = re.search(r'NUMPARTS\s+(\d+)', new_content)
        new_count = int(new_match.group(1)) if new_match else 0
        print(f"  {name}: {orig_count} -> {new_count} parts (removed {orig_count - new_count})")

print(f"\nDone! All {len(files)} xanim files stripped to T6-compatible bones.")
