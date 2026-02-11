$ErrorActionPreference = "Stop"

$sourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$targetDir = Join-Path $env:LOCALAPPDATA "Plutonium\storage\t6\scripts"
$targetZmDir = Join-Path $targetDir "zm"

New-Item -ItemType Directory -Path $targetDir -Force | Out-Null

$files = @(
    "mod_i_am_mod.gsc"
)

$legacyFiles = @(
    "script_i_am_script.gsc"
)

foreach ($file in $files) {
    Copy-Item -Path (Join-Path $sourceDir $file) -Destination (Join-Path $targetDir $file) -Force
}

foreach ($legacy in $legacyFiles) {
    $legacyPath = Join-Path $targetDir $legacy
    if (Test-Path $legacyPath) {
        Remove-Item -Path $legacyPath -Force
    }
}

$animePath = Join-Path $targetZmDir "zm_origins_anime.gsc"
if (Test-Path $animePath) {
    Remove-Item -Path $animePath -Force
}

Write-Host "Installed mod files to: $targetDir"
Write-Host "Files:"
foreach ($file in $files) {
    Write-Host " - $file"
}
Write-Host "These scripts auto-load on all BO2 maps in Plutonium T6."
