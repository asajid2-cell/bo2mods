# Engine Map

## 23) Runtime/control map update: `t6-clean` is the stock control; generic `fs_game` mod support is the current crash frontier (2026-04-12)

Current intended runtime split:

- repo / Plutonium-side workspace:
  - `Z:\Games\pluto_t6_full_game`
- clean stock game runtime:
  - `Z:\Games\t6-clean\pluto_t6_full_game`

Meaning:

- the old project layout had allowed the game install to drift into the dev workspace
- the current setup treats `t6-clean` as the stock control and the repo as source/build/deploy only

What is now established about crash ownership:

- `-NoMod` on `t6-clean` is a valid stock control
- `fs_game=mods/<name>` activates a generic mod-session support lane
- that lane is unstable even for:
  - `new_mod`
  - a nonexistent mod name such as `ghostmod`

Observed generic mod-session behavior:

- before the stock Transit survival fastfiles, mod sessions still load:
  - `mod`
  - `mod_load`
  - `mod_patch`
- the resulting crash surface is therefore upstream of:
  - the Servant weapon
  - custom viewmodels
  - BO3 FX payloads

Current interpretation:

- the active stability bug is the generic `fs_game` mod support lane on this runtime/state
- custom weapon/viewmodel work is currently downstream of that lane

Synthetic `ipak` correction:

- fake zombie support alias `ipak`s had been introduced during repair/testing:
  - `code_post_gfx_zm.ipak`
  - `common_zm.ipak`
  - `lowmip.ipak`
  - `ui_zm.ipak`
  - `zm_transit.ipak`
  - `zm_transit_patch.ipak`
  - `patch_all.ipak`
  - `dlc1_load_zm.ipak` to `dlc4_load_zm.ipak`
- those aliases were not a real stock requirement
- they caused one of the earlier failure modes:
  - `no free ipak slots loading pak ...`
- do not reintroduce them into `t6-clean` as a generic repair step

## 22) Empirical stock input checkpoint: the current stock-control lane is now archived as a coherent engine-input dossier (2026-04-06)

Authoritative artifacts:

- `tools/run_stock_visibility_control.ps1`
- `_build/visibility_live/20260406_132914_stock_control/engine_input_dossier.json`
- `_build/visibility_live/20260406_132914_stock_control/resolved_sources.json`

Engine-map consequence:

- the repo now has a per-run machine-readable record of what the stock-control lane is actually feeding to the engine
- the current coherent stock-control staging is:
  - `weapon_shell = m1911_zm`
  - `starter_weapon = m1911_zm`
  - `gun_model_mode = base`
  - `gunModel = t6_wpn_pistol_m1911_view`
  - `handModel = ""`
- the synced loose runtime sources are now explicitly recoverable as:
  - `repo_mod` scripts / clientscripts / character files
  - `build_output` survival runtime FF

Current map consequence:

- a missing on-screen first-person model on this lane is no longer well explained by source drift alone
- the remaining visibility blocker is therefore more likely to be in:
  - first-person bind/materialization
  - render-owner selection
  - or downstream viewmodel visibility state

Important caveat:

- `mod_load.ff` is still absent on the current stock-control build output and is recorded as such by the dossier
- the launch-backed dossier did not produce fresh build-tag markers within the bounded capture window, so the sync-only dossier is currently the cleaner input truth source than the live-run dossier

## 21) Practical Control Follow-up: bounded downstream same-process takeover did not produce a fresh accepted case (2026-04-05)

Authoritative summary:

- `_build/bo3_rev_idg_probe/same_process_trio_transplant_matrix/20260405_152402/same_process_trio_transplant_matrix_summary.json`

Engine-map consequence:

- no new engine layer was discovered in this batch
- the downstream practical-control surfaces remain the same as before:
  - later-family `class +2/+3/+4`
  - possibly `+5` as a secondary compact field
- but the bounded retry did not recover a fresh accepted same-bucket takeover case

Current map consequence:

- the unresolved blocker is operational stability across:
  - source-side class emission capture
  - later-family practical takeover
- not uncertainty about where the major control surfaces live

This document is the consolidated engine map for the BO3/T7 -> BO2/T6 porting work in this repo.

It is meant to answer a different question from `docs/fullsummary.md`.

`fullsummary.md` is the timeline.

This file is the map:

- what the T6 runtime appears to accept
- what the repo has proven about that runtime
- what the real subsystem boundaries are
- where custom FX, models, and animations currently sit in the engine
- what is still inferred versus actually proven
- and where the remaining animation blocker now lives

Use this together with:

- `docs/handoff.md`
- `docs/fullsummary.md`
- `native/fx_runtime_probe/README.md`
- `_build/bo3_rev_idg_probe/build_report.json`

## 1. Reading guide

This file uses three evidence levels:

- `Proven`: supported by repeated live runs, logs, probe evidence, or successful runtime behavior
- `Inferred`: strongly suggested by the evidence, but not yet directly decoded end-to-end
- `Unknown`: still open

## 2. Top-level engine model

The practical T6 model exposed by this repo is:

1. The engine prefers accepted stock runtime contracts over fresh custom identities.
2. Foreign content can load, but acceptance depends on subsystem-specific contracts.
3. Weapon identity, model identity, FX identity, and animation identity are separate acceptance problems.
4. Being loaded in memory is not the same as being selected as the live winner.
5. The visible first-person result is downstream of a hidden ownership/lookup path, not just asset presence.

Current best global interpretation:

- custom FX can be translated and made live
- custom models can be loaded and attached under accepted carriers
- custom xanim data can be staged and loaded under runtime backend names
- but first-person animation playback is still gated by a hidden runtime ownership/lookup mapping

## 3. Core engine rules the repo has already established

### 3.1 Weapon identity rule

`Proven`

T6 does not behave like a friendly fresh-registration environment for weapons.

The working rule is:

- use a stock accepted weapon identity
- override its data and assets
- let that stock identity serve as the live runtime shell

This is the donor-shell / truth-alias rule.

Current active accepted carrier:

- `mg08_zm`

### 3.2 First-person shell rule

`Proven`

The live first-person shell is not controlled only by staged `handModel`.

What is proven:

- `setviewmodel("bo3_rev_bridge_viewhands")` is rejected at runtime
- live gameplay still chooses stock survivor shells
- observed winners include:
  - `c_zom_oldman_viewhands`
  - `c_zom_engineer_viewhands`
  - `c_zom_farmgirl_viewhands`
  - `c_zom_reporter_viewhands`
- deterministic stock-shell forcing works for investigation

Meaning:

- the live first-person shell is owned by a deeper runtime contract than the staged weapon field alone

### 3.3 Memory-presence rule

