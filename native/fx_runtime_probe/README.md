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

## Build

```powershell
powershell -ExecutionPolicy Bypass -File native/fx_runtime_probe/build_x86.ps1
```

## Inject

Inject into the actual BO2/T6 game process:

```powershell
powershell -ExecutionPolicy Bypass -File native/fx_runtime_probe/inject_latest.ps1 -ProcessName t6zm.exe -Wait
```

## Log

The DLL writes:

- `native/fx_runtime_probe/bin/x86/Release/fx_runtime_probe.log`

Look for:

- `Installed hook`
- `format_ref_hit`
- `watch_found`
- `guard_hit`
- `access_violation`
- `stack ...`
- `stack_str[...]`
- `backtrace[...]`
