# Full Summary

## 89) practical downstream pivot: bounded same-process later-family control did not recover a stable accepted takeover case (2026-04-05)

Authoritative summary:

- `_build/bo3_rev_idg_probe/same_process_trio_transplant_matrix/20260405_152402/same_process_trio_transplant_matrix_summary.json`

What was attempted:

- reused the known-good approved control bucket from the earlier same-process trio lane
- reran only practical downstream cases:
  - `same_process_plus234`
  - `same_process_plus5_only`
  - `same_process_plus234_plus5`

What happened:

- none of the bounded practical-control cases recovered a new accepted same-bucket run
- several attempts still produced render hits or isolated asset-lookup hits
- but none preserved the full old acceptance contract:
  - matching control-family producer shape
  - stable later-family carry-forward
  - joined-surface preservation

Meaning:

- the source-side class-emission lane failed due to bucket drift
- the downstream practical-control pivot also failed to recover a stable accepted takeover case in this bounded batch
- so the current blocker is no longer missing understanding of engine layers
- it is operational stability across the remaining handoff and takeover lanes

Current honest state:

- upstream bridge control is proven
- later-family practical control is proven in older authoritative runs
- but the latest bounded downstream batch did not produce a fresh stable accepted render-takeover case
- visible custom animation is still not working

This document is the long-form project summary for the BO3/T7 -> BO2/T6 weapon, FX, and animation porting effort in this repo. It is intended to answer one question:

What have we actually tried, what worked, what failed, what tooling was built, and where does the project stand right now?

It covers the arc from the earlier Thunder Gun-style donor-shell work, through the Apothicon Servant FX and gameplay work, into the current T7 animation integration effort.

## 1. Project Goal

The long-term goal of this repo is not just to swap models. It is to make BO3/T7-origin content function inside the BO2/T6 runtime with as much fidelity as practical. In the current active lane, that means:

- custom BO3-derived weapon visuals,
- custom BO3-derived FX,
- custom BO3-derived gameplay timing and semantics,
- and eventually custom BO3-derived animations,

all executing inside the live T6 engine.

The project has consistently had to solve four separate problems:

1. getting a weapon identity to exist in T6 at all,
2. getting foreign visuals and FX accepted by T6,
3. getting foreign gameplay semantics to behave correctly in T6,
4. getting foreign animation data selected and actually played by T6.

The first three made real progress. The fourth is still not finished.

## 2. Early Phase: Truth-Alias / Donor-Shell Weapon Work

The earliest important checkpoint still visible in git history is:

- commit `5351119`
- message: `checkpoint: truth alias thundergun path (ak74u override)`

That phase matters because it established the core donor-shell strategy that the later Servant work reused.

### 2.1 What that early phase was about

The engine did not give us an easy path for registering a completely fresh weapon name and having it behave like a first-class stock asset. The workaround was to:

- choose a real stock T6 weapon identity,
- override its data and assets,
- and use that stock identity as the runtime shell.

That is why phrases like "truth alias", "donor shell", and "override path" became central to the project. The engine wanted a stock identity. The project wanted foreign content. The solution was to bind foreign content to a stock identity that the engine would actually accept.

### 2.2 What was learned there

The early Thunder Gun-style lane established several enduring truths:

- Fresh-name registration was not the easy path.
- Stock-identity override was viable.
- Two-phase build/deploy logic was needed to keep runtime outputs and staged assets aligned.
- The right question was not "can the engine see my new asset name?" but "what stock runtime contract will the engine actually accept?"

Those lessons became the backbone of the Servant lane later.

## 3. Transition To the BO3 Rev Apothicon Servant

The active use case eventually became the BO3 Apothicon Servant port under:

- `mods/bo3_rev`

This moved the project from a relatively contained weapon-override problem to a much more complicated combined port:

- model,
- first-person carrier,
- FX,
- gameplay/parity,
- client/server bridge logic,
- and animation.

### 3.1 Why the Servant was harder

The Servant is not just a gun mesh:

- it has distinctive foreign FX,
- it has a foreign projectile/vortex behavior,
- it expects animation content that T6 does not naturally have,
- and it pushes more of the runtime pipeline at once.

That is why the Servant lane forced the creation of much more tooling than the earlier donor-shell work.

## 4. Core Servant Architecture That Was Built

The project converged on this basic architecture:

- keep a stock T6 weapon identity for runtime acceptance,
- replace the viewmodel with a custom Servant shell,
- stage BO3/T7-origin content through a build pipeline,
- and patch or bridge the parts T6 cannot accept directly.

In practice, the important runtime shell became:

- `mg08_zm`

This was not because MG08 was aesthetically correct. It was because it was a workable BO2 Zombies runtime carrier for the first-person weapon path.

### 4.1 Major files in this architecture

The most important files built around the Servant path include:

- [`_build/build_bo3_rev_idg_probe.py`](/z:/Games/pluto_t6_full_game/_build/build_bo3_rev_idg_probe.py)
- [`_build/run_bo3_rev_probe_case.py`](/z:/Games/pluto_t6_full_game/_build/run_bo3_rev_probe_case.py)
- [`_build/compile_xanim_zone.py`](/z:/Games/pluto_t6_full_game/_build/compile_xanim_zone.py)
- [`mods/bo3_rev/scripts/mod_i_am_mod.gsc`](/z:/Games/pluto_t6_full_game/mods/bo3_rev/scripts/mod_i_am_mod.gsc)
- [`mods/bo3_rev/scripts/mod_i_am_mod.gsc.in`](/z:/Games/pluto_t6_full_game/mods/bo3_rev/scripts/mod_i_am_mod.gsc.in)
- [`mods/bo3_rev/clientscripts/mp/zombies/_bo3_rev_servant_fx.csc.in`](/z:/Games/pluto_t6_full_game/mods/bo3_rev/clientscripts/mp/zombies/_bo3_rev_servant_fx.csc.in)
- [`mods/bo3_rev/clientscripts/mp/zombies/_bo3_rev_servant_fx_v3.csc`](/z:/Games/pluto_t6_full_game/mods/bo3_rev/clientscripts/mp/zombies/_bo3_rev_servant_fx_v3.csc)
- [`mods/bo3_rev/ui/t6/mainlobby.lua`](/z:/Games/pluto_t6_full_game/mods/bo3_rev/ui/t6/mainlobby.lua)
- [`native/fx_runtime_probe/fx_runtime_probe_hook.cpp`](/z:/Games/pluto_t6_full_game/native/fx_runtime_probe/fx_runtime_probe_hook.cpp)

## 5. What Was Accomplished On the FX Side

The FX effort was one of the most productive parts of the project. This is where the repo moved from ad hoc asset replacement into a real compatibility pipeline.

### 5.1 FX was not just "ported"

The project discovered that T6 would not simply accept BO3/T7 FX content as-is. It needed:

- material classification,
- technique-set policy,
- image policy,
- runtime-safe fallback choices,
- donor-family substitution,
- and visual debugging.

That resulted in a real custom-effects compatibility layer around OAT, rather than a one-off effect swap.

### 5.2 Important FX findings

The major findings from the Servant vortex work were:

- T6 could load foreign FX assets only after careful translation and normalization.
- Some BO3 materials or images were structurally unacceptable to T6 until massaged into T6-safe forms.
- The vortex issue was not one bug; it was a stack of issues:
  - acceptance,
  - material family mismatch,
  - render contract mismatch,
  - bridge-model behavior,
  - and gameplay-state interaction.

### 5.3 Practical FX successes

The project reached several real successes on the Servant FX lane:

- The full layered vortex stack rendered in-game.
- The visible "nothing happened" path was reduced by replacing the old active vortex instead of blocking new shots.
- The FX bridge was stabilized away from the visible MG08 bridge model and moved to `tag_origin`.
- The visible portal lifetime and layer behavior were tuned much closer to stock BO3 behavior.
- The current remaining FX problem is no longer broad render failure; it is consistency/polish.

### 5.4 FX tooling that was built

The FX work built or expanded:

- family classification in the build pipeline,
- donor-template selection,
- translator output policy,
- image normalization rules,
- layer-isolation build modes,
- FX contract reporting,
- and runtime probe support for render-side debugging.

This is the strongest generally reusable work in the repo outside animation.

## 6. Gameplay / BO3 Parity Work

The project did not stop at visuals. It also pulled the Servant gameplay closer to BO3.

### 6.1 Local T7 source of truth

One major milestone was cloning the real BO3/T7 source locally and using it as a true reference:

- `C:\Users\Ahmed\Downloads\t7-source\scripts\zm\_zm_weap_idgun.gsc`
- `C:\Users\Ahmed\Downloads\t7-source\scripts\shared\ai\zombie_vortex.gsc`
- `C:\Users\Ahmed\Downloads\t7-source\scripts\zm\_zm_weap_idgun.csc`
- `C:\Users\Ahmed\Downloads\t7-source\scripts\shared\ai\zombie_vortex.csc`

That changed the project from "approximate stock behavior" to "port from actual stock scripts where possible."

### 6.2 What was ported or approximated

Work was done on:

- vortex durations,
- visual origin placement,
- pull-vs-effect timing split,
- post-pull explosion window,
- target kill/explosion pass,
- and fallback approximation for BO3-only AI/state logic that T6 did not expose directly.

### 6.3 What remained approximated

Even after that parity work:

- the exact BO3 AI pull/kill path was not fully available in T6,
- the equipment/clientfield system did not map 1:1,
- and sound/visionset/rumble parity was not the main priority while FX and animation were still unstable.

## 7. Probe / Runtime Instrumentation Work

The project spent a large amount of time building runtime probes. Some of that time was productive, and some of it became a loop.

### 7.1 Why the probes were built

The T6 runtime often failed silently or ambiguously. The probes were built to answer:

- what assets were in memory,
- what names were being touched,
- what runtime code path was comparing or resolving those names,
- what sections of xanim data or FX data actually existed in memory,
- and whether stock or custom data was winning.

### 7.2 Important probe files

- [`native/fx_runtime_probe/fx_runtime_probe_hook.cpp`](/z:/Games/pluto_t6_full_game/native/fx_runtime_probe/fx_runtime_probe_hook.cpp)
- [`native/fx_runtime_probe/README.md`](/z:/Games/pluto_t6_full_game/native/fx_runtime_probe/README.md)
- [`native/fx_runtime_probe/active_probe_watchlist.txt`](/z:/Games/pluto_t6_full_game/native/fx_runtime_probe/active_probe_watchlist.txt)
- [`native/fx_runtime_probe/xanim_runtime_expectations.txt`](/z:/Games/pluto_t6_full_game/native/fx_runtime_probe/xanim_runtime_expectations.txt)
- [`native/fx_runtime_probe/xanim_runtime_patches.txt`](/z:/Games/pluto_t6_full_game/native/fx_runtime_probe/xanim_runtime_patches.txt)

### 7.3 What the probe proved

Over time the xanim-focused probe established several important things:

- custom xanim names could be present in memory,
- the live resolver did compare runtime keys,
- the engine was capable of falling back into donor/runtime anim resolution paths,
- stock duplicate paths were real,
- and merely packaging a custom animation was not enough to prove playback.

Later, the probe also evolved into:

- runtime xanim section fingerprinting,
- section patch injection,
- expectation scans,
- and asset-header candidate discovery around watched names.

### 7.4 Limits of the probe work

The probe work was useful, but it also consumed a lot of time without closing the final playback gap. By the end of the recent deep dives, the probe was a strong support tool but not the product. The real unsolved problem remained: getting T7-derived animation data accepted, selected, and actually played.

## 8. Animation Work: What Was Tried

The current hardest problem is animation.

### 8.1 Early animation assumptions that failed

At different points, the project tried or tested:

- fresh custom animation names,
- single-animation overrides on an otherwise stock donor shell,
- static-pose emission,
- partial frame-based emission,
- donor-name backend mapping,
- custom debug anim names like `bo3_rev_dbg_idle`,
- and runtime alias/rewrite approaches.

These attempts proved pieces of the pipeline, but not full end-to-end playback.

### 8.2 The key animation insight

The most important high-level animation lesson was:

- semantic authoring and runtime backend naming are separate concerns.

In other words:

- author in source-semantic terms,
- but emit under the runtime names that T6 actually consumes.

That is why the project moved toward:

- semantic BO3/T7 source clips,
- donor runtime names like `viewmodel_zomb_mg08_idle`,
- and eventually debug asset names such as `bo3_rev_dbg_idle` mapped into the runtime lane.

### 8.3 What the compiler currently does

The current animation tooling can:

- parse or stage BO3/T7-derived xanim exports,
- rebake them,
- map them into runtime staging directories,
- compile T6-side xanim containers,
- and emit debug runtime assets into `mod_load.ff`.

The major files for this are:

- [`_build/compile_xanim_zone.py`](/z:/Games/pluto_t6_full_game/_build/compile_xanim_zone.py)
- [`_build/compare_xanim_contracts.py`](/z:/Games/pluto_t6_full_game/_build/compare_xanim_contracts.py)
- [`tools/asset_port_pipeline/blender_rebake_xanim_worker.py`](/z:/Games/pluto_t6_full_game/tools/asset_port_pipeline/blender_rebake_xanim_worker.py)

### 8.4 What the compiler does not yet do correctly

The animation compiler is still not complete in the sense required for final success.

Problems discovered along the way included:

- hybrid or invalid contracts,
- donor-shaped payloads with mismatched semantic names,
- runtime acceptance without actual playback,
- likely mismatch between expected T6 channel layout and the emitted foreign data,
- and cases where assets were built and staged but the live runtime still behaved like stock.

At one point the project also discovered that simply swapping names on a donor payload was unsafe because the channel sections are positional relative to the names/category contract.

That is a crucial finding:

- you cannot just take a stock donor animation payload and overlay a foreign name table on top of it.

The name order, channel layout, and dependent data sections must remain coherent as one runtime contract.

## 9. Recent Deep Dives: What They Actually Found

The recent deep dives were mostly about narrowing why custom animation playback still was not happening.

### 9.1 Runtime startup / match-start problem

One major blocker was not the animation asset itself, but losing the ability to reliably get into a live zombies match offline.

Important findings from that line of work:

- The project had definitely reached in-map `InitGame` successfully before.
- Historical `games_mp.log` entries prove real match start, weapon grant, and animation probes.
- The launch path that used to work was relatively plain:
  - normal offline launcher,
  - mod enabled,
  - and `ExecCfg ffprobe_autorun.cfg`.
- The problem was not a missing secret command-line argument.
- Later regressions came from UI/raw overrides drifting and startup automation moving into the wrong layers.

### 9.2 Main menu vs main lobby confusion

The deep dive established that different automation was happening at different layers:

- top-level main menu,
- zombies main menu,
- main lobby,
- and local/private lobby.

One of the mistakes in the recent stuck loop was pushing automation too far down into later UI layers after earlier menu behavior had already drifted.

This is why the repo now contains:

- a patched [`mods/bo3_rev/ui/t6/mainlobby.lua`](/z:/Games/pluto_t6_full_game/mods/bo3_rev/ui/t6/mainlobby.lua)
- and a restored earlier hook in [`mods/bo3_rev/ui_mp/t6/mainmenu.lua`](/z:/Games/pluto_t6_full_game/mods/bo3_rev/ui_mp/t6/mainmenu.lua)

The main point is:

- the project has repeatedly had a real route into the map,
- but that route has been flaky and sensitive to where the automation is injected.

### 9.3 Debug animation build

The later animation deep dives produced a real debug build:

- build tag `0401170107_8eeccc`

In that build report:

- `idleAnim = bo3_rev_dbg_idle`
- `fireAnim = bo3_rev_dbg_fire`
- `firstRaiseAnim = bo3_rev_dbg_first_raise`
- `sprintInAnim = viewmodel_zomb_mg08_sprint_in`

That is important because it means the staging/build layer is no longer limited to stock MG08 names. The debug lane can now emit obviously distinct runtime animation assets.

### 9.4 Probe expectations and runtime patch data

The runtime probe now carries explicit expectations for debug animation assets, for example:

- `bo3_rev_dbg_idle`
- `bo3_rev_dbg_first_raise`
- `bo3_rev_dbg_fire`
- `bo3_rev_dbg_pullout`

and it also has patch-manifest support for runtime xanim sections.

That is valuable because it means the toolchain is no longer blind. It can now:

- identify section hashes,
- locate runtime headers,
- and compare expected custom sections against what the live process actually exposes.

### 9.5 What the recent deep dives did not prove

Even with all that instrumentation, the project still does not yet have complete proof that:

- the live T6 runtime is selecting the custom T7-derived debug animation as the winner,
- and then actually using its data for playback.

That is the current gap.

## 10. Current State of FX vs Animation

These two areas are in very different states.

### 10.1 FX state

The Servant FX lane is in a mature-but-not-perfect state:

- the layered vortex renders,
- the bridge works,
- the old silent no-op shot case was addressed,
- and the remaining work is polish/parity, not gross existence.

### 10.2 Animation state

The animation lane is not yet complete:

- the build pipeline can emit staged custom assets,
- the probe can watch for them,
- and the repo now has custom debug animation names and expectations,
- but end-to-end proof of live playback is still missing.

This means animation is the current highest-risk subsystem.

## 11. What the Repo Proves Today

At the time this summary was written, the repo proves all of the following:

- A donor-shell strategy works in T6.
- The BO3 Servant viewmodel can be loaded without the old giant-rig crash.
- The Servant FX stack can render in the live T6 runtime.
- BO3 gameplay parity work can be guided by the real local T7 scripts.
- The build pipeline can stage BO3/T7-derived animation assets into T6 fastfiles.
- The runtime probe can inspect xanim names, headers, sections, and selected runtime structures.
- Historical logs prove that the mod can reach live `InitGame`, grant the carrier weapon, and log animation probes in-map.

## 12. What Is Still Not Proven

The following is still not proven end-to-end:

- that a T7-derived animation asset is the live winner in the T6 runtime,
- that the runtime accepts its translated data as the playback source,
- and that the weapon pose/motion on screen is being driven by that custom T7-derived data rather than stock T6 content or ordinary sway.

That is the single biggest unfinished piece.

## 13. Major Checkpoints and Their Meaning

### 13.1 `5351119`

- `checkpoint: truth alias thundergun path (ak74u override)`

Meaning:

- early donor-shell truth-alias path was established,
- stock runtime identity override was proven as the practical approach.

### 13.2 `3592dda`

- `checkpoint: servant fx and bo3 parity state 0321232501_4c7e1d`

Meaning:

- the Servant lane became a real documented pipeline,
- FX and parity work were serious enough to checkpoint as a stable state.

### 13.3 `3faa921`

- `Skip mod_load carrier during runtime xanim link`

Meaning:

- animation work had become deep enough that the exact carrier FF path (`mod_load`, runtime link lane, section ownership) needed explicit policy control.

## 14. Practical Lessons Learned

The project has learned several durable lessons:

1. T6 accepts stock contracts more readily than foreign names or fresh registrations.
2. Rendering problems, gameplay problems, and animation problems are separate layers and must be treated separately.
3. BO3/T7-origin content can often be made to work, but only after identifying the real runtime contract T6 expects.
4. Building a compatibility pipeline around OAT was necessary; OAT by itself was not enough for the Servant use case.
5. Animation is harder than models or FX because it requires structural coherence between:
   - names,
   - channels,
   - bone groups,
   - deltas,
   - header flags,
   - and the runtime’s actual selection/playback assumptions.

## 15. Current Best Restart Point

If someone had to resume from here, the important facts are:

- The active lane is `mods/bo3_rev`.
- The current debug animation build recorded in the latest build report is:
  - `0402041237_8eeccc`
- The current debug animation intent is visible in:
  - [`_build/bo3_rev_idg_probe/build_report.json`](/z:/Games/pluto_t6_full_game/_build/bo3_rev_idg_probe/build_report.json)
- The current runtime probe watchlist and expectations are in:
  - [`native/fx_runtime_probe/active_probe_watchlist.txt`](/z:/Games/pluto_t6_full_game/native/fx_runtime_probe/active_probe_watchlist.txt)
  - [`native/fx_runtime_probe/xanim_runtime_expectations.txt`](/z:/Games/pluto_t6_full_game/native/fx_runtime_probe/xanim_runtime_expectations.txt)
- The current UI automation files that were touched during the recent launch deep dives are:
  - [`mods/bo3_rev/ui/t6/mainlobby.lua`](/z:/Games/pluto_t6_full_game/mods/bo3_rev/ui/t6/mainlobby.lua)
  - [`mods/bo3_rev/ui_mp/t6/mainmenu.lua`](/z:/Games/pluto_t6_full_game/mods/bo3_rev/ui_mp/t6/mainmenu.lua)

## 16. Current Bottom Line

The project is not starting from nothing.

The donor-shell model works.
The Servant model path works.
The Servant FX path works well enough to be considered real.
The gameplay/parity path is grounded in real T7 source.
The animation pipeline has moved beyond pure theory and now has:

- staged custom assets,
- debug runtime names,
- contract comparison tooling,
- runtime expectation files,
- and live runtime inspection support.

But the central unfinished problem remains:

- end-to-end proof that T7-derived animation data is the thing the live T6 engine is actually selecting and playing.

That is the current frontier.

## 17. April 1, 2026 Reset: What Was Wrong About Startup

One of the recent stuck loops was self-inflicted:

- too much emphasis moved into wrapper/UI startup semantics,
- and not enough emphasis stayed on the simplest proven path:
  - launch the game directly with the correct command-line state.

The repo already had the correct primitive in:

- [`tools/launch_t6_offline.ps1`](/z:/Games/pluto_t6_full_game/tools/launch_t6_offline.ps1)

The important working command-line contract is now:

- `fs_game=mods/bo3_rev`
- `+map zm_transit`
- `ui_mapname=zm_transit`
- `ui_gametype=zclassic`
- `ui_zm_gamemodegroup=zsurvival`
- `ui_zm_mapstartlocation=town`
- `g_gametype=zclassic`

That direct launch path is what finally restored:

- command line -> map load

without needing later menu-state automation to be correct first.

### 17.1 Why the UI-wrapper path kept going wrong

The wrapper/UI path was not failing because a secret launch argument was missing. It was failing because too many startup semantics were being changed after launch:

- `ffprobe_autorun.cfg`
- menu/lobby layer automation
- client-side script overrides
- and gametype coercion inside loose/generated clientscripts

Those layers were able to drift the client into a different startup contract than the server.

The direct `launch_t6_offline.ps1` path works better because it declares the real target state at launch and avoids relying on later UI state transitions to repair it.

### 17.2 First mismatch that was fixed

The first concrete mismatch was:

- client-side `_zm.csc` was rewriting the transit survival lane into the wrong gametype path for `town`

That caused the client to register a different world-clientfield set than the server, including wallbuy fields at the wrong coordinates.

That specific issue was fixed by removing the client-side gametype rewrite in:

- [`mods/bo3_rev/clientscripts/mp/zombies/_zm.csc`](/z:/Games/pluto_t6_full_game/mods/bo3_rev/clientscripts/mp/zombies/_zm.csc)

### 17.3 What the current mismatch became after that

Once the first mismatch was fixed, the error changed. That was a useful sign.

The current remaining mismatch is no longer the old town-vs-transit wallbuy set. It is a transit-script mismatch where the client was still registering transit-only fields on the `town` start lane:

- `the_bus_spawned`
- `bus_flashing_lights`
- `bus_head_lights`
- `bus_brake_lights`
- `bus_turn_signal_left`
- `bus_turn_signal_right`
- `screecher_sq_lights`
- `screecher_maxis_lights`
- `sq_tower_sparks`
- `power_rumble`

Those fields were being registered by the generated transit clientscript under:

- [`_build/bo3_rev_idg_probe/clientscripts/mp/zm_transit.csc`](/z:/Games/pluto_t6_full_game/_build/bo3_rev_idg_probe/clientscripts/mp/zm_transit.csc)

The two concrete problems found there were:

1. it was still forcing `ui_gametype`/default survival behavior in the client layer instead of preserving the direct launch state,
2. it was registering transit-only bus/tower clientfields for every `zclassic` run, instead of only the real `transit` start location.

The local generated-script fix is now:

- preserve the incoming `ui_gametype` for the transit survival client path,
- and only register transit-only bus/tower clientfields when `ui_zm_mapstartlocation == "transit"`.

That is the current practical fix path for the `town` lane.

### 17.4 Current handmodel / "mitts mats" status

At the moment, the animation debug lane is still using the reduced first-person lane:

- `force_low_handmodel = true`
- `gunModel = bo3_rev_v2_idg_view_<build_tag>`
- `handModel = bo3_rev_bridge_viewhands`

This is visible in:

- [`_build/bo3_rev_idg_probe/build_report.json`](/z:/Games/pluto_t6_full_game/_build/bo3_rev_idg_probe/build_report.json)

The bridge viewhands asset is staged in the zone and is now the active staged `handModel`:

- `bo3_rev_bridge_viewhands`

So the build-side contract is no longer "blank hands". The current unresolved question is runtime acceptance:

- whether the live first-person DObj actually assembles with `bo3_rev_v2_idg_view_<build_tag>` plus `bo3_rev_bridge_viewhands`,
- or whether T6 silently falls back, drops the gun model, or rejects part of the composition before visible playback.

That is why the probe had to be deepened from plain xanim-name watching into xmodel-name watching and live reference mapping. The latest probe direction is:

- watch both `xanim=` and `xmodel=` targets,
- prioritize pass-1 xmodel census before heavy xanim full scans,
- log immediate near-address reference neighborhoods for watched xmodel names,
- and dump pointer neighborhoods around each watched xmodel ref so the runtime slot selection can be reverse-mapped.

So the safest current statement is:

- the hand/mitten material lane is not the current launch blocker,
- the build is now pointing at bridge viewhands on purpose,
- and the blocker has moved to proving what the runtime actually assembled from those weapon fields.

### 17.5 April 1, 2026 probe timing correction

The next important correction was probe timing.

Injecting the deep `xanim_focus` probe during early bootstrap looked like "the game crashes", but the real behavior was:

- normal direct launch without probe reaches `so_zsurvival_zm_transit`,
- the mod reaches `[bo3_rev][start]`,
- the local player reaches `[connect]`,
- the carrier weapon is granted,
- and the GSC animation probes run in-map.

The failure path was early probe injection, not the map/mod lane itself.

The practical working order is now:

1. launch normally with the direct `launch_t6_offline.ps1` command,
2. wait until the game is already in-map,
3. inject the latest probe,
4. then inspect runtime xmodel/xanim state.

That avoids reintroducing the old startup loop and keeps the probe focused on the real problem: runtime animation/model acceptance after the weapon is already live.

### 17.6 Current live evidence after the launch fix

The current live lane is no longer hypothetical. Recent `console_zm.log` runs on build `0402041237_8eeccc` show:

- `[bo3_rev][start]` on `zm_transit`,
- client connect,
- `mg08_zm` grant,
- `idleAnim=vm_zod_id_gun_idle`,
- `firstRaiseAnim=vm_zod_id_gun_first_raise`,
- `fireAnim=vm_zod_id_gun_fire`,
- and full GSC probe output for `first_raise`, `pullout`, and `idle`.

The most important animation-side observations from that live run are:

- `first_raise` shows real positional deltas at first,
- later `first_raise` and `pullout` samples flatten or stall,
- `idle` stays effectively static,
- many BO3-specific animated tags remain `<undef>`,
- and the reported runtime first-person hand viewmodel is still stock survivor hands like `c_zom_farmgirl_viewhands`, not a proven custom bridge-hands runtime winner.

That means the current blocker is no longer "can we get in-map and grant the weapon?" It is:

- which xmodel composition actually won at runtime,
- which xanim headers/sections the runtime is really touching,
- and why the expected BO3-derived motion is not becoming the persistent live winner.

## 18. Current Immediate Priorities

The immediate order is now much clearer:

1. keep using the direct launch path, not the wrapper-first UI path,
2. do probe injection after normal in-map launch, not during bootstrap,
3. keep the `town` survival baseline on `zm_transit`,
4. use the deeper probe to prove live gunModel/handModel/xanim selection on that lane,
5. then use those live results to finish the animation acceptance fix.

## 19. April 2, 2026 current animation/model baseline

The current minimal Servant animation lane has now been corrected in two important build-side ways:

- the staged gun model source is no longer the old 89-bone reduced shell by default,
- the semantic-name BO3 xanim compile path is no longer forced through the old `weapon_only_rig_report.json` keep-bones file when the full source GLB is active.

Current build baseline from `build_report.json`:

- `build_tag = 0402060413_a9fbb2`
- `source_model = _build/asset_port_pipeline/tmp/idg_view.glb`
- `gunModel = bo3_rev_v2_idg_view_0402060413_a9fbb2`
- `handModel = viewmodel_usa_no_model`

This matters because the previous lane was silently mixing:

- a full source GLB on the model side,
- but a still-reduced 89-bone xanim contract on the animation side.

That mismatch preserved the exact failure pattern we were seeing:

- BO3-specific animated tags still showed up as `<undef>` in GSC probes,
- `pullout` and `fire` continued to flatten on `tag_weapon`,
- and the visible shell could still look wrong even though startup and weapon grant were already fixed.

The current compile output now proves the full animation contract is being emitted:

- `vm_zod_id_gun_fire.xanim_export: 141 bones`
- `vm_zod_id_gun_first_raise.xanim_export: 141 bones`
- `vm_zod_id_gun_idle.xanim_export: 141 bones`
- `vm_zod_id_gun_pullout.xanim_export: 141 bones`

So the current offline baseline is:

- normal direct launch is still the correct way into map,
- the active custom gun shell is now sourced from the full IDG view GLB,
- and the BO3 semantic animation lane is now compiled against the full 141-bone contract instead of the cut-down 89-bone contract.

That is the right baseline for the next visual/manual check, because it removes the two biggest hidden reductions that were still contaminating the animation debugging lane.

## 20. April 2, 2026 runtime contract after the bridge + fit pass

The next correction pass changed the live first-person contract in three important ways:

- the full-source custom gun now gets the old fit normalization back as a root scale of `0.72`,
- the debug weapon no longer stages `handModel=viewmodel_usa_no_model`,
- the weapondef now stages `handModel=bo3_rev_bridge_viewhands`.

Current build baseline from `build_report.json`:

- `build_tag = 0402063315_a9fbb2`
- `gunModel = bo3_rev_v2_idg_view_0402063315_a9fbb2`
- `handModel = bo3_rev_bridge_viewhands`
- `stub_zm_viewhands = false`
- `force_low_handmodel = true`

The staged custom gun GLB for that build now preserves the semantic BO3 animated tags again while also carrying the corrected fit scale:

- root scene node scale is `0.72, 0.72, 0.72`
- `tag_weapon` exists
- `tag_flash` exists
- `tag_brass` exists
- `tag_eye_left_big_lid_animate` exists
- `tag_jaw_lower_2_animate` exists
- `tag_tentacle_bottom_left_4_animate` exists

This removed the previous build-side contamination where the model lane itself was wrong. The remaining failure is now clearly runtime-side.

### 20.1 What the short live check proved

A short direct launch plus post-load probe inject on build `0402063315_a9fbb2` produced these important facts in `console_zm.log`:

