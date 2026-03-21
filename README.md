# BO3 -> BO2 Asset Porting Workspace

This repo is a BO2/Plutonium modding workspace kept inside the game root so the tooling can build, unlink, relink, deploy, and validate fastfiles against the live runtime.

The current active lane is `mods/bo3_rev`: porting the BO3 Apothicon Servant into BO2 by combining:
- an engine-recognized BO2 donor shell
- a BO3-derived reduced first-person weapon rig
- a BO3-to-BO2 material/IPAK translation path
- BO3-inspired black-hole gameplay logic implemented in T6-safe GSC

## Current state
- The live donor shell is `mg08_zm`.
- The FX bridge host is now `tag_origin`, not the visible `t6_wpn_zmb_mg08_world` bridge model.
- The custom Servant viewmodel loads in-game without the old 160-bone crash.
- The black-hole pull/kill logic works in BO2.
- The BO3-derived vortex FX path now renders in-game on the real runtime lane.
- The current BO3 FX contract uses namespaced `bo3rfx_*` materials/images to avoid leaking broken surfaces onto unrelated stock effects.
- The current stable portal lane is the safe glow contract, not the stock phosphorous flare contract.
- Repeated shots no longer silently no-op while an old vortex is active; new shots replace the old active vortex.
- The current FX-loader checkpoint is "working with light polish debt", not "still blocked on loading".
- The current live checkpoint build is `0321232501_4c7e1d`.
- BO3 Servant gameplay parity work is now grounded in the local T7 source scripts.
- Demo/admin commands work:
  - `.p`
  - `.round`
  - `.fast`
  - `.hits`
  - `.debug`
- Remaining work is now polish, not first proof:
  - final portal consistency polish, especially slight direction/background-dependent fade
  - visible lifetime polish on the layered hole
  - phosphorous texture fidelity and softness
  - final per-layer vortex semantics tuning
  - better animation parity
  - finish the BO3 gameplay parity port from the real T7 scripts

## BO3 source parity
The BO3 Servant / vortex source is now available locally for reference:
- `C:\Users\Ahmed\Downloads\t7-source\scripts\zm\_zm_weap_idgun.gsc`
- `C:\Users\Ahmed\Downloads\t7-source\scripts\shared\ai\zombie_vortex.gsc`
- `C:\Users\Ahmed\Downloads\t7-source\scripts\zm\_zm_weap_idgun.csc`

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
- Runtime/probe safety notes: `docs/how-to/debug-runtime.md`

## Credits
Docs structure uses the Diataxis framework: `docs/credit.md`
