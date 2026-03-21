# Master Deep-Dive Timeline

This document is the persistent record of what the project actually learned.

It is not a changelog. It is a running list of:
- what was tested
- what was really proven
- what was not proven
- what questions remain open

Use this when picking the project back up so the reasoning does not live only in chat history.

## 26. BO3 source parity moved from guesswork to real source-driven porting

### What we changed
- cloned the local T7 source reference repo
- started porting Servant timing/origin behavior from:
  - `scripts/zm/_zm_weap_idgun.gsc`
  - `scripts/shared/ai/zombie_vortex.gsc`
  - `scripts/zm/_zm_weap_idgun.csc`

### What we learned
- the project no longer needs to approximate core Servant timing only from memory
- BO3 parity work can now be grounded in the real weapon/vortex script lane

### What it proved
- the next gameplay fixes should be source-driven parity work, not broad behavior guesswork

### Lasting consequence
- current remaining gameplay work is a BO3 parity port problem, not a missing-reference problem

## 27. The current checkpoint is a working loader/bridge with polish debt

### What we changed
- kept the MG08 donor shell stable
- moved the live FX bridge host to `tag_origin`
- replaced silent active-vortex shot blocks with replace-active-vortex behavior
- stabilized the layered vortex enough to checkpoint

### What we learned
- the loader/bridge problem is sufficiently solved for a stable checkpoint
- the remaining issues are smaller and local:
  - portal consistency
  - visible lifetime feel
  - gameplay pull polish

### Lasting consequence
- treat build `0321232501_4c7e1d` as the current recoverable FX/GSC checkpoint
- future work should preserve this lane and iterate from it rather than reopening old loader uncertainty

## 23. The visible MG08 bridge model was not required

### What we tested
- kept the working MG08 donor shell
- swapped the client FX bridge host from `t6_wpn_zmb_mg08_world` to `tag_origin`

### What we learned
- the visible bridge model was not part of the real FX requirement
- it was only the host identity for the equipment-activated callback lane

### What it proved
- the client FX bridge can stay on the proven equipment callback lane without showing the MG08 world model as a debug host

### Lasting consequence
- live bridge host is now `tag_origin`
- future visual work should not assume the visible MG08 bridge model is part of the effect

## 24. Some "misfires" were not opacity bugs; they were real active-vortex blocks

### What we tested
- checked the live fire watcher path against recent "nothing happened" shots

### What we learned
- one real source of fake misfires was:
  - `stage=blocked_active`
- the script was silently refusing new shots while an older vortex was still active

### What it proved
- not every "nothing" shot was a render-semantics problem
- the bridge/gameplay lane itself was dropping some shots by design

### Lasting consequence
- the active vortex is now replaced by a new shot instead of silently blocking it
- remaining inconsistency should now be treated as a real portal render-consistency issue, not mixed with the old no-op path

## 25. The last visible defect is now a mild portal consistency issue inside the working lane

### What we tested
- multiple live runs after:
  - namespaced BO3 surfaces
  - packed-only image lane
  - safe glow material lane
  - stabilized shell/loop donor contract
  - active-vortex replacement

### What we learned
- the effect now reliably exists and usually looks correct
- the remaining defect is smaller:
  - the portal can still come out slightly faded depending on direction / background
- this is no longer the old:
  - square-card-only failure
  - invisible-or-crash failure
  - silent blocked-active shot

### What it proved
- the FX loader/bridge problem is effectively solved enough to checkpoint
- remaining work is polish inside the working render family

### Lasting consequence
- this is now the FX-loader checkpoint
- further work should focus on:
  - phosphorous pass weighting
  - blend consistency
  - BO3 gameplay parity from real source

## 17. The old loose-image crash lane was real, and removing it fixed startup

### What we tested
- deep native tracing of the accepted BO3 image path
- both malformed/sanitized opens and later success-branch handling
- comparison between working controls and failing BO3-side images

### What we learned
- the engine really was reading the BO3-side images
- the old crash was not “image never loaded”
- the first concrete runtime crash root was the loose global FX-image lane under:
  - `AppData\\Local\\Plutonium\\storage\\t6\\images`
