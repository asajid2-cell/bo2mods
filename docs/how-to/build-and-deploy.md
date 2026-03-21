# How-to: Build and Deploy the Current Servant Case

This is the current working loop for the live BO3 Rev Apothicon Servant path.

## Preferred entrypoint
Run from repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_servant_vortex_runtime.ps1 -LayerMode all
```

That is the current recommended case:
- donor shell: `mg08_zm`
- FX bridge host: `tag_origin`
- FX scope: `vortex_core`
- layer mode: `all`
- deploys to base lane, mod lane, and AppData mod lane
- current checkpoint build tag after the latest full rebuild: `0321232501_4c7e1d`

## What gets built
The current builder writes:
- `so_zsurvival_zm_transit.ff`
- `so_zsurvival_zm_transit.ipak`
- `mod_load.ff`
- rendered raw script: `mods/bo3_rev/scripts/mod_i_am_mod.gsc`
- build report: `_build/bo3_rev_idg_probe/build_report.json`

The case runner also archives the report to:
- `_build/bo3_rev_probe_cases/<case>/build_report_<build_tag>.json`

Treat `_build/bo3_rev_idg_probe/build_report.json` as the canonical checkpoint record for restoring the exact current build.

## If you only want a local build without deploy
```powershell
python _build/run_bo3_rev_probe_case.py mg08_v2_bo3_weapon_only --no-deploy
```

## Current direct builder
The lower-level entrypoint is:

```powershell
python _build/build_bo3_rev_idg_probe.py
```

You usually only need this if you are overriding env vars manually.

## Layer-isolation entrypoint
For visual semantics work, the layer runner is:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_servant_vortex_runtime.ps1 -LayerMode control_only
```

Supported modes:
- `all`
- `control_only`
- `burst_vs_control`
- `shell_vs_control`
- `loop_vs_control`

## Full restart rule
Do a full game restart after rebuilding when you changed any of:
- the base survival FF
- the runtime IPAK
- xmodels/materials/images
- the donor shell definition

`map_restart` is fine for some raw-script-only iterations, but not for the current full Servant asset path.

## What to verify first in-game
Look for the BO3 Rev startup log line and confirm:
- build tag matches the build report
- donor shell is still `mg08_zm`
- expected clip/max values are correct for the current build

Then verify:
- the Servant model loads
- the weapon fires
- the singularity logic runs
- the vortex renders
- repeat shots replace the old active vortex instead of silently doing nothing

## Expected live controls
The current build supports:
- `.p <amount>`
- `.round <target>`
- `.fast`
- `.hits <count>`
- `.debug`

## Common reasons a build "worked" but runtime did not change
- You rebuilt but did not fully restart the game.
- The survival FF/IPAK did not win because you were not on the correct lane.
- You were looking at a stale rendered script or stale build report instead of the active build tag.
- A generated output changed, but the underlying source file did not.

## Common outputs to inspect
- `mods/bo3_rev/scripts/mod_i_am_mod.gsc`
- `mods/bo3_rev/clientscripts/mp/zombies/_bo3_rev_servant_fx_v3.csc`
- `_build/bo3_rev_idg_probe/build_report.json`
- `_build/bo3_rev_idg_probe/fx_surface_bundle/fx_surface_image_policy_report.json`

## If deployment fails because the game has the files open
Close the game fully and rerun the build.
