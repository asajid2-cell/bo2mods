# How-to: Build and Deploy the Current Servant Case

This is the current working loop for the BO3 Rev Apothicon Servant path.

## Preferred entrypoint
Run from repo root:

```powershell
python _build/run_bo3_rev_probe_case.py mg08_v2_bo3_weapon_only
```

That wrapper sets the current recommended case:
- donor shell: `mg08_zm`
- starter weapon: `mg08_zm`
- custom model: BO3-derived reduced weapon-only GLB
- deploys to base lane so the survival FF and IPAK actually win

## What gets built
The current builder writes:
- `so_zsurvival_zm_transit.ff`
- `so_zsurvival_zm_transit.ipak`
- `mod_load.ff`
- rendered raw script: `mods/bo3_rev/scripts/mod_i_am_mod.gsc`
- build report: `_build/bo3_rev_idg_probe/build_report.json`

The case runner also archives the report to:
- `_build/bo3_rev_probe_cases/<case>/build_report_<build_tag>.json`

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
- probe weapon is `mg08_zm`
- expected clip/max values are correct for the current build

Then verify:
- the Servant model loads
- the weapon fires
- the singularity logic runs

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
- `_build/bo3_rev_idg_probe/build_report.json`
- `_build/bo3_rev_probe_cases/mg08_v2_bo3_weapon_only/`

## If deployment fails because the game has the files open
Close the game fully and rerun the build.
