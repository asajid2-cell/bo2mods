# Tutorial: Getting Started (Dev Loop)

This tutorial gets you from a fresh clone to a deterministic “build → deploy → test” loop, without contaminating base runtime.

## 0) Legal / asset note
This repo does **not** ship copyrighted assets. The pipeline assumes you have:
- A T6/BO2 runtime (Plutonium) installed
- Your own T6 baseline zone dumps / extracted assets
- Your own T7/BO3 dumps for the assets you want to port

## 1) Clone location and path expectations
Many scripts currently assume the repo is located at:
`z:\Games\pluto_t6_full_game`

If you relocate the repo, update hard-coded paths in `_build/*.py` (search for `z:\\Games\\pluto_t6_full_game`).

## 2) Choose your “lane”
This project is strict about runtime lanes:
- **clean lane**: baseline gameplay; no dev mods enabled
- **dev lane**: exactly one mod enabled for controlled testing

Use the lane tool:
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode clean
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode dev -DevMod "zm_roguelike_panzer"
```

## 3) Run the build spine
Run the build/deploy pipeline:
```powershell
python _build/two_phase_build.py
```

What it does (high-level):
- Resets/validates runtime state
- Builds weapondefs for the truth-alias carrier + thundergun entries
- Ensures the viewmodel GLB is structurally valid
- Stages xanim exports and compiles a runtime custom-xanim fastfile
- Builds patched `so_zsurvival_zm_transit.ff` + `.ipak`
- Deploys to mod lane (and optionally base lane)

## 4) Launch and reproduce
1. Launch Plutonium T6.
2. Load the mod and map.
3. Use the mod’s `.tg` path (or whichever debug path you’re currently using) to equip the thundergun carrier.

## 5) Collect the right log evidence
When something fails, capture:
- `console_zm.log` lines around the failure
- `[ROGUE]` event lines (these are designed to be “gate traces”)
- The build manifest:
  - `_build/reports/last_tg_build_manifest.json`
  - `_build/reports/preflight_so_zsurvival_zm_transit_*.json`

## 6) Next docs to read
- `docs/status.md` (what is currently blocked and why)
- `docs/how-to/build-and-deploy.md`
- `docs/how-to/debug-runtime.md`
- `docs/how-to/debug-viewmodel-flip.md`