- startup and grant are still good,
- `mg08_zm` is granted and switched correctly,
- `first_raise` still shows motion on `tag_flash`, `tag_weapon`, `tag_brass`, and `tag_clip`,
- `pullout` and `idle` still flatten,
- BO3-specific animated tags still remain `<undef>` at runtime,
- and the active runtime VM is still stock survivor hands (`c_zom_oldman_viewhands` in the sampled run).

Most importantly, the bridge shell is still being rejected at runtime:

- `stage=pre_grant_rejected ... target=bo3_rev_bridge_viewhands`
- repeated `stage=set_rejected ... target=bo3_rev_bridge_viewhands`
- after 5 failures the script disables forced viewmodel swapping

That means the current blocker is no longer startup, build staging, or the hidden reduced-rig path. The blocker is:

- T6 is refusing `setviewmodel("bo3_rev_bridge_viewhands")`,
- the live first-person shell remains the stock zombie hands model,
- and the BO3 gun model is still being observed through the stock VM attachment path rather than as an accepted custom first-person shell.

### 20.2 What this means for animation debugging

Right now the runtime is split into two layers:

- stock zombie viewhands provide the accepted camera/viewmodel shell,
- the custom Servant gun model exists and moves enough for `first_raise` to be visible,
- but the live tag queries for BO3-specific animated bones do not resolve through that accepted shell.

So the next animation-side debugging target is no longer “can the BO3 gun compile” or “can the map launch.”
It is:

- why `bo3_rev_bridge_viewhands` is rejected by `setviewmodel`,
- whether the accepted first-person DObj can expose attached-model semantic tags at all,
- and whether we need a stock-shell-compatible bridge model rather than a separate bridge viewmodel asset.

## 21. April 2, 2026 xmodel memory-focus pass

This pass stayed on the native memory path. The direct offline launcher remained the baseline; the new work was all probe-side.

### 21.1 Probe changes

- `xanim_focus` asset census now starts early enough to run during short offline passes.
- The probe now performs immediate live scans when watched `xmodel` or `xanim` names are touched at runtime.
- The xmodel path no longer stops at the `touch_near_only` shortcut. It now does the full string/ref search for watched xmodels.
- The active xmodel watchlist was narrowed for animation debugging:
  - `bo3_rev_v2_idg_view_0402063315_a9fbb2`
  - `bo3_rev_bridge_viewhands`
  - `c_zom_oldman_viewhands`
  - `viewmodel_usa_no_model`

### 21.2 What the memory evidence now proves

The current live runtime still keeps stock hands as the accepted first-person shell:

- gameplay logs still show `vm=c_zom_oldman_viewhands`
- `setviewmodel("bo3_rev_bridge_viewhands")` is still rejected repeatedly before the force path disables itself

The probe now proves the relevant xmodel names are live and touched in the same runtime:

- `bo3_rev_v2_idg_view_0402063315_a9fbb2`
- `bo3_rev_bridge_viewhands`
- `c_zom_oldman_viewhands`
- `viewmodel_usa_no_model`

For the custom gun xmodel specifically, the probe now sees the name in multiple live memory families:

- executable image string storage around `0x0118DA5B/0x0118DA5C`
- loaded/copy storage around `0x02C51544/0x02C51574`
- later private copies such as `0x2FC420A8` and `0x453D0A64`

That means the custom gun xmodel name is not missing. It is loaded, copied, and touched in live runtime.

### 21.3 What is still missing

The xmodel side still is not yielding a clean pointer-style `XModel` object from plain name scans:

- the probe is finding string copies,
- but it is not yet finding `rawRefs > 0` or a stable xmodel candidate/header structure around those names,
- which suggests the active xmodel consumer path is not exposing a simple name-pointer field the way the xanim side exposes `XAnimParts`-style structures.

Current interpretation:

- the animation failure is still downstream of first-person shell acceptance,
- the stock zombie hands shell is the accepted runtime winner,
- the custom gun xmodel is present in memory,
- but the model-side runtime contract still looks indirect: copied-string, hash/index, descriptor, or DObj/model-array driven rather than a simple pointer-to-name struct we can grab by scanning around the string alone.

## 22. April 2, 2026 server + client + memory alignment pass

This pass corrected the stale live-script problem, then ran a full direct offline cycle against the AppData mod mirror:

- direct `launch_t6_offline.ps1`
- in-map server-side `anim_probe` logging
- new client-side `_zm.csc` local animation watcher
- late `xanim_focus` probe injection
- shutdown after capture

### 22.1 Important implementation changes

- `mods/bo3_rev/clientscripts/mp/zombies/_zm.csc` now starts a local animation watcher on player spawn.
- That watcher logs `[bo3_rev][csc_anim]` samples for:
  - local player model
  - `tag_flash`
  - `tag_weapon`
  - `tag_brass`
  - `tag_clip`
  - `tag_gasmask`
  - `tag_eye_left_big_lid_animate`
  - `tag_jaw_lower_2_animate`
  - `tag_tentacle_bottom_left_4_animate`
- The attempted server-to-client pulse path through `setclientfield` in `mod_i_am_mod.gsc` was removed. In this script context it hard-fails compile with:
  - `Unresolved external : "setclientfield" with 2 parameters`
- The live mod path was confirmed to be the AppData mirror under:
  - `C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\mods\bo3_rev`
- The active memory watchlist now includes all four survivor hand shells:
  - `c_zom_farmgirl_viewhands`
  - `c_zom_oldman_viewhands`
  - `c_zom_engineer_viewhands`
  - `c_zom_reporter_viewhands`

### 22.2 What the aligned evidence proves

The live runtime shell is still stock survivor hands, and the exact shell can vary by survivor:

- this aligned run used `vm=c_zom_farmgirl_viewhands`
- earlier runs used `c_zom_oldman_viewhands` and `c_zom_engineer_viewhands`
- `bo3_rev_bridge_viewhands` is still rejected by `setviewmodel(...)`

So the blocker is broader than a single donor shell. The engine is choosing one of the stock survivor viewhands models at runtime and refusing the custom bridge shell entirely.

The new client-side watcher proves the client is also seeing a stock-player shell, not a custom first-person shell:

- client model resolves to `c_zom_player_farmgirl_fb`
- client `tag_weapon` stays flat at `(0, 0, 0)`
- client BO3-specific animated tags remain `<undef>`
- client `tag_flash` / `tag_brass` alternate between two stable stock states instead of exposing a richer custom rig

That means the visible local shell is not just failing server-side queries; it is also failing client-side to expose the custom BO3 semantic tag surface.

The server-side `anim_probe` remains consistent with that:

- `first_raise` produces movement
- `pullout` is mostly just `tag_flash` displacement
- `idle` stays flat
- BO3 semantic tags stay `<undef>`

### 22.3 What the memory probe adds

The probe still shows the custom assets are present in runtime memory:

- `bo3_rev_v2_idg_view_0402063315_a9fbb2`
- `bo3_rev_bridge_viewhands`
- `vm_zod_id_gun_idle`
- `vm_zod_id_gun_first_raise`
- `vm_zod_id_gun_fire`
- `vm_zod_id_gun_pullout`

But the consumer-side evidence is now more specific:

- resolver-time stack strings show `c_zom_farmgirl_viewhands`
- the watched string block also contains adjacent stock hand names like `c_zom_oldman_viewhands` and `c_zom_engineer_viewhands`
- the custom gun/viewhands names are present as copied strings
- the xanim fast scans still report `rawRefs=0` and `candidates=0` for the BO3 runtime anim names

So the current failure split is:

- custom xmodel/xanim names are loaded into memory
- stock survivor viewhands are the accepted runtime shell
- the active local shell exposes only the stock tag surface
- the BO3 runtime anim names still are not surfacing as a simple live `XAnimParts` candidate/header through the current scan path

### 22.4 Current blocker after this pass

The next real debugging target is the accepted first-person contract itself:

- why stock survivor hand shells are always selected over `bo3_rev_bridge_viewhands`
- how the accepted survivor shell composes its attached weapon model and tags
- whether the custom gun has to be rebased onto a stock survivor hand/viewmodel contract rather than replacing the hand shell

At this point the repo has all three evidence layers running together:

- server-side animation probes
- client-side local tag/model probes
- memory-level xmodel/xanim presence scans

## 23. April 2, 2026 target-backend donor-order unification pass

This pass was the first build-side correction that fully aligned the active animation family to the accepted T6 backend contract instead of mixing donor-order and semantic staging.

### 23.1 What changed

The stock-survivor carrier lane was kept, but the animation source/backend path was corrected:

- source model now stays on the reduced weapon-only IDG GLB for the stock-carrier lane
- runtime backend stays on real MG08 backend names
- runtime oracle search now includes:
  - `mod_load.ff`
  - generated output `mod_load.ff`
  - `mod_patch.ff`
  - survival runtime FF
  - survival baseline FF
  - `zm_prison.ff`
- backend names now have explicit donor fallbacks:
  - `viewmodel_zomb_mg08_idle -> viewmodel_minigun_t6_idle`
  - `viewmodel_zomb_mg08_fire -> viewmodel_minigun_t6_fire`
  - `viewmodel_zomb_mg08_ads_fire -> viewmodel_minigun_t6_fire`
  - `viewmodel_zomb_mg08_pullout -> viewmodel_minigun_t6_pullout`
  - `viewmodel_zomb_mg08_pullout_quick -> viewmodel_minigun_t6_pullout_quick`
  - `viewmodel_zomb_mg08_first_raise -> viewmodel_minigun_t6_pullout`
  - `viewmodel_zomb_mg08_putaway -> viewmodel_minigun_t6_putaway`
- `patch_mod_load_ff_xanim_backend_sections()` now takes its live BO3-frame patch source from:
  - `mod_load_runtime_patchsrc.ff`
  instead of incorrectly trying to read those runtime-named assets out of `so_zsurvival_zm_transit.ff`

### 23.2 What this fixed

Before this pass, the active target-backend runtime map was still mixed:

- `idle` could donor-stage cleanly
- `fire`, `pullout`, and `first_raise` were still falling back to `semantic_runtime_name`

After this pass, the entire active family stages as donor-order runtime exports under real backend names. The current `xanim_runtime_map.json` now shows:

- `viewmodel_zomb_mg08_idle`
- `viewmodel_zomb_mg08_first_raise`
- `viewmodel_zomb_mg08_fire`
- `viewmodel_zomb_mg08_ads_fire`
- `viewmodel_zomb_mg08_pullout`
- `viewmodel_zomb_mg08_pullout_quick`

all with:

- `staging_mode = donor_order_export`
- `donor_ff = zm_prison.ff`
- donor minigun runtime assets
- `donor_name_count = 82`
- `output_name_count = 82`

This is the first time the full active family has been on one coherent 82-bone donor-order contract instead of a hybrid contract.

### 23.3 What the build now proves

Current successful build:

- `build_tag = 0402090218_75d444`

Important verified outputs:

- the rebaked/staged backend-name exports are all 82 bones
- `mod_load.ff` is now patched from `mod_load_runtime_patchsrc.ff`
- verification after patch shows:
  - `viewmodel_zomb_mg08_ads_fire: numframes=24, bDelta=1, bDelta3D=1, bones=82`
  - `viewmodel_zomb_mg08_fire: numframes=24, bDelta=1, bDelta3D=1, bones=82`
  - `viewmodel_zomb_mg08_first_raise: numframes=56, bDelta=1, bDelta3D=1, bones=82`
  - `viewmodel_zomb_mg08_idle: numframes=171, bDelta=1, bDelta3D=1, bones=82`
  - `viewmodel_zomb_mg08_pullout: numframes=29, bDelta=1, bDelta3D=1, bones=82`
  - `viewmodel_zomb_mg08_pullout_quick: numframes=29, bDelta=1, bDelta3D=1, bones=82`

This means the live animation family is no longer being authored as a semantic-name contract and then loosely aliased at runtime. It is being emitted directly in the backend-name shape the accepted T6 weapon shell expects.

### 23.4 What is still unresolved

There is a new launch regression on this exact build that appears before any `[bo3_rev][start]` script logging:

- direct launch returns to desktop / exits early
- no explicit `EXE_CLIENT_FIELD_MISMATCH` or fastfile-load error is written in the active mod console log
- no Windows crash report was recorded for the game executable during that launch window

Important interpretation:

- the meaningful animation-side progress in this pass is real and should not be discarded
- the current blocker is now split:
  - build-side animation contract alignment improved substantially
  - this exact deployed build still needs a separate early-launch validation pass before in-map motion can be judged

So the repo state after this pass is:

- animation backend naming is in a much better place
- donor-order contract alignment is much better than before
- the current live build still needs one more stabilization step before the new in-game motion behavior can be measured cleanly

The problem is no longer “we cannot observe it.” The problem is that every layer now points to the same runtime winner: stock survivor viewhands, not the custom BO3 bridge shell.
## 24. April 2, 2026 crash root cause and stable ownership fix

The early-exit regression was isolated to the late `mod_load.ff` full-asset xanim patch path, not to the donor-order runtime export lane itself.

### 24.1 What the bisect proved

- `PATCH_RUNTIME_BACKEND_FF=1` with `patch_mod_load_ff_xanim_backend_sections()` active caused the game to exit before any `[bo3_rev][start]` marker.
- `PATCH_RUNTIME_BACKEND_FF=0` on the same donor-order MG08 runtime-name lane produced a stable launch, reached map load, granted `mg08_zm`, and ran the server/client animation probes.
- On the stable build, probe memory still showed the expected runtime assets in memory:
  - `viewmodel_zomb_mg08_idle`
  - `viewmodel_zomb_mg08_first_raise`
  - `viewmodel_zomb_mg08_fire`
  - `viewmodel_zomb_mg08_pullout`
  - `bo3_rev_v2_idg_view_<build_tag>`

### 24.2 Why the crash happened

- `mod_load.ff` is intentionally compiled as a safe donor-template seed when the lane uses `bo3_frames`.
- `mod_load_runtime_patchsrc.ff` carries the real animated payload for patch/probe work.
- The crashing path was trying to resize and replace the tiny safe-seed xanim assets inside `mod_load.ff` after link with the real animated payload.
- That mutation is not required once the survival runtime FF already owns the backend-name assets directly.

### 24.3 Stable fix now implemented

- the minimal runtime build now defaults `PatchRuntimeBackendFF` to `false`
- even if runtime backend patching is enabled for experiments, the build script now skips the dangerous `mod_load.ff` full-asset patch on the target-runtime-name lane when the survival FF can own the assets directly
- `mod_load.ff` remains a legal seed/probe carrier instead of a mutated animation owner

### 24.4 Current meaning after the fix

- the launch crash was a build ownership and stability bug
- the actual animation bug remains separate:
  - runtime/backend anim names are loaded in memory
  - stock survivor first-person shell is still the accepted runtime shell
  - server/client tag motion still shows only partial movement on the stock tag surface

## 25. April 2, 2026 runtime-name-only xanim lane

This pass removed one major source of ambiguity in the active animation lane: the build was still emitting runtime backend names and then copying those same exports back out under the original BO3 semantic names.

That meant the shipped FFs still contained live `vm_zod_id_gun_*` resolver targets even when the weapon fields were pointed at `viewmodel_zomb_mg08_*`.

### 25.1 What was changed

- added an explicit build gate:
  - `ROGUE_EMIT_SHADOW_SEMANTIC_EXPORTS`
- defaulted that gate off in the minimal runtime build lane
- when the gate is off:
  - `stage_runtime_xanim_exports()` no longer writes `shadow_semantic_export`
  - the probe watchlist no longer seeds `vm_zod_id_gun_*`
  - probe expectations no longer treat semantic shadow assets as first-class candidates in the target-runtime-name lane

Files changed:

- `_build/build_bo3_rev_idg_probe.py`
- `tools/build_servant_minimal_anim_runtime.ps1`

### 25.2 What the narrow validation proved

A narrow idle-only build completed successfully with:

- `build_tag = 0402154244_75d444`
- `ROGUE_BO3_ANIM_SUBSET = vm_zod_id_gun_idle`
- `ROGUE_EMIT_SHADOW_SEMANTIC_EXPORTS = 0`

On that build:

- runtime staging now contains only:
  - `viewmodel_zomb_mg08_idle.xanim_export`
- `active_probe_watchlist.txt` now contains:
  - `viewmodel_zomb_mg08_idle`
  - donor fallback names like `viewmodel_minigun_t6_idle`
  - no `vm_zod_id_gun_*` semantic xanim entries

This is the first clean target-runtime-name build where the semantic BO3 names are no longer being shipped as parallel xanim resolver targets by default.

### 25.3 What this means

Current blocker is now narrower and easier to reason about:

- if the engine still does not visibly play the intended motion on this lane, it is no longer because our own runtime package is advertising the BO3 semantic names as parallel live assets
- the remaining failure is now in one of these buckets:
  - the engine is not touching the target runtime-name asset family at all
  - the engine is touching the target family but the live header/section winner still resolves to donor-like data
  - the stock survivor viewhands shell plus reduced custom gun contract still does not expose the expected animated tag surface

### 25.4 Current evidence after the change

- build-side runtime staging is clean and runtime-name-only
- the probe now loads a runtime-name-only watchlist
- the live gameplay lane still uses stock survivor viewhands
- server-side motion logs still show:
  - partial first-raise movement
  - pullout mostly on flash-space only
  - idle flat on the important tags
  - BO3 semantic tags undefined

So this pass did not solve visible animation playback yet, but it removed one false branch in the debugging tree: the build is no longer giving the engine an easy semantic-shadow fallback path in the default target-runtime-name lane.

## 26. April 2, 2026 idle resolver matrix and consumer-side probe

This pass finally answered the next real decision point.

The repo now has a strict idle-only resolver matrix and a deterministic stock-shell lane:

- build script: `tools/run_idle_resolver_matrix.ps1`
- fixed shell target for these runs: `c_zom_engineer_viewhands`
- stable lane:
  - stock survivor carrier on
  - target runtime names on
  - donor-order staging on
  - shadow semantic exports off
  - alias binding off
  - `PATCH_RUNTIME_BACKEND_FF=0`

### 26.1 What the matrix built

Three idle-only builds were run on the same map, same launch path, same shell forcing, and same weapon grant:

- `A_stock_donor`
  - `emit_mode=donor_clone`
  - `build_tag=0402213433_75d444`
- `B_donor_tiny_edit`
  - `emit_mode=donor_template_static_pose`
  - `idle_static_bone=tag_weapon`
  - `idle_static_translate=18,0,0`
  - `build_tag=0402215129_75d444`
- `C_bo3_rebake`
  - `emit_mode=bo3_frames`
  - `build_tag=0402215809_75d444`

Archives:

- `_build/bo3_rev_idg_probe/idle_resolver_matrix/20260402_153427/A_stock_donor`
- `_build/bo3_rev_idg_probe/idle_resolver_matrix/20260402_153427/B_donor_tiny_edit`
- `_build/bo3_rev_idg_probe/idle_resolver_matrix/20260402_153427/C_bo3_rebake`

### 26.2 What the matrix proved

All three variants reached:

- `[bo3_rev][grant]`
- `first_raise`
- `idle_begin`
- `idle_end`

Important result:

- the positive control did **not** show up
- the tiny donor-order-valid idle edit on `tag_weapon` did **not** change the live idle contract
- `idle` stayed flat on the stock visible tags in all three variants

Representative evidence from `games_mp.log`:

- `A_stock_donor`
  - `idle_begin` on `vm=c_zom_engineer_viewhands`
  - `idle_end max_tag_flash_delta_sq=0`
  - `idle_end max_tag_weapon_delta_sq=0`
  - `idle_end max_tag_clip_delta_sq=0`
  - `idle_end max_tag_brass_delta_sq=0`
- `B_donor_tiny_edit`
  - same live backend name: `viewmodel_zomb_mg08_idle`
  - same forced shell: `c_zom_engineer_viewhands`
  - same flat idle result on visible tags
- `C_bo3_rebake`
  - same visible outcome: flat idle on stock visible tags

Interpretation:

- the engine is not visibly consuming the target runtime idle family as the live winner
- the blocker is no longer “BO3 rebake might still be wrong”
- the blocker is now runtime ownership / selection / consumer-side attachment

### 26.3 What the matrix also clarified

`first_raise` still moves in all three cases, but that does **not** rescue the idle result.

Observed `first_raise_end` maxima:

- `A_stock_donor`: `314.942`
- `B_donor_tiny_edit`: `283.027`
- `C_bo3_rebake`: `191.668`

So gross motion exists, but idle selection is still not using the positive-control edit. That means “some movement exists” is not enough evidence anymore.

### 26.4 Client-side watcher result

The client CSC watcher is still not the live first-person object.

It continues to report local body models such as:

- `c_zom_player_oldman_fb`
- `c_zom_player_farmgirl_fb`

while the server-side forced first-person shell is:

- `c_zom_engineer_viewhands`

So the CSC watcher remains useful as a secondary sanity check, but not as proof of the actual first-person DObj winner.

### 26.5 Probe work completed in this pass

The native probe was extended in two ways:

1. `xanim_focus` can now start the consumer-side arm thread as a supplemental path.
2. a new probe mode was added:
   - `xanim_consumer_focus`

`xanim_consumer_focus` is intended for the post-matrix selection problem:

- keep the watchlist and touch-trace layer
- skip the heavy xanim asset census / resolver workload
- arm the consumer-side render path directly

The probe now also logs:

- consumer render-table hits
- branch inference
- dword windows around consumer heap structs
- local pointer windows around those structs looking for watched xmodel/xanim strings

### 26.6 What the consumer probe proved

Using `xanim_consumer_focus` on the live C build:

- `consumer_render_table` hit
- `consumer_render_table_nonzero_branch` hit
- `consumer_render_table_zero_path` hit
- `consumer_render_table_compare` hit
- `consumer_render_table_match_branch` hit
- `consumer_asset_class_lookup` hit
- `consumer_submit_flags` hit

So the consumer-side hook path is real and active on the live first-person render flow.

What it did **not** prove yet:

- no direct `consumer_watch_hit` lines were recovered near the logged render-state heap structs
- that means the active first-person render objects do not expose watched asset names as simple nearby string pointers
- the current render-state objects appear to be heap structures using indirect tables / IDs / hashes rather than direct name pointers

### 26.7 Important probe caveat

The consumer-focused probe emits an `access_violation` line inside the DLL during safe memory probing.

Current interpretation:

- this is probe noise from guarded/offline heap memory reads
- it is **not** a game crash
- the process keeps running and the consumer traces still arm and hit afterward

So this is a probe robustness issue worth cleaning up later, but it does not invalidate the consumer findings from this pass.

### 26.8 Current blocker after this pass

The blocker is now explicit:

- custom gun model and target runtime xanim names are still loaded in memory
- deterministic stock first-person shell forcing is working
- the positive-control idle edit is not visible
- the consumer render path is active, but its heap structs do not expose direct watched-name pointers

That leaves one live problem:

- reverse the consumer-side model / anim attachment contract for the first-person render object

The next useful work is not more “is the asset loaded” passes.

The next useful work is:

- decode the consumer-side heap/object layout around the render-table hits
- identify which pointer/ID fields select model arrays and anim tables
- prove whether the live first-person consumer is attached to:
  - stock survivor viewhands only
  - donor MG08 model family
  - or the intended target runtime family

## 27. 2026-04-02 correction: consumer probe tooling bugs fixed, but live consumer hits are still not proven

The earlier "consumer path hit" conclusion is no longer authoritative by itself.

This pass found and fixed several real tooling bugs:

- multiple PowerShell runners were writing `active_probe_mode.txt` in the wrong format:
  - wrong: `mode=xanim_consumer_focus`
  - correct: `xanim_consumer_focus`
- the compare/matrix runners were still injecting the DLL using `-ProcessName t6zm`
  - corrected to the stable path:
    - `-ProcessName plutonium-bootstrapper-win32`
- the compare/matrix log wait regexes were incorrectly escaped as if PowerShell used C-style backslash escaping
  - example wrong pattern:
    - `\\[bo3_rev\\]\\[grant\\]`
  - corrected to:
    - `\[bo3_rev\]\[grant\]`

Those bugs mattered because they caused false "timeout" conclusions and empty probe logs even on runs that had actually reached `grant`.

### 27.1 What is now actually proven

The native DLL loads correctly and reads the intended mode:

- latest validated probe build in this pass:
  - `fx_runtime_probe_hook_20260402_223953.dll`
- direct injection into `plutonium-bootstrapper-win32` now logs:
  - `probe_mode ... value=xanim_consumer_focus`
  - `consumer_arm_thread_started mode=xanim_consumer_focus reason=consumer_focus`

The consumer arm thread itself was also instrumented and moved earlier:

- `xanim_consumer_focus` initial arm delay reduced from `5000 ms` to `1500 ms`
- explicit logs added:
  - `consumer_arm_attempt_begin`
  - `consumer_arm_attempt_enumerate_done`
  - `consumer_arm_attempt`
  - `consumer_arm_attempt_exception`

On a direct fast injection test, the consumer arm thread now reaches and arms the trace sites:

- `consumer_arm_attempt attempt=1 armed=4`

So the previous silent failure inside the consumer arm thread is fixed.

### 27.2 What is still not proven

A stable in-map custom idle run with `xanim_consumer_focus` still does **not** yet yield live `exec_trace_hit label=consumer_*` evidence.

Current observed failure shape:

- custom idle build can still reach:
  - `connect`
  - `grant`
  - forced stock shell selection
- watched live names still appear in memory:
  - `viewmodel_zomb_mg08_idle`
  - `viewmodel_zomb_mg08_first_raise`
  - `viewmodel_zomb_mg08_pullout`
  - `viewmodel_zomb_mg08_putaway`
  - `bo3_rev_v2_idg_view_<build_tag>`
  - `c_zom_engineer_viewhands`
- but on the current consumer compare custom pass, the gameplay logs stop almost immediately after `grant` once the probe is injected
- and the probe log shows:
  - consumer thread started
  - xanim/xmodel touch targets observed
  - no `exec_trace_hit label=consumer_*`

So the current blocker is narrower than before:

- the consumer arm path itself now works
- the remaining blocker is getting a stable in-map consumer-focus capture window where the armed traces can actually fire before the process/log flow stalls

### 27.3 Stock reference status

The stock-reference control in `run_consumer_reference_compare.ps1` is still unstable.

Current behavior:

- `custom_rebake` can reach `grant`
- `stock_reference` often fails before any `games_mp.log` gameplay markers appear
- in those failing stock runs:
  - `console_zm.log` stops in UI/load territory
  - `games_mp.log` is empty
  - no probe capture occurs

So right now the authoritative lane for consumer-focus debugging is still:

- custom idle lane
- deterministic stock shell forcing
- direct launch

not the donor-clone stock control.

### 27.4 Correct current blocker

The blocker is now:

1. get one stable custom idle run that reaches `grant`
2. inject the consumer-focus probe on that run
3. keep the process alive long enough for the already-armed consumer traces to fire
4. then recover the live first-person consumer object from actual `exec_trace_hit label=consumer_*` evidence

Until step 3 is stable, any statement stronger than "the consumer arm sites can now be armed" would be premature.

## 28. 2026-04-02 correction: live consumer hits are now proven on the custom idle lane

This section supersedes section 27 as the authoritative consumer-capture state.

### 28.1 What changed

`xanim_consumer_focus` was reduced to a true minimal first-hit mode in `native/fx_runtime_probe/fx_runtime_probe_hook.cpp`.

Important behavior changes:

- it no longer loads watchlists, touch tracing, xanim expectation scans, or runtime patch manifests in this mode
- it skips file-hook setup in this mode
- it now logs:
  - `consumer_focus_minimal_init enabled`
  - `consumer_first_hit ...`

A dedicated timing-sweep runner was also added:

- `tools/run_consumer_hit_sweep.ps1`

Purpose:

- freeze one custom idle build
- direct launch only
- deterministic stock shell only
- inject at several timings
- stop as soon as a real `consumer_*` hit is observed

### 28.2 Authoritative sweep result

Archive:

- `_build/bo3_rev_idg_probe/consumer_hit_sweeps/20260402_225906`

Build:

- `build_tag = 0403045909_75d444`

Probe:

- `fx_runtime_probe_hook_20260402_225856.dll`

Observed results:

- `startup`
  - probe armed successfully
  - `consumer_first_hit label=consumer_render_table`
  - but this run does **not** prove in-map gameplay state because no grant marker was reached before hit-and-exit
- `grant_plus_1s`
  - `grant` observed
  - stock shell forced to `c_zom_engineer_viewhands`
  - `first_raise_begin`, `first_raise_end`, and `idle_begin` observed in logs
  - probe armed successfully
  - `consumer_first_hit label=consumer_render_table`

This is the first authoritative proof in the repo that a live `consumer_*` execution hit occurs during a stable post-grant custom idle run.

### 28.3 What the probe logged on the first live in-map hit

On the `grant_plus_1s` run, the probe logged:

- `consumer_arm_attempt attempt=1 armed=4`
- `exec_trace_hit label=consumer_render_table`
- `consumer_first_hit label=consumer_render_table`

It also logged the live render-state neighborhoods:

- `esi_minus_e0 = 0x334CC050`
- `esi = 0x334CC130`
- `esi_plus_8 = 0x334CC138`
- `eax = 0x338306B0`

and emitted dword/object windows for:

- `render_state_esi_minus_e0`
- `render_state_esi`
- `render_state_esi_plus_8`
- `render_state_eax`

So the next reverse-engineering task is no longer "make the consumer sites fire." It is:

- recover the owning first-person consumer object chain from these live render-state structures

### 28.4 What is no longer the blocker

The blocker is no longer:

- wrong probe-mode file syntax
- wrong target process
- consumer arm-thread silence
- inability to arm the consumer trace sites
- inability to get a live `consumer_*` hit during a post-grant custom run

All of those are now proven good enough.

### 28.5 Current blocker after this pass

The active blocker is now the consumer object model itself.

Specifically:

- identify the live first-person consumer object behind the `consumer_render_table` hit
- recover how it resolves:
  - model ownership
  - anim ownership
  - handle / index / table indirection
- determine whether that chain resolves to:
  - stock first-person ownership
  - custom runtime backend ownership
  - or a mixed / fallback path

### 28.6 Heartbeat correction

A server-side `consumer_heartbeat` logger was added so future runs can show whether script-side activity survives immediately after injection.

Important correction:

- the first implementation checked `__PROBE_MODE__`, which is actually the gun-model lane token (`custom`, `base`, etc.), not the native probe mode
- that was corrected by adding a dedicated native probe-mode token to the rendered script

Treat the consumer-hit proof above as authoritative. Treat heartbeat verification as a small follow-up, not the blocker.

## 29. Consumer object capture is now stable

Authoritative archive:

- `_build/bo3_rev_idg_probe/consumer_hit_sweeps/20260402_234928`

Frozen lane:

- direct offline launch
- deterministic shell forcing
- `xanim_consumer_focus`
- custom idle build
- `grant_plus_1s` injection timing

The important correction in this pass was inside the probe:

- `log_consumer_render_state()` no longer runs the older heavy correlation / watched-pointer scans in `xanim_consumer_focus`
- `log_consumer_anchor_snapshot()` now emits only:
  - raw dwords
  - typed slot classification
  - window hash
  - completion marker
