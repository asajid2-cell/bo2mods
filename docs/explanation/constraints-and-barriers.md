# Explanation: Constraints & Barriers (T7 → T6)

This document explains the “invisible walls” you keep running into when trying to do a full BO3-quality port in BO2.

## 1) The T6 first-person bone cap (the 160-bone DObj limit)
T6 has a hard limit on the number of bones in the first-person DObj:
- gun model bones + hand model / viewhands bones must be ≤ 160
- exceeding this fails with:
  - `dobj for xmodel '<name>' has more than 160 bones`

Why this matters for a “full BO3” port:
- The BO3 combined viewmodel rig can be ~133 bones by itself.
- That leaves very little headroom for any additional viewhands/hand model bones.

Implication:
- A literal “drop in BO3 rig + drop in BO3 hands” is usually impossible in T6 without **bone pruning / reweighting**.

## 2) Weapon registration / “weapondef_unregistered”
T6 can refuse to grant weapons even when:
- the weapon file exists
- the zone contains the string name

Because:
- weapondefs must be registered/included in the correct lifecycle window
- “included” checks and “can use content” checks can still pass while the internal weapondef pointer is null-ish

This repo’s current workaround:
- use a known registered carrier weapon (`ak74u_zm`) and patch its weaponfile fields to reference thundergun assets/anims.
- drive “true thundergun behavior” via script watchers.

This is not “final port quality”; it is a **registration bypass** to unblock animation/model work.

## 3) Viewmodel camera/tag contracts (why camera flips happen)
T6 derives camera/view basis from a particular tag/bone hierarchy:
- `tag_view`, `tag_ads`, `tag_cambone`, `tag_camera`

If your imported rig:
- has different parentage, or
- uses different bind rotations, or
- drives camera bones via torso motion during equip

…then equipping the weapon can rotate the camera basis and feel like controls inverted.

This is a structural contract problem, not an “animation looks wrong” problem.

See:
- `docs/how-to/debug-viewmodel-flip.md`

## 4) XAnimParts binary compatibility
Even when you can “store” animation payloads in a fastfile, T6 is picky about:
- pointer stream ordering
- delta vs non-delta usage
- quantization formats

The repo keeps a format reference here:
- `docs/reference/t6-xanimparts-format.md`

## 5) What “full BO3-quality” realistically means here
To get a true full port, you eventually need:
- a correct per-bone curve encoder for T6 XAnimParts
- a final rig architecture that respects:
  - bone cap
  - camera chain contracts
  - weapon state machine expectations
- stable packaging (no lane mismatch, no asset provenance ambiguity)

The current state is “pipeline can build and deploy” but “engine-level viewmodel contracts still being satisfied.”

