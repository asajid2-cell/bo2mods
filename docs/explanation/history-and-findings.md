# History and Findings

This is the detailed BO3 Rev Apothicon Servant experiment log. It is the main answer to:
- what we tried
- what failed
- what each failure actually proved
- what was changed to get from repeated crashes to the current working MG08 donor build

## Current checkpoint
The FX loader / bridge work is now past first-proof status.

Current checkpoint:
- MG08 donor shell remains the stable weapon carrier
- the visible MG08 bridge model is gone from the FX host path
- the full layered vortex renders on the live runtime lane
- repeated shots now replace an active vortex instead of silently doing nothing
- the current live checkpoint build is `0321232501_4c7e1d`
- the remaining visual problem is mild portal consistency / visible lifetime polish, not broad render failure
- BO3 gameplay parity work has started from the real local T7 scripts

For BO3 gameplay parity, the real T7 source is now local:
- [`_zm_weap_idgun.gsc`](/C:/Users/Ahmed/Downloads/t7-source/scripts/zm/_zm_weap_idgun.gsc)
- [`zombie_vortex.gsc`](/C:/Users/Ahmed/Downloads/t7-source/scripts/shared/ai/zombie_vortex.gsc)
- [`_zm_weap_idgun.csc`](/C:/Users/Ahmed/Downloads/t7-source/scripts/zm/_zm_weap_idgun.csc)

For the current persistent master timeline, also read:
- [`docs/explanation/master-deep-dive-timeline.md`](/z:/Games/pluto_t6_full_game/docs/explanation/master-deep-dive-timeline.md)

## 1. Original goal
The original goal was not "make a donor pretend to be the Servant forever." The original goal was:
- add a true `apothicon_servant_zm` style weapon identity
- load real BO3 Servant assets
- get BO3-like first-person presentation and black-hole behavior in BO2

That goal immediately split into two independent problems:
1. engine weapon identity / registration
2. first-person asset authoring and runtime compatibility

The project only started moving once those were treated as separate gates.

## 2. Fresh-name weapon identity experiments

### What was tried
The first approach tried to make BO2 accept:
- `apothicon_servant_zm`

as a real engine-recognized weapon through normal mod-lane registration and zombies inclusion.

The GSC was reduced to the smallest possible test:
- register
- grant `m1911_zm`
- grant `apothicon_servant_zm`

Registration timing was also moved earlier to avoid the obvious "you registered too late" failure.

### What the logs showed
The conclusive early-registration test showed:
- bootstrap ran before spawn
- zombies registration succeeded
- inclusion tables succeeded
- but engine queries still returned undefined ammo/clip data for the fresh name

The failure signature looked like:
- `clip=<undef>`
- `max=<undef>`
- every give path returned `has=0`

### What that proved
That result proved:
- this was not a late-registration problem anymore
- this was not a BO3 art problem anymore
- this was not a zombies inclusion-table problem anymore

It was an engine weapon identity problem.

### Conclusion
The repo now treats this as proven:
- a fresh-name Servant identity is blocked in the normal BO2/Plutonium mod lane used here

That does not mean "impossible in all circumstances." It means:
- not practical in the current supported workflow
- not worth blocking the whole project on

This is why the architecture pivoted to donor shells.

## 3. Donor-shell isolation

### First donor: `ray_gun_zm`
The Ray Gun was the obvious early donor because it was closer in fantasy and weapon class.

#### What was tried
- override `ray_gun_zm`
- prove override with impossible scalar values
- swap in different gun model paths

The override proof values were things like:
- `clipSize=7`
- `maxAmmo=77`

That let the runtime log prove whether stock or patched weapondef won.

#### What worked
The runtime proved the override could win on `ray_gun_zm`.

#### What failed
No matter what visible gun model path was used, the same crash kept coming back:
- `dobj for xmodel 'c_zom_*_viewhands' has more than 160 bones`

That happened even when the gun model was:
- a tiny custom probe model
- a stock BO2 RPG viewmodel
- effectively `viewmodel_usa_no_model`

#### What that proved
This was a major result.

It proved the crash was not simply:
- "your imported BO3 mesh has too many bones"

Instead, it pointed to:
- hidden first-person composition in the `ray_gun_zm` path
- shell-specific baggage beyond the obvious `gunModel` field