- the old heavy correlation scans are skipped in `xanim_consumer_focus`

That removed the mid-dump stall and made the object windows complete reliably.

### 29.1 Current recovered first-hit object anchors

From the stable `grant_plus_1s` run in `20260402_234928/grant_plus_1s/fx_runtime_probe.log`:

- owning heap object base: `0x32DBC050`
- render / consumer node: `0x32DBC130`
- render sub-struct / field block: `0x32DBC138`
- lookup-side object: `0x331206B0`

The first hit was:

- `consumer_first_hit label=consumer_render_table`

and the branch inference on that hit was:

- `esi_word = 0x0002`
- `zero_lane = 0`
- `table_value = 0x3E1B784F`
- `esi_plus_8_value = 0xA0AB1041`
- `compare_match = 0`
- `inferred = nonzero_branch`

That means the first authoritative live custom idle hit is on the nonzero render-table path, not the zero-lane compare-match path.

### 29.2 Stable fields now recovered

The following windows were captured at:

- `first_hit`
- `post_hit_250ms`
- `post_hit_1000ms`

Observed behavior:

- `render_state_esi_minus_e0` stayed stable across all captured phases
  - hash `0xDA2684F5`
- `render_state_esi` stayed stable across all captured phases
  - hash `0xBA04C74E`
- `render_state_esi_plus_8` stayed stable across all captured phases
  - hash `0x63F31B2D`
- `render_state_eax` stayed stable across all captured phases
  - hash `0xADB1CD2F`

So, at least on the current idle lane, these structures are ownership / identity carriers, not rapidly-changing per-frame state blocks.

### 29.3 Most useful typed first-hit fields

Current high-signal fields from the recovered windows:

- owning object `0x32DBC050`
  - mostly zero / small-int fields
  - `slot -3 = 0x00000200`
  - `slot -2 = 0x00000200`
  - `slot +1 = 0x00000100`
  - `slot +8 = 0x00000100`
- render node `0x32DBC130`
  - `slot +0 = 0x00000002`
  - `slot +1 = 0x00000001`
  - `slot +2 = 0xA0AB1041` classified as `ptr_heap`
- render node +8 block `0x32DBC138`
  - `slot +0 = 0xA0AB1041` classified as `ptr_heap`
  - this is the same value seen at render-node `slot +2`
- lookup object `0x331206B0`
  - `slot +0 = 0x3E1B784F` classified as `ptr_heap`
  - `slot +8 = 0x8147AD2D` classified as `int_or_flags`

Working interpretation:

- `0x32DBC050` is still the best candidate for the owning first-person consumer object
- `0x32DBC130` is still the best candidate for the active render / consumer node
- `0x32DBC138` is likely the important sub-struct or field block directly referenced by the render node
- `0x331206B0` is still the best candidate for a lookup / handle-source object rather than a direct string-bearing asset struct

### 29.4 What is now proven

This pass proves:

- the custom idle lane is stable enough for in-map post-grant consumer capture
- first-hit object capture now completes
- deferred object capture at `250 ms` and `1000 ms` now completes
- the relevant first-hit ownership windows are stable enough to diff and reason about

### 29.5 Current blocker after this pass

The blocker is no longer “can we capture the live consumer object.”

The blocker is now:

- recover the indirection from:
  - owning object `0x32DBC050`
  - render node `0x32DBC130`
  - render sub-struct `0x32DBC138`
  - lookup object `0x331206B0`
- determine which field(s) are:
  - model owner pointer / handle
  - anim owner pointer / handle
  - compact state / flags
  - final lookup input

That is the next real reverse-engineering step.

## 30. 2026-04-03 consumer lookup-path capture pass

This pass stayed on the exact same frozen lane:

- custom idle-only build
- deterministic stock shell forcing
- direct offline launch
- `xanim_consumer_focus`

No launcher/UI work was touched.

### 30.1 What was implemented

The native probe in `native/fx_runtime_probe/fx_runtime_probe_hook.cpp` was extended in three specific ways:

- first-hit consumer object capture can now start multiple deferred snapshot threads keyed by trigger/object family, instead of only the original render-table family
- `consumer_asset_class_lookup` now has its own compact logging and object capture path
- `consumer_image_class_map` now has its own compact logging and object capture path

The new lookup-path compact log lines are:

- `consumer_asset_lookup_compact`
- `consumer_image_map_compact`

For `consumer_asset_class_lookup`, the probe now captures:

- `EDI` owner object
- `EAX` source object
- `ECX` class/lookup object
- `ECX+6` word field as `class_word`
- `owner_plus_4`
- `ESI & 0xF` as a compact selector nibble

The sweep parser in `tools/run_consumer_hit_sweep.ps1` was updated to archive:

- `asset_lookup_hits`
- `image_map_hits`

inside `consumer_object_summary.json`.

### 30.2 Authoritative new archives

Current archives from this pass:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_003931`
- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_004213`

Both were run on the same frozen custom idle lane.

### 30.3 What the new runs proved

The new code path is live and stable enough to keep using:

- probe built successfully as `fx_runtime_probe_hook_20260403_003931.dll`
- both new runs reached:
  - build complete
  - direct launch
  - grant
  - probe injection
  - `consumer_render_table` first hit

So the new pass did not regress the only stable custom consumer lane.

### 30.4 What did not happen yet

The new logging path for `consumer_asset_class_lookup` is implemented, but on these two fresh runs that trace did not fire again.

So:

- the older recovered archive `20260403_003415_recovered` still remains the only proof that `consumer_asset_class_lookup` can fire on this custom lane
- the new code is ready to capture it in a structured way the next time it does fire
- but these two fresh runs only produced the render-table family

That means the current blocker is not “the lookup-path probe is missing.” It is “the lookup-path hit is still intermittent compared with the render-table family.”

### 30.5 New render-family observations

The new render-family captures still look like real persistent object carriers, but they are now even more obviously descriptor/state-like instead of string-bearing asset structs.

Example from `20260403_004213`:

- owning object candidate:
  - `0x2E1A29D4`
- render node candidate:
  - `0x2E1A2AB4`
- render sub-struct candidate:
  - `0x2E1A2ABC`
- lookup object candidate:
  - `0x2E1A45E0`

High-signal fields:

- owning `+0xE0 -> render node` remains consistent by construction of the hit site
- render node:
  - `slot +0 = 0x00000002`
  - `slot +1 = 0x00000001`
  - `slot +2 = 0xA0AB1041`
- render sub-struct:
  - `slot +0 = 0xA0AB1041`
- lookup object:
  - `slot +0 = 0xB60C3B3A`
  - `slot +4..+7 = 0x3F800000`

That `lookup object` layout is important:

- `slot +0` looks like an opaque ID / hash / compact handle, not a simple pointer
- `slot +4..+7` are repeated `1.0f`
- the object no longer looks like a nearby-string carrier

Working interpretation:

- the render-table family is probably downstream render/descriptor state
- the `EAX` lookup object is more plausibly a compact descriptor or lookup input than a direct asset struct
- this strengthens the earlier conclusion that stock/custom ownership is hidden behind numeric indirection, not simple string-adjacent pointers

### 30.6 Current state after this pass

The project is now at this exact decision point:

- `consumer_render_table` is the reliable stable anchor family
- `consumer_asset_class_lookup` is implemented as the next better ownership/indirection hook
- but fresh custom runs still only surface the render-table family

So the blocker has narrowed to:

- recover more meaning from the stable render-family objects and opaque lookup block
- and wait for / force the next `consumer_asset_class_lookup` hit so the new capture path can identify whether `EDI -> EAX -> ECX(+6)` is the real owner/class chain

### 30.7 What to do next

Do not change launcher flow, shell forcing, or xanim packaging.

The next correct work is:

- keep running the same narrow custom lane
- treat the current render-family objects as stable descriptor anchors
- use the new structured lookup capture the next time `consumer_asset_class_lookup` fires
- compare:
  - render-family opaque `EAX` descriptor block
  - lookup-path `ECX(+6)` class word
  - owner/source link from `EDI -> EAX -> ECX`

Only after that is it worth deciding whether the live stock/custom selection point is:

- an anim handle/index
- a model handle/index
- or a higher-level first-person consumer ownership choice

## 31. 2026-04-03 render-site differential capture pass

This pass stayed on the same frozen custom idle lane again, but changed the native probe in two targeted ways:

- stricter consumer slot classification
- repeated-hit instrumentation at the reliable `consumer_render_table` site

### 31.1 Classifier correction

`classify_consumer_value()` in `native/fx_runtime_probe/fx_runtime_probe_hook.cpp` was tightened so:

- printable 4-byte values are now classified as `ascii4` before module-pointer classification
- module pointers now require:
  - real mapped module membership
  - `VirtualQuery` success
  - `MEM_IMAGE`
  - committed, non-guarded memory
- finite floats are now recognized earlier

This removed several misleading “ptr_module” classifications from the render windows.

Current example from archive `20260403_005827`:

- render block bytes like:
  - `0x706D6970`
  - `0x6365745F`
  - `0x71696E68`
  - `0x745F6575`
are now classified as `ascii4`, not as bogus module pointers

That is a real improvement because those fields look like packed descriptor text / opaque data, not ownership pointers.

### 31.2 New render-site instrumentation

The render-table trace now:

- arms with `max_hits=4` in `xanim_consumer_focus`
- logs:
  - `consumer_render_hit_summary`
  - `caller_select`
- is prepared to snapshot:
  - `hit_2`
  - `hit_4`

if additional render-table hits occur during the same run.

The sweep parser now archives:

- `render_hit_summaries`
- `caller_selects`

inside `consumer_object_summary.json`.

### 31.3 Authoritative archive

Current authoritative archive for this pass:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_005827`

Probe build used:

- `fx_runtime_probe_hook_20260403_005827.dll`

### 31.4 What this pass proved

The corrected build ran successfully on the live lane and produced:

- stable build
- stable launch
- grant
- probe injection
- in-map `consumer_render_table` hit
- corrected slot classification
- caller context capture

Recovered first-hit summary:

- owning: `0x335DC050`
- render: `0x335DC130`
- render+8: `0x335DC138`
- lookup: `0x339406B0`

The caller context now also logs a stable selected return:

- `caller_select ... selected=0x7124D9F7 frame_count=6`

### 31.5 What did not happen

Even with `max_hits=4`, this lane still produced only one `consumer_render_table` hit in the archived run.

That means:

- the site is reliable for first-hit capture
- but it is not currently giving repeated in-map hits on this lane
- so the new `hit_2` / `hit_4` differential phases are implemented but did not fire yet

This is important because it narrows the next blocker further:

- the project is no longer blocked on render-site instrumentation
- it is blocked on finding a reliable way to capture a later nearby consumer state, either:
  - by reusing a site adjacent to `consumer_render_table`
  - or by catching another always-hit consumer path later in the same state sequence

### 31.6 Current interpretation of the render family

With the improved classifier, the current best reading is:

- `render_state_esi_minus_e0` still looks like a durable owner/state carrier
- `render_state_esi` and `render_state_esi_plus_8` still look like render-side node / sub-struct state
- `render_state_eax` still does not look like a direct asset header

In this pass:

- `render_state_eax +0 = 0x3E1B784F` now classifies as `float=0.151826`
- `+1..+3` classify as printable `ascii4`
- `+8` still points to a heap region

So `render_state_eax` remains descriptor-like and numerically opaque, not a direct model/xanim struct.

### 31.7 Current blocker after this pass

The blocker is now:

- first-hit consumer object recovery works
- render-family classification is cleaner
- but the render site is still only yielding one hit per live run on the frozen custom lane

So the next step should not be more generic scanning.

It should be one of:

- recover an adjacent always-hit site near the render-table path that fires later in the same first_raise -> idle sequence
- or force a second dependable consumer transition while staying on the same frozen lane

## 32. Consumer upstream return-site recovery and deferred-snapshot deadlock fix (2026-04-03)

### 32.1 What changed

This pass fixed a real native probe bug and added the next upstream trace family.

In `native/fx_runtime_probe/fx_runtime_probe_hook.cpp`:

- fixed the deferred-snapshot scheduling path so it no longer tries to reacquire `g_state_mutex` from inside the breakpoint handler
- added `start_consumer_deferred_snapshots_once_locked(...)` and switched all in-handler call sites to it
- added structured `render_state_edi` capture to the render-family first hit
- added upstream return-site arming from the live render-hit stack
- added structured upstream capture:
  - `consumer_upstream_hit_summary`
  - `upstream_edi`
  - `upstream_esi`
  - `upstream_eax`

In `tools/run_consumer_hit_sweep.ps1`:

- added parsing for:
  - `upstream_hit_summaries`
  - `upstream_arms`

### 32.2 Authoritative archive

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_014609`

Probe build:

- `fx_runtime_probe_hook_20260403_014551.dll`

### 32.3 What this pass proved

This was the first pass that completed the whole intended chain on the frozen custom idle lane:

- stable build
- stable launch
- grant
- probe injection
- live `consumer_render_table` hit
- deferred snapshots actually start and run
- upstream return-site traces arm from the render-hit stack
- one upstream return-site fires in the same run

Relevant probe lines from the authoritative archive:

- `consumer_deferred_snapshot_thread_started trigger=consumer_render_table ...`
- `consumer_upstream_arm slot=6 addr=0x00749BE0 rva=0x00349BE0`
- `consumer_upstream_arm slot=7 addr=0x00749C95 rva=0x00349C95 preferred=1`
- `exec_trace_hit label=consumer_upstream_ret_00349C95`
- `consumer_upstream_hit_summary label=consumer_upstream_ret_00349C95 hit=1 eip=0x00749C95 eax=0x38401BEC esi=0x30F57E48 edi=0x30F57E40`

### 32.4 Recovered object links

This pass recovered the first concrete cross-link between the reliable render family and an upstream caller-family site.

Render-family anchors:

- owning: `0x30F57D98`
- render: `0x30F57E78`
- render+8: `0x30F57E80`
- lookup: `0x38401C70`
- render_state_edi: `0x30F57E40`

Upstream hit:

- label: `consumer_upstream_ret_00349C95`
- `EDI = 0x30F57E40`
- `ESI = 0x30F57E48`
- `EAX = 0x38401BEC`

Meaning:

- upstream `EDI` is exactly the same object base as `render_state_edi`
- upstream `ESI` is `render_state_edi + 0x8`
- upstream `EAX` is in the same object family as the render lookup block and sits `0x84` bytes before `render_state_eax` / lookup (`0x38401C70 - 0x38401BEC = 0x84`)

So the best current working model is now:

- `render_state_edi` is an upstream parent/owner-side object
- `consumer_upstream_ret_00349C95` is a real caller-family site operating on that same parent object
- the render-table hit is downstream of that parent object, not the first owner edge

### 32.5 Important field-level facts

`render_state_edi` is now a meaningful anchor, not just another pointer dump.

From the authoritative run:

- `render_state_edi base = 0x30F57E40`
- `render_state_edi +0 = 0x30F57E84`
- `render_state_edi +2 = 0x30E2C374`
- `render_state_edi +3 = 0x30E76060`
- `render_state_edi +4 = 0x30F57ABC`
- `render_state_edi +7 = 0x30F57E60`

Notable relationships:

- `render_state_edi +0` points into the descriptor tail just past the render node base, not back to the render node header
- `render_state_edi +2` and `+3` are live heap children and are now good candidate sub-objects for model/anim ownership
- `render_state_edi +7` points at a small local sub-block where the first dword is `3`

### 32.6 Why this pass matters

This pass killed two important uncertainties:

- the probe was not “just stopping after the first hit for unclear reasons”; there was a real deadlock bug
- the upstream caller-family is no longer hypothetical; `consumer_upstream_ret_00349C95` is now a live, repeatable site on the custom lane

That means the project is now firmly in object-model recovery, not capture debugging.

### 32.7 Current blocker after this pass

The blocker is now:

- identify which fields inside `render_state_edi` / `upstream_esi` / the nearby lookup family are the ownership links
- determine whether `render_state_edi +2` / `+3` are model-owner or anim-owner sub-objects
- recover the exact relationship between upstream `EAX = 0x38401BEC` and render lookup `0x38401C70`

The next step should stay on this exact lane and focus on:

- one-hop field chasing from `render_state_edi`
- one-hop field chasing from `upstream_esi`
- compact differential capture around the `0x38401BEC -> 0x38401C70` lookup-family region

## 33. `render_state_edi` child-object recovery (2026-04-03)

### 33.1 What changed

This pass kept the exact same frozen `grant_plus_1s` custom idle lane and deepened the recovered render root itself.

In `native/fx_runtime_probe/fx_runtime_probe_hook.cpp`:

- `render_state_edi` child pointers are now promoted to first-class anchor snapshots
- deferred snapshots now include:
  - `render_state_edi_child_2`
  - `render_state_edi_child_3`
  - `render_state_edi_child_4`
  - `render_state_edi_child_7`
- lookup-family span capture was added so the `upstream EAX -> render lookup` region can be logged as one object when the upstream hit appears

### 33.2 Authoritative archive

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_015837`

Probe build:

- `fx_runtime_probe_hook_20260403_015837.dll`

### 33.3 What this pass proved

This run did not repeat the upstream-hit branch, but it did recover stable child objects directly from the render root:

- `render_state_edi base = 0x30A87E40`
- `render_state_edi +2 -> render_state_edi_child_2 = 0x3095C374`
- `render_state_edi +3 -> render_state_edi_child_3 = 0x309A6060`

These links are now encoded in the parsed summary as `anchor_links`.

### 33.4 Interpreting the child objects

`render_state_edi_child_2` now looks much more like a compact numeric/header block than a rich descriptor:

- `+0 = 0x00010003`
- `+1 = 0x02010000`
- `+2 = 0x00000502`
- later slots mostly zero

That makes `child_2` a better candidate for compact state / handle / ownership metadata than for a string-bearing descriptor.

`render_state_edi_child_3` looks very different:

- pointer-heavy header around `-4`, `-1`, `+0`, `+1`, `+2`
- `+3 = 0x00001820`
- embedded printable payload beginning at `+4`

So `child_3` currently looks more like a descriptor/string sidecar than the core compact ownership state.

### 33.5 Current best interpretation after this pass

The object model is narrowing in a useful way:

- `render_state_edi` is still the strongest parent/root candidate
- `render_state_edi +2 / child_2` is now the better candidate for compact state / ID / ownership metadata
- `render_state_edi +3 / child_3` is now more likely a descriptor payload sidecar than the main stock/custom selector

This matters because it reduces the next search space: `child_2` is now the higher-value target than `child_3`.

### 33.6 Current blocker after this pass

The blocker is now:

- determine whether `render_state_edi_child_2` contains the compact owner/handle path
- correlate that compact block against the lookup-family region
- demote `child_3` unless later evidence shows it feeds the selection path directly

So the next pass should focus on:

- one-hop chasing and numeric interpretation of `render_state_edi_child_2`
- renewed lookup-family span capture the next time the upstream branch fires

## 34. Child-state timing matrix on the frozen lane (2026-04-03)

I tightened the child-state matrix tool so it can re-summarize an existing sweep archive, report captured-only invariants, and compute root-relative child deltas instead of treating a single missing variant as a full negative.

Files:

- `Z:\Games\pluto_t6_full_game\tools\run_consumer_child_state_matrix.ps1`

Authoritative archive:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_021424`

Important sweep facts:

- variants run: `grant`, `grant_plus_1s`, `grant_plus_2s`, `grant_plus_4s`
- all four variants reached `grant`, injected, armed, and hit `consumer_render_table`
- `grant_plus_1s` did **not** recover `render_state_edi` child captures
- the missing `grant_plus_1s` child data is a partial-capture case, not a matrix parser bug

### 34.1 `child_2` result

Across the successful child-capture variants (`grant`, `grant_plus_2s`, `grant_plus_4s`), `render_state_edi_child_2` is completely invariant in both value and kind for every captured slot:

- `-4..-1 = 0`
- `+0 = 0x00010003`
- `+1 = 0x02010000`
- `+2 = 0x00000502`
- `+3..+8 = 0`

The root-relative placement is also invariant across those variants:

- `root -> child_2 delta = -0x0012BACC`

That is the strongest evidence so far that `child_2` is not transient descriptor material. It behaves like a compact ownership/state block or a compact handle block that stays stable across the tested timing windows.

### 34.2 `child_3` result

`render_state_edi_child_3` shows a split profile:

Stable captured slots across the successful variants:

- `-3 = 0x00010101`
- `-2 = 0x00000203`
- `+3 = 0x00001820`
- `+4..+8 = ascii payload beginning with "pimp_sha_der_debugper..."`

Variant-dependent slots across the successful variants:

- `-4`
- `-1`
- `+0`
- `+1`
- `+2`

Those varying slots are pointer-like / relocated values, while the payload / small-int region stays fixed.

The root-relative placement is still invariant:

- `root -> child_3 delta = -0x000E1DE0`

So `child_3` still looks like downstream descriptor / materialized render state, not the compact primary owner block.

### 34.3 Additional stable root links

The same matrix also showed that two other `render_state_edi` links are root-stable across the successful variants:

- `root -> child_4 delta = -0x00000384`
- `root -> child_7 delta = +0x00000020`

That means the local object layout around `render_state_edi` is more rigid than it first appeared. The child addresses relocate with the run, but their relative placement under the root stays constant.

### 34.4 Current interpretation after the matrix

The best current model is:

- `render_state_edi` is the real root object for the live render family
- `child_2` is the strongest compact ownership/state candidate
- `child_3` is a richer descriptor/projection block downstream of that compact state
- `child_4` and `child_7` are local sub-objects with stable root-relative placement, but not yet the main ownership lead

### 34.5 Current blocker after the matrix

The blocker is now narrower again:

- prove whether `child_2` is immutable ownership metadata or a compact state/handle block that changes only across a stronger state transition than this timing sweep
- correlate `child_2` against the lookup-family span from the upstream-hit run
- treat `child_3` as projection / descriptor state unless a later correlation shows it drives the selection path directly

## 35. Offline `child_2` to upstream-lookup join analysis (2026-04-03)

I added an offline join-analysis tool so we can correlate the finished child-state matrix against the earlier upstream-hit archive without waiting for the upstream branch to fire again.

Files:

- `Z:\Games\pluto_t6_full_game\tools\analyze_consumer_child2_lookup_join.ps1`

Authoritative output:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_021424\child2_lookup_join_summary.json`

Inputs:

- child-state matrix archive:
  - `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_021424`
- upstream-hit archive:
  - `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_014609\grant_plus_1s`

### 35.1 What the join confirms

The structural bridge is still valid:

- upstream `EDI == render_state_edi`
- upstream `ESI == render_state_edi + 0x8`
- upstream `EAX -> render lookup delta = +0x00000084`
- root `-> child_2 delta = -0x0012BACC`

The `child_2` compact signature used for the join was:

- `+0 = 0x00010003`
- `+1 = 0x02010000`
- `+2 = 0x00000502`

### 35.2 What the join does **not** show

There is no direct byte-level or dword-level presence of that `child_2` signature inside the captured windows for:

- `upstream_eax`
- `render_state_eax` / render lookup

There is also no contiguous match for the `child_2` three-dword sequence inside those captured windows.

Current conclusion from the offline join tool:

- `child_2_not_present_as_direct_dword_sequence_in_captured_lookup_windows`

### 35.3 Meaning

This is important because it rules out the simplest join theory:

- `child_2` is **not** just being copied verbatim into the captured upstream or render-lookup window we already have

So the current object model is:

- `render_state_edi` is still the root
- `child_2` is still the strongest compact ownership/state candidate
- `upstream_eax` and the later render lookup block are in one coherent family
- but the join between `child_2` and that lookup family is still indirect

That means the next useful recovery target is not another timing sweep. It is one of:

- a stronger semantic state transition that might move `child_2`
- or a one-hop handle/index correlation between `child_2` and the upstream lookup family

## 36. Field-transform join pass for `child_2` (2026-04-03)

I extended the offline join tool so it no longer checks only raw dword equality. It now compares the `child_2` compact fields against the captured `upstream_eax` and render-lookup windows using:

- low/high 16-bit halves
- bytewise matches
- low16/high16/low24/high24 masked comparisons
- 16-bit-swapped and byte-swapped dword transforms
- small delta candidates
- small XOR candidates

Files:

- `Z:\Games\pluto_t6_full_game\tools\analyze_consumer_child2_lookup_join.ps1`

Authoritative output:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_021424\child2_lookup_join_summary.json`

### 36.1 Result

The raw transform output contained only trivial overlaps dominated by zero padding.

After filtering for nontrivial signal:

- `high_signal_field_transform_summary.upstream_eax = null`
- `high_signal_field_transform_summary.render_lookup = null`

So there is currently **no meaningful field-transform evidence** that the `child_2` signature is being directly represented inside the captured:

- `upstream_eax` window
- render lookup (`render_state_eax`) window

### 36.2 Meaning

This kills the next easiest theory after raw dword equality:

- the `child_2` compact block is not obviously present in the lookup-family windows as simple:
  - halves
  - bytes
  - masked bitfields
  - swapped words
  - small delta transforms
  - small XOR transforms

So the join is still indirect.

### 36.3 Current blocker after the transform pass

The current blocker is now:

- recover the intermediate decode / table / handle step between `child_2` and the upstream lookup family
- stop spending passes on timing-only variation
- move next to a stronger semantic transition or a one-hop table/owner correlation

## 37. Root-local correlation pass (2026-04-03)

I added a dedicated root-local analysis pass so the next step is driven from the stable `render_state_edi` object family instead of from downstream lookup windows alone.

Files:

- `Z:\Games\pluto_t6_full_game\tools\analyze_render_root_local_correlation.ps1`

Authoritative output:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_hit_sweeps\20260403_021424\render_root_local_correlation_summary.json`

### 37.1 Stable root-local layout

Across the successful captures (`grant`, `grant_plus_2s`, `grant_plus_4s`), the root-side local layout is structurally rigid:

- `root +0 -> root +0x44`
- `root +2 -> child_2` with delta `-0x0012BACC`
- `root +3 -> child_3` with delta `-0x000E1DE0`
- `root +4 -> child_4` with delta `-0x00000384`
- `root +7 -> child_7` with delta `+0x00000020`

Invariant inline root fields:

- `root +1 = 0x00010080`
- `root +5 = 0x00010101`
- `root +6 = 0x00000203`
- `root +8 = 0x00000003`

### 37.2 New root-local relationships

The root-local correlation summary proved all of these relationships across every successful captured variant:

- `root +5 == child_3 -3`
- `root +6 == child_3 -2`
- `root +5 == child_4 -3`
- `root +6 == child_4 -2`
- `root +4 == child_7 -4`
- `root +5 == child_7 -3`
- `root +6 == child_7 -2`
- `root +7 == child_7 -1`
- `root +8 == child_7 +0`

This means two things:

- `child_7` is not behaving like an independent external owner object; it is an overlapping view into the root tail
- the root itself already contains inline header words that are mirrored into both descriptor-style children (`child_3` and `child_4`)

### 37.3 Descriptor-style children

Both `child_3` and `child_4` now look root-local descriptor/materialization blocks:

- `child_3 +0 -> child_3 +0x10`
- `child_4 +0 -> child_4 +0x10`
- `child_3 +2 -> child_3 +0x3B`
- `child_4 +2 -> child_4 +0x3A`

`child_4` also has a very descriptor-like payload shape:

- shared header words `0x00010101` / `0x00000203`
- payload beginning at `+4` with printable descriptor text

So `child_3` and `child_4` now look like sibling descriptor/materialization blocks rooted under the same parent object, not like the compact stock/custom selector itself.

### 37.4 Current interpretation after the root-local pass

The root-local chain now looks like:

- `render_state_edi` = stable root
- `child_2` = compact owner/state candidate
- root inline header words (`+5`, `+6`, `+8`) = shared compact descriptor header fields
- `child_3` / `child_4` = richer root-local descriptor/materialization blocks
- `child_7` = overlapping view into the root tail / continuation, not the ownership source

This is the strongest owner-side model in the repo so far.

### 37.5 Current blocker after the root-local pass

The blocker is now even narrower:

- determine whether `child_2` selects which root-local descriptor/materialization block becomes active
- or determine what one-hop table / handle / selector step exists between `child_2` and the mirrored root-local descriptor header fields

The next live pass should therefore target a stronger semantic transition, not another timing sweep.

## 38. Semantic transition compare: `first_raise_begin` vs `idle_begin` (2026-04-03)

I added a stage-targeted semantic compare runner so the next question could be answered directly from real script phases instead of timing approximations.

Files:

- `Z:\Games\pluto_t6_full_game\tools\run_consumer_semantic_transition_compare.ps1`

Authoritative archive:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_semantic_transitions\20260403_024405`

The runner:

- rebuilds the frozen custom idle lane once
- launches normally on the direct offline path
- waits for a real script marker
- injects on either:
  - `first_raise_begin`
  - `idle_begin`
- archives both runs and writes:
  - `semantic_transition_summary.json`
  - `semantic_transition_child2_summary.json`

### 38.1 Result

This pass answered the main question cleanly:

- `child_2` is invariant across the semantic `first_raise_begin` vs `idle_begin` compare

Authoritative output:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_semantic_transitions\20260403_024405\semantic_transition_child2_summary.json`

Captured variants:

- `first_raise_begin`
- `idle_begin`

For `render_state_edi_child_2`, every captured slot matched across both semantic runs:

- `-4..-1 = 0`
- `+0 = 0x00010003`
- `+1 = 0x02010000`
- `+2 = 0x00000502`
- `+3..+8 = 0`

Conclusion written by the runner:

- `child2_invariant_across_semantic_transition`

### 38.2 Stage verification

The stage-targeted runs did hit the intended script phases in the archived logs:

- `first_raise_begin` present in:
  - `first_raise_begin/console_zm.log`
  - `first_raise_begin/games_mp.log`
- `idle_begin` present in:
  - `idle_begin/console_zm.log`
  - `idle_begin/games_mp.log`

I also fixed a helper bug in:

- `Z:\Games\pluto_t6_full_game\tools\run_consumer_hit_sweep.ps1`
- `Z:\Games\pluto_t6_full_game\tools\run_consumer_semantic_transition_compare.ps1`

The stage-line extractor had only been matching `;stage=` and was missing lines where the payload began with ` stage=...`.

### 38.3 Meaning

This is a strong narrowing:

- `child_2` is not just invariant across timing-only variants
- `child_2` is also invariant across a real semantic `first_raise_begin -> idle_begin` transition

So the best current interpretation is now:

- `child_2` is more likely immutable ownership metadata than the dynamic handle that changes during that transition

That pushes the missing dynamic step one link away from `child_2`.

### 38.4 Current blocker after the semantic compare

The blocker is now:

- recover the immediate decode / selector / table step around `child_2`
- determine which root-local or one-hop object uses `child_2` to choose the mirrored descriptor/materialization state

The next useful live pass should therefore target:

- a stronger ownership-changing event than `first_raise -> idle`
- or one-hop root-side table/selector capture immediately around `child_2`

## 39. Root-local decode compare with corrected pointer-chase probe (2026-04-03)

I fixed a native probe capture bug before rerunning the semantic compare:

- `native/fx_runtime_probe/fx_runtime_probe_hook.cpp`

Correction:

- typed consumer slots stay on the conservative classifier
- pointer-chase logging now uses explicit readable-pointer validation instead of reusing the typed classifier

This matters because the previous semantic compare could miss a real one-hop chase when a heap address happened to look printable, while a naive pointer-first classifier polluted the typed windows and produced false structure drift.

I also added:

- `tools/analyze_semantic_root_decode_compare.ps1`

That script is the focused interpreter for the semantic archive. It compares:

- `render_state_edi`
- `render_state_edi_child_2`
- `render_state_edi_child_3`
- `render_state_edi_child_4`
- first-hop pointer chases for those contexts

and filters out known junk/noise cases when deciding whether a real decode signal exists.

Authoritative archive:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_semantic_transitions\20260403_025947`

