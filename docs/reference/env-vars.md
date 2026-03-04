# Reference: Environment Variables

This is a consolidated reference of the environment variables used by the build spine.

Primary entrypoint:
- `_build/two_phase_build.py`

## Deploy / runtime lanes
- `ROGUE_DEPLOY_TO_MOD`
  - `1` deploy to Plutonium storage mod zone directory
  - default: `1`
- `ROGUE_DEPLOY_TO_BASE`
  - `1` deploy to game `zone/all`
  - default: `0`

## Thundergun weapon build
- `ROGUE_TG_PROFILE`
  - weapon build profile (e.g. `hybrid_core`)
- `ROGUE_TG_SEMANTICS`
  - `minigun` or `thundergun` (which non-animation semantics to keep)
- `ROGUE_TG_MODEL_MODE`
  - `rogue` / `minigun` / `base`
- `ROGUE_TG_HAND_MODEL`
  - forced `handModel` for generated weapondefs (e.g. `viewmodel_usa_morphine`)
- `ROGUE_TG_GUN_MODEL`
  - forced `gunModel` override if needed
- `ROGUE_TG_WORLD_MODEL`
  - forced `worldModel` override if needed

## Truth alias carrier (registration bypass)
- `ROGUE_TG_TRUTH_ALIAS`
  - default carrier weapon (commonly `ak74u_zm`)
- `ROGUE_TG_TRUTH_ALIAS_UPG`
  - upgraded carrier weapon (commonly `ak74u_upgraded_zm`)

## Viewhands swap mode (experimental)
- `ROGUE_TG_VIEWHANDS_ENABLE`
  - when enabled, pipeline stages a `rogue_tg_viewhands` xmodel and forces `gunModel` to a no-visual carrier
  - default: `0` (disabled; risky)
- runtime dvar gate:
  - `rogue_tg_viewhands_enable`
  - must be set to `1` in-game to actually swap via GSC

## XAnim compile modes
- `ROGUE_TG_XANIM_EMIT_MODE`
  - `static_pose` / `stub` / `donor_clone` / `bo3_frames`
- `ROGUE_TG_XANIM_BO3_TARGETS`
  - comma-separated animation names to emit via `bo3_frames`
- `ROGUE_TG_XANIM_BO3_FALLBACK_MODE`
  - fallback for non-target anims (`donor_clone` / `static_pose` / `stub`)
- `ROGUE_TG_XANIM_BO3_ROOT_BONES`
- `ROGUE_TG_XANIM_BO3_NONROOT_BONES`

## Rig validation safety gates
- `ROGUE_TG_RIG_STRICT`
  - hard-fail if rig mismatches animation export bones
- `ROGUE_TG_RIG_AUTOFALLBACK_STUB`
  - auto-fallback to stub payloads if rig mismatch detected (prevents misleading visuals)

## Notes
Use `_build/reports/last_tg_build_manifest.json` as the source of truth for what a given run actually did.