- this first showed up on:
  - `$identitynormalmap`
- after removing that, it reappeared on:
  - `fxt_debris_clump`

### What it proved
- loose global BO3 FX-image overrides are unsafe in this port
- packed/mod-lane BO3 FX images are the correct lane

### Lasting consequence
- staged FX images are no longer deployed to the loose global image folder
- old loose crash results should not be treated as verdicts against the packed BO3 surface path

## 18. Namespacing translated BO3 surfaces fixed the stock-leak problem

### What we tested
- translated BO3 FX surfaces under stock-like names
- then the same translated surfaces under namespaced `bo3rfx_*` names

### What we learned
- stock-like translated names could leak malformed squares onto unrelated zombie/fire/dirt effects
- that visible contamination was not the real Servant path

### What it proved
- naming collisions were a real barrier
- visibility through the leaked path could be misleading

### Lasting consequence
- the live BO3 FX lane now uses namespaced `bo3rfx_*` materials and images end-to-end

## 19. The namespaced BO3 surface contract is now proven

### What we tested
- a minimal namespaced BO3 phosphorous shell
- forced through a known-loadable Servant slot

### What we learned
- the namespaced BO3 surface path does render on the real runtime lane
- the first visible result was a giant phosphorous card

### What it proved
- the remaining problem is not “BO3 surface contract is invisible”
- the remaining problem is semantics and fidelity

### Lasting consequence
- future work should treat the current lane as a render-polish lane, not a render-existence lane

## 20. Full layered vortex render is now working; current work is polish

### What changed
- control shell animation was added
- namespaced phosphorous materials were made double-sided
- the phosphorous image switched to a real mask-driven alpha-shaping path
- the current full layered vortex stack renders live again after those normalizations

### What we learned
- the Servant vortex now looks like a real layered effect instead of “nothing” or a hard crash
- the main remaining defects are:
  - low-fidelity phosphorous texture
  - close-range fade/consistency problems
  - approximate BO3 semantics on some layers

### Current recommendation
- stop using deep intrusive probes for normal visual iteration
- use the safe probe only when a new runtime failure appears
- treat the current work as build-side FX polish

## 21. The stock phosphorous flare contract is promising, but not safe as the live default

### What we tested
- switched the namespaced portal shell onto the stock phosphorous flare template/techset
- used that as the live portal contract instead of the safe glow lane

### What we learned
- the change was not ignored or overridden
- the game really loaded the new lane
- but that exact contract produced a real render-side access violation at `0x0077C253`

### What it proved
- the flare lane is worth future research because it is visually closer to the desired BO2 phosphorous behavior
- but it is not safe enough to use as the mainline portal contract today

### Lasting consequence
- the flare contract is now deferred isolated probe work only
- the live portal lane stays on the safer glow contract until the circular cutout and visibility issues are solved there first

## 22. Current mainline goal is restore the circular portal cutout on the safe glow lane

### What changed
- the safe portal lane was restored back onto the glow template/techset
- the phosphorous bake remains `512x512`
- RGB is zeroed anywhere alpha is zero so fully transparent pixels cannot leak border color

### What remains
- the portal still needs to read as a circular vortex rather than a square card
- the portal still needs stronger readability up close and in bright scenes

### Current recommendation
- keep working on the safe glow lane
- treat flare work as deferred R&D
- use probe work only if a new runtime instability appears

## 16. Correlated asset tracing proved the BO3 image files are really consumed

### What we tested
- rebuilt the native probe into a correlated per-asset tracer
- carried a `trace_id` from `CreateFile*` into later runtime tracepoints
- hooked `ReadFile` and `CloseHandle` for watched handles
- traced both:
  - working control image `fxt_light_glow_square`
  - failing BO3-side images `fxt_light_phosphorous`, `fxt_debris_clump`, `fxt_debris_clump_dirt`

