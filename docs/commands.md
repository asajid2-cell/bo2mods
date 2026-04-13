# Commands And Tooling Reference

This document is the command-line and script reference for the BO3 Rev / T6 / Plutonium repo.

It is meant to answer four practical questions:

1. What are the stable entrypoints in this repo?
2. What does each one do?
3. How do you actually run the common workflows end to end?
4. Where do artifacts, logs, screenshots, and probe outputs land?

This file is intentionally operational, not historical. Use it together with:

- `docs/fullsummary.md` for the latest state and findings
- `docs/enginemap.md` for the reverse-engineered runtime model
- `docs/handoff.md` for the long-form project handoff

## Scope

This document focuses on the stable command surface:

- `tools/*.ps1`
- `native/fx_runtime_probe/*.ps1`
- the main builder `_build/build_bo3_rev_idg_probe.py`
- recurring operational helpers in `_build/`

It does not try to fully reverse-document every one-off experiment script under `_build/`. Those are cataloged at the end as experimental utilities.

## Repo Map

Use this mental map first:

```text
Z:\Games\pluto_t6_full_game
|- tools/                          Main operational entrypoints
|- native/fx_runtime_probe/        Native x86 probe build/inject/config
|- mods/bo3_rev/                   Repo-side loose mod content
|- _build/bo3_rev_idg_probe/       Active build workspace + outputs
|- docs/                           Long-form docs and findings
|- zone/                           Base game fastfiles/ipaks used at runtime
```

The main path today is:

```text
builder -> sync/restart wrapper -> launch script -> optional probe injection -> logs/artifacts
```

## Core Workflow Map

### 1. Build / sync / launch

```text
_build/build_bo3_rev_idg_probe.py
  driven directly or through:
    tools/build_servant_minimal_anim_runtime.ps1
    tools/build_full_servant_runtime.ps1
    tools/run_stock_visibility_control.ps1
    tools/run_anim_debug_cycle.ps1

sync/restart:
  tools/restart_t6_probe_cycle.ps1

launch:
  tools/launch_t6_offline.ps1
```

### 2. Probe workflow

```text
native/fx_runtime_probe/build_x86.ps1
native/fx_runtime_probe/inject_latest.ps1
native/fx_runtime_probe/active_probe_mode.txt
native/fx_runtime_probe/active_probe_watchlist.txt
native/fx_runtime_probe/bin/x86/Release/fx_runtime_probe.log
```

### 3. Validation / capture

```text
tools/validate_t6_zm_install.ps1
tools/repair_t6_zm_install_ipaks.ps1
tools/capture_game_screenshot.ps1
tools/run_stock_visibility_control.ps1
tools/run_project_mcp.ps1
tools/mcp/server.py
```

## Path Conventions

Unless overridden, most scripts assume:

- `GameDir = Z:\Games\pluto_t6_full_game`
- `PlutoniumDir = C:\Users\Ahmed\AppData\Local\Plutonium`
- `Mod = bo3_rev`
- `Map = zm_transit`
- `UiMapName = zm_transit`
- `UiGametype = zclassic`
- `UiZmGamemodeGroup = zsurvival`
- `UiMapStartLocation = town`
- `GGametype = zclassic`
- `Name = ffprobe_offline`

Common runtime logs:

- `C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\mods\bo3_rev\games_mp.log`
- `C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\mods\bo3_rev\console_zm.log`
- `C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\main\console_zm.log`

Common probe log:

- `native/fx_runtime_probe/bin/x86/Release/fx_runtime_probe.log`

Common build output root:

- `_build/bo3_rev_idg_probe`

Common MCP output root:

- `_build/mcp_screenshots`

## Canonical Commands

### Normal offline launch (clean runtime)

```powershell
powershell -ExecutionPolicy Bypass -File Z:\Games\pluto_t6_full_game\tools\launch_t6_offline.ps1 `
  -Mode ZM `
  -Name offline_player `
  -GameDir Z:\Games\t6-clean\pluto_t6_full_game `
  -PlutoniumDir C:\Users\Ahmed\AppData\Local\Plutonium `
  -Mod bo3_rev `
  -Map zm_transit `
  -UiMapName zm_transit `
  -UiGametype zclassic `
  -UiZmGamemodeGroup zsurvival `
  -UiMapStartLocation town `
  -GGametype zclassic
