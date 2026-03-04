# BO3 -> BO2 Porting Foundation

See also:
- `_build/PORTING_ARCHITECTURE_V2.md` (system architecture + phase model)
- `_build/PORTING_RUNBOOK.md` (exact per-run command cycle)

## What Went Wrong
- Runtime and source were mixed in the same places (`mods`, `storage/mods`, base `zone/all`).
- Base game FFs were overwritten during experiments, so failures leaked into normal play.
- Multiple mods were simultaneously present in active search paths.
- Debugging was done with too many moving parts at once (FF patching + script changes + runtime overrides).

## New Runtime Lanes
- `clean` lane: normal gameplay, no dev mods active.
- `dev` lane: exactly one mod active for controlled tests.

## Commands
- Clean runtime (recommended before normal server play):
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode clean
```

- Enable one dev mod only:
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode dev -DevMod "zm_roguelike_panzer"
```

- Audit runtime state (no mutations):
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode audit
```

The reset tool writes a reversible log + report under:
- `_build/runtime_reset/<timestamp>/actions.log`
- `_build/runtime_reset/<timestamp>/report.json`

Runtime log gate check:
```powershell
py -3 "_build/runtime_health_check.py"
```

For thundergun-specific validation:
```powershell
py -3 "_build/runtime_health_check.py" --require-tg
```

Audit report fields to trust first:
- `active_game_mods` and `active_storage_mods` must be empty in clean lane.
- `zone_so_zsurvival_is_baseline` must be `true` before online/non-mod play.
- `storage_autoload_files` must be empty.
- `suspicious_storage_raw_artifacts` must be empty.

## Deployment Safety (Now Enforced)
`_build/two_phase_build.py` now defaults to:
- deploy to mod path only
- no base `zone/all` overwrite

Default behavior:
- `ROGUE_DEPLOY_TO_MOD=1`
- `ROGUE_DEPLOY_TO_BASE=0`

If you intentionally need base overwrite (rare), opt in explicitly:
```powershell
$env:ROGUE_DEPLOY_TO_BASE="1"
py -3 _build/two_phase_build.py
```

## Porting Method (Deterministic)
1. Start in `clean` lane.
2. Switch to `dev` lane for one target mod.
3. Validate only one layer at a time:
   - layer A: asset registration (`weapon` exists / included)
   - layer B: give/switch behavior
   - layer C: animation payload compatibility
4. Never mix global/base and mod-scoped deploys in the same test cycle.
5. Keep each experiment reproducible with:
   - hash of deployed FF/IPAK
   - exact script version ID
   - one log excerpt showing pass/fail condition

## Why Progress Stalled Previously
- Runtime contamination and asset-format bugs were mixed together in the same runs.
- Animtree/mech integration and thundergun animation porting were debugged simultaneously.
- Success criteria were not gated per layer, so failures looked random.

Fix: each test run now has one lane (`clean` or `dev`) and one variable change.

## Minimum Pass Criteria Per Iteration
- Map loads to gameplay.
- `.tg` (or test command) returns `has=1`.
- No startup COM_ERROR/awaiting-gamestate stall.

If one criterion fails, rollback to prior known-good run from `_build/runtime_reset` quarantine/snapshots and change exactly one variable for the next run.
