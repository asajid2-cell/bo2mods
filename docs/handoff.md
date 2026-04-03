# Handoff

This document is the full handoff for the BO3/T7 -> BO2/T6 porting project in this repo, with the Apothicon Servant and BO3 animation port as the active case study.

It is written for a new contributor who is starting from zero and needs to understand:

- what this repo is for,
- what has already been proven,
- what tooling exists,
- what dead ends have already been explored,
- what the current blocker is,
- and how to continue from the exact point where the project was left.

This file should be read together with:

- `docs/fullsummary.md`
- `docs/status.md`
- `docs/reference/repo-layout.md`
- `docs/how-to/build-and-deploy.md`
- `native/fx_runtime_probe/README.md`
- `_build/bo3_rev_idg_probe/build_report.json`

## 1. Project purpose

The project goal is not just to swap art assets into BO2.

The actual goal is to understand and satisfy the real BO2/T6 runtime contract well enough that BO3/T7-origin content can:

- load,
- be accepted by the T6 engine,
- render,
- behave correctly,
- and eventually animate correctly,

inside a real live T6 runtime.

The Apothicon Servant is the current active testbed, but it is not the whole project. The Servant is being used because it stresses almost every hard part of the problem at once:

- custom weapon visuals,
- foreign materials and images,
- foreign FX,
- foreign gameplay semantics,
- first-person composition,
- and foreign animation data.

## 2. What the repo has already accomplished

The project has already moved through multiple real milestones.

### 2.1 Donor-shell weapon identity

The early project established the donor-shell strategy:

- T6 does not reliably behave like a fresh custom weapon registration environment.
- A stock runtime-recognized weapon identity must usually be used as the accepted shell.
- Foreign content can then be layered into that shell.

This led to the donor-shell / truth-alias model:

- choose a real T6 weapon shell,
- override/stage its data,
- use that shell as the engine-accepted runtime contract.

That pattern remains central to the whole repo.

### 2.2 BO3 FX and gameplay

The FX side is the strongest completed part of the project.

What has been proven:

- BO3/T7-derived FX can be translated and made acceptable to T6.
- BO3 images/materials do not just work raw; they need normalization and policy.
- The full Servant vortex lane can render in the live runtime.
- The old crash lane involving loose global staged images in `storage\\t6\\images` was isolated and fixed.
- The client FX bridge was stabilized.
- The visible MG08 bridge model was removed in favor of a neutral bridge at `tag_origin`.
- The gameplay loop for the Servant black-hole effect works in BO2.
- Repeated shots can replace the active vortex instead of silently doing nothing.

The repo therefore already proves:

- model and surface staging,
- FF/IPAK packaging,
- client/server scripting,
- runtime deployment,
- and live in-game BO3-derived FX behavior.

### 2.3 Runtime probe infrastructure

The project also built a substantial runtime probe system, primarily for:

- FX debugging,
- xanim debugging,
- xmodel/runtime reference tracing,
- and byte-level contract comparison.

That probe is now one of the core project tools.

## 3. What the project is doing now

The current active problem is BO3 first-person animation porting.

The repo is trying to make BO3/T7-derived first-person animation data play correctly in T6 for the Servant lane.

The active practical target is:

- a custom gun model derived from BO3 content,
- on a stock-accepted T6 first-person shell,
- with BO3-derived animation content staged under T6 runtime backend names,
- actually being selected and played by the engine.

This is much harder than the FX problem, because T6 appears to care deeply about:

- XAnimParts header shape,
- section layout,
- bone counts and ordering,
- flags like loop/delta/delta3D,
- pointer presence such as `deltaPart`,
- and overall contract coherence.

## 4. Repo layout: what matters

This repo lives inside the BO2 game root on purpose. Many scripts read and write live runtime paths.

The important tracked areas are:

### 4.1 `mods/bo3_rev/`

Active mod source.

This contains:

- the rendered/templated GSC used by the live build,
- clientscript sources,
- mod UI overrides,
- supporting zombie scripts and character scripts.

Important files:

- `mods/bo3_rev/scripts/mod_i_am_mod.gsc`
- `mods/bo3_rev/scripts/mod_i_am_mod.gsc.in`
- `mods/bo3_rev/clientscripts/mp/zombies/_zm.csc`
- `mods/bo3_rev/clientscripts/mp/zm_transit.csc`
- `mods/bo3_rev/scripts/mp/zombies/_zm_spawner.gsc`

### 4.2 `_build/`

This is the orchestration and build logic layer.

Important files:

- `_build/build_bo3_rev_idg_probe.py`
- `_build/compile_xanim_zone.py`
- `_build/run_bo3_rev_probe_case.py`
- `_build/build_bo3_rev_idg_reduced_rig.py`
- `_build/build_bo3_rev_idg_weapon_only_rig.py`

Important generated output tree:

- `_build/bo3_rev_idg_probe/`

This generated tree contains:

- staged xmodels,
- staged xanim exports,
- runtime xanim exports,
- built FFs/IPAKs,
- reports,
- probe payloads,
- and current build diagnostics.

### 4.3 `tools/`

This contains the operator entrypoints.

Important files:

- `tools/build_servant_vortex_runtime.ps1`
- `tools/build_servant_minimal_anim_runtime.ps1`
- `tools/launch_t6_offline.ps1`
- `tools/run_anim_offline_probe_pass.ps1`
- `tools/restart_t6_probe_cycle.ps1`

### 4.4 `tools/asset_port_pipeline/`

Reusable conversion and Blender workers.

Important files:

- `tools/asset_port_pipeline/blender_idg_reduce_worker.py`
- `tools/asset_port_pipeline/blender_rebake_xanim_worker.py`
- `tools/asset_port_pipeline/translate_bo3_materials_to_bo2.py`

### 4.5 `native/fx_runtime_probe/`

Native runtime probe source and helper scripts.

Important files:

- `native/fx_runtime_probe/fx_runtime_probe_hook.cpp`
- `native/fx_runtime_probe/README.md`
- `native/fx_runtime_probe/build_x86.ps1`
- `native/fx_runtime_probe/inject_latest.ps1`
- `native/fx_runtime_probe/active_probe_watchlist.txt`
- `native/fx_runtime_probe/xanim_runtime_expectations.txt`
- `native/fx_runtime_probe/xanim_runtime_patches.txt`

### 4.6 `docs/`

Current documentation.

Important files:

- `docs/fullsummary.md`
- `docs/status.md`
- `docs/reference/repo-layout.md`
- `docs/reference/env-vars.md`
- `docs/how-to/build-and-deploy.md`
- `docs/servant-dossier.html`

## 5. Current architecture

The active animation lane is built around a few key decisions.

### 5.1 Runtime carrier weapon

Current accepted runtime carrier:

- `mg08_zm`

This is not because MG08 is aesthetically right. It is because it is a workable accepted T6 Zombies weapon shell for the current first-person path.

### 5.2 Current first-person composition strategy

The current build is not trying to force a custom bridge viewhands shell as the primary live shell.

Instead, the lane now prefers:

- stock survivor hand shell,
- custom BO3-derived gun model,
- BO3-derived xanim data staged under T6 runtime backend names,
- live evaluation on a stock-accepted shell.

This shift happened because:

- the old `bo3_rev_bridge_viewhands` forcing path was repeatedly rejected by runtime `setviewmodel()` attempts,
- and the weapon `handModel` field by itself did not prove to be the true owner of the live first-person shell in the town survival lane.

### 5.3 Current shell/model strategy

The active model contract in recent builds is:

- `gunModel = bo3_rev_v2_idg_view_<build_tag>`
- `handModel = c_zom_hazmat_viewhands` in the staged weapon fields

Important nuance:

- even when the build stages `c_zom_hazmat_viewhands`,
- live runtime has still been observed using stock survivor variants such as:
  - `c_zom_reporter_viewhands`
  - `c_zom_engineer_viewhands`
  - `c_zom_farmgirl_viewhands`

So staged `handModel` is not the whole story. Live survivor character state still matters.

### 5.4 Current animation naming strategy

Current intended runtime backend family:

- `viewmodel_zomb_mg08_idle`
- `viewmodel_zomb_mg08_first_raise`
- `viewmodel_zomb_mg08_fire`
- `viewmodel_zomb_mg08_ads_fire`
- `viewmodel_zomb_mg08_pullout`
- `viewmodel_zomb_mg08_pullout_quick`
- `viewmodel_zomb_mg08_putaway`

BO3 semantic source family:

- `vm_zod_id_gun_idle`
- `vm_zod_id_gun_first_raise`
- `vm_zod_id_gun_fire`
- `vm_zod_id_gun_pullout`
- and related semantic names

The current target-runtime lane is supposed to:

- compile or rebake BO3 semantic source exports,
- reorder them into donor/T6-compatible backend-name contracts,
- and ship only the backend-name family as the active runtime family.

## 6. Historical path to the current animation strategy

The animation work went through several phases.

### 6.1 Fresh custom debug-name phase

The project previously used debug names like:

- `bo3_rev_dbg_idle`
- `bo3_rev_dbg_first_raise`
- `bo3_rev_dbg_fire`

That phase was useful for proving:

- the build could emit custom xanim assets,
- weapon fields could be redirected,
- and the probe could watch those names.

But it was not the final answer because it did not match the accepted runtime contract strongly enough.

### 6.2 Semantic-runtime-name hybrid phase

The project then moved into a hybrid state where:

- semantic BO3 names existed,
- runtime names existed,
- and aliasing/shadow paths were allowed in parallel.

This was useful for investigation, but it also created ambiguity:

- if something moved,
- it was hard to know whether the engine was really consuming the intended target runtime asset,
- or whether it had fallen into a shadow semantic/donor-like path.

### 6.3 Donor-order target-runtime-name phase

The current architecture is the strongest animation-side direction so far:

- runtime backend names are staged with donor-order export logic,
- donor runtime assets come from `zm_prison.ff`,
- name counts are aligned to donor counts,
- and the active backend family is emitted under real target weapon runtime names.

This is the correct direction, even though visible playback is still not solved.

## 7. Key facts that are now proven

These are the most important facts a new contributor should treat as already established.

### 7.1 Startup/launch is no longer the main blocker

Earlier time was lost on UI-wrapper startup semantics.

That is no longer the right problem.

The direct stable launch path is:

```powershell
powershell -ExecutionPolicy Bypass -File z:\Games\pluto_t6_full_game\tools\launch_t6_offline.ps1 -Mode ZM -Name ffprobe_offline -GameDir z:\Games\pluto_t6_full_game -PlutoniumDir C:\Users\Ahmed\AppData\Local\Plutonium -Mod bo3_rev -Map zm_transit -UiMapName zm_transit -UiGametype zclassic -UiZmGamemodeGroup zsurvival -UiMapStartLocation town -GGametype zclassic
```

This is the baseline offline launch.

Do not default back to UI wrapper experimentation unless there is a new reason.

### 7.2 The old client mismatch blocker was startup-state/script mismatch, not animation

There were real client/server `client field mismatch` problems during startup.

Those were traced to script-side gametype/start-location mismatches and transit-specific clientfield registration behavior.

Those were important, but they were not the core animation blocker.

### 7.3 The late `mod_load.ff` full-asset patch path caused a real crash/early-exit regression

That was isolated and fixed.

The stable conclusion was:

- `mod_load.ff` should stay a safe seed/probe carrier,
- the survival runtime FF should own the real backend anim assets directly,
- late dangerous full-asset mutation of `mod_load.ff` is not the stable path.

### 7.4 The live game can run the custom weapon lane

The game has been proven to:

- launch into the map,
- connect,
- grant `mg08_zm`,
- and run the animation probe lane.

### 7.5 The custom gun model and runtime xanim family do get built and staged

Recent builds have proven:

- custom gun model asset exists,
- runtime xanim exports are generated,
- runtime FFs are built and deployed,
- and probe watchlists/expectation files are generated from those assets.

### 7.6 The live visible shell is still a stock survivor shell

This remains true in recent runs.

The live `vm=` field seen in logs has still resolved to survivor viewhands variants rather than a truly custom first-person shell.

### 7.7 The BO3 semantic tags are still not the live tag surface

Repeated logs show:

- stock tags like `tag_flash`, `tag_weapon`, `tag_brass`, `tag_clip` can move,
- but BO3 semantic tags like:
  - `tag_gasmask`
  - `tag_eye_left_big_lid_animate`
  - `tag_jaw_lower_2_animate`
  - `tag_tentacle_bottom_left_4_animate`
  are usually `<undef>` live.

This is one of the clearest signs that the intended BO3 semantic surface is not the runtime winner.

## 8. Current build and test entrypoints

There are multiple entrypoints. A new contributor should know which are still relevant.

### 8.1 Older stable FX/vortex build entrypoint

For the older stable Servant FX/vortex lane:

- `tools/build_servant_vortex_runtime.ps1`

This is still useful historical infrastructure, but it is not the main active animation debugging path now.

### 8.2 Current animation build entrypoint

Current animation-focused build wrapper:

- `tools/build_servant_minimal_anim_runtime.ps1`

This wrapper currently sets the active animation environment, including:

- BO3 anim mode enabled,
- stock survivor carrier enabled,
- full zone source enabled,
- target runtime backend names,
- donor-order staging enabled,
- shadow semantic exports disabled by default,
- direct deploy to base/mod/AppData lanes.

### 8.3 Current direct low-level builder

Low-level builder:

- `_build/build_bo3_rev_idg_probe.py`

This is the main source of truth for:

- env vars,
- model staging,
- xanim staging,
- weapon contract rendering,
- zone generation,
- probe watchlist generation,
- expectation file generation,
- patch payload generation,
- and build report generation.

### 8.4 Current offline probe-run wrapper

Current offline probe pass wrapper:

- `tools/run_anim_offline_probe_pass.ps1`

This exists for:

- build,
- launch,
- delayed probe injection,
- short dwell,
- capture,
- archive.

It is useful, but the stable launcher itself should still be treated as the ground truth.

### 8.5 Current native probe entrypoint

Build probe:

```powershell
powershell -ExecutionPolicy Bypass -File native\fx_runtime_probe\build_x86.ps1
```

Inject probe:

```powershell
powershell -ExecutionPolicy Bypass -File native\fx_runtime_probe\inject_latest.ps1 -ProcessName plutonium-bootstrapper-win32 -Wait
```

## 9. Current build knobs that matter

The most important current animation knobs are in:

- `tools/build_servant_minimal_anim_runtime.ps1`
- `_build/build_bo3_rev_idg_probe.py`

Key ones:

- `ROGUE_USE_BO3_IDG_ANIMS=1`
- `ROGUE_BO3_ANIM_RUNTIME_BACKEND=target_weapon_names`
- `ROGUE_BO3_ANIM_RUNTIME_STAGE_DONOR_ORDER=1`
- `ROGUE_BO3_ANIM_RUNTIME_BIND_ALIASES=0`
- `ROGUE_EMIT_SHADOW_SEMANTIC_EXPORTS=0`
- `ROGUE_USE_STOCK_SURVIVOR_CARRIER=1`
- `ROGUE_STOCK_SURVIVOR_HANDMODEL=c_zom_hazmat_viewhands`
- `ROGUE_FORCE_LOW_HANDMODEL=0`
- `ROGUE_PATCH_RUNTIME_BACKEND_FF=0` by default in the stable lane

That last point matters:

