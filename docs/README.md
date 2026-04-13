# Documentation

These docs now reflect the current BO3 Rev Apothicon Servant work, not the older thundergun-only lane.

Use them in this order if you are picking the project back up:
- `docs/status.md`
- `docs/explanation/master-deep-dive-timeline.md`
- `C:\Users\Ahmed\Downloads\t7-source\scripts\zm\_zm_weap_idgun.gsc`
- `C:\Users\Ahmed\Downloads\t7-source\scripts\shared\ai\zombie_vortex.gsc`
- `docs/servant-dossier.html`
- `docs/servant-fx-preview.html`
- `docs/tutorials/getting-started.md`
- `docs/how-to/build-and-deploy.md`
- `docs/explanation/history-and-findings.md`

## Tutorials
Learning-oriented step-by-step material.
- `docs/tutorials/getting-started.md`

## How-to guides
Task-oriented operational docs.
- `docs/how-to/build-and-deploy.md`
- `docs/how-to/debug-runtime.md`
- `docs/how-to/debug-viewmodel-flip.md`
- `docs/how-to/runbook.md`

## Reference
Authoritative "look it up" material.
- `docs/commands.md`
- `docs/servant-fx-preview.html`
- `docs/servant-fx-preview-data.json`
- `docs/reference/env-vars.md`
- `docs/reference/repo-layout.md`
- `docs/reference/t6-xanimparts-format.md`

## Explanation
Architecture, constraints, and the detailed experiment history.
- `docs/servant-dossier.html`
- `docs/explanation/master-deep-dive-timeline.md`
- `docs/explanation/porting-architecture.md`
- `docs/explanation/porting-foundation.md`
- `docs/explanation/constraints-and-barriers.md`
- `docs/explanation/history-and-findings.md`
- `docs/explanation/bo3_to_bo2_apothicon_architecture.tex`
- `docs/explanation/bo3_to_bo2_apothicon_architecture.pdf`

## What changed recently
The current documented path is:
- fresh-name weapon identity was proven blocked in normal mod-lane registration
- `ray_gun_zm` was proven to be a bad donor shell because of hidden first-person composition
- `mg08_zm` is the current donor shell
- the current weapon uses a reduced BO3-derived weapon-only rig
- black-hole gameplay logic is live in GSC
- minimal custom FF/IPAK packaging was proven and moved into the real Servant lane
- clientscript ownership is proven on the full runtime lane
- namespaced `bo3rfx_*` BO3 FX surfaces now render in-game
- the old loose-image crash lane was fixed by removing staged FX images from the loose global `storage\\t6\\images` path
- the visible MG08 FX bridge model was removed; the live bridge now uses `tag_origin`
- the old "shot did nothing" case was partly a real gameplay gate: firing while a vortex was already active
- the active vortex now gets replaced instead of silently blocking the next shot
- the current live checkpoint build is `0321232501_4c7e1d`
- BO3 Servant gameplay parity work is now being driven from the real local T7 scripts
- the stock phosphorous flare contract is deferred isolated probe work, not the live default
- the current work is visual polish:
  - final portal consistency
  - slight direction/background-dependent fade
  - blend/alpha tuning on the phosphorous core
  - phosphorous fidelity
  - final vortex layer semantics
- current runtime/control split:
  - repo / tooling / Plutonium-side workspace: `Z:\Games\pluto_t6_full_game`
  - clean stock game runtime: `Z:\Games\t6-clean\pluto_t6_full_game`
- the old synthetic zombie support alias `ipak`s were a self-inflicted runtime repair artifact, not real missing stock DLC
- the current active crash boundary is the generic `fs_game` mod-session support lane, not the Servant payload itself

## Credits
- `docs/credit.md`