```

### Launch on monitor 2 (clean runtime)

```powershell
powershell -ExecutionPolicy Bypass -File Z:\Games\pluto_t6_full_game\tools\launch_t6_offline.ps1 `
  -Mode ZM `
  -Name offline_player `
  -GameDir Z:\Games\t6-clean\pluto_t6_full_game `
  -PlutoniumDir C:\Users\Ahmed\AppData\Local\Plutonium `
  -Mod bo3_rev `
  -Map zm_transit `
  -UiMapName zm_transit `
  -UiGametype zclassic `
  -UiZmGamemodeGroup zsurvival `
  -UiMapStartLocation town `
  -GGametype zclassic `
  -MonitorIndex 2
```

### Sync and relaunch through the wrapper

```powershell
powershell -ExecutionPolicy Bypass -File Z:\Games\pluto_t6_full_game\tools\restart_t6_probe_cycle.ps1 `
  -Launch `
  -Map zm_transit `
  -UiMapName zm_transit `
  -UiGametype zclassic `
  -UiZmGamemodeGroup zsurvival `
  -UiMapStartLocation town `
  -GGametype zclassic `
  -Name offline_player
```

### Prepare clean runtime (no launch)

```powershell
powershell -ExecutionPolicy Bypass -File Z:\Games\pluto_t6_full_game\tools\prepare_t6_clean_regular_runtime.ps1
```

### Menu-only launch (no direct `+map`)

```powershell
powershell -ExecutionPolicy Bypass -File Z:\Games\pluto_t6_full_game\tools\launch_t6_offline.ps1 `
  -Mode ZM `
  -Name offline_player `
  -GameDir Z:\Games\t6-clean\pluto_t6_full_game `
  -PlutoniumDir C:\Users\Ahmed\AppData\Local\Plutonium `
  -NoMod `
  -MenuOnly `
  -MonitorIndex 2
```

### Send a menu “start match” input (after manual lobby setup)

```powershell
powershell -ExecutionPolicy Bypass -File Z:\Games\pluto_t6_full_game\tools\start_t6_zm_menu_match.ps1 `
  -Keys '{UP}','{ENTER}'
```

### Build the native probe

```powershell
powershell -ExecutionPolicy Bypass -File Z:\Games\pluto_t6_full_game\native\fx_runtime_probe\build_x86.ps1
```

### Inject the latest probe into the live process

```powershell
powershell -ExecutionPolicy Bypass -File Z:\Games\pluto_t6_full_game\native\fx_runtime_probe\inject_latest.ps1 `
  -ProcessName plutonium-bootstrapper-win32 `
  -Wait
```

### Run the stock visibility control

```powershell
powershell -ExecutionPolicy Bypass -File Z:\Games\pluto_t6_full_game\tools\run_stock_visibility_control.ps1 `
  -Launch `
  -CaptureScreenshot `
  -KillAfterCapture
```

### Run the animation debug cycle

```powershell
powershell -ExecutionPolicy Bypass -File Z:\Games\pluto_t6_full_game\tools\run_anim_debug_cycle.ps1 `
  -Phase idle_first_raise `
  -Lane custom `
  -PatchMode observe_only
```

### Run the repo-local MCP stack

```powershell
powershell -ExecutionPolicy Bypass -File Z:\Games\pluto_t6_full_game\tools\run_project_mcp.ps1 `
  -InstallDependencies `
  -Host 127.0.0.1 `
  -Port 8765
```

Mounted MCP endpoints:

- `http://127.0.0.1:8765/artifacts/mcp`
- `http://127.0.0.1:8765/windows/mcp`
- `http://127.0.0.1:8765/assets/mcp`
- `http://127.0.0.1:8765/process/mcp`
- `http://127.0.0.1:8765/pe/mcp`

## Detailed Reference

## `tools/launch_t6_offline.ps1`

Purpose:

- Launches Plutonium/T6 offline
- Applies launch hygiene
- Repairs zombie ipak aliases unless skipped
- Syncs selected UI and clientscript overrides into AppData
- Supports monitor-targeted launching

Primary parameters:

- `-Mode`
  - `ZM` or `MP`
- `-Name`
  - offline player name
- `-GameDir`
  - game install root
- `-PlutoniumDir`
  - Plutonium AppData root
- `-Mod`
  - usually `bo3_rev`
- `-NoMod`
  - launch with no mod
- `-Map`
  - map to launch, usually `zm_transit`
- `-UiGametype`
- `-UiZmGamemodeGroup`
- `-UiMapStartLocation`
- `-UiMapName`
- `-GGametype`
- `-ExecCfg`
  - run a cfg after startup
- `-ExtraCommands`
  - additional `+` commands
- `-SkipAssetValidation`
- `-SkipUiOverrides`
- `-SkipZombieIpakRepair`
- `-SkipLaunchHygiene`
- `-MonitorIndex`
  - one-based display index, `2` means second display
- `-WindowMoveTimeoutSec`
  - how long the window guard remains active