### What we learned
- the failing BO3-side images are not just being opened; they are really being read:
  - `fxt_light_phosphorous`: `21936` bytes over `3` reads
  - `fxt_debris_clump`: `11024` bytes over `3` reads
  - `fxt_debris_clump_dirt`: `11024` bytes over `3` reads
- the working control is also read cleanly:
  - `fxt_light_glow_square`: `87444` bytes over `3` reads
- the failing BO3-side images also pass through the same deeper success chain:
  - `special_open_success_branch`
  - `special_open_success_postcall`
  - `special_open_success_continue`
  - `special_open_success_class1_continue`

### What it proved
- the current render failure is deeper than:
  - file-open path resolution
  - sanitized filename fallback
  - fake handle success
  - “file opened but never parsed”

### The strongest new divergence
- the working control image begins with a different format/class than the failing BO3-side images:
  - `fxt_light_glow_square` header starts with `... 01 00 ...`
  - `fxt_light_phosphorous` header starts with `... 0D 00 ...`
  - `fxt_debris_clump` header starts with `... 0D 00 ...`
- the accepted BO3-side images still reach the `special_open_success_class1_continue` path

### Lasting consequence
- the project is no longer mainly blocked on asset lookup
- the next root-cause target is the call made from `special_open_success_class1_continue`
- this is the most likely place where accepted `0x0D` images either:
  - become a usable runtime image object, or
  - silently diverge into a later invisible/rejected lane

## 1. Fresh-name weapon identity was the first hard barrier

### What we tested
- tried to create a real `apothicon_servant_zm`-style weapon identity in the normal BO2/Plutonium mod lane
- reduced the test to the smallest grant/registration path possible

### What we learned
- registration/inclusion can succeed while the engine still refuses to resolve the fresh weapon name
- this is not the same as a bad model/material problem

### What it proved
- fresh-name Servant weapon identity is blocked in this workflow

### Lasting consequence
- donor-shell architecture is not optional in the current project

## 2. Donor-shell choice is an architectural decision

### What we tested
- `ray_gun_zm`
- `m1911_zm`
- `m14_zm`
- `mg08_zm`

### What we learned
- `ray_gun_zm` carries hidden first-person baggage that keeps triggering composition failures
- donor choice changes more than weapon feel; it changes runtime composition behavior

### What it proved
- `mg08_zm` is the current practical shell
- donor selection must be treated as part of engine compatibility, not cosmetic preference

## 3. The first-person rig problem was real, not just "too many BO3 assets"

### What we tested
- full BO3-style first-person paths
- combined gun + hands paths
- reduced weapon-only rig

### What we learned
- T6 has a hard first-person DObj bone budget
- literal BO3 first-person rig parity is not the right first target

### What it proved
- reduced BO3-derived weapon-only rig is the right initial presentation lane

## 4. Material/IPAK contract problems were real and independent

### What we tested
- BO3-derived image/material translation
- runtime IPAK deployment
- image-backed surface loading

### What we learned
- compiled assets can exist while runtime image resolution still fails
- the runtime IPAK contract matters, not just staged images on disk

### Concrete fixes that mattered
- runtime IPAK emission/deploy
- T6 image hash bug fix
- x86 custom OAT rebuild

### What it proved
- some earlier "invisible BO3 FX" results were packaging failures, not pure FX semantic failures

## 5. Server probe and client probe are different questions

### What we tested
- server GSC `ffprobe`
- client CSC `ffprobe`

### What we learned
- server `loadfx/playfx` success does not prove client rendering
- a server probe can succeed while the client probe never even executes

### What it proved
- render debugging must be client-owned, not inferred from server logs

## 6. Several BO3 probe choices were invalid

### What we tested
- `hole_md`
- `vortex_explo`
- `projectile`
- custom raw stock-style orb probes

### What we learned
- `hole_md` is support-only and effectively a bad standalone visibility probe
- some BO3 effects are too brief or too layered to use as first visual discriminators

### What it proved
- standalone probe choice matters
- "nothing visible" can be a bad probe, not a dead port

## 7. Offline validation is useful, but not sufficient

