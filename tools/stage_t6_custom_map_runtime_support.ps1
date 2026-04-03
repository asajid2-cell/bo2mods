param(
    [string]$GameDir = "Z:\Games\pluto_t6_full_game",
    [string]$PlutoniumStorageDir = "C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6",
    [string]$MapName = "zm_cosmodrome",
    [string]$CarrierMapName = "",
    [string]$ModName = "zm_cosmodrome",
    [string]$BuiltFastfile = "Z:\Games\pluto_t6_full_game\_build\custom_maps\zm_cosmodrome_project\out_release_x64\zm_cosmodrome.ff",
    [string]$DonorConfigMap = "zm_transit",
    [string]$DonorSurvivalMap = "zm_transit",
    [string]$GametypesDumpZone = "patch_zm",
    [string]$MissingGametypeFallback = "zstandard.txt"
)

$ErrorActionPreference = "Stop"

function Ensure-Dir {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Copy-RequiredFile {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path -LiteralPath $Source)) {
        throw "Missing required source file: $Source"
    }

    $destDir = Split-Path -Parent $Destination
    Ensure-Dir $destDir
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
}

function Stage-GametypeFile {
    param(
        [string]$SourceDir,
        [string]$DestinationDir,
        [string]$Name,
        [string]$FallbackName
    )

    $primary = Join-Path $SourceDir $Name
    $fallback = Join-Path $SourceDir $FallbackName
    $destination = Join-Path $DestinationDir $Name

    if (Test-Path -LiteralPath $primary) {
        Copy-RequiredFile -Source $primary -Destination $destination
        return
    }

    if (-not (Test-Path -LiteralPath $fallback)) {
        throw "Missing gametype fallback file: $fallback"
    }

    $destDir = Split-Path -Parent $destination
    Ensure-Dir $destDir
    Copy-Item -LiteralPath $fallback -Destination $destination -Force
    Write-Host "[stage_custom_map] fallback gametype $Name -> $FallbackName" -ForegroundColor Yellow
}

$modRoot = Join-Path $GameDir "mods\$ModName"
$baseZoneAllDir = Join-Path $GameDir "zone\all"
$baseZoneEnglishDir = Join-Path $GameDir "zone\english"
$zoneAllDir = Join-Path $modRoot "zone\all"
$zoneEnglishDir = Join-Path $modRoot "zone\english"
$configStringsDir = Join-Path $modRoot "mp\configStrings"
$gametypesDir = Join-Path $modRoot "maps\mp\gametypes_zm"
$storageModRoot = Join-Path $PlutoniumStorageDir "mods\$ModName"
$storageZoneAllDir = Join-Path $storageModRoot "zone\all"
$storageZoneEnglishDir = Join-Path $storageModRoot "zone\english"
$storageConfigStringsDir = Join-Path $storageModRoot "mp\configStrings"
$storageGametypesDir = Join-Path $storageModRoot "maps\mp\gametypes_zm"
$animtreesDir = Join-Path $modRoot "animtrees"
$rawAnimtreesDir = Join-Path $GameDir "raw\animtrees"
$modRawAnimtreesDir = Join-Path $modRoot "raw\animtrees"
$storageAnimtreesDir = Join-Path $storageModRoot "animtrees"
$storageModRawAnimtreesDir = Join-Path $storageModRoot "raw\animtrees"
$storageRawConfigStringsDir = Join-Path $PlutoniumStorageDir "raw\mp\configStrings"
$storageRawGametypesDir = Join-Path $PlutoniumStorageDir "raw\maps\mp\gametypes_zm"
$storageRawAnimtreesDir = Join-Path $PlutoniumStorageDir "raw\animtrees"

$donorConfig = Join-Path $PlutoniumStorageDir "dump\$DonorConfigMap\mp\configstrings\configstrings_${DonorConfigMap}.csv"
$donorSurvivalFastfile = Join-Path $GameDir "zone\all\so_zsurvival_${DonorSurvivalMap}.ff"
$donorSurvivalIpak = Join-Path $GameDir "zone\all\so_zsurvival_${DonorSurvivalMap}.ipak"
$donorSurvivalEnglishFastfile = Join-Path $GameDir "zone\english\en_so_zsurvival_${DonorSurvivalMap}.ff"
$customConfigCandidates = @(
    (Join-Path $GameDir "_build\custom_maps\${MapName}_project\zone_raw\$MapName\mp\configStrings\configstrings_${MapName}.csv"),
    (Join-Path $GameDir "_build\custom_maps\${MapName}_source\mp\configStrings\configstrings_${MapName}.csv"),
    (Join-Path $GameDir "_build\custom_maps\${MapName}_source\mp\configstrings\configstrings_${MapName}.csv")
)
$donorAnimtreeDir = Join-Path $PlutoniumStorageDir "dump\common_zm\animtrees"
$targetConfig = Join-Path $configStringsDir "configStrings_${MapName}.csv"
$gamedumpDir = Join-Path $PlutoniumStorageDir "dump\$GametypesDumpZone\maps\mp\gametypes_zm"
$animtreeFiles = @(
    "fxanim_props.atr"
    "mp_vehicles.atr"
    "mp_missile_drone.atr"
)

$gametypeFiles = @(
    "_gametypes.txt"
    "zclassic.txt"
    "zstandard.txt"
    "zcontainment.txt"
    "zrace.txt"
    "zdeadpool.txt"
    "zmeat.txt"
    "znml.txt"
    "zturned.txt"
    "zpitted.txt"
    "zcleansed.txt"
    "zgrief.txt"
    "zrichtofen.txt"
    "zmaxis.txt"
)