- `-WindowMoveFastPollMs`
  - fast startup polling interval
- `-WindowMoveSlowPollMs`
  - later polling interval
- `-WindowMoveFastPhaseSec`
  - duration of the aggressive early poll phase
- `-HiddenWorker`
  - internal handoff mode; do not use directly unless testing launch behavior
- `-DryRun`
  - print the resolved command without launching

Notes:

- The monitor-moving logic only activates when `-MonitorIndex` is greater than `0`.
- The script writes monitor trace data to:
  - `C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\launch_monitor_trace.log`
- The hidden-worker path is there to keep the visible launcher terminal off monitor 1.

Example:

```powershell
powershell -ExecutionPolicy Bypass -File tools\launch_t6_offline.ps1 `
  -Mode ZM `
  -Mod bo3_rev `
  -Map zm_transit `
  -UiMapName zm_transit `
  -UiGametype zclassic `
  -UiZmGamemodeGroup zsurvival `
  -UiMapStartLocation town `
  -GGametype zclassic `
  -MonitorIndex 2
```

## `tools/restart_t6_probe_cycle.ps1`

Purpose:

- Kills running Plutonium/T6 processes
- Syncs runtime files into the right loose/AppData locations
- Optionally launches the game
- Optionally injects the probe after a startup gate

Primary parameters:

- `-Launch`
  - relaunch after sync
- `-InjectProbe`
  - inject the latest probe after the gate
- `-ModOnly`
  - sync only; do not build or launch
- `-UseStockSurvivalZone`
- `-SyncBaseZoneAll`
- `-SyncGeneratedClientOverrides`
- `-Map`
- `-UiGametype`
- `-UiZmGamemodeGroup`
- `-UiMapStartLocation`
- `-UiMapName`
- `-GGametype`
- `-ExecCfg`
- `-ExtraCommands`
- `-ProbeMode`
  - one of:
    - `safe`
    - `bootstrap_guard_only`
    - `render_opacity_focus`
    - `viewmodel_render_focus`
    - `xanim_focus`
    - `xanim_consumer_focus`
    - `xanim_asset_lookup_focus`
    - `producer_compact_override_focus`
    - `class_family_materialization_writepath`
- `-ProbeAttachGate`
  - one of:
    - `startup`
    - `connect`
    - `grant`
    - `first_raise_begin`
    - `idle_begin`
    - `fire_begin`
- `-ProbeAttachDelayMs`
- `-ProbeAttachTimeoutSec`
- `-EnableProbeGuards`
- `-ProbeGuardLabel`
- `-ProbeGuardNeedle`
- `-ProbeGuardDelayMs`
- `-ProbeGuardMax`
- `-Name`
- `-Mod`
- `-GameDir`
- `-PlutoniumDir`
- `-MonitorIndex`
- `-HiddenWorker`
  - internal handoff mode
- `-SkipAssetValidation`
- `-ResolvedSourceReportPath`
  - optional output path for resolved runtime source reporting

Typical uses:

- sync only
- sync + launch
- sync + launch + inject probe

Example:

```powershell
powershell -ExecutionPolicy Bypass -File tools\restart_t6_probe_cycle.ps1 `
  -Launch `
  -InjectProbe `
  -ProbeMode xanim_asset_lookup_focus `
  -ProbeAttachGate idle_begin `
  -Map zm_transit `
  -UiMapName zm_transit `
  -UiGametype zclassic `
  -UiZmGamemodeGroup zsurvival `
  -UiMapStartLocation town `
  -GGametype zclassic
