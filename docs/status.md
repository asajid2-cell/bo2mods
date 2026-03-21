# Status

Last updated: 2026-03-21

## Goal
Port BO3/T7 assets into BO2/T6 in a way that the retail T6 runtime actually accepts, renders, and behaves convincingly.

The Apothicon Servant is the current use case, not the whole goal. The real project is:
- understand the T6 engine contract
- make the toolchain emit that contract correctly
- prove one BO3-derived asset class at a time

## Current state
The project is no longer blocked on client ownership, gross packaging, or the basic BO3 surface path. The real Servant vortex lane now renders in-game on the live runtime path.

Current live runtime build:
- `0321232501_4c7e1d`

Current recommended probe build for normal runtime testing:
- `20260320_174022`

What the current state proves:
- `mg08_zm` donor shell is stable
- the BO3-derived reduced Servant weapon rig is stable
- the black-hole gameplay loop works in BO2
- the full layered vortex stack visibly renders in-game
- namespaced `bo3rfx_*` BO3 FX surfaces load and render on the real runtime lane
- the old loose global `storage\\t6\\images` crash lane is fixed
- the client FX bridge now uses `tag_origin` instead of the visible `t6_wpn_zmb_mg08_world` host
- repeated shots now replace an active vortex instead of silently doing nothing
- BO3 Servant gameplay timing/origin work is now being ported from the real local T7 scripts

## Current checkpoint
This is now a stable FX-loader and bridge checkpoint.

The current boundary is:
- the bridge is working
- the full layered vortex stack is working
- old square-card / invisible-or-crash failure classes are no longer the main issue
- remaining work is mostly visual consistency, visible lifetime polish, and BO3 gameplay parity

## What is proven

### Toolchain and packaging
- The custom OAT runtime tools had a real architecture bug.
  - The custom linker/unlinker had been built as `x64`.
  - Rebuilding them as `x86` fixed a real T6 DB-layout problem.
- The T6 streamed-image lookup path had a real hash bug.
  - T6 images were being emitted with `hash = 0`.
  - Fixing that made IPAK-backed BO3 images resolvable.
- A minimal custom `mod_load.ff` can load safely at runtime.
- A minimal custom `mod_load.ipak` can be built and deployed safely.
- The full Servant runtime lane can now be built and deployed cleanly to:
  - base `zone/all`
  - `mods/bo3_rev`
  - `AppData\\Local\\Plutonium\\storage\\t6\\mods\\bo3_rev`

### Probe and runtime findings
- Server-side `ffprobe` works, but was never enough by itself.
- Client-side ownership is proven on the full runtime lane.
- A custom raw stock-control probe renders visibly on the same lane.
- The native probe traced the old invisible/crashing BO3 image path deep enough to prove:
  - BO3 images were really opened
  - BO3 images were really read
  - accepted `0x0D` image lanes could still crash later
- The major loose-image crash cause was real:
  - staged BO3 FX images deployed into loose `storage\\t6\\images`
  - especially `$identitynormalmap` and later `fxt_debris_clump`
  - caused null-pointer faults in the `0x0D`/class1 path
- Removing staged FX images from the loose global image lane fixed that crash class.
- The old deep intrusive consumer probes are not part of the normal visual loop anymore.

### Current BO3 FX understanding
- `hole_md` was a bad standalone BO3 probe.
- Minimal custom raw FX are not universally impossible.
- BO3 raw FX are parseable, linkable, and renderable in T6 when their material/image contract is normalized correctly.
- The namespaced BO3 surface contract works:
  - `bo3rfx_*` images/materials render when forced through a known-loadable slot
- The live FX bridge host is now neutral:
  - `tag_origin`
  - not the old visible `t6_wpn_zmb_mg08_world` bridge model
- The previous visible stock-square contamination was a real naming leak:
  - translated BO3 surfaces under stock-like names could affect unrelated stock zombie/fire/dirt effects
  - namespacing those surfaces fixed that leak

### BO3 source parity
- The real BO3 Servant / vortex scripts are now available locally:
  - `C:\\Users\\Ahmed\\Downloads\\t7-source\\scripts\\zm\\_zm_weap_idgun.gsc`
  - `C:\\Users\\Ahmed\\Downloads\\t7-source\\scripts\\shared\\ai\\zombie_vortex.gsc`
  - `C:\\Users\\Ahmed\\Downloads\\t7-source\\scripts\\zm\\_zm_weap_idgun.csc`
  - `C:\\Users\\Ahmed\\Downloads\\t7-source\\scripts\\shared\\ai\\zombie_vortex.csc`
- The BO3 weapon script handles projectile impact and hands off to `zombie_vortex::start_timed_vortex(...)`.
- The current T6 Servant gameplay rewrite has started porting timing/origin behavior from those source files.

## Current blocker
The project is now in polish, not first-proof debugging.

The remaining issues are:
- portal consistency
  - the portal can still come out slightly faded depending on direction / background
  - it is no longer the old "nothing rendered" class, but it is still not perfectly consistent
- visible lifetime feel
  - the visible hole is closer now, but still needs final timing polish to hang with the gameplay window convincingly
- phosphorous fidelity
  - the portal texture still looks more pixelated than desired because the source art is tiny
- final layer semantics
  - the effect is now readable and layered, but not yet BO3-authentic in motion/detail
- gameplay pull polish
  - the current T6 forced-pull rewrite works, but still needs BO3-like state polish

## Deferred isolated probe work
- `flare_stock_trial` exists as a separate portal render mode for later R&D.
- The stock phosphorous flare contract (`effect_775wj8ww`) is not the current live lane.
- When used as the live default on the translated BO3 portal shell, it produced a real render-side access violation at `0x0077C253`.
- Revisit that path only in narrow `control_only` tests with targeted probing, not in the normal visual loop.

## Current interpretation
- More deep file-open probe work is not the main path forward anymore.
- The current problems are mostly build-side:
  - image shaping
  - alpha/blend tuning
  - layer sizing and placement
  - visible timing
  - per-family semantics polish
  - gameplay parity polish

## Current recommended next step
Treat the current Servant lane as a render-polish and gameplay-parity project, not a render-existence project.

Focus on:
1. keep the current stable FX bridge/runtime lane intact
2. finish the last portal consistency issue on the safe glow lane
3. finish visible timing polish on the layered hole
4. improve phosphorous source/bake quality
5. continue porting gameplay parity from the real BO3 source files
6. only use the safe probe when a new real instability appears

## Authoritative artifacts
- Main build report:
  - [`_build/bo3_rev_idg_probe/build_report.json`](/z:/Games/pluto_t6_full_game/_build/bo3_rev_idg_probe/build_report.json)
- Full deep-dive timeline:
  - [`docs/explanation/master-deep-dive-timeline.md`](/z:/Games/pluto_t6_full_game/docs/explanation/master-deep-dive-timeline.md)
- Current detailed findings:
  - [`docs/explanation/history-and-findings.md`](/z:/Games/pluto_t6_full_game/docs/explanation/history-and-findings.md)
