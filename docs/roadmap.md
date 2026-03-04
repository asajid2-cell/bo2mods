# Roadmap / Plan

This is the “what next” plan written for someone actively iterating in the repo.

## Stage 0 — Never regress runtime isolation (always)
**Done / enforced**:
- Use `_build/runtime_reset.ps1` for `clean` and `dev` lanes.
- Do not debug multiple layers in the same run (deploy + gsc + xanim) without a run ID and a rollback plan.

## Stage 1 — Stabilize first-person viewmodel (current blocker)
Goal: equipping the Thundergun carrier should not change camera orientation (no snap behind/up), and the gun should sit in a stable, expected view position.

Work items:
1. Prove which asset is actually loaded at runtime
   - Confirm the game is using the deployed `so_zsurvival_zm_transit.ff` and the expected model names.
   - Verify whether xmodels are cached across runs and require full restarts for correctness.
2. Normalize the camera/tag chain to T6 contracts
   - Ensure `tag_view` is the true rig root for view + camera chain.
   - Ensure `tag_camera` and `tag_cambone` are not driven by torso motion during equip/sprint.
3. Establish a minimum “camera-safe” anim set
   - Temporarily force camera-related bones to identity in high-risk anims (raise/sprint) if needed.
   - Add a regression script that checks “camera basis unchanged on equip” (log-based where possible).

Supporting doc:
- `docs/how-to/debug-viewmodel-flip.md`

## Stage 2 — Commit to the final architecture for full BO3 visuals
Once camera behavior is stable, choose and lock the approach:

Option A (most aligned with “full BO3”):
- Use the BO3 combined rig as viewhands via `setviewmodel`, keep `gunModel` as no-visual carrier.
- Pros: closest to BO3 presentation.
- Cons: bone cap pressure, and T6 camera chain expectations are strict.

Option B (more engine-native):
- Use `gunModel=rogue_tg_view` + stock T6 viewhands.
- Pros: lowest risk for camera/control stability.
- Cons: harder to get “exact BO3 hands” because you’re binding into a foreign hand rig.

## Stage 3 — Full per-bone curve fidelity (BO3 frame encoder)
Current pipeline can ensure coverage and parity at the “asset exists + right frame count” level.
Next is correctness:
- Encode full per-bone per-frame transforms for all 133 parts
- Ensure correct quantization, delta usage, and pointer stream order for T6 loader
- Add deterministic round-trip oracles against known-good donor assets

Supporting docs:
- `docs/reference/t6-xanimparts-format.md`
- `docs/explanation/constraints-and-barriers.md`

## Stage 4 — FX/sound/camo chains (later)
After the viewmodel and animation fidelity are stable:
- Link/pack sounds (SAB/alias chains)
- Fix/verify FX tags and effect assets
- Bring in camos only after IPak/image chain is deterministic