- the default stable lane does not try to late-patch `mod_load.ff` into a full animated owner anymore.

## 10. Current most important generated artifacts

These are the first files a new contributor should inspect after any serious run.

### 10.1 Main build report

- `_build/bo3_rev_idg_probe/build_report.json`

This is the best single source for:

- build tag,
- source model,
- staged weapon fields,
- xanim probe summary,
- first-person composition estimate,
- and current blocker notes.

### 10.2 Runtime xanim map

- `_build/bo3_rev_idg_probe/xanim_reports/xanim_runtime_map.json`

This shows:

- `runtime_name`
- `semantic_name`
- donor source
- staging mode
- source/staged export paths

### 10.3 Contract reports

Example:

- `_build/bo3_rev_idg_probe/xanim_reports/vm_zod_id_gun_idle_contract_report.json`

These compare:

- donor header,
- emitted header,
- section sizes,
- section hashes,
- key flag differences.

### 10.4 Probe expectations

- `native/fx_runtime_probe/xanim_runtime_expectations.txt`

This is one of the most important files for runtime debugging now.

It contains per-asset fingerprints for:

- `runtime_custom`
- `modload_custom`
- and relevant stock or donor variants

across:

- header fields,
- `dataShort`,
- `dataInt`,
- `deltaPart`

### 10.5 Probe watchlist

- `native/fx_runtime_probe/active_probe_watchlist.txt`

This tells you exactly what the native probe is watching on a given build.

### 10.6 Runtime probe log

- `native/fx_runtime_probe/bin/x86/Release/fx_runtime_probe.log`

This is where you look for:

- watched name touches,
- candidate asset headers,
- live asset maps,
- xmodel candidate neighborhoods,
- and section/header classification.

### 10.7 Live game logs

- `C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\mods\bo3_rev\games_mp.log`
- `C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\mods\bo3_rev\console_zm.log`

Use these for:

- `[bo3_rev][start]`
- `[bo3_rev][connect]`
- `[bo3_rev][grant]`
- `[bo3_rev][player_state]`
- `[bo3_rev][anim_probe]`

Important warning:

- these logs append across runs,
- so always filter by the current `build_tag`.

## 11. Current known-good facts from the latest animation passes

These are the most relevant recent checkpoints.

### 11.1 Full four-asset animation build before the latest narrowing

One of the last meaningful broader builds was:

- `0402145906_75d444`

That build established:

- custom gun model staging,
- stock survivor carrier staging,
- runtime backend family generation,
- active first-person motion probes,
- and logs proving the game reached map and ran the probe lane.

It also showed:

- live shell still stock survivor viewhands,
- partial movement in some phases,
- idle still mostly flat,
- BO3 semantic tags still undefined.

### 11.2 Narrow runtime-name-only idle validation build

Latest narrow validation build:

- `0402154244_75d444`

This build was important for one specific reason:

- it was the first build where the target-runtime animation lane was shipped without the parallel semantic shadow xanim exports.

What this build proved on disk:

- runtime staging contained only `viewmodel_zomb_mg08_idle.xanim_export`
- the xanim probe watchlist contained runtime names and donor fallback names
- the watchlist no longer contained `vm_zod_id_gun_*`

This removed one major ambiguity from the debugging tree.

## 12. What the current blocker actually is

The current blocker is no longer startup.

The current blocker is no longer broad packaging.

The current blocker is no longer “can T6 load BO3 FX”.

The current blocker is:

### 12.1 We still do not have proof that the live engine is actually consuming the intended target runtime animation family as the winner

Recent investigation showed:

- weapon fields point at `viewmodel_zomb_mg08_*`
- previous hybrid builds still allowed semantic shadow names like `vm_zod_id_gun_*`
- probe evidence showed donor-shaped header matches around semantic paths
- build-side emitted semantic reports were much more dynamic than those donor-shaped live findings

This strongly suggested that the live runtime winner was not cleanly the intended runtime-custom family.

### 12.2 The live shell/tag surface still looks like stock survivor hands

Server/client logs still show:

- stock survivor viewhands at runtime,
- stock tags available,
- BO3 semantic tags undefined,
- partial first-raise motion,
- pullout mostly flash-space only,
- idle flat.

That means the intended BO3 semantic rig/tag surface is still not the live visible winner.

### 12.3 The first-person DObj/composition estimate is still suspiciously large

Build-side first-person composition estimates have indicated very large combined node/joint totals when stacking:

- stock survivor hands
- custom gun model

This may still be related to:

- composition limits,
- hidden pruning,
- attachment behavior,
- or runtime DObj simplification/fallback.

### 12.4 Therefore the active unresolved question is:

Is the failure primarily:

1. runtime selection never touching the intended `viewmodel_zomb_mg08_*` assets,
2. runtime touching them but still resolving to donor-like header/section content,
3. or runtime using them but on a shell/tag surface that does not expose the expected animated bones?

That is the real blocker.

## 13. What has already been ruled out

These are not the main blockers anymore and should not be treated as first suspects without new evidence.

- general startup path
- UI wrapper semantics
- direct launch command-to-map reliability
- generic “BO3 assets can’t load at all”
- broad FX packaging impossibility
- generic “the game just crashes because of animations”
- old loose-image crash lane
- `mod_load.ff` late patch ownership path as a default build strategy

## 14. Important dead ends and traps

A new contributor should actively avoid repeating these.

### 14.1 Do not get trapped in startup semantics again

Use the direct launch command.

Do not make the UI wrapper path the default workflow.

### 14.2 Do not assume `handModel` alone controls the live first-person shell

Recent runs showed that staging a specific `handModel` does not necessarily force the live survivor shell in the town survival lane.

### 14.3 Do not assume that because names exist in memory, playback is working

The probe can prove:

- names exist,
- names are copied,
- names are touched,

without proving:

- the correct runtime asset is winning,
- or the correct visible animation is playing.

### 14.4 Do not mix logs from different build tags

The gameplay logs append.

Always filter by:

- current `build_tag`

before making conclusions.

### 14.5 Do not re-enable semantic shadow exports by default

That ambiguity cost time.

Only re-enable them if you are doing a narrow forensic comparison and you explicitly want both families present.

## 15. Recommended way to resume the project

If a new contributor were taking over from this point, the correct next work should be:

### 15.1 Rebuild the full four-asset animation lane with shadow semantic exports still disabled

Current narrow validation only proved the idle-only runtime-name-only build.

The next real continuation should be:

- `first_raise`
- `pullout`
- `idle`
- `fire`

all together again,

but with:

- `ROGUE_EMIT_SHADOW_SEMANTIC_EXPORTS=0`

still disabled by default.

### 15.2 Launch with the direct stable offline command

Use:

```powershell
powershell -ExecutionPolicy Bypass -File z:\Games\pluto_t6_full_game\tools\launch_t6_offline.ps1 -Mode ZM -Name ffprobe_offline -GameDir z:\Games\pluto_t6_full_game -PlutoniumDir C:\Users\Ahmed\AppData\Local\Plutonium -Mod bo3_rev -Map zm_transit -UiMapName zm_transit -UiGametype zclassic -UiZmGamemodeGroup zsurvival -UiMapStartLocation town -GGametype zclassic
```

### 15.3 Inject the probe after map load

Use:

```powershell
powershell -ExecutionPolicy Bypass -File z:\Games\pluto_t6_full_game\native\fx_runtime_probe\inject_latest.ps1 -ProcessName plutonium-bootstrapper-win32 -Wait
```

### 15.4 Use fresh logs and filtered probe evidence

Specifically ask:

- do we get `xanim_live_asset_map` hits for `viewmodel_zomb_mg08_*`?
- what variant do those hits classify as?
  - `runtime_custom`
  - `modload_custom`
  - stock/donor-like
- do we ever see only donor fallback names touched?
- do gameplay logs for the current build tag still show flat idle and flash-only pullout behavior?

### 15.5 If runtime-name touches still do not appear

Then the next work should focus on:

- why the engine is not resolving the target runtime family at all,
- whether the zone ownership or asset search path still leaves another higher-priority family live,
- and whether the live shell/animtree path even references the expected runtime keys in this lane.

### 15.6 If runtime-name touches do appear but still classify donor-like

Then the next work should focus on:

- section/header ownership,
- verifying which zone variant is supplying the live header,
- and using the expectation file plus live asset map to see whether the runtime FF is actually winning over `mod_load`/stock data.

### 15.7 If runtime-name touches appear and classify `runtime_custom`

Then the remaining blocker is likely:

- first-person shell/tag surface mismatch,
- reduced-model contract mismatch,
- or hidden composition pruning.

At that point the next work would shift more toward:

- xmodel/DObj/runtime composition inspection,
- rather than xanim packaging.

## 16. Suggested first-day checklist for a new contributor

1. Read `docs/fullsummary.md`.
2. Read this `docs/handoff.md`.
3. Read `_build/build_bo3_rev_idg_probe.py` at a high level.
4. Read `tools/build_servant_minimal_anim_runtime.ps1`.
5. Read `mods/bo3_rev/scripts/mod_i_am_mod.gsc`.
6. Read `mods/bo3_rev/clientscripts/mp/zombies/_zm.csc`.
7. Inspect the latest `_build/bo3_rev_idg_probe/build_report.json`.
8. Inspect `native/fx_runtime_probe/xanim_runtime_expectations.txt`.
9. Rebuild the full animation lane with shadow exports still off.
10. Launch directly and inject the probe after map load.
11. Filter logs by current build tag only.
12. Decide whether the next blocker is:
   - no runtime-name touches,
   - donor-like live runtime winner,
   - or shell/tag-surface mismatch.

## 17. Glossary

### Donor shell

A stock T6 runtime-recognized weapon or asset identity used as the accepted engine carrier for foreign content.

### Donor-order export

An xanim staging mode where the output names/order are forced to the donor runtime contract rather than the source BO3 semantic contract.

### Semantic shadow export

A copy of a target runtime asset written back out under its original BO3 semantic name, which can unintentionally remain a live resolver target.

### Runtime custom

The intended target-family custom runtime asset variant built for the real target runtime names.

### Modload custom

A donor-shaped or seed/probe-oriented mod_load variant used for patch/probe work, which is not automatically the desired final runtime winner.

### Stock survivor carrier

The current strategy of using accepted stock survivor hand/viewmodel shells rather than forcing a fully custom first-person hand shell.

## 18. Final project state at handoff

If this project were being handed to a new contributor right now, the honest state is:

- the repo is no longer blocked on startup, packaging, or broad FX acceptance,
- the probe and build system are much stronger than they were,
- the FX side has real working results,
- the animation side is narrowed to a much more precise blocker than before,
- and the most recent meaningful implementation change was removing semantic-shadow ambiguity from the target-runtime animation lane.

What is still missing is the final proof that the live T6 engine is selecting and visibly playing the intended BO3-derived runtime animation family on the active first-person shell.

That is the work left for the next contributor.

## 19. April 2, 2026 update: idle resolver truth is now negative

After the sections above were written, the repo moved one step further and answered the next major decision point.

### 19.1 What changed

A strict idle-only resolver matrix was added:

- `tools/run_idle_resolver_matrix.ps1`

It runs three tightly-controlled idle variants on the same stable lane:

- `A_stock_donor`
- `B_donor_tiny_edit`
- `C_bo3_rebake`

Each run uses:

- direct launch only
- `zm_transit` town survival
- forced stock shell:
  - `c_zom_engineer_viewhands`
- target runtime names
- donor-order staging
- shadow semantic exports off
- alias binding off
- `PATCH_RUNTIME_BACKEND_FF=0`

### 19.2 Matrix result

The archived run is:

- `_build/bo3_rev_idg_probe/idle_resolver_matrix/20260402_153427`

The important conclusion is:

- the positive control is **negative**

More concretely:

- the tiny donor-order-valid static edit on `tag_weapon` in `B_donor_tiny_edit`
- does **not**
- change the live visible idle contract

All three variants:

- grant the weapon
- run `first_raise`
- reach `idle_begin`
- reach `idle_end`
- and end with flat idle on the stock visible tags

This is the strongest evidence in the repo now that:

- the engine is **not** visibly consuming the target `viewmodel_zomb_mg08_idle` family as the live winner

### 19.3 Why this matters

Before this pass, there were still two plausible stories:

1. the engine is selecting the target runtime family, but the BO3 rebake is wrong
2. the engine is not actually selecting the target runtime family as the visible winner

The resolver matrix collapses that ambiguity toward the second answer.

If the intentionally obvious donor-order-valid edit does not show up, then the problem is not merely “BO3 rebake quality.” It is selection / ownership / consumer-side attachment.

### 19.4 What is still true after the matrix

- custom gun xmodel names are still loaded in memory
- target runtime xanim names are still loaded in memory
- deterministic stock-shell forcing works
- `first_raise` still shows gross motion
- `idle` remains flat
- BO3 semantic tags remain irrelevant / undefined on the live visible stock shell

### 19.5 New probe modes and consumer-side work

The native probe was extended again after the matrix:

- `xanim_focus` can now optionally start the consumer-side arm thread
- a new dedicated mode exists:
  - `xanim_consumer_focus`

Purpose of `xanim_consumer_focus`:

- move past generic name-presence census
- arm the live first-person render-table / consumer path directly
- log the heap-struct context around the active render object

What this mode now logs:

- consumer render-table hits
- branch inference
- dword windows around render-state heap structures
- local pointer windows around those same structures looking for watched xmodel/xanim strings

### 19.6 What the consumer probe proved

On the live C build (`0402215809_75d444`), `xanim_consumer_focus` proved:

- `consumer_render_table` hit
- `consumer_render_table_nonzero_branch` hit
- `consumer_render_table_zero_path` hit
- `consumer_render_table_compare` hit
- `consumer_render_table_match_branch` hit
- `consumer_asset_class_lookup` hit
- `consumer_submit_flags` hit

That means:

- the probe is now on the real first-person consumer path

What it still did **not** recover:

- no nearby direct watched-name pointers were found around the render-state heap structures

Interpretation:

- the live first-person render objects are probably not storing model/anim identity as simple adjacent string pointers
- they are likely using indirect IDs / tables / hashed lookups / compact descriptors

### 19.7 Current best statement of the blocker

The blocker now is not:

- startup
- launcher UI
- FF ownership
- semantic-shadow ambiguity
- or “are the runtime names loaded in memory”

The blocker is:

- decode the consumer-side first-person render object and prove which model/anim attachment contract it is actually using at runtime

### 19.8 If a new contributor resumes from here

Do **not** go backward into old problem branches.

Do:

1. trust the idle resolver matrix result
2. treat the selection question as answered enough to move deeper
3. keep using deterministic stock-shell forcing
4. keep direct launch as the only baseline
5. use `xanim_consumer_focus` for further native reverse engineering

The next good reverse-engineering target is:

- the heap/object layout behind the consumer render-table hits
- specifically which fields select:
  - model arrays
  - first-person shell identity
  - anim-tree / anim-table ownership

That is the highest-value continuation point now.

## 20. 2026-04-02 correction: the consumer probe infrastructure is fixed, but live consumer hits are still pending

This section supersedes the earlier assumption that live `consumer_*` execution hits were already a settled result.

### 20.1 Tooling bugs that were fixed

Several runner bugs were causing false negatives and false summaries:

- `active_probe_mode.txt` was being written incorrectly
  - wrong: `mode=xanim_consumer_focus`
  - correct: `xanim_consumer_focus`