### What we built
- native T6 `FxEffectDef` dumper
- BO3/T6 FX comparators
- visual viability checker
- contract probe builder

### What we learned
- offline analysis can prove a lot:
  - asset structure acceptance
  - image hash correctness
  - standalone viability heuristics
- but offline validity does not guarantee live startup/runtime fidelity

### What it proved
- offline gates are necessary
- they do not replace runtime ownership and runtime startup checks

## 8. Minimal custom FF lane is safer than the full rebuilt runtime lane

### What we tested
- tiny `mod_load.ff`
- tiny `mod_load.ipak`
- isolated custom probe assets

### What we learned
- minimal custom FF/IPAK can load safely
- so custom asset packaging is not inherently impossible

### What it proved
- the current big crash is not "any custom FF crashes T6"
- the bigger issue is full runtime-zone rebuild fidelity

## 9. Clientscript ownership was a separate blocker

### What we tested
- `mod_patch.ff`
- loose clientscript overrides
- tiny same-name `so_zsurvival_zm_transit.ff`
- full rebuilt `so_zsurvival_zm_transit.ff`

### What we learned
- `mod_patch.ff` loading is not enough to own `clientscripts/mp/zm_transit.csc`
- tiny same-name runtime FF can take ownership, but it breaks the zone
- the only ownership path that really works is the full runtime `so_zsurvival_zm_transit.ff`

### What it proved
- ownership and runtime fidelity are separate issues

## 10. Client ownership is now solved

### What we tested
- full builder path with a minimal client helper rendered into `_bo3_rev_servant_fx_v3.csc`

### What we learned
- the client helper now executes on the full runtime lane

### Proof
- `[ffprobe][csc] helper init reached ...`
- `[ffprobe][csc] init asset=...`

### What it proved
- we are no longer blocked on client ownership

## 11. The current blocker is startup fidelity of rebuilt `so_zsurvival_zm_transit.ff`

### What we observe now
- client helper initializes
- no spawn-time probe playback yet
- crash occurs during normal Transit startup before spawn
- `Could not load material "zombie_transporter_overlay"` remains the most suspicious warning at the crash boundary

### What that means
- the current failure is not a BO3 FX render verdict yet
- it is a rebuilt runtime-zone fidelity problem

## 12. Specific fixes that materially changed understanding

### A. Custom OAT architecture
- rebuilding custom linker/unlinker as `x86` was mandatory

### B. T6 streamed image hash bug
- fixing the T6 name-hash path was mandatory for IPAK-backed custom images

### C. Probe discipline
- bad probes caused false conclusions

### D. Ownership isolation
- separating server probe, client probe, and runtime ownership was mandatory

## 13. Current open questions

### Runtime fidelity
- Why does the rebuilt full runtime zone still drop stock Transit startup dependencies?
- Is `zombie_transporter_overlay` the actual tripwire or just the first visible symptom?
- Are there more hidden stock assets/rawfiles/materials that the rebuilt runtime FF must explicitly preserve?

### Probe substrate
- Can the rebuilt runtime zone be made stable enough to reach spawn?
- If not, is there a stock-faithful script-patching path that preserves the stock runtime FF while still owning `zm_transit.csc`?

### BO3 render path
- Once spawn is reached, does a stock client probe render?
- Once stock client probe renders, does a custom raw stock-style probe render?
- Once that renders, does a BO3-derived probe render?

## 14. Rules for future deep dives

1. State exactly what the current test proves.
2. State exactly what the current test does not prove.
3. Do not treat server probe results as client render results.
4. Do not use support-only BO3 effects as first visibility probes.
5. Do not change ownership path and effect semantics in the same test if it can be avoided.

## 15. The "orb-only" lane was still contaminated by the global BO3 surface bundle

### What we tested
- full runtime ownership path with a custom raw stock-style orb:
  - `zombie/fx_ffprobe_debug_orb_stock`
- native DLL probe attached to the live process
- latest probe build stamped and verified in both injector output and probe log