```

## `tools/build_servant_minimal_anim_runtime.ps1`

Purpose:

- The main animation/runtime build wrapper
- Sets a large `ROGUE_*` environment surface
- Drives `_build/build_bo3_rev_idg_probe.py`
- Optionally syncs and launches through the restart wrapper

High-value parameters:

- `-EmitMode`
  - `static_pose`
  - `donor_clone`
  - `donor_template_static_pose`
  - `donor_semantic_static_pose`
  - `bo3_frames`
- `-AnimStage`
  - `idleonly`
  - `idlefire`
  - `spawn`
- `-AnimSubset`
- `-AnimProbePhase`
  - `idle_first_raise`
  - `pullout`
  - `fire`
  - `combined`
  - `putaway`
  - `equip_hold`
- `-IdleAnimOverride`
- `-RaiseAnimOverride`
- `-QuickRaiseAnimOverride`
- `-FirstRaiseAnimOverride`
- `-FireAnimOverride`
- `-AnimDebugTargets`
- `-RunLabel`
- `-ForceStockShell`
- `-ForcedStockShell`
- `-GunModelMode`
  - `custom`
  - `base`
  - `literal`
- `-ForceLowHandmodel`
- `-DisableStockSurvivorCarrier`
- `-UseCustomIdgViewhands`
- `-ProbeWeapon`
- `-StarterWeapon`
- `-DisableBo3IdgAnims`
- `-IdleDiagBone`
- `-IdleDiagTranslate`
- `-IdleDiagFrequency`
- `-IdleStaticBone`
- `-IdleStaticTranslate`
- `-Map`
- `-UiGametype`
- `-UiZmGamemodeGroup`
- `-UiMapStartLocation`
- `-GGametype`
- `-ExecCfg`
- `-ExtraCommands`
- `-ForceIdentity`
- `-UseStockSurvivalZone`
- `-Launch`
- `-InjectProbe`
- `-RuntimeBackend`
  - `semantic_names`
  - `target_weapon_names`
- `-PatchRuntimeBackendFF`
- `-ProbeMode`

Important note:

- This wrapper is environment-variable heavy. It sets a large `ROGUE_*` contract consumed by `_build/build_bo3_rev_idg_probe.py`.
- If you want reproducibility, archive the exact parameter set and resulting `build_report.json`.

Example:

```powershell
powershell -ExecutionPolicy Bypass -File tools\build_servant_minimal_anim_runtime.ps1 `
  -EmitMode bo3_frames `
  -AnimStage spawn `
  -AnimSubset vm_zod_id_gun_first_raise,vm_zod_id_gun_idle `
  -AnimProbePhase idle_first_raise `
  -GunModelMode base `
  -ProbeWeapon mg08_zm `
  -StarterWeapon m1911_zm `
  -RuntimeBackend target_weapon_names `
  -ForceStockShell `
  -ForcedStockShell c_zom_hazmat_viewhands
