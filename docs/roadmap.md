# Roadmap

This is the current "what next" list for BO3 Rev.

## Stage 1: keep the MG08 baseline stable
Do not regress:
- donor shell acceptance
- material/IPAK stability
- black-hole pull/kill logic
- admin/demo commands
- current live vortex rendering

## Stage 2: improve Servant vortex readability and consistency
Current work items:
1. reduce the remaining direction/background-dependent fade on the portal core
2. improve phosphorous alpha/blend behavior without reopening the old flare crash lane
3. keep the portal readable in brighter scenes
4. finish per-layer semantics tuning without reopening the old crash lane
5. keep the current replace-active-vortex fire behavior stable
6. finish visible lifetime polish so the hole hangs with the gameplay window

Goal:
- the portal should always read as "present" and intentional, not swing between normal and slightly faded based on direction or lighting

Deferred investigation:
- revisit `flare_stock_trial` only as isolated probe work if the safe glow lane cannot achieve the needed readability

## Stage 3: improve phosphorous fidelity
Current work items:
1. better phosphorous source bake
2. softer/higher-quality portal edges
3. less crunchy/pixelated portal detail

Goal:
- closer to BO3 look without reopening the old material/image instability

## Stage 4: improve first-person animation feel
Current work items:
1. better fire animation selection
2. better raise/pullout family
3. better reload feel and timing

Goal:
- closer to BO3 handling without destabilizing the shell path

## Stage 4.5: BO3 gameplay parity port
Current work items:
1. port impact/vortex setup from `scripts/zm/_zm_weap_idgun.gsc`
2. port pooled vortex behavior from `scripts/shared/ai/zombie_vortex.gsc`
3. compare BO3 duration/radius/explosion behavior against the current T6 rewrite
4. replace more of the current T6 pull approximation with BO3-like vortex-state behavior where T6 safely allows it

Goal:
- stop approximating Servant gameplay from memory when the real BO3 source is now available locally

## Stage 5: improve remaining material fidelity
Current work items:
1. body/flesh color grading
2. emissive/glow surface fidelity
3. final eye/orb surface contract

Goal:
- closer to BO3 color and emissive look without reopening the old crash lanes

## Stage 6: deeper parity research
After the above is stable:
1. revisit BO3 animation retargeting for real parity
2. revisit BO3 black-hole presentation assets
3. only then reconsider whether the fresh-name/native path is worth reopening
