param(
    [ValidateSet("audit", "clean", "dev")]
    [string]$Mode = "audit",
    [string]$DevMod = "zm_roguelike_panzer"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$GameRoot = (Resolve-Path ".").Path
$StorageRoot = Join-Path $env:LOCALAPPDATA "Plutonium\storage\t6"
$GameModsRoot = Join-Path $GameRoot "mods"
$StorageModsRoot = Join-Path $StorageRoot "mods"
$ZoneAllRoot = Join-Path $GameRoot "zone\all"
$StorageScriptsRoot = Join-Path $StorageRoot "scripts"
$StorageImagesRoot = Join-Path $StorageRoot "images"
$StorageRawRoot = Join-Path $StorageRoot "raw"

$BaselineTransitHash = "1076303B8D35F33B7E680B477F40362C37D30DC071FD71322081BADA9C62D01E"

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunRoot = Join-Path $GameRoot ("_build\runtime_reset\" + $Stamp)
$null = New-Item -ItemType Directory -Path $RunRoot -Force
$LogFile = Join-Path $RunRoot "actions.log"

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    $line | Tee-Object -FilePath $LogFile -Append
}

function Disable-AllMods {
    param([string]$Root)
    if (-not (Test-Path $Root)) { return @() }
    $changed = @()
    Get-ChildItem -Path $Root -Directory | ForEach-Object {
        $item = $_
        if ($item.Name.StartsWith("__disabled__")) { return }
        $dst = Join-Path $Root ("__disabled__" + $item.Name)
        if (Test-Path $dst) {
            $dst = Join-Path $Root ("__disabled__" + $item.Name + "_" + $Stamp)
        }
        try {
            Move-Item -Path $item.FullName -Destination $dst -ErrorAction Stop
            $changed += [PSCustomObject]@{ action = "disable_mod"; from = $item.FullName; to = $dst }
        }
        catch {
            $err = $_
            $null = Write-Log ("WARN: failed to disable mod: " + $item.FullName + " -> " + $dst + " :: " + $err.Exception.Message)
            $changed += [PSCustomObject]@{ action = "disable_mod_failed"; from = $item.FullName; to = $dst; error = $err.Exception.Message }
        }
    }
    return $changed
}

function Enable-OnlyMod {
    param(
        [string]$Root,
        [string]$ModName
    )
    if (-not (Test-Path $Root)) { return @() }
    $changed = @()

    # First disable any currently-enabled mod except target.
    Get-ChildItem -Path $Root -Directory | ForEach-Object {
        $item = $_
        if ($item.Name.StartsWith("__disabled__")) { return }
        if ($item.Name -eq $ModName) { return }
        $dst = Join-Path $Root ("__disabled__" + $item.Name)
        if (Test-Path $dst) {
            $dst = Join-Path $Root ("__disabled__" + $item.Name + "_" + $Stamp)
        }
        try {
            Move-Item -Path $item.FullName -Destination $dst -ErrorAction Stop
            $changed += [PSCustomObject]@{ action = "disable_mod"; from = $item.FullName; to = $dst }
        }
        catch {
            $err = $_
            $null = Write-Log ("WARN: failed to disable mod: " + $item.FullName + " -> " + $dst + " :: " + $err.Exception.Message)
            $changed += [PSCustomObject]@{ action = "disable_mod_failed"; from = $item.FullName; to = $dst; error = $err.Exception.Message }
        }
    }

    # Then enable target if it exists in disabled form.
    $disabledTarget = Join-Path $Root ("__disabled__" + $ModName)
    $enabledTarget = Join-Path $Root $ModName
    if ((Test-Path $disabledTarget) -and -not (Test-Path $enabledTarget)) {
        try {
            Move-Item -Path $disabledTarget -Destination $enabledTarget -ErrorAction Stop
            $changed += [PSCustomObject]@{ action = "enable_mod"; from = $disabledTarget; to = $enabledTarget }
        }
        catch {
            $err = $_
            $null = Write-Log ("WARN: failed to enable mod: " + $disabledTarget + " -> " + $enabledTarget + " :: " + $err.Exception.Message)
            $changed += [PSCustomObject]@{ action = "enable_mod_failed"; from = $disabledTarget; to = $enabledTarget; error = $err.Exception.Message }
        }
    }

    return $changed
}

function Restore-TransitBaselineFF {
    param([string]$Root)
    $result = @()
    $target = Join-Path $Root "so_zsurvival_zm_transit.ff"
    if (-not (Test-Path $target)) { return $result }

    $baseline = Join-Path $GameRoot "_build\ff_backup\20260213-125735\so_zsurvival_zm_transit.ff"
    if (-not (Test-Path $baseline)) {
        $null = Write-Log "baseline ff missing: $baseline"
        return $result
    }

    $targetHash = (Get-FileHash $target -Algorithm SHA256).Hash
    $baselineHash = (Get-FileHash $baseline -Algorithm SHA256).Hash
    if ($targetHash -eq $baselineHash) {
        $null = Write-Log "so_zsurvival_zm_transit.ff already baseline ($targetHash)"
        return $result
    }

    $backupDir = Join-Path $RunRoot "zone_all_backup"
    $null = New-Item -ItemType Directory -Path $backupDir -Force
    $backupTarget = Join-Path $backupDir "so_zsurvival_zm_transit.ff.pre_reset"
    Copy-Item -Path $target -Destination $backupTarget -Force
    Copy-Item -Path $baseline -Destination $target -Force

    $result += [PSCustomObject]@{
        action = "restore_ff"
        target = $target
        from_hash = $targetHash
        to_hash = $baselineHash
        backup = $backupTarget
    }
    return $result
}

function Move-IfExists {
    param(
        [string]$Path,
        [string]$DestDir,
        [string]$ActionName
    )
    $result = @()
    if (-not (Test-Path $Path)) { return $result }
    $null = New-Item -ItemType Directory -Path $DestDir -Force
    $dst = Join-Path $DestDir (Split-Path $Path -Leaf)
    if (Test-Path $dst) {
        $dst = Join-Path $DestDir ((Split-Path $Path -Leaf) + "." + $Stamp)
    }
    try {
        Move-Item -Path $Path -Destination $dst -ErrorAction Stop
        $result += [PSCustomObject]@{ action = $ActionName; from = $Path; to = $dst }
    }
    catch {
        $err = $_
        $null = Write-Log ("WARN: failed to move: " + $Path + " -> " + $dst + " :: " + $err.Exception.Message)
        $result += [PSCustomObject]@{ action = ($ActionName + "_failed"); from = $Path; to = $dst; error = $err.Exception.Message }
    }
    return $result
}

function Move-MatchingFiles {
    param(
        [string]$Root,
        [string[]]$Patterns,
        [string]$DestDir,
        [string]$ActionName
    )
    $result = @()
    if (-not (Test-Path $Root)) { return $result }
    $null = New-Item -ItemType Directory -Path $DestDir -Force
    foreach ($p in $Patterns) {
        Get-ChildItem -Path $Root -File -Filter $p -ErrorAction SilentlyContinue | ForEach-Object {
            $item = $_
            $dst = Join-Path $DestDir $item.Name
            if (Test-Path $dst) {
                $dst = Join-Path $DestDir ($item.Name + "." + $Stamp)
            }
            try {
                Move-Item -Path $item.FullName -Destination $dst -ErrorAction Stop
                $result += [PSCustomObject]@{ action = $ActionName; from = $item.FullName; to = $dst }
            }
            catch {
                $err = $_
                $null = Write-Log ("WARN: failed to move: " + $item.FullName + " -> " + $dst + " :: " + $err.Exception.Message)
                $result += [PSCustomObject]@{ action = ($ActionName + "_failed"); from = $item.FullName; to = $dst; error = $err.Exception.Message }
            }
        }
    }
    return $result
}

function Find-MatchingFiles {
    param(
        [string]$Root,
        [string[]]$Patterns
    )
    $result = @()
    if (-not (Test-Path $Root)) { return $result }
    foreach ($p in $Patterns) {
        Get-ChildItem -Path $Root -File -Filter $p -ErrorAction SilentlyContinue | ForEach-Object {
            $result += $_.FullName
        }
    }
    return $result
}

function Find-SuspiciousRawArtifacts {
    param([string]$Root)
    $result = @()
    if (-not (Test-Path $Root)) { return $result }

    Get-ChildItem -Path $Root -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
        $rel = $_.FullName.Substring($Root.Length).TrimStart('\', '/')
        $relNorm = $rel -replace '/', '\'
        $isUi = $relNorm.StartsWith("ui\") -or $relNorm.StartsWith("ui_mp\")
        $isRankedFix =
            ($relNorm -ieq "scripts\mp\ranked.gsc") -or
            ($relNorm -ieq "scripts\zm\ranked.gsc") -or
            ($relNorm.StartsWith("scripts\scripts.disabled\"))
        if ($isUi -or $isRankedFix) { return }

        if ($relNorm -match "(?i)(rogue|panzer|thunder|thundergun|mechz|zm_tomb|mod_i_am_mod)") {
            $result += $_.FullName
        }
    }
    return $result
}

function Move-ReservedRuntimeFFs {
    param(
        [string]$ModsRoot,
        [string]$DestRoot,
        [string]$ActionName
    )
    $result = @()
    if (-not (Test-Path $ModsRoot)) { return $result }
    Get-ChildItem -Path $ModsRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $zoneAll = Join-Path $_.FullName "zone\all"
        if (Test-Path $zoneAll) {
            $modDest = Join-Path $DestRoot $_.Name
            $result += Move-MatchingFiles -Root $zoneAll -Patterns @("mod.ff", "mod_load.ff", "mod_patch.ff") -DestDir $modDest -ActionName $ActionName
        }
    }
    return $result
}

function Find-ReservedRuntimeFFs {
    param([string]$ModsRoot)
    $result = @()
    if (-not (Test-Path $ModsRoot)) { return $result }
    Get-ChildItem -Path $ModsRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $zoneAll = Join-Path $_.FullName "zone\all"
        if (Test-Path $zoneAll) {
            $result += Find-MatchingFiles -Root $zoneAll -Patterns @("mod.ff", "mod_load.ff", "mod_patch.ff")
        }
    }
    return $result
}

Write-Log "mode=$Mode dev_mod=$DevMod"
Write-Log "game_root=$GameRoot"
Write-Log "storage_root=$StorageRoot"

$changes = @()

if ($Mode -eq "clean") {
    Write-Log "disabling all mods (game + storage)"
    $changes += Disable-AllMods -Root $GameModsRoot
    $changes += Disable-AllMods -Root $StorageModsRoot

    Write-Log "restoring base transit survival ff to known baseline"
    $changes += Restore-TransitBaselineFF -Root $ZoneAllRoot

    Write-Log "quarantining reserved runtime ff names from base zone/all"
    $changes += Move-MatchingFiles -Root $ZoneAllRoot -Patterns @("mod.ff", "mod_load.ff", "mod_patch.ff", "thundergun_xanims.ff") -DestDir (Join-Path $RunRoot "zone_all_quarantine") -ActionName "quarantine_zone_file"

    Write-Log "quarantining storage script autoload remnants"
    $changes += Move-MatchingFiles -Root $StorageScriptsRoot -Patterns @("mod_i_am_mod.autoload*") -DestDir (Join-Path $RunRoot "storage_scripts_quarantine") -ActionName "quarantine_storage_script"

    Write-Log "quarantining global rogue/tg images from storage/images"
    $changes += Move-MatchingFiles -Root $StorageImagesRoot -Patterns @("rogue_tg_*", "tg_*") -DestDir (Join-Path $RunRoot "storage_images_quarantine") -ActionName "quarantine_storage_image"

    Write-Log "quarantining suspicious rogue artifacts from storage/raw"
    $suspiciousRawClean = @(Find-SuspiciousRawArtifacts -Root $StorageRawRoot)
    foreach ($rawPath in $suspiciousRawClean) {
        $changes += Move-IfExists -Path $rawPath -DestDir (Join-Path $RunRoot "storage_raw_quarantine") -ActionName "quarantine_storage_raw"
    }

    Write-Log "quarantining reserved runtime ff names from game/storage mods zone/all"
    $changes += Move-ReservedRuntimeFFs -ModsRoot $GameModsRoot -DestRoot (Join-Path $RunRoot "game_mod_zone_quarantine") -ActionName "quarantine_reserved_runtime_ff"
    $changes += Move-ReservedRuntimeFFs -ModsRoot $StorageModsRoot -DestRoot (Join-Path $RunRoot "storage_mod_zone_quarantine") -ActionName "quarantine_reserved_runtime_ff"
}
elseif ($Mode -eq "dev") {
    Write-Log "enabling dev mod only: $DevMod"
    $changes += Enable-OnlyMod -Root $GameModsRoot -ModName $DevMod
    $changes += Enable-OnlyMod -Root $StorageModsRoot -ModName $DevMod
}
else {
    Write-Log "audit mode: no mutations performed"
}

$allGameMods = if (Test-Path $GameModsRoot) { @(Get-ChildItem -Path $GameModsRoot -Directory | Select-Object -ExpandProperty Name) } else { @() }
$allStorageMods = if (Test-Path $StorageModsRoot) { @(Get-ChildItem -Path $StorageModsRoot -Directory | Select-Object -ExpandProperty Name) } else { @() }
$activeGameMods = @($allGameMods | Where-Object { -not $_.StartsWith("__disabled__") })
$activeStorageMods = @($allStorageMods | Where-Object { -not $_.StartsWith("__disabled__") })
$zonePath = Join-Path $ZoneAllRoot "so_zsurvival_zm_transit.ff"
$zoneHash = if (Test-Path $zonePath) { (Get-FileHash $zonePath -Algorithm SHA256).Hash } else { "" }
$zoneIsBaseline = if ($zoneHash) { ($zoneHash -eq $BaselineTransitHash) } else { $false }
$storageAutoload = @(Find-MatchingFiles -Root $StorageScriptsRoot -Patterns @("mod_i_am_mod.autoload*"))
$suspiciousRaw = @(Find-SuspiciousRawArtifacts -Root $StorageRawRoot)
$reservedRuntimeZoneAll = @(Find-MatchingFiles -Root $ZoneAllRoot -Patterns @("mod.ff", "mod_load.ff", "mod_patch.ff", "thundergun_xanims.ff"))
$reservedRuntimeStorage = @(Find-ReservedRuntimeFFs -ModsRoot $StorageModsRoot)
$reservedRuntimeGame = @(Find-ReservedRuntimeFFs -ModsRoot $GameModsRoot)

$report = [PSCustomObject]@{
    mode = $Mode
    dev_mod = $DevMod
    timestamp = $Stamp
    run_root = $RunRoot
    game_mods = $allGameMods
    storage_mods = $allStorageMods
    active_game_mods = $activeGameMods
    active_storage_mods = $activeStorageMods
    zone_so_zsurvival_hash = $zoneHash
    zone_so_zsurvival_expected_hash = $BaselineTransitHash
    zone_so_zsurvival_is_baseline = $zoneIsBaseline
    storage_autoload_files = $storageAutoload
    suspicious_storage_raw_artifacts = $suspiciousRaw
    reserved_runtime_ff_zone_all = $reservedRuntimeZoneAll
    reserved_runtime_ff_storage = $reservedRuntimeStorage
    reserved_runtime_ff_game = $reservedRuntimeGame
    changes = $changes
}

$reportPath = Join-Path $RunRoot "report.json"
$report | ConvertTo-Json -Depth 6 | Set-Content -Path $reportPath -Encoding ASCII
Write-Log ("report=" + $reportPath)
Write-Log ("changes=" + $changes.Count)

Write-Output ""
Write-Output "Runtime reset complete."
Write-Output ("Mode: " + $Mode)
Write-Output ("Run dir: " + $RunRoot)
Write-Output ("Changes: " + $changes.Count)
