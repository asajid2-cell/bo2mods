# BO3 → BO2 (T7 → T6) Asset Porting — Thundergun Pipeline

This repo tracks a *working, reproducible* porting pipeline to bring Black Ops 3 (T7) assets into Black Ops 2 (T6 / Plutonium), starting with the **Thundergun** and a target mod (**`zm_roguelike_panzer`**).

It is intentionally set up as an **engineering notebook + build spine**:
- `mods/*` contains gameplay scripts (GSC) that exercise the ported assets at runtime.
- `_build/*` contains build/deploy/validation tooling (Python + PowerShell) that keeps experiments deterministic.
- `docs/` contains in-depth documentation in **Diátaxis** structure (tutorials / how-to / reference / explanation).

## What’s in scope
- Porting *asset containers* (models, materials/images, xanims) into T6-fastfile shape.
- Keeping runtime deterministic (base vs mod lanes, reset/audit tools).
- Debugging the *engine contracts* that block “looks right” viewmodels (bone cap, camera/tag basis, registration barriers).

## What is not in this repo
This repo does **not** include copyrighted game assets.
You must provide your own dumps/extracts (T7 source + T6 baselines) and configure paths as described in `docs/`.

## Current status (high level)
- The build pipeline can compile and deploy a patched `so_zsurvival_zm_transit.ff` + `.ipak`, and a runtime custom-xanim lane `mod_load.ff`.
- Thundergun assets are present in-zone (materials/images/models) and weapondefs are patched via a “truth alias” carrier weapon (for T6 registration constraints).
- **Active blocker:** first-person viewmodel behavior on equip (camera orientation / “flip behind you”) is still being debugged.

Details: `docs/status.md`.

## Quick start (dev lane)
See the full, reproducible flow in `docs/tutorials/getting-started.md`.

Common commands:
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode dev -DevMod "zm_roguelike_panzer"
python _build/two_phase_build.py
```

## Documentation
Start here: `docs/README.md`.

## Credits
Docs structure uses the Diátaxis framework: see `docs/credit.md`.