Authoritative focused summary:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_semantic_transitions\20260403_025947\semantic_root_decode_summary.json`

### 39.1 Result

Across the corrected `first_raise_begin -> idle_begin` semantic compare:

- the meaningful root-local decode region stayed invariant
- there was no meaningful one-hop decode-table change

Specifically, these root slots matched after normalization in both variants:

- `root +3 = 0x00020101`
- `root +4 = 0x00000003`
- `root +5 = ptr_heap:+0x00002E00`
- `root +6 = ptr_heap:+0x00000028`

The focused summary writes:

- `root_local_slots_show_meaningful_change = false`
- `root_one_hop_changes = false`
- `child3_one_hop_changes = false`
- `child4_one_hop_changes = false`
- `semantic_decode_signal_found = false`

### 39.2 What changed and what did not

What did **not** move:

- the meaningful root-local region (`+3/+4/+5/+6`)
- any non-bogus one-hop root/local decode table capture

What **did** drift, but is currently treated as noise:

- `root +7`, which is just changing inline printable/ascii-looking payload
- `child_3` one-hop captures that resolve to the constant sentinel `0x3F3F3F3F`

Those `child_3` chases are not treated as a real decode path anymore. They are junk/sentinel captures, not a usable ownership/selector link.

### 39.3 Important correction about the built-in semantic runner summary

The fresh archive’s built-in runner output:

- `semantic_transition_summary.json`
- `semantic_transition_child2_summary.json`

is **not** the authoritative interpretation for this pass.

Reason:

- the generic runner summary treats all captured `child_2` slots equally
- the corrected focused analysis shows the apparent `child_2` drift is coming from an inline tail/noise field, not from the meaningful compact key region

The authoritative interpretation for this pass is the focused summary:

- `semantic_root_decode_summary.json`

### 39.4 Meaning

This is the cleanest statement of the blocker now:

- `first_raise_begin -> idle_begin` is still too weak to move the meaningful root-local decode path
- the dynamic ownership/materialization step is still not exposed by this semantic transition

So the next useful live pass should not be another timing-only or `first_raise -> idle` rerun.

### 39.5 Current blocker after the corrected decode compare

The blocker is now:

- trigger a stronger ownership-changing semantic transition
- or gate capture to a tighter consumer family / caller family before diffing

What should happen next:

- keep the current probe fix
- keep the focused root-decode analyzer
- move to a stronger transition such as putaway / weapon-away / equivalent ownership-changing state
- or bucket by stable consumer family before comparing decode fields

## 40. Grant/equip transition compare produced the first real decode signal (2026-04-03)

The putaway path did not become a reliable stronger-transition lane. Multiple `putaway` runs still stalled before `putaway_begin`, so I stopped treating that as the primary next move and implemented the next stronger ownership-changing edge instead:

- starter weapon still active immediately after the probe is granted
- then switch to the probe weapon
- then compare that against the live probe-weapon idle state

Files changed:

- `mods/bo3_rev/scripts/mod_i_am_mod.gsc.in`
- `tools/build_servant_minimal_anim_runtime.ps1`
- `tools/run_consumer_semantic_transition_compare.ps1`

New phase:

- `equip_hold`

New stage markers:

- `equip_hold_begin`
- `equip_hold_end`

The `equip_hold` phase briefly keeps `m1911_zm` active after the probe weapon is granted, logs the hold stage, then allows the normal switch into `first_raise` and `idle`.

### 40.1 Authoritative archive

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_semantic_transitions\20260403_034408`

Key summary files:

- `semantic_transition_summary.json`
- `semantic_transition_context_summary.json`
- `semantic_transition_caller_summary.json`
- `semantic_root_decode_summary.json`

### 40.2 What the run proved

Both variants completed successfully:

- `equip_hold_begin`
- `idle_begin`

Both variants also reached a real in-map consumer hit:

- `consumer_first_hit label=consumer_render_table`

Critical stage proof:

- `equip_hold_begin`: `cur=m1911_zm`, `vm=c_zom_engineer_viewhands`
- `idle_begin`: `cur=mg08_zm`, `vm=c_zom_engineer_viewhands`

So this is the first successful compare across an actual ownership-changing event, not just an animation-phase change inside the same equipped state.

### 40.3 Main result

This run produced the first authoritative positive decode signal in the repo:

- `semantic_transition_summary.json` conclusion:
  - `root_decode_changes_across_grant_equip_transition`
- `semantic_root_decode_summary.json` conclusion:
  - `semantic_decode_signal_found = true`

This means the meaningful consumer object family really does change across the starter-weapon ownership -> probe-weapon idle transition.

### 40.4 What changed

The root family changed materially:

- `render_state_edi`
- `render_state_edi_child_2`
- `render_state_edi_child_3`
- `render_state_edi_child_4`

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
- `+3`
  - equip hold: `0`
  - idle: `0x00001574`

So the old statement "child_2 is static ownership metadata" is now only true inside the same equipped-object family. Across a real starter -> probe ownership transition, the `child_2` family itself changes.

### 40.5 What this means

This is the cleanest current model:

- `first_raise_begin -> idle_begin` inside the same equipped probe state was too weak and left the meaningful root-local decode region invariant
- starter-weapon ownership -> probe-weapon idle is strong enough to move the root/child family
- therefore the first true dynamic selection point is upstream of the old idle-only object family and tied to ownership/equip selection, not idle-phase motion

In practical terms:

- the consumer path is not just mutating one fixed root-local table
- it is selecting or swapping to a different root/child object family when ownership changes from starter weapon to probe weapon

### 40.6 Caller-family note

Caller summaries differ across the two variants:

- `semantic_transition_caller_summary.json`

But this should be interpreted carefully:

- unresolved `<other>` frames still make caller-family signatures weaker than true RVAs
- stack-return families do differ too, which is still useful signal

So the safest conclusion is:

- caller/stack-return context is not identical across the ownership-changing transition
- the stronger transition is exercising a different live consumer path than the old idle-only compare

### 40.7 Current blocker after the grant/equip compare

The blocker is now narrower and better defined:

- recover how the starter-weapon ownership family transitions into the probe-weapon family
- identify which upstream selector / handle / table causes the object-family swap
- stop treating the idle-only root as the only root; it is one ownership-specific family, not the whole decode path

The next best pass should therefore focus on:

- the grant/equip edge as the authoritative stronger transition
- caller/stack-return bucketing around that edge
- and upstream ownership-family recovery rather than more idle-only table diffing

## 41. Grant/equip family-bundle recovery and caller bucketing (2026-04-03)

I added a dedicated bundle analyzer for the new ownership-side baseline:

- `tools/analyze_grant_equip_family_bundle.ps1`

Authoritative archive:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_semantic_transitions\20260403_034408`

Authoritative bundle summary:

- `Z:\Games\pluto_t6_full_game\_build\bo3_rev_idg_probe\consumer_semantic_transitions\20260403_034408\grant_equip_family_bundle_summary.json`

This script does four things the older semantic analyzer did not:

- treats `root`, `child_2`, `child_3`, `child_4`, and the render head as one ownership-family bundle
- emits the smallest practical selector set that distinguishes starter-weapon ownership from probe-weapon ownership
- buckets the two variants by caller family and stack-return family
- records upstream/lookup-family availability per ownership family

### 41.1 Main result

The grant/equip archive now has a clean ownership-family interpretation:

- ownership-family swap is confirmed
- the strongest selector deltas live in `root` and `child_2`
- the render head core is still stable
- the render descriptor pointer changes
- downstream materialization (`child_3` / `child_4`) changes too
- upstream bridge capture is present for the starter-owned family but still missing for the probe-idle family

From `grant_equip_family_bundle_summary.json`:

- `ownership_family_swap_confirmed = true`
- `render_head_core_stays_stable = true`
- `render_descriptor_ptr_changes = true`
- `selector_candidates_live_in_root_or_child2 = true`
- `downstream_materialization_changes = true`
- `upstream_bridge_complete_for_both_variants = false`

### 41.2 Invariant structure

The most useful invariant now is the render-head core:

- `render +0 = small_int:0x00000002`
- `render +1 = small_int:0x00000001`

So the core render-state counters stay fixed across the ownership swap.

What changes at render-head level is the descriptor pointer lane:

- `render +2`

That means the ownership transition is not changing the whole render-state shape blindly; it is preserving the small render-head counters while switching the descriptor side and the root/child family under them.

### 41.3 High-confidence selector set

The analyzer now emits a high-confidence selector set that avoids the noisiest inline/ascii slot.

Current best selector candidates:

- `root +4`
  - starter-owned family: `ptr_heap:-0x00000384`
  - probe-idle family: `small_int:0x00000003`
- `root +5`
  - starter-owned family: `ptr_region:0x00010101`
  - probe-idle family: `ptr_heap:+0x00002E00`
- `root +6`
  - starter-owned family: `small_int:0x00000203`
  - probe-idle family: `ptr_heap:+0x00000028`
- `child_2 +0`
  - starter-owned family: `ptr_region:0x00010003`
  - probe-idle family: `ptr_heap:+0x00000010`
- `child_2 +1`
  - starter-owned family: `ptr_module:0x02010000`
  - probe-idle family: `ptr_heap:+0x4543FB4C`
- `child_2 +2`
  - starter-owned family: `small_int:0x00000502`
  - probe-idle family: `ptr_heap:+0x0000003A`
- `child_2 +3`
  - starter-owned family: `zero:0x00000000`
  - probe-idle family: `small_int:0x00001574`

This is the cleanest practical selector set in the repo right now.

### 41.4 Caller-family bucketing on the ownership transition

The caller-family split is now explicit in the same summary.

Starter-owned family (`equip_hold_begin`):

- caller family:
  - `<other>:0x7BE6F7 > <other>:0x7BE2F2 > <other>:0x7D3FFE > <other>:0xDA37DF`
- stack-return family includes:
  - `plutonium-bootstrapper-win32.exe:0x00349BE0`
  - `plutonium-bootstrapper-win32.exe:0x00349C95`
  - `plutonium-bootstrapper-win32.exe:0x02FF39D0`
  - `plutonium-bootstrapper-win32.exe:0x02FED240`
- upstream hit present:
  - yes

Probe-idle family (`idle_begin`):

- caller family:
  - `<other>:0x63E6F7 > <other>:0x63E2F2 > <other>:0x653FFE > <other>:0xDA37DF`
- stack-return family includes:
  - `plutonium-bootstrapper-win32.exe:0x0360D6A0`
  - `plutonium-bootstrapper-win32.exe:0x0037C68D`
  - `plutonium-bootstrapper-win32.exe:0x0037C6B7`
  - `plutonium-bootstrapper-win32.exe:0x035F4864`
  - `plutonium-bootstrapper-win32.exe:0x0034EAA5`
  - `plutonium-bootstrapper-win32.exe:0x03606900`
  - `plutonium-bootstrapper-win32.exe:0x03608380`
- upstream hit present:
  - no

So the ownership transition is not only a root/child-family swap. It is also a caller/stack-return family split.

### 41.5 Upstream reconnect status

The upstream reconnect is now partially recovered, not complete.

Starter-owned family:

- upstream hit present:
  - `consumer_upstream_ret_00349C95`
- upstream registers:
  - `EAX = 0x387A1BEC`
  - `ESI = 0x312F7E48`
  - `EDI = 0x312F7E40`
- lookup-family span captured:
  - `+0`
  - `+4`
  - `+7`
  - `+37`

Probe-idle family:

- no upstream hit captured yet
- no lookup-family span captured yet

This is the current reconnect blocker:

- we now know the exact selector bundle that swaps ownership family
- but we do not yet have the matching upstream lookup-side capture for the probe-idle family

### 41.6 Current blocker after the bundle pass

The blocker is no longer “where does the ownership signal live?”

That part is now narrowed to:

- `root +4/+5/+6`
- `child_2 +0/+1/+2/+3`

The blocker is now:

- recover the same upstream lookup/descriptor family for the probe-idle branch
- then map which root/child selector bundle corresponds to which upstream lookup family

So the next correct pass should stay on the grant/equip edge and target:

- probe-idle upstream capture
- caller-family / stack-return-family gated recovery
- ownership-family-to-upstream-family mapping

## 42. Probe-idle upstream bridge recovered on the grant/equip edge (2026-04-03)

The missing probe-side upstream bridge is now real.

The key implementation fix was in the native probe:

- upstream-return arming moved to the front of the first-hit `consumer_render_table` path
- upstream arming now happens before the heavy first-hit anchor snapshots
- the semantic transition runner dwell was increased so the probe has time to flush the upstream captures

Authoritative archive:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_041208`

Relevant files:

- `native/fx_runtime_probe/fx_runtime_probe_hook.cpp`
- `tools/run_consumer_semantic_transition_compare.ps1`
- `tools/analyze_grant_equip_family_bundle.ps1`

### 42.1 What the new archive proves

On `idle_begin`:

- the probe now logs `consumer_upstream_bucket`
- the probe now arms upstream return sites
- the probe now records real upstream hits
- the probe now captures probe-side lookup-family span and upstream anchor windows

The probe-side upstream hits are:

- `consumer_upstream_ret_00349C95`
- `consumer_upstream_ret_00349C3B`

The first recovered probe-side upstream hit is:

- `EAX = 0x3359EF20`
- `ESI = 0x33565900`
- `EDI = 0x335658F8`

The probe-side first render hit in the same run is:

- `render root = 0x33565850`
- `render = 0x33565930`
- `render lookup = 0x3359EF60`

### 42.2 Probe-side upstream-to-render join

`grant_equip_family_bundle_summary.json` now includes a first-class upstream/render join summary.

For `idle_begin`:

- `upstream_edi_to_render_root = +0x000000A8`
- `upstream_edi_to_render = -0x00000038`
- `upstream_esi_to_render = -0x00000030`
- `upstream_eax_to_lookup = -0x00000040`

This is the first clean probe-side join recovered in the repo.

The meaning is:

- the probe-owned branch now reaches a live upstream lookup-side object family
- that family is structurally adjacent to the live render family
- the upstream EAX block sits 0x40 bytes before the later render lookup block on this branch

### 42.3 Important correction: probe-owned selector bundle, starter-owned return bucket

The latest archive does **not** repeat the older “probe-owned caller bucket” story in the same way.

On `idle_begin` in `20260403_041208`:

- the ownership-side selector bundle is still probe-owned and distinct
- but the recovered upstream return-site bucket is:
  - `starter_owned`
- the armed return sites are:
  - `0x00349C3B`
  - `0x00349C95`

So the newer authoritative correction is:

- probe-owned **ownership-family** selection is still real
- probe-owned **upstream connectivity** is now recovered
- but the upstream return-family on this run collapses back onto the `0x00349C3B / 0x00349C95` family rather than the older probe-only return bucket

This means the next blocker is no longer “get probe-side upstream at all.”

It is now:

- explain why the probe-owned selector bundle reaches the starter-style upstream return family on this branch
- map the probe-owned selector bundle to the recovered upstream lookup family and its `lookup - 0x40` relation

### 42.4 Current blocker after the upstream recovery

The repo is now past:

- launch uncertainty
- probe arming uncertainty
- “maybe the probe-side upstream bridge never fires”

The current blocker is now narrower:

- understand the selector/decode step that turns the probe-owned `root +4/+5/+6` and `child_2 +0/+1/+2/+3` bundle into the recovered upstream lookup-side family
- explain why the live probe-owned branch currently joins through the `0x00349C3B / 0x00349C95` upstream return family
- use that recovered join to continue the stock-vs-custom ownership mapping

## 43. Joined ownership-family mapping summary and caller-family correction (2026-04-03)

The next pass turned `20260403_041208` into a proper joined-family artifact instead of leaving the new probe-side bridge buried in raw logs.

Authoritative joined summary:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_041208/grant_equip_joined_mapping_summary.json`

Implementation file:

- `tools/analyze_grant_equip_joined_mapping.ps1`

### 43.1 Probe-owned joined family

The probe-owned branch is now explicitly modeled as one joined family:

- selector bundle
  - `root +4/+5`
  - `child_2 +0/+1/+2/+3`
- upstream family
  - `EDI = 0x335658F8`
  - `ESI = 0x33565900`
  - `EAX = 0x3359EF20`
- render family
  - `root = 0x33565850`
  - `render = 0x33565930`
  - `render_plus_8 = 0x33565938`
  - `lookup = 0x3359EF60`

Recovered root-local layout:

- `root -> upstream EDI = +0x000000A8`
- `root -> upstream ESI = +0x000000B0`
- `root -> render = +0x000000E0`
- `root -> render_plus_8 = +0x000000E8`

Recovered lookup relation:

- `upstream EAX -> lookup = -0x00000040`

So the probe-owned upstream path is now clearly root-local, and the upstream EAX object acts like a header/descriptor block 0x40 bytes before the later lookup object.

### 43.2 Important correction: the shared return family is not the ownership discriminator

The joined summary also answers the narrower caller-family question.

On `20260403_041208`:

- starter branch stack-return family includes:
  - `0x00349C3B`
  - `0x00349C95`
  - `0x02FF4F90`
  - `0x02FF0380`
- probe branch stack-return family includes:
  - `0x00349C3B`
  - `0x00349C95`
  - `0x02FF39D0`
  - `0x02FED240`

Shared return-family RVAs:

- `0x00349C3B`
- `0x00349C95`

That means the current best interpretation is:

- `0x00349C3B / 0x00349C95` are not the ownership discriminator by themselves
- they are a stable caller/return family that both ownership branches can pass through
- the actual ownership discrimination still lives on the selector/decode side

## 44. Probe-owned joined subviews are now decoded enough to stop guessing (2026-04-03)

The next pass stopped treating the recovered probe-owned upstream/render family as a loose cluster of addresses and turned it into a direct subview mapping.

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_041208/probe_joined_subviews_summary.json`

Implementation:

- `tools/analyze_probe_joined_subviews.ps1`

### 44.1 Corrected selector-root interpretation

An important correction was required before the mapping became clear:

- the earlier selector bundle `root +4/+5/+6` does **not** belong to `render_state_esi_minus_e0`
- it belongs to the `render_state_edi` / probe-owned `upstream_edi` view
- that view is the selector-root subview at:
  - `root + 0xA8 = upstream_edi = 0x335658F8`

So the current probe-owned joined family is:

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

### 44.2 First-hit mapping that now holds

The first-hit mapping on the probe-owned branch is now explicit:

- `root + 0xA8` / `upstream_edi`
  - `+4 = 0x3351BDCC`
  - `+5 = 0x00020101`
  - `+6 = 0x00000203`
  - those are the probe-owned selector-root values
- `root + 0xB0` / `upstream_esi`
  - `+0 -> 0x3123C374`
  - pointer-chase dwords at that target are:
    - `0x00010003`
    - `0x02010000`
    - `0x00000502`
    - `0x00000000`
  - that is the exact probe `child_2 +0/+1/+2/+3` signature
  - `+2/+3/+4` also mirror the selector-root values:
    - `+2 = 0x3351BDCC`
    - `+3 = 0x00020101`
    - `+4 = 0x00000203`
- `lookup - 0x40` / `upstream_eax`
  - behaves like a descriptor/header block, not a selector block
  - stable header-like fields:
    - `+0 = 0xA0AB1041`
    - `+1 = 0x02147063`
    - `+3 = 0x2C5D98C4`
  - stable ascii payload:
    - `+4 = 0x74672D7E` (`~-gt`)
    - `+5 = 0x6F665F35` (`5_fo`)
    - `+6 = 0x6761696C` (`liag`)
    - `+7 = 0x72645F65` (`e_dr`)
    - `+8 = 0x72625F79` (`y_br`)

### 44.3 What is now actually proven

The corrected subview summary gives the following true statements:

- `upstream_edi +4/+5/+6` mirror the probe-owned selector-root bundle
- `upstream_esi +0` points to the `child_2` base and decodes the exact `child_2` payload signature
- `upstream_esi +2/+3/+4` also mirror the probe-owned selector-root bundle
- `upstream_eax` behaves like the descriptor/header family at `lookup - 0x40`, not like the compact selector path

This means the probe-owned path is now concrete enough to describe as:

- selector-root view:
  - `root + 0xA8`
- selector-decode / child2 path:
  - `root + 0xB0`
- descriptor/header materialization:
  - `lookup - 0x40`

### 44.4 Current blocker after the joined-subview decode

The blocker is no longer:

- find probe-side upstream
- identify the selector bundle
- guess which recovered subview is the descriptor path

The blocker is now narrower:

- decode the exact step that takes the probe-owned selector-root bundle
  - `root + 0xA8 : +4/+5/+6`
- through the compact key at
  - `root + 0xB0 : +0 -> child_2`
- into the descriptor/header family at
  - `lookup - 0x40`

So the next reverse-engineering target is the selector/decode step **between**:

- `root + 0xA8`
- `root + 0xB0`
- `child_2`

and **before**:

- `lookup - 0x40`

## 45. Ownership-family compare on the selector-root to selector-decode hop (2026-04-03)

The next pass compared the starter-owned and probe-owned ownership families directly on the selector-root / selector-decode path using the same `20260403_041208` archive.

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_041208/selector_root_decode_ownership_compare_summary.json`

Implementation:

- `tools/analyze_selector_root_decode_ownership_compare.ps1`

### 45.1 What is now compared directly

Starter-owned side:

- selector-root base:
  - `0x3353C0F8`
- important fields:
  - `+2 = 0x31577F68` (`ptr_heap`)
  - `+3 = 0x31576754` (`ascii4`)
  - `+4 = 0x3353BDCC` (`ptr_heap`)
  - `+5 = 0x00010101` (`ptr_region`)
  - `+6 = 0x00000203` (`small_int`)

Probe-owned side:

- selector-root base:
  - `0x335658F8`
- selector-root fields:
  - `+2 = 0x3123C374` (`ptr_heap`)
  - `+3 = 0x33563B8C` (`ptr_heap`)
  - `+4 = 0x3351BDCC` (`ptr_heap`)
  - `+5 = 0x00020101` (`ptr_region`)
  - `+6 = 0x00000203` (`small_int`)
- selector-decode base:
  - `0x33565900`
- decode fields:
  - `+0 -> 0x3123C374`, which resolves to the exact `child_2` payload
  - `+2/+3/+4` mirror the selector-root bundle

### 45.2 Minimal ownership-family delta set

The minimal selector-root delta across starter-owned vs probe-owned is now explicit:

- `+2`
- `+3`
- `+4`
- `+5`

Invariant selector-root field:

- `+6 = 0x00000203`

So the ownership-family difference does **not** live in the whole selector-root block uniformly. It is concentrated in:

- the decode/projection candidate slots:
  - `+2`
  - `+3`
- and the selector input pair:
  - `+4`
  - `+5`

### 45.3 What this says about the field roles

Current best interpretation:

- starter `selector-root +2`
  - strongest starter-side decode candidate
- starter `selector-root +3`
  - dispatch/projection candidate, not yet decoded
- probe `selector-decode +0`
  - direct child pointer into the decoded `child_2` payload
- probe `selector-decode +2/+3/+4`
  - mirrors of selector-root inputs, not the compact child payload itself

So the probe-owned branch is now more explicit than the starter-owned branch:

- starter side still exposes the decode path only as a candidate at `selector-root +2/+3`
- probe side exposes the split path:
  - selector-root view
  - selector-decode child pointer
  - mirrored selector inputs

### 45.4 Current blocker after the ownership compare

The blocker is now narrower again:

- recover whether starter `selector-root +2 = 0x31577F68` is the starter-owned analog of the probe `selector-decode +0 -> child_2`
- determine whether starter `selector-root +3` and probe `selector-decode +1` are dispatch/projection fields or true decode inputs

So the highest-value unresolved roles in the repo are now:

- starter `selector-root +2`
- starter `selector-root +3`
- probe `selector-decode +1`

## 46. Historical consistency confirms probe selector-root +2 is an established decode-child pointer (2026-04-03)

The next offline pass checked whether the probe-family `selector-root +2` role was just a one-run interpretation or a repeated property of the recovered probe-family object model.

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_041208/probe_selector_decode_consistency_summary.json`

Implementation:

- `tools/analyze_probe_selector_decode_consistency.ps1`

### 46.1 Archives checked

The pass reused existing probe-family captures:

- `consumer_hit_sweeps/20260403_014609/grant_plus_1s`
- `consumer_hit_sweeps/20260403_015837/grant_plus_1s`
- `consumer_hit_sweeps/20260403_021424/grant`
- `consumer_hit_sweeps/20260403_021424/grant_plus_2s`
- `consumer_semantic_transitions/20260403_041208/idle_begin`

### 46.2 What is now confirmed

The conclusions in the new summary are now:

- `render_state_edi_plus_2_consistently_pointer_chases_to_child_2_in_probe_family = true`
- `render_state_edi_plus_2_matches_child_2_base_when_child_snapshot_exists = true`
- `semantic_idle_archive_also_shows_same_child_2_payload_via_upstream_esi = true`

That means the role is now upgraded:

- probe-family `selector-root +2` is no longer just a candidate
- it is an established decode-child pointer in the probe family
- in the semantic idle archive, the same child payload is surfaced through the split decode path at:
  - `root + 0xB0 = upstream_esi`
  - `+0 -> child_2`

### 46.3 What this changes

This removes another branch of uncertainty.

Current best interpretation is now:

- probe selector-root `+2`
  - established decode-child pointer
- probe selector-root `+3`
  - still unresolved dispatch/projection field
- starter selector-root `+2`
  - best candidate for the starter-owned analog of that same decode-child role
- starter selector-root `+3`
  - still unresolved dispatch/projection field

### 46.4 Current blocker after the consistency pass

The blocker is now narrower again:

- prove whether starter `selector-root +2 = 0x31577F68` is the starter-owned analog of the established probe decode-child pointer
- determine whether starter `+3` and probe decode `+1` are dispatch fields or downstream projections

## 47. Starter and probe decode-child symmetry is now proven (2026-04-03)

The next pass used one new live archive to close the biggest remaining ownership-side question.

Live archive:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_050555`

Authoritative symmetry summary:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_050555/starter_probe_decode_child_symmetry_summary.json`

Implementation:

- `tools/analyze_starter_probe_decode_child_symmetry.ps1`

### 47.1 What the new live archive proved

On the starter-owned branch in `20260403_050555/equip_hold_begin`:

- selector-root base:
  - `0x32D858F8`
- `selector-root +2 = 0x30A5C374`
- `render_state_edi_child_2` is now explicitly captured at:
  - `0x30A5C374`
- starter decode-child payload:
  - `0x00010003`
  - `0x02010000`
  - `0x00000502`
  - `0x00000000`

Compared against the authoritative probe-owned reference from `20260403_041208`:

- probe selector-root base:
  - `0x335658F8`
- probe `selector-root +2 = 0x3123C374`
- probe decode-child payload:
  - `0x00010003`
  - `0x02010000`
  - `0x00000502`
  - `0x00000000`

### 47.2 What is now confirmed

The new symmetry summary confirms:

- `starter_selector_root_plus_2_is_direct_decode_child_pointer = true`
- `starter_and_probe_decode_child_payloads_match = true`
- `probe_split_decode_path_matches_probe_child_payload = true`

So the starter-side analog is no longer open.

Current best model is now:

- starter selector-root `+2`
  - direct decode-child pointer
- probe selector-root `+2`
  - direct decode-child pointer
- starter and probe decode-child payloads
  - match exactly

This means the compact decode child is not an ownership discriminator by payload contents. The ownership-family distinction still lives in the fields surrounding that child path.

### 47.3 What this collapses

The blocker is no longer:

- recover the starter-owned analog of the probe decode-child path

That part is now solved.

The blocker is now narrower again:

- classify `selector-root +3` on starter and probe branches
- determine whether it is a true dispatch input or only a downstream projection
- then re-evaluate how `+4/+5` participate once `+2` is known symmetric

## 48. The semantic transition harness now captures `equip_hold_begin` pre-grant (2026-04-03)

The earlier `equip_hold_begin` path was contaminated by runner order. The old flow effectively waited for `grant`, then waited for `equip_hold_begin`, then injected, which is too late for a true starter-owned capture.

This is now fixed in:

- `tools/run_consumer_semantic_transition_compare.ps1`

Current trigger policy:

- `equip_hold_begin`
  - inject on `[bo3_rev][player_state] stage=pre_grant`
- `idle_begin`
  - inject on `[bo3_rev][grant]`

The runner also now regenerates `consumer_object_summary.json` from the archived `fx_runtime_probe.log` copy instead of the live probe handle, so future archives do not silently lose late-written contexts.

Validated post-fix archive:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_053026`

Proof from that archive:

- pre-grant line:
  - `[bo3_rev][player_state][t=2650] ... cur=m1911_zm`
- target stage line:
  - `[bo3_rev][anim_probe][t=2700] stage=equip_hold_begin ... cur=m1911_zm`
- grant line:
  - `[bo3_rev][grant][t=3800] ... current=mg08_zm`

So the starter capture is now genuinely pre-grant.

## 49. `selector-root +3` and `selector-decode +1` are the same probe-side field (2026-04-03)

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_053026/selector_dispatch_role_matrix_summary.json`

Implementation:

- `tools/analyze_selector_dispatch_role_matrix.ps1`

This pass used:

- corrected starter archive:
  - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_053026/equip_hold_begin`
- authoritative probe-owned joined-family archive:
  - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_041208/idle_begin`

### 49.1 What is now proven on the probe branch

Probe selector-root:

- base:
  - `0x335658F8`
- `+3`
  - slot addr `0x33565904`
  - value `0x33563B8C`

Probe selector-decode:

- base:
  - `0x33565900`
- `+1`
  - slot addr `0x33565904`
  - value `0x33563B8C`

So:

- `selector-decode +1` is not an independent selector variable
- it is the exact same field as `selector-root +3`

### 49.2 What that field points to

Probe consumer summary from `20260403_041208/idle_begin` shows:

- `render_state_edi_child_3` base:
  - `0x33563B8C`

That matches the probe `selector-root +3` value exactly.

So the correct probe-side role model is now:

- `+2`
  - decode-child pointer
- `+3`
  - family-specific pointer into the downstream `child_3` descriptor/materialization block
- `decode +1`
  - split-view alias of `+3`

This kills the old ambiguity between `+3` and `decode +1`.

### 49.3 What the corrected starter archive did and did not expose

