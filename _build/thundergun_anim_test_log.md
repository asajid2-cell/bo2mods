# Thundergun Animation Debug Log (BO3 -> BO2 T6)

## Goal
Stabilize custom thundergun animations in BO2/T6 without crashes, then expand coverage group-by-group.

## Current Status
- Root crashing anim identified: `vm_thunder_gun_first_raise`.
- Minimal baseline profile is stable in gameplay tests.
- We are now moving to additive testing (known-good baseline + one group at a time).

## Known Good (Confirmed)
Baseline stable profile:
1. `vm_thunder_gun_idle`
2. `vm_thunder_gun_fire`
3. `vm_thunder_gun_fire_ads`
4. `vm_thunder_gun_reload_empty`
5. `vm_thunder_gun_pullout`
6. `vm_thunder_gun_putaway`
7. `vm_thunder_gun_ads_base_up`
8. `vm_thunder_gun_ads_base_down`

Weapon-side stability remaps currently in place:
- `firstRaiseAnim -> vm_thunder_gun_pullout`
- `quickRaiseAnim -> vm_thunder_gun_pullout`
- `quickDropAnim -> vm_thunder_gun_putaway`

## Known Bad (Confirmed)
1. `vm_thunder_gun_first_raise` (real data causes crash)

Evidence:
- `4A` (`first_raise + idle`) crashed.
- `5A` (`first_raise` only real) crashed.

## Crash Signatures Seen
1. Immediate/early crash class (precache/weapon init path):
- `0xC0000005 @ 0x00485765`

2. Delayed runtime crash class (during gameplay/state transitions):
- `0xC0000005 @ 0x008DC435`
- last gsc pos reported: `maps/mp/zombies/_zm_powerups::powerup_hud_monitor`

## What We Tried So Far (Chronological)
1. Verified model path and weapon file cause for garbling vs non-garbling cases.
2. Stub-only XAnim entries (name-correct, empty data):
- weapon precache/load succeeded
- crash occurred when firing (expected due missing real fire anim)
3. Switched XAnim `assetType` to match vanilla style (`2`) and re-tested.
4. Single-entry isolation:
- only `vm_thunder_gun_idle` real => safe at load
- shooting crashes if fire remains stub
5. Full patch (all real entries) => crash returned.
6. Binary search round set (A/B) to locate offender:
- narrowed down to subset containing `first_raise`
- final isolation proved `vm_thunder_gun_first_raise` is crashing anim
7. Mitigation pass:
- excluded `first_raise` from real patch
- remapped `firstRaiseAnim` to `pullout`
8. Additional delayed runtime crash still observed under movement/prone conditions.
9. Strategy switched from pure bisect to additive known-good progression.
10. Built stable baseline with only core 8 real anims (listed above) and validated as safe.

## Test Matrix Snapshot (Recent)
- `2A` safe
- `2B` crash
- `3A` safe
- `3B` crash
- `4A` crash
- `5A` crash (first_raise only)

## Active Additive Plan
- Start from known-good baseline (8).
- Add one functional group at a time.
- If crash appears, bisect only inside that group.

Planned next group (movement):
- `vm_thunder_gun_sprint_in`
- `vm_thunder_gun_sprint_loop`
- `vm_thunder_gun_sprint_out`
- `vm_thunder_gun_slide_in`
- `vm_thunder_gun_slide_loop`
- `vm_thunder_gun_slide_out`
- `vm_thunder_gun_walk_f`
- `vm_thunder_gun_fall`
- `vm_thunder_gun_jump`
- `vm_thunder_gun_jump_land`

## Notes
- Keep `vm_thunder_gun_first_raise` excluded until separately repaired.
- Always patch from `unpatched_so_zsurvival_zm_transit.ff` for deterministic runs.

## Update 2026-02-18 22:48:06
- Latest additive movement group (baseline + sprint/slide/jump/fall/walk) **crashes**.
- User repro: crash happens **as soon as sprint starts**; idle/walk are fine.
- Next isolate order: `sprint_in` -> `sprint_loop` -> `sprint_out`.

