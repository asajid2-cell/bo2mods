# BO3 Servant FX Porting

Last updated: 2026-03-21

## Current checkpoint
The BO3 Servant FX lane is now in a checkpoint state, not a first-proof state.

Current live checkpoint build:
- `0321232501_4c7e1d`

What is now true:
- the full layered vortex renders on the real runtime lane
- the live FX bridge host is `tag_origin`
- namespaced `bo3rfx_*` surfaces are the real working path
- repeated shots replace an older active vortex instead of silently doing nothing
- current remaining work is fidelity/parity polish, not loader uncertainty

## Summary
The BO3 Servant black-hole presentation is now a tooling problem, not a mystery engine problem.

The important architectural point is:
- BO2/T6 does not consume BO3 `.efx` directly at runtime.
- The conversion step happens inside the local OAT raw FX loader.
- That loader parses BO3 raw `.efx` text and emits native T6 `FxEffectDef` assets into the linked FF.

So there is no second hidden "engine conversion" after link. If the effect is valid in-game, it is because OAT already translated the raw effect definition into a T6-native structure the BO2 engine can read.

## The actual pipeline

### Source side
Current BO3 Servant FX source comes from:
- `hb21_black_ops_3_fx_library_v2.1.0/share/raw/fx`

Relevant roots:
- `zombie/fx_idgun_muz_1p_zmb`
- `zombie/fx_idgun_projectile_zod_zmb`
- `zombie/fx_idgun_vortex_explo_zod_zmb`
- `zombie/fx_idgun_vortex_zod_zmb`

### Analysis side
The graph is analyzed by:
- `_build/analyze_bo3_idgun_fx.py`

It currently proves:
- the Servant graph resolves cleanly
- the graph does not need model emitters
- the current subset does not require `trailDef`
- the remaining warnings are mostly `dynamicLight2`

### Conversion side
The raw parser and T6 packer live in:
- `_build/_tmp/OpenAssetTools/src/ObjLoading/Game/T6/Fx/LoaderFxT6.cpp`
- `_build/_tmp/OpenAssetTools/src/ObjLoading/Game/T6/Fx/LoaderFxT6.h`

That code:
1. parses the BO3 raw `.efx`
2. maps supported visual blocks onto T6 `FxElemDef`
3. resolves material/effect dependencies
4. emits a native T6 `FxEffectDef`

The T6 runtime structures it targets are defined in:
- `_build/_tmp/OpenAssetTools/src/Common/Game/T6/T6_Assets.h`

### Link side
The T6 raw FX loader is enabled in:
- `_build/_tmp/OpenAssetTools/src/ObjLoading/Game/T6/ObjLoaderT6.cpp`

The linked output is then written into:
- `so_zsurvival_zm_transit.ff`
- `so_zsurvival_zm_transit.ipak`

At runtime, BO2 only sees the linked T6 assets. It does not know or care that the source originally came from BO3 raw `.efx`.

## What changed after the loader checkpoint

The project moved from "can BO3 raw FX render at all?" to:
- portal consistency polish on the safe glow lane
- visible timing/layer polish on the hole
- BO3 gameplay parity using the real local T7 source:
  - `C:\Users\Ahmed\Downloads\t7-source\scripts\zm\_zm_weap_idgun.gsc`
  - `C:\Users\Ahmed\Downloads\t7-source\scripts\shared\ai\zombie_vortex.gsc`
  - `C:\Users\Ahmed\Downloads\t7-source\scripts\zm\_zm_weap_idgun.csc`

That means the loader work is now mature enough to treat as a reusable custom-effects compatibility lane around OAT, not just a one-off debugging experiment.

## Current supported BO3->T6 effect coverage

The local T6 FX loader currently supports enough of the Servant graph to build it:
- `billboardSprite`
- `orientedSprite`
- `rotatedSprite`
- `line`
- `tail`
- `cloud`
- `decal`

It also synthesizes dynamic-light-only elements into a safe T6 light path where possible, and otherwise ignores unsupported light behavior instead of crashing the build.

The current Servant graph no longer reports fatal blockers in the analyzer.

## What is still incomplete

The local loader is still not a full BO3 FX implementation.

Important gaps that still matter for future BO3 effects:
- `trail`
  - requires proper `FxTrailDef` serialization
- `model`
- `runner`
- full BO3 light semantics
  - current `dynamicLight2` handling is intentionally reduced

These gaps do not stop the current Servant graph from compiling, but they can matter for future BO3 weapon/effect graphs.

## What the earlier crashes were

The earlier raw-FX crashes were not random.

The main causes were:
- missing material staging for BO3 `line` and `tail` blocks
- missing BO3 decal dependencies
- letting partially supported graphs reach runtime before the loader was complete enough

Those issues were fixed by:
- expanding material harvesting beyond billboard sprites
- staging decal-linked materials and backing images
- adding graph analysis and compatibility checks before build/deploy
- extending the T6 raw FX loader to cover the Servant subset

## What "proper BO3 black hole" still requires

The end goal is not just "compile the effect." It is:
- stable runtime playback
- recognizable BO3 Servant projectile
- recognizable BO3 Servant vortex burst
- recognizable BO3 Servant persistent black-hole loop
- acceptable material fidelity on the supporting sprite sheets

That means the project is now split into three separate tracks:

### 1. FX graph correctness
Make sure the BO3 graph is translated into valid T6 `FxEffectDef` assets with all required dependencies.

### 2. Runtime stability
Stage the BO3 roots in steps:
- muzzle
- projectile
- impact
- full vortex root

This is why the staged rollout exists in the builder.

### 3. Fidelity
Even if the raw effect links and plays, it may still look wrong if:
- sprite materials are staged incorrectly
- image formats resolve incorrectly
- BO2 material templates respond differently than BO3

That is a separate fidelity problem, not a loader problem.

## What this means for animations

The Servant black-hole presentation is not primarily an xanim problem.

The black-hole look is dominated by:
- projectile FX
- impact burst FX
- persistent vortex loop FX
- end/implode FX

Weapon first-person animation is still a separate lane:
- donor BO2 anims currently live
- BO3 first-person anim parity is still separate work

So the correct sequence is:
1. get the BO3 black-hole FX graph stable
2. keep donor anims while doing that
3. revisit BO3 first-person animation parity after the FX path is trustworthy

## Current conclusion

The BO3 Servant FX path is not blocked by a missing abstract conversion stage.

The conversion stage already exists:
- raw BO3 `.efx`
- parsed by OAT
- packed into T6 `FxEffectDef`
- linked into BO2 FF/IPAK

The real remaining work is:
- complete element support where needed
- validate runtime behavior root by root
- fix material/image fidelity around the raw FX package

That is the correct path to a stable BO3 Servant black-hole presentation in BO2.