The corrected pre-grant starter archive is valid on sequencing, but it still did **not** materialize the same joined selector-root/decode surface in the archived probe log.

From `selector_dispatch_role_matrix_summary.json`:

- `starter_selector_root_is_not_yet_materialized_in_true_pregrant_archive = true`

So after the harness fix:

- probe branch:
  - `+3` / `decode +1` ambiguity is closed
  - that field points to `child_3`
- starter branch:
  - the capture is genuinely pre-grant
  - but the archived hit still does not expose the joined selector-root/decode subview

### 49.4 Current blocker after this pass

The blocker is no longer:

- decide whether `selector-root +3` or `selector-decode +1` is the real field

That ambiguity is dead.

The blocker is now:

- recover the joined selector-root/decode surface on the true starter-owned pre-grant branch
- then compare the starter-owned `+3` descriptor/projection pointer against the probe-owned `+3` pointer directly

### 43.3 Confirmation rerun

Confirmation archive:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_042235`

That rerun used a longer post-hit dwell to test whether the starter-owned branch would also produce live upstream hits in the same harness.

Result:

- starter-owned branch still only armed upstream return sites and did not produce upstream hits
- probe-owned branch still used the same general return-family surface

So the latest confirmed blocker is:

- decode how the ownership selector bundle maps into the root-local probe-side upstream/render family
- not “find a unique caller family”
### 50. Correction: the starter joined selector-root/decode surface is now recovered (2026-04-03)

Sections 49.3 and 49.4 are now superseded by a newer archive.

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

### 51. Fresh live confirmation and focused `+4 / +5` role pass (2026-04-03)

Fresh live confirmation archive:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_055327`

Important verification from the corrected runner:

- `equip_hold_begin/variant_summary.json`
  - `joined_surface_seen = true`
  - `joined_surface_line = consumer_anchor_snapshot context=render_state_edi phase=first_hit base=0x314A7E40 ...`
- `idle_begin/variant_summary.json`
  - `joined_surface_seen = true`

So the new fallback in `tools/run_consumer_semantic_transition_compare.ps1` is now validated on a real fresh archive. The runner no longer depends on an explicit helper line to recognize starter joined-surface success.

Focused analyzer:

- `tools/analyze_selector_plus45_role_compare.ps1`
- authoritative output:
  - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/selector_plus45_role_summary.json`

What the focused `+4 / +5` compare now proves:

- on both branches:
  - `selector-root +4`
    - points to the branch-specific `child_4` descriptor family
  - `selector-root +5`
    - differs across starter vs probe
  - `selector-root +6`
    - matches across both branches (`0x00000203`)
- `child_3` header relationship:
  - `child_3[-3]` tracks `selector-root +5` on both starter and probe branches
- `child_4` header relationship:
  - starter `child_4[-3]` also tracks `selector-root +5`
  - probe `child_4[-3]` does **not**; it stays `0x00010101` while probe `+5` is `0x00020101`

Current best interpretation after this pass:

- `+4`
  - branch-specific pointer/base into `child_4`
- `+5`
  - smallest compact branch discriminator currently recovered
  - mirrored into `child_3` headers on both branches
- `+6`
  - shared structural constant

Current blocker after this pass:

- determine whether `+5` alone is sufficient to drive ownership-family dispatch
- or whether `+4` and `+5` form a coupled selector/base pair before `child_3` / `child_4` materialization

### 52. Paired-role analysis: `+4 / +5` should be treated as a coupled selector/base pair (2026-04-03)

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/selector_plus45_tuple_pairing_summary.json`
- `tools/analyze_selector_plus45_tuple_pairing.ps1`

This pass answered the next narrow question directly: is `+5` alone the true branch discriminator, or do `+4` and `+5` need to be interpreted together?

The tuple comparison used:

- starter tuple:
  - `(+4, +5) = (0x30BE7ABC, 0x00010101)`
- probe tuple:
  - `(+4, +5) = (0x3351BDCC, 0x00020101)`

and compared them against the downstream reporters:

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

Current best interpretation:

- `+5`
  - carries the compact family/mode signal
- `+4`
  - provides the branch-local descriptor/materialization base
- the live dispatch surface is therefore not `+5` in isolation
- it is the tuple:
  - `(+4, +5)`

Current blocker after this pass:

- recover where the coupled `(+4, +5)` tuple is consumed before `child_4` materialization diverges on the probe branch

### 53. Selector-decode is the first recovered consumer of the coupled `(+4, +5)` tuple (2026-04-03)

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

Current blocker after this pass:

- recover the next consumer after selector-decode that turns the coupled `(+4, +5)` tuple and `child_3` projection into probe-divergent `child_4` materialization

### 54. `child_3` header is the first recovered post-decode consumer (2026-04-03)

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
  - pointer-chase target:
    - `0x3351BDCC`
  - that matches probe `child_4` base exactly
- on starter:
  - `child_3[-4]` does **not** resolve directly to the final `child_4` base
  - pointer-chase target:
    - `0x30B078BC`
  - starter `child_4` base:
    - `0x30BE7ABC`
  - but the starter target still has the same child4-like `+0x10` descriptor shape

Concrete statement now supported by the repo:

- the `child_3` header is the first recovered post-decode consumer that maps selector-decode output toward `child_4` materialization
- probe collapses this step directly to `child_4`
- starter inserts one more child4-like intermediate descriptor node after `child_3[-4]`

Current blocker after this pass:

- recover the consumer between starter `child_3[-4]`'s intermediate descriptor node and final `child_4` base
- explain why the probe branch collapses that step directly to `child_4`

### 55. The starter-only `child_4` split is a clone/projection boundary, not a new selector surface (2026-04-03)

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/child4_clone_boundary_summary.json`
- `tools/analyze_child4_clone_boundary.ps1`

This pass closed the next ambiguity using the existing starter/probe archive. The repo now has enough evidence to say the extra starter hop is not a new unresolved selector stage. It is a clone/projection boundary between the child3-side descriptor pool and the root-local child4 binding surface.

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

Current blocker after this pass:

- explain the projection/materialization step that makes starter `child_3[-4]` land on a clone while root-local `+4` / `decode+2` already bind the final `child_4` self-base object

### 56. The first recovered post-clone link is the shared child4-like `-1` materializer class (2026-04-03)

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/child4_projection_materializer_summary.json`
- `tools/analyze_child4_projection_materializer.ps1`

This pass stayed entirely on the starter-only clone boundary and asked for the first concrete link between the child3-side clone view and final root-local `child_4`.

Result:

- the first recovered link is **not** another selector field
- it is a shared child4-like materializer/control class hanging off descriptor slot:
  - `-1`

Recovered `-1` materializer class:

- starter child3-side clone:
  - `child_3[-1] -> 0x30B07BE4`
  - materializer signature:
    - `0x00000003`
    - `0x00030040`
    - `0x040000D5`
    - `0x02400003`
- starter final `child_4`:
  - `child_4[-1] -> 0x30BE7DF4`
  - same materializer signature
- probe child3-side view:
  - `child_3[-1] -> 0x335658A4`
  - same materializer signature
- probe final `child_4`:
  - `child_4[-1] -> 0x3351C0B0`
  - same materializer signature

What is now proven:

- authoritative final bind is already root-local on both branches:
  - `selector-root +4`
  - `selector-decode +2`
  - final `child_4`
- starter clone and final `child_4` have distinct `-1` targets
- probe clone and final `child_4` also have distinct `-1` targets
- but **all four** `-1` targets carry the same materializer/control signature class
- therefore probe does **not** bypass the `-1` materializer class
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

Current blocker after this pass:

- recover how the starter branch projects from the child3-side child4-like clone to the root-local final `child_4` bind despite both descriptors already carrying the same local `-1` materializer class

### 57. No direct descriptor-local field links the starter clone to final `child_4`; the first recovered projection link is root-local (2026-04-03)

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

Current blocker after this pass:

- recover the earlier root-local or projection-layer object that emits both the child3-side clone view and the authoritative root-local final `child_4` bind on the starter branch

### 58. The first recovered common parent emitter is selector-root, mirrored by selector-decode (2026-04-03)

Authoritative artifact:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/common_parent_emitter_summary.json`
- `tools/analyze_common_parent_emitter.ps1`

This pass stopped treating the starter clone and final `child_4` as if one had to locally transform into the other. Instead it asked for the first recovered object that can already see and emit both outputs in the same family.

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
  - mirrors the same emitter surface
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

### 59. The selector-root +7 tail is downstream, not the projection-policy producer (2026-04-03)

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

Current blocker after this pass:

- recover the earlier root-local or projection-policy producer that writes `selector-root +3/+4` before the `+7` tail mirrors only the authoritative child4 side

### 60. No earlier local producer appears inside the widened selector-root policy window (2026-04-03)

Authoritative artifacts:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_123139/selector_root_policy_window_summary.json`
- `tools/analyze_selector_root_policy_window_compare.ps1`
- `native/fx_runtime_probe/fx_runtime_probe_hook.cpp`

This pass widened the live capture around `selector-root` itself instead of chasing more downstream descriptors. The probe now records a dedicated `render_state_edi_policy` window with `before=16, after=8`, and the same `equip_hold_begin -> idle_begin` ownership-edge compare was rerun live at `20260403_123139`.

Result:

- the widened policy window was captured successfully on both branches:
  - starter:
    - `render_state_edi_policy` at `0x31087E40`
  - probe:
    - `render_state_edi_policy` at `0x31037E40`
- after normalization:
  - slots `-16 .. +1`
    - are branch-invariant
  - `+2`
    - is still only the shared decode-child pointer
  - no earlier recovered local field before `+3`
    - explains the branch policy

What is now proven:

- there is no newly recovered earlier local producer inside the currently recovered selector-root window
- the widened local prefix is ruled out:
  - `-16 .. +1`
    - do not carry a branch-specific policy input
  - `+2`
    - remains shared decode-child plumbing
- therefore the next unresolved producer is either:
  - outside the currently recovered selector-root window
  - or a write site that populates `selector-root +3/+4/+5` before first-hit observation

Concrete statement now supported by the repo:

- no earlier root-local prefix field inside the widened selector-root policy window explains starter-versus-probe policy
- the earliest recovered policy surface is still the selector-root output region itself, and anything earlier has not yet been directly recovered in the current first-hit window

Current blocker after this pass:

- recover an earlier root-local producer outside the current selector-root window, or recover the write site that populates `selector-root +3/+4/+5` before first-hit capture

Current blocker after this pass:

- recover the earlier projection-policy object or root-local producer that populates `selector-root +3/+4` with starter’s split outputs versus probe’s collapsed identity output

### 61. Direct selector-root write provenance did not surface; the earliest live starter producer is `consumer_asset_class_lookup` (2026-04-03)

I implemented a direct write-provenance pass on the actual policy fields in [fx_runtime_probe_hook.cpp](/z:/Games/pluto_t6_full_game/native/fx_runtime_probe/fx_runtime_probe_hook.cpp): on the first recovered selector-root render hit, the probe now arms guarded watches for `selector-root +3`, `+4`, and `+5`, and the semantic runner keeps the starter branch alive long enough to catch a later overwrite if one occurs.

The authoritative run is [20260403_125212](/z:/Games/pluto_t6_full_game/_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_125212).

What it proved:

- On `idle_begin`, the probe reached the real selector-root render surface again:
  - first hit was `consumer_render_table`
  - the probe armed `selector_root_plus3/+4/+5` at `0x3345C104 / 0x3345C108 / 0x3345C10C`
  - but no `policy_write_guard_hit` or `policy_write_commit` ever followed in the archived probe log
- On the true starter-side `equip_hold_begin` branch, the first live consumer hit was not `consumer_render_table`
  - it was `consumer_asset_class_lookup`
  - the archive never materialized the joined selector-root render surface on that branch in this run
  - so there was no starter-side selector-root page to watch yet

The important correction is:

- the widened read-side window around selector-root is exhausted
- the direct write-side watch on selector-root also did not surface a writer
- not because the watch is broken on probe idle, but because the starter pre-grant branch in this run is still one stage earlier: `consumer_asset_class_lookup`

The earliest dynamic predecessor visible in the same starter archive is the asset-lookup family itself:

- `asset_lookup_edi` changes sharply after first hit
  - example: `+3` goes from `0x033F3880` at first hit to `0x00000006` by `post_hit_250ms`
  - `+4` goes from `0x00000000` to `0x00000007`
  - `+5` goes from `0x00000000` to `0x64356E1C`
- `asset_lookup_eax` also changes early
  - `+0` goes from `0x010161EA` to `0x010161F4`
  - `+4` goes from `0x000000EA` to `0x000000F4`
- `asset_lookup_ecx` is comparatively stable

So the blocker moved again:

- we do not currently have a direct writer for `selector-root +3/+4/+5`
- the earliest live starter-side producer we can actually see mutating is `consumer_asset_class_lookup`
- the next correct frontier is earlier than selector-root: recover how the `asset_lookup` owner/source/class family emits the later selector-root policy surface
### 62. Dedicated `xanim_asset_lookup_focus` recovers the probe-owned producer, but starter symmetry is still missing on the current lane (2026-04-03)

I added a dedicated `xanim_asset_lookup_focus` mode in [fx_runtime_probe_hook.cpp](/z:/Games/pluto_t6_full_game/native/fx_runtime_probe/fx_runtime_probe_hook.cpp) so the probe can arm only `consumer_asset_class_lookup` without the render surface taking over first. I also fixed [run_consumer_semantic_transition_compare.ps1](/z:/Games/pluto_t6_full_game/tools/run_consumer_semantic_transition_compare.ps1) so the mode file is no longer silently reset back to `xanim_consumer_focus` inside the per-variant loop.

The authoritative archive is now [20260403_134746](/z:/Games/pluto_t6_full_game/_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_134746).

What it proved:

- The new mode really loaded.
  - probe log reports `value=xanim_asset_lookup_focus`
  - only one consumer trace armed: `consumer_asset_class_lookup`
- Probe-owned `post_switch` now recovers the producer family directly.
  - first hit is `consumer_asset_class_lookup`
  - `asset_lookup_seen = true`
  - first hit summary: `edi=0x5F899010 eax=0x5F899080 ecx=0x380D9C34 esi=0x00000126`
  - compact tuple: owner `0x5F899010`, owner_plus_4/source `0x5F899080`, class `0x380D9C34`, class_head `0x380DD814`, class_word `0x0001`
  - recovered stack-return families now exist for the producer layer:
    - `consumer_asset_class_lookup|plutonium-bootstrapper-win32.exe:0x02FF4E10`
    - `consumer_asset_class_lookup|plutonium-bootstrapper-win32.exe:0x02C00000`
    - `consumer_asset_class_lookup|plutonium-bootstrapper-win32.exe:0x1222273F`
- The probe-owned producer snapshot is stable across deferred captures.
  - `asset_lookup_edi` hash stays `0x38F3BA4D`
  - `asset_lookup_eax` hash stays `0xB177170D`
  - `asset_lookup_ecx` hash stays `0x579378B0`
- Starter symmetry is still missing on the current dedicated lane.
  - `equip_hold_begin` armed the asset-lookup-only mode successfully
  - but no consumer hit fired on that branch in the same run
  - so the best starter-side producer archive remains [20260403_125212](/z:/Games/pluto_t6_full_game/_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_125212)

So the current frontier is tighter again:

- the producer layer is now directly recovered on the probe-owned branch with the dedicated mode
- the current missing symmetry is specifically the starter-side producer on the same dedicated lane
- the authoritative producer-layer compare is now:
  - starter-side producer evidence from `20260403_125212`
  - probe-side producer evidence from `20260403_134746`
### 63. Dedicated asset_lookup producer symmetry is recovered on both branches (2026-04-03)

This pass stayed entirely on the dedicated producer frontier and stopped trying to infer starter-side producer state from mixed consumer traces.

Changes:
- `native/fx_runtime_probe/fx_runtime_probe_hook.cpp`
  - `xanim_asset_lookup_focus` now arms earlier:
    - `consumer_arm_initial_delay_ms() = 250ms`
    - retry cadence reduced to `500ms`
  - asset-lookup deferred snapshots were tightened to the shorter schedule:
    - `post_hit_100ms`
    - `post_hit_400ms`
    - `post_hit_1200ms`
    - `post_hit_2500ms`
- `tools/run_consumer_semantic_transition_compare.ps1`
  - new transition: `asset_lookup_starter_only`
  - this path injects on true starter-side `pre_grant`
  - it uses `xanim_asset_lookup_focus`
  - it exits after the first producer tuple plus a short dwell instead of waiting for later selector-root materialization
- `tools/analyze_asset_lookup_owner_family_compare.ps1`
  - defaults now point at the dedicated starter/probe producer archives
  - compare output now treats producer-layer symmetry as the primary question

Authoritative dedicated starter archive:
- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_140546/equip_hold_begin`

Starter-side result on the dedicated lane:
- real pre-grant isolation:
  - `pre_grant` at `t=2650`
  - `equip_hold_begin` at `t=2700`
  - `grant` at `t=3800`
- `probe_mode = xanim_asset_lookup_focus`
- `consumer_first_hit = consumer_asset_class_lookup`
- dedicated starter producer tuple recovered:
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
- starter producer-layer caller/return families are now explicit:
  - caller family:
    - `selected = 0x00741F6C`
  - stack return families:
    - `consumer_asset_class_lookup|plutonium-bootstrapper-win32.exe:0x02FF4D50`
    - `consumer_asset_class_lookup|plutonium-bootstrapper-win32.exe:0x1031C49F`
    - `consumer_asset_class_lookup|plutonium-bootstrapper-win32.exe:0x1061C471`

Authoritative probe-side dedicated producer reference:
- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_134746/post_switch`

Probe-side result remains:
- hit 1:
  - `owner = 0x5F899010`
  - `source = 0x5F899080`
  - `class = 0x380D9C34`
  - `class_head = 0x380DD814`
  - `class_word = 0x0001`
  - `esi_nibble = 0x6`
- caller selected return:
  - `0x00741F6C`
- stack return families:
  - `consumer_asset_class_lookup|plutonium-bootstrapper-win32.exe:0x02FF4E10`
  - `consumer_asset_class_lookup|plutonium-bootstrapper-win32.exe:0x02C00000`
  - `consumer_asset_class_lookup|plutonium-bootstrapper-win32.exe:0x1222273F`

Authoritative compare:
- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_134746/asset_lookup_owner_family_compare_summary.json`
- conclusion:
  - `asset_lookup_owner_family_recovered_on_both_branches`

What is now established:
- `consumer_asset_class_lookup` is the earliest recovered live mutable family on both ownership branches.
- `selector-root +3/+4/+5` is downstream of this producer layer.
- starter-side producer symmetry is no longer missing on the dedicated lane.
- the producer caller surface is at least partly shared:
  - both branches currently select `0x00741F6C`
- the branch split is now in the producer family contents / stack-return families, not in whether the producer layer exists.

Important nuance:
- starter dedicated recovery has two producer hits and stable owner/source across those hits.
- dedicated deferred snapshot phase lines did not materialize cleanly on the starter archive even though the deferred thread started, so the strongest starter-side stability evidence in this pass is:
  - repeated producer hits
  - stable owner/source
  - stable caller family
  - evolving class/class_head pair within the same starter-owned producer family

Current blocker after this pass:
- not launch
- not probe mode
- not producer-layer symmetry
- now specifically:
  - determine which `consumer_asset_class_lookup` field(s) are the earliest live producer inputs that later materialize as downstream selector-root `+3/+4/+5`

Best next continuation:
- stay on `xanim_asset_lookup_focus`
- compare starter/probe producer tuples and stack-return families as the primary layer
- only after that reconnect the recovered producer fields to downstream selector-root population

### 64. Producer-to-selector materialization candidates are narrowed to the class/class_head family (2026-04-03)

Authoritative summary:
- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_134746/asset_lookup_to_selector_materialization_summary.json`

This pass stayed at the producer layer and joined it to the already-recovered downstream selector bundle instead of widening back out into downstream descriptor analysis.

Inputs:
- starter producer archive:
  - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_140546/equip_hold_begin`
- probe producer archive:
  - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_134746/post_switch`
- downstream selector references:
  - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/selector_dispatch_role_matrix_summary.json`
  - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_054006/selector_plus45_role_summary.json`

Recovered producer-side shape:
- starter hit 1 class object:
  - `class = 0x2DFE5754`
  - `class_head = 0x2DFE7BC0`
  - `class +2 = 0x2DFDBB20`
  - `class +3 = 0x2DFDEDD0`
  - `class +4 = 0x2DFE5774`
  - `class +5 = 0x00120105`
  - `class +6 = 0x00000201`
- starter hit 2 class object:
  - `class = 0x2FC10DAC`
  - `class_head = 0x2FC14390`
  - `class +2 = 0x2FC02BCC`
  - `class +3 = 0x2FC07E90`
  - `class +4 = 0x2FC10DCC`
  - `class +5 = 0x01150105`
  - `class +6 = 0x00000201`
- probe hit 1 class object:
  - `class = 0x380D9C34`
  - `class_head = 0x380DD814`
  - `class +2 = 0x30B6A428`
  - `class +3 = 0x380D9C54`
  - `class +4 = 0x380DBAEC`
  - `class +5 = 0x00070101`
  - `class +6 = 0x00000203`

Downstream selector bundle used for the join:
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

What this kills:
- the earliest producer inputs for downstream selector-root `+3/+4/+5` are not the outer owner/source wrapper
- `class_word = 0x0001` is structural, not the earliest branch discriminator
- the producer frontier is not “owner/source versus selector-root”; it is inside the class/class_head family

What is now established:
- structural wrapper fields:
  - `source = owner + 0x70` on both branches
  - `class_word = 0x0001` on both branches
  - starter `owner/source` stay stable across repeated hits while `class/class_head` evolve
- strongest producer-side pointer-family candidates upstream of selector-root `+3/+4`:
  - `class`
  - `class_head`
  - `class +2`
  - `class +3`
  - `class +4`
- strongest producer-side compact candidates upstream of selector-root `+5`:
  - `class +5`
  - `class +6`

Best current interpretation:
- the earliest recovered producer inputs for downstream selector-root `+3/+4/+5` are the branch-shaped `class/class_head` family, not the outer producer wrapper
- `class/+2/+3/+4` are the best current upstream candidates for downstream selector-root pointer-family materialization
- `class/+5/+6` are the best current upstream candidates for downstream selector-root compact flag materialization

Current blocker after this pass:
- producer-layer symmetry is no longer the blocker
- the unresolved step is now:
  - which `consumer_asset_class_lookup` class/class_head field(s) are the first producer inputs that later materialize as downstream selector-root `+3/+4/+5`

### 65. Producer-to-selector field join and class-family role split are now explicit (2026-04-03)

Authoritative summaries:
- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_134746/producer_to_selector_field_join_summary.json`
- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_134746/class_family_role_split_summary.json`

This pass stopped treating `consumer_asset_class_lookup` as one opaque producer tuple and instead split the producer family into:
- pointer-family candidates for downstream selector-root `+3/+4`
- compact-family candidates for downstream selector-root `+5/+6`

What is now established:
- pointer-family side:
  - the earliest recovered branch-local projection-base family upstream of selector-root `+3/+4` is:
    - `class`
    - `class_head`
    - `class +2`
    - `class +3`
    - `class +4`
  - branch-local shape inside that pointer family is now explicit:
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
- compact-family side:
  - the earliest recovered compact family-code candidates upstream of selector-root `+5/+6` are:
    - `class +5`
    - `class +6`
  - `class +5` is now the stronger branch-shaped compact signal before selector normalization:
    - starter hit 1:
      - `class +5 = 0x00120105`
      - `class +6 = 0x00000201`
    - starter hit 2:
      - `class +5 = 0x01150105`
      - `class +6 = 0x00000201`
    - probe hit 1:
      - `class +5 = 0x00070101`
      - `class +6 = 0x00000203`
  - `class +6` behaves partly structural:
    - it matches downstream selector `+6` on probe
    - it does not match downstream selector `+6` on starter

Downstream selector reference:
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

Best current interpretation:
- `class/class_head` choose the branch-local projection-base family for downstream selector-root `+3/+4`
- `class +5/+6` carry the upstream compact family code that later normalizes into downstream selector-root `+5/+6`
- within that compact pair:
  - `class +5` is the stronger branch-discriminative compact signal
  - `class +6` behaves partly structural and converges to downstream selector `+6`

Current blocker after this pass:
- the unresolved step is no longer “where is the producer family”
- it is now:
  - which exact `class/class_head/+2/+3/+4` field(s) emit downstream selector-root `+3/+4`
  - whether `class +5` alone is the true compact discriminator for downstream selector-root `+5`, with `class +6` acting as partly structural pre-normalization state

### 66. Canonical producer->selector emission model is now ranked and falsifiable (2026-04-03)