### Second donor sweep: `m1911_zm` and `m14_zm`
`m1911_zm` was used as a simpler non-Ray Gun control.

#### `m1911_zm` result
- no crash
- but override did not win

That meant it was not a useful acceptance shell for this lane.

#### `m14_zm` result
`m14_zm` became the next useful donor because:
- it was a simpler shell
- its weapon file already had a cleaner `handModel` path

This donor gave the first stable proof that:
- the BO3-derived model could load without the Ray Gun crash class

Its downside was fit:
- the model looked squashed or too tightly adapted to the M14 hand posture

### Current donor: `mg08_zm`
The donor was finally moved to `mg08_zm` because it was a better structural and visual fit:
- heavier wonder-weapon posture
- better hand relationship
- better overall silhouette fit

This is the current live donor shell.

## 4. Rig and bone-budget experiments

### Initial assumption that failed
The early assumption was that a literal BO3 first-person rig plus BO3 hands could be made to work directly.

That failed for two reasons:
1. BO3 and BO2 first-person rig contracts differ
2. T6 has a 160-bone first-person DObj cap

### What was measured
The project measured that the literal BO3 first-person path was too large for T6.

The solution was not "keep deleting random bones." The solution had to be:
- a reduced rig
- reweighted mesh
- a T6-safe first-person architecture

### Combined custom-viewhands path
There were several attempts to:
- replace stock zombie viewhands
- use custom viewmodel swaps
- bridge through low-bone custom viewhands

These attempts kept failing because stock `c_zom_*_viewhands` stayed in the runtime composition path or the swap path did not actually take.

### Weapon-only rig path
The breakthrough was moving to:
- a BO3-derived reduced weapon-only rig

instead of trying to make a full custom gun+hands path win immediately.

That let the model fit into BO2 without reopening the earlier full-viewhands crash class.

### What this proved
The project proved that the right question was not:
- "can BO2 load the whole BO3 first-person rig?"

The right question was:
- "what is the smallest BO3-derived rig that still preserves the Servant silhouette and can survive BO2 first-person limits?"

## 5. Material and IPAK pipeline experiments

### Invisible weapon stage
Once the donor and rig path started working, the next failure was:
- weapon loaded
- weapon could be equipped
- but the model was invisible

That phase turned out to be a placeholder-material issue.

### First real BO3 surface attempt
The next step tried to translate and stage real BO3-derived image-backed materials.

That caused a new failure:
- access violation during runtime load

### What caused that crash
The problem was not "the Servant textures are cursed." It was:
- the custom image-backed surface path existed
- but the runtime `.ipak` contract was incomplete

The fix required:
- explicitly emitting a runtime IPAK
- verifying it exists
- deploying the IPAK together with the FF

### Chrome/silver stage
Once the IPAK contract was fixed, the material path became visible, but the model turned into a chrome-like silver surface.

That was caused by:
- feeding BO3 gloss/spec content too directly into BO2 specular expectations

The fix was:
- soften and darken spec
- keep normals
- re-grade diffuse separately

### Missing chunks / black holes / emissive issues
The next round of fixes addressed:
- backface culling / missing chunks
- black cavity/orb surfaces
- wrong emissive shader/template choices

Fixes included:
- double-sided material handling
- better BO2 template selection
- per-surface texture selection and grading
- separate handling for glow-style surfaces instead of treating everything like a normal lit body surface

### Current material state
The material path is now good enough to keep developing gameplay on top of it:
- no longer invisible
- no longer chrome
- major missing-surface issues mostly fixed

What remains is fidelity:
- some body colors are still muted compared to BO3
- glow/emissive surfaces are still approximate, not fully authentic

## 6. Native runtime hook experiment

### Why it was created
At one point, normal logs and build reports were not enough to explain the Ray Gun composition crash.

A local native hook project was created under:
- `native/dobj_probe/`

Its purpose was to inspect first-person DObj assembly more directly.

### Why it was shelved
The reason it is not part of the default workflow is simple:
- client injection on Plutonium carries anti-cheat risk outside safe local/LAN conditions

So the source is retained as R&D, but the normal project path does not depend on it.

## 7. Gameplay logic port