- some runners were still injecting with:
  - `-ProcessName t6zm`
  - corrected to:
    - `-ProcessName plutonium-bootstrapper-win32`
- PowerShell wait regexes were over-escaped
  - example wrong pattern:
    - `\\[bo3_rev\\]\\[grant\\]`
  - corrected to:
    - `\[bo3_rev\]\[grant\]`

Affected scripts fixed in this pass:

- `tools/build_and_launch_anim_offline.ps1`
- `tools/restart_t6_probe_cycle.ps1`
- `tools/run_anim_offline_probe_pass.ps1`
- `tools/run_consumer_reference_compare.ps1`
- `tools/run_idle_resolver_matrix.ps1`

### 20.2 Native probe changes in this pass

`native/fx_runtime_probe/fx_runtime_probe_hook.cpp` was updated so that `xanim_consumer_focus` now arms earlier and reports its own internal progress.

Key changes:

- `xanim_consumer_focus` consumer-arm initial delay reduced to `1500 ms`
- retry delay reduced to `2000 ms` for that mode
- new logs added:
  - `consumer_arm_attempt_begin`
  - `consumer_arm_attempt_enumerate_done`
  - `consumer_arm_attempt`
  - `consumer_arm_attempt_exception`

Latest validated probe build from this pass:

- `native/fx_runtime_probe/bin/x86/Release/fx_runtime_probe_hook_20260402_223953.dll`

### 20.3 What is now proven

The consumer arm thread no longer stalls silently.

On a direct live injection test:

- the DLL loads
- `probe_mode` reads `xanim_consumer_focus`
- `consumer_arm_thread_started` appears
- and the arm thread reaches:
  - `consumer_arm_attempt attempt=1 armed=4`

That means the consumer trace sites can be armed successfully in the live process now.

### 20.4 What is still not proven

We still do **not** have a stable in-map custom idle run that produces live:

- `exec_trace_hit label=consumer_render_table`
- `exec_trace_hit label=consumer_asset_class_lookup`
- `exec_trace_hit label=consumer_submit_flags`

Current failure shape on the best custom compare run:

- `custom_rebake` reaches:
  - `connect`
  - `grant`
  - forced stock shell selection (`c_zom_engineer_viewhands`)
- the probe sees watched live asset names in memory
- but after injection, the gameplay logs stop almost immediately after `grant`
- and the probe log shows no `consumer_*` execution hits before the process is closed

So the remaining blocker is no longer "can the consumer arm thread arm traces?"

It is:

- how to keep the custom in-map lane stable long enough after injection for those armed consumer traces to actually fire

### 20.5 Stock-reference control status

The stock-reference branch in `tools/run_consumer_reference_compare.ps1` is currently not a dependable control.

Current behavior:

- `stock_reference` often fails before gameplay markers appear
- `games_mp.log` can be empty on those runs
- `console_zm.log` often stops in UI/load territory

So do not assume stock-reference is presently the best control sample. The useful active lane remains:

- direct launch
- custom idle lane
- deterministic stock shell forcing
- post-grant consumer-focus injection

### 20.6 Exact next target

The next correct target is:

1. make one custom idle run stable after post-grant injection
2. capture actual `exec_trace_hit label=consumer_*` evidence
3. only then decode the live first-person consumer object from those hits

Until that happens, the strongest current claim is:

- the consumer probe can now arm the intended trace points
- but the repo still lacks a stable post-injection in-map capture where those points fire

## 21. 2026-04-02 correction: live consumer hits are now proven

This section supersedes section 20 as the authoritative state for the consumer-side probe.

### 21.1 What changed

`xanim_consumer_focus` was reduced to a true minimal first-hit mode in:

- `native/fx_runtime_probe/fx_runtime_probe_hook.cpp`

Important behavior changes:

- no watchlist/touch-trace/xanim-expectation work in this mode
- no file-hook setup in this mode
- explicit first-hit log:
  - `consumer_first_hit ...`

New runner added:

- `tools/run_consumer_hit_sweep.ps1`

Purpose:

- freeze one custom idle lane
- direct launch only
- deterministic stock shell only
- inject at several timings
- exit on first real `consumer_*` hit

### 21.2 Authoritative sweep result

Archive:

- `_build/bo3_rev_idg_probe/consumer_hit_sweeps/20260402_225906`

Build:

- `0403045909_75d444`

Probe:

- `fx_runtime_probe_hook_20260402_225856.dll`

Key results:

- `startup`
  - probe armed
  - `consumer_first_hit label=consumer_render_table`
  - not sufficient to prove in-map gameplay because no grant marker was reached before hit-and-exit
- `grant_plus_1s`
  - `grant` reached
  - shell forced to `c_zom_engineer_viewhands`
  - `first_raise_begin`, `first_raise_end`, and `idle_begin` reached
  - probe armed
  - `consumer_first_hit label=consumer_render_table`

This is the first authoritative proof that a live `consumer_*` execution hit occurs during a stable post-grant custom idle run.

### 21.3 What the live hit gives us

The first live in-map hit logged:

- `consumer_arm_attempt attempt=1 armed=4`
- `exec_trace_hit label=consumer_render_table`
- `consumer_first_hit label=consumer_render_table`

with live render-state neighborhoods around:

- `0x334CC050`
- `0x334CC130`
- `0x334CC138`
- `0x338306B0`

So the next reverse-engineering step is now consumer-object recovery, not capture stability.

### 21.4 Current blocker

The blocker is now:

- recover the live first-person consumer object chain behind `consumer_render_table`
- identify how it resolves model ownership and anim ownership
- determine whether it resolves to:
  - stock first-person ownership
  - custom runtime backend ownership
  - or a mixed fallback path

### 21.5 Small follow-up note

A `consumer_heartbeat` logger was added on the script side, but its first implementation keyed off the wrong token (`__PROBE_MODE__`, which is the gun-model lane token).

That was corrected by adding a dedicated native probe-mode token. Treat heartbeat verification as a minor follow-up. It is not the blocker anymore.

### 21.6 Consumer object capture is now stable

Authoritative archive:

- `_build/bo3_rev_idg_probe/consumer_hit_sweeps/20260402_234928`

This pass fixed the remaining probe-side stall in `xanim_consumer_focus`.

What changed:

- `log_consumer_render_state()` now skips the old heavy correlation / watched-pointer scans in `xanim_consumer_focus`
- `log_consumer_anchor_snapshot()` now records:
  - bytes
  - dword windows
  - typed slots
  - a compact hash
  - a completion marker
- old correlation scans are skipped in `xanim_consumer_focus`

That made the consumer-object capture complete reliably.

### 21.7 Recovered live object anchors

Stable custom idle run:

- direct offline launch
- forced shell `c_zom_engineer_viewhands`
- post-grant injection with `grant_plus_1s`
- probe mode `xanim_consumer_focus`

Recovered first-hit anchors from `grant_plus_1s/fx_runtime_probe.log`:

- owning object candidate: `0x32DBC050`
- render node candidate: `0x32DBC130`
- render sub-struct candidate: `0x32DBC138`
- lookup object candidate: `0x331206B0`

Branch inference on the first authoritative hit:

- `consumer_first_hit label=consumer_render_table`
- `esi_word = 0x0002`
- `zero_lane = 0`
- `table_value = 0x3E1B784F`
- `esi_plus_8_value = 0xA0AB1041`
- `compare_match = 0`
- `inferred = nonzero_branch`

So the live custom idle run is hitting the nonzero render-table path.

### 21.8 Stable hashes and what they mean

The following anchor hashes were stable across:

- `first_hit`
- `post_hit_250ms`
- `post_hit_1000ms`

Hashes:

- `render_state_esi_minus_e0 = 0xDA2684F5`
- `render_state_esi = 0xBA04C74E`
- `render_state_esi_plus_8 = 0x63F31B2D`
- `render_state_eax = 0xADB1CD2F`

Interpretation:

- these are not rapidly-changing per-frame payloads on the current idle lane
- they look more like ownership / state-carrier objects
- the next step is no longer “find a stable object”
- the next step is “recover the handle / pointer / table indirection inside the stable object family”

### 21.9 Highest-signal fields recovered so far

Owning object `0x32DBC050`:

- mostly zeros and small ints
- notable:
  - `slot -3 = 0x00000200`
  - `slot -2 = 0x00000200`
  - `slot +1 = 0x00000100`
  - `slot +8 = 0x00000100`

Render node `0x32DBC130`:

- `slot +0 = 0x00000002`
- `slot +1 = 0x00000001`
- `slot +2 = 0xA0AB1041` classified as `ptr_heap`

Render sub-struct `0x32DBC138`:

- `slot +0 = 0xA0AB1041` classified as `ptr_heap`
- same value as render-node `slot +2`

Lookup object `0x331206B0`:

- `slot +0 = 0x3E1B784F` classified as `ptr_heap`
- `slot +8 = 0x8147AD2D` classified as `int_or_flags`

### 21.10 Immediate next step

Do not widen the animation family yet.

The next correct step is:

- take the stable object family above
- map which fields are:
  - owning-object links
  - model owner / model handle
  - anim owner / anim handle
  - compact flags / state IDs
  - lookup inputs

Only after that should work return to whether the custom runtime backend or donor backend is the actual live winner.

## 22. Latest consumer-object recovery pass

### 22.1 What changed in code

The probe now treats the earlier consumer lookup sites as first-class capture targets, not just the render-table family.

Implemented in `native/fx_runtime_probe/fx_runtime_probe_hook.cpp`:

- per-trigger deferred snapshot scheduling keyed by object family
- `consumer_asset_class_lookup` compact capture
- `consumer_image_class_map` compact capture

Implemented in `tools/run_consumer_hit_sweep.ps1`:

- parsing and archiving of:
  - `asset_lookup_hits`
  - `image_map_hits`

So the repo is now prepared to recover the earlier `EDI -> EAX -> ECX(+6)` ownership/lookup chain the next time it fires.

### 22.2 Latest archives

Newest archives from this pass:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_003931`
- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_004213`

Both use the same frozen lane:

- custom idle-only build
- deterministic stock shell forcing
- direct launch
- `xanim_consumer_focus`

### 22.3 What these runs showed

The lane is still stable enough for consumer reverse engineering:

- build succeeds
- launch succeeds
- grant succeeds
- probe injects successfully
- `consumer_render_table` still hits reliably in-map

But on these fresh runs, the earlier lookup-path site did not fire again:

- no new `consumer_asset_lookup_compact`
- no new `consumer_image_map_compact`

This matters because it means:

- the lookup-path probe is now implemented correctly
- but `consumer_asset_class_lookup` is currently less reliable / less frequent than the render-table family on this lane

### 22.4 Authoritative interpretation

The old recovered archive `20260403_003415_recovered` is still the only direct proof that `consumer_asset_class_lookup` can fire in this custom lane.

The new passes prove something different:

- render-table capture is now the dependable baseline
- lookup-path capture is wired and ready
- the current gap is live occurrence, not implementation

### 22.5 Most useful new observation

The newest render-family `EAX` lookup object looks more like a compact descriptor block than a pointer-bearing asset struct.

Example from `20260403_004213`:

- lookup object candidate: `0x2E1A45E0`
- important fields:
  - `slot +0 = 0xB60C3B3A`
  - `slot +4 = 0x3F800000`
  - `slot +5 = 0x3F800000`
  - `slot +6 = 0x3F800000`
  - `slot +7 = 0x3F800000`

Working meaning:

- `slot +0` looks like a compact ID / hash / handle
- the block is descriptor-like, not string-adjacent
- this reinforces the conclusion that stock/custom ownership is hidden behind numeric indirection

### 22.6 Current blocker

The blocker is now:

- keep using the stable render-family anchors
- catch the next real `consumer_asset_class_lookup` hit
- recover whether `EDI -> EAX -> ECX(+6)` is the ownership / class-handle chain that resolves stock vs custom

Do not go back to launcher work, shell experiments, or generic memory-presence scans.

## 23. Latest render-site differential pass

### 23.1 What was added

The newest native probe pass did two useful things:

1. tightened consumer slot classification
2. added repeated-hit capture at the reliable `consumer_render_table` site

Implemented in `native/fx_runtime_probe/fx_runtime_probe_hook.cpp`:

- module pointers now require real `MEM_IMAGE` validation
- printable packed fields now classify as `ascii4` earlier
- `consumer_render_table` now logs:
  - `consumer_render_hit_summary`
  - `caller_select`
- `xanim_consumer_focus` now arms `consumer_render_table` with `max_hits=4`
- later render hits are ready to emit:
  - `hit_2`
  - `hit_4`

Implemented in `tools/run_consumer_hit_sweep.ps1`:

- parsing of:
  - `render_hit_summaries`
  - `caller_selects`

### 23.2 Authoritative archive

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_005827`

Probe build:

- `fx_runtime_probe_hook_20260403_005827.dll`

### 23.3 What this run proved

The lane still works with the tighter instrumentation:

- build succeeds
- launch succeeds
- grant succeeds
- probe injects
- `consumer_render_table` hits in-map

Recovered first-hit anchors from this pass:

- owning `0x335DC050`
- render `0x335DC130`
- render+8 `0x335DC138`
- lookup `0x339406B0`

Caller context now also records:

- `caller_select ... selected=0x7124D9F7 frame_count=6`

### 23.4 Why this pass matters

The stricter classifier removed several fake pointer interpretations.

Example:

- values like `0x706D6970`, `0x6365745F`, `0x71696E68`, `0x745F6575`
are now treated as packed printable data instead of bogus module pointers

That makes the current render-node windows read more honestly as descriptor/state blocks.

### 23.5 What did not happen

Even with `max_hits=4`, this live run still only produced one `consumer_render_table` hit.

That means:

- first-hit capture is dependable
- repeated render-hit differential capture is implemented
- but the frozen custom lane still does not naturally give later render-table hits in the same run

So the next blocker is not “instrument more at the render site.”
It is:

- find a nearby always-hit site in the same consumer path that fires later
- or force a second dependable consumer transition while keeping the same frozen lane

### 23.6 Current best interpretation

The render family is still the right stable anchor.

The `EAX` block is still not behaving like a direct asset object. With the improved classifier it still looks descriptor-like and numerically opaque, not like a string-bearing model/xanim header.

## 24. Upstream return-site recovery and deferred-snapshot deadlock fix

### 24.1 What changed

This pass fixed a real correctness bug in the native probe and recovered the first upstream caller-family site that connects back into the render-family objects.

Implemented in `native/fx_runtime_probe/fx_runtime_probe_hook.cpp`:

- fixed deferred-snapshot scheduling so breakpoint-handler paths no longer deadlock on `g_state_mutex`
- added `start_consumer_deferred_snapshots_once_locked(...)`
- added `render_state_edi` capture to the render-family first hit
- added upstream return-site arming from the live render-hit stack
- added structured upstream-hit capture:
  - `consumer_upstream_hit_summary`
  - `upstream_edi`
  - `upstream_esi`
  - `upstream_eax`

Implemented in `tools/run_consumer_hit_sweep.ps1`:

- parsing for:
  - `upstream_hit_summaries`
  - `upstream_arms`

### 24.2 Authoritative archive

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_014609`

Probe build:

- `fx_runtime_probe_hook_20260403_014551.dll`

### 24.3 What this run proved

The frozen `grant_plus_1s` custom idle lane now completes this chain:

- build succeeds
- launch succeeds
- grant succeeds
- probe injects
- live `consumer_render_table` hit occurs
- deferred snapshots really start
- upstream return-site traces arm from the live render-hit stack
- one upstream return-site actually fires in the same run

Important log lines:

- `consumer_deferred_snapshot_thread_started trigger=consumer_render_table ...`
- `consumer_upstream_arm slot=6 addr=0x00749BE0 rva=0x00349BE0`
- `consumer_upstream_arm slot=7 addr=0x00749C95 rva=0x00349C95 preferred=1`
- `exec_trace_hit label=consumer_upstream_ret_00349C95`
- `consumer_upstream_hit_summary label=consumer_upstream_ret_00349C95 hit=1 eip=0x00749C95 eax=0x38401BEC esi=0x30F57E48 edi=0x30F57E40`

### 24.4 Recovered object links

Render-family anchors from this run:

- owning `0x30F57D98`
- render `0x30F57E78`
- render+8 `0x30F57E80`
- lookup `0x38401C70`
- render_state_edi `0x30F57E40`

Upstream hit:

- `consumer_upstream_ret_00349C95`
- `EDI = 0x30F57E40`
- `ESI = 0x30F57E48`
- `EAX = 0x38401BEC`

Concrete relations:

- upstream `EDI` exactly equals `render_state_edi`
- upstream `ESI` is `render_state_edi + 0x8`
- upstream `EAX` is in the same lookup family as render lookup and sits `0x84` bytes before `0x38401C70`

This is the first solid caller-family -> parent object -> render-family connection recovered in the repo.

### 24.5 Important fields in `render_state_edi`

Current `render_state_edi` base:

- `0x30F57E40`

Important offsets from the authoritative run:

- `+0 = 0x30F57E84`
- `+2 = 0x30E2C374`
- `+3 = 0x30E76060`
- `+4 = 0x30F57ABC`
- `+7 = 0x30F57E60`

Useful interpretation:

- `+0` points into the descriptor tail after the render-node base
- `+2` and `+3` are now the best candidate child objects for model/anim ownership
- `+7` points to a tiny local sub-block whose first dword is `3`

### 24.6 Current blocker

The blocker is no longer capture stability and no longer “can we hit the caller family.”

The blocker is now pure object-model recovery:

- determine whether `render_state_edi +2` / `+3` are model-owner or anim-owner sub-objects
- recover the meaning of upstream `ESI = render_state_edi + 0x8`
- recover the lookup-family relation between upstream `EAX = 0x38401BEC` and render lookup `0x38401C70`

### 24.7 Recommended next step

Stay on the same frozen `grant_plus_1s` custom idle lane and do only this:

- one-hop field chasing from `render_state_edi`
- one-hop field chasing from `upstream_esi`
- compact differential capture inside the `0x38401BEC -> 0x38401C70` lookup-family region

Do not widen back to stock/reference or full-family animation work until that object graph is named.

## 25. `render_state_edi` child-object recovery

### 25.1 What changed

This pass stayed on the same frozen custom idle lane and promoted the important `render_state_edi` child pointers into first-class capture targets.

Implemented in `native/fx_runtime_probe/fx_runtime_probe_hook.cpp`:

- first-hit snapshots for:
  - `render_state_edi_child_2`
  - `render_state_edi_child_3`
  - `render_state_edi_child_4`
  - `render_state_edi_child_7`
- deferred snapshots now include those children when they are valid pointers
- lookup-family span capture is ready for runs where the upstream branch fires again

### 25.2 Authoritative archive

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_015837`

Probe build:

- `fx_runtime_probe_hook_20260403_015837.dll`

### 25.3 What this run proved

This run did not repeat the upstream-hit branch, but it did recover stable child links directly from the render root:

- `render_state_edi base = 0x30A87E40`
- `render_state_edi +2 -> render_state_edi_child_2 = 0x3095C374`
- `render_state_edi +3 -> render_state_edi_child_3 = 0x309A6060`

Those relationships are now present in the parsed summary as `anchor_links`.

### 25.4 Interpreting the children

`render_state_edi_child_2` looks compact and mostly numeric:

- `+0 = 0x00010003`
- `+1 = 0x02010000`
- `+2 = 0x00000502`
- later slots mostly zero

That makes it a stronger candidate for compact state / handle / ownership metadata.

`render_state_edi_child_3` looks pointer-rich and descriptor-heavy:

- header pointers around `-4`, `-1`, `+0`, `+1`, `+2`
- `+3 = 0x00001820`
- printable payload starting at `+4`

That makes it look more like a descriptor/string sidecar than the core compact owner block.

### 25.5 Current best next target

The next reverse-engineering target should now be:

- `render_state_edi_child_2` first

The lookup-family span should still be captured again when the upstream branch fires, but `child_2` is now the better immediate candidate for the compact owner/handle path than `child_3`.

## 26. Child-state timing matrix on the frozen lane

I tightened `tools/run_consumer_child_state_matrix.ps1` so it can re-summarize an existing sweep archive, report captured-only invariants, and compute root-relative child deltas. That matters because the first matrix summary was too pessimistic: one missing variant made it look like there were no invariants, even though three successful variants were already agreeing.

Authoritative archive:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_021424`

Variant set:

- `grant`
- `grant_plus_1s`
- `grant_plus_2s`
- `grant_plus_4s`

Important facts:

- all four variants reached `grant`, injected, armed, and hit `consumer_render_table`
- `grant_plus_1s` did not recover `render_state_edi` child captures
- that missing `grant_plus_1s` child data is a partial-capture case, not a parser bug

### 26.1 `child_2` is currently the strongest compact owner/state candidate

Across the successful child-capture variants (`grant`, `grant_plus_2s`, `grant_plus_4s`), `render_state_edi_child_2` is completely invariant:

- `-4..-1 = 0`
- `+0 = 0x00010003`
- `+1 = 0x02010000`
- `+2 = 0x00000502`
- `+3..+8 = 0`

It also stays at the same root-relative offset in every successful variant:

- `root -> child_2 delta = -0x0012BACC`

That makes `child_2` the best compact ownership / handle / state lead in the repo right now.

### 26.2 `child_3` looks downstream and descriptor-heavy

`render_state_edi_child_3` splits into:

Stable slots:

- `-3 = 0x00010101`
- `-2 = 0x00000203`
- `+3 = 0x00001820`
- `+4..+8 = fixed ascii payload beginning with "pimp_sha_der_debugper..."`

Variant-dependent slots:

- `-4`
- `-1`
- `+0`
- `+1`
- `+2`

Those changing slots are pointer-like / relocated values, while the payload and small-int region stay fixed. The root-relative offset is also invariant:

- `root -> child_3 delta = -0x000E1DE0`

Current interpretation: `child_3` is likely a richer downstream descriptor/projection block, not the compact stock/custom decision point.

### 26.3 Other stable root-local links

The same matrix also showed:

- `root -> child_4 delta = -0x00000384`
- `root -> child_7 delta = +0x00000020`

So the object layout around `render_state_edi` is structurally stable even though absolute heap addresses relocate each run.

### 26.4 Current blocker after the matrix

The next useful questions are now very narrow:

- is `child_2` immutable ownership metadata, or a compact state/handle block that only changes on a stronger state transition than this timing sweep
- how does `child_2` correlate against the lookup-family span from the upstream-hit run
- does `child_3` merely project / materialize state from `child_2`

## 27. Offline `child_2` to upstream-lookup join

I added `tools/analyze_consumer_child2_lookup_join.ps1` so the finished child-state matrix can be correlated against the earlier upstream-hit archive without waiting for the upstream branch to fire again.

Authoritative output:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_021424\child2_lookup_join_summary.json`

Inputs:

- child-state matrix archive:
  - `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_021424`
- upstream-hit archive:
  - `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_014609\grant_plus_1s`

### 27.1 Structural relationships the join confirms

- upstream `EDI == render_state_edi`
- upstream `ESI == render_state_edi + 0x8`
- upstream `EAX -> render lookup delta = +0x00000084`
- root `-> child_2 delta = -0x0012BACC`

The compact `child_2` signature used for the join is:

- `+0 = 0x00010003`
- `+1 = 0x02010000`
- `+2 = 0x00000502`

### 27.2 What the join ruled out

There is no direct byte-level or dword-level presence of that `child_2` signature in the captured:

- `upstream_eax` window
- render lookup (`render_state_eax`) window

There is also no contiguous match for the full three-dword `child_2` signature in either captured window.

Conclusion currently recorded by the tool:

- `child2_not_present_as_direct_dword_sequence_in_captured_lookup_windows`

### 27.3 Why this matters

That rules out the simplest theory that `child_2` is copied verbatim into the captured lookup window.

So the current best model is:

- `child_2` is still the best compact ownership/state lead
- the upstream `EAX -> render lookup` family is still the best lookup-side lead
- but the join between them is indirect and still needs either:
  - a stronger semantic transition
  - or one-hop handle/index correlation

## 28. Field-transform join pass

I extended `tools/analyze_consumer_child2_lookup_join.ps1` so it tests more than raw dword equality. The tool now checks the `child_2` signature against the captured `upstream_eax` and render-lookup windows using:

- low/high 16-bit halves
- bytewise matches
- low16/high16/low24/high24 masks
- 16-bit-swapped / byte-swapped dword forms
- small delta candidates
- small XOR candidates

Authoritative output:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_021424\child2_lookup_join_summary.json`

### 28.1 Result

The raw transform output was dominated by trivial zero-padding overlap.

After filtering for nontrivial signal:

- `high_signal_field_transform_summary.upstream_eax = null`
- `high_signal_field_transform_summary.render_lookup = null`

So there is currently no meaningful evidence that `child_2` is represented directly in those lookup-family windows as:

- halves
- bytes
- masked bitfields
- swapped words
- simple small deltas
- simple small XOR transforms

### 28.2 Why this matters

That kills the next easy theory after raw byte equality.

Current best interpretation:

- `child_2` is still the strongest compact owner/state candidate
- the lookup family is still the strongest downstream lookup-side lead
- but the link between them is an intermediate decode/table/handle step, not a trivial encoded mirror

## 29. Root-local correlation pass

I added `tools/analyze_render_root_local_correlation.ps1` so the stable `render_state_edi` family can be analyzed from the owner/root side instead of only from the downstream lookup side.

Authoritative output:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_021424\render_root_local_correlation_summary.json`

### 29.1 Stable root-local layout

Across the successful captures (`grant`, `grant_plus_2s`, `grant_plus_4s`):

- `root +0 -> root +0x44`
- `root +2 -> child_2` with delta `-0x0012BACC`
- `root +3 -> child_3` with delta `-0x000E1DE0`
- `root +4 -> child_4` with delta `-0x00000384`
- `root +7 -> child_7` with delta `+0x00000020`

Stable inline root fields:

- `root +1 = 0x00010080`
- `root +5 = 0x00010101`
- `root +6 = 0x00000203`
- `root +8 = 0x00000003`

### 29.2 Important new relationships

These held across every successful captured variant:

- `root +5 == child_3 -3`
- `root +6 == child_3 -2`
- `root +5 == child_4 -3`
- `root +6 == child_4 -2`
- `root +4 == child_7 -4`
- `root +5 == child_7 -3`
- `root +6 == child_7 -2`
- `root +7 == child_7 -1`
- `root +8 == child_7 +0`

So:

- `child_7` is an overlapping view into the root tail, not a separate external owner object
- the root itself already carries inline header words that are mirrored into both descriptor-style children

### 29.3 Descriptor/materialization blocks

Both `child_3` and `child_4` now look like root-local descriptor/materialization blocks:

- `child_3 +0 -> child_3 +0x10`
- `child_4 +0 -> child_4 +0x10`
- `child_3 +2 -> child_3 +0x3B`
- `child_4 +2 -> child_4 +0x3A`

`child_4` especially looks descriptor-heavy:

- shared header words `0x00010101` / `0x00000203`
- printable payload beginning at `+4`

### 29.4 Current best owner-side model

Current best model:

- `render_state_edi` = stable root
- `child_2` = compact owner/state candidate
- root inline header words = shared compact descriptor header
- `child_3` / `child_4` = richer root-local descriptor/materialization blocks
- `child_7` = overlapping tail view / continuation, not the primary selector

### 29.5 Current blocker after the root-local pass

The blocker is now:

- determine whether `child_2` selects which root-local descriptor/materialization block becomes active
- or recover the one-hop table/handle step between `child_2` and those mirrored root-local descriptor header fields

So the next live work should target a stronger semantic transition, not another timing sweep.

## 30. Semantic transition compare: `first_raise_begin` vs `idle_begin`

I added `tools/run_consumer_semantic_transition_compare.ps1` so the repo can answer the next question with real script phases instead of timing proxies.

Authoritative archive:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_semantic_transitions\20260403_024405`

The runner:

- rebuilds the frozen custom idle lane once
- launches on the stable direct offline path
- waits for a real script marker
- injects on:
  - `first_raise_begin`
  - `idle_begin`
- writes:
  - `semantic_transition_summary.json`
  - `semantic_transition_child2_summary.json`

### 30.1 Main result

`child_2` is invariant across the semantic `first_raise_begin` vs `idle_begin` compare.

From:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_semantic_transitions\20260403_024405\semantic_transition_child2_summary.json`

Captured variants:

- `first_raise_begin`
- `idle_begin`

Every captured `child_2` slot matched across both runs:

- `-4..-1 = 0`
- `+0 = 0x00010003`
- `+1 = 0x02010000`
- `+2 = 0x00000502`
- `+3..+8 = 0`

Conclusion written by the runner:

- `child2_invariant_across_semantic_transition`

### 30.2 Stage verification and helper fix

The intended stage markers are present in the archived logs for both runs:

- `first_raise_begin`
- `idle_begin`

I also fixed the stage-line helper in:

- `tools/run_consumer_hit_sweep.ps1`
- `tools/run_consumer_semantic_transition_compare.ps1`

The helper had only been matching `;stage=` and was missing payloads where the stage token started right after the log prefix as ` stage=...`.

### 30.3 Current best interpretation after this pass

This is a strong narrowing:

- `child_2` is not only invariant across timing-only variants
- it is also invariant across a real semantic `first_raise_begin -> idle_begin` transition

So `child_2` is now more likely immutable ownership metadata than the dynamic handle that changes during that transition.

That means the missing dynamic step is probably one link away from `child_2`, not inside `child_2` itself.

## 31. Corrected root-local decode compare on the semantic archive

I fixed a probe capture bug in:

- `native/fx_runtime_probe/fx_runtime_probe_hook.cpp`

Important correction:

- typed slot logging stays conservative
- pointer-chase logging now uses explicit readable-pointer validation

This prevents the old failure mode where:

- a real heap pointer was dropped because it looked printable
- or a pointer-first classifier polluted the typed window with false pointer interpretations

I also added:

- `tools/analyze_semantic_root_decode_compare.ps1`

That is now the focused interpreter for the semantic-transition archive.

Authoritative archive:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_semantic_transitions\20260403_025947`