## Update 2026-02-18 22:51:21
- Sprint isolate Stage 1 (`sprint_in` only real, loop/out->idle) **crashes immediately on sprint**.
- Conclusion: `vm_thunder_gun_sprint_in` is bad.
- Next: isolate `sprint_loop` with in/out forced to idle.

## Update 2026-02-18 22:57:42
- Sprint isolate Stage 2 (`sprint_loop` only real, in/out->idle) also **crashes on sprint**.
- Crash dump still matches delayed runtime AV pattern:
  - `Exception 0xC0000005 @ 0x008DC435`
  - `last gsc error: cannot cast undefined to bool`
  - `last gsc pos: _zm_powerups::powerup_hud_monitor` (or `_zm_playerhealth::playerhealthregen`)
- Interpretation: this signature is likely downstream fallout from malformed anim state data, not a direct scripting bug.

## Update 2026-02-19 (Current Baseline Re-Deploy)
- Re-deployed strict baseline profile (no custom sprint/crawl playback):
  - Real only: `idle`, `fire`, `fire_ads`, `reload_empty`, `pullout`, `putaway`, `ads_base_up`, `ads_base_down`
  - All sprint/crawl/dtp state refs remapped to `vm_thunder_gun_idle`
- Purpose: verify whether crouch/stand/shoot crashes are independent, or secondary after entering known-bad sprint states.

## Update 2026-02-19 (Root-Trace Instrumentation)
- New crash (`2026-02-18_11-18-48`) matches same signature:
  - `0xC0000005 @ 0x008DC435`
  - `cannot cast undefined to bool`
  - `_zm_powerups::powerup_hud_monitor`
- Added script-level guard + tracing in mod overrides:
  - `mods/zm_roguelike_panzer/maps/mp/zombies/_zm_powerups.gsc`
  - `mods/zm_roguelike_panzer/maps/mp/zombies/_zm_playerhealth.gsc`
- Guard behavior:
  - Coerces undefined bool inputs to safe defaults at known fault points
  - Emits `[ROGUE_BOOL]` traces (limited count) with weapon context when undefined is observed
- Goal:
  - Catch first undefined-bool origin in logs and stop crash chain long enough to identify root trigger.

## Update 2026-02-19 (Dive/Floor Impact Crash Follow-up)
- User repro: crash triggers when dolphin-diving and hitting the floor.
- Newest dump (`2026-02-18_11-31-34`) still matches:
  - `0xC0000005 @ 0x008DC435`
  - `cannot cast undefined to bool`
  - `_zm_powerups::powerup_hud_monitor`
- Patched likely undefined-bool source in `_zm_powerups::powerup_hud_monitor`:
  - `client_fields[...].solo` now defaults to `0` if undefined (no direct bool cast on undefined).
  - malformed powerup defs are skipped at registration if `time_name`/`on_name` are missing.
  - Added guard for missing `time_name` / `on_name` before clientfield evaluation.
  - Added bounded `[ROGUE_BOOL]` trace lines for both conditions.

## Update 2026-02-19 (Runtime-Path Bool Sanitizer in mod_i_am_mod)
- New crash (`2026-02-18_11-41-48`) changed last gsc pos to:
  - `_zm_playerhealth::playerhealthregen`
- Observation:
  - `games_mp.log` did not show `[ROGUE_BOOL]` lines from `_zm_powerups/_zm_playerhealth` overrides,
    suggesting those file overrides are not the active runtime source.
- Action moved to confirmed runtime script `scripts/mod_i_am_mod.gsc`:
  - Added `level thread rogue_bool_safety_sanitizer();` in `start_mod()`.
  - Sanitizer runs continuously and ensures per-player fields are always defined:
    - `player.flag`, `player.flags_lock`
    - `player.flag["player_has_red_flashing_overlay"]`
    - `player.flag["player_is_invulnerable"]`
    - `player.hurtagain`
  - Added powerup HUD definition sanitizer:
    - fills missing `.solo` with `0`
    - replaces missing `.time_name/.on_name` with safe fallback keys in `level.zombie_vars`
  - Added bounded `[ROGUE] event=bool_sanitize_*` logging for verification.