### What we learned
- the crash was not a generic "custom orb FX body is invalid" verdict
- the native probe showed the crashing registration record contained:
  - `gfx_dust_gen`
  - `pimp_technique_zfeather_c4c6df88`
  - null pointer at `edx+0x64`
- so the live crash path was inside BO3 material/technique registration, not directly on `bo3_rev_debug_stock_glow`

### What caused it
- the builder was still populating `mod_load` from the global BO3 Servant surface graph in probe mode
- specifically:
  - `raw_fx_stage=off` meant no staged Servant rows
  - `load_bo3_servant_fx_material_names()` then fell back to `FX_GRAPH_REPORT`
  - that reintroduced the entire BO3 FX surface bundle into the supposedly minimal probe lane

### What fixed it
- stage raw FX before surface staging so probe FX sources exist when closure is computed
- resolve surface closure from active staged/probe FX, not only from the staged Servant set
- stop falling back to the global graph when a specific probe FX is active
- keep stock/passthrough materials separate from translated BO3 materials

### What it proved
- the previous orb crash was still a polluted test
- the new build is the first truly minimal custom-orb runtime repro

### Current clean repro state
- `mod_load.zone` now contains only:
  - `fx,zombie/fx_ffprobe_debug_orb_stock`
  - `material,bo3_rev_debug_stock_glow`
  - `image,$identitynormalmap`
  - `image,fxt_env_dust_mote_atlas`

## 16. The project has now been moved back onto the full Servant shot/vortex lane

### What we changed
- stopped building around `CLIENT_FFPROBE_ASSET`
- restored the real `_bo3_rev_servant_fx_v3.csc` client bridge
- rebuilt the full BO3 Servant raw FX suite into `mod_load`
- added a full-Servant native-probe watchlist so runtime instrumentation still works without a single-probe asset

### What this proved
- the codebase already had the real Servant shot/vortex path preserved
- the main missing piece was a clean preset/build mode that stopped rendering the ffprobe helper and kept the probe useful

### Current full-suite build
- `0320093938_f36984`

### Full-suite watchlist now includes
- `zombie/fx_idgun_muz_1p_zmb`
- `zombie/fx_idgun_projectile_zod_zmb`
- `zombie/fx_idgun_ground_displace_zod_zmb`
- `zombie/fx_idgun_vortex_explo_zod_zmb`
- `zombie/fx_idgun_vortex_zod_zmb`
- `zombie/fx_idgun_hole_lg_zod_zmb`
- `zombie/fx_idgun_hole_md_zod_zmb`
- `zombie/fx_idgun_hole_sm_zod_zmb`
- `zombie/fx_idgun_hole_xsm_zod_zmb`
- `zombie/fx_idgun_hole_xl_zod_zmb`

### Practical meaning
- the repo is no longer staged only for narrow phosphorous-orb experiments
- the next runtime test should answer what the actual Servant shot, projectile bridge, and vortex suite look like on the now-proven runtime/client path
  - `image,fxt_light_glow_square`

### Lasting consequence
- every probe lane must validate its final `mod_load.zone` and expected manifest before a runtime result is interpreted

## 16. Custom raw stock-control orb is now proven live

### What we tested
- full runtime ownership path
- truly minimal `mod_load` containing only:
  - `fx,zombie/fx_ffprobe_debug_orb_stock`
  - `material,bo3_rev_debug_stock_glow`
  - `image,$identitynormalmap`
  - `image,fxt_env_dust_mote_atlas`
  - `image,fxt_light_glow_square`

### What we learned
- the custom raw stock-control orb no longer crashes
- the client helper loads it successfully:
  - `init asset=zombie/fx_ffprobe_debug_orb_stock;bo3=1`
- the client reaches a real spawn-time play call:
  - `spawn play asset=zombie/fx_ffprobe_debug_orb_stock;bo3=1`
- the orb is visibly rendered on screen
- the latest native probe block for this run has no new access violation

### What it proved
- full runtime startup is stable enough for client render probes
- full runtime client ownership is stable enough for client render probes
- the custom raw FX path itself is not inherently rejected by T6
- the previous crash was not the orb shell; it was the polluted BO3 surface bundle

