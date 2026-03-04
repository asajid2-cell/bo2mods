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
  [switch]$ManageGameMods,

  # Lane toggles (defaults are the recommended local dev setup)
  [switch]$DeployToBase = $true,
  [switch]$RuntimeXanimToBase = $false,
  [switch]$StubZmViewhands = $false
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Section([string]$title) {
  Write-Host ""
  Write-Host ("=== " + $title + " ===")
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $repoRoot
try {
  Write-Section "Reset Runtime (dev lane)"
  $runtimeReset = Join-Path $PSScriptRoot "runtime_reset.ps1"
  if (!(Test-Path $runtimeReset)) {
    throw "Missing runtime reset script: $runtimeReset"
  }

  & $runtimeReset -Mode dev -DevMod $ModName -ManageGameMods:$ManageGameMods

  Write-Section "Build + Deploy (two-phase)"
  $env:ROGUE_DEPLOY_TO_BASE = $(if ($DeployToBase) { "1" } else { "0" })
  $env:ROGUE_TG_RUNTIME_XANIM_TO_BASE = $(if ($RuntimeXanimToBase) { "1" } else { "0" })
  $env:ROGUE_TG_STUB_ZM_VIEWHANDS = $(if ($StubZmViewhands) { "1" } else { "0" })

  python _build/two_phase_build.py

  Write-Section "Next Steps (in-game)"
  Write-Host "1) Fully restart Plutonium (xmodels can be cached)."
  Write-Host "2) Load mod: $ModName"
  Write-Host "3) Start a local match and verify stock weapons render (hands + gun)."
  Write-Host "4) Then test Thundergun give/spawn."
  Write-Host ""
  Write-Host "Before joining public servers, run:"
  Write-Host "  powershell -ExecutionPolicy Bypass -File `_build/runtime_reset.ps1` -Mode server"
}
finally {
  Pop-Location
}