Authoritative focused summary:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_semantic_transitions\20260403_025947\semantic_root_decode_summary.json`

### 31.1 Main result

Across the corrected `first_raise_begin -> idle_begin` compare:

- the meaningful root-local decode region did **not** change
- no non-bogus one-hop decode-table change was found

The stable root-local region was:

- `root +3 = 0x00020101`
- `root +4 = 0x00000003`
- `root +5 = ptr_heap:+0x00002E00`
- `root +6 = ptr_heap:+0x00000028`

The focused summary concludes:

- `root_local_slots_show_meaningful_change = false`
- `root_one_hop_changes = false`
- `child3_one_hop_changes = false`
- `child4_one_hop_changes = false`
- `semantic_decode_signal_found = false`

### 31.2 Noise that should not be over-interpreted

The corrected pass still shows two noisy surfaces:

- `root +7` drifting printable/ascii-like payload
- `child_3` one-hop captures to the constant sentinel `0x3F3F3F3F`

Those are not treated as real decode-path signal anymore.

### 31.3 Important interpretation rule

For this pass, do **not** trust the generic runner summaries as the final interpretation:

- `semantic_transition_summary.json`
- `semantic_transition_child2_summary.json`

Use the focused summary instead:

- `semantic_root_decode_summary.json`

Reason:

- the generic summary overcalls noise in the captured inline tail
- the focused summary isolates the meaningful root-local decode region

### 31.4 Current blocker after the corrected compare

The blocker is now:

- `first_raise_begin -> idle_begin` is too weak to expose the dynamic root-local decode step

So the next live pass should be:

- a stronger ownership-changing transition such as putaway / weapon-away / equivalent
- or a tighter consumer-family / caller-family-gated compare on the same decode objects

## 32. Grant/equip compare is the first real dynamic decode signal

The putaway path did not turn into a reliable stronger-transition lane. Repeated `putaway` runs still failed before `putaway_begin`, so the next stronger ownership-changing edge was implemented instead:

- keep the starter weapon active briefly after the probe is granted
- log that starter-owned state as `equip_hold_begin`
- then switch into the probe weapon and compare against probe `idle_begin`

Files changed:

- `mods/bo3_rev/scripts/mod_i_am_mod.gsc.in`
- `tools/build_servant_minimal_anim_runtime.ps1`
- `tools/run_consumer_semantic_transition_compare.ps1`

New probe phase:

- `equip_hold`

New stage markers:

- `equip_hold_begin`
- `equip_hold_end`

### 32.1 Authoritative archive

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_semantic_transitions\20260403_034408`

Important outputs:

- `semantic_transition_summary.json`
- `semantic_transition_context_summary.json`
- `semantic_transition_caller_summary.json`
- `semantic_root_decode_summary.json`

### 32.2 What the run proves

Both variants succeeded:

- `equip_hold_begin`
- `idle_begin`

Both also produced a real in-map consumer hit:

- `consumer_first_hit label=consumer_render_table`

Stage proof:

- `equip_hold_begin`: `cur=m1911_zm`
- `idle_begin`: `cur=mg08_zm`
- both kept `vm=c_zom_engineer_viewhands`

So this compare is the first good ownership-changing transition in the repo, not just a phase compare inside the same equipped state.

### 32.3 Main conclusion

This pass is the first authoritative positive decode result:

- runner conclusion:
  - `root_decode_changes_across_grant_equip_transition`
- focused analysis:
  - `semantic_decode_signal_found = true`

Meaning:

- the meaningful render/root/child object family really changes across starter-weapon ownership -> probe-weapon idle

### 32.4 Most important interpretation change

Before this pass, the best model was:

- `child_2` looks like static ownership metadata
- the obvious root-local decode region is static across `first_raise -> idle`

That is still true **within the same equipped probe-state family**.

But across the stronger grant/equip transition:

- `render_state_edi` changes
- `child_2` changes
- `child_3` changes
- `child_4` changes

So the better model now is:

- the idle-only root/child family is ownership-specific
- the first real dynamic selection point is tied to object-family selection across the equip edge

### 32.5 Most useful data points

Representative root changes:

- `root +3`
  - equip hold: `0x31216060`
  - idle: `0x00020101`
- `root +4`
  - equip hold: `ptr_heap:-0x00000384`
  - idle: `small_int:0x00000003`
- `root +5`
  - equip hold: `ptr_region:0x00010101`
  - idle: `ptr_heap:+0x00002E00`
- `root +6`
  - equip hold: `small_int:0x00000203`
  - idle: `ptr_heap:+0x00000028`

Representative `child_2` changes:

- `+0`
  - equip hold: `0x00010003`
  - idle: `ptr_heap:+0x00000010`
- `+1`
  - equip hold: `0x02010000`
  - idle: `ptr_heap:+0x4543FB4C`
- `+2`
  - equip hold: `0x00000502`
  - idle: `ptr_heap:+0x0000003A`

### 32.6 Caller-family note

Caller/stack-return summaries differ across the two variants, but unresolved `<other>` frames still make raw caller bucketing imperfect.

What is safe to say:

- the ownership-changing compare is not following the exact same downstream consumer context as the old idle-only compare
- stack-return families differ too, so the stronger transition is reaching a different live consumer path

### 32.7 What is blocked now

The blocker is no longer “does anything meaningful change across a stronger transition?”

That is now answered: yes.

The blocker is now:

- identify which upstream selector / handle / table drives the swap from the starter-owned family to the probe-owned family
- recover that transition path before going back to finer byte-level idle-only decode work

### 32.8 Practical resume point

If resuming from here, do not go back to:

- launcher work
- generic “is it loaded in memory” scans
- more idle-only timing sweeps

Resume from:

- the `equip_hold` transition
- `20260403_034408`
- upstream ownership-family recovery around the grant/equip edge

## 33. Grant/equip family-bundle summary is now the main ownership map

There is now a dedicated analyzer for the grant/equip archive:

- `tools/analyze_grant_equip_family_bundle.ps1`

Authoritative output:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_semantic_transitions\20260403_034408\grant_equip_family_bundle_summary.json`

This is now the best compact map of the ownership-side problem.

### 33.1 What it proves

The ownership transition is now decomposed into four parts:

- invariant render-head core
- root/child selector bundle
- downstream materialization bundle
- upstream availability split

Key conclusions from the summary:

- `ownership_family_swap_confirmed = true`
- `render_head_core_stays_stable = true`
- `render_descriptor_ptr_changes = true`
- `selector_candidates_live_in_root_or_child2 = true`
- `downstream_materialization_changes = true`
- `upstream_bridge_complete_for_both_variants = false`

### 33.2 Best current selector bundle

The current high-confidence selector fields are:

- `root +4`
- `root +5`
- `root +6`
- `child_2 +0`
- `child_2 +1`
- `child_2 +2`
- `child_2 +3`

Current normalized values:

Starter-owned family (`equip_hold_begin`):

- `root +4 = ptr_heap:-0x00000384`
- `root +5 = ptr_region:0x00010101`
- `root +6 = small_int:0x00000203`
- `child_2 +0 = ptr_region:0x00010003`
- `child_2 +1 = ptr_module:0x02010000`
- `child_2 +2 = small_int:0x00000502`
- `child_2 +3 = zero:0x00000000`

Probe-idle family (`idle_begin`):

- `root +4 = small_int:0x00000003`
- `root +5 = ptr_heap:+0x00002E00`
- `root +6 = ptr_heap:+0x00000028`
- `child_2 +0 = ptr_heap:+0x00000010`
- `child_2 +1 = ptr_heap:+0x4543FB4C`
- `child_2 +2 = ptr_heap:+0x0000003A`
- `child_2 +3 = small_int:0x00001574`

This is the cleanest ownership selector set in the repo now.

### 33.3 What stays stable

The render-head core still stays stable across the ownership swap:

- `render +0 = 2`
- `render +1 = 1`

So the live ownership change is not just random structure churn. It is preserving the render-head counters while swapping descriptor and root/child family state.

### 33.4 Caller-family split

Caller/stack-return families now differ across starter-owned and probe-idle branches.

Starter-owned branch:

- caller family:
  - `<other>:0x7BE6F7 > <other>:0x7BE2F2 > <other>:0x7D3FFE > <other>:0xDA37DF`
- stack-return family includes:
  - `0x00349BE0`
  - `0x00349C95`
  - `0x02FF39D0`
  - `0x02FED240`
- upstream hit present:
  - yes

Probe-idle branch:

- caller family:
  - `<other>:0x63E6F7 > <other>:0x63E2F2 > <other>:0x653FFE > <other>:0xDA37DF`
- stack-return family includes:
  - `0x0360D6A0`
  - `0x0037C68D`
  - `0x0037C6B7`
  - `0x035F4864`
  - `0x0034EAA5`
  - `0x03606900`
  - `0x03608380`
- upstream hit present:
  - no

### 33.5 Best current interpretation

The project is now past:

- “does the consumer path move at all?”
- “is child_2 always immutable?”

Current best model:

- the live starter-owned family and probe-owned family are different consumer object families
- the smallest distinguishing selector set lives in `root +4/+5/+6` and `child_2 +0/+1/+2/+3`
- downstream `child_3` / `child_4` are materialization, not the compact ownership source
- the upstream lookup bridge is currently only recovered for the starter-owned family

### 33.6 What to do next from here

Do not go back to:

- idle-only timing sweeps
- generic memory-name scans
- launcher work

Resume from:

- `20260403_034408`
- `grant_equip_family_bundle_summary.json`
- the missing probe-idle upstream bridge

The next real task is:

- capture the same upstream lookup family for the probe-idle branch
- then map the root/child selector bundle to the corresponding upstream lookup-family delta

## 34. Probe-idle upstream bridge is now recovered

This is the newest authoritative correction after section 33.

The missing probe-side upstream bridge is no longer missing.

Authoritative archive:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_041208`

Key implementation changes:

- `native/fx_runtime_probe/fx_runtime_probe_hook.cpp`
  - upstream-return arming now happens at the front of the first-hit `consumer_render_table` path
  - the stack candidate selector now buckets and scores upstream return sites instead of taking the first two blindly
- `tools/run_consumer_semantic_transition_compare.ps1`
  - longer post-hit dwell so upstream captures finish flushing
- `tools/analyze_grant_equip_family_bundle.ps1`
  - now emits per-variant upstream/render join summaries

### 34.1 What the new probe-idle run proved

On `idle_begin`:

- upstream return sites are armed
- upstream hits occur
- upstream anchor snapshots complete
- lookup-family span is captured

First recovered probe-side upstream hit:

- label:
  - `consumer_upstream_ret_00349C95`
- registers:
  - `EAX = 0x3359EF20`
  - `ESI = 0x33565900`
  - `EDI = 0x335658F8`

Corresponding first render hit:

- `render root = 0x33565850`
- `render = 0x33565930`
- `render lookup = 0x3359EF60`

Recovered join:

- `upstream_edi_to_render_root = +0x000000A8`
- `upstream_edi_to_render = -0x00000038`
- `upstream_esi_to_render = -0x00000030`
- `upstream_eax_to_lookup = -0x00000040`

That is now the cleanest live upstream/render join on the probe-owned branch.

### 34.2 Important correction to the older caller-bucket story

Do **not** assume the newest probe-owned branch still uses the earlier probe-only return bucket from section 33.

In `20260403_041208`:

- the ownership selector bundle on `idle_begin` is still distinct from starter-owned `equip_hold_begin`
- but the recovered upstream return family on `idle_begin` is now:
  - `0x00349C3B`
  - `0x00349C95`

So the updated interpretation is:

- probe-owned selection is still real on the root/child side
- probe-owned upstream connectivity is now recovered
- but the recovered upstream return-family on this run collapses onto the starter-style return sites

This supersedes the older simpler model of:

- “starter-owned uses starter upstream bucket”
- “probe-owned uses probe-only upstream bucket”

That older split was useful as an intermediate lead, but it is no longer the final authoritative model.

### 34.3 Current blocker now

The blocker is no longer:

- get probe-side upstream to fire

The blocker is now:

- explain how the probe-owned selector bundle
  - `root +4/+5/+6`
  - `child_2 +0/+1/+2/+3`
  reaches the recovered upstream lookup family
- explain why that probe-owned branch currently joins through the `0x00349C3B / 0x00349C95` upstream return family
- use the recovered `upstream_eax_to_lookup = -0x40` relation to keep reversing the selector/decode step

### 34.4 Resume work from here

Resume from these artifacts, in this order:

- `consumer_semantic_transitions/20260403_041208/semantic_transition_summary.json`
- `consumer_semantic_transitions/20260403_041208/grant_equip_family_bundle_summary.json`
- `consumer_semantic_transitions/20260403_041208/idle_begin/consumer_object_summary.json`
- `consumer_semantic_transitions/20260403_041208/idle_begin/fx_runtime_probe.log`

Do not go back to:

- launch work
- generic asset-presence scans
- weak phase-only diffs

The next productive task is selector/decode recovery on top of the probe-owned upstream/render join that now exists.

## 35. Joined ownership-family mapping and caller-family correction

This section supersedes the simpler “probe branch uses a different upstream return bucket” interpretation.

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_041208/grant_equip_joined_mapping_summary.json`

Implementation:

- `tools/analyze_grant_equip_joined_mapping.ps1`

### 35.1 What is now explicitly joined

The probe-owned branch is now described as one joined family:

- selector side:
  - `root +4/+5`
  - `child_2 +0/+1/+2/+3`
- upstream side:
  - `EDI = 0x335658F8`
  - `ESI = 0x33565900`
  - `EAX = 0x3359EF20`
- render side:
  - `root = 0x33565850`
  - `render = 0x33565930`
  - `render_plus_8 = 0x33565938`
  - `lookup = 0x3359EF60`

Recovered relations:

- `root -> upstream EDI = +0xA8`
- `root -> upstream ESI = +0xB0`
- `root -> render = +0xE0`
- `root -> render_plus_8 = +0xE8`
- `upstream EAX -> lookup = -0x40`

This is the cleanest current model of the probe-owned path.

### 35.2 Important correction

Do not treat `0x00349C3B / 0x00349C95` as the ownership discriminator anymore.

The joined summary shows those return sites are shared across starter/probe branch surfaces in the same grant/equip comparison.

Current best interpretation:

- those return sites are a stable caller/return family
- the ownership discrimination still happens in the selector/decode side, not in those return addresses alone

### 35.3 Confirmation rerun

Confirmation archive:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_042235`

What it proved:

- a longer dwell still does not produce starter-owned upstream hits in this harness
- so the missing starter-side live upstream bridge remains unresolved here
- but that does not change the joined-family correction above

### 35.4 Resume work from here

The next target is now very specific:

- use the joined probe-owned family to recover the selector/decode step from:
  - `root +4/+5`
  - `child_2 +0/+1/+2/+3`
  into:
  - `root +0xA8`
  - `root +0xB0`
  - `lookup - 0x40`

Do not spend another pass trying to rediscover caller buckets or generic upstream presence. That part is solved well enough now.

