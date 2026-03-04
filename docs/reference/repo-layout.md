# Reference: Repo Layout

This repo is intentionally “inside the game root” because the toolchain expects to read/write:
- fastfiles (`zone/all`)
- Plutonium storage mods (`%LOCALAPPDATA%/Plutonium/storage/t6`)
- OAT tooling paths

Only a curated set of **source** files are tracked in Git. Everything else is runtime/build output.

## Tracked directories/files (core)
- `mods/`
  - The mod(s) used to exercise runtime behavior.
  - Source scripts and text assets only; built `.ff/.ipak` outputs are ignored.
- `_build/`
  - The “build spine” and debug tooling used for deterministic iteration:
    - patch → preflight → compile → deploy → verify
    - runtime reset/audit/health checks
    - format probes / analyzers / validators
  - Generated dumps/exports are ignored.
- `tools/asset_port_pipeline/`
  - The reusable pipeline library (more general than the `_build/` integration scripts).
- `docs/`
  - Documentation set (Diátaxis).
- `README.md`
  - Top-level project entry point.
- `.gitignore`
  - The guardrail that prevents committing proprietary/binary outputs.

## High-churn / not meant for Git
- `zone/`, `zone_dump/`, `sound/`, `video/` (game installs and dumps)
- `_build/panzer_work/` outputs, `_build/asset_port_pipeline/` output trees, and most `_build/*` experiment/output dirs
- `mods/**/zone/**` (built mod fastfiles/ipaks)
- `mods/__disabled__*` folders created by runtime lane tools

## Why we keep `_build/` scripts in-repo
These scripts are the “brains” for reproducible iteration:
- they validate fastfile integrity (avoid silent “it built but isn’t loaded” states)
- they enforce lane policies (don’t accidentally poison base runtime)
- they emit manifests that make failures debuggable