`Proven`

All of the following can be true at once:

- custom xmodels are loaded in memory
- custom xanim names are loaded in memory
- custom build products are packaged correctly
- and the visible runtime winner is still stock/donor-like

Meaning:

- "asset exists in memory" is only an upstream condition
- selection happens later

### 3.4 Acceptance rule by subsystem

`Proven`

Each subsystem has its own acceptance layer:

- weapon identity acceptance
- model/viewmodel acceptance
- material/image acceptance
- FX render acceptance
- animation selection/playback acceptance

The repo is strongest on FX acceptance and weakest on first-person animation selection.

## 4. Repo subsystem map

### 4.1 Active mod and script layer

Primary path:

- `mods/bo3_rev/`

Important roles:

- `mods/bo3_rev/scripts/mod_i_am_mod.gsc.in`
  - server-side runtime control
  - grant path
  - shell forcing
  - animation probe markers
- `mods/bo3_rev/clientscripts/mp/zombies/_zm.csc`
  - client-side watcher and local animation/tag sampling

### 4.2 Build/orchestration layer

Primary path:

- `_build/`

Important roles:

- `_build/build_bo3_rev_idg_probe.py`
  - main orchestration
  - emits runtime assets
  - controls animation staging modes
- `_build/compile_xanim_zone.py`
  - xanim staging and runtime-zone preparation
- `_build/bo3_rev_idg_probe/`
  - generated runtime assets
  - reports
  - sweep archives
  - probe summaries

### 4.3 Operator entrypoints

Primary path:

- `tools/`

Important roles:

- `tools/build_servant_minimal_anim_runtime.ps1`
  - current animation build wrapper
- `tools/launch_t6_offline.ps1`
  - stable direct launch
- `tools/run_idle_resolver_matrix.ps1`
  - proves visible idle winner
- `tools/run_consumer_hit_sweep.ps1`
  - current live consumer-object capture harness
- `tools/run_consumer_child_state_matrix.ps1`
  - root-relative child-state comparison
- `tools/analyze_consumer_child2_lookup_join.ps1`
  - offline join analysis between compact child state and lookup-family captures

### 4.4 Native runtime probe

Primary path:

- `native/fx_runtime_probe/`

Important roles:

- `fx_runtime_probe_hook.cpp`
  - live detours, memory watch, asset tracing, consumer-object capture
- `inject_latest.ps1`
  - injects into `plutonium-bootstrapper-win32`
- `active_probe_mode.txt`
  - current active probe mode token

## 5. Models: what the engine seems to do

### 5.1 Custom xmodels

`Proven`

The repo can stage and load custom xmodels successfully.

Important proved examples:

- custom gun model names appear in memory
- custom gun model names appear in multiple memory families, not just one string pool
- the custom gun model is usable under accepted carrier lanes

Current active custom gun family:

- `bo3_rev_v2_idg_view_<build_tag>`

### 5.2 What is still not proven for models

`Unknown`

The repo still does not have a fully decoded direct model-owner chain for the live first-person consumer object.

Current best interpretation:

- the engine is not storing model ownership in a simple adjacent string-pointer form near the live render objects
- model identity is likely hidden behind compact handles, indices, or descriptor indirection

## 6. FX: what the engine seems to do

### 6.1 FX acceptance

`Proven`

The FX subsystem is the best-understood and most successful foreign-content lane in the repo.

The repo has proven:

- BO3/T7-derived FX can be translated into T6-safe forms
- image/material normalization matters
- namespacing matters
- donor-family substitution matters
- the full Servant vortex lane can render live in T6

### 6.2 Important FX engine rules

`Proven`

The engine is sensitive to:

- image class / hash correctness
- material family shape
- technique-set compatibility
- runtime-safe image deployment
- effect attachment host and tag placement

Important historical fixes:

- x86 linker/unlinker build was required for correct T6 DB layout
- streamed-image hash bugs had to be fixed
- loose global image deployment under `storage\\t6\\images` caused real crash paths
- the neutral FX bridge at `tag_origin` is safer than a visible world-model host

### 6.3 Practical meaning

The FX question is no longer "can T6 load BO3 FX."

That is already answered yes.

The remaining FX work is polish/parity, not gross engine acceptance.

## 7. Animations: what the engine seems to do

### 7.1 What is already proven

`Proven`

The repo can:

- emit custom xanim exports
- stage them under runtime backend names
- ship them in the active build
- load those names into memory

The repo has also proven:

- semantic BO3 names and runtime backend names are different concerns
- staging under the names T6 actually consumes matters
- donor-order bone/name contract alignment matters
- semantic-shadow fallback paths create ambiguity and must be disabled in clean runtime-name tests

### 7.2 What the idle matrix proved

`Proven`

The idle resolver matrix was the major narrowing step.

It proved:

- stock donor idle, tiny donor idle edit, and BO3 rebake all reach the same visible idle result
- the positive control does not visibly win
- first_raise movement alone is not proof of custom idle ownership

Meaning:

- the live visible winner is not simply the intended `viewmodel_zomb_mg08_idle` family in the way the build expects

### 7.3 Current animation-state conclusion

`Proven`

The animation blocker is no longer:

- packaging
- startup
- launch flow
- probe mode loading
- probe injection
- or "are the names in memory"

The blocker is now:

- live runtime ownership/lookup selection inside the first-person consumer path

## 8. The first-person composition model

Current best composition model:

- accepted weapon shell: `mg08_zm`
- accepted live first-person shell: stock survivor viewhands
- custom gun model: attached successfully under that accepted shell/carrier lane
- custom animation family: loaded and staged, but not yet proven as the visible winner

Important consequence:

- the visible first-person result is downstream of the shell/consumer ownership path
- not just weapon-field configuration

## 9. Probe-mode map

### 9.1 `safe`

Minimal/stable probe mode.

### 9.2 `render_opacity_focus`

Narrow render-side mode used for FX opacity/render contract investigation.

### 9.3 `xanim_focus`

Broader xanim/xmodel watch mode.

Useful for:

- asset presence
- touch tracing
- name watch hits
- asset-header candidate work

### 9.4 `xanim_consumer_focus`

Current high-value animation investigation mode.

Purpose:

- arm the live first-person consumer path
- capture stable runtime objects from live render/lookup execution

Current status:

- no longer blocked on arm-thread setup
- no longer blocked on probe-mode token bugs
- no longer blocked on post-injection capture stability
- currently the main path to the real selection logic

## 10. What the probe has proven about the live consumer path

### 10.1 Earlier broad result

`Proven`

The consumer path is real and reachable from live gameplay.

Earlier runs proved live hits on:

- `consumer_render_table`
- `consumer_render_table_nonzero_branch`
- `consumer_render_table_compare`
- `consumer_render_table_match_branch`
- `consumer_submit_flags`
- and, intermittently, `consumer_asset_class_lookup`

### 10.2 Stable current anchor

`Proven`

The most reliable live hook family now is:

- `consumer_render_table`

This is the dependable anchor for current object recovery.

### 10.3 Intermittent upstream/lookup hooks

`Proven`

The upstream/lookup family is real, but not always repeatable on every fresh run.

Important proved relationship from the recovered upstream run:

- upstream `EDI == render_state_edi`
- upstream `ESI == render_state_edi + 0x8`
- upstream `EAX` is in the same family as the later render lookup block
- upstream `EAX -> render lookup delta = +0x84`

Meaning:

- the render-family and upstream lookup-family captures belong to one coherent object chain

## 11. Current recovered object model

This is the most important current reverse-engineering map in the repo.

### 11.1 Root

`Proven`

`render_state_edi` is now the best current root object for the live render family.

Why:

- it is directly recovered from the live consumer path
- it links cleanly to the upstream branch when that branch fires
- it has stable child links across successful variants

### 11.2 Stable child links

`Proven`

Across successful captures:

- `root -> child_2 delta = -0x0012BACC`
- `root -> child_3 delta = -0x000E1DE0`
- `root -> child_4 delta = -0x00000384`
- `root -> child_7 delta = +0x00000020`

Meaning:

- the local object layout under `render_state_edi` is structurally stable
- absolute heap addresses relocate per run, but the internal shape stays consistent

### 11.3 `child_2`

`Proven`

Current compact signature:

- `+0 = 0x00010003`
- `+1 = 0x02010000`
- `+2 = 0x00000502`
- later slots mostly zero

What is known:

- fully invariant across successful timing-sweep captures
- compact and numeric
- not pointer-rich

Current best interpretation:

- strongest compact ownership/state/handle candidate in the repo

### 11.4 `child_3`

`Proven`

Current profile:

- pointer-rich / relocated header region
- fixed small-int region
- printable payload beginning around `+4`

What is known:

- root-relative placement is stable
- some fields relocate per run
- payload region is fixed

Current best interpretation:

- downstream descriptor/projection/materialized state block
- not the primary compact owner key

### 11.5 `child_4` and `child_7`

`Proven`

These are structurally stable root-local neighbors.

What is not yet known:

- whether either one participates directly in model/anim ownership resolution

Current status:

- secondary leads
- not the best current owner/handle candidate

### 11.6 Lookup-family block

`Proven`

The lookup-family region connected to the upstream branch is real.

Important current interpretation:

- it behaves more like a descriptor/parameter/lookup family than a direct asset struct
- it does not expose the `child_2` signature directly

Examples from live capture:

- opaque first dword / ID-like value
- repeated scalar values such as `1.0f`
- no direct nearby watched-name ownership recovery

## 12. What has been ruled out

### 12.1 Wrong major branches already dead

`Proven`

The following theories have effectively been killed:

- launcher flow is the main blocker
- the probe is failing to inject
- the consumer arm thread is failing before gameplay
- the custom assets are missing from memory
- `child_2` is copied verbatim into the captured lookup windows
- `child_2` joins to the lookup family by trivial:
  - byte reuse
  - half reuse
  - simple masking
  - swapped-word transforms
  - small delta transforms
  - small XOR transforms

### 12.2 What that means

The remaining join between compact state and lookup family is almost certainly one of:

- table lookup
- handle/index indirection
- packed bitfield decode
- another object hop

## 13. Current best engine interpretation by subsystem

### 13.1 Weapon subsystem

Best interpretation:

- accepted stock identity first
- custom content layered under that identity second

### 13.2 First-person shell subsystem

Best interpretation:

- shell choice is deeper than staged `handModel`
- live survivor-state/runtime ownership still decides the accepted shell

### 13.3 Model subsystem

Best interpretation:

- custom models can load and exist live
- visible ownership still depends on the deeper consumer object model

### 13.4 FX subsystem

Best interpretation:

- foreign FX can be normalized into a T6-accepted render contract
- this lane is largely solved

### 13.5 Animation subsystem

Best interpretation:

- custom xanim payloads can be emitted and loaded
- visible playback depends on hidden consumer-side ownership/lookup resolution
- the unresolved problem is now engine selection logic, not asset existence

## 14. What this means for getting custom anims working

The repo is no longer blocked on "can custom anims exist."

It is blocked on:

- finding the runtime value the engine actually obeys when selecting the live first-person ownership/lookup path

Current likely flow:

1. `render_state_edi` is the live root
2. `child_2` holds compact ownership/state/handle data
3. the engine decodes or indexes that compact state indirectly
4. that decode selects or materializes the downstream lookup/descriptor family
5. the downstream family determines whether stock/donor/custom becomes the visible winner

Practical implication:

- once that hidden mapping is decoded, the remaining work should stop being blind experimentation
- the fix should become a concrete binding/contract problem:
  - emit the right compact state
  - patch the right lookup/table entry
  - or redirect the ownership chain to the custom runtime family

## 15. Current blocker

The current blocker is no longer broad debugging.

It is now:

- recover the intermediate decode / table / handle step between `child_2` and the upstream/render lookup family

In plainer terms:

- the repo already has the likely compact key object
- the repo already has the likely downstream lookup family
- the missing piece is the mapping between them

## 16. Recommended next work

Do:

- keep the frozen custom idle lane
- keep `render_state_edi` as the root object
- treat `child_2` as the highest-value compact ownership/state lead
- use upstream-hit recovery when it appears
- focus on one-hop table/handle correlation and stronger semantic transitions

Do not:

- go back to launcher experimentation
- go back to generic "is the asset loaded" scans
- widen back to full-family animation work yet
- demote `child_2` without stronger contradictory evidence

## 17. Short version

The engine map today is:

- stock runtime contracts are accepted more readily than fresh custom ones
- custom FX is largely solved
- custom models can load and attach under accepted carriers
- custom xanim data can be staged and loaded
- visible first-person animation is controlled by a hidden runtime ownership/lookup path
- `render_state_edi` is the best current live root for that path
- `child_2` is the strongest compact owner/state/handle candidate
- `child_3` looks like a richer downstream descriptor sidecar
- the unresolved step is the indirect mapping from `child_2` into the upstream/render lookup family

That is the current frontier of the repo.

## 18. Producer-Family Control Map Update

The current animation frontier is no longer the old `render_state_edi` / `child_2` object-model lane by itself.

The newer live producer-family work established a practical control map that matters more for visible first-person animation takeover.

### 18.1 Same-process starter->probe trio transplant