### Lasting consequence
- the next ladder is now clean:
  1. stock probe
  2. custom raw stock-control orb
  3. stock-safe orb shell with BO3 surface
  4. BO3-derived effect probe
6. Prefer one-variable tests over integrated Servant tests until startup is stable.
7. If runtime crashes before spawn, treat it as zone/startup fidelity first, not FX failure.

## 15. Best current summary

We are not at "BO3 FX are impossible in T6".

We are at:
- minimal custom asset packaging is possible
- client ownership is possible
- rebuilt full runtime zone is still not startup-faithful enough
- therefore we still need one more stability layer before BO3 client render tests become authoritative

## 16. New startup-fidelity root cause: donor search roots can poison stock asset reuse

### What we tested
- restored the stock `soundbank, zmb_survival_transit.all` line in the rebuilt runtime zone source
- added a hard guard so the rebuilt zone cannot silently drop stock entries
- isolated the soundbank behavior with minimal linker probes

### What we learned
- the runtime builder had been adding the donor tree at [`_build/runtime_unlink_so_zsurvival_clean`](/z:/Games/pluto_t6_full_game/_build/runtime_unlink_so_zsurvival_clean) as a live linker search root
- that donor tree contains a partial dumped soundbank source for `zmb_survival_transit.all`:
  - `soundbank/zmb_survival_transit.all.aliases.csv`
  - `soundbank/zmb_survival_transit.all.reverbs.csv`
- in the full build context, that partial source footprint caused OAT to choose the raw T6 soundbank loader and try to regenerate the stock Transit soundbank from raw sound files
- that regeneration then failed on missing source audio such as `sound/zmb/level/zm_transit/alarms/alarm2.LL55.pc.snd`

### What it proved
- the crashy rebuilt runtime lane was being built from a polluted asset/source search graph
- the problem was not just "soundbank support is broken"
- minimal probes proved:
  - rebuilding a tiny zone that only references `zmb_survival_transit.all` works
  - rebuilding a same-name `so_zsurvival_zm_transit` probe with only that soundbank also works
  - the failure appears only when the full build context includes the donor search root with partial dumped stock soundbank sources

### Lasting consequence
- donor trees can be used as reference/template inputs during staging
- donor trees must not automatically be fed back into the final runtime relink as live search roots
- preserving stock runtime fidelity requires both:
  - preserving stock zone source entries
  - preventing partial dumped donor content from hijacking loaded-stock asset reuse
## 2026-03-19: Custom Raw Stock Orb Root Cause

### Symptom

- The stock probe rendered on the full runtime path.
- Swapping only the probe asset to `zombie/fx_ffprobe_debug_orb_stock` caused a startup crash before client helper logs.
- This looked at first like a generic live-runtime rejection of custom raw FX.

### What We Checked

1. Dumped the live `mod_load.ff` output and compared:
   - stock reference:
     - `maps/zombie/fx_zmb_tranzit_marker_glow`
   - custom control:
     - `zombie/fx_ffprobe_debug_orb_stock`
2. Verified that the custom orb was being packaged.
3. Compared the compiled native `FxEffectDef` fields instead of trusting the raw `.efx` source text.

### What We Learned

- The live custom orb was not actually stock-like.
- Two separate converter-side bugs caused that:

1. Wrong template patched
- `write_debug_raw_fx()` uses two templates.
- The live probe asset `fx_ffprobe_debug_orb_stock` comes from `stock_minimal_template`, but earlier contract fixes were applied to `debug_template`.

2. Invalid scale normalization
- `normalize_placeholder_scale_graphs()` rewrote:
  - `scaleGraph 0`
  - into
  - `scaleGraph 1`
- This was based on a false assumption that zero-valued scale graphs were placeholders.
- Stock T6 effects such as `fx_zmb_tranzit_marker_glow` legitimately compile with `scale = 0`.
- So the normalizer was globally mutating valid stock-like FX into non-stock runtime semantics.

### Concrete Before/After

