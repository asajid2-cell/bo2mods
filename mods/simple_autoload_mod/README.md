# Simple Auto-Load BO2 Mod

This mod installs one auto-loaded script for Plutonium T6 Zombies:

- `mod_i_am_mod.gsc`

## What It Does

- On first spawn, shows a loadout picker with 3 class choices.
- Each match, those 3 choices are randomly drawn from a themed class catalog of 20 archetypes.
- Each loadout contains:
  - 3 themed weapons from the current map weapon pool (including available upgrades/wonder weapons).
  - 1 random melee weapon from the current map melee pool.
  - 5 perks total with Juggernog guaranteed and the other 4 randomized.
- After selection, the player receives:
  - `10000` points
  - The chosen 3 weapons with max ammo
  - The chosen 5 perks

## Class Themes

- The picker UI color palette updates per selected class theme.
- Each class has:
  - custom title + subtitle
  - themed weapon tag preferences (used to bias weapon rolls)
  - themed UI colors for header/accent/sections

## Picker Controls

- `ADS` = previous loadout
- `ATTACK` = next loadout
- `USE` = confirm selection

If no selection is confirmed, the script auto-selects after a short timeout.

## Optional Dvars

- `mod_picker_text_scale` (default clamp target `1.00`)
  - hard-clamped to `1.00` .. `1.60`
  - use this if you want the picker text a little smaller/larger
- `mod_picker_debug` (default `0`)
  - `0` = normal
  - `1` = show debug probes + write truncation/debug entries to log

## Install

Run in PowerShell from this folder:

```powershell
.\install_mod.ps1
```

The installer copies scripts to:

`%LOCALAPPDATA%\Plutonium\storage\t6\scripts`