### Decision
The project did not attempt a literal direct BO3 GSC drop-in.

Instead, it used:
- BO3 Servant behavior as the spec
- BO2/T6-safe primitives for the implementation

### What got implemented
The current live logic does this:
1. watch `weapon_fired` on the donor shell
2. trace an impact point
3. spawn a timed singularity entity

## 8. Raw BO3 FX porting

### What changed in the project understanding
Early on, BO3 Servant FX were treated mostly as references:
- BO3 asset names
- BO3 GDT references
- placeholder BO2-safe fallbacks

That was good enough to keep moving gameplay forward, but it was not the real end goal.

The current understanding is more precise:
- BO3 raw `.efx` can be treated as source assets
- local OAT can be extended to parse them
- local OAT can then emit T6-native `FxEffectDef`
- BO2 can consume those linked T6 assets like any other effect

In other words, the problem is not "BO2 cannot ever use BO3 raw FX."
The problem is:
- whether the local raw loader understands enough of the BO3 graph

## 9. BO3 animation emitter diagnosis

### What was finally proven
The BO3 animation problem turned out to be narrower than "BO2 cannot load BO3 xanims."

The project now has hard proof for all of these:
- `mod_load.ff` itself can load
- a tiny BO3 xanim asset can load
- a large BO3 xanim asset can also live in `mod_load.ff`
- the native access violation only appears when a custom-emitted BO3 `XAnimParts` payload is actually assigned to the weapon and consumed by the runtime

That means the failure is not primarily:
- GSC
- fresh-name weapon identity
- `mod_load.ff` presence by itself
- or the old `>160 bones` DObj limit

It is a custom `XAnimParts` runtime-contract problem.

### Donor-clone oracle
The key breakthrough was creating a donor-clone oracle for:
- `vm_zod_id_gun_idle`

The donor-clone branch proved that:
- a renamed donor payload under the BO3 alias does not crash
- the alias/bind path is valid
- but the pose/camera are wrong, because the donor anim is not authored for the Servant rig

That is why donor-clone is useful only as an oracle, not as a final solution.

### Contract diffs that mattered
The project added:
- `_build/compare_xanim_contracts.py`

and used it to compare the stable donor-clone payload against custom-emitted BO3 idle payloads.

The important differences were:
- donor payload:
  - `assetType=1`

## 10. Runtime FF and client-ownership deep dives

### What changed in understanding
The project stopped being only about Servant FX. It became clear that there were three separate layers:
1. BO3 asset translation
2. custom FF/IPAK correctness
3. runtime ownership of the clientscript path

Those had been getting conflated because the symptom kept looking the same:
- nothing visible

### What was actually fixed

#### x86 custom OAT correction
The local custom OAT binaries had been built as `x64`, while the working stable lane was `x86`.
That broke T6 DB-layout-sensitive serialization and caused structurally bad custom FF outputs.

Fix:
- rebuild custom `Linker.exe` / `Unlinker.exe` as `Win32`

#### T6 streamed-image hash bug
The T6 image loader path had a real hash bug:
- streamed images were being emitted with `hash = 0`

That made image lookup inside IPAKs impossible even when the image bytes existed.

Fix:
- correct the T6 image hash assignment path

#### Minimal custom FF proof
The project then proved:
- a minimal custom `mod_load.ff`
- with a minimal `mod_load.ipak`
- can load safely at runtime

This mattered because it proved the custom asset lane itself is not universally impossible.

### What that proved
At that point, the current blocker was no longer:
- "custom FFs are impossible"

It became:
- "which runtime ownership path is actually honored for `zm_transit.csc`?"

## 11. Client probe ownership findings

### What was tried
- server-side `ffprobe` in `mod_i_am_mod.gsc`
- `mod_patch.ff`
- loose clientscript overrides
- tiny same-name `so_zsurvival_zm_transit.ff`
- full rebuilt `so_zsurvival_zm_transit.ff`

### What the project learned

#### Server probe is not client probe
Server `loadfx/playfx` success only proved server-side asset lookup/playback.
It did not prove client rendering.

#### `mod_patch.ff` is not enough to own `zm_transit.csc`
It can load, but it does not reliably take ownership of the map clientscript.

