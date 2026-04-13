param(
    [string]$GameDir = "Z:\Games\t6-clean\pluto_t6_full_game",
    [string]$SourceRuntimeDir = "Z:\Games\pluto_t6_full_game",
    [string]$PlutoniumDir = "C:\Users\Ahmed\AppData\Local\Plutonium",
    [switch]$CopyMissingStockFiles = $true,
    [switch]$UnblockPlutonium = $true
)

$ErrorActionPreference = "Stop"

function Get-RealZoneFiles {
    param([string]$Root)

    $synthetic = @(
        "code_post_gfx_zm.ipak",
        "common_zm.ipak",
        "lowmip.ipak",
        "ui_zm.ipak",
        "zm_transit.ipak",
        "zm_transit_patch.ipak",
        "patch_all.ipak",
        "patch_loc_zm.ipak",
        "dlc1_load_zm.ipak",
        "dlc2_load_zm.ipak",
        "dlc3_load_zm.ipak",
        "dlc4_load_zm.ipak"
    )

    Get-ChildItem -Path $Root -File -ErrorAction SilentlyContinue |
        Where-Object {
            $synthetic -notcontains $_.Name -and
            $_.Name -notmatch '\.(codextest|tmp_copy)$'
        }
}

function Copy-MissingFiles {
    param(
        [string]$SourceDir,
        [string]$DestinationDir,
        [scriptblock]$Enumerator
    )

    $copied = @()
    $sourceFiles = & $Enumerator $SourceDir
    $destNames = @((Get-ChildItem -Path $DestinationDir -File -ErrorAction SilentlyContinue).Name)

    foreach ($file in $sourceFiles) {
        if ($destNames -contains $file.Name) {
            continue
        }
        Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $DestinationDir $file.Name) -Force
        $copied += $file.Name
    }

    return $copied
}

if (-not (Test-Path (Join-Path $GameDir "zone\all\base.ipak"))) {
    throw "Clean runtime does not look valid: $GameDir"
}

if (-not (Test-Path (Join-Path $SourceRuntimeDir "zone\all\base.ipak"))) {
    throw "Source runtime does not look valid: $SourceRuntimeDir"
}

$zoneAllCopied = @()
$zoneEnglishCopied = @()

if ($CopyMissingStockFiles) {
    $zoneAllCopied = Copy-MissingFiles `
        -SourceDir (Join-Path $SourceRuntimeDir "zone\all") `
        -DestinationDir (Join-Path $GameDir "zone\all") `
        -Enumerator ${function:Get-RealZoneFiles}

    $zoneEnglishCopied = Copy-MissingFiles `
        -SourceDir (Join-Path $SourceRuntimeDir "zone\english") `
        -DestinationDir (Join-Path $GameDir "zone\english") `
        -Enumerator { param($p) Get-ChildItem -Path $p -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne "patch_loc_zm.ipak" } }
}

$unblockResult = "skipped"
if ($UnblockPlutonium) {
    $unblockScript = Join-Path $PSScriptRoot "unblock_plutonium_network.ps1"
    if (Test-Path $unblockScript) {
        try {
            & powershell -ExecutionPolicy Bypass -File $unblockScript
            if ($LASTEXITCODE -eq 0) {
                $unblockResult = "ok"
            } else {
                $unblockResult = "nonzero_exit_$LASTEXITCODE"
            }
        }
        catch {
            $unblockResult = "failed: $($_.Exception.Message)"
        }
    } else {
        $unblockResult = "missing_script"
    }
}

$summary = [ordered]@{
    game_dir = $GameDir
    source_runtime_dir = $SourceRuntimeDir
    plutonium_dir = $PlutoniumDir
    zone_all_copied = $zoneAllCopied
    zone_english_copied = $zoneEnglishCopied
    unblock_plutonium = $unblockResult
    launcher_default = "Z:\Games\pluto_t6_full_game\tools\launch_t6_offline.ps1"
    launcher_defaults = [ordered]@{
        game_dir = "Z:\Games\t6-clean\pluto_t6_full_game"
        name = "offline_player"
        probe_disabled = $true
        firewall_block_disabled = $true
    }
}

$summary | ConvertTo-Json -Depth 6
