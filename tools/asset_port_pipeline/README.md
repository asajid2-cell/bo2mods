# BO2 Asset Port Pipeline (Baseline)

This module gives you a reproducible baseline for BO3->BO2 asset conversion and adversarial training.

Scope implemented now:
- Build BO2 ground-truth statistics from dumped assets.
- Validate candidate assets against BO2 legality/style envelopes.
- Build feature datasets for adversarial training.
- Train a feature-space generator/discriminator.
- Deterministic xmodel pre-pass (`VERSION`, influence clamp, bone pruning).
- Blender conversion backend for real mesh outputs (`.fbx/.obj/.gltf/.glb -> glb + xmodel json`).
- Linker oracle for compile pass/fail labels.
- Compile-dataset builder using real linker outcomes.

Scope not implemented yet:
- Full animation retargeting quality parity for all rigs.
- Fully automatic BO3 weapon/script behavior translation to BO2 GSC.
- Texture/material semantic remastering across engines.

## 1) Build BO2 ground truth

```powershell
python tools\asset_port_pipeline\build_bo2_ground_truth.py `
  --roots _build\t6_asset_dump\zone_raw zone_dump\zone_raw `
  --output _build\asset_port_pipeline\bo2_ground_truth.json `
  --verbose
```

## 2) Validate assets (headless gate)

Validate a folder of candidates:

```powershell
python tools\asset_port_pipeline\validate_assets.py `
  --baseline _build\asset_port_pipeline\bo2_ground_truth.json `
  --inputs path\to\candidate_assets `
  --type auto `
  --output _build\asset_port_pipeline\validation_report.json
```

## 3) Deterministic xmodel compression

Apply BO2-safe pre-pass before learning:

```powershell
python tools\asset_port_pipeline\compress_xmodel_export.py `
  --input path\to\bo3_models `
  --output _build\asset_port_pipeline\compressed_models `
  --target-version 6 `
  --max-influences 4 `
  --max-bones 128
```

## 4) Build feature dataset

Use BO2 as positives, BO3 (and/or synthetic corruptions) as negatives:

```powershell
python tools\asset_port_pipeline\build_feature_dataset.py `
  --bo2-root _build\t6_asset_dump\zone_raw `
  --source-root path\to\bo3_xmodel_exports `
  --negative-mode source+corrupt `
  --output-dir _build\asset_port_pipeline\dataset
```

## 5) Train adversarial feature model

```powershell
python tools\asset_port_pipeline\train_feature_gan.py `
  --dataset _build\asset_port_pipeline\dataset\dataset.jsonl `
  --meta _build\asset_port_pipeline\dataset\dataset_meta.json `
  --epochs 200 `
  --batch-size 64 `
  --output-dir _build\asset_port_pipeline\models