## Update 2026-02-19 (powerup_player_valid Safe Wrapper)
- Crash (`2026-02-18_11-49-18`) reverted to:
  - `_zm_powerups::powerup_hud_monitor`
  - `cannot cast undefined to bool`
- Root candidate in that function: callback cast
  - `if ( ![[ level.powerup_player_valid ]]( player ) )`
  - If callback returns `undefined`, this bool-cast crashes.
- Mitigation added in `scripts/mod_i_am_mod.gsc`:
  - `rogue_install_powerup_player_valid_wrapper()` installs once at runtime.
  - Wraps existing callback with `rogue_powerup_player_valid_safe(player)`.
  - If wrapped callback returns undefined, coerces to `true` and logs:
    - `event=bool_sanitize;msg=undef_ret=powerup_player_valid;...`
  - Added `event=bool_sanitize;msg=stage=start` startup marker to confirm sanitizer thread is active.

## Update 2026-02-19 (Pivot: _visionset_mgr::monitor Crash)
- Latest crash (`2026-02-18_11-58-35`) changed last gsc pos to:
  - `maps/mp/_visionset_mgr::monitor`
  - still `cannot cast undefined to bool`
- Action in `scripts/mod_i_am_mod.gsc`:
  - Build marker bumped to:
    - `id=2026-02-19-panzer-thundergun-v84-vsmgr-guard`
  - Disabled custom burn overlay registration during triage:
    - `rogue_register_burn_overlay_vsmgr()` call commented out
  - Added `rogue_sanitize_vsmgr_state()` and call inside sanitizer loop:
    - ensures `level.vsmgr[type].in_use` is always defined
    - ensures each `state.players[entnum].active/lerp` exists for connected players
    - initializes per-player `ref_count` when required
- Goal:
  - prevent undefined bool casts inside `_visionset_mgr::monitor` path and validate by new build marker.

## Update 2026-02-19 (Live Script Path Desync Found + Fixed)
- New crash (`2026-02-19_12-03-35`) still showed:
  - `0xC0000005 @ 0x008DC435`
  - `last gsc pos: _zm_powerups::powerup_hud_monitor`
- Root process issue discovered:
  - Runtime was loading scripts from `%LOCALAPPDATA%\\Plutonium\\storage\\t6\\mods\\zm_roguelike_panzer\\...`
  - While we had been editing `z:\\Games\\pluto_t6_full_game\\mods\\zm_roguelike_panzer\\...`
  - `games_mp.log` build marker confirmed old runtime script (`v83`) and no `bool_sanitize` markers.
- Fix applied:
  - Synced these files from workspace -> live `%LOCALAPPDATA%` mod folder:
    - `scripts/mod_i_am_mod.gsc`
    - `maps/mp/zombies/_zm_powerups.gsc`
    - `maps/mp/zombies/_zm_playerhealth.gsc`
  - Verified SHA256 hashes match after sync.
- Next validation target:
  - `games_mp.log` must now show:
    - `event=build;...id=2026-02-19-panzer-thundergun-v84-vsmgr-guard`
    - `event=bool_sanitize;msg=stage=start`

## Update 2026-02-19 (Shoot-Crash Safe Fire Repatch)
- Repatched from unpatched FF with patch-only safe profile.
- Real entries: idle, fire, fire_ads, reload_empty, pullout, putaway, ads_base_up, ads_base_down.
- Fire and fire_ads xanim_export were overridden with idle source data (safe_fire_dir) to eliminate shoot-time anim corruption while preserving fire refs.
- Output FF size: 18,705,600 bytes.
- Deployed to both game zone/all and Plutonium localappdata mod zone.


## 2026-02-19 - Shoot Isolation (idle+fire only)
- Goal: isolate shoot crash without remapping to non-BO3 anim names.
- Weapon refs kept BO3 names: fireAnim=vm_thunder_gun_fire, adsFireAnim=vm_thunder_gun_fire_ads.
- FF patch profile: --patch-only vm_thunder_gun_idle vm_thunder_gun_fire
- Real xanim entries: idle, fire.
- Stub entries: all other vm_thunder_gun_* (including fire_ads).
- Output FF: 18,703,616 bytes deployed to zone/all and LocalAppData mod path.
- Test instruction: hip-fire only first (do not ADS fire in this pass).