Before the fix, the live orb compiled with:
- `atlas.behavior = 4`
- `lifeSpanMsec.base = 1000`
- `emitDist.base = 0`
- `reflectionFactor.base = 0`
- `visSamples.base.scale = 1`
- `spawnRange = 0`
- `spawnFrustumCullRadius = 256`

After the fix, the live orb compiles with:
- `atlas.behavior = 0`
- `lifeSpanMsec.base = 1`
- `emitDist.base = 1`
- `reflectionFactor.base = 1`
- `visSamples.base.scale = 0`
- `spawnRange = 0,600`
- `spawnFrustumCullRadius = 30`

### Why This Matters

- This is a general converter bug, not just a Servant-specific issue.
- It means some earlier “custom raw FX are unsafe” conclusions were based on a control asset that our own normalization pass had silently corrupted.
- The right workflow remains:
  1. inspect compiled native T6 dumps
  2. compare against stock references
  3. do not trust staged raw `.efx` text alone

## 2026-03-19: Orb-only crash narrowed to material identity vs top-level effect header

### Symptom

- After fixing the corrupted control orb, the orb-only full-runtime build still crashed before any client helper log.
- The crash remained the same newer native class:
  - exception address `0x007777F9`
  - last GSC pos `_visionset_mgr::monitor`
  - empty last GSC error
- So this was not the old missing-effect/precache failure anymore.

### What we compared

1. Safe control build
- `0320043328_f36984`
- stock probe asset: `maps/zombie/fx_zmb_tranzit_marker_glow`
- `surface_pipeline.staged_fx = []`

2. Crashing orb-only build
- `0320031307_f36984`
- custom probe asset: `zombie/fx_ffprobe_debug_orb_stock`
- `surface_pipeline.staged_fx = ['zombie/fx_ffprobe_debug_orb_stock']`

### What it proved

- The safe control build still carried the broader background BO3 surface staging.
- The orb-only crashing build differed in the live `mod_load` asset set essentially by:
  - `fx, zombie/fx_ffprobe_debug_orb_stock`
  - `material, gfx_fxt_light_glow_square_gr`
- The safe control build already included a uniquely named clone of that material:
  - `bo3_rev_debug_stock_glow`

### Material identity finding

- [`bo3_rev_debug_stock_glow.json`](/z:/Games/pluto_t6_full_game/_build/bo3_rev_idg_probe/materials/bo3_rev_debug_stock_glow.json) is identical to [`gfx_fxt_light_glow_square_gr.json`](/z:/Games/pluto_t6_full_game/_build/ff_contract_probe/materials/gfx_fxt_light_glow_square_gr.json) except for `debugName`.
- So the remaining non-orb delta was not shader state. It was stock-material identity/ownership in `mod_load`.

### Current change

- The raw custom orb template in [`_build/build_bo3_rev_idg_probe.py`](/z:/Games/pluto_t6_full_game/_build/build_bo3_rev_idg_probe.py) now uses:
  - `bo3_rev_debug_stock_glow`
  - instead of
  - `gfx_fxt_light_glow_square_gr`

### Current build after that change

- `0320043816_f36984`
- `surface_pipeline.staged_fx = ['zombie/fx_ffprobe_debug_orb_stock']`
- `mod_load` now contains:
  - `fx, zombie/fx_ffprobe_debug_orb_stock`
  - `material, bo3_rev_debug_stock_glow`
- `mod_load` no longer contains:
  - `material, gfx_fxt_light_glow_square_gr`

### Remaining strongest open suspect

- The T6 raw FX loader still zeroes and never explicitly populates top-level `FxEffectDef.flags` or `efPriority` in [`LoaderFxT6.cpp`](/z:/Games/pluto_t6_full_game/_build/_tmp/OpenAssetTools/src/ObjLoading/Game/T6/Fx/LoaderFxT6.cpp).
- The current dumped custom orb still shows:
  - `flagsHex = 0x0000`
  - `priority = 0`
- So if `0320043816_f36984` still crashes, the next deep-dive target is no longer material identity.
- It becomes the top-level native effect header contract.