#### Tiny same-name runtime override is too stripped
A tiny replacement `so_zsurvival_zm_transit.ff` can take ownership, but it breaks the zone contract and causes unresolved externals/startup failure.

#### Full runtime FF path is the real owner
The only ownership path that actually produced trustworthy client execution is the full rebuilt `so_zsurvival_zm_transit.ff` path.

### What it proved
The ownership problem is now solved in principle.

Current proof:
- `[ffprobe][csc] helper init reached ...`
- `[ffprobe][csc] init ...`

That means the client helper is finally executing on the real runtime ownership lane.

## 12. Current blocker: rebuilt runtime-zone startup fidelity

### What now happens
The client helper initializes successfully, but the game still crashes before spawn.

The current repeated warning closest to the crash is:
- `Could not load material "zombie_transporter_overlay"`

### What that means
This is no longer a BO3 FX render verdict.
It is a startup/runtime-zone fidelity problem.

The engine is now getting far enough to:
- execute the client helper

but not far enough to:
- reach spawn
- run the probe playback

### Current interpretation
The rebuilt full `so_zsurvival_zm_transit.ff` is still not faithful enough to stock startup behavior.

That makes the current blocker:
- full runtime-zone rebuild fidelity

not:
- BO3 render semantics alone

## 13. Practical lesson

The project has made real progress, but the symptom stayed deceptive.

The main repeated symptom was:
- "nothing renders"

But the real causes changed over time:
- fresh-name weapon identity barrier
- donor-shell composition barrier
- bad first-person rig assumptions
- material/IPAK contract bugs
- x64 custom linker bug
- streamed image hash bug
- bad BO3 standalone probe choice
- client ownership failure
- current full runtime-zone startup fidelity failure

That is why the work can feel circular while still advancing.

## 14. FX porting is now in the polish phase

### What changed
The project eventually crossed the line from:
- “can the BO3 Servant FX render at all?”

to:
- “the BO3 Servant FX render, but they still need fidelity work”

That was the real transition point.

### What made that possible
The key fixes were:
- removing staged BO3 FX images from the loose global `storage\\t6\\images` lane
- namespacing translated BO3 surfaces as `bo3rfx_*`
- forcing a known-loadable Servant slot to carry a minimal namespaced BO3 phosphorous shell
- normalizing the translated image/material contract enough for T6 to draw it

### What that proved
The giant phosphorous control card was ugly, but it was a breakthrough:
- the namespaced BO3 surface path really renders
- the remaining problem is not “BO3 path is invisible”
- the remaining problem is semantics and polish

### Current live semantics state
The current full layered vortex lane now:
- renders in-game
- animates
- no longer causes the old unrelated stock zombie/fire/dirt square leakage

The remaining defects are:
- portal texture still looks too low-fidelity
- portal can look too faint up close or in bright scenes
- some layers are still approximate T6-safe interpretations rather than perfect BO3 parity

### Current best interpretation
At this point the main path forward is no longer:
- deeper file-open probe work

It is:
- better source-image shaping
- better alpha/blend behavior
- better per-layer sizing and placement
- only targeted probe work when a new actual instability appears
  - `numframes=2`
  - `frequency=15.0`
  - `notifyCount=1`
  - donor-style category counts like `[8,0,0,0,63,0,0,65,6,71]`
- custom emitted payloads:
  - much larger frame counts
  - different `frequency`
  - different `boneCount` category layout
  - different notify behavior
  - different section counts and channel layout

This showed that the header/section semantics mattered at least as much as the raw bone count.

### Donor-template experiment
The first follow-up fix was:
- `donor_template_static_pose`

That mode copied the donor header/section semantics almost exactly and filled those slots with source frame-0 data.

It was useful, but it also revealed an architectural limitation:
- the donor payload only carries a 71-bone contract
- the reduced Servant rig uses 89 bones

So donor-template can preserve donor semantics, but it cannot ever be the final full-rig solution.

### Current emitter pass
The next emitter mode is:
- `donor_semantic_static_pose`

Its purpose is:
- keep donor-like T6 weapon-animation semantics
- but rebuild the payload for the reduced 89-bone Servant rig itself