## 2026-02-19 - Powerup HUD Monitor Hard Disable
- New dump (2026-02-19_12-44-24) still: cannot cast undefined to bool at _zm_powerups::powerup_hud_monitor.
- Applied hard kill-switch in maps/mp/zombies/_zm_powerups.gsc: powerup_hud_monitor() returns immediately.
- Synced to runtime path: %LOCALAPPDATA%/Plutonium/storage/t6/mods/zm_roguelike_panzer/maps/mp/zombies/_zm_powerups.gsc.
- Goal: eliminate recurring 0x008DC435 bool-cast crash path entirely while continuing thundergun anim isolation.


## 2026-02-19 - Rampage Bookmark Kill-Switch (v85)
- New dump 2026-02-19_01-02-56 still: cannot cast undefined to bool at maps/mp/zombies/_zm::watch_rampage_bookmark.
- Added hard runtime kill-switch in mod_i_am_mod.gsc: force level.rampage_bookmark_kill_times_count = 0.
- Called once at startup and continuously in rogue_bool_safety_sanitizer loop.
- Build marker updated: id=2026-02-19-panzer-thundergun-v85-rampage-killswitch.
- Synced script to LocalAppData runtime mod path.


## 2026-02-19 - VisionSet Monitor Hardening
- New dump 2026-02-19_01-09-39: cannot cast undefined to bool @ maps/mp/_visionset_mgr::monitor.
- Added explicit mod override: mods/zm_roguelike_panzer/maps/mp/_visionset_mgr.gsc (copied from official ZM1 core and hardened).
- Guarded undefined access in: on_player_connect(), monitor(), get_first_active_name(), update_clientfields().
- Synced patched _visionset_mgr.gsc to LocalAppData runtime mod path.


## 2026-02-19 - PlayerHealth Regen Kill-Switch
- Dump 2026-02-19_01-44-08: cannot cast undefined to bool @ maps/mp/zombies/_zm_playerhealth::playerhealthregen.
- Applied hard kill-switch in mods/zm_roguelike_panzer/maps/mp/zombies/_zm_playerhealth.gsc: playerhealthregen() returns immediately.
- Synced to LocalAppData runtime mod path.


## 2026-02-19 - Core _zm Rampage Watcher Disabled
- Verified patches are applying via console build marker: v85-rampage-killswitch.
- Dump 2026-02-19_01-48-37 still at maps/mp/zombies/_zm::watch_rampage_bookmark.
- Added explicit mod override maps/mp/zombies/_zm.gsc from official ZM1 core and kill-switched watch_rampage_bookmark() with immediate return.
- Synced override to LocalAppData runtime mod path.


## 2026-02-19 - Rampage Watchdog (v86)

## 2026-02-22 - Strict Parser + Donor Proxy
- Added strict pointer-walk parser:
  - `_build/strict_xanim_parser.py`
  - Supports recursive `deltaPart` parsing and relative-base alignment.
- Validated patched FF structure:
  - All `vm_thunder_gun_*` entries strict-parse successfully (28/28).
  - Report: `_build/donor_blobs/strict_parse_report_patched.json`
- Added donor-FF replacement mode to `_build/patch_zone_xanims.py`:
  - `--donor-ff`, `--donor-zone-name`, `--donor-asset`
  - per-target overrides: `--donor-override target=donor`
  - optional fallback for missing donor scriptstrings:
    - `--donor-allow-missing-strings`
- All-Minigun-Idle proxy build executed:
  - Donor source: `zm_transit.ff` -> `viewmodel_minigun_t6_idle`
  - Target: all 28 `vm_thunder_gun_*` stubs
  - Output size: `18,706,688`
  - Patched 28/28 (verification: 0 empty stubs remain)
  - 9 donor scriptstrings missing in target zone were mapped to index `0` in fallback mode.
