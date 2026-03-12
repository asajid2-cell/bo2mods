# History and Findings

This is the detailed BO3 Rev Apothicon Servant experiment log. It is the main answer to:
- what we tried
- what failed
- what each failure actually proved
- what was changed to get from repeated crashes to the current working MG08 donor build

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
