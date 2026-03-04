# Status (Current Stage)

Last updated: 2026-03-04

## Goal
Port BO3 Thundergun (T7) assets into BO2 (T6 / Plutonium) with **full-fidelity visuals and animation**, not donor “tape”.

## What currently works
- **Reproducible build/deploy spine:** `python _build/two_phase_build.py`
  - Builds and deploys:
    - Patched map/survival fastfile: `so_zsurvival_zm_transit.ff`
    - IPak bundle: `so_zsurvival_zm_transit.ipak`
    - Runtime custom-xanim lane: `mod_load.ff` (custom xanim fastfile loaded at runtime)
- **Runtime isolation lanes:**
  - `clean` lane restores baseline fastfiles and disables mods.
  - `dev` lane enables exactly one mod (`zm_roguelike_panzer`) for controlled tests.
  - Tool: `_build/runtime_reset.ps1` (see `docs/how-to/debug-runtime.md`).
- **Weapon grant path is stable:**
  - The mod’s `.tg` logic can reliably “grant” a carrier weapon and drive the Thundergun behavior watcher.
  - The pipeline uses a **truth alias carrier** to bypass `weapondef_unregistered` for new weapon names.

### XAnim runtime coverage (current conversion milestone)
- **All 28 `vm_thunder_gun_*` xanim aliases resolve to non-stub payloads at runtime** via the `mod_load.ff` lane.
- The analyzer can verify frame parity against the deployed runtime `mod_load.ff`.
- Important nuance:
  - “REAL + frame parity” means the assets exist and load with the expected frame counts.
  - It does **not** automatically guarantee perfect curve/bone transform fidelity (that’s the next fidelity stage).

## What is currently broken (active blocker)
### Viewmodel equip/camera orientation
When switching to the Thundergun carrier weapon, the first-person camera can “flip” (appear to snap behind/up), which makes controls feel inverted.

Current hypothesis:
- This is caused by **viewmodel rig contracts** in T6:
  - `tag_view`, `tag_ads`, `tag_cambone`, `tag_camera` hierarchy + bind orientation
  - Which bones are driven by XAnim state on equip/raise/sprint
  - How the engine derives the camera basis from the viewmodel DObj

Recent mitigation work:
- GLB repair work in `_build/two_phase_build.py` attempts to normalize the camera chain to match stock T6 viewhands.
- Still requires runtime verification (cache invalidation and “actual loaded asset” checks).

### First-person presentation is still unstable
Depending on the current hand model strategy and build profile, you may see:
- invisible or incorrect hands
- weapon sitting off-screen / too high
- state transitions (sprint/raise) that tilt or “fall” the camera

These are symptoms of **engine contract compliance** issues (rig/tag basis + which bones are driven per state), not a “missing asset” problem.

## Constraints (hard caps)
- **T6 first-person DObj bone cap**: 160 bones (combined gun + hands/viewhands).
  - Exceeding this crashes with `dobj ... has more than 160 bones`.
- **Weapon registration barrier:**
  - T6 can refuse to give weapons if their weapondef isn’t registered/included early enough.
  - Current workaround is carrier alias + behavior proxy (intent is to later transition to true weapondefs once registration is proven).

## Where we are in the pipeline (layer model)
This maps to the “layer stack” in `docs/explanation/porting-architecture.md`.

- Layer A — Runtime isolation: **PASS**
- Layer B — Structural conversion (models/materials/xanims compile): **PASS (for current dataset)**
- Layer C — Semantic translation (weapon fields + state mapping): **PASS enough to exercise viewmodel states**
- Layer D — Integration packaging: **PASS**
- Layer E — Engine contract compliance (viewmodel camera/tags/bone budget): **IN PROGRESS (current blocker)**

## Next milestone
Make equip/sprint/raise states stable (no camera flip) with:
- correct camera/tag hierarchy
- correct bind orientation
- and a “known-good” state set we can regress-test automatically.

See plan: `docs/roadmap.md`.
