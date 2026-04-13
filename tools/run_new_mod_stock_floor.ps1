param(
    [switch]$Launch,
    [string]$GameDir = "Z:\Games\t6-clean\pluto_t6_full_game",
    [string]$PlutoniumDir = "C:\Users\Ahmed\AppData\Local\Plutonium",
    [string]$Map = "zm_transit",
    [string]$UiMapName = "zm_transit",
    [string]$UiGametype = "zclassic",
    [string]$UiZmGamemodeGroup = "zsurvival",
    [string]$UiMapStartLocation = "town",
    [string]$GGametype = "zclassic",
    [ValidateRange(0, 16)]
    [int]$MonitorIndex = 2
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$repoMod = Join-Path $root "mods\new_mod"
$appMod = Join-Path $PlutoniumDir "storage\t6\mods\new_mod"
$launchScript = Join-Path $root "tools\launch_t6_offline.ps1"

if (-not (Test-Path $repoMod)) {
    throw "Missing repo mod: $repoMod"
}

if (-not (Test-Path $launchScript)) {
    throw "Missing launcher script: $launchScript"
}

if (Test-Path $appMod) {
    Remove-Item -LiteralPath $appMod -Recurse -Force
}

New-Item -ItemType Directory -Path (Split-Path -Parent $appMod) -Force | Out-Null
Copy-Item -LiteralPath $repoMod -Destination $appMod -Recurse -Force
Write-Host "Synced new_mod -> $appMod"

if (-not $Launch) {
    return
}

& powershell -ExecutionPolicy Bypass -File $launchScript `
    -Mode ZM `
    -Name offline_player `
    -GameDir $GameDir `
    -PlutoniumDir $PlutoniumDir `
    -Mod new_mod `
    -Map $Map `
    -UiMapName $UiMapName `
    -UiGametype $UiGametype `
    -UiZmGamemodeGroup $UiZmGamemodeGroup `
    -UiMapStartLocation $UiMapStartLocation `
    -GGametype $GGametype `
    -MonitorIndex $MonitorIndex