`Proven`

Authoritative control:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_013747/same_process`

Authoritative same-process trio transplant:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_013814/same_process`

What is now proven:

- starter-side `class_plus_2/+3/+4` can be captured
- the process can remain alive through `post_switch`
- the first later distinct probe-side producer family can be patched in the same process

Meaning:

- the stale cross-run pointer-family confounder is no longer the main excuse for trio-causality uncertainty

### 18.2 Current producer-side role split

`Proven`

The current best live role split on the later producer family is:

- `class_plus_3 + class_plus_4`
  - strongest direct drivers of later render-family divergence
- `class_plus_2`
  - likely binding/topology preservation field needed to keep joined selector-state alive
- `class_plus_5`
  - secondary compact family-code candidate

### 18.3 Why `class_plus_2` is now special

`Proven`

Accepted same-bucket `same_process_plus234` run:

- changed later render family
- preserved `joined_surface_seen = true`

Accepted same-bucket `same_process_plus34_only` run:

- still changed later render family
- but dropped `joined_surface_seen = false`

Meaning:

- `class_plus_2` is not required to perturb later render
- but it currently looks required to preserve the downstream joined selector surface on the same normalized bucket

### 18.4 Current earliest practical control surface

`Proven`

The earliest practical live patch surface that measurably changes later render outcome is now:

- later producer family:
  - `class_plus_2`
  - `class_plus_3`
  - `class_plus_4`

This is a stronger statement than the older passive tracing conclusions:

- it is no longer just an inferred control surface
- it is a live patch surface that changes downstream render materialization

### 18.5 What is still not proven

`Unknown`

Still not proven:

- that same-process `class_plus_2/+3/+4/+5` can recover a clean accepted same-bucket run
- that the later producer trio is sufficient for a visible custom animation takeover
- whether the real ultimate control point is:
  - exactly the later producer trio,
  - or the earlier writer/provenance path that populates that trio

### 18.6 Practical current engine map

Current best practical interpretation:

1. producer-side family appears
2. later producer-family `class_plus_3/+4` steer later render-family divergence
3. `class_plus_2` helps preserve joined selector-state while that happens
4. downstream selector-root / joined surface / child chain still sit below that producer layer
5. visible custom animation is still blocked either by:
   - incomplete later-family takeover,
   - or an earlier writer path that must be controlled instead of the already-materialized trio

### 18.7 Producer writepath boundary update

`Proven`

Authoritative writepath run:

- `_build/bo3_rev_idg_probe/producer_target_family_writepath/20260404_022949/producer_target_family_writepath_summary.json`

Same-process accepted control:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_022949/same_process`

What is now proven:

- the first later distinct producer family on the accepted `0x000F0105 -> 0x01120105` bucket can be targeted directly
- a short single-step provenance trace can be armed on that later family at the first recovered `consumer_asset_class_lookup` hit
- on that accepted bucket, the later family arrives fully formed there:
  - `class_head`
  - `class_plus_2`
  - `class_plus_3`
  - `class_plus_4`
  - `class_plus_5`
  - `class_plus_6`
  all stay unchanged through the traced first-hit window

Meaning:

- later producer-family `class_plus_2/+3/+4/+5` is still the earliest practical recovered control surface for render divergence
- but it is not the earliest observed writer site
- the actual writer/provenance boundary is now earlier than the first recovered `consumer_asset_class_lookup` hit on the accepted bucket

Practical engine-map consequence:

1. same-process later-family transplant work remains valid causal evidence
2. but provenance now has to move earlier than the first recovered asset-lookup family
3. the next likely live producer frontier is:
   - the caller / wrapper / pre-entry path that emits the later producer family before first recovered hit

### 18.8 Entry-first same-process boundary update

`Proven`

Producer-mode same-process partial archive:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_023600/same_process`

What is now proven:

- on the same-process lane, `consumer_asset_lookup_entry` can be the first recovered consumer hit before any later `consumer_asset_class_lookup` family is recovered
- the recovered entry wrapper is already prepopulated there:
  - `minus3 = 0x033F4D50`
  - `minus1 = 0x033F0380`
  - `plus3 = 0x033F4D50`
- the recovered stack-return family for that entry-first lane is:
  - `0x00341F6C`
  - `0x02FF4D50`
  - `0x02FF0380`
  - `0x0036EE73`

Meaning:

- provenance is earlier than the first recovered later producer family
- and it is earlier than the recovered `consumer_asset_lookup_entry` wrapper too
- so the next practical engine-map frontier is the caller / stack-return producer family feeding the prepopulated entry wrapper

### 18.9 Entry-return bridge family update

`Proven`

Authoritative bridge summary:

- `_build/bo3_rev_idg_probe/entry_return_bridge_override_matrix/20260404_032806/entry_return_bridge_override_matrix_summary.json`

What is now proven on the corrected same-process entry-first lane:

1. `consumer_upstream_ret_00341F6C` is a real bridge between:
   - first recovered `consumer_asset_lookup_entry`
   - first recovered `consumer_asset_class_lookup`
   - the next entry cycle
2. the bridge bucket already splits into stable module-pointer families before any later distinct producer family is recovered
3. those bridge families correlate with different first recovered producer compact families

Recovered bridge families:

- family A:
  - `minus1 = 0x033F0380`
  - `plus3 = 0x033F4D50`
  - first recovered producer compact:
    - `class_plus_5 = 0x000F0105`
    - `class_plus_6 = 0x00000201`
- family B:
  - `minus1 = 0x033ED240`
  - `plus3 = 0x033F3790`
  - first recovered producer compact:
    - `class_plus_5 = 0x00020105` or `0x000E0105`
    - `class_plus_6 = 0x00000201`

Practical engine consequence:

- the live frontier is now earlier than:
  - selector-root
  - later producer-family `class_plus_2/+3/+4/+5`
  - the first recovered `consumer_asset_lookup_entry` wrapper considered as a single undifferentiated object
- the active earlier branch split is now best described as:
  - normalized entry-return bridge family at `consumer_upstream_ret_00341F6C`

Current best causal interpretation:

1. first entry wrapper appears already prepopulated
2. first asset-lookup producer family appears
3. `consumer_upstream_ret_00341F6C` bridges into the next entry cycle
4. the bridge family (`0x02FF0380/0x02FF4D50` vs `0x02FED240/0x02FF3790`) already shapes which compact producer family is recovered next
5. later producer-family takeover and downstream render materialization are therefore downstream of that bridge bucket, not the first place where branch identity begins

### 18.10 Bridge-local causal role update

`Proven`

Authoritative bridge-bucket causal summary:

- `_build/bo3_rev_idg_probe/entry_return_bridge_override_matrix/20260404_085014/entry_return_bridge_override_matrix_summary.json`

