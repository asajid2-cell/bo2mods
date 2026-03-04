# BO3 -> BO2 Porting Architecture (v2)

## 1. Goal
Build a repeatable BO3-to-BO2 asset port pipeline that can scale from a single weapon proof-of-concept (Thundergun) to full map/system ports, without contaminating base runtime or losing debuggability.

## 2. Core Decision
Use `tools/asset_port_pipeline` as the canonical pipeline spine.

Treat `_build/*.py` binary patch utilities as R&D tools only, behind explicit opt-in experiments.

Why:
- `tools/asset_port_pipeline` already provides staged conversion, validation, linker-oracle feedback, remediation loops, and integration packaging.
- `_build` patch scripts are useful for format forensics, but they are too easy to mix with runtime/deploy and create non-reproducible states.

## 3. Existing Tooling Inventory

### 3.1 Canonical spine (`tools/asset_port_pipeline`, 36 Python tools)
- Extraction/staging: `extract_t7_thundergun_bundle.py`, `transfer_thundergun_to_bo2.py`
- Geometry conversion: `convert_cod_bin_with_blender.py`, `blender_convert.py`
- Validation: `validate_assets.py`, `fidelity_audit.py`
- Compile feedback: `linker_oracle.py`, `build_compile_dataset.py`, `remediate_compile_failures.py`
- Animation transform: `retarget_xanim_exports.py`, `normalize_xanim_exports.py`
- Gameplay translation: `build_bo2_gameplay_baseline.py`, `translate_weapon_gameplay.py`
- Integration/package: `finalize_bo2_integration.py`
- Orchestration: `run_thundergun_e2e.py`, `run_full_pipeline.ps1`

### 3.2 R&D / low-level tooling (`_build`, many scripts)
- Binary format/patching: `patch_zone_xanims.py`, `compile_xanim_zone.py`, `strict_xanim_parser.py`, `ff_integrity_check.py`
- Deployment/runtime control: `runtime_reset.ps1`, `runtime_health_check.py`, `preflight_deploy_ff.py`, `two_phase_build.py`
- Numerous one-off experiments (`_tmp_*`, `test_*`)

## 4. Why progress stalled
1. Runtime contamination
- Base and mod deployment targets were mixed over time.
- Multiple active mods / storage overrides caused non-local failures.

2. Debug scope mixing
- Animtree/mech initialization, map load health, thundergun registration, and animation payload translation were debugged in the same runs.

3. Missing phase gates
- No strict requirement that one layer passes before moving to the next.
- Result: symptoms looked random (hang, COM_ERROR, giveweapon fail).

4. Artifact sprawl
- Generated outputs and source-like files coexisted in large shared trees, making provenance unclear.

## 5. Architecture: Layered port stack

### Layer A: Runtime Isolation (must always pass first)
Purpose: keep test runtime deterministic.
Owner tools:
- `_build/runtime_reset.ps1`
- `_build/runtime_health_check.py`

Rules:
- `clean` lane for normal gameplay.
- `dev` lane with one active mod only.
- No base `zone/all` overwrite unless explicitly approved for a bounded test.

### Layer B: Structural Conversion
Purpose: convert mesh/material/anim containers into BO2-compilable shapes.
Owner tools:
- `blender_convert.py`
- `convert_cod_bin_with_blender.py`
- `retarget_xanim_exports.py`
- `normalize_xanim_exports.py`

This layer answers: "Can this asset compile/load structurally?"

### Layer C: Semantic Translation
Purpose: map BO3 behavior semantics onto BO2 gameplay/animation contracts.
Owner tools:
- `build_bo2_gameplay_baseline.py`
- `translate_weapon_gameplay.py`
- manually maintained translation profiles/maps (`skeleton_map_bo3_to_bo2.json`, weapon field mappings)

This layer answers: "Does this asset behave correctly in BO2 expectations?"

### Layer D: Build and Integration
Purpose: produce installable bundles with deterministic manifests.
Owner tools:
- `linker_oracle.py`
- `remediate_compile_failures.py`
- `finalize_bo2_integration.py`
- `run_thundergun_e2e.py`

This layer answers: "Can we produce a consistent, loadable FF/IPAK package?"

