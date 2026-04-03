# Engine Map

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
