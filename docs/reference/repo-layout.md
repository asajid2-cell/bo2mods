# Reference: Repo Layout

This repo is intentionally inside the BO2 game root because the tooling reads and writes live fastfile paths, Plutonium storage paths, and extracted asset trees.

Only source and documentation should be tracked. Generated FF/IPAK/GLB/output trees should not.

## Core tracked areas

### `mods/bo3_rev/`
Current active mod source.

Tracked here:
- raw GSC source
- GSC templates

Ignored here:
- built `zone/all` FF/IPAK outputs

### `_build/`
Current orchestration and build helpers.

Important current source files:
- `build_bo3_rev_idg_probe.py`
- `run_bo3_rev_probe_case.py`
- `build_bo3_rev_idg_reduced_rig.py`
- `build_bo3_rev_idg_weapon_only_rig.py`
- `build_bo3_rev_donor_pose_preview.py`

Generated output trees under `_build/bo3_rev_*` are intentionally ignored.

### `tools/asset_port_pipeline/`
Reusable conversion and translation helpers.

Important current additions:
- `blender_idg_reduce_worker.py`
- `blender_idg_preview_worker.py`
- `blender_donor_pose_preview_worker.py`
- `idg_reduced_rig_manifest.json`
- `idg_weapon_only_rig_manifest.json`
- `idg_weapon_acceptance_rig_manifest.json`

### `native/dobj_probe/`
Source for a shelved local runtime hook experiment used to inspect first-person DObj failures.

Source is tracked.
Built binaries, logs, and object files are ignored.

### `docs/`
Project documentation.

This now documents the BO3 Rev Apothicon Servant path as the active lane.

## High-churn generated areas
These should not be committed:
- `zone/`
- `zone_dump/`
- `_build/bo3_rev_idg_probe/` generated subtrees
- `_build/bo3_rev_idg_reduced/`
- `_build/bo3_rev_idg_weapon_only/`
- `_build/bo3_rev_idg_weapon_acceptance/`
- `_build/bo3_rev_probe_cases/`
- `mods/**/zone/**`

## Why `_build/` scripts stay in Git
The `_build` scripts are not throwaway output. They are the reproducible logic that:
- stages donor shells
- translates materials/images
- compiles runtime FF/IPAK outputs
- deploys to the correct lane
- writes reports that explain what each run actually did
