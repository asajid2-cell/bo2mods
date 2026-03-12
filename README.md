# BO3 -> BO2 Asset Porting Workspace

This repo is a BO2/Plutonium modding workspace kept inside the game root so the tooling can build, unlink, relink, deploy, and validate fastfiles against the live runtime.

The current active lane is `mods/bo3_rev`: porting the BO3 Apothicon Servant into BO2 by combining:
- an engine-recognized BO2 donor shell
- a BO3-derived reduced first-person weapon rig
- a BO3-to-BO2 material/IPAK translation path
- BO3-inspired black-hole gameplay logic implemented in T6-safe GSC

## Current state
- The live donor shell is `mg08_zm`.
- The custom Servant viewmodel loads in-game without the old 160-bone crash.
- The black-hole pull/kill logic works in BO2.
- Demo/admin commands work:
  - `.p`
  - `.round`
  - `.fast`
  - `.hits`
  - `.debug`
- Remaining work is polish, not first proof:
  - better animation parity
  - better material/color fidelity
  - better black-hole FX and presentation

## Repo role
This repo is both:
- a build/deploy spine
- an engineering notebook of what was tried, what failed, and what was learned

Tracked source lives mainly in:
- `mods/bo3_rev/`
- `_build/`
- `tools/asset_port_pipeline/`
- `docs/`
- `native/dobj_probe/` (source only; not part of the normal safe workflow)

Generated FF/IPAK/GLB/output trees are intentionally ignored.

## Asset note
This repo does not ship copyrighted BO2/BO3 game assets. You must provide your own extracted baselines and source dumps.

## Start here
- Docs index: `docs/README.md`
- Current project status: `docs/status.md`
- Build/deploy loop: `docs/how-to/build-and-deploy.md`

## Credits
Docs structure uses the Diataxis framework: `docs/credit.md`
