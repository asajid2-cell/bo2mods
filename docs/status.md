# Status

Last updated: 2026-03-12

## Goal
Port the BO3 Apothicon Servant into BO2/Plutonium in a way that is:
- actually playable in BO2 zombies
- reproducible to build and deploy
- progressively closer to BO3 visuals, handling, and black-hole behavior

The project is no longer in the "can we even load anything" stage. It is in the "make the donor-shell port look and behave more like BO3" stage.

## Current live architecture
- Mod: `mods/bo3_rev`
- Current donor shell: `mg08_zm`
- Current first-person model path: BO3-derived reduced weapon-only rig
- Deployment path: patched `so_zsurvival_zm_transit.ff` + `.ipak` plus `mod_load.ff`
- Preferred build entrypoint: `python _build/run_bo3_rev_probe_case.py mg08_v2_bo3_weapon_only`

## What currently works

### Build and deploy
- The BO3 Rev probe builder is reproducible:
  - `_build/build_bo3_rev_idg_probe.py`
  - `_build/run_bo3_rev_probe_case.py`
- The build emits and deploys:
  - `so_zsurvival_zm_transit.ff`
  - `so_zsurvival_zm_transit.ipak`
  - `mod_load.ff`
- The pipeline now hard-fails if custom images are staged without a matching runtime IPAK.

### Weapon shell and grant path
- The project no longer depends on a fresh-name `apothicon_servant_zm` engine weapon.
- The live shell is `mg08_zm`, and the override is proven by runtime clip/max logs.
- The user spawns into the donor shell directly instead of receiving a second temporary donor weapon.

### Viewmodel acceptance
- The Servant model loads in BO2 without the old `>160 bones` crash.
- The current path uses a reduced BO3-derived weapon-only rig instead of the earlier combined gun+hands attempt.
- The current donor pose is close enough to iterate visually and record demos.

### Gameplay logic
- Custom Servant fire logic is live in GSC.
- Firing the donor shell spawns a timed singularity at the trace point.
- Zombies are pulled inward and killed inside the inner radius.
- Only one active singularity per player is allowed at a time.
- The active window is currently set to the BO3 `black_hole_bomb_zm` 4.0 second timing target.

### Demo/admin command layer
The live script now supports:
- `.p <amount>`
- `.round <target>`
- `.fast`
- `.hits <count>`
- `.debug`

### Demo survivability tuning
- Fast-spawn demo mode can force `level.zombie_vars["zombie_spawn_delay"] = 0.08`.
- Demo health can be raised to a chosen hits-to-down target.
- Script-usage overlay is off by default and only shown through `.debug`.

## What is proven

### Fresh-name weapon identity is blocked in this normal mod lane
The project proved that:
- zombies registration can succeed
- inclusion tables can succeed
- donor surfaces can be valid
- and the engine can still refuse to resolve a new name like `apothicon_servant_zm`

That is no longer a theory. It is a proven barrier for this workflow.

### `ray_gun_zm` is a bad donor shell for this project
The project also proved that `ray_gun_zm` still crashes with hidden first-person composition even when:
- the gun model is tiny
- the gun model is a stock BO2 model
- or the gun model is effectively no-model

So `ray_gun_zm` is no longer the active donor route.

## What is still imperfect

### Animation parity
- Fire and reload are donor-animation approximations, not real BO3 Servant animation parity.
- Current choices are tuned for feel, not final fidelity:
  - staff-like fire
  - PDW reload

### Material fidelity
- The model is no longer invisible or chrome, and the major surface holes are mostly fixed.
- The remaining material problem is fidelity:
  - some body colors are still muted compared to BO3
  - some emissive/glow surfaces are still approximate, not authored-perfect

### FX/presentation
- The singularity has placeholder visible FX and lightning cues.
- The logic works, but the presentation is still a BO2-safe approximation, not a BO3-authored black-hole package.

## Active risk areas
- Any change that touches the base survival FF or IPAK still requires a full game restart for trustworthy testing.
- `mg08_zm` donor dependencies are noisier than a simpler shell, so image/material issues can still be harder to separate.
- The current black-hole presentation is intentionally using stock T6 FX as a safe first pass.

## Live tuning notes
- Engine-side ammo is staged as `1/10` so the HUD reads `1/9` on this shell.
- `.debug` is the supported way to enable script-usage and verbose state tracing.

## Next milestone
Keep the current `mg08_zm` shell and improve:
1. fire/reload/raise animation feel
2. material fidelity, especially emissive surfaces
3. black-hole presentation and polish

See `docs/roadmap.md`.