```

## `tools/run_anim_debug_cycle.ps1`

Purpose:

- Authoritative animation debug loop
- Builds a lane
- Launches
- Waits for markers
- Optionally fires a synthetic burst
- Archives logs and verdicts

Primary parameters:

- `-Phase`
  - `idle_first_raise`
  - `pullout`
  - `fire`
  - `combined`
- `-Lane`
  - `custom`
  - `donor_baseline`
- `-PatchMode`
  - `observe_only`
  - `dataInt`
  - `dataShort`
  - `deltaPart`
  - `all_sections`
- `-RuntimeBackend`
  - `semantic_names`
  - `target_weapon_names`
- `-GunModelMode`
  - `custom`
  - `base`
  - `literal`
- `-ForceLowHandmodel`
- `-DisableStockSurvivorCarrier`
- `-UseCustomIdgViewhands`
- `-ForceStockShell`
- `-ForcedStockShell`
- `-IdleDiagBone`
- `-IdleDiagTranslate`
- `-IdleDiagFrequency`
- `-IdleStaticBone`
- `-IdleStaticTranslate`
- `-Map`
- `-UiGametype`
- `-UiZmGamemodeGroup`
- `-UiMapStartLocation`
- `-GGametype`
- `-ExecCfg`
- `-ProbeAttachGate`
- `-ProbeAttachDelayMs`
- `-ProbeAttachTimeoutSec`
- `-LaunchTimeoutSec`
- `-ObservationTimeoutSec`
- `-IdleWindowMs`
- `-BurstShots`
- `-BurstSpacingMs`
- `-SkipBuild`
- `-NoShutdown`

Artifacts:

- `_build/bo3_rev_idg_probe/anim_debug_runs/...`

Use this when you want reproducible animation-family runs, not just ad hoc launching.

## `tools/run_stock_visibility_control.ps1`

Purpose:

- Build a stock-control lane
- Launch it
- Wait for runtime markers
- Capture screenshot/log deltas
- Archive a stock floor run

Primary parameters:

- `-Weapon`
- `-StarterWeapon`
- `-Launch`
- `-UseStockSurvivalZone`
- `-ForceStockShell`
- `-ForcedStockShell`
- `-CaptureScreenshot`
- `-CaptureDelaySec`
- `-MarkerTimeoutSec`
- `-KillAfterCapture`
- `-Map`
- `-UiMapName`
- `-UiGametype`
- `-UiZmGamemodeGroup`
- `-UiMapStartLocation`
- `-GGametype`
- `-Name`
- `-GameDir`
- `-PlutoniumDir`

Artifacts:

- `_build/visibility_live/<timestamp>_stock_control`

Use this for screenshot-verified stock-control runs.

## `tools/build_full_servant_runtime.ps1`

Purpose:

- Build the broader raw-FX/client-FX Servant lane
- Optionally sync and launch

Parameters:

- `-Scope`
  - `full`
  - `vortex_core`
- `-LayerMode`
  - `all`
  - `control_only`
  - `burst_vs_control`
  - `shell_vs_control`
  - `loop_vs_control`
- `-PortalRenderMode`
  - `safe_alpha`
  - `flare_stock_trial`
- `-Launch`
- `-InjectProbe`

This is not the stable stock-control lane. Use it when you are intentionally working on the broader Servant FX suite.

## `tools/build_and_launch_anim_offline.ps1`

Purpose:

- Convenience wrapper for a build + normal offline launch

Parameters:

- `-Phase`
  - `idle_first_raise`
  - `pullout`
  - `fire`
  - `combined`
- `-Lane`
  - `custom`
  - `donor_baseline`
- `-Map`
- `-UiGametype`
- `-UiZmGamemodeGroup`
- `-UiMapStartLocation`
- `-GGametype`
- `-ProbeMode`
  - `safe`
  - `render_opacity_focus`
  - `xanim_focus`
- `-InjectProbe`
- `-BlockNetwork`
- `-DryRun`

## `tools/capture_game_screenshot.ps1`

Purpose:

- Capture either a window or the full virtual screen
- Save a PNG and matching metadata JSON

Parameters:

- `-OutputPath` (required)
- `-CaptureMode`
  - `window`
  - `screen`
- `-ProcessNamePatterns`
- `-WindowTitlePattern`
- `-FocusDelayMs`
- `-AllowScreenFallback`

Outputs:

- PNG image
- adjacent JSON metadata file

## `tools/validate_t6_zm_install.ps1`

Purpose:

- Validate that the base zombie files and expected content are present
- Scan the main console log for missing-content signals

Parameters:

- `-GameDir`
- `-PlutoniumDir`
- `-OutputPath`
- `-Quiet`

Verdicts:

- `ok`
- `missing_required_files`
- `missing_expected_zm_content`

## `tools/repair_t6_zm_install_ipaks.ps1`

Purpose:

- Creates or copies zombie ipak aliases/hardlinks
- Intended to repair lightweight install mismatches

Parameters:

- `-GameDir`

This is commonly called automatically by `launch_t6_offline.ps1`.

## `native/fx_runtime_probe/build_x86.ps1`

Purpose:

- Build the native x86 probe DLL and injector executable

Parameters:

- `-Configuration`
  - usually `Release`

Outputs:

- `native/fx_runtime_probe/bin/x86/<Configuration>/fx_runtime_probe_hook_<stamp>.dll`
- `native/fx_runtime_probe/bin/x86/<Configuration>/fx_runtime_probe_injector.exe`
- `native/fx_runtime_probe/bin/x86/<Configuration>/fx_runtime_probe_latest_build.json`

## `native/fx_runtime_probe/inject_latest.ps1`

Purpose:

- Resolve the latest built probe DLL
- Inject it into a target process by PID or name

Parameters:

- `-ProcessName`
- `-TargetPid`
- `-Configuration`
- `-Wait`

Examples:

```powershell
powershell -ExecutionPolicy Bypass -File native\fx_runtime_probe\inject_latest.ps1 `
  -ProcessName plutonium-bootstrapper-win32 `
  -Wait
```

```powershell
powershell -ExecutionPolicy Bypass -File native\fx_runtime_probe\inject_latest.ps1 `
  -TargetPid 12345
```

## `_build/build_bo3_rev_idg_probe.py`

Purpose:

- Main builder for the current BO3 Rev IDG / donor-shell runtime
- Generates fastfiles, runtime artifacts, loose script outputs, reports, watchlists, and probe manifests

Important:

- This script is primarily environment-driven, not argparse-driven.
- The normal way to use it is through PowerShell wrappers that set `ROGUE_*` variables.

Key outputs:

- `_build/bo3_rev_idg_probe/build_report.json`
- `_build/bo3_rev_idg_probe/xanim_reports/...`
- `mods/bo3_rev/...` loose outputs
- `native/fx_runtime_probe/active_probe_watchlist.txt`
- `native/fx_runtime_probe/xanim_runtime_expectations.txt`
- `native/fx_runtime_probe/xanim_runtime_patches.txt`

Key environment families:

- weapon / shell
  - `ROGUE_PROBE_SHELL`
  - `ROGUE_STARTER_WEAPON`
  - `ROGUE_FORCE_STOCK_SHELL`
  - `ROGUE_FORCED_STOCK_SHELL`
- model composition
  - `ROGUE_GUN_MODEL_MODE`
  - `ROGUE_FORCE_LOW_HANDMODEL`
  - `ROGUE_USE_CUSTOM_IDG_VIEWHANDS`
