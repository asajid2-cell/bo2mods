# Tutorial: Getting Started (Current BO3 Rev Loop)

This is the shortest path from clone to a working local BO3 Rev test loop.

## 0. Requirements
You need:
- the repo located at `z:\Games\pluto_t6_full_game`
- BO2/Plutonium installed locally
- your own BO2 baseline dumps and BO3 source dumps
- Blender installed for rig/model conversion steps

This repo does not ship copyrighted BO2/BO3 assets.

## 1. Start from a clean runtime lane
From repo root:

```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode clean
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode dev -DevMod "bo3_rev"
```

If you also keep live mods under the game-install `mods/` folder and want them quarantined:

```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode dev -DevMod "bo3_rev" -ManageGameMods
```

## 2. Build the current working Servant case
The active case is the MG08 donor path:

```powershell
python _build/run_bo3_rev_probe_case.py mg08_v2_bo3_weapon_only
```

What this does:
- builds the donor-shell Servant weapon
- stages the reduced BO3-derived weapon model
- stages translated materials/images
- compiles and deploys `so_zsurvival_zm_transit.ff`
- compiles and deploys `so_zsurvival_zm_transit.ipak`
- compiles and deploys `mod_load.ff`
- renders the raw script from `mods/bo3_rev/scripts/mod_i_am_mod.gsc.in`

## 3. Restart the game fully
Because the current working path touches the base survival FF and IPAK, a full game restart is the safe default after rebuilding.

Do not rely on `map_restart` for:
- xmodel changes
- material/IPAK changes
- base-lane survival FF changes

## 4. Verify the loaded build
On first load, check the BO3 Rev log line in console:
- build tag
- weapon shell
- current model asset

You want the `bo3_rev` script output to match the build you just ran.

## 5. Test the current command layer
Useful commands:
- `.p 10000`
- `.round 15`
- `.fast`
- `.hits 50`
- `.debug`

## 6. What success looks like
The current good baseline is:
- you spawn with `mg08_zm`
- the model is the Servant, not a stock MG08
- the weapon fires the custom singularity logic
- zombies get pulled inward and die
- there is no `dobj ... has more than 160 bones` crash

## 7. If something goes wrong
Go here next:
- `docs/how-to/debug-runtime.md`
- `docs/how-to/debug-viewmodel-flip.md`
- `docs/explanation/history-and-findings.md`
