# Explanation: History & Findings (What We Tried, What It Proved)

This is the high-signal timeline of what we attempted and what each failure taught us.

## Phase A — “It doesn’t give the thundergun”
Observed:
- script calls to grant `thundergun_zm` failed
- logs showed `alias_grant_failed`, later classified as `weapondef_unregistered`

Finding:
- It was not primarily `.tg` logic.
- The engine was refusing to grant a weapon because the weapondef wasn’t registered in the expected way.

Outcome:
- Introduced a **truth-alias carrier** approach:
  - grant a known registered weapon (`ak74u_zm`)
  - patch its weaponfile to reference thundergun models/anims
  - run thundergun behavior via script watchers

This unblocked animation/model work while registration is still being researched.

## Phase B — Lane mismatch (“I built it but the game reads a different FF”)
Observed:
- builds succeeded
- runtime logs showed the game loading fastfiles from base `zone/all`
- your built fastfile was deployed only to mod storage

Finding:
- deployment target and runtime lookup did not match.

Outcome:
- build/deploy tooling was updated to support explicit “base” vs “mod” deploy lanes
- runtime reset tooling was added to restore baselines and prevent contamination

## Phase C — Bone cap crashes (`>160 bones`)
Observed:
- engine crashes on load with:
  - `dobj for xmodel 'c_zom_*_viewhands' has more than 160 bones`

Finding:
- combined gun + viewhands exceeded the T6 first-person DObj cap.

Outcome:
- Introduced explicit bone-budget gating in the build pipeline.
- Began exploring architectures that avoid doubling rigs (no “gun rig + separate hands rig”).

## Phase D — “It renders but anims are warped / no anims”
Observed:
- model could appear but animation was wrong or missing.

Finding:
- early in the pipeline the viewmodel GLB was missing the full joint set that BO3 animations reference.

Outcome:
- rebuilt the viewmodel GLB to include the full union of bones referenced by `vm_thunder_gun_*`.
- added strict rig validation reports.

## Phase E — Viewmodel camera flips / control inversion (current)
Observed:
- switching to the carrier weapon snaps the view basis (feels like looking behind/up).

Working hypothesis:
- camera/tag chain hierarchy or bind rotations do not match T6 expectations
- camera bones may be inadvertently parented under torso motion in equip/sprint states

Current mitigations:
- GLB repair step that normalizes camera chain and tag rotations
- doc’d debug procedure: `docs/how-to/debug-viewmodel-flip.md`

Status:
- still under active verification (asset caching and “which model is loaded” checks matter here).

## What this history implies (short)
We are past the “can we compile and deploy” milestone.
We are now in the “engine contract compliance” stage, where:
- the game will load the assets
- but first-person correctness depends on exact rig/tag assumptions and state-machine semantics