- animation emission
  - `ROGUE_BO3_ANIM_EMIT_MODE`
  - `ROGUE_BO3_ANIM_SUBSET`
  - `ROGUE_BO3_ANIM_STAGE`
  - `ROGUE_BO3_ANIM_RUNTIME_BACKEND`
  - `ROGUE_WEAPON_*_ANIM_OVERRIDE`
- probe/runtime debug
  - `ROGUE_NATIVE_PROBE_MODE`
  - `ROGUE_ANIM_PROBE_PHASE`
  - `ROGUE_RUN_LABEL`
- FX lane
  - `ROGUE_USE_BO3_RAW_FX`
  - `ROGUE_USE_BO3_SERVANT_CLIENT_FX`
  - `ROGUE_USE_BO3_FX_LOAD_FF`
- deploy/sync behavior
  - `ROGUE_DEPLOY_TO_MOD`
  - `ROGUE_DEPLOY_TO_BASE`
  - `ROGUE_SKIP_SCRIPT_SYNC`
  - `ROGUE_SKIP_MOD_LOAD_SYNC`
  - `ROGUE_SKIP_MOD_PATCH_SYNC`

If you want a reproducible build, prefer the wrapper scripts over calling this directly.

## Practical Runbooks

## Recreate a standard offline run

1. Validate install:

```powershell
powershell -ExecutionPolicy Bypass -File tools\validate_t6_zm_install.ps1
```

2. Repair ipak aliases if needed:

```powershell
powershell -ExecutionPolicy Bypass -File tools\repair_t6_zm_install_ipaks.ps1
```

3. Sync and launch:

```powershell
powershell -ExecutionPolicy Bypass -File tools\restart_t6_probe_cycle.ps1 -Launch
```

## Build a minimal animation runtime and launch it

```powershell
powershell -ExecutionPolicy Bypass -File tools\build_servant_minimal_anim_runtime.ps1 `
  -EmitMode bo3_frames `
  -AnimStage spawn `
  -AnimSubset vm_zod_id_gun_first_raise,vm_zod_id_gun_idle `
  -AnimProbePhase idle_first_raise `
  -Launch
```

## Build, sync, and then inject the probe

```powershell
powershell -ExecutionPolicy Bypass -File tools\restart_t6_probe_cycle.ps1 `
  -Launch `
  -InjectProbe `
  -ProbeMode xanim_asset_lookup_focus `
  -ProbeAttachGate idle_begin
```

## Capture a screenshot after launch

```powershell
powershell -ExecutionPolicy Bypass -File tools\capture_game_screenshot.ps1 `
  -OutputPath Z:\Games\pluto_t6_full_game\_build\captures\current.png `
  -CaptureMode window `
  -AllowScreenFallback
```

## Use the stock visibility harness

```powershell
powershell -ExecutionPolicy Bypass -File tools\run_stock_visibility_control.ps1 `
  -Launch `
  -CaptureScreenshot `
  -CaptureDelaySec 30 `
  -KillAfterCapture
```

## Probe Modes

Current modes surfaced by the wrappers:

- `safe`
  - lowest-risk mode
- `bootstrap_guard_only`
  - startup guard-only mode
- `render_opacity_focus`
  - render-table/submit-flags oriented
- `viewmodel_render_focus`
  - deferred render-family visibility probe
- `xanim_focus`
  - name/watch/touch oriented xanim tracing
- `xanim_consumer_focus`
  - consumer-side xanim tracing
- `xanim_asset_lookup_focus`
  - producer / asset-class lookup tracing
- `producer_compact_override_focus`
  - compact producer override tracing
- `class_family_materialization_writepath`
  - producer-to-selector writepath tracing

Mode file:

- `native/fx_runtime_probe/active_probe_mode.txt`

Watchlist file:

- `native/fx_runtime_probe/active_probe_watchlist.txt`

## Artifact Map

### Build artifacts

- `_build/bo3_rev_idg_probe/build_report.json`
- `_build/bo3_rev_idg_probe/xanim_reports/`
- `_build/bo3_rev_idg_probe/output/`

### Probe artifacts

- `native/fx_runtime_probe/bin/x86/Release/fx_runtime_probe.log`
- `native/fx_runtime_probe/bin/x86/Release/fx_runtime_probe_latest_build.json`
- `native/fx_runtime_probe/xanim_runtime_expectations.txt`
- `native/fx_runtime_probe/xanim_runtime_patches.txt`

### Visibility / screenshot artifacts

- `_build/visibility_live/`
- `_build/monitor_debug/`
- output PNG/JSON pairs from `capture_game_screenshot.ps1`

### Logs