Authoritative summary:
- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_134746/canonical_producer_selector_emission_summary.json`

This pass consolidated the authoritative producer and joined-surface archives into one canonical offline model. It used:
- producer layer:
  - starter: `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_140546/equip_hold_begin`
  - probe: `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_134746/post_switch`
- joined selector surfaces:
  - starter: `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_053026/equip_hold_begin`
  - starter: `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_055327/equip_hold_begin`
  - probe: `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_041208/idle_begin`
  - probe: `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_055327/idle_begin`

Branch consensus in the final artifact:
- starter:
  - `producer_hit_support_count = 2`
  - `joined_surface_support_count = 2`
- probe:
  - `producer_hit_support_count = 1`
  - `joined_surface_support_count = 2`

Canonical model now supported by the repo:
- producer wrapper:
  - `owner/source/class_word` are structural
- pointer-family / projection-base side:
  - `class/class_head/+2/+3/+4` are the earliest recovered branch-local projection-base family upstream of selector-root `+3/+4`
- compact-family side:
  - `class +5/+6` are the earliest recovered compact family-code candidates upstream of selector-root `+5/+6`

Ranked hypotheses:
- projection-base family:
  - highest-confidence hypothesis:
    - selector-root `+3/+4` are best explained as a branch-controlled permutation/materialization of the class-family projection bases
  - support:
    - starter support count `2`
    - probe support count `1`
    - conflicting archive count `0`
  - rejected direct theory:
    - selector-root `+3/+4 == class +3/+4` directly
    - support counts `0 / 0`
- compact family:
  - highest-confidence hypothesis:
    - selector-root `+5` is emitted from `class +5`
    - `class +6` contributes mostly structural pre-normalization state that later converges into selector-root `+6`
  - support:
    - starter support count `2`
    - probe support count `1`
    - conflicting archive count `0`

Most important surviving evidence:
- branch-swap clue:
  - starter:
    - `class +3 = external_ptr_family`
    - `class +4 = self_plus_0x20`
  - probe:
    - `class +3 = self_plus_0x20`
    - `class +4 = external_ptr_family`
- downstream compact convergence:
  - `class +5` remains strongly branch-shaped before selector normalization
  - `class +6` converges into shared downstream selector-root `+6 = 0x00000203`

Best current interpretation:
- `class/class_head` identify the branch-local projection family
- `class +3/+4` are the immediate projection-base candidates whose ordering/materialization is branch-controlled
- `class +5` is the strongest compact discriminator candidate for downstream selector-root `+5`
- `class +6` is mostly normalized structural state

Canonical conclusion:
- selector-root `+3/+4` are best explained as a branch-controlled permutation/materialization of the class-family projection bases
- selector-root `+5` is emitted from `class +5`
- `class +6` is mostly normalized structural state

Explicit falsification rules now recorded:
- if any future trustworthy branch capture shows matching `class +5` but differing downstream selector-root `+5`, the `class +5` discriminator theory is wrong
- if any future trustworthy branch capture shows downstream selector-root `+6` diverging without corresponding `class +6` normalization drift, the `class +6` structural theory is wrong
- if any future trustworthy branch capture breaks the starter/probe `class +3/+4` swap pattern while downstream selector-root `+3/+4` still materialize normally, the permutation/materialization model is wrong
- if downstream selector-root `+3/+4` change while `class/class_head` remain fixed across the same producer family transition, then `class/class_head` are not the upstream projection-family identity inputs we think they are

Current blocker after this pass:
- the repo is no longer blocked on identifying the compact family
- the strongest remaining ambiguity is now:
  - which exact member of `class/class_head/+3/+4` is the first direct emitter of downstream selector-root `+3/+4` on the write path
- next live hook if needed:
  - `consumer_asset_class_lookup` class-family write path that materializes `class/class_head/+3/+4` into selector-root `+3/+4`

# 67) class_family_materialization_writepath: asset_lookup-only capture + candidate selector roots

Live writepath pass pivoted to asset_lookup-only arming so the producer tuple fires before any render-table work.

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

What this means now:
- we can recover a candidate selector-root directly from the producer-side `asset_lookup_ecx` on both branches
- `policy_write_*` never fires after candidate watch arming
- the selector-root `+3/+4/+5` values are already populated before the asset_lookup breakpoint fires

Updated blocker after this pass:
- the missing write provenance is earlier than the current `consumer_asset_class_lookup` hit site
- we need an earlier write-side hook (pre-asset_lookup or function-entry provenance) or a forced re-materialization after watch arming

Next live move:
- add an earlier write hook (pre-hit site) for the asset-lookup path, or
- force a re-materialization after watch arming so `policy_write_guard_hit` can observe a live write

# 68) class_family_materialization_writepath: earlier hook attempt results

Implementation:
- added asset-lookup entry hook (`consumer_asset_lookup_entry`) by scanning for a prologue near `kConsumerAssetClassLookupRva`
- added asset-lookup callsite scan across all modules (direct `E8` rel32)
- expanded upstream return capture to:
  - more stack slots
  - relaxed RVAs for main module in writepath mode
  - non-main module candidates in writepath mode
- added explicit stack scan logging (`asset_lookup_stack`) for this mode

Result (starter / equip_hold_begin):
- entry hook armed at `0x00741AE0` for target `0x00741C36`
- no `consumer_asset_lookup_entry` hits observed
- callsite scan across modules still returns empty
- upstream return candidates arm successfully, but no upstream hits observed
- still no `policy_write_guard_hit` / `policy_write_commit`

Meaning:
- the initial materialization write of selector-root `+3/+4/+5` appears to occur before any of the current asset-lookup-site hooks execute
- direct callsite provenance (rel32 `E8`) and simple prologue entry hooks did not expose the writer

Updated blocker after this pass:
- need a pre-asset-lookup writer hook that is not reachable via direct callsite scan or simple prologue entry
- either the writer is in a different phase before our injection, or the call path is indirect (jmp table / vtable / function pointer)

# 69) temporal provenance on selector-root candidates

Implemented a new object-side temporal pass for `class_family_materialization_writepath`:
- pre-hit selector-root temporal scan thread
- candidate first-seen logging
- immediate `selector_root +3/+4/+5` watch arming on first sight
- temporal match logging when a later asset-lookup candidate equals an already-tracked selector-root

Two key outcomes:

1. Loose temporal scan was too permissive:
- archive: `20260403_172307/equip_hold_begin`
- it found many pre-hit heap candidates and armed watches
- it produced real pre-consumer `policy_write_guard_hit` events before any `consumer_asset_class_lookup` hit
- but the compact family on those candidates was wrong:
  - example guarded candidate:
    - `selector_root=0x25634114`
    - `+3=0x000003E9`
    - `+4=0x00180000`
    - `+5=0x10000000`
    - `+6=0x00000201`
- this proves the temporal object watch machinery works
- it does **not** prove we found the real branch selector-root family

2. Tightened temporal scan removed noise but found no pre-hit real branch candidate:
- tightened shape:
  - `+3 == 0`
  - `+5 in {0x00070101, 0x01030105, 0x01070105}`
  - `+6 in {0x00000201, 0x00000203}`
- archives:
  - `20260403_172632/equip_hold_begin`
  - `20260403_172924/post_switch`
- result:
  - no temporal candidate first-seen lines
  - no `selector_root_temporal_match`
  - no pre-hit guard events on the tightened family

What this means:
- the real branch selector-root family is not appearing early enough to be caught by the tightened pre-hit scan, at least with the current candidate shape
- the earlier noisy page writes belong to other heap objects that happen to satisfy weaker structural filters
- the actual branch-defining object is either:
  - born/populated later than those noisy temporal hits, or
  - one step upstream/downstream of the exact `asset_lookup_ecx` candidate shape we are scanning for

Current blocker after this pass:
- temporal provenance now works mechanically, but candidate identification is still one level too loose or too late
- the next useful move is not another generic callsite search
- it is a branch-specific temporal/object-family scan seeded by the recovered producer family instead of generic heap-shape matching

# 70) class_family_materialization_writepath: entry frontier moved earlier and became concrete

I took the frontier over from `consumer_asset_class_lookup` and moved it one level earlier into `consumer_asset_lookup_entry`.

Important probe/runtime fixes in this pass:
- repaired the live semantic runner so `-SkipBuild` still syncs the actual loose scripts and generated client scripts into AppData before launch
- hardened selector-root writepath capture so the dedicated lane runs on a valid mod mirror instead of stale scripts
- added real `consumer_asset_lookup_entry` object capture:
  - first-hit anchor snapshots
  - deferred snapshots
  - stack-return capture
  - candidate selector-root probing
- tightened false-positive logic:
  - upstream stack-return arming now filters to executable addresses
  - `looks_like_selector_root()` no longer accepts the bogus low-address / float-block families that were poisoning the run

Authoritative live archives from this pass:
- starter / pre-grant: `20260403_184232/equip_hold_begin`
- probe / true post-switch injection: `20260403_185720/post_switch`
- offline compare artifact: `20260403_185720/asset_lookup_entry_wrapper_compare_summary.json`

What is now proven:
- the earliest reliable live hit on the writepath lane is `consumer_asset_lookup_entry`, not `consumer_asset_class_lookup`
- stage-triggered probe injection at real `stage=post_switch` still reaches `consumer_asset_lookup_entry`
- the first recovered object family at that frontier is a stack-local wrapper, not a durable heap-side selector object:
  - on both starter and probe:
    - `EDI = ESP + 0x14`
    - `ECX = EDI + 0x70`
    - `EDI[+0] = EAX` (owner float block)
    - `EDI[+1] = ECX` (adjacent source/class-local block)
    - `ESP[+2]` and `ESP[+4]` mirror `EDI[-3]`
    - `ESP[+8]` mirrors `EDI[+3]`

Earliest recovered branch split at that wrapper:
- starter (`20260403_184232/equip_hold_begin`)
  - `EDI[-3] = EDI[-1] = 0x033F0380`
  - `EDI[+3] = 0x033F4E10`
- probe (`20260403_185720/post_switch`)
  - `EDI[-3] = EDI[-1] = 0x033ED240`
  - `EDI[+3] = 0x033F3580`

Concrete statement the repo now supports:
- the earliest recovered starter/probe branch split is already present at `consumer_asset_lookup_entry` in a stack-local wrapper at `EDI = ESP + 0x14`
- that wrapper emits a branch-local projection-base pair in `[-3/-1]` and `+3`
- selector-root is therefore downstream of this wrapper, not the earliest branch-discriminative producer surface

One caveat that is still unresolved:
- the new entry step-trace now begins reliably, but an unrelated breakpoint fires before the first single-step lands
- so instruction-by-instruction provenance from entry is still blocked, even though object capture at entry is now good

Updated blocker after this pass:
- not selector-root shape
- not producer symmetry
- not entry-site existence
- the real frontier is now the earlier writer or call chain that populates the `consumer_asset_lookup_entry` wrapper fields `[-3/-1/+3]` before selector-root materialization

Correction / continuation:

I implemented the entry-wrapper provenance pass directly in `fx_runtime_probe_hook.cpp`, rewired `run_consumer_semantic_transition_compare.ps1` so the writepath lane treats `entry_wrapper_*` as success instead of stale selector-root write events, and reran the ownership-edge harness. The authoritative live archive is `20260403_192823`.

What this pass proved:
- the stale "selector-root writer" blocker is dead for real
- on the same dedicated writepath lane, both starter and probe now recover `consumer_asset_lookup_entry` with real branch-local wrapper state
- the branch split is already prepopulated at entry on both sides; there was no first-step mutation of `[-3/-1/+3]` in the recovered entry flow

Starter / true pre-grant branch from `20260403_192823/equip_hold_begin`:
- inject trigger: `[bo3_rev][player_state] stage=pre_grant`
- first hit: `consumer_asset_lookup_entry`
- wrapper base: `0x5FA28FE8`
- `EDI[-3] = 0x00000012`
- `EDI[-1] = 0x033ED204`
- `EDI[+3] = 0x033F3880`
- caller family captured from `entry_wrapper_prepopulated`

Probe / post-switch branch from `20260403_192823/post_switch`:
- inject trigger: `[bo3_rev][player_state] stage=post_switch`
- first hit: `consumer_asset_lookup_entry`
- wrapper base: `0x5FA28FE8`
- `EDI[-3] = 0x00000012`
- `EDI[-1] = 0x033F0304`
- `EDI[+3] = 0x033F4E40`
- repeated step snapshots stayed unchanged through the recovered entry flow
- caller family captured from `entry_wrapper_prepopulated`

Concrete statement the repo now supports:
- the earliest live starter/probe branch split is already prepopulated at `consumer_asset_lookup_entry`
- the discriminative wrapper fields are now narrowed to `EDI[-1]` and `EDI[+3]`
- `EDI[-3] = 0x00000012` is shared/structural on the recovered lane
- selector-root and the later child/descriptor chain are downstream materialization of this already-split wrapper state

The current blocker moved earlier again:
- not entry-wrapper existence
- not starter/probe symmetry at the entry site
- not selector-root provenance
- the real frontier is now the earlier producer/caller path that arrives with `EDI[-1]` and `EDI[+3]` already branch-shaped before or at `consumer_asset_lookup_entry`

Override causality pass:

I implemented a real entry-wrapper override path in `fx_runtime_probe_hook.cpp` and a probe-side matrix runner in `tools/run_entry_wrapper_override_matrix.ps1`. The patch point is now causal, not passive:
- at `consumer_asset_lookup_entry`
- patchable fields:
  - `EDI[-1]`
  - `EDI[+3]`
- supported cases:
  - control
  - patch `-1` only
  - patch `+3` only
  - patch both

The first matrix archive is:
- `_build/bo3_rev_idg_probe/entry_wrapper_override_matrix/20260403_195037/entry_wrapper_override_matrix_summary.json`

I then hardened it so a case only counts if its prepatch tuple matches the intended probe reference, and reran it:
- `_build/bo3_rev_idg_probe/entry_wrapper_override_matrix/20260403_195702/entry_wrapper_override_matrix_summary.json`

What this pass proved:
- the earliest recovered branch split is now patchable in live code
- `entry_wrapper_override_apply` fires and can transplant starter values onto the live entry wrapper
- but the supposed probe-side control tuple is not stable enough yet for a clean causal animation conclusion

Expected probe reference from the earlier authoritative probe-side run:
- `EDI[-1] = 0x033F0304`
- `EDI[+3] = 0x033F4E40`

What the gated rerun actually observed across attempts:
- control:
  - attempt 1: `[-1]=0x033ED204`, `[+3]=0x033F3880`
  - attempt 2: `[-1]=0x033ED240`, `[+3]=0x033F3790`
- patch `-1` only:
  - both attempts: prepatch `[-1]=0x033F0380`, `[+3]=0x033F4D50`
- patch `+3` only:
  - both attempts: prepatch `[-1]=0x033ED240`, `[+3]=0x033F3790`
- patch both:
  - attempt 1: prepatch `[-1]=0x033ED240`, `[+3]=0x033F3580`
  - attempt 2: prepatch `[-1]=0x033F0380`, `[+3]=0x033F4D50`

Important meaning:
- the override machinery works
- the recovered frontier is genuinely writable
- but the live post-switch producer branch is not deterministic enough yet to use as a clean baseline
- so the current blocker is no longer "can we patch the earliest split?"
- it is "how do we normalize or bucket the earlier producer branch so the override matrix compares against one stable control family?"

Visible downstream result so far:
- no stable selector-root materialization surfaced in these override runs
- no clean visible animation win yet
- first-raise/tag logs still stay on stock-shell behavior and often remain `<undef>` on the important tag surface

Updated blocker after the override pass:
- not whether `EDI[-1]` / `EDI[+3]` are patchable
- not whether entry-wrapper override can be injected live
- the missing piece is a stable, normalized producer/branch identity before `consumer_asset_lookup_entry`, likely gated by caller family / shell family / earlier producer tuple
## 71) entry_wrapper_override_post_switch: family-normalized override matrix is causally negative (2026-04-03)

I tightened the probe-side override matrix so it no longer hard-coded one rare raw tuple. The runner now:

- refreshes `probe_entry_wrapper_family_buckets_summary.json` before the matrix,
- can consume a recommended control tuple from the offline bucket pass,
- and retries each case until the prepatch entry wrapper matches one approved control family.

The authoritative normalized matrix is:

- `_build/bo3_rev_idg_probe/entry_wrapper_override_matrix/20260403_201531/entry_wrapper_override_matrix_summary.json`

What this run proved:

- the stable accepted probe-side control family is now real, not inferred:
  - prepatch tuple:
    - `minus3 = 0x00000012`
    - `minus1 = 0x033F0304`
    - `plus3 = 0x033F4E40`
- control accepted on attempt 1:
  - `entry_wrapper_prepopulated ... minus3=0x00000012 minus1=0x033F0304 plus3=0x033F4E40`
- `patch_minus1_only` accepted on attempt 4:
  - prepatch still matched the same control tuple,
  - then patched to:
    - `minus1 = 0x033ED204`
    - `plus3 = 0x033F4E40`
- `patch_plus3_only` accepted on attempt 2:
  - prepatch still matched the same control tuple,
  - then patched to:
    - `minus1 = 0x033F0304`
    - `plus3 = 0x033F3880`
- `patch_both` accepted on attempt 1:
  - prepatch still matched the same control tuple,
  - then patched to:
    - `minus1 = 0x033ED204`
    - `plus3 = 0x033F3880`

The important conclusion is no longer ambiguous:

- the wrapper override path is real,
- the control family can be normalized,
- and even inside one stable accepted probe family, transplanting starter values into `EDI[-1]` and/or `EDI[+3]` does **not** produce downstream selector-root materialization on this lane.

Observed downstream/visible result across all accepted cases:

- `joined_surface_seen = false`
- `selector_state = null`
- no `idle_begin`
- no visible custom-animation win
- first-person behavior still stays on the stock survivor shell / flat-tag path

So the stale blocker is dead:

- it is **not** “the wrapper matrix was polluted by mixed control families”
- it is **not** “we still need a cleaner entry-wrapper override run before drawing conclusions”

The current frontier moved earlier again. The earliest recovered branch split at `consumer_asset_lookup_entry` is patchable, but it is not sufficient by itself to drive downstream selector materialization. The next practical control point is now earlier than the wrapper fields themselves: the producer/caller path that populates them before or at entry.

## 72) producer_compact_override_post_switch: producer->render bridge is real; old "hit2" cases were false until target-hit support (2026-04-03)

I pushed the earlier producer-side compact override lane far enough to get a real producer->render bridge, then corrected one bad assumption in the override matrix.

What changed in the probe/runner:

- fixed a real deadlock in `ProducerCompactOverrideFocus`:
  - the late follow-on render armer was trying to take `g_state_mutex` from inside the breakpoint path that already held it,
  - that deadlocked immediately after the first asset-lookup hit and silently prevented downstream render traces from arming,
- changed `ProducerCompactOverrideFocus` to arm `consumer_render_table` concurrently from startup instead of relying only on late follow-on arming,
- added true `target_hit` support to `active_producer_class_override.txt` and the native producer override path,
- corrected the old false "hit2" assumption:
  - before this pass, so-called `patch_plus5_hit2` / `patch_plus5_plus6_hit2` cases were not actually hit-2 overrides,
  - the native override path hard-stopped at `hit == 1`,
  - so those old matrix cases were mislabeled and never touched the downstream-producing second class family,
- reduced heavy asset-lookup snapshot work in `ProducerCompactOverrideFocus` so the lane can survive farther into post-switch render on more runs.

The first authoritative control bridge after the deadlock fix is:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_210956/post_switch`

That run proves a real same-run producer->render bridge on the post-switch probe lane:

- `consumer_render_table` now arms and hits from startup:
  - `render_hit_count = 9`
  - `joined_surface_seen = true`
- later in the same run, `consumer_asset_class_lookup` also hits twice:
  - hit 1:
    - `class = 0x2D829A7C`
    - `class_head = 0x2D82D440`
    - `class_plus_5 = 0x00020105`
    - `class_plus_6 = 0x00000201`
  - hit 2:
    - `class = 0x2F45088C`
    - `class_head = 0x2F455374`
    - `class_plus_5 = 0x01050105`
    - `class_plus_6 = 0x00000201`
- the post-producer downstream render family then lands in that same later heap family:
  - `consumer_render_hit_summary hit=9 ... owning=0x2F455258 render=0x2F455338 render_plus_8=0x2F455340 lookup=0x2F4A9550`
  - that is the first strong live evidence on this lane that the later producer class/class_head family is feeding downstream render-side materialization.

That is a substantive shift:

- the producer lane is no longer isolated from downstream render,
- and the stale "we still need to prove producer-side state ever reaches render-side objects" branch is dead.

I then enabled **true** hit-targeted producer compact overrides:

- `target_hit=1` or `target_hit=2` can now be set in `active_producer_class_override.txt`,
- the native log now records `producer_compact_override_apply hit=<n> target_hit=<n> ...`,
- the matrix runner writes `target_hit=` per case instead of only pretending to distinguish hit 1 vs hit 2.

Current blocker after this pass:

- the corrected hit-2 patch lane is still operationally nondeterministic:
  - some runs stay on the render surface and never recover `consumer_asset_class_lookup`,
  - some runs recover asset lookup but still do not stay alive long enough to give a clean post-patch downstream selector/render comparison,
  - one successful retry (`20260403_211909`) recovered asset lookup again on the true hit-2 override lane, but the archive still cut off before a clean post-patch producer summary / downstream joined-surface comparison was fully serialized.

So the frontier moved, but in a useful way:

- not back to selector-root,
- not back to wrapper override,
- now specifically to a **stable** hit-2 producer compact override run that preserves:
  - producer compact apply,
  - post-producer render hits,
  - and downstream joined/selector materialization in the same archive.

The important stale conclusion to retire is:

- old `patch_plus5_hit2` / `patch_plus5_plus6_hit2` results are **not authoritative** unless they come from the new `target_hit=2` path.

## 73) producer_compact_override_post_switch: later producer-family ordinal is not stable (2026-04-03)

One more correction came out of the next live control runs after the producer->render bridge was fixed.

The downstream-producing compact family is **not** stably "hit 2" on this lane.

Evidence:

- in `20260403_210956/post_switch`, the producer lane recovered:
  - hit 1:
    - `class_plus_5 = 0x00020105`
    - `class_plus_6 = 0x00000201`
  - hit 2:
    - `class_plus_5 = 0x01050105`
    - `class_plus_6 = 0x00000201`
  - and the later render family then landed in that later `0x2F455xxx` heap family
- but in a later clean control run:
  - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_215111/post_switch`
  - the lane recovered:
    - `consumer_asset_lookup_hit_summary hit=1 ... class=0x2F3C95E8`
    - `consumer_asset_lookup_hit_summary hit=2 ... class=0x2F3C95E8`
    - `consumer_asset_lookup_hit_summary hit=3 ... class=0x2F87175C`
  - and the later render family then moved to:
    - `consumer_render_hit_summary hit=2 ... owning=0x2F873890 render=0x2F873970 render_plus_8=0x2F873978 lookup=0x2F2359D0`

So the corrected model is:

- the important producer-side target is **not** "always hit 2",
- it is the **last producer family before the later downstream render materialization** on this lane.

That is a meaningful correction because it changes the causal patch target:

- a fixed `target_hit=2` override is not sufficient as a permanent solution,
- the real producer override path likely needs either:
  - later-hit capture/patching,
  - or a relative target like "last producer family before render" rather than a fixed ordinal.

Related tooling improvements landed in the same pass:

- `inject_latest.ps1` now resolves the **newest** matching process instead of the oldest bootstrapper, which was important on this machine because stale access-denied bootstrapper leftovers were polluting probe injection,
- `ProducerCompactOverrideFocus` now records more producer states (`hit <= 4`) so later producer-family transitions can be observed on this lane.

## 74) producer_compact_override_post_switch: first-distinct producer-family override is live, but compact-only patching is still causally insufficient (2026-04-03)

I pushed the producer override lane one step farther by removing the fixed-hit assumption in the native patch path.

What changed:

- `fx_runtime_probe_hook.cpp` now supports a relative producer override mode:
  - `target_mode=first_distinct_after_initial`
- the native producer override no longer needs a hard-coded ordinal on this lane:
  - it captures the initial producer family on hit 1,
  - then patches the **first later distinct** `class/class_head` family that appears after that baseline,
  - which matches both previously recovered patterns:
    - `20260403_210956/post_switch` (later family on hit 2)
    - `20260403_215111/post_switch` (later family on hit 3)
- I added a focused compare harness:
  - `tools/run_producer_first_distinct_causal_compare.ps1`
- I also added an offline bridge summary:
  - `_build/bo3_rev_idg_probe/producer_first_distinct_causal_compare/20260403_221841/producer_first_distinct_render_bridge_summary.json`

The first normalized control recovered by the new harness is:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_222038/post_switch`

That control proves the new relative target is real:

- initial family:
  - `class_plus_5 = 0x000A0105`
  - `class_plus_6 = 0x00000201`
- first later distinct family:
  - `class_plus_5 = 0x010D0105`
  - `class_plus_6 = 0x00000201`
- later render still lands in that later producer heap family:
  - `class_head = 0x2F46D594`
  - last render:
    - `owning=0x2F46D418`
    - `render=0x2F46D4F8`
    - `lookup=0x2F4A9550`

So the stale fixed-hit blocker is dead:

- the override now follows the first later producer family even when its ordinal moves.

I then used that mode to patch the first later distinct producer family toward the starter compact pair:

- target compact pair:
  - `class_plus_5 = 0x01150105`
  - `class_plus_6 = 0x00000201`

The clearest effective change run is:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_222434/post_switch`

What happened there:

- first later distinct family before patch:
  - `class = 0x2F2D088C`
  - `class_head = 0x2F2D5374`
  - `old_class_plus_5 = 0x01050105`
  - `old_class_plus_6 = 0x00000201`
- patch applied through the new relative mode:
  - `new_class_plus_5 = 0x01150105`
  - `new_class_plus_6 = 0x00000201`
- downstream still stayed on the same later render family:
  - `owning=0x2F2D5258`
  - `render=0x2F2D5338`
  - `lookup=0x2F329550`
- `joined_surface_seen = true`
- no visible idle or custom-animation win surfaced

The new offline bridge summary makes the current conclusion explicit:

- `_build/bo3_rev_idg_probe/producer_first_distinct_causal_compare/20260403_221841/producer_first_distinct_render_bridge_summary.json`
- conclusion:
  - `first_distinct_compact_patch_changed_compact_pair_but_render_bridge_is_not_consistently_preserved`

That is the useful causal answer from this pass:

- patching the **compact** fields (`class_plus_5` / `class_plus_6`) on the first later producer family is now a real live control surface,
- but compact-only patching is still not sufficient to force a stable downstream render takeover or a visible custom-animation change.

So the frontier moved again, in a useful way:

- not back to selector-root,
- not back to entry-wrapper override,
- and not back to fixed-hit producer patching.

The next practical target is now narrower:

- the **pointer-family / projection-base** side of that same later producer family:
  - `class`
  - `class_head`
  - `class_plus_3`
  - `class_plus_4`
- because the compact-only side has now been causally tested and is too weak by itself.

## 75) producer_pointer_family_override_matrix: coherent pointer-family override is live, and pointer-side patching is the first producer-side change that perturbs the later render family (2026-04-03)

I implemented a new live matrix on the same `producer_compact_override_post_switch` / `first_distinct_after_initial` lane, but moved the patch surface from compact-only state to the producer pointer-family side.

Files changed:

- `native/fx_runtime_probe/fx_runtime_probe_hook.cpp`
- `tools/run_consumer_semantic_transition_compare.ps1`
- `tools/run_producer_pointer_family_override_matrix.ps1`
- `tools/build_servant_minimal_anim_runtime.ps1`

What changed in the native probe:

- `ProducerCompactOverrideConfig` now supports live pointer-family patch modes:
  - `patch_pointer_swap_34`
  - `patch_pointer_family_from_initial`
- the first recovered producer family now stores its initial pointer-family baseline:
  - `class_head`
  - `class_plus_2`
  - `class_plus_3`
  - `class_plus_4`
- the first later distinct producer family can now be patched by role in the current run:
  - swap its local `class_plus_3` / `class_plus_4`
  - or transplant the current run's initial pointer-family (`class_head`, `+2`, `+3`, `+4`)
  - optionally combine that with compact patching on `class_plus_5`

The new live matrix harness is:

- `_build/bo3_rev_idg_probe/producer_pointer_family_override_matrix/20260403_225136/producer_pointer_family_override_matrix_summary.json`

Important runtime/build correction made in the same pass:

- `run_consumer_semantic_transition_compare.ps1` now uses `AnimProbePhase=idle_first_raise` on this transition instead of the invalid old `producer_compact` token
- `build_servant_minimal_anim_runtime.ps1` now accepts the newer probe modes:
  - `bootstrap_guard_only`
  - `xanim_asset_lookup_focus`
  - `producer_compact_override_focus`
  - `class_family_materialization_writepath`

### 75.1 Clean normalized control

Accepted control:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_225505/post_switch`

Recovered control family:

- initial family:
  - `class = 0x2F3495E8`
  - `class_head = 0x2F34B65C`
  - `class_plus_2 = 0x2F34B27C`
  - `class_plus_3 = 0x2F349608`
  - `class_plus_4 = 0x2F34B2F0`
  - `class_plus_5 = 0x00010101`
  - `class_plus_6 = 0x00000003`
- first later distinct family:
  - `class = 0x2EE10334`
  - `class_head = 0x2EE123BC`
  - `class_plus_2 = 0x2ED79400`
  - `class_plus_3 = 0x2ED7EBD0`
  - `class_plus_4 = 0x2EE10354`
  - `class_plus_5 = 0x00060101`
  - `class_plus_6 = 0x00000003`
- later render family:
  - `owning = 0x2EE12294`
  - `render = 0x2EE12374`
  - `lookup = 0x44AF8520`

So on this lane:

- the later render family still normally lands inside the later producer heap family,
- and the normalized control bucket is now explicit for pointer-family retests.

### 75.2 Coherent pointer-family + compact override is real on the normalized bucket

Accepted coherent full-family case:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_230521/post_switch`

That run proves the later producer family can be patched coherently by role:

- patch target:
  - first later distinct family on hit 3
  - `class = 0x2EE50334`
  - old `class_head = 0x2EE523BC`
  - old `class_plus_2 = 0x2EDB9400`
  - old `class_plus_3 = 0x2EDBEBD0`
  - old `class_plus_4 = 0x2EE50354`
  - old `class_plus_5 = 0x00060101`
- applied coherent override:
  - new `class_head = 0x2F38B65C`
  - new `class_plus_2 = 0x2F38B27C`
  - new `class_plus_3 = 0x2F389608`
  - new `class_plus_4 = 0x2F38B2F0`
  - new `class_plus_5 = 0x01150105`

The important causal result:

- the later producer family carried the transplanted pointer-family and compact state in the same live run,
- and a later render family still materialized:
  - `owning = 0x2EE522C4`
  - `render = 0x2EE523A4`
  - `lookup = 0x44B3DED0`

So the stale branch is dead:

- pointer-family patching on the later producer family is now a real live control surface,
- not just an offline role model.

But the visible win is still not there:

- no joined selector-root surface survived in this accepted coherent run,
- no visible custom-animation takeover surfaced.

### 75.3 Pointer-side patching is the first producer-side change that perturbs render-family outcome

Even though the matrix did not recover every case inside the normalized bucket, the exploratory accepted runs are still useful.

`pointer_swap_only`:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_230154/post_switch`
- patch applied on the later family:
  - old `class_plus_3 = 0x2F4308AC`
  - old `class_plus_4 = 0x2F432C40`
  - new `class_plus_3 = 0x2F432C40`
  - new `class_plus_4 = 0x2F4308AC`
- later render no longer stayed on that later producer family page:
  - render moved to `0x30BF7E78`

`pointer_base_only`:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_230227/post_switch`
- patch applied on the later family:
  - old `class_head = 0x2F28D594`
  - new `class_head = 0x2D65D958`
  - old `class_plus_3 = 0x2F2708AC`
  - new `class_plus_3 = 0x2D649A9C`
  - old `class_plus_4 = 0x2F28A808`
  - new `class_plus_4 = 0x2D65BD44`
- later render also diverged:
  - render moved to `0x2F26D52C`

So the useful causal conclusion from this pass is:

- compact-only patching can change producer compact state without a render-family takeover,
- but pointer-side patching is the first producer-side intervention that measurably perturbs the later render-family outcome.

That is a major shift even though visible custom animation is still not won.

### 75.4 Current blocker after the pointer-family matrix

The blocker is no longer:

- compact-only producer patching
- fixed-hit targeting
- selector-root tracing
- or "can the pointer-family be patched live"

It is now narrower:

- get a stable same-bucket pointer-side accepted run (`pointer_swap_only` and `pointer_base_only`) against the normalized control family from `20260403_225505`,
- or move one level earlier and recover the writer/provenance for the later producer family's:
  - `class_head`
  - `class_plus_2`
  - `class_plus_3`
  - `class_plus_4`

Short version:

- the later producer family's pointer-family side is now proven to be a real live control surface,
- and it is the first producer-side patch surface that perturbs the later render-family result,
- but the stable visible-animation takeover still needs either:
  - same-bucket pointer-side causality on a clean control family,
  - or an earlier writer/provenance hook on the class-family projection-base fields.

## 76) producer_pointer_ablation_matrix: current-build ablation narrows the likely minimal driver to `class_plus_2 + class_plus_3 + class_plus_4` (2026-04-04)

I followed the broad pointer-family matrix with a tighter ablation pass on the same later producer family.

New runner:

- `tools/run_producer_pointer_ablation_matrix.ps1`

Key native extension:

- `ProducerCompactOverrideConfig` now supports granular initial-family transplants for:
  - `patch_class_head_from_initial`
  - `patch_class_plus2_from_initial`
  - `patch_class_plus3_from_initial`
  - `patch_class_plus4_from_initial`

This pass also exposed an important correction:

- the old canonical control from `20260403_225505/post_switch` did not reproduce under the newer native build `fx_runtime_probe_hook_20260403_232923.dll`
- under the newer probe build, the strongest recovered control bucket was instead:
  - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_233119/post_switch`
  - initial family:
    - `class_plus_5 = 0x00120105`
    - `class_plus_6 = 0x00000201`
  - first later distinct family:
    - `class_plus_5 = 0x01150105`
    - `class_plus_6 = 0x00000201`

So the broad ablation matrix against the old control source:

- `_build/bo3_rev_idg_probe/producer_pointer_ablation_matrix/20260403_232941/producer_pointer_ablation_matrix_summary.json`

did not produce formally accepted cases, but the later same-build exploratory attempts are still useful because they cluster into a newer stable bucket.

### 76.1 Negative controls inside the newer current-build bucket

Inside the newer bucket with:

- initial:
  - `class_plus_5 = 0x00020105`
  - `class_plus_6 = 0x00000201`
- later distinct:
  - `class_plus_5 = 0x01050105`
  - `class_plus_6 = 0x00000201`

three different patch sets still failed to push render out of the normal later-family page:

`class_head_only`

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_233546/post_switch`
- patch:
  - `old_class_head = 0x2F2A5374`
  - `new_class_head = 0x2D67D440`
- unchanged:
  - `class_plus_2`
  - `class_plus_3`
  - `class_plus_4`
  - `class_plus_5`
- later render still remained in the later producer page:
  - `render = 0x2F2A5338`

`plus2_only`

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_233706/post_switch`
- patch:
  - `old_class_plus_2 = 0x2FDE2BCC`
  - `new_class_plus_2 = 0x2E1BBB20`
- unchanged:
  - `class_head`
  - `class_plus_3`
  - `class_plus_4`
  - `class_plus_5`
- later render still remained in the later producer page:
  - `render = 0x2FDE5338`

`class_head_plus3_plus4`

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_234344/post_switch`
- patch:
  - `old_class_head = 0x2F455374`
  - `new_class_head = 0x2D82D440`
  - `old_class_plus_3 = 0x2F4508AC`
  - `new_class_plus_3 = 0x2D829A9C`
  - `old_class_plus_4 = 0x2F452C40`
  - `new_class_plus_4 = 0x2D82BB94`
- unchanged:
  - `class_plus_2`
  - `class_plus_5`
- later render still remained in the later producer page:
  - `render = 0x2F455338`

That is the useful negative result:

- `class_head` alone is not enough
- `class_plus_2` alone is not enough
- `class_head + class_plus_3 + class_plus_4` is still not enough

### 76.2 Positive divergence candidate inside the same bucket

`class_plus_2 + class_plus_3 + class_plus_4`

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_000425/post_switch`
- patch:
  - `old_class_plus_2 = 0x2F702BCC`
  - `new_class_plus_2 = 0x2DADBB20`
  - `old_class_plus_3 = 0x2F7008AC`
  - `new_class_plus_3 = 0x2DAD9A9C`
  - `old_class_plus_4 = 0x2F702C40`
  - `new_class_plus_4 = 0x2DADBB94`
- unchanged:
  - `class_head`
  - `class_plus_5`
  - `class_plus_6`

Important result:

- later render diverged out of the ordinary later producer page:
  - `render = 0x30EC7E78`
  - `owning = 0x30EC7D98`
  - `lookup = 0x38371D70`

So within the same newer bucket, this is the strongest current minimal-driver evidence:

- `class_plus_2 + class_plus_3 + class_plus_4` are sufficient to perturb later render-family outcome,
- while `class_head` is not required for that perturbation on the same bucket.

### 76.3 Secondary current-build observations

`plus4_only`