```

Outputs:
- `generator.pt`
- `discriminator.pt`
- `train_metrics.json`
- `converted_feature_samples.json`

## 6) Convert real meshes with Blender backend

This creates a full OAT-ready project structure:
- `.../<project>/xmodel/*.json`
- `.../<project>/model_export/*.glb`
- `.../<project>/zone_source/<project>.zone`

```powershell
python tools\asset_port_pipeline\blender_convert.py `
  --input path\to\bo3_meshes `
  --output-root _build\asset_port_pipeline\converted_zone_raw `
  --project-name bo3_ported_assets `
  --blender-exe "C:\Program Files\Blender Foundation\Blender 4.1\blender.exe" `
  --decimate-ratio 0.45 `
  --max-bones 128 `
  --max-weights 4
```

Skeleton mapping file used by converter:
- `tools/asset_port_pipeline/skeleton_map_bo3_to_bo2.json`

## 7) Linker oracle for compile labels

Compile one or more converted xmodels and get structured pass/fail diagnostics:

```powershell
python tools\asset_port_pipeline\linker_oracle.py `
  --xmodels _build\asset_port_pipeline\converted_zone_raw\bo3_ported_assets\xmodel\my_asset.json `
  --project-name oracle_my_asset `
  --linker tools\oat\Linker.exe `
  --load-zones zone\all\common_zm.ff `
  --auto-resolve-missing `
  --max-retries 2 `
  --dependency-roots zone_dump\zone_raw _build\t6_asset_dump\zone_raw `
  --output _build\asset_port_pipeline\linker_oracle_report.json
```

`--auto-resolve-missing` now does two retry actions:
- Stages missing dependency source files from `--dependency-roots`.
- Auto-adds inferred map fastfiles (for example `zone\all\zm_tomb.ff`) to linker preload zones when available.

## 8) Build compile dataset (real discriminator labels)

```powershell
python tools\asset_port_pipeline\build_compile_dataset.py `
  --xmodel-root _build\asset_port_pipeline\converted_zone_raw\bo3_ported_assets\xmodel `
  --linker tools\oat\Linker.exe `
  --load-zones zone\all\common_zm.ff `
  --auto-resolve-missing `
  --max-retries 2 `
  --dependency-roots zone_dump\zone_raw _build\t6_asset_dump\zone_raw `
  --cluster-top-k 25 `
  --output-dir _build\asset_port_pipeline\compile_dataset
```

Output:
- `_build\asset_port_pipeline\compile_dataset\compile_dataset.jsonl`
- `_build\asset_port_pipeline\compile_dataset\compile_dataset_meta.json`
- `_build\asset_port_pipeline\compile_dataset\compile_failure_summary.json` (top error signatures + missing-asset clusters)

## 9) Auto-remediate failed compile rows

Requeues failed rows from `compile_dataset.jsonl` through linker oracle with:
- dependency staging retries enabled
- source-map FF preload inferred from each xmodel path
- optional cluster-priority ordering from `compile_failure_summary.json`

```powershell
python tools\asset_port_pipeline\remediate_compile_failures.py `
  --dataset-jsonl _build\asset_port_pipeline\compile_dataset\compile_dataset.jsonl `
  --failure-summary _build\asset_port_pipeline\compile_dataset\compile_failure_summary.json `
  --linker tools\oat\Linker.exe `
  --load-zones zone\all\common_zm.ff `
  --max-retries 6 `
  --dependency-roots zone_dump\zone_raw _build\t6_asset_dump\zone_raw `
  --output-dir _build\asset_port_pipeline\compile_dataset\remediation
```

Outputs:
- `_build\asset_port_pipeline\compile_dataset\remediation\compile_remediation.jsonl`
- `_build\asset_port_pipeline\compile_dataset\remediation\compile_dataset_remediated.jsonl`
- `_build\asset_port_pipeline\compile_dataset\remediation\compile_remediation_report.json`

## 10) One-command pipeline runner

```powershell
powershell -ExecutionPolicy Bypass -File tools\asset_port_pipeline\run_full_pipeline.ps1 `
  -SourceRoot "path\to\bo3_meshes" `
  -ProjectName "bo3_ported_assets" `
  -BlenderExe "C:\Program Files\Blender Foundation\Blender 4.1\blender.exe"
```

With profile auto-tuning enabled:

```powershell
powershell -ExecutionPolicy Bypass -File tools\asset_port_pipeline\run_full_pipeline.ps1 `
  -SourceRoot "path\to\bo3_meshes" `
  -ProjectName "bo3_ported_tuned" `
  -AutoTune `
  -RemediateFailures `
  -ProfilesPath "tools\asset_port_pipeline\conversion_profiles.json" `
  -BlenderExe "C:\Program Files\Blender Foundation\Blender 4.1\blender.exe"
```

## 11) Auto-tune conversion profiles per asset

Runs profile sweep (`conversion_profiles.json`), compiles each candidate with linker oracle,
and assembles best outputs into one final project.

```powershell
python tools\asset_port_pipeline\auto_tune_conversion.py `
  --input path\to\bo3_meshes `
  --profiles tools\asset_port_pipeline\conversion_profiles.json `
  --project-name bo3_ported_tuned `
  --output-root _build\asset_port_pipeline\tuned_zone_raw `
  --workspace _build\asset_port_pipeline\auto_tune_workspace `
  --blender-exe "C:\Program Files\Blender Foundation\Blender 4.1\blender.exe" `
  --linker tools\oat\Linker.exe `
  --load-zones zone\all\common_zm.ff `
  --auto-resolve-missing `
  --max-retries 2 `
  --dependency-roots zone_dump\zone_raw _build\t6_asset_dump\zone_raw `
  --report _build\asset_port_pipeline\auto_tune_report.json
```

Outputs:
- Tuned final project: `_build\asset_port_pipeline\tuned_zone_raw\<project>`
- Trial diagnostics: `_build\asset_port_pipeline\auto_tune_workspace\reports\*.json`
- Selection report: `_build\asset_port_pipeline\auto_tune_report.json`

## 12) Build BO2 gameplay baseline (weapons)

Builds numeric envelopes, defaults, and known model/anim references from BO2 weapon dumps.

```powershell
python tools\asset_port_pipeline\build_bo2_gameplay_baseline.py `
  --roots zone_dump\zone_raw _build\t6_asset_dump\zone_raw `
  --output _build\asset_port_pipeline\bo2_gameplay_baseline.json
```

## 13) Translate weapon gameplay fields (BO3 -> BO2 envelope)

Clamps out-of-envelope numeric stats and remaps missing model/anim references to closest BO2-known values.

```powershell
python tools\asset_port_pipeline\translate_weapon_gameplay.py `
  --input path\to\source_weapons `
  --baseline _build\asset_port_pipeline\bo2_gameplay_baseline.json `
  --output-root _build\asset_port_pipeline\converted_gameplay `
  --project-name bo3_gameplay_port `
  --report _build\asset_port_pipeline\weapon_gameplay_translation_report.json
```

## 14) Generate boss parity GSC from profile

Use template profile:
- `tools/asset_port_pipeline/boss_profile_template.json`

Generate script:

```powershell
python tools\asset_port_pipeline\generate_boss_parity_gsc.py `
  --profile tools\asset_port_pipeline\boss_profile_template.json `
  --output _build\asset_port_pipeline\generated_gsc\panzer_ported.gsc `
  --report _build\asset_port_pipeline\boss_parity_report.json
```

## 15) Build map parity plan (full-map port)

Parses the source map `.zone`, classifies asset phases, and checks BO2-side coverage.

```powershell
python tools\asset_port_pipeline\plan_map_port.py `
  --source-zone-root path\to\bo3_zone_raw\zm_stalingrad `
  --source-map zm_stalingrad `
  --bo2-reference-roots zone_dump\zone_raw _build\t6_asset_dump\zone_raw `
  --output _build\asset_port_pipeline\map_port_plan.json
```

## 16) Bootstrap map port project from plan

Copies source assets that can be resolved, writes BO2 project zone file, and reports unresolved assets.

```powershell
python tools\asset_port_pipeline\bootstrap_map_port_project.py `
  --plan _build\asset_port_pipeline\map_port_plan.json `
  --project-name zm_stalingrad_bo2_port `
  --output-root _build\asset_port_pipeline\map_port_projects `
  --include-phases core_map render_assets gameplay_assets scripts `
  --only-bo2-missing `
  --max-assets 500 `
  --output-report _build\asset_port_pipeline\map_bootstrap_report.json
```

Default behavior only writes zone lines for assets actually copied into the bootstrap project.
Use `--keep-missing-zone-lines` only when you explicitly want unresolved placeholders in zone output.

Outputs:
- `_build\asset_port_pipeline\map_port_plan.json`
- `_build\asset_port_pipeline\map_port_projects\<project>\zone_source\<project>.zone`
- `_build\asset_port_pipeline\map_bootstrap_report.json`

## 17) Remediate bootstrap map project with linker loop

Runs linker repeatedly, stages missing dependencies when available, rewrites missing material techniquesets to nearest available BO2 techsets, and can prune unresolved zone lines to force a compilable subset.

```powershell
python tools\asset_port_pipeline\remediate_map_project.py `
  --project-root _build\asset_port_pipeline\map_port_projects\zm_stalingrad_bo2_port `
  --project-name zm_stalingrad_bo2_port `
  --linker tools\oat\Linker.exe `
  --load-zones zone\all\common_zm.ff zone\all\zm_tomb.ff `
  --dependency-roots zone_dump\zone_raw _build\t6_asset_dump\zone_raw `
  --max-retries 20 `
  --prune-unresolved `
  --output _build\asset_port_pipeline\map_project_remediation_report.json
```

Notes:
- Remediation now stages both explicit `Missing asset ...` and linker unresolved assets (`Could not load asset ...`) when stageable.
- Techniqueset fallback rewrites are enabled by default for missing techsets; disable with `--no-techset-fallback`.
- Retry loop is adaptive past `--max-retries` while remediation actions continue, capped by an internal hard limit.

`run_full_pipeline.ps1` also supports map planning/bootstrap/remediation in one run:
- `-EnableMapPortPlan`
- `-MapSourceZoneRoot <zone_raw\map>`
- `-MapSourceName <mapname>`
- `-MapBootstrapProject <bo2_project_name>`
- `-MapBootstrapMaxAssets <N>`
- `-MapRemediateProject`
- `-MapRemediateRetries <N>`
- `-MapRemediatePruneUnresolved`
- `-MapExportMeshPack`
- `-MapMeshPackRoot <path>`
- `-MapMeshPackReport <json>`
- `-FinalizeIntegrationBundle`
- `-IntegrationRoot <path>`
- `-IntegrationBundleName <name>`
- `-IntegrationCompile`
- `-IntegrationInstallZoneDir <mods\<name>\zone\all>`
- `-IntegrationReport <json>`

## 18) Generate starter zone_source template

```powershell
python tools\asset_port_pipeline\generate_zone_source_template.py `
  --project-name zm_tomb_port_patch `
  --source-map zm_tomb `
  --ipak-reads zm_tomb zm_transit `
  --output _build\asset_port_pipeline\zone_source_templates\zm_tomb_port_patch.zone
```

Static starter example:
- `tools/asset_port_pipeline/templates/zm_tomb_port_patch_template.zone`

## 19) Extract compiled script behavior profile

```powershell
python tools\asset_port_pipeline\extract_compiled_gsc_profile.py `
  --input zone_dump\zone_raw\zm_tomb\aitype `
  --output _build\asset_port_pipeline\compiled_gsc_profile.json
```

## 20) Generate BO2 script stubs from extracted profile

```powershell
python tools\asset_port_pipeline\generate_bo2_script_stubs.py `
  --profile _build\asset_port_pipeline\compiled_gsc_profile.json `
  --project-name zm_tomb_port_patch `
  --output _build\asset_port_pipeline\generated_gsc\zm_tomb_port_stub.gsc `
  --report _build\asset_port_pipeline\script_stub_report.json
```

`run_full_pipeline.ps1` supports this stage with:
- `-EnableScriptParity`
- `-ScriptSource <source_dir_or_file>` (optional if `-MapSourceZoneRoot` is set)
- `-ScriptProfileOut <json>`
- `-ScriptStubOut <gsc>`

## 21) Export compilable mesh pack from remediated map project

Exports the final surviving xmodels from a remediated project and rewrites LOD paths into a portable mesh pack.

```powershell
python tools\asset_port_pipeline\export_compilable_mesh_pack.py `
  --project-root _build\asset_port_pipeline\map_port_projects\zm_tomb_full_7548 `
  --project-name zm_tomb_full_7548 `
  --output-root _build\asset_port_pipeline\mesh_packs `
  --output-report _build\asset_port_pipeline\mesh_pack_export_zm_tomb_full_7548.json
```

Outputs:
- `_build\asset_port_pipeline\mesh_packs\<project>\xmodel\*.json`
- `_build\asset_port_pipeline\mesh_packs\<project>\model_export\*`
- `_build\asset_port_pipeline\mesh_pack_export_<project>.json`

## 22) Finalize BO2 integration bundle

Packages a remediated project into a clean BO2-ready bundle (`zone_raw` + `zone_source`), with optional compile/install.

```powershell
python tools\asset_port_pipeline\finalize_bo2_integration.py `
  --project-root _build\asset_port_pipeline\map_port_projects\zm_tomb_full_7548 `
  --project-name zm_tomb_full_7548 `
  --output-root _build\asset_port_pipeline\integration_ready `
  --compile `
  --linker tools\oat\Linker.exe `
  --load-zones zone\all\common_zm.ff zone\all\zm_tomb.ff `
  --output-report _build\asset_port_pipeline\finalize_bo2_integration_zm_tomb_full_7548.json
```

Optional install copy for compiled ff:

```powershell
python tools\asset_port_pipeline\finalize_bo2_integration.py `
  --project-root _build\asset_port_pipeline\map_port_projects\zm_tomb_full_7548 `
  --project-name zm_tomb_full_7548 `
  --output-root _build\asset_port_pipeline\integration_ready `
  --compile `
  --install-zone-dir mods\my_mod\zone\all
```

## 23) Transfer BO3 Thundergun bundle + BO2 logic package

Stages all BO3 Thundergun references from `t7_thundergun.gdt` and copies BO2-side gameplay logic files into a single integration bundle.

```powershell
python tools\asset_port_pipeline\transfer_thundergun_to_bo2.py `
  --t7-root "Z:\Games\T7 Assets V2.5 (2)\T7 Assets V2.5\T7 Assets" `
  --source-mod mods\zm_roguelike_panzer `
  --output-root _build\asset_port_pipeline\thundergun_bo2_transfer `
  --report _build\asset_port_pipeline\thundergun_bo2_transfer_report.json
```

Outputs:
- `_build\asset_port_pipeline\thundergun_bo2_transfer\t7_bundle\staged\...` (BO3 Thundergun referenced assets)
- `_build\asset_port_pipeline\thundergun_bo2_transfer\mod_raw\...` (BO2 Thundergun scripts + weapon files)
- `_build\asset_port_pipeline\thundergun_bo2_transfer\zone_source\thundergun_town_transfer.zone`
- `_build\asset_port_pipeline\thundergun_bo2_transfer_report.json`

## 24) End-to-end Thundergun integration (transfer -> convert -> patch -> compile/install)

Single pipeline entrypoint:

```powershell
python tools\asset_port_pipeline\run_thundergun_e2e.py `
  --t7-root "Z:\Games\T7 Assets V2.5 (2)\T7 Assets V2.5\T7 Assets" `
  --source-mod mods\zm_roguelike_panzer `
  --output-root _build\asset_port_pipeline\thundergun_e2e `
  --integration-project-name thundergun_town_full `
  --converter-mode mesh-folder `
  --mesh-input-root <path_to_preconverted_thundergun_meshes> `
  --max-submesh-vertices 2400 `
  --run-fidelity-audit `
  --strict-preflight `
  --verbose-converter `
  --compile `
  --remediate-on-fail `
  --remediate-retries 12 `
  --load-zones zone\all\common_zm.ff `
  --install-zone-dir mods\zm_roguelike_panzer\zone\all
```

With donor-based xanim retarget + custom xanim fastfile emit:

```powershell
python tools\asset_port_pipeline\run_thundergun_e2e.py `
  --t7-root "Z:\Games\T7 Assets V2.5 (2)\T7 Assets V2.5\T7 Assets" `
  --source-mod mods\zm_roguelike_panzer `
  --output-root _build\asset_port_pipeline\thundergun_e2e `
  --integration-project-name thundergun_town_full `
  --auto-codbin-converter `
  --converter-blender-exe "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" `
  --retarget-xanims `
  --xanim-donor _build\panzer_work\so_zsurvival_zm_transit\raw\xanim_export\vm_thunder_gun_idle.xanim_export `
  --xanim-retarget-min-match-ratio 0.35 `
  --compile-custom-xanim-zone `
  --custom-xanim-zone-name thundergun_xanims `
  --custom-xanim-stub-numframes 0 `
  --custom-xanim-stub-is-default `
  --custom-xanim-bone-count-profile cumulative_none `
  --compile `
  --load-zones zone\all\common_zm.ff `
  --install-zone-dir mods\zm_roguelike_panzer\zone\all
```

If you already have converted meshes, use `mesh-folder` mode (as above).  
If you want fully automated BIN conversion from dumped BO3 files, use the built-in Blender + blender-cod converter bridge:

```powershell
python tools\asset_port_pipeline\run_thundergun_e2e.py `
  --t7-root "Z:\Games\T7 Assets V2.5 (2)\T7 Assets V2.5\T7 Assets" `
  --source-mod mods\zm_roguelike_panzer `
  --output-root _build\asset_port_pipeline\thundergun_e2e `
  --integration-project-name thundergun_town_full `
  --auto-codbin-converter `
  --converter-blender-exe "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" `
  --converter-blender-cod-root tools\external\blender-cod-src `
  --max-submesh-vertices 2400 `
  --run-fidelity-audit `
  --strict-preflight `
  --verbose-converter `
  --compile `
  --remediate-on-fail `
  --remediate-retries 12 `
  --load-zones zone\all\common_zm.ff `
  --install-zone-dir mods\zm_roguelike_panzer\zone\all
```

If you have your own external converter CLI, use command mode (tokens: `{input_file}` `{output_file}` `{output_dir}` `{input_stem}` `{input_ext}` `{asset_kind}`):

```powershell
python tools\asset_port_pipeline\run_thundergun_e2e.py `
  --t7-root "Z:\Games\T7 Assets V2.5 (2)\T7 Assets V2.5\T7 Assets" `
  --converter-mode command `
  --model-converter-cmd "<your_converter_cli> --in \"{input_file}\" --out \"{output_file}\"" `
  --anim-converter-cmd "<your_anim_converter_cli> --in \"{input_file}\" --out \"{output_file}\"" `
  --compile
```

Outputs:
- `_build\asset_port_pipeline\thundergun_e2e\transfer\...` (staged BO3 refs + BO2 logic copy)
- `_build\asset_port_pipeline\thundergun_e2e\converted_zone_raw\...` (converted xmodel descriptors + mesh payload)
- `_build\asset_port_pipeline\thundergun_e2e\integration_project\...` (BO2 project with patched weapon defs)
- `_build\asset_port_pipeline\thundergun_e2e\integration_ready\...` (compiled bundle/install target when compile passes)
- `_build\asset_port_pipeline\thundergun_e2e_report.json`

Behavior notes:
- If compile fails and `--remediate-on-fail` is enabled, the E2E runner now reuses remediation-discovered load zones for the final compile pass.
- If `--anim-converter-cmd` outputs `.json`, those files are staged into `zone_raw/<project>/xanim` and emitted as `xanim,<name>` lines in the generated zone file.
- `--auto-codbin-converter` auto-builds converter commands around `convert_cod_bin_with_blender.py` and forces `.XMODEL_BIN -> .glb`, `.xanim_bin -> .xanim_export`.
- `--retarget-xanims` is enabled by default and rewrites converted `.xanim_export` files onto a donor skeleton/order before integration staging.
- Donor fallback now picks the richest candidate (`max parts -> max frames`) instead of first-file order, reducing low-bone donor regressions.
- `xanim_health_pre_retarget` report step now flags low-part conversions early; tune with `--xanim-low-parts-threshold`.
- `--normalize-xanims` (enabled by default) runs `normalize_xanim_exports.py` to bake missing-part transforms, clamp extreme offsets, and orthonormalize rotation bases.
- `--compile-custom-xanim-zone` runs `_build/compile_xanim_zone.py` over staged `xanim_export` files and emits a standalone FF (for runtime `--load` usage). Use `--custom-xanim-pattern` to target non-thundergun anim names.
- `--auto-patch-raygun-anims` is enabled by default and rewrites lingering `viewmodel_raygun_t6_*` refs in copied thundergun weapon defs.
- Preflight now validates unresolved raygun refs in thundergun weapon defs; use `--allow-raygun-anims` to downgrade that check to warnings.
- Custom xanim compile defaults now favor safe fallback stubs (`--custom-xanim-stub-numframes 0`, `--custom-xanim-stub-is-default`, `--custom-xanim-bone-count-profile cumulative_none`).
- When both `--compile` and `--compile-custom-xanim-zone` are enabled, the emitted xanim FF is appended to the linker preload list automatically.
- E2E now runs an explicit preflight stage before compile (model file-size heuristics, weapon model-field patch validation, xmodel LOD path checks).
- Use `--strict-preflight` to block compile when preflight/fidelity checks detect hard failures.
- Use `--verbose-converter` to stream converter/blender worker stdout/stderr directly to terminal.
- Converted xanim descriptors are bucketed into `zone_raw/<project>/xanim/viewmodel`, `.../worldmodel`, and `.../misc` for easier debugging.
- BIN discovery is now pattern-driven (`--model-bin-pattern`, `--anim-bin-pattern`) so the same pipeline can be reused for non-thundergun asset sets.

## 27) Standalone BIN converter (single asset)

Convert one dumped BO3 asset directly:

```powershell
python tools\asset_port_pipeline\convert_cod_bin_with_blender.py `
  --asset-kind xmodel `
  --input "Z:\Games\T7 Assets V2.5 (2)\T7 Assets V2.5\T7 Assets\model_export\_midgetblaster\weapons\t7\wpn_t7_zmb_thundergun_view\wpn_t7_zmb_thundergun_view_LOD0.XMODEL_BIN" `
  --output _build\asset_port_pipeline\tmp\thundergun_view.glb `
  --blender-exe "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" `
  --blender-cod-root tools\external\blender-cod-src `
  --verbose
```

```powershell
python tools\asset_port_pipeline\convert_cod_bin_with_blender.py `
  --asset-kind xanim `
  --input "Z:\Games\T7 Assets V2.5 (2)\T7 Assets V2.5\T7 Assets\xanim_export\_midgetblaster\black_ops_3\vm_thunder_gun_idle.xanim_bin" `
  --output _build\asset_port_pipeline\tmp\vm_thunder_gun_idle.xanim_export `
  --blender-exe "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" `
  --blender-cod-root tools\external\blender-cod-src `
  --verbose
```

## 28) Retarget xanim_export to donor skeleton/order

```powershell
python tools\asset_port_pipeline\retarget_xanim_exports.py `
  --input-root _build\asset_port_pipeline\thundergun_e2e\converted_anims `
  --donor _build\panzer_work\so_zsurvival_zm_transit\raw\xanim_export\vm_thunder_gun_idle.xanim_export `
  --output-root _build\asset_port_pipeline\thundergun_e2e\retargeted_anims `
  --skeleton-map tools\asset_port_pipeline\skeleton_map_bo3_to_bo2.json `
  --min-match-ratio 0.35 `
  --report _build\asset_port_pipeline\retarget_xanim_report.json
```

Use `--strict` to fail the step when any animation falls below the configured match ratio.

## 25) Fidelity audit (validation baseline)

Run a focused quality audit against `blender_convert` output metadata:

```powershell
python tools\asset_port_pipeline\fidelity_audit.py `
  --blender-report _build\asset_port_pipeline\thundergun_e2e\blender_convert_report.json `
  --submesh-limit 2400 `
  --output _build\asset_port_pipeline\fidelity_audit_report.json
```

Checks include:
- armature loss between source and output
- bone/tag naming quality ratio (BO2-style `j_` / `tag_`)
- scale drift from source to converted mesh bounds
- submesh vertex-limit overflow

## 26) BO3->BO2 material translator pass

Generate BO2 material descriptors from converted metadata material names and append them to zone source:

```powershell
python tools\asset_port_pipeline\translate_bo3_materials_to_bo2.py `
  --project-root _build\asset_port_pipeline\thundergun_e2e\integration_project\thundergun_town_full `
  --project-name thundergun_town_full `
  --blender-report _build\asset_port_pipeline\thundergun_e2e\blender_convert_report.json `
  --bundle-report _build\asset_port_pipeline\thundergun_e2e\transfer\t7_bundle_report.json `
  --append-zone-lines `
  --report _build\asset_port_pipeline\material_translation_report.json
```

Notes:
- This is a compatibility translator for BO2 linker/runtime, not a full BO3 PBR renderer port.
- When `--bundle-report` is provided, the translator stages mapped BO3 source images into `zone_raw/<project>/images` and emits matching `image,<name>` lines.
- Missing images/techsets can still be remediated by `remediate_map_project.py` during compile loop.

## 29) Normalize xanim_export (bake + sanitize)

```powershell
python tools\asset_port_pipeline\normalize_xanim_exports.py `
  --input-root _build\asset_port_pipeline\thundergun_e2e\converted_anims `
  --output-root _build\asset_port_pipeline\thundergun_e2e\normalized_anims `
  --donor _build\panzer_work\so_zsurvival_zm_transit\raw\xanim_export\vm_thunder_gun_idle.xanim_export `
  --skeleton-map tools\asset_port_pipeline\skeleton_map_bo3_to_bo2.json `
  --fill-mode hold_previous `
  --max-offset 4096 `
  --report _build\asset_port_pipeline\normalize_xanim_report.json
```

## Practical integration order

1. Run `blender_convert.py` to output real mesh payloads + xmodel descriptors.
2. Run `linker_oracle.py` / `build_compile_dataset.py` to get true compile labels.
3. Train discriminators using compile outcomes, not synthetic negatives only.
4. Add per-domain translators for weapons/anims/scripts and validate each with game-specific oracles.

## Next layer to add

- Animation retargeting score loop (pose error + compile pass objective).
- Weapon semantic translator with behavior test harness.
- Script translator for AI/state/event hooks with static + runtime validation.
