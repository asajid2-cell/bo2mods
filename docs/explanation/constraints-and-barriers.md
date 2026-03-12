# Constraints and Barriers

This document explains the real constraints the BO3 Rev project hit.

## 1. T6 first-person bone cap
The T6 first-person DObj cap is still the hard wall:
- combined first-person composition must stay under 160 bones

This is why the project moved away from:
- full BO3 rig + separate hands

and toward:
- reduced BO3-derived weapon-only rig

## 2. Fresh-name weapon identity barrier
The project proved that the following can all be true at once:
- registration code runs
- inclusion tables show the weapon
- the donor surface is valid
- the engine still does not resolve a new weapon name

That is why `apothicon_servant_zm` is not the live shell today.

## 3. Donor shell choice is not cosmetic
The donor shell determines more than basic weapon stats.

`ray_gun_zm` was proven to be structurally bad for this project because it still triggered first-person composition failures even when the visible gun model was tiny or stock.

That is why donor-shell selection is now treated as an architecture decision, not a cosmetic preference.

## 4. Material/IPAK contract matters
Custom BO3-derived materials did not become stable until the build emitted and deployed a matching runtime IPAK.

Before that, the project could:
- compile
- stage images
- and still crash at runtime because the image package contract was incomplete

## 5. BO3 authoring contracts are richer than BO2
BO3 assets assume:
- more bones
- richer material/shader inputs
- different first-person presentation assumptions

BO2 will accept parts of that contract, but not all of it unchanged.

## 6. Client runtime introspection is risky on Plutonium
There is native source in `native/dobj_probe/` for a shelved first-person DObj inspection hook.

The reason it is shelved:
- client injection carries Plutonium anti-cheat risk outside safe local/LAN conditions

So the default workflow remains:
- GSC
- FF/IPAK
- build reports
- runtime logs

not client injection.