Mirror bridge-bucket summary:

- `_build/bo3_rev_idg_probe/entry_return_bridge_override_matrix/20260404_091236/entry_return_bridge_override_matrix_summary.json`

What is now proven:

1. normalized `consumer_upstream_ret_00341F6C` bridge families are not just correlated with later producer families
2. patching bridge-local `plus3` inside a pinned bridge bucket changes the first recovered producer family
3. the same bridge-local `plus3` effect is recoverable on both family-A and family-B buckets
4. bridge-local `minus1` is still live and patchable, but not yet isolated as an equally strong independent driver

Family A bucket:

- required bridge:
  - `minus1 = 0x033F0380`
  - `plus3 = 0x033F4D50`
- control first producer compact:
  - `0x000F0105`
- `plus3` patched to family-B value:
  - first producer compact -> `0x000A0105`
  - later distinct compact -> `0x010D0105`
- `minus1 + plus3` patched together:
  - first producer compact -> `0x00020105`

Family B bucket:

- required bridge:
  - `minus1 = 0x033ED240`
  - `plus3 = 0x033F3790`
- accepted `plus3` patch to family-A value:
  - first producer compact -> `0x00120105`
  - later distinct compact -> `0x01150105`

Practical engine consequence:

- the bridge-local branch decision is now live-causal, not just inferred
- `plus3` is the strongest currently recovered upstream causal field before first producer-family selection
- the remaining hard problem is not bridge discovery anymore
- it is the unstable carry-forward from bridge-local `plus3` change into later render-family takeover and then visible first-person custom animation

### 18.11 Track split resolution: upstream bridge control and downstream practical render control

The work was split into two explicit tracks:

- Track A: bridge provenance / earlier-than-producer control
- Track B: practical later-family control inside one normalized same-process bucket

Both tracks now produced real results.

`Track A proven`

- `consumer_upstream_ret_00341F6C` is a real upstream control surface
- normalized bridge-local `plus3` is the strongest recovered causal field there
- patching bridge `plus3` changes the first recovered producer family

`Track B proven`

