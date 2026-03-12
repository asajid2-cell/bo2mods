# BO3 Rev Foundation

This is the current operational foundation for the repo.

## The core rule
Do not mix runtime provenance problems, donor-shell problems, rig problems, material problems, and gameplay logic in the same conclusion.

The project only started moving once each failure was isolated into its own lane.

## The lane model

### Clean lane
Used before normal play or before resetting back to a known baseline.

### Dev lane
Used for controlled local BO3 Rev testing with one mod enabled.

### Base deploy lane
Used when the survival FF or IPAK must actually win over stock.

The current working Servant path uses base deploy because mod-lane-only deployment was not sufficient for several donor and survival-zone tests.

## The big architectural decision
Stop treating the project as:
- "make a brand new engine weapon name work first"

And treat it as:
- "make a stable donor-shell Servant work first"

That shift is what unblocked real progress.

## What the project proved before the current path
- Fresh-name `apothicon_servant_zm` registration can succeed at the zombies/script layer and still fail at the engine-weapon layer.
- `ray_gun_zm` can be a valid override and still be the wrong shell because of hidden first-person composition.
- BO3 meshes can be valid assets and still fail in BO2 because of shell/path/contract problems unrelated to the mesh itself.

## Current philosophy
1. Prove the shell path.
2. Prove the rig fits.
3. Prove the material/IPAK path.
4. Prove gameplay logic.
5. Polish animation and presentation.

That order is what got the project from repeated crashes to a working singularity weapon.
