# How-to: Debug Runtime Provenance

Most "random" failures in this repo turned out to be provenance problems:
- wrong mod lane
- stale base FF/IPAK state
- cached xmodels/materials
- a build report that did not match the runtime actually under test

## 1. Reset runtime lanes
From repo root:

Clean lane:
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode clean
```

Server-safe lane:
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode server
```

Dev lane:
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode dev -DevMod "bo3_rev"
```

Audit lane:
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode audit
```

## 2. Trust the build tag first
The live script logs a build tag on startup.

Before drawing conclusions, verify:
- the build tag in-game
- the build tag in `_build/bo3_rev_idg_probe/build_report.json`
- the rendered raw script at `mods/bo3_rev/scripts/mod_i_am_mod.gsc`

If those do not match, stop there. You are debugging the wrong build.

## 3. Know what a good live proof looks like
For the current MG08 donor path, good proof means:
- donor shell is `mg08_zm`
- the override fields resolve to the staged values
- the Servant model is visible
- the vortex renders
- the bridge host is `tag_origin`, not a visible MG08 world model
- no `dobj ... has more than 160 bones` crash

## 4. Common failure signatures

### `clip=<undef>` and `max=<undef>`
This was the fresh-name weapon barrier.

Meaning:
- zombies registration may have succeeded
- but the engine still did not resolve the weapon identity into a real weapon handle

Do not keep debugging materials or bones if you are still on this error.

### `dobj for xmodel 'c_zom_*_viewhands' has more than 160 bones`
This was the first-person composition/bone-budget failure.

Important history:
- it was not just the BO3 mesh
- `ray_gun_zm` still crashed even with tiny stock or no-model gun paths

This is why the project moved away from the Ray Gun donor.

### Invisible weapon but valid give path
Likely causes:
- placeholder material path
- missing or bad IPAK
- bad transform/origin fit

### Access violation after real BO3 materials were introduced
This was the IPAK contract failure.

The current builder now emits and verifies the runtime IPAK on purpose to prevent this exact class of crash.

### Startup crash with probe attached
If the game suddenly starts crashing on boot while the current content was previously stable, check the attached probe build first.

Important current rule:
- do not use the old intrusive deep consumer-tracing probe for normal visual testing
- the current safe default probe is:
  - `20260320_174022`

If `fx_runtime_probe.log` shows one of the old deep consumer builds, treat that crash as probe-induced until proven otherwise.

### "The shot did nothing"
There are two different versions of this symptom:

1. Old behavior:
- the fire watcher silently blocked a new shot while an older vortex was still active
- log signature:
  - `stage=blocked_active`

2. Current behavior:
- that silent block was removed
- the active vortex is now replaced by the new shot
- if the portal now looks weak, treat it as a render-consistency issue, not a missing `playfx` path until the logs prove otherwise

### `Couldn't find animtree 'mechz_claw'`
That was old contaminated survival-zone content from a prior lane. It is not a normal BO3 Rev error and usually means the runtime source/deploy lane was polluted.

### `Unresolved external: wait_network_frame`
That was a raw-script external mismatch in `mod_i_am_mod.gsc`. The fix was to remove the unsupported call and use safe waits.

## 5. Full restart vs map restart
Use a full game restart for:
- xmodel changes
- material/image changes
- base-lane FF/IPAK changes

Only use map restart for narrow raw-script-only tests when you are sure nothing else changed.

## 6. Avoid intrusive client injection in the normal loop
There is native source under `native/dobj_probe/`, and there is also the FX runtime probe under `native/fx_runtime_probe/`.

Current rule:
- safe probe builds are fine for targeted runtime confirmation
- intrusive deep consumer-tracing builds are not for day-to-day visual tuning

Treat the heavy probe as R&D, not the default loop.

## 7. Flare contract experiments are isolated work
If you are testing the stock phosphorous flare contract:
- do not make it the default live portal lane
- use isolated control-shell tests only
- assume crashes on that path are render-contract research until proven otherwise

Current reason:
- the stock flare techset path (`effect_775wj8ww`) previously produced a real render-side access violation around `0x0077C253` on the translated BO3 portal shell
- current mainline work should stay on the safe glow lane while visual polish continues

## 8. BO3 source of truth now exists locally
For Servant gameplay parity, stop guessing from memory. Use:
- `C:\Users\Ahmed\Downloads\t7-source\scripts\zm\_zm_weap_idgun.gsc`
- `C:\Users\Ahmed\Downloads\t7-source\scripts\shared\ai\zombie_vortex.gsc`
- `C:\Users\Ahmed\Downloads\t7-source\scripts\zm\_zm_weap_idgun.csc`