### Layer E: Runtime Validation
Purpose: validate map load, registration, and interactive behavior.
Owner tools:
- `_build/runtime_health_check.py`
- in-game debug events (`[ROGUE]` tg_step/tg_give logs)

This layer answers: "Does it work in-session, not just in compile?"

## 6. Semantic translation model (what must be translated)

### 6.1 Skeleton/animation semantics
- Bone naming and expected tags must map to BO2 conventions.
- Animation channel sets must satisfy BO2 parser/runtime constraints.
- Frame/bone-part coverage must be valid for load-time and playback.

### 6.2 Weapon behavior semantics
- BO3 weapon defs contain fields/assumptions outside BO2 envelopes.
- Must clamp/remap to BO2-observed distributions and valid references.
- "giveweapon accepts asset" is a semantic gate, not only a compile gate.

### 6.3 Script/animtree semantics
- BO3 scripts can require animtrees/assets BO2 transit runtime never loads.
- Must either supply required animtrees or gate mech/tomb features by map/context.

### 6.4 Material/fx semantics
- Many missing material/fx lines are tolerable warnings.
- Some are hard blockers when referenced by required gameplay scripts.

## 7. Canonical data domains (no mixing)

1. Source domain (immutable)
- BO3 dumps, BO2 baseline dumps (`zone_dump`, `_build/t6_asset_dump`)

2. Build domain (generated)
- `_build/asset_port_pipeline/<run_id>/...`
- All intermediate conversion artifacts and reports

3. Deploy domain (runtime)
- `mods/<mod>/zone/all`
- `%LOCALAPPDATA%/Plutonium/storage/t6/mods/<mod>/zone/all`

Hard rule:
- Build domain never directly edits source domain.
- Deploy domain is only written by explicit install/finalize steps.

## 8. Phase gates (required)

Gate G0: Runtime hygiene
- Pass: one active dev mod, no stale autoload remnants, baseline safety checks pass.
- Tools: `runtime_reset.ps1`, `runtime_health_check.py`

Gate G1: Structural conversion
- Pass: converted assets produce no hard preflight failures.
- Tools: `run_thundergun_e2e.py --strict-preflight`

Gate G2: Compile acceptance
- Pass: linker oracle or finalize compile succeeds (with remediation if needed).
- Tools: `linker_oracle.py`, `finalize_bo2_integration.py`

Gate G3: Registration acceptance
- Pass: runtime log shows no missing rogue weapon registration; tg give step can succeed.
- Signal examples:
  - No `Could not load weapon "rogue_thundergun*_zm"`
  - `[ROGUE] event=tg_step ... after_giveweapon ... ok=1`

Gate G4: Behavior acceptance
- Pass: weapon can be given/switched/fired without startup crash/hang.

Do not advance to next gate until current gate is green.

## 9. What to stop doing
- Stop multi-variable runs (anim patch + map script changes + deployment strategy changes at once).
- Stop ad-hoc copying files into runtime paths outside scripted deployment.
- Stop treating successful map load as proof of weapon semantic compatibility.

## 10. What to start doing
- Every run has a run ID and report bundle.
- Every run changes one variable class only.
- Every failure is tagged by layer (`runtime`, `registration`, `animation_semantic`, `compile`, `script_animtree`).

## 11. Immediate backlog (ordered)
1. Enforce pipeline spine
- Use `run_thundergun_e2e.py` as default orchestrator.
- Keep `_build` xanim patching in isolated experiment branches only.

2. Strengthen health classification
- Done: `_build/runtime_health_check.py` now classifies missing animtree, core weapon surface breakage, registration failures, giveweapon rejection, and gamestate hangs.

3. Fix deployment helper correctness
- Done: `_build/preflight_deploy_ff.py` attribute bug fixed.

4. Build semantic translation profiles
- Explicit mapping docs for:
  - weapon fields
  - animation coverage expectations per state
  - required tags/bones per asset class

5. Add per-run manifest discipline
- Each run should record:
  - command line
  - input hashes
  - output FF hash
  - runtime classification result

## 12. Expected result
This architecture will not magically make BO3 assets compatible with BO2. It will make incompatibilities observable, localizable, and fixable in sequence. That is what enables scaling beyond Thundergun to harder ports.