## 36. Probe-owned joined subviews are now explicit

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_041208/probe_joined_subviews_summary.json`

Implementation:

- `tools/analyze_probe_joined_subviews.ps1`

### 36.1 Corrected model

The selector bundle `root +4/+5/+6` should now be treated as belonging to the probe-owned `render_state_edi` / `upstream_edi` view, not to `render_state_esi_minus_e0`.

Current probe-owned joined-family layout:

- owning/render root:
  - `root = 0x33565850`
- selector-root subview:
  - `root + 0xA8 = upstream_edi = 0x335658F8`
- selector-decode subview:
  - `root + 0xB0 = upstream_esi = 0x33565900`
- descriptor/header subview:
  - `lookup - 0x40 = upstream_eax = 0x3359EF20`
- later lookup object:
  - `lookup = 0x3359EF60`

### 36.2 What the probe-owned branch now proves

The first-hit subview mapping is now explicit:

- `upstream_edi +4/+5/+6`
  - `0x3351BDCC`
  - `0x00020101`
  - `0x00000203`
  - this is the probe-owned selector-root bundle
- `upstream_esi +0`
  - points to `0x3123C374`
  - the pointer-chase dwords at that target are:
    - `0x00010003`
    - `0x02010000`
    - `0x00000502`
    - `0x00000000`
  - this is the exact `child_2 +0/+1/+2/+3` payload signature
- `upstream_esi +2/+3/+4`
  - mirror the probe-owned selector-root bundle again
- `upstream_eax`
  - is a descriptor/header family at `lookup - 0x40`
  - not the compact selector path
  - stable header-like fields:
    - `+0 = 0xA0AB1041`
    - `+1 = 0x02147063`
    - `+3 = 0x2C5D98C4`
  - stable ascii descriptor payload:
    - `+4 = 0x74672D7E` (`~-gt`)
    - `+5 = 0x6F665F35` (`5_fo`)
    - `+6 = 0x6761696C` (`liag`)
    - `+7 = 0x72645F65` (`e_dr`)
    - `+8 = 0x72625F79` (`y_br`)

### 36.3 Current blocker

The blocker is now narrower than the earlier joined-family summary:

- `root + 0xA8` is the selector-root view
- `root + 0xB0` is the decode path that points to and re-expresses `child_2`
- `lookup - 0x40` is the downstream descriptor/header family

So the remaining reverse-engineering target is the selector/decode step between:

- `root + 0xA8`
- `root + 0xB0`
- `child_2`

before the path materializes as:

- `lookup - 0x40`

## 37. Ownership-family compare across selector-root and selector-decode

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_041208/selector_root_decode_ownership_compare_summary.json`

Implementation:

- `tools/analyze_selector_root_decode_ownership_compare.ps1`

### 37.1 What this comparison adds

This pass compares ownership families directly on the selector-root / selector-decode hop instead of only describing the probe-owned branch in isolation.

Starter-owned selector-root:

- base:
  - `0x3353C0F8`
- important fields:
  - `+2 = 0x31577F68`
  - `+3 = 0x31576754`
  - `+4 = 0x3353BDCC`
  - `+5 = 0x00010101`
  - `+6 = 0x00000203`

Probe-owned selector-root:

- base:
  - `0x335658F8`
- important fields:
  - `+2 = 0x3123C374`
  - `+3 = 0x33563B8C`
  - `+4 = 0x3351BDCC`
  - `+5 = 0x00020101`
  - `+6 = 0x00000203`

Probe-owned selector-decode:

- base:
  - `0x33565900`
- key facts:
  - `+0 -> 0x3123C374`
  - that target decodes to the exact `child_2` payload
  - `+2/+3/+4` mirror the selector-root inputs

### 37.2 Minimal ownership-family delta set

The minimal selector-root delta across starter-owned vs probe-owned is now:

- `+2`
- `+3`
- `+4`
- `+5`

Invariant field:

- `+6 = 0x00000203`

This means the ownership-family distinction is concentrated in:

- the decode/projection candidate pair:
  - `+2`
  - `+3`
- and the selector input pair:
  - `+4`
  - `+5`

### 37.3 Highest-value unresolved roles now

The most important unresolved field roles are:

- starter `selector-root +2`
  - likely the starter-owned analog of the probe decode child pointer
- starter `selector-root +3`
  - likely dispatch/projection or a decode input
- probe `selector-decode +1`
  - likely projection/dispatch or a decode input

So the current blocker is not generic anymore. It is specifically the unresolved decode/dispatch roles around:

- starter `selector-root +2/+3`
- probe `selector-decode +1`

## 38. Probe selector-root +2 is now established, not tentative

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_041208/probe_selector_decode_consistency_summary.json`

Implementation:

- `tools/analyze_probe_selector_decode_consistency.ps1`

### 38.1 What this pass checked

This pass compared existing probe-family captures across:

- `20260403_014609/grant_plus_1s`
- `20260403_015837/grant_plus_1s`
- `20260403_021424/grant`
- `20260403_021424/grant_plus_2s`
- `20260403_041208/idle_begin`

### 38.2 What is now confirmed

The new consistency summary confirms:

- probe-family `render_state_edi +2` consistently pointer-chases to the same compact child payload family
- when a `child_2` snapshot exists, that `+2` pointer matches the recovered `child_2` base
- in the semantic idle archive, the same compact payload is still present through the split decode path:
  - `root + 0xB0 = upstream_esi`
  - `+0 -> child_2`

So probe-family `selector-root +2` should now be treated as:

- an established decode-child pointer

not merely:

- a plausible candidate

### 38.3 What remains unresolved

That leaves the unresolved ownership/decode roles as:

- starter `selector-root +2`
  - best starter-owned analog candidate
- starter `selector-root +3`
  - dispatch/projection candidate
- probe `selector-decode +1`
  - dispatch/projection candidate

So the next offline target is no longer proving the probe side. It is recovering the starter-side analog and separating true decode inputs from projection fields.

## 39. Starter/probe decode-child symmetry is now proven

Live archive:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_050555`

Authoritative symmetry summary:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_050555/starter_probe_decode_child_symmetry_summary.json`

Implementation:

- `tools/analyze_starter_probe_decode_child_symmetry.ps1`

### 39.1 What is now settled

Starter-owned branch:

- selector-root base:
  - `0x32D858F8`
- `selector-root +2 = 0x30A5C374`
- captured starter decode child:
  - `0x30A5C374`
- starter decode-child payload:
  - `0x00010003`
  - `0x02010000`
  - `0x00000502`
  - `0x00000000`

Probe-owned reference branch:

- selector-root base:
  - `0x335658F8`
- `selector-root +2 = 0x3123C374`
- probe decode-child payload:
  - `0x00010003`
  - `0x02010000`
  - `0x00000502`
  - `0x00000000`

Confirmed conclusions:

- starter `selector-root +2` is the starter-owned analog of the established probe decode-child pointer
- starter and probe decode-child payloads match exactly

### 39.2 What remains unresolved

This means `+2` is no longer the open question.

The next unresolved roles are now:

- starter `selector-root +3`
- probe `selector-root +3`
- probe `selector-decode +1`

So the next useful pass should focus on whether `+3` / decode `+1` are:

- true dispatch inputs
or
- downstream projection fields

## 40. The semantic transition harness now captures `equip_hold_begin` pre-grant

The old `equip_hold_begin` runner ordering was wrong. It effectively waited for `grant`, then waited for `equip_hold_begin`, then injected, which is too late for a true starter-owned capture.

This is now fixed in:

- `tools/run_consumer_semantic_transition_compare.ps1`

Current trigger policy:

- `equip_hold_begin`
  - inject on `[bo3_rev][player_state] stage=pre_grant`
- `idle_begin`
  - inject on `[bo3_rev][grant]`

The runner also now regenerates `consumer_object_summary.json` from the archived `fx_runtime_probe.log` copy instead of the live probe handle.

Validated post-fix archive:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_053026`

Sequencing proof:

- pre-grant:
  - `[bo3_rev][player_state][t=2650] ... cur=m1911_zm`
- starter stage:
  - `[bo3_rev][anim_probe][t=2700] stage=equip_hold_begin ... cur=m1911_zm`
- grant:
  - `[bo3_rev][grant][t=3800] ... current=mg08_zm`

So the starter capture is now genuinely pre-grant.

## 41. `selector-root +3` and `selector-decode +1` are the same probe-side field

Artifacts:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_053026/selector_dispatch_role_matrix_summary.json`
- `tools/analyze_selector_dispatch_role_matrix.ps1`

This pass used:

- corrected starter archive:
  - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_053026/equip_hold_begin`
- authoritative probe-owned joined-family archive:
  - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_041208/idle_begin`

What is now proven on the probe-owned branch:

- selector-root base:
  - `0x335658F8`
- selector-decode base:
  - `0x33565900`
- selector-root `+3`
  - slot addr `0x33565904`
  - value `0x33563B8C`
- selector-decode `+1`
  - slot addr `0x33565904`
  - value `0x33563B8C`

So:

- `selector-decode +1` is not an independent selector field
- it is the split-view alias of `selector-root +3`

The probe-side role model is now:

- `+2`
  - decode-child pointer
- `+3`
  - family-specific pointer into the downstream `child_3` descriptor/materialization block
- `decode +1`
  - same field as `+3`

This is backed by the probe consumer summary:

- `render_state_edi_child_3` base:
  - `0x33563B8C`

which matches the probe `selector-root +3` value exactly.

## 42. Current blocker after the `+3 / decode +1` role pass

The ambiguity between `selector-root +3` and `selector-decode +1` is gone.

Current state:

- probe branch:
  - `+3` / `decode +1` are the same field
  - that field points to `child_3`
- starter branch:
  - the corrected archive is genuinely pre-grant
  - but the same joined selector-root/decode subview still does not materialize in the archived probe log

So the next blocker is now:

- recover the joined selector-root/decode surface on the true starter-owned pre-grant branch
- then compare the starter-owned `+3` descriptor/projection pointer against the probe-owned `+3` pointer directly
## 43. Correction: the starter joined selector-root/decode surface is now recovered (2026-04-03)

Sections 41-42 below are now superseded by a newer archive.

Authoritative artifacts:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/equip_hold_begin/consumer_object_summary.json`
- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/selector_dispatch_role_matrix_summary.json`

What the newer starter-owned pre-grant archive proves:

- starter root:
  - `0x30BE7D98`
- starter selector-root:
  - `0x30BE7E40`
  - `root + 0xA8`
- starter selector-decode:
  - `0x30BE7E48`
  - `selector-root + 0x8`
- starter render:
  - `0x30BE7E78`
  - `root + 0xE0`

Starter selector-root fields now recovered in a true pre-grant archive:

- `+2 = 0x30ABC374`
  - points to starter `child_2`
- `+3 = 0x30B06060`
  - points to starter `child_3`
- `+4 = 0x30BE7ABC`
- `+5 = 0x00010101`
- `+6 = 0x00000203`

Updated role model across both ownership branches:

- `selector-root +2`
  - shared decode-child pointer
- `selector-root +3`
  - same field as `selector-decode +1`
  - points into the branch-specific `child_3` descriptor/materialization block
- `selector-root +2` is not the ownership discriminator

So the old blocker is dead. The current blocker is now narrower:

- the starter joined surface is recovered
- `+2` is solved on both branches
- `+3` / `decode +1` are solved on both branches
- the next direct branch-role comparison is the selector bundle around:
  - `+3`
  - `+4`
  - `+5`

Current best role split:

- `+2`
  - shared compact decode-child pointer
- `+3`
  - family-specific descriptor/projection pointer
- `+4` / `+5`
  - best remaining candidates for the true ownership dispatch/materialization split

## 44. Fresh live confirmation and focused `+4 / +5` role pass (2026-04-03)

Fresh live confirmation archive:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_055327`

Important verification from the corrected runner:

- `equip_hold_begin/variant_summary.json`
  - `joined_surface_seen = true`
  - `joined_surface_line = consumer_anchor_snapshot context=render_state_edi phase=first_hit base=0x314A7E40 ...`
- `idle_begin/variant_summary.json`
  - `joined_surface_seen = true`

So the runner fallback is now validated on a real fresh archive. Starter joined-surface success is recognized from the archived `render_state_edi` anchor snapshot.

Focused analyzer:

- `tools/analyze_selector_plus45_role_compare.ps1`
- authoritative output:
  - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/selector_plus45_role_summary.json`

What the focused `+4 / +5` compare proves:

- on both branches:
  - `selector-root +4`
    - points to the branch-specific `child_4` descriptor family
  - `selector-root +5`
    - differs across starter vs probe
  - `selector-root +6`
    - matches across both branches (`0x00000203`)
- `child_3[-3]`
  - tracks `selector-root +5` on both branches
- `child_4[-3]`
  - tracks `selector-root +5` on the starter branch
  - does **not** track it on the probe branch, where `child_4[-3]` stays `0x00010101`

Best current interpretation:

- `+4`
  - branch-specific pointer/base into `child_4`
- `+5`
  - smallest compact branch discriminator currently recovered
  - mirrored into `child_3` headers on both branches
- `+6`
  - shared structural constant

Current blocker:

- determine whether `+5` alone is sufficient to drive ownership-family dispatch
- or whether `+4` and `+5` form a coupled selector/base pair before `child_3` / `child_4` materialization

## 45. Paired-role analysis: `+4 / +5` should be treated as a coupled selector/base pair (2026-04-03)

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/selector_plus45_tuple_pairing_summary.json`
- `tools/analyze_selector_plus45_tuple_pairing.ps1`

This pass answered the narrow dispatch question directly: is `+5` alone the true discriminator, or do `+4` and `+5` need to be interpreted together?

The tuple comparison used:

- starter:
  - `(+4, +5) = (0x30BE7ABC, 0x00010101)`
- probe:
  - `(+4, +5) = (0x3351BDCC, 0x00020101)`

and compared those tuples against:

- `child_3[-3]`
- `child_4[-3]`

What is now proven:

- `+5` alone tracks `child_3[-3]` on both branches
- `+4` independently changes across branches and points to the branch-local `child_4` base on both branches
- probe `child_4[-3]` does **not** follow probe `+5`
  - probe `+5 = 0x00020101`
  - probe `child_4[-3] = 0x00010101`

So the best-supported role call is now:

- `+4 / +5` must be interpreted together as a coupled selector/base pair

Best current interpretation:

- `+5`
  - compact family/mode signal
- `+4`
  - branch-local descriptor/materialization base
- the live dispatch surface is the tuple:
  - `(+4, +5)`

Current blocker:

- recover where the coupled `(+4, +5)` tuple is consumed before `child_4` materialization diverges on the probe branch

## 46. Selector-decode is the first recovered consumer of the coupled `(+4, +5)` tuple (2026-04-03)

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/selector_decode_tuple_consumer_summary.json`
- `tools/analyze_selector_decode_tuple_consumer.ps1`

This pass answered the next narrow question directly: what is the earliest recovered object that sees the coupled `(+4, +5)` tuple together before `child_4` diverges?

Result:

- the earliest recovered tuple consumer is:
  - `selector-decode`
  - `selector-root + 0x8`

Recovered selector-decode fields on both branches:

- starter:
  - `decode +1 = 0x30B06060`
    - same as starter `selector-root +3`
    - same as starter `child_3` base
  - `decode +2 = 0x30BE7ABC`
    - same as starter `selector-root +4`
  - `decode +3 = 0x00010101`
    - same as starter `selector-root +5`
- probe:
  - `decode +1 = 0x33563B8C`
    - same as probe `selector-root +3`
    - same as probe `child_3` base
  - `decode +2 = 0x3351BDCC`
    - same as probe `selector-root +4`
  - `decode +3 = 0x00020101`
    - same as probe `selector-root +5`

Concrete statement now supported by the repo:

- the selector-decode subview is the first recovered object that sees the coupled `(+4, +5)` tuple together and projects it toward branch-specific `child_3` state
- `decode +1`
  - branch-specific `child_3` projection pointer
- `decode +2`
  - mirror of `selector-root +4`
- `decode +3`
  - mirror of `selector-root +5`

Current blocker:

- recover the next consumer after selector-decode that turns the coupled `(+4, +5)` tuple and `child_3` projection into probe-divergent `child_4` materialization

## 47. `child_3` header is the first recovered post-decode consumer (2026-04-03)

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/post_decode_child3_consumer_summary.json`
- `tools/analyze_post_decode_child3_consumer.ps1`