Normalized same-process control bucket:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_013747/same_process`

Accepted same-bucket practical-control run:

- `_build/bo3_rev_idg_probe/consumer_semantic_transitions/20260404_013814/same_process`

What Track B proves:

- later producer-family `class +2/+3/+4` is a real downstream practical control surface
- same-process transplant of that trio preserves joined-surface recovery
- later render family changes from the normal control page to a different render page in the same process

That means the repo now has a two-layer causal model:

1. earlier branch selection/control:
   - bridge `plus3`
2. later practical render-takeover control:
   - producer-family `class +2/+3/+4`

What is *not* proven:

- visible custom first-person animation
- independent sufficiency of later-family `class +5`
- stable same-bucket carry-forward from bridge-local change all the way through later render and visible motion

Practical engine consequence:

- the problem is no longer broad engine archaeology
- the hard remaining step is stable carry-forward between the proven upstream bridge control layer and the proven downstream later-family render-takeover layer
## Update - 2026-04-04 bridge handoff split

Latest carry-forward reruns:

- `_build/bo3_rev_idg_probe/bridge_later_carry_forward_matrix/20260404_102117/bridge_later_carry_forward_matrix_summary.json`
- `_build/bo3_rev_idg_probe/bridge_later_carry_forward_matrix/20260404_104025/bridge_later_carry_forward_matrix_summary.json`

Net result:

- no accepted composed bridge-plus-later-family carry-forward case
- combined bridge `plus3` + later-family `class +2/+3/+4` still does not reliably preserve joined surface and later render in the same normalized run

New analyzer:

- `tools/analyze_bridge_handoff_chains.ps1`
- `_build/bo3_rev_idg_probe/bridge_handoff_chain_analysis/20260404_105455/bridge_handoff_chain_summary.json`

Recovered model update:

- proven upstream control surface:
  - bridge-family `plus3` at `consumer_upstream_ret_00341F6C`
- proven downstream practical control surface:
  - later-family `class +2/+3/+4`
- unresolved layer:
  - bridge output -> productive first producer family -> later-family render materialization

Important chain examples:

- productive:
  - `0x033ED240/0x033F3790 -> 0x00120105/0x00000201 -> 0x01150105/0x00000201 -> 0x2F3Cxx`
  - `0x033F0380/0x033F4D50 -> 0x00020105/0x00000201 -> 0x01050105/0x00000201 -> 0x30AAxx`
- collapsed:
  - `0x033F0304/0x033F4E40 -> 0x00010101/0x00000003 -> none -> none`
  - `0x033ED204/0x033F3880 -> 0x00010101/0x00000003 -> none -> none`

Meaning:

- the unresolved problem is no longer "find the bridge" or "find the later-family driver"
- it is the normalization/provenance step that decides whether a bridge bucket collapses at the first producer family or continues into later-family render materialization
## 14) Handoff Update: bridge and first-producer field patching change early producer state but still do not force carry-forward (2026-04-04)

Authoritative summaries:

- `_build/bo3_rev_idg_probe/bridge_to_first_producer_carry_forward_matrix/20260404_114902/bridge_to_first_producer_carry_forward_matrix_summary.json`
- `_build/bo3_rev_idg_probe/bridge_to_first_producer_carry_forward_matrix/20260404_120356/bridge_to_first_producer_carry_forward_matrix_summary.json`

Recovered behavior:

- Hit-1 first-producer compact state is patchable, but promoting it does not create a later producer family or later render family.
- Example:
  - `20260404_115104/same_process`
  - initial compact changed `0x00020105 / 0x00000201 -> 0x00120105 / 0x00000201`
  - later producer family: none
  - later render family: none
- Bridge-only control is also insufficient on this lane:
  - `20260404_120838/same_process`
  - bridge family recovered as `0x033ED240 / 0x033F3790`
  - first producer compact recovered as `0x000A0105 / 0x00000201`
  - later producer family: none
  - later render family: none

Current interpretation:

- The unresolved handoff is not just the compact pair at hit 1.
- It is the bridge→first-producer normalization/emission step that decides whether the first producer family is merely an early observed family or a productive family that will carry forward into later-family render materialization.

Current frontier:

- provenance / writer recovery for the bridge→first-producer emission path
- not more selector-root work
- not more hit-1 first-producer field matrices unless new provenance evidence appears
## 16) Emitter Provenance Update: bridge/entry emitter trace is live, but not yet stable enough to recover the first-producer writer path (2026-04-04)

Authoritative summaries:

- `_build/bo3_rev_idg_probe/bridge_to_first_producer_emitter_provenance/20260404_132602/bridge_to_first_producer_emitter_provenance_summary.json`
- `_build/bo3_rev_idg_probe/bridge_to_first_producer_emitter_provenance/20260404_133727/bridge_to_first_producer_emitter_provenance_summary.json`

What exists now:

- a dedicated bridge/entry provenance trace in the native hook
- a dedicated provenance runner
- trace events for:
  - trace armed
  - first producer candidate birth
  - trace complete

What the current runs say:

- the provenance lane is still too unstable to recover an accepted traced emitter path on the same-process bucket
- productive retries can still land on productive render pages
- but they are not yet accompanied by a usable bridge→first-producer birth/mutation trace

Meaning:

- the unresolved engine map remains the same:
  - bridge / entry family
  - emission / normalization path
  - first producer family
  - later producer family
  - later render family
- but the direct provenance capture of the emission step is not stable enough yet to answer the writer question

Current practical frontier:

- stabilize the bridge-friendly emitter trace lane
- or recover the same provenance on a more stable entry-first bucket
- not more downstream field patching
## 17) Provenance Stability Update: the bridge→first-producer trace lane is now correctly configured, but still drifts across entry buckets before a full emission sequence is recovered (2026-04-05)

Current map refinement:

- bridge discovery: solved
- later-family practical control: solved
- remaining unresolved layer: bridge→first-producer emitter / normalizer

What this pass removed from the problem:

- the old config-path confusion is dead
- the dedicated provenance config file is now the file actually loaded by the live producer lane
- the logged producer config now correctly reflects:
  - `trace_bridge_to_first_producer=1`
  - `stop_after_bridge_candidate_birth=1`
  - required bridge bucket
  - no startup render arming
  - no follow-on render

What the live lane is still doing:

- the same-process entry-first provenance lane drifts across multiple wrapper families before the trace can normalize:
  - `0x033F0304 / 0x033F4E40`
  - `0x033F0380 / 0x033F4D50`
  - `0x033ED204 / 0x033F3880`
- because of that:
  - some runs never arm the trace on the selected bucket
  - some runs reach productive producer families without a traced birth/complete pair
  - no accepted bridge→first-producer emission sequence is recovered yet

Important implication:

- the blocker is no longer instrumentation existence
- it is the unstable provenance lane itself
- the next correct engine step is still provenance stabilization on one productive bridge bucket, not more selector/later-family patch matrices
## 18) Provenance Stability Success: the productive bridge bucket now has a clean accepted handoff trace (2026-04-05)

The bounded provenance phase succeeded on one productive bridge bucket.

Authoritative summary:

- `_build/bo3_rev_idg_probe/bridge_to_first_producer_emitter_provenance/20260405_143131/bridge_to_first_producer_emitter_provenance_summary.json`

Accepted productive bridge bucket:

- `minus1 = 0x033F0380`
- `plus3 = 0x033F4D50`

Recovered accepted sequence:

1. `bridge_to_first_producer_trace_armed`
2. `bridge_first_producer_candidate_birth`
3. `bridge_to_first_producer_trace_complete`

Recovered one-step emitter:

- `eip = 0x00741AE1`
- `reg = ecx`
- `class = 0x5F8C9070`

Recovered seed/normalization object at that step:

- `class_head = 0x01010101`
- `class_plus_2 = 0x01010101`
- `class_plus_3 = 0x01010101`
- `class_plus_4 = 0x00000001`
- `class_plus_5 = 0x00000001`
- `class_plus_6 = 0x00000001`

Then the later first recovered producer family appears downstream at `consumer_asset_class_lookup` as:

- `class = 0x2D889A7C`
- `class_head = 0x2D88D440`
- `class_plus_2 = 0x2D88BB20`
- `class_plus_3 = 0x2D889A9C`
- `class_plus_4 = 0x2D88BB94`
- `class_plus_5 = 0x00020105`
- `class_plus_6 = 0x00000201`

Engine-map consequence:

- stable bridge bucket provenance is no longer the blocker
- the earliest recovered post-bridge emitter is now the one-step `ecx` seed / normalization object
- the remaining unresolved handoff is:
  - how that seed object is turned into the later real first producer family

Current frontier:

- not more broad bridge stabilization
- not later-family-only patching
- now specifically the source-side normalization path immediately after `0x00741AE1`
## 19) Source-Side Identity Update: the seed object is the later `source/owner_plus_4`, and class-family materialization happens off that stable object (2026-04-05)

Authoritative summary:

- `_build/bo3_rev_idg_probe/seed_to_first_producer_normalization/20260405_144553/seed_to_first_producer_normalization_summary.json`

Recovered accepted relationship:

- seed birth:
  - `eip = 0x00741AE1`
  - `reg = ecx`
  - `seed = 0x5FA69070`
- first producer-family appearance:
  - `owner = 0x5FA69000`
  - `owner_plus_4 = 0x5FA69070`
  - `source = 0x5FA69070`
  - `class = 0x2DC89A7C`

Engine-map consequence:

- the seed object is not a disposable pre-class transient
- it survives as the later stable source-side identity object
- the unresolved normalization/emission step is therefore:
  - `seed/source/owner_plus_4`
  - emits / resolves
  - `class/class_head/+2/+3/+4/+5/+6`

Important negative proof:

- the tracked seed/source core slots did not mutate in place
- so the later producer family is not created by simply mutating the tracked seed core

Current frontier:

- source-side class emission provenance off `seed == source == owner_plus_4`
- not more bridge provenance stabilization
- not more later-family-only patching first

## 20) Source-Class Emission Follow-up: the lane is now instrumented for source-neighborhood capture, but the latest rerun drifted off the productive bridge bucket (2026-04-05)

Authoritative summary:

- `_build/bo3_rev_idg_probe/seed_to_first_producer_normalization/20260405_145953/seed_to_first_producer_normalization_summary.json`

Engine-map consequence:

- no new control surface was discovered in this rerun
- the source-class emission lane is now instrumented to summarize source-neighborhood relations automatically
- the actual frontier is unchanged:
  - stable `source == owner_plus_4`
  - unresolved emission/resolution into later `class-family`

Observed drift buckets in the latest rerun:

- `0x033ED204 / 0x033F3880`
- `0x033ED240 / 0x033F3790`
- `0x033F0304 / 0x033F4E40`

Current frontier remains:

- source-side class emission on the productive bucket
- not bridge rediscovery
- not later-family-only patching
## 21) Determinism Checkpoint: productive source bucket is reacquirable, but the old accepted downstream takeover lane is still not (2026-04-05)

Authoritative summary:

- `_build/bo3_rev_idg_probe/animation_lane_determinism/20260405_155411/animation_lane_determinism_summary.json`

Engine-map consequence:

- the productive source-emission bucket is not lost
- the repo can still recover:
  - `bridge/wrapper = 0x033F0380 / 0x033F4D50`
  - `seed == source == owner_plus_4`
  - later first producer-family class materialization
- but the old accepted downstream same-process takeover lane is still not reproducible in the bounded determinism batch

Important new source-side negative proof from the accepted reacquired run:

- source-neighborhood capture does not show a trivial direct owner/class pointer in:
  - `source[-4]`
  - `source[-1]`

So the map is now:

- source-side class emission remains a valid unresolved control step
- but the practical animation blocker is downstream lane reproducibility:
  - accepted `same_process_plus234` takeover still does not reacquire reliably

Current frontier:

- if continuing practical animation work:
  - focus on downstream takeover / render-family reproducibility
- if continuing reverse engineering:
  - keep it narrowly on source-side class emission only
- do not reopen older bridge discovery or selector archaeology

## 22) Practical visible-motion forcing is now a prepared runner, but fresh execution is blocked by the local OAT linker architecture mismatch (2026-04-05)

Engine-map consequence:

- this is not a new engine-theory blocker
- it is a packaging/runtime-toolchain blocker

Prepared practical lane:

- `tools/run_practical_visible_motion_forcing.ps1`
- extends `tools/run_anim_debug_cycle.ps1` with:
  - `-RuntimeBackend`
  - `-ForceStockShell`
  - `-ForcedStockShell`
  - `-IdleDiagBone`
  - `-IdleDiagTranslate`
  - `-IdleDiagFrequency`
  - `-IdleStaticBone`
  - `-IdleStaticTranslate`

Purpose of that lane:

- bounded practical test on the live shell/tag surface
- oldman and farmgirl
- control vs forced visible-motion diagnostic build
- judged only by live motion deltas / visible-motion summary

Current blocker:

- fresh animation builds currently fail before runtime because:
  - `tools/oat/Linker.exe` is `x64`
  - `tools/oat/Linker.exe.bak_031717` is also `x64`
  - T6 runtime packaging still requires `x86` linker binaries

Meaning:

- the project is no longer primarily blocked on where the engine decides
- it is currently blocked on:
  - downstream takeover reproducibility for no-build practical control
  - or missing x86 linker support for fresh practical animation builds

## 23) Practical pivot update: fresh practical builds are running again, but live runtime still resolves to an older script/build lane (2026-04-05)

- `tools/run_anim_debug_cycle.ps1` now supports `-SkipBuild`, live build-tag fallback, and timestamp-prefixed `games_mp.log` parsing.
- `tools/run_practical_visible_motion_forcing.ps1` can now reuse existing runtime builds.
- `_build/build_bo3_rev_idg_probe.py` now renders `mod_i_am_mod.gsc` to both repo and work outputs.
- missing `mods/bo3_rev` template files were restored from the known-good quarantine mod copy.

Recovered facts:

- no-build practical observation now resolves the active runtime tag and reaches valid connect/grant markers.
- fresh practical builds now complete again with intended diagnostic args.
- but the launched runtime still reports old live tag `0402021252_67ac52`, not the fresh practical build tag `0405233950_75d444`.

Meaning:

- practical animation work is no longer blocked on linker architecture or stale verdict parsing.
- the current blocker is a runtime-source split: fresh practical build artifacts are produced, but the game still executes an older live script/build lane.

## 24) Practical late-attach lane is now reproducible at raw-runtime level; blocker moved to post-attach accepted-verdict carry-through (2026-04-05)

What changed:

- `tools/restart_t6_probe_cycle.ps1`
  - now supports `-ProbeAttachGate` values:
    - `startup`
    - `connect`
    - `grant`
    - `first_raise_begin`
    - `idle_begin`
    - `fire_begin`
- `tools/run_anim_debug_cycle.ps1`
  - now supports late-attach gating through `-ProbeAttachGate`
  - now sets longer default attach windows for non-startup gates
  - now snapshots logs before launch/injection so late-attach runs retain pre-attach event history
- `tools/run_practical_visible_motion_forcing.ps1`
  - now drives the practical lane with `-ProbeAttachGate idle_begin`

Authoritative practical archive:

- `_build/bo3_rev_idg_probe/anim_debug_runs/20260405_194254_custom_idle_first_raise_observe_only`

What this archive proves:

- the practical mod lane reaches the real map/match again on the restored downstream path
- the same run contains:
  - `Loading fastfile so_zsurvival_zm_transit`
  - `[bo3_rev][start]`
  - `[bo3_rev][connect]`
  - `[bo3_rev][grant]`
  - `[bo3_rev][anim_probe] first_raise_begin/end`
  - `[bo3_rev][anim_probe] idle_begin`
- the forced visible shell is active in the same run:
  - `c_zom_farmgirl_viewhands`
- late probe attach is also real in the same run:
  - `fx_runtime_probe loaded pid=68960 build=20260405_145516`

Important interpretation:

- the practical downstream lane is no longer blocked on launch reproducibility
- the practical downstream lane is no longer blocked on probe attaching only at startup
- the remaining blocker is narrower:
  - post-attach carry-through into a fully accepted verdict / stable takeover lane

Current honest state:

- raw-runtime visible-capable lane: reproducible
- fully accepted practical debug verdict: not yet reproducible
- the next practical work should stay downstream:
  - accepted-takeover carry-through
  - visible-motion forcing on the restored late-attach lane

## 25) Visibility isolation: invisible weapon is a first-person bind/composition failure before animation forcing (2026-04-05)

Practical meaning:

- if the weapon is fully invisible, the current lane is not yet a valid visible first-person lane
- animation-selection debugging is secondary until the model bind is visible

Build-side isolation added:

- `tools/build_servant_minimal_anim_runtime.ps1`
  - now supports:
    - `-GunModelMode custom|base|literal`
    - `-ForceLowHandmodel`
    - `-DisableStockSurvivorCarrier`
    - `-UseCustomIdgViewhands`

Authoritative build-side visibility controls:

- stock gun control:
  - `_build/bo3_rev_idg_probe/build_report_visibility_stock_base.json`
- safer custom-gun composition:
  - `_build/bo3_rev_idg_probe/build_report_visibility_custom_lowhand.json`

Recovered composition facts:

- stock gun control:
  - gun = `t6_wpn_zmb_mg08_view`
  - hand = `c_zom_hazmat_viewhands`
  - predicted totals:
    - hazmat = `141 nodes / 130 joints`
    - suit = `142 nodes / 130 joints`
  - both under `160`

## Recent correction: default visibility lane was still invalid

- The repo was still defaulting plain builds to the custom BO3 gun model lane.
- The live `build_report.json` for that lane showed combined first-person estimates of:
  - `206 nodes / 201 joints` with suit viewhands
  - `206 nodes / 201 joints` with hazmat viewhands
- That is above the repo's practical T6 first-person cap of `160`.
- Defaults were corrected on `2026-04-06` so the implicit build/debug lane is now:
  - `gun_model_mode = base`
  - stock survivor carrier enabled by default
  - stock-visible baseline rebuilt under build tag `0406073807_7eef05`

## Recent correction: minimal transit client carrier no longer fails at clientfield registration

- `mods/bo3_rev/clientscripts/mp/zm_transit.csc.in` now registers the missing town-survival clientfield contract pieces:
  - `playerinfog`
  - `screecher_light_*`
  - perk clientfields through stock flags before `_zm::init()`
- it also suppresses the unsupported extras that were causing mismatch by:
  - setting `level._no_water_risers = 1`
  - constraining the included powerup subset to the town-safe set
- The old `Client and server clientfield registrations don't match` gate is no longer the active blocker on the rebuilt stock-visible baseline.
- safer custom composition:
  - gun = `bo3_rev_v2_idg_view_0406020649_150ab9`
  - hand = `bo3_rev_bridge_viewhands`
  - predicted totals:
    - hazmat = `136 nodes / 129 joints`
    - suit = `137 nodes / 129 joints`
  - both under `160`

