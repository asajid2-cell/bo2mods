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

The newer FX runtime probe is useful, but the project learned another hard rule:
- intrusive deep consumer-tracing builds can create fake startup crashes
- normal render-polish testing should use the safe probe or no probe at all
- probe work should now be reserved for new real regressions, not day-to-day visual tuning

## 7. Full runtime-zone fidelity is its own barrier
The project now has proof that:
- minimal custom FF/IPAK packaging can be safe
- clientscript ownership can be achieved on the full runtime lane
- the rebuilt full `so_zsurvival_zm_transit.ff` can still crash before spawn

That means there is a separate barrier beyond asset conversion:
- faithfully rebuilding enough of the stock survival runtime zone for startup to complete

This is not just an FX problem.
It affects whether any client render probe can reach spawn at all.

## 8. Ownership and render are different problems
For a long time these were mixed together.

The project now treats them separately:
- ownership problem:
  - does the engine actually execute our client helper?
- render problem:
  - if the helper executes and calls `playfx`, does the effect appear?

Current state:
- ownership: proven on the full runtime lane
- render existence: proven on the full runtime lane
- current remaining problem: fidelity and consistency, not basic visibility

## 9. Loose global FX-image overrides are unsafe for this port
The project now has concrete proof that staging BO3 FX images into the loose global:
- `AppData\\Local\\Plutonium\\storage\\t6\\images`

can push accepted BO3 `0x0D` image classes into a crashing runtime lane.

This first showed up with:
- `$identitynormalmap`

and then with:
- `fxt_debris_clump`

That means:
- packed/mod-lane BO3 FX images are acceptable
- loose global BO3 FX-image overrides are not a safe default for this port

## 10. Naming collisions were a real render barrier
Translated BO3 surfaces under stock-looking names could leak onto unrelated stock zombie/fire/dirt effects.

That is why the project moved to:
- `bo3rfx_*` namespaced BO3 surfaces

The cost:
- a temporary step back in visibility while the old leaked path disappeared

The payoff:
- the current visible Servant lane is now the real BO3 surface path, not a polluted stock-override artifact
