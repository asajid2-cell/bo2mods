# How-to: Build & Deploy

This guide is for the common “I changed something, build it, deploy it, and test it” loop.

## Build
From repo root:
```powershell
python _build/two_phase_build.py
```

## One-command local test loop
Run from repo root:
```powershell
powershell -ExecutionPolicy Bypass -File "_build/test_local.ps1"
```

This will:
- reset runtime to a safe dev lane (single active mod)
- rebuild + deploy with safe defaults (base deploy on, stub viewhands off)
- print the next in-game steps

### Common environment knobs
Deploy lanes:
- `ROGUE_DEPLOY_TO_MOD=1` (default)
- `ROGUE_DEPLOY_TO_BASE=0` (default; enable only when required)

### When you *must* deploy to base lane
Important T6 constraint: core map/survival fastfiles like `so_zsurvival_zm_transit.ff` are typically loaded from the **game install** `zone/all` path, not from the mod folder.

So if your change is inside `so_zsurvival_zm_transit.ff` (weapons/xmodels/xanims in that zone), and you don’t deploy to base, you’ll see “reverted” behavior at runtime (stock weapons, stock hands, no patched assets).

Typical “I need base lane too” run:
```powershell
$env:ROGUE_DEPLOY_TO_BASE = "1"
python _build/two_phase_build.py
```

### Server-safe workflow (recommended)
To test locally, then safely join servers afterwards:
```powershell
# Enable mod (local dev)
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode dev -DevMod "zm_roguelike_panzer"

# Build + deploy (enable base lane only while testing)
$env:ROGUE_DEPLOY_TO_BASE = "1"
python _build/two_phase_build.py

# When done testing and before joining servers
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode server
```

## What gets built
You should expect these logical outputs (exact staging paths can vary by profile/run):
- Patched survival/map FF: `so_zsurvival_zm_transit.ff`
- IPak: `so_zsurvival_zm_transit.ipak`
- Runtime custom xanim FF: `mod_load.ff`

Source of truth for a given run:
- `_build/reports/last_tg_build_manifest.json`

## Where it deploys
Mod lane (storage):
- `%LOCALAPPDATA%/Plutonium/storage/t6/mods/zm_roguelike_panzer/zone/all`

Base lane (game directory; only if enabled):
- `z:\Games\pluto_t6_full_game\zone\all`

## Verification (what to check first)
If it “builds” but runtime doesn’t change, assume a deployment mismatch and verify:
1) Which lane the game is reading from (base vs mod)
2) That the deployed FF actually contains the asset names you expect

The pipeline already runs a basic Unlinker verification step. If you need to do it manually:
- list: `Unlinker.exe --list <fastfile>`
- then search for:
  - `weapon,thundergun_zm`
  - `xmodel,rogue_tg_view`
  - `xanimparts,vm_thunder_gun_*`

## If deployment fails due to file locks
You can see warnings like “Permission denied” for `.ipak` or `.ff` when the game has the file open.

Fix:
- fully close the game
- rerun the build

## If you need a clean baseline
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode clean
```