Interpretation:

- the earlier invisible lane should no longer be treated as an animation-only problem
- the repo now has two visibility-safe composition controls on disk
- the currently synced runtime was last rebuilt on the safer custom-gun + low-handmodel path

## 26) Startup root cause closed: stock server plus stripped transit client now reaches live connect/grant/idle (2026-04-06)

This pass closed the startup/mismatch side of the project.

What was actually wrong:

- stale loose carrier server scripts under `mods/bo3_rev/maps/mp` and AppData were still forcing the stripped cosmodrome carrier path
- even after removing those loose server overrides, the base/full-map lane still deleted the loose `clientscripts/mp/zm_transit.csc` override, so the client fell back to stock full transit registrations
- the first stripped client override then failed on stock script-mover animtree ordering until the stock bus/automaton/turbine init order was restored
- after that, the only missing world registrations were the `screecher_light_*` fields

What was changed:

- `tools/launch_t6_offline.ps1`
  - now removes stale loose carrier map scripts from both repo mod runtime and AppData
  - syncs `clientscripts/mp/zm_transit.csc` when present
- `tools/restart_t6_probe_cycle.ps1`
  - carrier-map sync is now opt-in only
  - removes stale carrier loose scripts by default
  - resolves `zm_transit.csc` from the repo/runtime path directly