- Idle->Fire state-proxy variant prepared:
  - Output: `_build/panzer_work/output/so_zsurvival_zm_transit_proxy_state.ff`
  - Donor overrides:
    - `vm_thunder_gun_fire -> viewmodel_minigun_t6_fire`
    - `vm_thunder_gun_fire_ads -> viewmodel_minigun_t6_fire`
  - Output size: `18,707,840`
  - Deployed to active load paths on 2026-02-22:
    - `zone/all/so_zsurvival_zm_transit.ff` (`18,707,840`)
    - `%LOCALAPPDATA%/Plutonium/storage/t6/mods/zm_roguelike_panzer/zone/all/so_zsurvival_zm_transit.ff` (`18,707,840`)
  - Previous deployed proxy backup:
    - `*.bak_proxy_prev_20260222_011829` (`18,706,688`)

## 2026-02-22 - Proxy Swap: TG-Idle-All
- User reported upside-down camera / stretched pose on give while state-proxy build was active.
- Deployed alternate proxy build:
  - Source: `_build/panzer_work/output/so_zsurvival_zm_transit_proxy_tg_idle_all.ff`
  - Strategy: all 28 `vm_thunder_gun_*` slots use donor payload `vm_thunder_gun_idle`
    extracted from same-zone donor ff (`so_zsurvival_zm_transit_single_idle_donor.ff`)
  - Deployed size: `18,706,176`
  - Paths:
    - `zone/all/so_zsurvival_zm_transit.ff`
    - `%LOCALAPPDATA%/Plutonium/storage/t6/mods/zm_roguelike_panzer/zone/all/so_zsurvival_zm_transit.ff`
  - Backups of previous state-proxy deployment:
    - `*.bak_state_prev_20260222_012828` (`18,707,840`)

## 2026-02-22 - Minimal State Donor Test (Give-Path Focus)
- Objective: reduce stream growth and only replace actively used weapon-state slots.
- Build: `_build/panzer_work/output/so_zsurvival_zm_transit_state_minimal.ff`
- Donor source: `zm_transit.ff`
  - default donor: `viewmodel_m1911_idle`
  - overrides:
    - `vm_thunder_gun_pullout -> viewmodel_m1911_pullout`
    - `vm_thunder_gun_putaway -> viewmodel_m1911_putaway`
    - `vm_thunder_gun_fire -> viewmodel_m1911_fire`
    - `vm_thunder_gun_fire_ads -> viewmodel_m1911_fire`
- Patch scope (`--patch-only`): idle, pullout, putaway, fire, fire_ads.
- Resulting FF size: `18,716,544`
- Deployed to:
  - `zone/all/so_zsurvival_zm_transit.ff`
  - `%LOCALAPPDATA%/Plutonium/storage/t6/mods/zm_roguelike_panzer/zone/all/so_zsurvival_zm_transit.ff`

## 2026-02-22 - Minimal State Donor (No Fire Camera Transform)
- User result on prior minimal donor: give succeeded, shooting flipped camera upside-down then crashed.
- New build created to remove fire camera donor influence:
  - Output: `_build/panzer_work/output/so_zsurvival_zm_transit_state_minimal_no_firecam.ff`
  - Same give donors as previous:
    - `pullout -> viewmodel_m1911_pullout`
    - `putaway -> viewmodel_m1911_putaway`
  - Fire donors changed:
    - `fire -> viewmodel_m1911_idle`
    - `fire_ads -> viewmodel_m1911_idle`
  - Patch scope still only: idle, pullout, putaway, fire, fire_ads
  - Output size: `18,714,688`
- Deployed to both active paths:
  - `zone/all/so_zsurvival_zm_transit.ff`
  - `%LOCALAPPDATA%/Plutonium/storage/t6/mods/zm_roguelike_panzer/zone/all/so_zsurvival_zm_transit.ff`

## 2026-02-22 - Full Coverage No-Stub Variant
- Trigger: user repro showed sprint/dive crashes before shooting with minimal build.
- New strategy: eliminate all zero-frame transition targets by giving all 28 slots non-stub payloads.
- Build:
  - `_build/panzer_work/output/so_zsurvival_zm_transit_fullcover_no_stub.ff`
  - Default donor for all slots: `viewmodel_m1911_idle`
  - Give-path overrides:
    - `vm_thunder_gun_pullout -> viewmodel_m1911_pullout`
    - `vm_thunder_gun_putaway -> viewmodel_m1911_putaway`
  - Fire/fire_ads kept on idle donor to avoid fire camera roll.
  - Output size: `18,717,440`
