# FX Runtime Probe

Debug-only x86 runtime probe for T6/Plutonium client startup.

## What it does

- Installs x86 detours on asset-warning format-string call sites in the main module:
  - `Could not load fx "..."`
  - `Could not load material "..."`
  - `Could not load rawfile "..."`
  - `Waited ... for missing asset "..."`
  - `loadedfx could not find effect ...`
- Registers a vectored exception handler to log access violations before the process dies.
- Searches process memory for these exact watched asset strings and arms guard pages on them:
  - `zombie/fx_ffprobe_debug_orb_stock`
  - `bo3_rev_debug_stock_glow`
  - `effect_26z423jf`
  - `fxt_light_glow_square`
- Supports a narrower `render_opacity_focus` mode for render-table and submit-flags consumer traces, intended for investigating why a loaded effect renders with inconsistent opacity.
- Supports a `viewmodel_render_focus` mode that keeps the same lightweight render-side consumer coverage without the heavier xanim-consumer branch fanout.
- Supports an `xanim_focus` mode that watches xanim and xmodel names in memory and logs the code paths, registers, strings, raw pointer refs, and backtraces involved when those names are touched at runtime.

## Build

```powershell
powershell -ExecutionPolicy Bypass -File native/fx_runtime_probe/build_x86.ps1
```

## Inject

Inject into the actual live BO2/T6 process:

```powershell
powershell -ExecutionPolicy Bypass -File native/fx_runtime_probe/inject_latest.ps1 -ProcessName plutonium-bootstrapper-win32 -Wait
```

## Mode

Write `native/fx_runtime_probe/active_probe_mode.txt` before launching:

- `safe`
- `render_opacity_focus`
- `viewmodel_render_focus`
- `xanim_focus`
- `xanim_consumer_focus`
- `xanim_asset_lookup_focus`

The watchlist also accepts:

- `xanim=vm_zod_id_gun_idle`
- `xanim=vm_zod_id_gun_first_raise`
- `xanim=vm_zod_id_gun_fire`
- `xmodel=bo3_rev_v2_idg_view_...`
- `xmodel=bo3_rev_bridge_viewhands`

The restart wrapper will write this file for you.

## Log

The DLL writes:

- `native/fx_runtime_probe/bin/x86/Release/fx_runtime_probe.log`

Look for:

- `Installed hook`
- `format_ref_hit`
- `watch_found`
- `guard_hit`
- `xanim_focus targets=...`
- `stack_str ...`
- `access_violation`
- `stack ...`
- `stack_str[...]`
- `backtrace[...]`