- `_build/build_bo3_rev_idg_probe.py`
  - no longer deletes the loose transit client override just because `USE_MAP_FULL_ZONE_SOURCE=1`
- `mods/bo3_rev/clientscripts/mp/zm_transit.csc.in`
  - now preserves stock zombie-core client registrations
  - preserves stock script-mover animtree init order:
    - `zm_transit_bus::init_animtree()`
    - `zm_transit_bus::init_props_animtree()`
    - `zm_transit_automaton::init_animtree()`
    - `_zm_equip_turbine::init_animtree()`
  - restores only the world `screecher_light_*` registrations the current stock server exports
  - strips the transit extras that were mismatching this lane:
    - vehicle bus clientfields
    - `power_rumble`
    - allplayers `screecher_*` / `sq_tower_sparks`

Authoritative live result:

- current stock baseline reaches:
  - `[bo3_rev][connect]`
  - `[bo3_rev][grant]`
  - `first_raise_begin/end`
  - `pullout_begin/end`
  - `idle_begin/end`
- current live shell remains:
  - `vm=c_zom_engineer_viewhands`
- current granted stock-visible weapon remains:
  - `weapon=mg08_zm`
  - `model=t6_wpn_zmb_mg08_view`

Meaning:

- startup/clientfield mismatch is no longer the active blocker
- script-mover animtree order mismatch is no longer the active blocker
- the next live blocker is back where it should be:
  - first-person visibility / animation behavior on a working in-map stock baseline

2026-04-06 stock-control visibility checkpoint
---------------------------------------------

New operational lane:

- `tools/run_stock_visibility_control.ps1`
  - script-only stock control
  - `probe_weapon = m1911_zm`
  - `starter_weapon = m1911_zm`
  - stock survival zone
  - no forced stock shell
  - no BO3 anim lane
  - archives screenshot plus per-run log deltas

Authoritative run:

- archive:
  - `_build/visibility_live/20260406_073637_stock_control`
- build tag:
  - `stockctl_20260406_073637`

Recovered live lane:

- `[bo3_rev][connect]` and `[bo3_rev][grant]` both occur on the stock control
- granted weapon:
  - `m1911_zm`
- live shell:
  - `vm=c_zom_reporter_viewhands`
- first-person stock tags are defined and moving:
  - `tag_flash`
  - `tag_weapon`
  - `tag_brass`
- `tag_clip` stays `<undef>` on this pistol lane

Interpretation:

- the engine does still produce a live first-person shell/object on the corrected baseline
- first-person visibility is not globally broken
- the custom `mg08_zm` failure path is now the narrower blocker

Still-missing install/runtime content on this host:

- `zm_transit_common` ipak missing at map load
- stock `so_zsurvival_zm_transit.ipak` missing at map load
- many stock zombie weapons fail client load during init

Practical consequence:

- do not treat the current custom `mg08_zm` invisibility as proof that stock first-person rendering is dead
- use the stock-control lane as the new reference floor, then compare the custom survival/weapon lane against it
## 2026-04-06 correction: restored stock control is alive again

The practical stock control had regressed because `tools/run_stock_visibility_control.ps1` disabled the loose `zm_transit.csc` sync. Re-enabling that sync restored the stock pistol control to a coherent town-survival runtime again.

Fresh authoritative baseline:

- `stockctl_20260406_130915`
- `m1911_zm`
- `t6_wpn_pistol_m1911_view`
- `grant` and `idle_begin` both occur
- `tag_flash`, `tag_weapon`, and `tag_brass` move on the stock lane again
- manual capture: `_build/visibility_live/20260406_130915_stock_control_manual.png`

Important interpretation:

- stock first-person startup is no longer dead
- animation probing is no longer blocked by the old clientfield/startup regression
- but visible first-person rendering is still broken even on the restored stock control

So the current blocker is now clean:

- not packaging
- not startup
- not clientfield mismatch
- not “weapon never grants”
- but the live first-person render/bind path, because the stock pistol lane now animates logically while still showing no visible weapon/hands on screen
