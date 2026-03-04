# How-to: Debug the “Camera Flips / Controls Invert” on Equip

Symptom:
- Normal weapons behave correctly.
- Switching to the Thundergun carrier causes an immediate camera orientation snap:
  - feels like you’re suddenly facing behind you and slightly up
  - mouse/controls feel inverted because the view basis is now rotated

This is **not** a GSC input bug. It is almost always a **viewmodel rig contract** bug.

## The contracts that matter in T6
In T6 first-person viewmodels, the engine derives camera/view basis from a combination of:
- bone hierarchy (`tag_view`, `tag_ads`, `tag_cambone`, `tag_camera`)
- bind orientation (bone rotations in the model’s bind pose)
- which bones are driven by animation in the current weapon state (raise/sprint/ads)

If the camera chain is parented under a bone that the animation drives aggressively (e.g. `tag_torso`),
then equipping the weapon can rotate the camera basis.

## Known-good reference (stock ZM viewhands)
Stock ZM viewhands have a camera chain structured like:
- `tag_camera -> tag_cambone -> tag_view -> *_skel`
and torso is typically under `tag_view` (often via intermediate tags in different rigs).

Key property: the camera chain is **not driven by torso motion** during equip.

## What we changed in this repo (current attempt)
`_build/two_phase_build.py` includes a repair step that normalizes the BO3 combined rig:
- forces the camera chain to be under `tag_view`
- aligns bind rotations to match stock `tag_view` basis
- sets the skin skeleton root to `tag_view` so the OAT GLTF loader accepts the model

If you’re reading this while debugging, confirm that these repairs are actually applied to the **deployed** model.

## Debug steps
### 1) Prove the viewhands swap is not happening
This repo has a viewhands-swap watcher gated by a dvar.

In-game:
- ensure this is off:
  - `set rogue_tg_viewhands_enable 0`
- and confirm your log does not contain:
  - `[ROGUE] event=tg_viewmodel;stage=set`

If you are swapping viewhands, debug *that* first (it can override all other work).

### 2) Prove which model is actually being used
If the game cached the xmodel, you can change the GLB all day and see no effect.
For camera/orientation issues:
- fully restart the game between runs

### 3) Minimize the anim surface
To prove the flip is an animation-driven transform:
- temporarily switch the weapon profile to something that minimizes movement states
- or temporarily map raise/sprint to a known safe donor anim set

If the flip disappears, the bug is not “the model”; it’s one or more anim tracks driving camera bones.

### 4) Force camera bones to identity (last-resort triage)
If needed for diagnosis, implement an encoder rule that:
- strips transforms for `tag_camera` / `tag_cambone` in high-risk states
- keeps them fixed to bind pose

This is a diagnostic step, not a final port. The final port should support the full chain correctly.

## Output artifacts to attach when asking for help
- The `[ROGUE]` log excerpt covering equip/switch
- `_build/reports/last_tg_build_manifest.json`
- The deployed model bind rotations for:
  - `tag_view`, `tag_cambone`, `tag_camera`, `tag_torso`