- `_build/bo3_rev_idg_probe/producer_pointer_ablation_matrix/20260404_000057/producer_pointer_ablation_matrix_summary.json`
- produced mixed same-build runs:
  - some later render stayed on the later producer page:
    - `render = 0x2FC94294`
    - `render = 0x2FD65338`
  - no clean same-bucket accepted win was recovered

So `plus4_only` is not yet the strongest explanation.

`full_pointer_family_plus5`

- broad current-build evidence still shows this can perturb render strongly:
  - e.g. `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260403_235403/post_switch`
  - later render:
    - `render = 0x2F37D52C`
- but that is not a minimal explanation because it patches:
  - `class_head`
  - `class_plus_2`
  - `class_plus_3`
  - `class_plus_4`
  - `class_plus_5`

### 76.4 Current best interpretation after the ablation pass

The current best model is now:

- compact-only state is still secondary
- `class_head` is not the minimal driver by itself
- `class_plus_2` is not sufficient by itself
- the best current minimal driver candidate for later render-family divergence is:
  - `class_plus_2 + class_plus_3 + class_plus_4`

That is a real narrowing.

### 76.5 Current blocker after the ablation pass

The blocker is now more specific again:

- confirm `class_plus_2 + class_plus_3 + class_plus_4` on a cleaner same-bucket lane with downstream selector-state recovery,
- or move one level earlier and recover the writer/provenance for those three producer projection-base fields.

Short version:

- the later producer pointer-family is still the right frontier,
- and the current best minimal driver is no longer vague:
  - it looks like `class_plus_2 + class_plus_3 + class_plus_4`,
- which means the next live step should stay on those three fields, not widen back out.
## 77) same_process_trio_transplant: same-process starter->probe trio transplant is real, `+2/+3/+4` preserves joined-surface while `+3/+4` alone can still move later render (2026-04-04)

This pass moved the later producer-family lane forward in a way that matters more than another offline slice.

Two practical/runtime blockers had to be fixed first:

- `tools/restart_t6_probe_cycle.ps1` now syncs `maps/mp/gametypes_zm/*.txt` into the active `bo3_rev` mod lane again
  - the same-process lane had started failing before gameplay script stages because the mod-side raw gametype txts were missing
- `run_consumer_semantic_transition_compare.ps1` now injects the `producer_same_process_trio_transplant` lane on the real `pre_grant` player-state trigger instead of raw launch injection
  - this keeps starter-side and probe-side producer recovery in the same gameplay process

I also extended:

- `native/fx_runtime_probe/fx_runtime_probe_hook.cpp`
  - same-process compact override mode now supports:
    - `patch_class_plus5_from_initial`
    - `arm_render_from_startup`
- `tools/run_same_process_trio_transplant_matrix.ps1`
  - accepts `CaseFilter`
  - accepts `ApprovedControlSummaryPath`
  - can reuse an already-approved control bucket and rerun only unresolved cases

### 77.1 First real same-process control bucket

Authoritative first same-process matrix:

- `_build/bo3_rev_idg_probe/same_process_trio_transplant_matrix/20260404_013746/same_process_trio_transplant_matrix_summary.json`

Approved control:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_013747/same_process`

Recovered same-process control family:

- starter-side initial family:
  - `class = 0x2D723880`
  - `class_head = 0x2D725734`
  - `class_plus_2 = 0x2D71BB20`
  - `class_plus_3 = 0x2D719A9C`
  - `class_plus_4 = 0x2D7238A0`
  - `class_plus_5 = 0x000F0105`
  - `class_plus_6 = 0x00000201`
- first later distinct probe-side family:
  - `class = 0x2F34DD64`
  - `class_head = 0x2F350D8C`
  - `class_plus_2 = 0x2F342BCC`
  - `class_plus_3 = 0x2F3408AC`
  - `class_plus_4 = 0x2F34DD84`
  - `class_plus_5 = 0x01120105`
  - `class_plus_6 = 0x00000201`
- later render:
  - `owning = 0x30B07D2C`
  - `render = 0x30B07E0C`
  - `lookup = 0x33045680`
- `joined_surface_seen = true`

This killed the cross-run-pointer confounder for the trio fields:

- starter-side `+2/+3/+4` can now be captured and transplanted into the later probe-side family inside the same live process

### 77.2 `same_process_plus234`: same-process `+2/+3/+4` transplant is accepted on the same bucket and preserves joined-surface while moving later render

Authoritative accepted run:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_013814/same_process`

Patch applied on the first later distinct producer family:

- old:
  - `class_plus_2 = 0x2F422BCC`
  - `class_plus_3 = 0x2F4208AC`
  - `class_plus_4 = 0x2F42DD84`
- new from the same-process starter family:
  - `class_plus_2 = 0x2D7FBB20`
  - `class_plus_3 = 0x2D7F9A9C`
  - `class_plus_4 = 0x2D8038A0`
- unchanged:
  - `class_head`
  - `class_plus_5 = 0x01120105`
  - `class_plus_6 = 0x00000201`

Important result:

- `joined_surface_seen = true`
- later render moved from the control family:
  - control:
    - `render = 0x30B07E0C`
  - patched:
    - `render = 0x30BE7E0C`
    - `owning = 0x30BE7D2C`
    - `lookup = 0x33125680`

This is the strongest current same-process causal result:

- the same-process starter->probe transplant of `class_plus_2 + class_plus_3 + class_plus_4` is sufficient to change the later render family,
- and it does so without killing the joined-surface on the accepted control bucket.

### 77.3 `same_process_plus34_only`: same-process `+3/+4` alone is enough to perturb later render, but accepted same-bucket runs do not preserve joined-surface

This was rerun twice:

- `_build/bo3_rev_idg_probe/same_process_trio_transplant_matrix/20260404_014612/same_process_trio_transplant_matrix_summary.json`
- `_build/bo3_rev_idg_probe/same_process_trio_transplant_matrix/20260404_015317/same_process_trio_transplant_matrix_summary.json`

Authoritative same-bucket accepted run:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_015904/same_process`

Accepted same-bucket patch:

- old:
  - `class_plus_2 = 0x2FBF2BCC`
  - `class_plus_3 = 0x2FBF08AC`
  - `class_plus_4 = 0x2FBFDD84`
  - `class_plus_5 = 0x01120105`
- new:
  - `class_plus_2 = 0x2FBF2BCC` (unchanged)
  - `class_plus_3 = 0x2DFC9A9C`
  - `class_plus_4 = 0x2DFD38A0`
  - `class_plus_5 = 0x01120105` (unchanged)

Important result:

- later render still moved:
  - `owning = 0x2FC00BD4`
  - `render = 0x2FC00CB4`
  - `lookup = 0x2FC493F0`
- but `joined_surface_seen = false`
- and accepted same-bucket `+3/+4` runs did not recover a stable downstream selector/joined surface

There were exploratory `+3/+4` runs with `joined_surface_seen = true`, but those were on different later compact families such as `0x01050105`, so they are not authoritative against the normalized `0x01120105` control bucket.

This is now the best current role split:

- `class_plus_3 + class_plus_4` are already sufficient to perturb later render-family outcome
- `class_plus_2` is not required for that perturbation
- but `class_plus_2` currently looks necessary to keep the downstream joined/selector surface alive on the same control bucket

### 77.4 `same_process_plus234_plus5`: same-process `+5` is still not cleanly recovered on the normalized control bucket

Focused rerun:

- `_build/bo3_rev_idg_probe/same_process_trio_transplant_matrix/20260404_014612/same_process_trio_transplant_matrix_summary.json`

What it proved:

- same-process `+2/+3/+4/+5` patching is operationally real
- it can produce strong downstream divergence, for example:
  - `render = 0x33E82190`
  - selector-style state with:
    - `plus3 = 0x2DFBEDD0`
    - `plus4 = 0x2DFC5774`
    - `plus5 = 0x00120105`
- but it still did not recover a clean accepted same-bucket case against the normalized `0x01120105` later-family control

So `+5` remains secondary in the current same-process evidence:

- it may still matter as a family-code discriminator,
- but the current visible/render causality is now more strongly anchored on the pointer-side trio than on compact `+5` alone.

### 77.5 Current best interpretation after the same-process trio pass

The stale branch "we still need cross-run starter values to test trio causality" is now dead.

What is now established:

- same-process starter->probe trio transplant is real
- `class_plus_2 + class_plus_3 + class_plus_4` changes later render while preserving joined-surface
- `class_plus_3 + class_plus_4` alone can still change later render
- but accepted same-bucket `+3/+4` runs do not preserve joined-surface
- `class_plus_5` still does not have a clean same-bucket accepted win on top of the trio

So the current best role model is:

- `class_plus_3 + class_plus_4`
  - strongest direct drivers of later render divergence
- `class_plus_2`
  - likely topology / binding-preservation field needed to keep joined selector-state alive
- `class_plus_5`
  - still a secondary compact family-code candidate, not the primary render-takeover driver

### 77.6 Current blocker

Visible custom animation is still not won.

But the blocker is narrower again:

- either recover a clean same-bucket `same_process_plus234_plus5` run,
- or move earlier and recover writer/provenance for the later producer family's:
  - `class_plus_2`
  - `class_plus_3`
  - `class_plus_4`

The shortest remaining high-value frontier is:

- determine whether `class_plus_2` is the field that preserves downstream selector-state while `class_plus_3/+4` drive render takeover,
- or prove that the real control point is earlier than the already-materialized later producer trio.

## 78) same_process_trio_transplant: family-matched control recovery shows `+234+5` is recoverable on the `0x00120105 -> 0x01150105` bucket, but it still drops joined-surface (2026-04-04)

I pushed the same-process lane one step farther by removing the stale "one fixed control bucket" assumption.

What changed:

- `tools/run_same_process_trio_transplant_matrix.ps1` now also supports exact compact-family control gating:
  - `RequiredInitialClassPlus5`
  - `RequiredInitialClassPlus6`
  - `RequiredLaterClassPlus5`
  - `RequiredLaterClassPlus6`

This makes it possible to recover a control for the exact starter/probe compact family that a patched case is landing on, instead of judging every later run against the old `0x000F0105 -> 0x01120105` control.

### 78.1 Family-matched control bucket recovered on demand

Authoritative family-matched control:

- `_build/bo3_rev_idg_probe/same_process_trio_transplant_matrix/20260404_020452/same_process_trio_transplant_matrix_summary.json`

Recovered control family:

- initial:
  - `class_plus_2 = 0x2DBABB20`
  - `class_plus_3 = 0x2DBAEDD0`
  - `class_plus_4 = 0x2DBB5774`
  - `class_plus_5 = 0x00120105`
  - `class_plus_6 = 0x00000201`
- first later distinct:
  - `class_plus_2 = 0x2F7D2BCC`
  - `class_plus_3 = 0x2F7D7E90`
  - `class_plus_4 = 0x2F7E0DCC`
  - `class_plus_5 = 0x01150105`
  - `class_plus_6 = 0x00000201`
- later render:
  - `owning = 0x33A720B0`
  - `render = 0x33A72190`
  - `lookup = 0x37514860`
- `joined_surface_seen = true`
- selector candidate:
  - `plus3 = 0x2F7D7E90`
  - `plus4 = 0x2F7E0DCC`
  - `plus5 = 0x01150105`

This is important because it proves the `0x00120105 -> 0x01150105` same-process family is not a one-off patch artifact. A clean control exists for it.

### 78.2 `same_process_plus234_plus5` is now accepted against its own matched control family

Authoritative rerun:

- `_build/bo3_rev_idg_probe/same_process_trio_transplant_matrix/20260404_020534/same_process_trio_transplant_matrix_summary.json`

Accepted same-bucket run:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_020752/same_process`

Patch applied on the later producer family:

- old:
  - `class_plus_2 = 0x2FBE2BCC`
  - `class_plus_3 = 0x2FBE7E90`
  - `class_plus_4 = 0x2FBF0DCC`
  - `class_plus_5 = 0x01150105`
- new from the same-process starter family:
  - `class_plus_2 = 0x2DFBBB20`
  - `class_plus_3 = 0x2DFBEDD0`
  - `class_plus_4 = 0x2DFC5774`
  - `class_plus_5 = 0x00120105`

Important result:

- accepted against the matched `0x00120105 -> 0x01150105` control bucket
- later render changed to:
  - `owning = 0x2FBF41B4`
  - `render = 0x2FBF4294`
  - `lookup = 0x2FC393F0`
- selector candidate changed to:
  - `plus3 = 0x2DFBEDD0`
  - `plus4 = 0x2DFC5774`
  - `plus5 = 0x00120105`
- but:
  - `joined_surface_seen = false`

So the useful causal result is:

- `+234+5` is now fully recoverable on its own correct family-matched control bucket
- it definitely changes downstream render and selector-side state
- but it still collapses the joined selector surface instead of giving a visible custom-animation win

### 78.3 Matched-bucket `same_process_plus234` did not recover the same family cleanly

Focused rerun:

- `_build/bo3_rev_idg_probe/same_process_trio_transplant_matrix/20260404_020917/same_process_trio_transplant_matrix_summary.json`

What happened:

- multiple `same_process_plus234` runs were recovered
- some preserved `joined_surface_seen = true`
- some moved later render strongly
- but none reproduced a clean accepted same-bucket run against the exact `0x00120105 -> 0x01150105` control bucket within the allotted attempts

That means the current evidence is asymmetric:

- on the `0x00120105 -> 0x01150105` family, `+234+5` is recoverable and accepted
- `+234` alone did not cleanly reproduce the same family in the same search window

That is not yet proof that `+5` is required in all cases, but it does mean:

- `+5` is still part of the live family-shaping story on this bucket,
- even though its current effect is destabilizing the joined selector surface rather than helping visible custom animation.

### 78.4 Current best interpretation after the matched-control pass

The model is now:

- `class_plus_3 + class_plus_4`
  - direct render-divergence drivers
- `class_plus_2`
  - likely binding/topology-preservation field
- `class_plus_5`
  - still a real family-code participant
  - but on the matched `0x00120105 -> 0x01150105` bucket it currently appears to retarget the family while collapsing joined-surface

So the stale theory:

- "`+5` is irrelevant once `+2/+3/+4` are correct"

is too strong. The repo no longer supports that.

The better current statement is:

- `+5` is not the primary render-takeover driver,
- but it still affects whether the later producer family lands in the right starter-like family bucket,
- and the current `+234+5` effect is causally real but still too destructive downstream.

### 78.5 Current blocker after the matched-control pass

The visible custom-animation blocker is now narrower again:

- either recover a same-process family-matched patch that preserves:
  - starter-like trio state
  - later render divergence
  - and `joined_surface_seen = true`
- or move earlier and recover writer/provenance for the later producer family's:
  - `class_plus_2`
  - `class_plus_3`
  - `class_plus_4`
  - and possibly `class_plus_5`

The shortest next live question is:

- is `class_plus_5` actively destabilizing joined-surface after the trio transplant,
- or is the real control point earlier, in the writer path that populates the later producer family before patch time?

## 79. Same-process producer writepath shows the later family is already prepopulated at first recovered asset-lookup hit (2026-04-04)

I implemented a trace-only provenance pass for the later distinct producer family in [fx_runtime_probe_hook.cpp](/z:/Games/pluto_t6_full_game/native/fx_runtime_probe/fx_runtime_probe_hook.cpp) and a focused same-process runner in [run_producer_target_family_writepath.ps1](/z:/Games/pluto_t6_full_game/tools/run_producer_target_family_writepath.ps1). The pass uses the same stable same-process lane but stops trying to patch values; it instead single-steps the first later distinct `consumer_asset_class_lookup` family and records whether `class_head/+2/+3/+4/+5/+6` actually mutate there.

Authoritative live artifact:

- `_build/bo3_rev_idg_probe/producer_target_family_writepath/20260404_022949/producer_target_family_writepath_summary.json`

Accepted same-process control run:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_022949/same_process`

Recovered control bucket:

- initial family:
  - `class = 0x2D853880`
  - `class_head = 0x2D855734`
  - `class_plus_2 = 0x2D84BB20`
  - `class_plus_3 = 0x2D849A9C`
  - `class_plus_4 = 0x2D8538A0`
  - `class_plus_5 = 0x000F0105`
  - `class_plus_6 = 0x00000201`
- first later distinct family:
  - `class = 0x2F47DD64`
  - `class_head = 0x2F480D8C`
  - `class_plus_2 = 0x2F472BCC`
  - `class_plus_3 = 0x2F4708AC`
  - `class_plus_4 = 0x2F47DD84`
  - `class_plus_5 = 0x01120105`
  - `class_plus_6 = 0x00000201`

What the new trace proved:

- the first later distinct producer family is recoverable on the same normalized bucket where:
  - `asset_lookup_hit_count = 4`
  - `render_hit_count = 4`
  - `joined_surface_seen = true`
- the provenance tracer arms on the first later distinct producer family:
  - `producer_class_trace_target hit=2`
  - `producer_class_trace_armed`
  - `producer_class_trace_complete`
- within that short live step window:
  - `any_change = false`
  - `class_head_changed = false`
  - `class_plus_2_changed = false`
  - `class_plus_3_changed = false`
  - `class_plus_4_changed = false`
  - `class_plus_5_changed = false`
  - `class_plus_6_changed = false`

That is the important new shift. The later producer family that drives render divergence is not being built in the first recovered `consumer_asset_class_lookup` hit window on this bucket. It arrives there already fully formed.

So the stale next-step theory:

- "recover the writer by staying on the first recovered later producer hit itself"

is now too late on the accepted control bucket.

The better current statement is:

- later producer-family `class_plus_2/+3/+4/+5` is causally important,
- but on the stable same-process control bucket it is already prepopulated by the time the first later distinct `consumer_asset_class_lookup` family is recovered,
- so the writer/provenance frontier has moved earlier than `consumer_asset_class_lookup` itself.

What still remains unresolved:

- which earlier caller / wrapper / pre-entry object produces that later producer family before first recovered hit,
- and whether controlling that earlier producer path is the step that finally yields stable selector takeover and visible custom animation.

## 80. Producer-mode same-process entry recovery shows the boundary is earlier than `consumer_asset_lookup_entry` too (2026-04-04)

After the writepath pass, I pushed the same producer-mode lane one step earlier by arming `consumer_asset_lookup_entry` inside `ProducerCompactOverrideFocus` itself. The updated native probe still supports the later-family write trace, but it now also captures the entry wrapper and stack-return family on the same same-process lane.

The important partial archive is:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_023600/same_process`

This run did **not** recover the later normalized `0x01120105` producer family. But it did recover an earlier boundary that matters:

- `consumer_first_hit = consumer_asset_lookup_entry`
- `entry_wrapper_seen = true`
- `entry_wrapper_prepopulated_seen = true`
- no `entry_wrapper_change`
- no later `consumer_asset_class_lookup` hit in the same run

Recovered entry-wrapper state:

- `base = 0x5F8F9000`
- `minus3 = 0x033F4D50`
- `minus1 = 0x033F0380`
- `plus3 = 0x033F4D50`

Recovered same-run entry stack-return family summary:

- `consumer_asset_lookup_entry|plutonium-bootstrapper-win32.exe:0x00341F6C`
- `consumer_asset_lookup_entry|plutonium-bootstrapper-win32.exe:0x02FF4D50`
- `consumer_asset_lookup_entry|plutonium-bootstrapper-win32.exe:0x02FF0380`
- `consumer_asset_lookup_entry|plutonium-bootstrapper-win32.exe:0x0036EE73`

Meaning:

- the earlier writer/provenance boundary is now confirmed to be earlier than `consumer_asset_class_lookup`
- and on this same-process lane, the recovered `consumer_asset_lookup_entry` wrapper is already prepopulated too
- so the real missing producer is earlier than the first recovered entry wrapper, not just earlier than the first recovered later producer family

That is another stale theory killed:

- "move from later producer family to asset-lookup entry and recover the writer there"

The repo no longer supports that on the recovered same-process entry-first lane. The new frontier is now the caller / stack-return family that feeds the already-prepopulated `consumer_asset_lookup_entry` wrapper before entry executes.

## 81. The entry-first bridge at `consumer_upstream_ret_00341F6C` is real, and it already splits into stable module-pointer families before any later producer family appears (2026-04-04)

I pushed the same-process lane one step further by adding a label-targeted entry-wrapper override path in [fx_runtime_probe_hook.cpp](/z:/Games/pluto_t6_full_game/native/fx_runtime_probe/fx_runtime_probe_hook.cpp) and a live matrix runner in [run_entry_return_bridge_override_matrix.ps1](/z:/Games/pluto_t6_full_game/tools/run_entry_return_bridge_override_matrix.ps1). The important change is that entry-wrapper patching is no longer limited to `consumer_asset_lookup_entry` itself; it can now target a specific upstream return-family label and use module-RVA-based pointer values instead of run-local heap addresses.

The first raw bridge matrix mixed in render-first startup lanes, so I hardened the runner to pin producer mode back onto the entry-first bucket by forcing:

- `target_mode=first_distinct_after_initial`
- `trace_target_family_steps=1`
- `arm_render_from_startup=0`
- `follow_on_render=0`

That correction produced the authoritative bridge bucket summary:

- `_build/bo3_rev_idg_probe/entry_return_bridge_override_matrix/20260404_032806/entry_return_bridge_override_matrix_summary.json`

The important result is structural, even though there is still no visible animation win:

- the same-process lane can be held on `consumer_asset_lookup_entry` as the first hit again
- `consumer_upstream_ret_00341F6C` is a real bridge site between the first recovered entry/asset-lookup pass and the next entry cycle
- before any later producer family appears, the entry-side wrapper already splits into at least two stable module-pointer families

Recovered entry-side families on the corrected bridge lane:

- family A:
  - `minus1 = 0x033F0380`
  - `plus3 = 0x033F4D50`
  - representative archive: `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_032916/same_process`
  - first recovered producer compact on that run:
    - `class_plus_5 = 0x000F0105`
    - `class_plus_6 = 0x00000201`
- family B:
  - `minus1 = 0x033ED240`
  - `plus3 = 0x033F3790`
  - representative archives:
    - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_033027/same_process`
    - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_033627/same_process`
  - first recovered producer compact on those runs:
    - `class_plus_5 = 0x00020105` or `0x000E0105`
    - `class_plus_6 = 0x00000201`

That is the meaningful new narrowing:

- the frontier is no longer just “some caller family earlier than entry”
- the entry-first bridge already shows branch-local module-pointer families before the later producer family exists
- those bridge families correlate with different first recovered producer compact families

The bridge override itself is operational too. In:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_033627/same_process`

the probe logged:

- `consumer_upstream_hit_summary label=consumer_upstream_ret_00341F6C`
- `entry_wrapper_override_apply ... point=consumer_upstream_ret_00341F6C ...`

But that run was already on the alternate `0x033ED240 / 0x033F3790` family, so the patch was a no-op:

- `old_minus1/new_minus1` or `old_plus3/new_plus3` already matched the target module-RVA family

So the stale next-step theory:

- "patch a fixed alternate bridge family without bucketing the bridge itself"

is now dead too.

What is now actually established:

- `consumer_upstream_ret_00341F6C` is a real causal boundary between the first entry/asset-lookup cycle and whatever later producer family comes next
- the bridge bucket itself has at least two stable pointer families:
  - `0x02FF0380 / 0x02FF4D50`
  - `0x02FED240 / 0x02FF3790`
- those bridge families already shape the first recovered producer compact family before any later distinct producer family is recovered

Current best frontier after this pass:

- not later producer-family value patching
- not entry-wrapper patching at first entry
- the normalized bridge family at `consumer_upstream_ret_00341F6C`, and then the writer/provenance that emits one of those two module-pointer families before the later producer family ever appears

## 82. Bridge-family `plus3` is now the strongest recovered upstream causal driver of first producer-family selection (2026-04-04)

I stayed on the normalized `consumer_upstream_ret_00341F6C` bridge family and hardened the live bridge runner instead of jumping earlier again.

Tooling corrections:

- `tools/run_entry_return_bridge_override_matrix.ps1` now hard-gates on one required bridge family
- it can optionally arm `follow_on_render`
- it records a post-patch bridge snapshot so the comparison uses the patched bridge family, not the pre-entry snapshot
- it also supports case filtering cleanly for narrow reruns

### Family A normalized bucket: accepted causal bridge flip

Authoritative bucketed summary:

- `_build/bo3_rev_idg_probe/entry_return_bridge_override_matrix/20260404_085014/entry_return_bridge_override_matrix_summary.json`

Required family A:

- `minus1 = 0x033F0380`
- `plus3 = 0x033F4D50`

Control accepted run:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_085140/same_process`
- first recovered producer family:
  - `class_plus_5 = 0x000F0105`
  - no later distinct family on that accepted control

Accepted causal overrides inside that same family-A bucket:

- `bridge_plus3_alt`
  - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_085541/same_process`
  - post-patch bridge:
    - `minus1 = 0x033F0380`
    - `plus3 = 0x033F3790`
  - first producer family changed to:
    - `class_plus_5 = 0x000A0105`
  - later distinct family also appeared:
    - `class_plus_5 = 0x010D0105`
- `bridge_both_alt`
  - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_085700/same_process`
  - post-patch bridge:
    - `minus1 = 0x033ED240`
    - `plus3 = 0x033F3790`
  - first producer family changed to:
    - `class_plus_5 = 0x00020105`

That is the first clean family-normalized proof that the bridge override is not just live, but causal: patching the bridge family changes the first recovered producer family before later selector-root materialization.

### Family B mirror bucket: `plus3` is causal there too

Mirror summary:

- `_build/bo3_rev_idg_probe/entry_return_bridge_override_matrix/20260404_091236/entry_return_bridge_override_matrix_summary.json`

Required family B:

- `minus1 = 0x033ED240`
- `plus3 = 0x033F3790`

The family-B control bucket was less stable and did not produce a clean accepted control comparison inside that single summary, but the accepted `bridge_plus3_alt` run is still meaningful:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_091635/same_process`
- prepatch bridge:
  - `minus1 = 0x033ED240`
  - `plus3 = 0x033F3790`
- post-patch bridge:
  - `minus1 = 0x033ED240`
  - `plus3 = 0x033F4D50`
- recovered producer families:
  - hit 1: `class_plus_5 = 0x00120105`
  - hit 2: `class_plus_5 = 0x01150105`

That makes the bridge-local role split much tighter:

- `plus3` is now the strongest recovered bridge-local causal driver of downstream producer-family selection
- `minus1` is still live and patchable, but it has not yet shown the same clean independent causality on the normalized family-A bucket

### Follow-on render carry-forward is still unstable

I also ran a follow-on render version of the same bridge matrix:

- `_build/bo3_rev_idg_probe/entry_return_bridge_override_matrix/20260404_090142/entry_return_bridge_override_matrix_summary.json`

That lane did not yield a clean accepted same-bucket control+patch comparison with render preserved. Some attempts did recover:

- entry-first hit
- accepted bridge override
- later producer families
- occasional render hits

but not in one stable enough same-bucket pair to make a trustworthy bridge-to-render claim yet.

### Meaning

This kills another stale theory:

- "the bridge family is only a correlation surface, not an actual upstream control point"

The repo now supports a stronger model:

1. the normalized `00341F6C` bridge family is a real upstream control surface
2. bridge-local `plus3` is the strongest currently recovered driver of first producer-family selection
3. the remaining hard problem is not bridge causality itself, but carrying that earlier bridge change forward into a stable later producer/render takeover and eventually visible custom animation

Current best frontier after this pass:

- stay on `consumer_upstream_ret_00341F6C`
- treat bridge `plus3` as the highest-value live causal field
- either stabilize the bridge-to-render follow-on lane,
- or, if that stays unstable, recover why the bridge-local `plus3` change does not consistently survive into later render-family materialization

## 83. Track A succeeded on bridge causality, and Track B succeeded on practical later-family control

The user asked for two explicit tracks:

- Track A: one serious bridge-provenance pass
- Track B: one practical later-family control pass on a single normalized same-process bucket

Both tracks are now complete enough to reason from without reopening the same dead branches.

### Track A result: success

Track A success condition was:

- recover a writer/caller family for bridge A/B, or
- recover an earlier patchable surface before bridge, or
- recover a deterministic bridge override that changes first producer family

That success condition is now met.

Authoritative bridge artifacts:

- family-A bucket summary:
  - `_build/bo3_rev_idg_probe/entry_return_bridge_override_matrix/20260404_085014/entry_return_bridge_override_matrix_summary.json`
- family-B mirror summary:
  - `_build/bo3_rev_idg_probe/entry_return_bridge_override_matrix/20260404_091236/entry_return_bridge_override_matrix_summary.json`

What now counts as established:

1. `consumer_upstream_ret_00341F6C` is a real upstream control surface
2. bridge-local `plus3` is the strongest recovered causal field there
3. patching `plus3` inside a normalized bridge bucket deterministically changes the first recovered producer family

That means the stale “bridge is only a correlated observation surface” theory is dead.

### Track B result: success on practical control, but not yet visible custom motion

Track B stayed on one normalized same-process control bucket:

- control:
  - `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_013747/same_process`
- approved control summary:
  - `_build/bo3_rev_idg_probe/same_process_trio_transplant_matrix/20260404_014612/same_process_trio_transplant_matrix_summary.json`

The key accepted same-bucket practical-control win is still:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_013814/same_process`

That run proves:

- same-process starter-to-probe transplant of later-family `class +2/+3/+4` is live
- `joined_surface_seen = true` is preserved
- later render family moves from:
  - `render = 0x30B07E0C`
  - to `render = 0x30BE7E0C`

That satisfies the Track B success condition:

- joined surface remains preserved while later render family changes

So the stale “later-family control is already too late to move anything meaningful downstream” theory is also dead.

### What the fresh Track B rerun changed

I reran the same-process matrix after fixing case-filter parsing:

- `_build/bo3_rev_idg_probe/same_process_trio_transplant_matrix/20260404_094127/same_process_trio_transplant_matrix_summary.json`

That rerun did not recover fresh accepted same-bucket cases for:

- `same_process_plus234`
- `same_process_plus5_only`
- `same_process_plus234_plus5`

The lane was sparse:

- many attempts never recovered `consumer_asset_class_lookup`
- accepted same-bucket downstream carry-forward was not re-established in that rerun

This does **not** undo the earlier accepted same-bucket `+2/+3/+4` win. It only means:

- the same-process live lane remains unstable
- `+5`-only still has no accepted normalized proof
- `+2/+3/+4/+5` still has no accepted normalized proof on the original stable control bucket

### Current role split after both tracks

The repo now supports this tighter practical model:

1. bridge-local `plus3` is the strongest recovered upstream causal driver of first producer-family selection
2. later-family `class +2/+3/+4` is the best recovered downstream practical control surface for render takeover
3. later-family `class +5` is still secondary and not independently proven sufficient on the normalized same-process bucket

### Meaning for the animation goal

We still do **not** have visible custom first-person animation working.

But the project is no longer lost in passive tracing. The remaining frontier is now clean:

- upstream causal branch split:
  - bridge `plus3`
- downstream practical render-takeover surface:
  - later producer-family `class +2/+3/+4`

