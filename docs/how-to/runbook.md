# BO3 -> BO2 Porting Runbook (Single-Variable Cycle)

This runbook is the operational companion to `docs/explanation/porting-architecture.md`.

## 1. Preconditions
- Work from repo root: `z:\Games\pluto_t6_full_game`
- Use one mod target only (default shown below): `zm_roguelike_panzer`
- Keep base runtime clean before/after each dev session.

## 2. Run ID convention
Use a unique run ID for every iteration:
- `YYYYMMDD-topic-change`
- Example: `20260224-tg-semantic-gate1`

## 3. Runtime lane control

### 3.1 Clean lane (before normal play)
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode clean
```

### 3.1b Server lane (before joining servers)
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode server
```

### 3.2 Dev lane (one mod only)
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode dev -DevMod "zm_roguelike_panzer"
```

### 3.3 Audit lane state
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode audit
```

## 4. Canonical Thundergun build command

Use the pipeline spine, strict preflight, compile, and explicit install target.

```powershell
python tools\asset_port_pipeline\run_thundergun_e2e.py `
  --t7-root "<PATH_TO_T7_DUMP>" `
  --source-mod "mods/zm_roguelike_panzer" `
  --output-root "_build/asset_port_pipeline/thundergun_e2e_runs/<RUN_ID>" `
  --auto-codbin-converter `
  --converter-blender-exe "C:\Program Files\Blender Foundation\Blender 4.1\blender.exe" `
  --strict-preflight `
  --compile `
  --remediate-on-fail `
  --remediate-retries 8 `
  --dependency-roots zone_dump/zone_raw _build/t6_asset_dump/zone_raw `
  --install-zone-dir "%LOCALAPPDATA%/Plutonium/storage/t6/mods/zm_roguelike_panzer/zone/all" `
  --report "_build/asset_port_pipeline/thundergun_e2e_runs/<RUN_ID>/report.json"
```

Notes:
- Do not deploy to base `zone/all` in this loop.
- If conversion is already staged, use the appropriate converter-mode flags and keep everything under the same `<RUN_ID>` root.

## 5. Runtime validation after each run
1. Launch mod/map and reproduce the test.
2. Classify health from latest log:

```powershell
py -3 _build/runtime_health_check.py --require-tg --json-out _build/asset_port_pipeline/thundergun_e2e_runs/<RUN_ID>/runtime_health.json
```

3. Record outcome by gate:
- `classification`
- failed gate IDs
- first blocking error line

## 6. Gate-specific response matrix

### `missing_animtree`
- Scope: script/animtree integration.
- Action: map-guard or supply missing animtree assets; do not touch weapon conversion in same run.

### `core_weapon_surface_broken`
- Scope: FF/runtime surface corruption.
- Action: stop; reset runtime lane; validate deployed FF provenance and dependencies.

### `rogue_weapon_not_registered`
- Scope: registration/zone inclusion.
- Action: inspect zone source + compile outputs; confirm weapon asset present and not pruned.

### `tg_asset_rejected_by_giveweapon`
- Scope: semantic compatibility of weapon definition/state.
- Action: inspect translated weapon fields + supported BO2 refs; keep map/scripts unchanged.

### `startup_hang_awaiting_gamestate`
- Scope: startup/runtime load blockers.
- Action: isolate to one script or one asset class; verify mod lane is clean and no stale runtime artifacts.

## 7. One-variable rule
Allowed change classes per run (pick one only):
1. Runtime lane/deployment hygiene
2. Weapon semantic translation
3. Animation conversion/retargeting
4. Script/animtree integration
5. Material/fx fallback handling

If a run changes more than one class, it is non-diagnostic and should not be used for conclusions.

## 8. Definition of progress
A run is progress only if:
1. It is reproducible from command + report artifacts.
2. It turns one previously red gate green without regressing earlier gates.

## 9. Recovery baseline command set
If runtime gets unstable:
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode clean
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode dev -DevMod "zm_roguelike_panzer"
```
Then re-run only the last known-good `<RUN_ID>` command.

## 10. Scaling beyond Thundergun
Once Thundergun loop is stable, reuse the exact same gate model for harder ports:
- map actors
- boss AI/animtrees
- full map asset sets

The architecture stays the same; only the semantic translators and profiles expand.