- Deployed to both active paths:
  - `zone/all/so_zsurvival_zm_transit.ff`
  - `%LOCALAPPDATA%/Plutonium/storage/t6/mods/zm_roguelike_panzer/zone/all/so_zsurvival_zm_transit.ff`

## 2026-02-19 - Deep Pivot: Deterministic Donor Payload Build
- Re-validated latest dump signature remains unstable/runtime-hopping:
  - `0xC0000005 @ 0x008DC435`
  - `cannot cast undefined to bool`
  - last gsc pos alternates (`_visionset_mgr::monitor`, `_zm::watch_rampage_bookmark`, `_zm_playerhealth::playerhealthregen`)
- This pattern is treated as downstream state corruption, not one script bug.
- Confirmed intrusive core override files are currently absent in both workspace and LocalAppData paths:
  - `maps/mp/zombies/_zm.gsc`
  - `maps/mp/_visionset_mgr.gsc`
  - `maps/mp/zombies/_zm_playerhealth.gsc`
  - `maps/mp/zombies/_zm_powerups.gsc`
- Added new patcher mode in `_build/patch_zone_xanims.py`:
  - `--donor-anim <name>`
  - behavior: patch all `vm_thunder_gun_*` names, but use one known source anim payload for every entry while preserving each target name string.
- Built and deployed deterministic donor FF:
  - command donor: `vm_thunder_gun_idle`
  - patched entries: all 28 (`vm_thunder_gun_*`)
  - output FF size: `18,705,920` bytes
  - deployed to:
    - `z:\\Games\\pluto_t6_full_game\\zone\\all\\so_zsurvival_zm_transit.ff`
    - `%LOCALAPPDATA%\\Plutonium\\storage\\t6\\mods\\zm_roguelike_panzer\\zone\\all\\so_zsurvival_zm_transit.ff`
- Purpose:
  - remove per-animation source variability and mixed real/stub behavior
  - if crash persists, root is structural in generated XAnimParts format itself
  - if crash stops, root is specific bad source xanim payload(s)

## 2026-02-19 - Donor Rollback to Core-8 Baseline
- User repro on donor build: immediate crash on equip/pullout.
- Latest dump (`2026-02-19_02-25-58`) still same class:
  - `0xC0000005 @ 0x008DC435`
  - `cannot cast undefined to bool`
  - `last gsc pos: maps/mp/zombies/_zm_playerhealth::playerhealthregen`
- Rolled back from donor profile to known functional Core-8 patch profile:
  - real: `idle`, `fire`, `fire_ads`, `reload_empty`, `pullout`, `putaway`, `ads_base_up`, `ads_base_down`
  - rest: stubs with corrected names
- Rebuilt from `unpatched_so_zsurvival_zm_transit.ff` and deployed:
  - FF size: `18,706,688`
  - `zone/all/so_zsurvival_zm_transit.ff`
  - `%LOCALAPPDATA%/Plutonium/storage/t6/mods/zm_roguelike_panzer/zone/all/so_zsurvival_zm_transit.ff`

## 2026-02-19 - Structural Fix Attempt: deltaPart Stub Emission
- Root-format hypothesis: generated XAnimParts were missing `deltaPart` payload while T6 template declares `set count deltaPart 1`.
- Patched `_build/patch_zone_xanims.py`:
  - set header `deltaPart` pointer to `PTR_FOLLOWING`
  - emit minimal `XAnimDeltaPart` bytes in stream order:
    - `trans = NULL`
    - `quat2 = NULL`
    - `quat = NULL`
  - inserted after `names` (and after notify slot) per reorder.
- Full all-anim rebuild from clean unpatched FF:
  - patched 28/28
  - output FF: `18,720,512`
  - deployed to both `zone/all` and `%LOCALAPPDATA%` mod zone path.
- Test target:
  - verify whether this removes immediate/equip/runtime corruption without disabling BO3 animation references.

