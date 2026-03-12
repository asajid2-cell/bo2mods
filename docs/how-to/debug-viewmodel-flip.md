# How-to: Debug First-Person Viewmodel Failures

This file kept its original name, but it now covers the broader BO3 Rev first-person failure class, not only the old camera-flip symptom.

## The three first-person failure classes that mattered

### 1. Bone-cap crash
Signature:
- `dobj for xmodel 'c_zom_*_viewhands' has more than 160 bones`

What it meant here:
- T6 was building a first-person DObj larger than the 160-bone cap
- the problem was not fixed by GSC give logic
- it required a different rig architecture

### 2. Wrong shell composition
Signature:
- the same `>160 bones` crash even when the gun model was tiny or stock

What it meant here:
- `ray_gun_zm` had hidden first-person baggage
- the issue was not only the imported BO3 mesh
- donor shell choice mattered

### 3. Bad fit/origin/scale
Signature:
- model visible but huge, crushed, paper-thin, or offset

What it meant here:
- the model was loading
- the remaining issue was placement, fit transform, or material contract

## What finally worked
- Stop trying to win with custom viewhands swaps first.
- Move to a weapon-only BO3-derived reduced rig.
- Use a donor shell with a safer first-person path.
- Fit the weapon into that donor path by transform, not by blindly keeping the whole BO3 rig.

## Current working donor
The current donor shell is `mg08_zm`, not `ray_gun_zm`.

That decision came from runtime proof, not guesswork:
- Ray Gun kept hitting hidden first-person composition issues.
- MG08 gave a much more stable pose and did not reproduce the same crash class.

## If you see a first-person issue today
Classify it first:

1. Crash on equip:
   - likely shell composition or bone budget
2. Visible but wrong size/pose:
   - likely transform/fit problem
3. Visible but wrong colors/glow:
   - material/IPAK problem
4. Logic works but animation feels wrong:
   - donor-animation parity problem

Do not debug all four at once.