The next hard problem is making those two layers carry forward into a stable same-bucket downstream selector/render takeover often enough to test visible custom motion, not re-deriving selector-root, wrapper, or child-local theories that are already superseded.
## Correction - 2026-04-04 bridge-to-later carry-forward reruns and handoff split

The `bridge_later_carry_forward` pass was rerun twice to test the last unresolved layer between the proven bridge control surface and the proven later-family `class +2/+3/+4` control surface.

Authoritative carry-forward summaries:

- `_build/bo3_rev_idg_probe/bridge_later_carry_forward_matrix/20260404_102117/bridge_later_carry_forward_matrix_summary.json`
- `_build/bo3_rev_idg_probe/bridge_later_carry_forward_matrix/20260404_104025/bridge_later_carry_forward_matrix_summary.json`

Result:

- no accepted composed case was recovered
- neither `bridge_plus3_only`, `later_plus234_only`, nor `bridge_plus3_plus_later_plus234` produced a clean accepted same-bucket run with:
  - bridge bucket present
  - first producer family
  - later producer family
  - later render family
  - joined-surface preservation

The second rerun on the bridge-B bucket was still useful because it confirmed the failure is not just "wrong bridge bucket":

- bridge-B control bucket used:
  - `minus1 = 0x033ED240`
  - `plus3 = 0x033F3790`
- bridge patch flipped toward:
  - `minus1 = 0x033F0304`
  - `plus3 = 0x033F4E40`
- even there, the combined case did not compose into a stable carry-forward win

That means the unresolved layer is now the handoff/normalization step between bridge output and later-family materialization, not bridge discovery and not later-family field discovery.

### Authoritative handoff-chain analysis

To make that failure mode explicit, a new offline analyzer was added:

- `tools/analyze_bridge_handoff_chains.ps1`

Authoritative output:

- `_build/bo3_rev_idg_probe/bridge_handoff_chain_analysis/20260404_105455/bridge_handoff_chain_summary.json`

This pass scanned same-process archives and reconstructed:

- bridge bucket
- first producer compact family
- first later distinct producer compact family
- later render family
- joined-surface presence

Conclusion:

- `bridge_handoff_chain_split_recovered`

Best-supported statement:

- same-process bridge buckets split into at least one productive chain that reaches later-family render materialization and one collapsed chain that stalls at the first producer family

Important recovered productive chains:

- `0x033ED240/0x033F3790 -> 0x00120105/0x00000201 -> 0x01150105/0x00000201 -> 0x2F3Cxx`
- `0x033ED240/0x033F3790 -> 0x00020105/0x00000201 -> 0x01050105/0x00000201 -> 0x2FCBxx`
- `0x033F0380/0x033F4D50 -> 0x00020105/0x00000201 -> 0x01050105/0x00000201 -> 0x30AAxx`

Important collapsed chains:

- `0x033F0304/0x033F4E40 -> 0x00010101/0x00000003 -> none -> none`
- `0x033ED204/0x033F3880 -> 0x00010101/0x00000003 -> none -> none`
- `0x033ED240/0x033F3790 -> 0x00120105/0x00000201 -> none -> none`
- `0x033ED240/0x033F3790 -> 0x00020105/0x00000201 -> none -> none`

This is the important interpretation:

- bridge-family `plus3` is still a real upstream control surface
- later-family `class +2/+3/+4` is still a real downstream practical control surface
- but those layers do not compose reliably because the same-process handoff can still collapse before the later-family render lane appears

Current frontier:

- not more bridge-family discovery
- not more later-family field discovery
- the unresolved normalization/provenance step that turns bridge output into a productive first-producer and later-family render chain
## 82) bridge_to_first_producer_carry_forward: first-producer and bridge-only field patching can change early producer state, but carry-forward still stalls before later-family/render materialization (2026-04-04)

I pushed the handoff pass further in two steps:

- I refined `tools/run_bridge_to_first_producer_carry_forward_matrix.ps1` so producer-mode no longer arms render from startup during the hit-1 handoff test. The runner now keeps `consumer_asset_lookup_entry` / hit-1 `consumer_asset_class_lookup` as the priority surface and writes an enabled producer override config even for control so the same lane behavior is preserved.
- I extended the same runner with an explicit `bridge_plus3_only` case and reran the matrix on the intended collapsed bridge handoff.

Artifacts:

- `_build/bo3_rev_idg_probe/bridge_to_first_producer_carry_forward_matrix/20260404_114902/bridge_to_first_producer_carry_forward_matrix_summary.json`
- `_build/bo3_rev_idg_probe/bridge_to_first_producer_carry_forward_matrix/20260404_120356/bridge_to_first_producer_carry_forward_matrix_summary.json`

What the refined first-producer matrix established:

- There are still no accepted runs on the exact collapsed bridge bucket `0x033F0304 / 0x033F4E40`; the run-level conclusion remains `bridge_to_first_producer_carry_forward_no_cases_recovered`.
- Nevertheless, the hit-1 producer family is patchable when the lane stays alive:
  - in `20260404_115104/same_process`, `first_producer_compact_only` changed the initial family compact from `0x00020105 / 0x00000201` to `0x00120105 / 0x00000201`
  - in `20260404_115707/same_process` and `20260404_115925/same_process`, `bridge_plus3_plus_first_producer` changed the initial family from `0x00020105 / 0x00000201` to `0x00120105 / 0x00000201` while also transplanting the reference pointer family
- In every such case, the chain still stalled:
  - no later producer family appeared
  - no later render family materialized
  - `joined_surface_seen` stayed false

What the bridge-only follow-up established:

- Adding `bridge_plus3_only` did not recover an accepted strict collapsed-bucket run either, but it did recover an informative bridge-patched family in `20260404_120838/same_process`.
- In that run, the first recovered entry/bridge family was already the alternate productive-style bridge family `0x033ED240 / 0x033F3790`, and the first producer compact was `0x000A0105 / 0x00000201`.
- Even there, the chain still stalled:
  - no later distinct producer family
  - no later render family
  - no joined-surface preservation

Interpretation:

- The stale “fix the handoff by patching hit-1 producer fields” theory is dead.
- The stale “bridge `plus3` alone will force productive carry-forward” theory is also dead on this lane.
- Bridge-local and hit-1 first-producer field patching can change the *early* producer state, but that state still does not carry forward into later-family render materialization.

Current frontier:

- The unresolved layer is now the bridge→first-producer normalization/provenance step itself, specifically the emitter/writer path that produces a *productive first-producer pointer family* and allows later-family carry-forward.
- The next correct pass is provenance on that emission path, not more field-level patching of hit-1 producer or downstream later-family fields.
## 84) bridge_to_first_producer_emitter_provenance: native bridge/entry provenance trace exists now, but the bridge-friendly lane is still too unstable to recover an accepted emitter trace (2026-04-04)

I implemented a dedicated provenance pass instead of more field patching:

- native changes in [fx_runtime_probe_hook.cpp](/z:/Games/pluto_t6_full_game/native/fx_runtime_probe/fx_runtime_probe_hook.cpp)
  - added `trace_bridge_to_first_producer` producer-mode config
  - added a new single-step label `bridge_to_first_producer_flow`
  - bridge/entry flow now logs:
    - `bridge_to_first_producer_trace_armed`
    - `bridge_first_producer_candidate_birth`
    - `bridge_to_first_producer_trace_complete`
- new runner:
  - [run_bridge_to_first_producer_emitter_provenance.ps1](/z:/Games/pluto_t6_full_game/tools/run_bridge_to_first_producer_emitter_provenance.ps1)

Artifacts:

- `_build/bo3_rev_idg_probe/bridge_to_first_producer_emitter_provenance/20260404_132602/bridge_to_first_producer_emitter_provenance_summary.json`
- `_build/bo3_rev_idg_probe/bridge_to_first_producer_emitter_provenance/20260404_133727/bridge_to_first_producer_emitter_provenance_summary.json`

What this pass established:

- the new provenance instrumentation builds and runs live
- the same-process runner can now be pointed at normalized productive/collapsed bridge buckets without doing any value patching
- but on the current lane it still does **not** recover an accepted emitter trace:
  - most attempts devolve into render-first/no-asset-lookup runs
  - productive-bucket retries can still recover entry/first-producer/later-render state, but the provenance trace itself does not arm cleanly often enough to reason from
  - the run-level conclusion remains `bridge_to_first_producer_emitter_provenance_no_cases_recovered`

Meaning:

- the stale “a simple bridge-aligned entry trace will immediately expose the emitter” theory is now dead
- this does **not** reopen downstream patching
- it means the remaining emitter/writer path is still the right frontier, but the bridge-friendly provenance lane itself needs stabilization before it can answer the writer question cleanly

Current frontier after this pass:

- unresolved layer is still the bridge→first-producer emission / normalization path
- practical next move is to harden the bridge-friendly emitter lane or recover the same provenance on an even more stable entry-first bucket
- not more later-family field matrices
## 85) bridge_to_first_producer_provenance_stability: config poisoning is fixed, but the same-process provenance lane still drifts between entry buckets before a full emission trace is recovered (2026-04-05)

I used this pass to stabilize the exact remaining handoff lane rather than do more engine mapping.

Native/probe changes:

- in [fx_runtime_probe_hook.cpp](/z:/Games/pluto_t6_full_game/native/fx_runtime_probe/fx_runtime_probe_hook.cpp)
  - fixed the real producer override loader buffer on the live producer path from 512 to 4096 bytes
  - added dedicated provenance config file support:
    - `native/fx_runtime_probe/active_producer_class_override_stability.txt`
  - suppressed deferred snapshot spawning when `trace_bridge_to_first_producer=1` so the bridge→first-producer lane stays minimal
  - added `stop_after_bridge_candidate_birth` so this provenance lane can terminate immediately after the first valid producer birth instead of trying to survive extra same-process dwell

Runner changes:

- [run_bridge_to_first_producer_emitter_provenance.ps1](/z:/Games/pluto_t6_full_game/tools/run_bridge_to_first_producer_emitter_provenance.ps1)
  - now writes the dedicated stability config file instead of the shared producer override file
  - verifies the loaded native config from the archived `fx_runtime_probe.log`
  - classifies partial failure modes explicitly
  - tightened the trace to a one-step hit-and-exit provenance mode for the productive bucket

Authoritative summaries:

- `_build/bo3_rev_idg_probe/bridge_to_first_producer_emitter_provenance/20260405_135950/bridge_to_first_producer_emitter_provenance_summary.json`
- `_build/bo3_rev_idg_probe/bridge_to_first_producer_emitter_provenance/20260405_140434/bridge_to_first_producer_emitter_provenance_summary.json`
- `_build/bo3_rev_idg_probe/bridge_to_first_producer_emitter_provenance/20260405_141149/bridge_to_first_producer_emitter_provenance_summary.json`
- `_build/bo3_rev_idg_probe/bridge_to_first_producer_emitter_provenance/20260405_141810/bridge_to_first_producer_emitter_provenance_summary.json`

What this pass established:

- the stale config/path theory is dead:
  - the dedicated stability config file is now the file actually loaded by the live producer lane
  - the logged producer config now correctly reflects `trace_bridge_to_first_producer`, required bridge bucket, disabled render follow-on, and `stop_after_bridge_candidate_birth`
- the remaining blocker is lane stability, not config confusion
- the same-process entry-first lane is still drifting across at least three live wrapper families before provenance normalization can hold:
  - `0x033F0304 / 0x033F4E40`
  - `0x033F0380 / 0x033F4D50`
  - `0x033ED204 / 0x033F3880`
- because of that drift:
  - some runs reach `consumer_asset_lookup_entry` and even `consumer_asset_class_lookup`, but never arm the provenance trace because the live entry bucket does not match the selected bucket
  - some runs land on productive first/distinct producer families, but still without an accepted traced birth/mutation sequence

Useful raw-log proof from the stabilized lane:

- the live producer config now logs the intended stability fields:
  - `trace_bridge_to_first_producer=1`
  - `stop_after_bridge_candidate_birth=1`
  - `require_bridge_bucket=1`
  - selected `bridge_required_minus1` / `bridge_required_plus3`
- on the productive bridge bucket test, the trace can now at least begin on the right live surface:
  - `step_trace_begin label=bridge_to_first_producer_flow ...`
  - followed by `entry_wrapper_trace_armed` / `entry_wrapper_prepopulated`
- but the full accepted `bridge_first_producer_candidate_birth` + `bridge_to_first_producer_trace_complete` pair is still not recovered consistently enough to promote this to a solved emitter trace

Meaning:

- bridge discovery is still solved
- later-family practical control is still solved
- the unresolved layer is still the bridge→first-producer emitter / normalizer
- but the exact blocker has become more specific:
  - not missing instrumentation
  - not wrong bucket theory
  - not wrong config file
  - now specifically the unstable same-process lane that drifts between entry buckets before the provenance trace can complete cleanly

Current frontier after this pass:

- keep the work on provenance stabilization, not downstream field patching
- normalize on one reproducible productive bridge bucket first
- recover one accepted bridge→first-producer birth/complete pair on that bucket
- only after that revisit earlier writer provenance or later visible-animation carry-forward
## 86) bridge_to_first_producer_provenance_stability: one clean accepted handoff trace is now recovered on the productive bridge bucket (2026-04-05)

I did the one bounded provenance phase on a single productive bridge bucket and it finally paid off.

Authoritative summary:

- `_build/bo3_rev_idg_probe/bridge_to_first_producer_emitter_provenance/20260405_143131/bridge_to_first_producer_emitter_provenance_summary.json`

Accepted live run:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260405_143131/same_process/variant_summary.json`

Pinned productive bridge bucket:

- `minus1 = 0x033F0380`
- `plus3 = 0x033F4D50`

Recovered accepted pair:

- `bridge_to_first_producer_trace_armed`
- `bridge_first_producer_candidate_birth`
- `bridge_to_first_producer_trace_complete`

Concrete recovered sequence:

- entry wrapper at first hit:
  - `base = 0x5F8C9000`
  - `minus3 = 0x033F4D50`
  - `minus1 = 0x033F0380`
  - `plus3 = 0x033F4D50`
- one-step provenance trace:
  - `eip = 0x00741AE1`
  - `reg = ecx`
  - `class = 0x5F8C9070`
  - `class_head = 0x01010101`
  - `class_plus_2 = 0x01010101`
  - `class_plus_3 = 0x01010101`
  - `class_plus_4 = 0x00000001`
  - `class_plus_5 = 0x00000001`
  - `class_plus_6 = 0x00000001`
- immediate trace completion on that same step:
  - `producer_seen = 1`
  - `producer_any_change = 0`
  - final producer values still the same sentinel-style seed
- then the first recovered `consumer_asset_class_lookup` family appears later as:
  - `class = 0x2D889A7C`
  - `class_head = 0x2D88D440`
  - `class_plus_2 = 0x2D88BB20`
  - `class_plus_3 = 0x2D889A9C`
  - `class_plus_4 = 0x2D88BB94`
  - `class_plus_5 = 0x00020105`
  - `class_plus_6 = 0x00000201`

What this finally proves:

- the bounded productive-bucket provenance lane works
- the stale “we still cannot recover an accepted bridge→first-producer emission sequence” blocker is now dead
- the earliest recovered post-bridge emission step is not yet the final first producer family
- instead, the accepted handoff now shows an earlier one-step seed/normalization object on `ecx`
- the later first producer family recovered at `consumer_asset_class_lookup` is downstream of that seed object

Meaning:

- bridge discovery: solved
- later-family practical control: solved
- stable accepted bridge→first-producer handoff trace: now solved
- the unresolved layer moved again:
  - not “recover any accepted handoff trace”
  - now specifically “how the one-step `ecx` seed/normalization object becomes the first recovered producer family”

Current frontier after this pass:

- do not reopen broad provenance stabilization
- the next correct pass is a very narrow source-side normalization pass from:
  - `entry eip 0x00741AE1`
  - `reg = ecx`
  - `class = owner_plus_4/source-side object`
- the practical question is now:
  - what fields or write path turn that sentinel-style seed object into the later real first producer family
## 87) seed_to_first_producer_normalization: the accepted handoff now proves source-side identity, not in-place seed mutation (2026-04-05)

I stayed exactly on the post-bridge normalization gap and ran a narrow correlation pass instead of reopening bridge stabilization or downstream render theory.

Authoritative summary:

- `_build/bo3_rev_idg_probe/seed_to_first_producer_normalization/20260405_144553/seed_to_first_producer_normalization_summary.json`

Accepted run:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260405_144737/same_process/variant_summary.json`

What the accepted run proves:

- the accepted productive bridge bucket is still:
  - `minus1 = 0x033F0380`
  - `plus3 = 0x033F4D50`
- the seed birth is still the same one-step post-bridge object:
  - `eip = 0x00741AE1`
  - `reg = ecx`
  - `seed = 0x5FA69070`
- the later first recovered producer-family hit shows:
  - `owner = 0x5FA69000`
  - `owner_plus_4 = 0x5FA69070`
  - `source = 0x5FA69070`
  - `class = 0x2DC89A7C`

The key recovered identity:

- `source_matches_seed = true`
- `owner_plus4_matches_seed = true`

The key recovered non-mutation:

- seed core at birth:
  - `slot0..slot3 = 0x01010101`
  - `slot4..slot6 = 0x00000001`
- source core at first producer-family appearance:
  - unchanged
- all tracked `slot0..slot6` change flags stayed false

Meaning:

- the stale “seed object mutates in place into the first producer family” theory is dead
- the seed object survives as the later source-side identity object
- the real first producer family is emitted downstream from that stable source-side object, not by in-place mutation of its tracked core slots

So the unresolved layer moved again:

- not bridge stabilization
- not seed birth recovery
- not in-place seed mutation
- now specifically:
  - how the stable source-side object (`seed == source == owner_plus_4`) emits or resolves the later `class/class_head/+2/+3/+4/+5/+6` producer family

Current frontier after this pass:

- narrow source→class emission provenance
- likely around the source-side object at `owner_plus_4`
- not more bridge bucket work
- not more later-family-only patching until that source→class emission step is understood

## 88) source_to_class_emission follow-up: the narrowed lane is instrumented, but this rerun drifted off the productive bridge bucket before accepted source-class capture (2026-04-05)

Authoritative summary:

- `_build/bo3_rev_idg_probe/seed_to_first_producer_normalization/20260405_145953/seed_to_first_producer_normalization_summary.json`

What changed:

- the native source-side lane now logs `source_to_class_emission_neighborhood`
- `run_seed_to_first_producer_normalization.ps1` now parses and archives that relation when an accepted run exists

What this rerun proved:

- config loading is still correct for the narrowed source-side pass
- the lane did not recover a new accepted productive-bucket run in this batch
- the bridge trace kept skipping on off-bucket wrapper families before the source to class handoff could be summarized

Observed drift families in this rerun:

- `minus1 = 0x033ED204`, `plus3 = 0x033F3880`
- `minus1 = 0x033ED240`, `plus3 = 0x033F3790`
- `minus1 = 0x033F0304`, `plus3 = 0x033F4E40`

Meaning:

- the source-side class-emission hook is now ready to summarize the next accepted run automatically
- but this batch does not change the actual frontier
- the unresolved step is still:
  - stable `source == owner_plus_4`
  - resolves / emits
  - later `class/class_head/+2/+3/+4/+5/+6`
## 89) determinism-only checkpoint: the productive source-emission lane is reproducible again, but accepted downstream takeover is still not (2026-04-05)

Authoritative determinism summary:

- `_build/bo3_rev_idg_probe/animation_lane_determinism/20260405_155411/animation_lane_determinism_summary.json`

New runner:

- `tools/run_animation_lane_determinism.ps1`

What changed:

- this pass did not add new probe surfaces or widen the engine map
- it only tried to reacquire two previously proven lanes under one forced shell:
  - productive source-emission bucket
  - accepted same-process later-family takeover
- both reuses now accept `-ForcedStockShell`, and the bounded batch was run with:
  - `c_zom_oldman_viewhands`

### 89.1 Productive source-emission bucket was reacquired

Authoritative source summary:

- `_build/bo3_rev_idg_probe/seed_to_first_producer_normalization/20260405_155412/seed_to_first_producer_normalization_summary.json`

Accepted run:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260405_155519/same_process/variant_summary.json`

Recovered productive bucket again:

- `minus1 = 0x033F0380`
- `plus3 = 0x033F4D50`

Recovered source-side identity again:

- `owner = 0x2C779000`
- `owner_plus_4 = 0x2C779070`
- `source = 0x2C779070`
- `seed = 0x2C779070`

Recovered later first producer family again:

- `class = 0x2D7B5754`
- `class_head = 0x2D7B7BC0`
- `class_plus_2 = 0x2D7ABB20`
- `class_plus_3 = 0x2D7AEDD0`
- `class_plus_4 = 0x2D7B5774`
- `class_plus_5 = 0x00120105`
- `class_plus_6 = 0x00000201`

Important new negative result from the new source-neighborhood log:

- `source_to_class_emission_neighborhood`
  - `minus4 = 0x2C77E400`
  - `minus3 = 0x03EEA500`
  - `minus2 = 0x01010101`
  - `minus1 = 0x00000000`
  - `owner_match_minus4 = 0`
  - `class_match_minus4 = 0`
  - `class_match_minus1 = 0`

Meaning:

- forcing the oldman shell is enough to reacquire the productive source-emission lane
- the source-side lane is not lost to drift anymore
- the new source-neighborhood capture kills another easy theory:
  - there is no simple direct `source[-4] == owner`
  - and no simple direct `source[-4/-1] == class`

### 89.2 Accepted downstream same-process takeover was not reacquired

Authoritative same-process summary:

- `_build/bo3_rev_idg_probe/same_process_trio_transplant_matrix/20260405_155621/same_process_trio_transplant_matrix_summary.json`

What was attempted:

- approved control reused from:
  - `_build/bo3_rev_idg_probe/same_process_trio_transplant_matrix/20260404_013746/same_process_trio_transplant_matrix_summary.json`
- only the already-proven practical lane was retried:
  - `same_process_plus234`
- the same bounded batch forced:
  - `c_zom_oldman_viewhands`

Result:

- no accepted `same_process_plus234` run was recovered
- attempts drifted across:
  - reporter shell
  - farmgirl shell
  - oldman shell with delayed `pre_grant/post_switch` timing and wrong wrapper family
- none preserved the old accepted downstream takeover conditions

Best oldman drift example:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260405_155927/same_process/variant_summary.json`
- still landed on:
  - `minus1 = 0x033ED204`
  - `plus3 = 0x033F3880`
- with:
  - `joined_surface_seen = false`
  - `asset_lookup_hit_count = 0`

### 89.3 Current checkpoint after the determinism pass

Meaning:

- the productive source-emission lane is practically capturable again
- the old accepted downstream takeover lane is still the unstable one
- so the blocker for visible custom animation is no longer:
  - missing source-side instrumentation
  - missing source bucket recovery
- it is now:
  - downstream accepted takeover reacquisition / practical render-takeover reproducibility

Current frontier after this pass:

- source-side class emission is still a valid unresolved control step
- but the highest operational blocker for visible animation is now the unstable downstream accepted takeover lane
- more broad reverse engineering is no longer the highest-value move unless that downstream lane is made reproducible again

## 90) Practical pivot checkpoint: visible-motion forcing runner exists, but practical build execution is currently blocked by missing x86 OAT linker support (2026-04-05)

Files added / updated:

- `tools/run_practical_visible_motion_forcing.ps1`
- `tools/run_anim_debug_cycle.ps1`

What changed:

- `run_anim_debug_cycle.ps1` now exposes practical build/runtime knobs that already existed in `build_servant_minimal_anim_runtime.ps1`:
  - `-RuntimeBackend`
  - `-ForceStockShell`
  - `-ForcedStockShell`
  - `-IdleDiagBone`
  - `-IdleDiagTranslate`
  - `-IdleDiagFrequency`
  - `-IdleStaticBone`
  - `-IdleStaticTranslate`
- `run_practical_visible_motion_forcing.ps1` was added as a bounded practical package:
  - two shells:
    - `c_zom_oldman_viewhands`
    - `c_zom_farmgirl_viewhands`
  - control vs forced visible-motion diagnostic build
  - judged only by live motion output from `run_anim_debug_cycle`

What happened:

- the practical package failed on the first case before reaching runtime judgment
- blocker:
  - `_build/build_bo3_rev_idg_probe.py`
  - `verify_t6_oat_binary_architectures()`
- authoritative failure:
  - local `tools/oat/Linker.exe` is `x64`
  - local `tools/oat/Linker.exe.bak_031717` is also `x64`
  - runtime packaging currently requires `x86` linker binaries for T6 DB-safe packaging

Meaning:

- the reverse-engineering lane is no longer the immediate blocker
- the practical visible-motion forcing lane is now blocked by packaging/toolchain state on this machine
- so the repo has a practical experiment runner ready, but cannot currently execute a fresh practical animation build until an x86 OAT linker is restored or a trustworthy no-build practical lane is chosen

## 91) Practical pivot follow-up: fresh practical builds are unblocked again, but live runtime still lands on an older script/build lane (2026-04-05)

What changed:

- `tools/run_anim_debug_cycle.ps1`
  - added `-SkipBuild`
  - now falls back to the live runtime `build_tag`
  - now parses `games_mp.log` lines with leading server timestamps
- `tools/run_practical_visible_motion_forcing.ps1`
  - can reuse an existing runtime build
- `_build/build_bo3_rev_idg_probe.py`
  - now writes `mod_i_am_mod.gsc` to both:
    - `mods/bo3_rev/scripts/mod_i_am_mod.gsc`
    - `_build/bo3_rev_idg_probe/scripts/mod_i_am_mod.gsc`
- missing `mods/bo3_rev` template files were restored from the quarantine mod copy

Recovered facts:

- no-build practical observation now recovers the active live tag and valid connect/grant markers.
- fresh practical builds now complete again with intended diagnostic args such as:
  - `ForcedStockShell = c_zom_oldman_viewhands`
  - `IdleDiagBone = tag_weapon`
  - `IdleDiagTranslate = 0,0,160`
  - `IdleDiagFrequency = 8`
- fresh practical build tag from the rebuilt lane:
  - `0405233950_75d444`
- but the launched runtime still reports old live tag:
  - `0402021252_67ac52`

Meaning:

- current blocker is no longer linker/tooling or stale no-build verdict parsing.
- current blocker is a practical runtime-source split:
  - fresh build artifacts exist
  - but the live game still executes an older script/build lane

## 24) Practical late-attach lane now reaches the real in-map animation path again; accepted verdict is the remaining blocker (2026-04-05)

Implemented:

- `tools/restart_t6_probe_cycle.ps1`
  - added late probe gates:
    - `connect`
    - `grant`
    - `first_raise_begin`
    - `idle_begin`
    - `fire_begin`
- `tools/run_anim_debug_cycle.ps1`
  - added `-ProbeAttachGate`
  - added longer default attach windows for late gates
  - fixed log snapshots so they are taken before launch/injection, preserving pre-attach history
- `tools/run_practical_visible_motion_forcing.ps1`
  - now uses `-ProbeAttachGate idle_begin`

Authoritative late-attach archive:

- `_build/bo3_rev_idg_probe/anim_debug_runs/20260405_194254_custom_idle_first_raise_observe_only`

Recovered facts from that run:

- real map lane is live again:
  - `Loading fastfile so_zsurvival_zm_transit`
  - `[bo3_rev][start]`
  - `[bo3_rev][connect]`
  - `[bo3_rev][grant]`
- forced downstream visible shell is present:
  - `c_zom_farmgirl_viewhands`
- same run also reaches visible animation markers before/through late attach:
  - `first_raise_begin`
  - `first_raise_end`
  - `idle_begin`
- probe still attaches on the same late lane:
  - `fx_runtime_probe loaded pid=68960 build=20260405_145516`

Current interpretation:

- the practical downstream lane is now reproducible at raw-runtime level
- the old “cannot get the live lane back at all” blocker is dead
- the remaining blocker is post-attach carry-through:
  - the run still does not finish as a fully accepted debug verdict
  - current `run_verdict.json` still misses late-stage completion (`idle_end`) and resolver/expected-name proof

Meaning:

- do not reopen upstream reversing
- do not reopen bridge/source archaeology
- stay on practical downstream work:
  - accepted takeover carry-through
  - visible-motion forcing on the restored late-attach lane

## 25) Visibility isolation pass: invisible weapon is a bind/composition problem before animation forcing (2026-04-05)

Implemented:

- `tools/build_servant_minimal_anim_runtime.ps1`
  - added:
    - `-GunModelMode`
    - `-ForceLowHandmodel`
    - `-DisableStockSurvivorCarrier`
    - `-UseCustomIdgViewhands`

Authoritative build-side reports:

- stock gun control:
  - `_build/bo3_rev_idg_probe/build_report_visibility_stock_base.json`
- safer custom lane:
  - `_build/bo3_rev_idg_probe/build_report_visibility_custom_lowhand.json`

Recovered facts:

- stock control (`GunModelMode=base`)
  - `gunModel = t6_wpn_zmb_mg08_view`
  - `handModel = c_zom_hazmat_viewhands`
  - predicted composition:
    - `141 nodes / 130 joints` on hazmat
    - `142 nodes / 130 joints` on suit
  - under the `160`-joint/node danger threshold
- safer custom lane (`GunModelMode=custom`, `DisableStockSurvivorCarrier`, `ForceLowHandmodel`)
  - `gunModel = bo3_rev_v2_idg_view_0406020649_150ab9`
  - `handModel = bo3_rev_bridge_viewhands`
  - predicted composition:
    - `136 nodes / 129 joints` on hazmat
    - `137 nodes / 129 joints` on suit
  - also under the `160` threshold

Current interpretation:

- invisible weapon should now be treated as a first-person bind/composition failure first
- not as proof that the animation takeover work is wrong
- the active synced runtime was last rebuilt onto the safer custom-gun + low-handmodel lane
- next practical check should use this visibility-safe lane before any more animation forcing

## 26) Canonical runtime shell/client sources restored; startup now exposes fallback drift instead of hiding it (2026-04-05)

Implemented:

- restored the missing canonical runtime files into `mods/bo3_rev`:
  - `character/c_transit_player_engineer.gsc`
  - `character/c_transit_player_farmgirl.gsc`
  - `character/c_transit_player_oldman.gsc`
  - `character/c_transit_player_reporter.gsc`
  - `clientscripts/mp/zombies/_zm.csc`
  - `scripts/mp/zombies/_zm_spawner.gsc`
- `tools/restart_t6_probe_cycle.ps1`
  - accepts the newer active probe modes
  - logs the resolved source origin for critical loose runtime files
  - warns when quarantine fallback sources are being used
- `tools/run_anim_debug_cycle.ps1`
  - default runtime backend corrected to `target_weapon_names`
  - defaults to deterministic `c_zom_engineer_viewhands` forcing when no explicit shell override is supplied
- `tools/run_practical_visible_motion_forcing.ps1`
  - practical cases now explicitly build/run on the deterministic engineer-shell lane

Recovered meaning:

- the repo itself now contains the core shell/client runtime sources again, instead of depending on AppData/quarantine copies
- mixed-source runtime drift is now observable at startup time
- practical animation debugging is back on a deterministic stock-shell baseline, which is the right state before pushing further on first-person animation takeover