- `C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\mods\bo3_rev\games_mp.log`
- `C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\mods\bo3_rev\console_zm.log`
- `C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\main\console_zm.log`
- `C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\launch_monitor_trace.log`

## Script Catalog

This section is for fast recognition. The descriptions below are intentionally short and name-driven.

## `tools/` catalog

### Analysis scripts

- `analyze_asset_lookup_entry_wrapper_compare.ps1`
- `analyze_asset_lookup_owner_family_compare.ps1`
- `analyze_asset_lookup_to_selector_materialization.ps1`
- `analyze_bridge_handoff_chains.ps1`
- `analyze_canonical_producer_selector_emission.ps1`
- `analyze_child4_clone_boundary.ps1`
- `analyze_child4_projection_materializer.ps1`
- `analyze_class_family_role_split.ps1`
- `analyze_common_parent_emitter.ps1`
- `analyze_consumer_child2_lookup_join.ps1`
- `analyze_grant_equip_family_bundle.ps1`
- `analyze_grant_equip_joined_mapping.ps1`
- `analyze_post_decode_child3_consumer.ps1`
- `analyze_probe_entry_wrapper_family_buckets.ps1`
- `analyze_probe_joined_subviews.ps1`
- `analyze_probe_selector_decode_consistency.ps1`
- `analyze_producer_first_distinct_render_bridge.ps1`
- `analyze_producer_to_selector_field_join.ps1`
- `analyze_render_root_local_correlation.ps1`
- `analyze_root_local_policy_tail.ps1`
- `analyze_selector_decode_tuple_consumer.ps1`
- `analyze_selector_dispatch_role_matrix.ps1`
- `analyze_selector_plus45_role_compare.ps1`
- `analyze_selector_plus45_tuple_pairing.ps1`
- `analyze_selector_policy_write_provenance.ps1`
- `analyze_selector_root_decode_ownership_compare.ps1`
- `analyze_selector_root_policy_window_compare.ps1`
- `analyze_semantic_root_decode_compare.ps1`
- `analyze_starter_clone_projection_link.ps1`
- `analyze_starter_probe_decode_child_symmetry.ps1`

These are mostly offline comparison / report scripts used to interpret archived probe captures.

### Build scripts

- `build_and_launch_anim_offline.ps1`
- `build_full_servant_runtime.ps1`
- `build_servant_idle_anim_runtime.ps1`
- `build_servant_minimal_anim_runtime.ps1`
- `build_servant_vortex_runtime.ps1`
- `build_zm_cosmodrome.ps1`

### Launch / sync / environment scripts

- `launch_t6_lan_offline_blocked.ps1`
- `launch_t6_offline.ps1`
- `restart_t6_probe_cycle.ps1`
- `stage_t6_custom_map_runtime_support.ps1`
- `validate_t6_zm_install.ps1`
- `repair_t6_zm_install_ipaks.ps1`
- `block_plutonium_network.ps1`
- `unblock_plutonium_network.ps1`

### Execution matrix scripts

- `run_animation_lane_determinism.ps1`
- `run_anim_debug_cycle.ps1`
- `run_anim_offline_probe_pass.ps1`
- `run_bridge_later_carry_forward_matrix.ps1`
- `run_bridge_to_first_producer_carry_forward_matrix.ps1`
- `run_bridge_to_first_producer_emitter_provenance.ps1`
- `run_consumer_child_state_matrix.ps1`
- `run_consumer_hit_sweep.ps1`
- `run_consumer_reference_compare.ps1`
- `run_consumer_semantic_transition_compare.ps1`
- `run_entry_return_bridge_override_matrix.ps1`
- `run_entry_wrapper_override_matrix.ps1`
- `run_idle_resolver_matrix.ps1`
- `run_practical_visible_motion_forcing.ps1`
- `run_producer_compact_override_matrix.ps1`
- `run_producer_first_distinct_causal_compare.ps1`
- `run_producer_hit2_causal_compare.ps1`
- `run_producer_pointer_ablation_matrix.ps1`
- `run_producer_pointer_family_override_matrix.ps1`
- `run_producer_target_family_writepath.ps1`
- `run_same_process_trio_transplant_matrix.ps1`
- `run_seed_to_first_producer_normalization.ps1`
- `run_stock_visibility_control.ps1`
- `run_visibility_snapshot.ps1`

These are the main batch experiment runners. The names are generally literal: each script runs a defined matrix or capture pass around one specific reverse-engineering question.

### Utility / capture / dump

- `capture_game_screenshot.ps1`
- `dump_t6_assets.ps1`

### Bundled executables / archives

- `gsc-tool.exe`
- `gsc-tool.zip`
- `game_mod.zip`
- `LinkerMod-1.0.0.zip`
- `oat-windows.zip`
- `texconv.exe`

