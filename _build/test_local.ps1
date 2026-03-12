<#
.SYNOPSIS
Local dev test runner for this repo.

.DESCRIPTION
Resets runtime lanes into a safe "dev" state (single active mod), sets the
environment variables needed for local testing, then runs the two-phase build.

This is the quickest way to avoid:
- lane mismatch (building to mod folder while the engine reads base zone/all)
- accidentally shipping stubbed `c_zom_*_viewhands` overrides (all weapons invisible)
- server join contamination (use runtime_reset -Mode server before joining servers)

.EXAMPLE
powershell -ExecutionPolicy Bypass -File "_build/test_local.ps1"

.EXAMPLE
powershell -ExecutionPolicy Bypass -File "_build/test_local.ps1" -ModName "zm_roguelike_panzer" -ManageGameMods
#>

[CmdletBinding()]
param(
  [string]$ModName = "zm_roguelike_panzer",
  # Manage both the game-root mods folder and the storage mods folder by default.
  # This keeps the in-game mod list clean and prevents stale backups from being loadable.
  [bool]$ManageGameMods = $true,

  # Build architecture:
  # - mod_only: build mod.ff (+mod_load.ff) so assets load only when the mod is loaded (server-safe)
  # - map_patch: patch so_zsurvival_zm_transit.ff (dev-only; contaminates base zone/all if deployed)
  [ValidateSet("mod_only","map_patch")]
  [string]$BuildMode = "mod_only",

  # Lane toggles (defaults are the recommended local dev setup)
  [switch]$DeployToBase = $false,
  [switch]$RuntimeXanimToBase = $false,
  [switch]$StubZmViewhands = $false,

  # Viewmodel architecture:
  # - BuildViewhandsSwap: legacy runtime setviewmodel lane (kept for debugging only)
  # - CombinedViewmodel: BO3-forward lane (gunModel carries rig/visuals; handModel is no_model)
  [switch]$BuildViewhandsSwap = $false,
  [bool]$CombinedViewmodel = $false,

  # Weapondef generation strictness: fail build if any donor anim refs remain.
  [bool]$StrictNoFallbackAnims = $false,
  [ValidateSet("bo3_full","hybrid_core","hybrid_idle","stable","probe")]
  [string]$WeaponProfile = "stable",
  [string]$SetFields = "",
  [ValidateSet("thundergun","minigun")]
  [string]$Semantics = "thundergun",
  [ValidateSet("rogue","minigun","base")]
  [string]$ModelMode = "rogue",
  [string]$BaseWeapon = "",
  [string]$AmmoName = "",
  [string]$ClipName = "",

  # XAnim build mode (donor_clone is the most stable visual sanity check; bo3_frames is WIP)
  [ValidateSet("donor_clone","bo3_frames","static_pose","stub")]
  [string]$EmitMode = "donor_clone"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Section([string]$title) {
  Write-Host ""
  Write-Host ("=== " + $title + " ===")
}

$BlockingProcesses = @(
  "plutonium-bootstrapper-win32",
  "plutonium-launcher",
  "t6zm",
  "blackops2",
  "blackops2zm"
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $repoRoot
try {
  Write-Section "Reset Runtime (dev lane)"
  $runtimeReset = Join-Path $PSScriptRoot "runtime_reset.ps1"
  if (!(Test-Path $runtimeReset)) {
    throw "Missing runtime reset script: $runtimeReset"
  }

  & $runtimeReset -Mode dev -DevMod $ModName -ManageGameMods:$ManageGameMods

  Write-Section "Prepare Fresh Reports"
  $liveLog = Join-Path $PSScriptRoot "reports\\rogue_live_session.log"
  if (Test-Path $liveLog) {
    Remove-Item $liveLog -Force
    Write-Host "Removed stale live log: $liveLog"
  } else {
    Write-Host "Live log already clean: $liveLog"
  }

  Write-Section "Build + Deploy (two-phase)"
  if ($BuildMode -eq "mod_only") {
    # mod_only never needs base deploy; force it off to stay server-safe by default.
    $DeployToBase = $false
  }
  if ($DeployToBase) {
    Write-Host "WARNING: Deploying to base lane (zone/all) for local testing."
    Write-Host "This can affect server joins; run runtime_reset.ps1 -Mode server before joining public servers."

    $running = @()
    foreach ($name in $BlockingProcesses) {
      $running += @(Get-Process -Name $name -ErrorAction SilentlyContinue)
    }
    if ($running.Count -gt 0) {
      $names = ($running | Select-Object -ExpandProperty ProcessName -Unique | Sort-Object) -join ", "
      throw "Plutonium/T6 appears to be running ($names). Close it completely before base-lane deploy or you'll test cached fastfiles."
    }
  }
  $env:ROGUE_DEPLOY_TO_BASE = $(if ($DeployToBase) { "1" } else { "0" })
  $env:ROGUE_TG_RUNTIME_XANIM_TO_BASE = $(if ($RuntimeXanimToBase) { "1" } else { "0" })
  $env:ROGUE_TG_STUB_ZM_VIEWHANDS = $(if ($StubZmViewhands) { "1" } else { "0" })
  $env:ROGUE_TG_VIEWHANDS_ENABLE = $(if ($BuildViewhandsSwap) { "1" } else { "0" })
  $env:ROGUE_TG_COMBINED_VIEWMODEL = $(if ($CombinedViewmodel) { "1" } else { "0" })
  $env:ROGUE_TG_STRICT_NO_FALLBACK_ANIMS = $(if ($StrictNoFallbackAnims) { "1" } else { "0" })
  $env:ROGUE_TG_PROFILE = $WeaponProfile
  $env:ROGUE_TG_SEMANTICS = $Semantics
  $env:ROGUE_TG_MODEL_MODE = $ModelMode
  if ($BaseWeapon -ne "") {
    $env:ROGUE_TG_BASE_WEAPON = $BaseWeapon
  } elseif (Test-Path Env:ROGUE_TG_BASE_WEAPON) {
    Remove-Item Env:ROGUE_TG_BASE_WEAPON
  }
  if ($AmmoName -ne "") {
    $env:ROGUE_TG_AMMO_NAME = $AmmoName
  } elseif (Test-Path Env:ROGUE_TG_AMMO_NAME) {
    Remove-Item Env:ROGUE_TG_AMMO_NAME
  }
  if ($ClipName -ne "") {
    $env:ROGUE_TG_CLIP_NAME = $ClipName
  } elseif (Test-Path Env:ROGUE_TG_CLIP_NAME) {
    Remove-Item Env:ROGUE_TG_CLIP_NAME
  }
  if ($SetFields -ne "") {
    $env:ROGUE_TG_SET_FIELDS = $SetFields
  } elseif (Test-Path Env:ROGUE_TG_SET_FIELDS) {
    Remove-Item Env:ROGUE_TG_SET_FIELDS
  }
  if ($CombinedViewmodel) {
    $env:ROGUE_TG_HAND_MODEL = "viewmodel_usa_no_model"
    $env:ROGUE_TG_REQUIRE_VISIBLE_HANDMODEL = "0"
  }
  $env:ROGUE_TG_XANIM_EMIT_MODE = $EmitMode
  $env:ROGUE_BUILD_MODE = $BuildMode
  $env:ROGUE_MOD_NAME = $ModName

  python _build/two_phase_build.py

  Write-Section "Runtime Asset Audit"
  $runtimeAudit = Join-Path $PSScriptRoot "runtime_asset_audit.py"
  if (Test-Path $runtimeAudit) {
    python $runtimeAudit --mod-name $ModName
  } else {
    Write-Host "Skipping runtime asset audit (missing: $runtimeAudit)"
  }

  Write-Section "Next Steps (in-game)"
  Write-Host "1) Fully restart Plutonium/game before the run (xmodels and viewmodels can be cached)."
  Write-Host "2) Load mod: $ModName"
  Write-Host "3) Start a local match and verify stock weapons render (hands + gun)."
  Write-Host "4) Run the native gunModel proof first: leave rogue_tg_viewhands_enable at 0, then test Thundergun give/spawn."
  Write-Host "5) Pass condition from the fresh live log: tg_truth_result ok=1, tg_force_switch ok=1, and no tg_viewmodel events at all."
  Write-Host ""
  Write-Host "Default local lane: no runtime viewhands swap, stock T6 viewhands, safe donor anim profile."
  Write-Host "Enable -BuildViewhandsSwap only when explicitly debugging the dedicated rogue_tg_viewhands path."
  Write-Host ""
  Write-Host "Before joining public servers, run:"
  Write-Host "  powershell -ExecutionPolicy Bypass -File `_build/runtime_reset.ps1` -Mode server"
}
finally {
  Pop-Location
}