## 2026-02-19 - Structural Fix Attempt 2: Pointer-Section Alignment
- New hypothesis: serialized pointer-following payload was missing type alignment boundaries.
- Patched `_build/patch_zone_xanims.py` to align section starts in stream:
  - `names` -> align 2
  - `deltaPart` -> align 4
  - `dataByte` -> align 1
  - `dataShort` -> align 2
  - `dataInt` -> align 4
- Kept prior `deltaPart` minimal stub (`trans/quat2/quat = NULL`) with `PTR_FOLLOWING`.
- Full all-anim rebuild from clean unpatched FF:
  - patched 28/28
  - output FF: `18,720,576`
  - deployed to both `zone/all` and `%LOCALAPPDATA%` mod zone path.
- Verified patches are loading from LocalAppData (build marker present in console.log).
- Crash still at maps/mp/zombies/_zm::watch_rampage_bookmark (2026-02-19_01-48-37).
- Replaced rampage kill-switch strategy with strict normalization + per-player watchdog in mod_i_am_mod.gsc.
- Changes: keep rampage count sane (1..8, default 3), initialize globals, sanitize on connected, and add per-player 0.01s watchdog thread.
- Build marker updated: id=2026-02-19-panzer-thundergun-v86-rampage-watchdog.

## 2026-02-22 - Protocol Zero (All 28 Non-Stub, Give-Path Safe Overrides)
- Trigger: give-path regressed (flipped camera + hand geometry + crash on give) on 18,717,376 build.
- New deterministic build to eliminate null-state transitions while keeping camera safer:
  - Output: `_build/panzer_work/output/so_zsurvival_zm_transit_protocol_zero.ff`
  - Size: `18,719,296`
  - Donor source: `zone/all/zm_transit.ff`
  - Default donor for all 28: `viewmodel_m1911_idle`
  - Give-path overrides:
    - `vm_thunder_gun_first_raise -> viewmodel_m1911_pullout`
    - `vm_thunder_gun_pullout -> viewmodel_m1911_pullout`
    - `vm_thunder_gun_pullout_quick -> viewmodel_m1911_pullout`
    - `vm_thunder_gun_putaway -> viewmodel_m1911_putaway`
    - `vm_thunder_gun_putaway_quick -> viewmodel_m1911_putaway`
  - Patch scope: all 28 `vm_thunder_gun_*` entries (no stubs)
  - Donor fallback mapped 8 missing scriptstrings to index 0 (`--donor-allow-missing-strings`)
- Deployed to:
  - `zone/all/so_zsurvival_zm_transit.ff`
  - `%LOCALAPPDATA%/Plutonium/storage/t6/mods/zm_roguelike_panzer/zone/all/so_zsurvival_zm_transit.ff`
## 2026-02-22 - Protocol Zero Strict Strings (No donor fallback-to-0)
- Root issue: donor mode previously mapped missing scriptstrings to index 0 (`--donor-allow-missing-strings`), which can remap tracks onto wrong bones/camera.
- Tool fix in `_build/patch_zone_xanims.py`:
  - Added donor required-string collection (`_collect_required_donor_strings`).
  - In donor mode (without allow-missing), auto-expands target string table before patching.
  - Re-parses zone header/string table after expansion so offsets remain correct.
- Build:
  - `_build/panzer_work/output/so_zsurvival_zm_transit_protocol_zero_strict_strings.ff`
  - Size: `18,720,704`
  - Added 8 donor scriptstrings to target table (stringCount 364 -> 372).
  - Patched all 28 slots non-stub with same give-path overrides as Protocol Zero.
  - No donor missing-string fallback used.
- Deployed to:
  - `zone/all/so_zsurvival_zm_transit.ff`
  - `%LOCALAPPDATA%/Plutonium/storage/t6/mods/zm_roguelike_panzer/zone/all/so_zsurvival_zm_transit.ff`
## 2026-02-22 - Rollback: strict-strings build rejected
- User hit load-time script compile errors:
  - unresolved external "precache" with 0 params in `maps/mp/zm_transit.gsc` line 1.
- This occurred only on `so_zsurvival_zm_transit_protocol_zero_strict_strings.ff` (string-table-expanded build).
- Rolled back deployment to prior non-expansion build:
  - `_build/panzer_work/output/so_zsurvival_zm_transit_protocol_zero.ff`
  - deployed FF size: `18,719,296` to both active paths.