## `native/fx_runtime_probe/` catalog

- `build_x86.ps1`
  - build the probe DLL and injector
- `inject_latest.ps1`
  - inject the latest built DLL
- `active_probe_mode.txt`
  - current mode selector
- `active_probe_watchlist.txt`
  - current watched names / models / assets
- `active_entry_wrapper_override.txt`
  - probe-side override input
- `active_producer_class_override.txt`
  - producer override input
- `active_producer_class_override_stability.txt`
  - producer override stability input
- `xanim_runtime_expectations.txt`
  - expected xanim/runtime contract text
- `xanim_runtime_patches.txt`
  - patch manifest text
- `README.md`
  - native probe overview
- `fx_runtime_probe_hook.cpp`
  - main probe implementation
- `fx_runtime_probe_injector.cpp`
  - injector source

## Recurring `_build/` entrypoints

Stable / recurring:

- `build_bo3_rev_idg_probe.py`
  - main builder
- `runtime_reset.ps1`
  - runtime cleanup/reset helper
- `test_local.ps1`
  - local test helper
- `deploy_t6_runtime_probe.py`
  - probe-related deploy helper
- `runtime_health_check.py`
  - runtime health checker
- `runtime_asset_audit.py`
  - runtime asset audit
- `compile_xanim_zone.py`
  - xanim/zone helper
- `patch_zone_xanims.py`
  - patch runtime xanim sections
- `strict_xanim_parser.py`
  - strict xanim parser

Experimental / ad hoc `_build` tools:

- image / material utilities:
  - `convert_textures.py`
  - `dds_to_iwi_t6.py`
  - `create_black_iwi.py`
  - `create_default_specular.py`
  - `fix_images_and_materials.py`
  - `fix_materials.py`
  - `fix_material_properties.py`
  - `fix_specular.py`
  - `update_thundergun_materials.py`
- GLB / model utilities:
  - `flatten_glb.py`
  - `scale_glb.py`
  - `inspect_glb.py`
  - `inspect_glb_nodes.py`
  - `rebuild_viewmodel_glb.py`
  - `rebuild_viewmodel_glb_slim.py`
  - `rebuild_min_viewhands_glb.py`
  - `rebuild_glb_scaled.py`
  - `rebuild_glb_t6_style.py`
  - `fix_glb_bindpose.py`
- animation / xanim utilities:
  - `compare_xanim_contracts.py`
  - `diagnose_xanim_layout.py`
  - `patch_xanim_carrier_alias.py`
  - `repatch_named_xanim.py`
  - `strip_xanims.py`
  - `wire_thundergun_anims.py`
  - `update_weapon_anims.py`
  - `fix_weapon_anims.py`
  - `revert_weapon_anims.py`
  - `xanim_roundtrip_oracle.py`
- runtime / FF / dump helpers:
  - `dump_zone_header.py`
  - `ff_integrity_check.py`
  - `preflight_deploy_ff.py`
  - `build_t6_ff_contract_probe.py`
  - `two_phase_build.py`
- focused investigations and one-off experiments:
  - many files prefixed `analyze_`, `tmp_`, `test_`, or `compare_`

Treat most `_build` Python scripts as experiment-specific unless they are already part of a wrapper path in `tools/`.

## Recreate Everything Checklist

If a new person is trying to reproduce the environment from scratch, do it in this order:

1. Read:
   - `docs/fullsummary.md`
   - `docs/enginemap.md`
   - `docs/handoff.md`
2. Validate the install:
   - `tools/validate_t6_zm_install.ps1`
3. Repair zombie ipak aliases if needed:
   - `tools/repair_t6_zm_install_ipaks.ps1`
4. Build the probe:
   - `native/fx_runtime_probe/build_x86.ps1`
5. Choose a lane:
   - stock visibility
   - minimal anim runtime
   - full Servant FX runtime
6. Sync and launch:
   - `tools/restart_t6_probe_cycle.ps1 -Launch`
7. Inject if needed:
   - `native/fx_runtime_probe/inject_latest.ps1`
8. Archive:
   - screenshot
   - `build_report.json`
   - game logs
   - probe log
   - watchlists / expectation files

## Notes On Reproducibility

- Prefer wrapper scripts over calling the Python builder directly.
- Archive the exact command you ran.
- Archive `build_report.json` after every meaningful run.
- When using the probe, archive:
  - `active_probe_mode.txt`
  - `active_probe_watchlist.txt`
  - `xanim_runtime_expectations.txt`
  - `xanim_runtime_patches.txt`
  - `fx_runtime_probe.log`
- Treat screenshots as authoritative for visibility claims.
