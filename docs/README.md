# Documentation

These docs now reflect the current BO3 Rev Apothicon Servant work, not the older thundergun-only lane.

Use them in this order if you are picking the project back up:
- `docs/status.md`
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
- `docs/reference/env-vars.md`
- `docs/reference/repo-layout.md`
- `docs/reference/t6-xanimparts-format.md`

## Explanation
Architecture, constraints, and the detailed experiment history.
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

## Credits
- `docs/credit.md`
