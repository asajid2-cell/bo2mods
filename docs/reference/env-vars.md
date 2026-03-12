# Reference: Environment Variables

This is the current BO3 Rev env-var surface. The main entrypoint is:
- `_build/build_bo3_rev_idg_probe.py`

In normal use, prefer the case wrapper:
- `python _build/run_bo3_rev_probe_case.py <case>`

## Donor shell and identity

### `ROGUE_PROBE_SHELL`
Engine-recognized BO2 donor shell.

Examples:
- `mg08_zm`
- `m14_zm`
- `ray_gun_zm`

Default:
- `mg08_zm`

### `ROGUE_STARTER_WEAPON`
Weapon granted on spawn before the probe shell logic finishes.

Default:
- `m1911_zm` in the low-level builder
- case-dependent in the wrapper

### `ROGUE_BUILD_TAG`
Optional explicit build tag override.
If unset, the builder generates one from the current config and UTC time.

## Model selection

### `ROGUE_GUN_MODEL_MODE`
How `gunModel` is resolved.

Values:
- `custom`
- `literal`
- `base`

Default:
- `custom`

### `ROGUE_GUN_MODEL_LITERAL`
Required when `ROGUE_GUN_MODEL_MODE=literal`.

Example:
- `viewmodel_usa_no_model`

### `ROGUE_MODEL_ASSET_BASE`
Base asset name for staged custom xmodels.

Default:
- `bo3_rev_v2_idg_view`

### `ROGUE_IDG_VIEW_GLB`
Optional override path for the input GLB used to stage the custom model.

If unset, the builder uses the current weapon-only GLB under `_build/bo3_rev_idg_weapon_only/`.

## Animation mode

### `ROGUE_USE_BO3_IDG_ANIMS`
When enabled, the builder stages BO3 animation assets instead of donor-animation aliases.

Default:
- `0`

Important:
- the current stable path keeps this off
- the live build uses donor animation aliases

## Deploy lanes

### `ROGUE_DEPLOY_TO_MOD`
Deploy outputs to the mod lane.

Default:
- `1`

### `ROGUE_DEPLOY_TO_BASE`
Deploy outputs to the game `zone/all` base lane.

Default:
- `0` in the low-level builder
- enabled in the current working MG08 case

## First-person safety toggles

### `ROGUE_USE_CUSTOM_IDG_VIEWHANDS`
Enables the custom-viewhands experiment.

Default:
- `0`

Note:
- this is not the current stable path

### `ROGUE_FORCE_LOW_HANDMODEL`
Forces a low/blank handModel path for specific acceptance experiments.

Default:
- `0`

### `ROGUE_STUB_ZM_VIEWHANDS`
Stages stub stock zombie viewhands.

Default:
- `0`

This was an older experiment and is not part of the current stable path.

## Zone/build safety

### `ROGUE_ALLOW_STRIPPED_SURVIVAL_FF`
Bypasses the safety check that rejects a stripped survival FF.

Default:
- `0`

This should stay off for the normal working case.

### `ROGUE_USE_FULL_ZONE_SOURCE`
Use the full survival zone source instead of a tiny probe-only source.

Default:
- `1` when deploying to base
- otherwise `0`

## Current preferred wrapper case
The stable documented case is:

```powershell
python _build/run_bo3_rev_probe_case.py mg08_v2_bo3_weapon_only
```

That is the recommended path instead of manually setting env vars for day-to-day work.