This pass pushed one step past selector-decode and asked: what is the first recovered post-decode consumer that maps the tuple and `child_3` projection toward `child_4`?

Result:

- the first recovered post-decode consumer is:
  - `child_3` header fields
  - `(-4, -3, -2)`

Recovered role split:

- `child_3[-3]`
  - mirror of `+5` compact family/mode
- `child_3[-2]`
  - mirror of `+6` structural constant
- `child_3[-4]`
  - first branch-specific materialization pointer after selector-decode

What is now proven about `child_3[-4]`:

- on probe:
  - `child_3[-4]` resolves directly to the final `child_4` base
  - target:
    - `0x3351BDCC`
- on starter:
  - `child_3[-4]` does **not** resolve directly to the final `child_4` base
  - target:
    - `0x30B078BC`
  - starter `child_4` base:
    - `0x30BE7ABC`
  - but the starter target still has the same child4-like `+0x10` descriptor shape

Concrete statement now supported by the repo:

- the `child_3` header is the first recovered post-decode consumer that maps selector-decode output toward `child_4` materialization
- probe collapses this step directly to `child_4`
- starter inserts one more child4-like intermediate descriptor node after `child_3[-4]`

Current blocker:

- recover the consumer between starter `child_3[-4]`'s intermediate descriptor node and final `child_4` base
- explain why the probe branch collapses that step directly to `child_4`

## 48. The starter-only `child_4` split is a clone/projection boundary, not a new selector surface (2026-04-03)

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/child4_clone_boundary_summary.json`
- `tools/analyze_child4_clone_boundary.ps1`

This pass used the existing starter/probe archive to close the next ambiguity. The extra starter hop is not a new unresolved selector stage. It is a clone/projection boundary between the child3-side descriptor pool and the root-local child4 binding surface.

Recovered starter-side bridge:

- starter `child_3[-4]`
  - points to:
    - `0x30B078BC`
  - that object is child4-like:
    - `dword0 = target + 0x10`
    - same compact header shape family as final `child_4`
- starter final `child_4` base:
  - `0x30BE7ABC`
- starter `selector-root +4`
  - `0x30BE7ABC`
- starter `selector-decode +2`
  - `0x30BE7ABC`

Recovered probe-side collapse:

- probe `child_3[-4]`
  - points directly to:
    - `0x3351BDCC`
- probe final `child_4` base:
  - `0x3351BDCC`
- probe `selector-root +4`
  - `0x3351BDCC`
- probe `selector-decode +2`
  - `0x3351BDCC`

Concrete statement now supported by the repo:

- the starter-only hop is a child4-like clone/projection boundary, not a new selector surface
- on starter:
  - `child_3[-4]`
    - points to an intermediate child4-like descriptor clone in the child3-side pool
  - `selector-root +4` and `selector-decode +2`
    - are already bound to the final root-local `child_4` self-base descriptor
- on probe:
  - `child_3[-4]`, `selector-root +4`, `selector-decode +2`, and final `child_4`
    - collapse to the same object

Current blocker:

- explain the projection/materialization step that makes starter `child_3[-4]` land on a clone while root-local `+4` / `decode+2` already bind the final `child_4` self-base object

## 49. The first recovered post-clone link is the shared child4-like `-1` materializer class (2026-04-03)

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/child4_projection_materializer_summary.json`
- `tools/analyze_child4_projection_materializer.ps1`

This pass stayed strictly on the starter-only clone boundary and asked for the first concrete link between the child3-side clone view and final root-local `child_4`.

Result:

- the first recovered link is **not** another selector field
- it is a shared child4-like materializer/control class at descriptor slot:
  - `-1`

Recovered `-1` materializer class:

- starter child3-side clone:
  - `child_3[-1] -> 0x30B07BE4`
  - signature:
    - `0x00000003`
    - `0x00030040`
    - `0x040000D5`
    - `0x02400003`
- starter final `child_4`:
  - `child_4[-1] -> 0x30BE7DF4`
  - same signature
- probe child3-side view:
  - `child_3[-1] -> 0x335658A4`
  - same signature
- probe final `child_4`:
  - `child_4[-1] -> 0x3351C0B0`
  - same signature

What is now proven:

- authoritative final bind is already root-local on both branches:
  - `selector-root +4`
  - `selector-decode +2`
  - final `child_4`
- starter clone and final `child_4` have distinct `-1` targets
- probe clone and final `child_4` also have distinct `-1` targets
- but all four `-1` targets carry the same materializer/control signature class
- probe therefore does **not** bypass the `-1` materializer class
- probe bypasses the earlier clone boundary at:
  - `child_3[-4]`

Concrete statement now supported by the repo:

- the first recovered post-clone link between starter child3-side clone and final starter `child_4` is a shared child4-like materializer class at descriptor slot `-1`
- on starter:
  - `child_3[-4]`
    - lands on a child3-side clone
  - both clone and final `child_4`
    - carry their own local `-1` materializer blocks of the same class
- on probe:
  - the same `-1` materializer class still exists
  - but the clone boundary is short-circuited earlier because `child_3[-4]` already equals the final `child_4` base

Current blocker:

- recover how the starter branch projects from the child3-side child4-like clone to the root-local final `child_4` bind despite both descriptors already carrying the same local `-1` materializer class

## 50. No direct descriptor-local field links the starter clone to final `child_4`; the first recovered projection link is root-local (2026-04-03)

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/starter_clone_projection_link_summary.json`
- `tools/analyze_starter_clone_projection_link.ps1`

This pass tested the narrowest remaining theory on the starter clone boundary: whether the child3-side clone descriptor or final `child_4` descriptor contains any direct recovered local field that links one to the other.

Result:

- no direct descriptor-local field was recovered that links the starter clone descriptor to final `child_4`
- no direct descriptor-local field was recovered that links final `child_4` back to the starter clone
- the first recovered projection link therefore remains:
  - `selector-root +4`
  - `selector-decode +2`
  - the authoritative root-local final `child_4` bind

Recovered starter-side non-link evidence:

- starter clone base:
  - `0x30B078BC`
- starter final `child_4` base:
  - `0x30BE7ABC`
- captured clone-local fields:
  - `dword0 = 0x30B078CC`
  - `dword1 = 0x92C84EF8`
  - `dword2 = 0x30B078F7`
  - `dword3 = 0x000002EC`
  - `-1 target = 0x30B07BE4`
- captured final-`child_4` local fields:
  - `dword0 = 0x30BE7ACC`
  - `dword1 = 0xA13662B8`
  - `dword2 = 0x30BE7AF6`
  - `dword3 = 0x000002FC`
  - `-1 target = 0x30BE7DF4`

What is now proven:

- starter clone and final `child_4` are parallel descriptors, not a directly recovered parent/child pair
- the clone does **not** locally point to final `child_4`
- final `child_4` does **not** locally point back to the clone
- probe collapse control confirms the interpretation:
  - probe `child_3[-4]`
  - probe `selector-root +4`
  - probe `selector-decode +2`
  - final probe `child_4`
    - all collapse to the same base

Concrete statement now supported by the repo:

- no direct descriptor-local field in the recovered starter clone or final `child_4` windows links the clone descriptor to the final `child_4` base
- the first recovered projection link is therefore external and root-local:
  - `selector-root +4 / selector-decode +2`
    - already emit the authoritative final `child_4` bind
- the child3-side clone remains a parallel descriptor view

Current blocker:

- recover the earlier root-local or projection-layer object that emits both the child3-side clone view and the authoritative root-local final `child_4` bind on the starter branch

## 51. The first recovered common parent emitter is selector-root, mirrored by selector-decode (2026-04-03)

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/common_parent_emitter_summary.json`
- `tools/analyze_common_parent_emitter.ps1`

This pass stopped treating the starter clone and final `child_4` as if one had to locally transform into the other. It asked for the first recovered object that can already see and emit both outputs in the same family.

Result:

- the first recovered common parent emitter is:
  - `selector-root`
  - mirrored by:
    - `selector-decode`

Recovered emitter field set:

- `selector-root +3`
  - branch-specific `child_3` projection output
- `selector-root +4`
  - authoritative final `child_4` bind
- `selector-root +5`
  - compact branch-family/mode tag
- `selector-root +6`
  - shared structural constant
- `selector-decode`
  - mirrors the same emitter surface:
    - `decode +1 = root +3`
    - `decode +2 = root +4`
    - `decode +3 = root +5`
    - `decode +4 = root +6`

What is now proven:

- on starter:
  - `selector-root`
    - emits two sibling outputs from the same recovered family
  - `+3`
    - emits the child3-side projection view
    - whose `-4`
      - becomes the starter clone descriptor
  - `+4`
    - emits the authoritative final root-local `child_4` bind
- on probe:
  - the same emitter surface exists
  - but probe collapses the outputs to identity because:
    - `child_3[-4] == final child_4 == root +4`

Concrete statement now supported by the repo:

- the first recovered common parent emitter is the root-local `selector-root` field set, mirrored by `selector-decode`
- on starter:
  - it emits both the child3-side clone view and the authoritative final root-local `child_4` bind
- on probe:
  - it emits one unified collapsed `child_4` view

## 52. The selector-root +7 tail is downstream, not the projection-policy producer (2026-04-03)

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/root_local_policy_tail_summary.json`
- `tools/analyze_root_local_policy_tail.ps1`

This pass tested whether the recovered `selector-root +7` tail block was the earlier root-local producer behind the starter split versus probe collapse model.

Result:

- starter tail:
  - `child7[-4] = root +4 = final child_4`
  - `child7[-3] = root +5`
  - `child7[-2] = root +6`
  - `child7[-1] = self`
  - `child7[+0] = root +8`
- probe tail:
  - same structure
  - same mirror roles

What is now proven:

- `render_state_edi_child_7`
  - is downstream
  - not the earlier split/collapse policy producer
- it mirrors only:
  - `root +4`
  - `root +5`
  - `root +6`
- it does not carry:
  - `root +3`
    - the child3-side projection output

Concrete statement now supported by the repo:

- the selector-root `+7` tail block is a downstream root-tail view of the authoritative child4-side branch
- the split-versus-collapse policy is already decided before this tail block

Current blocker:

- recover the earlier root-local or projection-policy producer that writes `selector-root +3/+4` before the `+7` tail mirrors only the authoritative child4 side

## 53. No earlier local producer appears inside the widened selector-root policy window (2026-04-03)

Authoritative artifacts:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_123139/selector_root_policy_window_summary.json`
- `tools/analyze_selector_root_policy_window_compare.ps1`
- `native/fx_runtime_probe/fx_runtime_probe_hook.cpp`

This pass widened the live capture around `selector-root` itself using a dedicated `render_state_edi_policy` window and reran the same starter/probe ownership-edge harness.

Result:

- starter policy window:
  - `0x31087E40`
- probe policy window:
  - `0x31037E40`
- after normalization:
  - slots `-16 .. +1`
    - are branch-invariant
  - `+2`
    - is still only the shared decode-child pointer
  - there is no newly recovered earlier local producer before `+3`

What is now proven:

- the widened local prefix inside selector-root is not the missing policy source
- the next unresolved producer is either:
  - outside the currently recovered selector-root window
  - or a write site that populates `selector-root +3/+4/+5` before first-hit capture

Concrete statement now supported by the repo:

- no earlier root-local prefix field inside the widened selector-root policy window explains starter-versus-probe policy
- the earliest recovered policy surface is still the selector-root output region itself

Current blocker:

- recover an earlier root-local producer outside the current selector-root window, or recover the write site that populates `selector-root +3/+4/+5` before first-hit capture

Current blocker:

- recover the earlier projection-policy object or root-local producer that populates `selector-root +3/+4` with starter’s split outputs versus probe’s collapsed identity output

## 54. Direct selector-root write provenance did not surface; the earliest live starter producer is `consumer_asset_class_lookup` (2026-04-03)

I implemented a direct write-provenance pass on the actual selector-root policy fields in [fx_runtime_probe_hook.cpp](/z:/Games/pluto_t6_full_game/native/fx_runtime_probe/fx_runtime_probe_hook.cpp). On the first recovered selector-root render hit, the probe now arms guarded watches for `selector-root +3`, `+4`, and `+5` and keeps the run alive long enough to catch a later overwrite if one occurs.

The authoritative run is [20260403_125212](/z:/Games/pluto_t6_full_game/_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_125212).

What that run proved:

- Probe idle still reaches the selector-root render surface.
  - `consumer_render_table` hit first.
  - the watcher armed on `selector_root_plus3/+4/+5`.
  - but no `policy_write_guard_hit` or `policy_write_commit` followed.
- Starter pre-grant is still one stage earlier.
  - the first live consumer hit on `equip_hold_begin` was `consumer_asset_class_lookup`, not `consumer_render_table`.
  - the joined selector-root render surface did not materialize on that branch in this run.
  - so there was no starter-side selector-root page to watch yet.

This kills the current easy write-side theory too:

- the missing producer is not hiding in the widened local selector-root read window
- and it is not surfacing as a direct post-hit writer on the already recovered selector-root page either

The earliest dynamic predecessor visible in the same starter archive is the asset-lookup family:

- `asset_lookup_edi` mutates immediately after first hit
  - `+3: 0x033F3880 -> 0x00000006`
  - `+4: 0x00000000 -> 0x00000007`
  - `+5: 0x00000000 -> 0x64356E1C`
- `asset_lookup_eax` mutates too
  - `+0: 0x010161EA -> 0x010161F4`
  - `+4: 0x000000EA -> 0x000000F4`
- `asset_lookup_ecx` stays relatively stable compared to the other two

Current blocker after this correction:

- we do not currently have a direct writer for `selector-root +3/+4/+5`
- the earliest live starter-side producer we can actually see mutating is `consumer_asset_class_lookup`
- the next correct frontier is earlier than selector-root: recover how the `asset_lookup` owner/source/class family emits the later selector-root policy surface
## 55. Dedicated `xanim_asset_lookup_focus` recovers the probe-owned producer, but starter symmetry is still missing on the current lane (2026-04-03)

I added a dedicated `xanim_asset_lookup_focus` mode in [fx_runtime_probe_hook.cpp](/z:/Games/pluto_t6_full_game/native/fx_runtime_probe/fx_runtime_probe_hook.cpp) so the probe can arm only `consumer_asset_class_lookup` without the render surface taking over first. I also fixed [run_consumer_semantic_transition_compare.ps1](/z:/Games/pluto_t6_full_game/tools/run_consumer_semantic_transition_compare.ps1) so the mode file is no longer reset back to `xanim_consumer_focus` inside the per-variant loop.

The authoritative archive is [20260403_134746](/z:/Games/pluto_t6_full_game/_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_134746).

What it proved:

- The new mode really loaded.
  - probe log reports `value=xanim_asset_lookup_focus`
  - only `consumer_asset_class_lookup` was armed