That means:
- target rig names, not donor names
- donor-style `assetType`, `numframes`, `frequency`, and notify handling
- donor-style category packing with a full `dataByte` permutation and explicit rotated/translated/none sets

This is the current best path forward for stabilizing a real custom BO3 idle animation before expanding to `fire`, `raise`, and the rest of the family.

### Deployment lesson
The animation-isolation work also exposed a deployment bug:
- purge-first deploys could delete the live survival FF before failing on a locked target

That is now fixed by:
- mod-lane-only anim isolation cases
- overwrite-first deploys instead of destructive purge-first behavior
- whether all required material and image dependencies are staged correctly

### What was actually blocking the path
The earlier raw-FX path failed because it was incomplete in multiple ways at once:
- the loader did not cover enough effect element types
- line/tail/decal-linked materials were not all staged
- dynamic-light-only parts were being treated too literally
- the project was testing runtime before the graph was fully closed

This is why the early raw-FX attempts looked like:
- freeze on fire
- black model state
- no visible usable vortex

### What is now proven
The project now has a real BO3 Servant raw-FX graph analysis and build path.

It can:
- resolve the Servant graph
- stage the dependent BO3 sprite materials/images
- parse the raw roots
- link them into a T6 survival FF

That means the project is beyond the "can OAT even do this?" stage.

### Current architectural conclusion
There is no extra hidden conversion stage after link.

The real conversion is:
- BO3 raw `.efx`
- parsed in OAT
- mapped into T6 `FxElemDef`
- written as native T6 `FxEffectDef`

So when the project says "port BO3 Servant FX into BO2," it now means:
- extend OAT until the raw BO3 graph can be expressed safely enough as T6 runtime FX

That is the right direction for the final Servant black-hole presentation.
4. pull zombies inward
5. kill them in the inner radius
6. clean up after the active window ends

### Important gameplay choices
- one active vortex per player
- timed active window based on the BO3 black-hole bomb timing target
- BO2-safe visible FX for lifetime readability

### Optimization pass
There was also a stability fix in the pull logic.

The earlier version created too much per-zombie churn by:
- spawning helper entities
- starting extra drag threads

That was replaced with a leaner pull implementation using:
- `setgoalpos()`
- limited inner-band `forceteleport()`

This reduced long-run script churn and made the demo build safer.

## 8. Admin/demo command layer

The following commands were added:
- `.p <amount>`
- `.round <target>`
- `.fast`
- `.hits <count>`
- `.debug`

### Why they exist
They were not added as final gameplay features. They were added so the project could:
- test the weapon faster
- record demos
- stress the singularity logic
- debug long rounds without wasting setup time

### Specific uses
- `.fast`
  - forces rapid spawn pacing
- `.hits`
  - raises player survivability for demo/testing
- `.debug`
  - hides script-usage and state noise by default and only enables it on demand

## 9. Ammo and UX tuning

The live weapon was tuned to present:
- `1/9` on the HUD

That required engine-side values of:
- `clipSize=1`
- `startAmmo=10`
- `maxAmmo=10`

because this donor shell effectively counts the full ammo pool including the chamber in a way that would otherwise display as `1/8`.

This is a good example of the difference between:
- raw engine fields
- player-facing HUD result

## 10. Current live state

The project now has all of these working at once:
- stable donor shell
- custom Servant model loading
- no old Ray Gun composition crash
- no fresh-name barrier blocking day-to-day progress
- visible singularity behavior
- usable demo/admin commands

That is a real milestone. The project is no longer trapped in registration and crash triage.

## 11. What is still left

### Animation parity
Current fire/reload choices are good enough to playtest, but they are still donor-animation approximations.

### Visual fidelity
The model is now clearly the Servant, but it is still not a perfect BO3-authored surface result.

### Presentation
The black-hole logic works, but the visuals are still stock T6-safe approximations rather than the final BO3 presentation path.

## 12. Short version of the biggest lessons

1. Fresh-name weapon identity was the wrong first hill to die on.
2. `ray_gun_zm` was a misleading donor because it carried hidden first-person baggage.
3. BO2-compatible first-person structure mattered more than raw BO3 asset purity.
4. FF/IPAK/material contracts mattered just as much as rigging.
5. The project moved once each failure was isolated and treated as a separate gate.
