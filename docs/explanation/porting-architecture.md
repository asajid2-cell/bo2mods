# BO3 Rev Porting Architecture

## Goal
Bring the BO3 Apothicon Servant into BO2 in a way that is playable, debuggable, and incrementally improvable.

## Current architecture
The active architecture is:

1. BO2 donor shell
2. BO3-derived reduced weapon-only rig
3. BO3-to-BO2 material/image translation
4. BO2-safe FF/IPAK packaging
5. BO3-inspired black-hole behavior implemented with T6-safe GSC primitives

This is intentionally not a literal "drop BO3 straight into BO2" architecture.

## Why this architecture won

### The fresh-name path lost
The project proved that a fresh-name engine weapon identity was blocked in the normal mod lane.

So the architecture had to move from:
- new name first

to:
- donor shell first

### The Ray Gun donor path lost
The project proved that `ray_gun_zm` carried hidden first-person composition baggage that kept crashing even when the visible model was tiny or stock.

So the architecture had to move from:
- Ray Gun themed donor

to:
- whichever donor shell is structurally safest

That is how the project ended up on `mg08_zm`.

## Layer model

### Layer A: runtime hygiene
Tools:
- `_build/runtime_reset.ps1`

Purpose:
- keep mod/base lanes understandable
- avoid polluted survival FF state

### Layer B: donor-shell override proof
Tools:
- `_build/build_bo3_rev_idg_probe.py`
- `_build/run_bo3_rev_probe_case.py`

Purpose:
- prove whether the staged weapondef actually won
- isolate shell behavior from art behavior

### Layer C: rig reduction
Tools:
- `_build/build_bo3_rev_idg_reduced_rig.py`
- `_build/build_bo3_rev_idg_weapon_only_rig.py`
- `tools/asset_port_pipeline/blender_idg_reduce_worker.py`

Purpose:
- keep the BO3-derived rig under T6 first-person limits

### Layer D: material and image translation
Tools:
- `tools/asset_port_pipeline/translate_bo3_materials_to_bo2.py`
- `_build/build_bo3_rev_idg_probe.py`

Purpose:
- translate BO3 texture sets into BO2-safe materials
- emit a matching IPAK

### Layer E: gameplay logic
Tools:
- `mods/bo3_rev/scripts/mod_i_am_mod.gsc.in`

Purpose:
- implement the Servant behavior on top of the donor shell
- keep the logic independent from unfinished animation polish

## Current runtime behavior architecture
The current weapon logic does this:

1. Spawn player
2. Grant donor shell
3. Watch `weapon_fired`
4. Trace an impact point
5. Spawn a timed singularity entity
6. Pull zombies inward
7. Kill them inside the inner radius
8. Play placeholder BO2-safe FX for lifetime feedback

This is BO3 behavior translated into BO2 primitives, not a verbatim BO3 script port.
