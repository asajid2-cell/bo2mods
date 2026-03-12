# BO3 Rev Release Branch

This `main` branch is a release-shaped branch, not the full development workspace.

It contains only the files needed to install the current `bo3_rev` mod build by dragging them into the BO2 game root.

## Install
1. Download this branch as a zip, or use a GitHub release made from it.
2. Extract it.
3. Copy the included `mods/` and `zone/` folders into your BO2 game root:
   - `z:\Games\pluto_t6_full_game`
4. Overwrite when prompted.
5. Launch Plutonium and load the `bo3_rev` mod.

## Included payload
- `mods/bo3_rev/scripts/mod_i_am_mod.gsc`
- `mods/bo3_rev/zone/all/mod_load.ff`
- `mods/bo3_rev/zone/all/so_zsurvival_zm_transit.ff`
- `mods/bo3_rev/zone/all/so_zsurvival_zm_transit.ipak`
- `zone/all/mod_load.ff`
- `zone/all/so_zsurvival_zm_transit.ff`
- `zone/all/so_zsurvival_zm_transit.ipak`

## Development branch
The full source, tooling, docs, and experiment history live on:
- `working-branch`

Use that branch for development. Keep `main` for release packaging.