- Probe-owned `post_switch` now recovers the producer family directly.
  - first hit is `consumer_asset_class_lookup`
  - `asset_lookup_seen = true`
  - first hit tuple: `edi=0x5F899010 eax=0x5F899080 ecx=0x380D9C34 esi=0x00000126`
  - compact tuple: owner `0x5F899010`, owner_plus_4/source `0x5F899080`, class `0x380D9C34`, class_head `0x380DD814`, class_word `0x0001`
  - producer-layer stack-return families now exist:
    - `consumer_asset_class_lookup|plutonium-bootstrapper-win32.exe:0x02FF4E10`
    - `consumer_asset_class_lookup|plutonium-bootstrapper-win32.exe:0x02C00000`
    - `consumer_asset_class_lookup|plutonium-bootstrapper-win32.exe:0x1222273F`
- The producer snapshot is stable across deferred captures.
  - `asset_lookup_edi` hash stays `0x38F3BA4D`
  - `asset_lookup_eax` hash stays `0xB177170D`
  - `asset_lookup_ecx` hash stays `0x579378B0`
- Starter symmetry is still missing on the same dedicated lane.
  - `equip_hold_begin` armed correctly
  - but no consumer hit fired on that branch in the same run
  - so the best starter-side producer evidence remains [20260403_125212](/z:/Games/pluto_t6_full_game/_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_125212)

Current blocker after this correction:

- the producer layer is now directly recovered on the probe-owned branch
- the missing symmetry is specifically starter-side producer recovery on the same dedicated lane
- the authoritative producer-layer compare is now starter `20260403_125212` vs probe `20260403_134746`
## 56. Dedicated asset_lookup producer symmetry is recovered on both branches (2026-04-03)

This is the current authoritative producer-layer checkpoint.

What changed:
- `native/fx_runtime_probe/fx_runtime_probe_hook.cpp`
  - `xanim_asset_lookup_focus` now arms much earlier:
    - initial arm delay `250ms`
    - retry cadence `500ms`
  - asset-lookup deferred snapshot timing is shorter:
    - `post_hit_100ms`
    - `post_hit_400ms`
    - `post_hit_1200ms`
    - `post_hit_2500ms`
- `tools/run_consumer_semantic_transition_compare.ps1`
  - new transition: `asset_lookup_starter_only`
  - injects on true starter-side `pre_grant`
  - uses dedicated `xanim_asset_lookup_focus`
  - exits after producer capture instead of waiting for later selector-root materialization
- `tools/analyze_asset_lookup_owner_family_compare.ps1`
  - defaults now point at the dedicated starter/probe producer archives

Starter authoritative archive:
- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_140546/equip_hold_begin`

Starter proof:
- real pre-grant branch:
  - `pre_grant` at `t=2650`
  - `equip_hold_begin` at `t=2700`
  - `grant` at `t=3800`
- dedicated mode:
  - `probe_mode = xanim_asset_lookup_focus`
- earliest recovered starter producer family:
  - hit 1:
    - `owner = 0x5F9F9000`
    - `source = 0x5F9F9070`
    - `class = 0x2DFE5754`
    - `class_head = 0x2DFE7BC0`
    - `class_word = 0x0001`
    - `esi_nibble = 0x7`
  - hit 2:
    - `owner = 0x5F9F9000`
    - `source = 0x5F9F9070`
    - `class = 0x2FC10DAC`
    - `class_head = 0x2FC14390`
    - `class_word = 0x0001`
    - `esi_nibble = 0xA`
- starter caller / return families:
  - selected caller:
    - `0x00741F6C`
  - stack return families:
    - `0x02FF4D50`
    - `0x1031C49F`
    - `0x1061C471`

Probe authoritative reference:
- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_134746/post_switch`

Probe proof:
- hit 1:
  - `owner = 0x5F899010`
  - `source = 0x5F899080`
  - `class = 0x380D9C34`
  - `class_head = 0x380DD814`
  - `class_word = 0x0001`
  - `esi_nibble = 0x6`
- selected caller:
  - `0x00741F6C`
- stack return families:
  - `0x02FF4E10`
  - `0x02C00000`
  - `0x1222273F`

Authoritative compare:
- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_134746/asset_lookup_owner_family_compare_summary.json`
- compare conclusion:
  - `asset_lookup_owner_family_recovered_on_both_branches`

Current model after this checkpoint:
- `consumer_asset_class_lookup` is now the earliest recovered live mutable producer layer on both branches.
- `selector-root +3/+4/+5` is downstream of that producer layer.
- producer symmetry is no longer blocked.
- the branch split now lives in:
  - producer-family contents
  - producer stack-return families
  - later downstream population of selector-root

Important caveat:
- starter dedicated runs now recover the producer family directly, but the dedicated deferred snapshot thread did not emit clean `post_hit_*` archive lines on the starter archive even though it started.
- The strongest starter stability evidence in this checkpoint is therefore:
  - repeated producer hits
  - stable owner/source
  - stable selected caller
  - class/class_head evolution inside the same starter-owned producer family

Active blocker:
- recover which `consumer_asset_class_lookup` field(s) are the first producer inputs that later materialize as downstream selector-root `+3/+4/+5`

Do not regress to:
- mixed consumer traces as the primary producer proof
- selector-root-only recovery as the main frontier
- launch/automation debugging

## 57. Producer-to-selector materialization candidates are narrowed to the class/class_head family (2026-04-03)

Authoritative summary:
- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_134746/asset_lookup_to_selector_materialization_summary.json`

This pass joined the dedicated producer-layer recovery to the already-established downstream selector bundle. The goal was to answer one narrow question: which `consumer_asset_class_lookup` fields are the earliest producer inputs for downstream selector-root `+3/+4/+5`.

Inputs:
- starter producer archive:
  - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_140546/equip_hold_begin`
- probe producer archive:
  - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_134746/post_switch`
- downstream selector summaries:
  - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/selector_dispatch_role_matrix_summary.json`
  - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/selector_plus45_role_summary.json`

Recovered producer-side shape:
- starter hit 1:
  - `class = 0x2DFE5754`
  - `class_head = 0x2DFE7BC0`
  - `class +2 = 0x2DFDBB20`
  - `class +3 = 0x2DFDEDD0`
  - `class +4 = 0x2DFE5774`
  - `class +5 = 0x00120105`
  - `class +6 = 0x00000201`
- starter hit 2:
  - `class = 0x2FC10DAC`
  - `class_head = 0x2FC14390`
  - `class +2 = 0x2FC02BCC`
  - `class +3 = 0x2FC07E90`
  - `class +4 = 0x2FC10DCC`
  - `class +5 = 0x01150105`
  - `class +6 = 0x00000201`
- probe hit 1:
  - `class = 0x380D9C34`
  - `class_head = 0x380DD814`
  - `class +2 = 0x30B6A428`
  - `class +3 = 0x380D9C54`
  - `class +4 = 0x380DBAEC`
  - `class +5 = 0x00070101`
  - `class +6 = 0x00000203`

Joined downstream selector outputs:
- starter:
  - `selector-root +3 = 0x30B06060`
  - `selector-root +4 = 0x30BE7ABC`
  - `selector-root +5 = 0x00010101`
  - `selector-root +6 = 0x00000203`
- probe:
  - `selector-root +3 = 0x33563B8C`
  - `selector-root +4 = 0x3351BDCC`
  - `selector-root +5 = 0x00020101`
  - `selector-root +6 = 0x00000203`

What this rules out:
- the earliest producer inputs are not the outer owner/source wrapper
- `class_word = 0x0001` is structural, not the earliest branch discriminator
- the producer frontier is not “owner/source vs selector-root”; it is the class/class_head family

What is now established:
- structural wrapper fields:
  - `source = owner + 0x70` on both branches
  - `class_word = 0x0001` on both branches
  - starter `owner/source` are stable across repeated hits while `class/class_head` evolve
- earliest recovered producer-side pointer-family candidates upstream of selector-root `+3/+4`:
  - `class`
  - `class_head`
  - `class +2`
  - `class +3`
  - `class +4`
- earliest recovered producer-side compact candidates upstream of selector-root `+5`:
  - `class +5`
  - `class +6`

Best current interpretation:
- the earliest recovered producer inputs for downstream selector-root `+3/+4/+5` are the branch-shaped `class/class_head` family, not the outer producer wrapper
- `class/+2/+3/+4` are the best current upstream candidates for downstream selector-root pointer-family materialization
- `class/+5/+6` are the best current upstream candidates for downstream selector-root compact flag materialization

Current blocker after this pass:
- producer symmetry is already recovered
- the active unresolved step is now:
  - which `consumer_asset_class_lookup` class/class_head field(s) are the first producer inputs that later materialize as downstream selector-root `+3/+4/+5`

## 58. Producer-to-selector field join and class-family role split are explicit (2026-04-03)

Authoritative summaries:
- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_134746/producer_to_selector_field_join_summary.json`
- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_134746/class_family_role_split_summary.json`

This pass decomposed the producer layer into:
- pointer-family inputs for downstream selector-root `+3/+4`
- compact-family inputs for downstream selector-root `+5/+6`

Recovered pointer-family split:
- earliest branch-local projection-base candidates upstream of selector-root `+3/+4`:
  - `class`
  - `class_head`
  - `class +2`
  - `class +3`
  - `class +4`
- branch-local roles inside that family:
  - starter hit 1:
    - `class +2 = external_ptr_family`
    - `class +3 = external_ptr_family`
    - `class +4 = self_plus_0x20`
  - starter hit 2:
    - `class +2 = external_ptr_family`
    - `class +3 = external_ptr_family`
    - `class +4 = self_plus_0x20`
  - probe hit 1:
    - `class +2 = external_ptr_family`
    - `class +3 = self_plus_0x20`
    - `class +4 = external_ptr_family`

Recovered compact-family split:
- earliest compact family-code candidates upstream of selector-root `+5/+6`:
  - `class +5`
  - `class +6`
- values:
  - starter hit 1:
    - `class +5 = 0x00120105`
    - `class +6 = 0x00000201`
  - starter hit 2:
    - `class +5 = 0x01150105`
    - `class +6 = 0x00000201`
  - probe hit 1:
    - `class +5 = 0x00070101`
    - `class +6 = 0x00000203`
- downstream selector reference:
  - starter:
    - `selector-root +5 = 0x00010101`
    - `selector-root +6 = 0x00000203`
  - probe:
    - `selector-root +5 = 0x00020101`
    - `selector-root +6 = 0x00000203`
- role interpretation:
  - `class +5` is the stronger branch-shaped compact signal before selector normalization
  - `class +6` behaves partly structural and converges to downstream selector `+6`

Best current interpretation:
- `class/class_head` choose the branch-local projection-base family for downstream selector-root `+3/+4`
- `class +5/+6` carry the upstream compact family code that later normalizes into downstream selector-root `+5/+6`
- within that compact pair, `class +5` is the stronger branch discriminator and `class +6` is partly structural

Current blocker after this pass:
- which exact `class/class_head/+2/+3/+4` field(s) emit downstream selector-root `+3/+4`
- whether `class +5` alone is the true compact discriminator for downstream selector-root `+5`, with `class +6` acting as partly structural pre-normalization state

## 59. Canonical producer->selector emission model is ranked and falsifiable (2026-04-03)

Authoritative summary:
- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_134746/canonical_producer_selector_emission_summary.json`

This pass consolidated the authoritative producer and joined-surface archives into one final offline model.

Authoritative archive set used:
- producer layer:
  - starter: `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_140546/equip_hold_begin`
  - probe: `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_134746/post_switch`
- joined selector surfaces:
  - starter:
    - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_053026/equip_hold_begin`
    - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_055327/equip_hold_begin`
  - probe:
    - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_041208/idle_begin`
    - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_055327/idle_begin`

Consensus counts:
- starter:
  - `producer_hit_support_count = 2`
  - `joined_surface_support_count = 2`
- probe:
  - `producer_hit_support_count = 1`
  - `joined_surface_support_count = 2`

Canonical model:
- structural wrapper:
  - `owner/source/class_word`
- projection-base family:
  - `class/class_head/+2/+3/+4`
- compact family:
  - `class +5/+6`

Ranked conclusions:
- highest-confidence projection-base hypothesis:
  - selector-root `+3/+4` are best explained as a branch-controlled permutation/materialization of the class-family projection bases
- highest-confidence compact hypothesis:
  - selector-root `+5` is emitted from `class +5`
  - `class +6` contributes mostly structural pre-normalization state that later converges into selector-root `+6`

Most important evidence:
- branch-swap pattern:
  - starter:
    - `class +3 = external_ptr_family`
    - `class +4 = self_plus_0x20`
  - probe:
    - `class +3 = self_plus_0x20`
    - `class +4 = external_ptr_family`
- compact-family interpretation:
  - `class +5` is the strongest branch-shaped compact signal
  - `class +6` is partly structural and converges into shared downstream selector-root `+6 = 0x00000203`

Rejected theory:
- selector-root `+3/+4` are not direct raw copies of `class +3/+4`

Explicit falsification table:
- `class +5` as true compact discriminator is false if a future trustworthy branch capture shows matching `class +5` but differing downstream selector-root `+5`
- `class +6` as mostly structural pre-normalization state is false if downstream selector-root `+6` diverges without corresponding `class +6` normalization drift
- permutation/materialization of `class +3/+4` is false if a future trustworthy branch capture breaks the starter/probe role-swap pattern while downstream selector-root `+3/+4` still materialize normally
- `class/class_head` as upstream projection-family identity is false if downstream selector-root `+3/+4` change while `class/class_head` remain fixed across the same producer family transition

Current blocker after this pass:
- compact-family identification is no longer the blocker
- the strongest remaining ambiguity is now:
  - which exact member of `class/class_head/+3/+4` is the first direct emitter of downstream selector-root `+3/+4` on the write path

Named next live hook:
- `consumer_asset_class_lookup` class-family write path that materializes `class/class_head/+3/+4` into selector-root `+3/+4`

## 59) class_family_materialization_writepath: asset_lookup-only capture + candidate selector roots

Live writepath pass now uses asset_lookup-only arming so producer hits arrive before render-table work.

Successful dedicated producer hits (asset_lookup-only):
- starter-side: `20260403_161557/equip_hold_begin`
  - `consumer_asset_class_lookup` hit observed
  - candidate selector root derived from `asset_lookup_ecx`:
    - `selector_root=0x37E49C34`
    - `+3=0x00000000`, `+4=0x37E4BAEC`, `+5=0x00070101`, `+6=0x00000203`
  - `policy_write_candidate` logged, but no `policy_write_guard_hit` / `policy_write_commit` after watch arming
- probe-side: `20260403_162026/post_switch`
  - `consumer_asset_class_lookup` hit observed
  - candidate selector root derived from `asset_lookup_ecx`:
    - `selector_root=0x313E1B00`
    - `+3=0x00000000`, `+4=0x313E1B20`, `+5=0x01030105`, `+6=0x00000201`
  - `policy_write_candidate` logged, but no `policy_write_guard_hit` / `policy_write_commit` after watch arming

Interpretation:
- selector-root candidates can be recovered directly from producer-side `asset_lookup_ecx` on both branches
- policy write guards never fire after candidate watch arming
- selector-root `+3/+4/+5` values are populated before the asset_lookup breakpoint fires

Updated blocker:
- the missing write provenance is earlier than the current `consumer_asset_class_lookup` hit site
- we need a pre-asset-lookup write hook or a forced re-materialization after watch arming