- Interpretation: in-zone string table insertion still corrupts scriptparsetree/linking; do not use string-table expansion path in production test builds.
## 2026-02-22 - Baseline rollback for crash signature isolation
- Latest dump (`2026-02-22_08-22-48`) still showed:
  - `0xC0000005 @ 0x004601F0`
  - unresolved external `precache` in `maps/mp/zm_transit.gsc` line 1
  - undefined->bool fallout in `_zm_powerups::powerup_hud_monitor`
- Deployed known-clean baseline FF to both active paths to isolate script-parse marker origin:
  - Source: `zone/all/so_zsurvival_zm_transit_base.ff`
  - Active `so_zsurvival_zm_transit.ff` size now `17,910,720` in game + LocalAppData mod path.
- Note: attempted external carrier build path (`two_phase_build.py` + custom `thundergun_xanims.ff`) currently fails in linker with inflate `-3` while loading stream(s), so custom writer FF is not yet valid for OAT `--load`.
## 2026-02-22 - Pipeline hardening implemented
- Added offline integrity gate script: `_build/ff_integrity_check.py`
  - checks decrypt completeness, xfile header length consistency, script marker consistency, stub scan.
  - supports `--strict-counts` fail mode.
- Added preflight deploy guard: `_build/preflight_deploy_ff.py`
  - refuses deployment if integrity check fails.
- Updated `_build/compile_xanim_zone.py`:
  - added `--neutralize-bones` (default: `tag_player tag_camera tag_origin`).
  - neutralizes those tracks in parsed xanim frames before emit.
  - updated XChunk writer boundary accounting to start at `FASTFILE_HEADER_SIZE` and modulo 512KB boundary.
- Updated `_build/two_phase_build.py`:
  - custom xanim FF compile now passes `--neutralize-bones tag_player tag_camera tag_origin`.
  - added preflight gate (`run_preflight`) before deployment.
  - preflight reports written to `_build/reports`.
- Verification:
  - Python compile checks passed for updated scripts.
  - standalone `compile_xanim_zone.py` runs and reports neutralized track writes.
- Current blocker remains:
  - `two_phase_build.py` still fails Phase 1 linker load with `inflate ... -3` while loading `--load thundergun_xanims.ff`.
  - this indicates custom carrier FF serialization still incompatible with OAT linker expectations.
## 2026-02-23 - Baseline load-FF fallback gate (inflater blocker resolved for build loop)
- Root cause isolated for current linker failures: baseline load FF selection, not xanim patching.
  - `zone/all/so_zsurvival_zm_transit.ff.vanilla_save` consistently fails linker load with `inflate ... -3`.
  - `zone/all/so_zsurvival_zm_transit.ff` also fails (`Loading fastfile failed ... STREAMER_RESERVE offset`).
  - `_build/ff_backup/20260213-123213/so_zsurvival_zm_transit.ff` loads successfully.
- Updated `_build/two_phase_build.py`:
  - `USE_CUSTOM_XANIM_FF` default set to `False` (carrier path remains experimental).
  - Added baseline load candidates + automatic fallback/retry on load errors:
    - detect `inflate of stream failed` and `Loading fastfile failed`.
    - auto-switch `SO_SURVIVAL_LOAD_FF` and retry Phase 1 build.
  - Added hard fallback candidate path:
    - `_build/ff_backup/20260213-123213/so_zsurvival_zm_transit.ff`.
- Result:
  - `py -3 two_phase_build.py` now completes end-to-end again without manual monkeypatching.
  - Phase 1 auto-fallback selects working baseline FF.
  - Phase 2 build succeeds.
  - Phase 3 patch succeeds (23 thundergun stubs patched in this baseline family).
  - Preflight passes and deploy completes to game + LocalAppData mod paths.
- Additional carrier work done:
  - `_build/compile_xanim_zone.py` now supports `--crypto-seed`.
  - `_build/two_phase_build.py` custom carrier compile passes explicit seed and validates decrypted payload shape.
  - External `--load` carrier still unresolved and not used in default pipeline.