Write-Host "[stage_custom_map] map      : $MapName" -ForegroundColor Cyan
Write-Host "[stage_custom_map] carrier  : $CarrierMapName"
Write-Host "[stage_custom_map] mod      : mods/$ModName"
Write-Host "[stage_custom_map] fastfile : $BuiltFastfile"
Write-Host "[stage_custom_map] donor cfg: $donorConfig"
Write-Host "[stage_custom_map] donor so : $donorSurvivalFastfile"
Write-Host "[stage_custom_map] donor atr: $donorAnimtreeDir"
Write-Host "[stage_custom_map] donor gt : $gamedumpDir"

$configSource = $null
foreach ($candidate in $customConfigCandidates) {
    if (Test-Path -LiteralPath $candidate) {
        $configSource = $candidate
        break
    }
}

if (-not $configSource) {
    $configSource = $donorConfig
}

Write-Host "[stage_custom_map] cfg src  : $configSource"

Copy-RequiredFile -Source $BuiltFastfile -Destination (Join-Path $baseZoneAllDir "$MapName.ff")
Copy-RequiredFile -Source $BuiltFastfile -Destination (Join-Path $zoneAllDir "$MapName.ff")
Copy-RequiredFile -Source $BuiltFastfile -Destination (Join-Path $storageZoneAllDir "$MapName.ff")

if ($CarrierMapName -and $CarrierMapName -ne $MapName) {
    Copy-RequiredFile -Source $BuiltFastfile -Destination (Join-Path $zoneAllDir "$CarrierMapName.ff")
    Copy-RequiredFile -Source $BuiltFastfile -Destination (Join-Path $storageZoneAllDir "$CarrierMapName.ff")
}
Copy-RequiredFile -Source $configSource -Destination $targetConfig
Copy-RequiredFile -Source $configSource -Destination (Join-Path $storageConfigStringsDir "configStrings_${MapName}.csv")
Copy-RequiredFile -Source $configSource -Destination (Join-Path $storageRawConfigStringsDir "configStrings_${MapName}.csv")

if (Test-Path -LiteralPath $donorSurvivalFastfile) {
    Copy-RequiredFile -Source $donorSurvivalFastfile -Destination (Join-Path $baseZoneAllDir "so_zsurvival_${MapName}.ff")
    Copy-RequiredFile -Source $donorSurvivalFastfile -Destination (Join-Path $zoneAllDir "so_zsurvival_${MapName}.ff")
    Copy-RequiredFile -Source $donorSurvivalFastfile -Destination (Join-Path $storageZoneAllDir "so_zsurvival_${MapName}.ff")
}

if (Test-Path -LiteralPath $donorSurvivalIpak) {
    Copy-RequiredFile -Source $donorSurvivalIpak -Destination (Join-Path $baseZoneAllDir "so_zsurvival_${MapName}.ipak")
    Copy-RequiredFile -Source $donorSurvivalIpak -Destination (Join-Path $zoneAllDir "so_zsurvival_${MapName}.ipak")
    Copy-RequiredFile -Source $donorSurvivalIpak -Destination (Join-Path $storageZoneAllDir "so_zsurvival_${MapName}.ipak")
}

if (Test-Path -LiteralPath $donorSurvivalEnglishFastfile) {
    Copy-RequiredFile -Source $donorSurvivalEnglishFastfile -Destination (Join-Path $baseZoneEnglishDir "en_so_zsurvival_${MapName}.ff")
    Copy-RequiredFile -Source $donorSurvivalEnglishFastfile -Destination (Join-Path $zoneEnglishDir "en_so_zsurvival_${MapName}.ff")
    Copy-RequiredFile -Source $donorSurvivalEnglishFastfile -Destination (Join-Path $storageZoneEnglishDir "en_so_zsurvival_${MapName}.ff")
}

foreach ($animtreeName in $animtreeFiles) {
    $animtreeSource = Join-Path $donorAnimtreeDir $animtreeName
    Copy-RequiredFile -Source $animtreeSource -Destination (Join-Path $animtreesDir $animtreeName)
    Copy-RequiredFile -Source $animtreeSource -Destination (Join-Path $rawAnimtreesDir $animtreeName)
    Copy-RequiredFile -Source $animtreeSource -Destination (Join-Path $modRawAnimtreesDir $animtreeName)
    Copy-RequiredFile -Source $animtreeSource -Destination (Join-Path $storageAnimtreesDir $animtreeName)
    Copy-RequiredFile -Source $animtreeSource -Destination (Join-Path $storageModRawAnimtreesDir $animtreeName)
    Copy-RequiredFile -Source $animtreeSource -Destination (Join-Path $storageRawAnimtreesDir $animtreeName)
}

foreach ($name in $gametypeFiles) {
    Stage-GametypeFile -SourceDir $gamedumpDir -DestinationDir $gametypesDir -Name $name -FallbackName $MissingGametypeFallback
    Stage-GametypeFile -SourceDir $gamedumpDir -DestinationDir $storageGametypesDir -Name $name -FallbackName $MissingGametypeFallback
    Stage-GametypeFile -SourceDir $gamedumpDir -DestinationDir $storageRawGametypesDir -Name $name -FallbackName $MissingGametypeFallback
}

Write-Host "[stage_custom_map] staged mod lane at $modRoot" -ForegroundColor Green
