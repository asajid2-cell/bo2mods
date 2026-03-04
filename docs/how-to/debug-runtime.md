# How-to: Debug Runtime (Lanes, Mods, Provenance)

Most “random” failures in this project were actually **runtime provenance** failures:
- the game read a fastfile from a different lane than the one you built
- multiple mods were enabled and fought over the same asset names
- baseline fastfiles were overwritten and never restored

This guide is the shortest path to proving what is loaded.

## 1) Reset runtime lanes
Run from repo root (`z:\\Games\\pluto_t6_full_game`):

Clean lane:
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode clean
```

Server-safe lane (explicit intent alias for clean):
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode server
```

Dev lane (one mod only):
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode dev -DevMod "zm_roguelike_panzer"
```

Audit (no mutations):
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode audit
```

### Recommended loops
Before joining public servers (guarantee nothing local can interfere):
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode server
```

Before local testing (make the mod show up + be loadable):
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode dev -DevMod "zm_roguelike_panzer"
python _build/two_phase_build.py
```

After you’re done testing and want to go back to servers:
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode server
```

## 2) Read the runtime_reset report
Each run emits:
- `_build/runtime_reset/<timestamp>/report.json`

Key fields to trust first:
- active mods in game path and storage path
- whether `so_zsurvival_zm_transit.ff` is baseline or modified
- existence of “autoload remnants” in storage

Note on mods:
- `clean` / `server` **quarantines mod folders** (moves them out of the `mods/` directory) so they:
  - do not appear in the in-game mod list
  - cannot be accidentally loaded when you join servers
- `dev` restores exactly one mod folder into `mods/` and quarantines the rest

Where quarantine goes:
- Storage mods quarantine:
  - `%LOCALAPPDATA%\\Plutonium\\storage\\t6\\_runtime_quarantine\\mods\\<timestamp>\\`
- Game install mods quarantine (only if enabled):
  - `z:\\Games\\pluto_t6_full_game\\_build\\runtime_quarantine\\game_mods\\<timestamp>\\`

By default, quarantine is applied to the **Plutonium storage** mods directory (this is the one that affects the in-game mod list).
If you also have runtime mods living under the game install `mods/` directory and need to quarantine/restore them too, pass:
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode server -ManageGameMods
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode dev -DevMod "zm_roguelike_panzer" -ManageGameMods
```

## 3) Health check the lane
```powershell
python _build/runtime_health_check.py
python _build/runtime_health_check.py --require-tg
```

## 4) Prove which fastfiles the engine loaded
In `console_zm.log`, look for:
- `Loading fastfile mod`
- `Loading fastfile mod_load`
- `Loading fastfile so_zsurvival_zm_transit`

If the game is loading `so_zsurvival_zm_transit` from base lane while you deployed only to mod lane, you will not see your changes.

## 5) Common failure signatures
`weapondef_unregistered`
- Your weapon asset may exist in the FF, but T6 hasn’t registered it in time.
- Workaround in this repo is the truth-alias carrier system.

`dobj ... has more than 160 bones`
- You exceeded the first-person DObj cap (gun + hands/viewhands).
- Fix is architectural, not “try another giveweapon”.

## 6) Don’t trust hot reload for xmodels
xmodels and viewmodel rigs can be cached.
If you are debugging viewmodel orientation or camera chains:
- fully restart the game between tests
