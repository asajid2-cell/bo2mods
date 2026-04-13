param(
    [switch]$Launch,
    [switch]$InjectProbe,
    [switch]$ModOnly,
    [switch]$UseStockSurvivalZone,
    [switch]$SyncBaseZoneAll,
    [switch]$SyncGeneratedClientOverrides,
    [string]$Map = "",
    [string]$UiGametype = "",
    [string]$UiZmGamemodeGroup = "",
    [string]$UiMapStartLocation = "",
    [string]$UiMapName = "",
    [string]$GGametype = "",
    [string]$ExecCfg = "",
    [string[]]$ExtraCommands = @(),
    [ValidateSet("safe", "bootstrap_guard_only", "render_opacity_focus", "viewmodel_render_focus", "xanim_focus", "xanim_consumer_focus", "xanim_asset_lookup_focus", "producer_compact_override_focus", "class_family_materialization_writepath")]
    [string]$ProbeMode = "safe",
    [ValidateSet("startup", "connect", "grant", "first_raise_begin", "idle_begin", "fire_begin")]
    [string]$ProbeAttachGate = "startup",
    [int]$ProbeAttachDelayMs = 12000,
    [int]$ProbeAttachTimeoutSec = 25,
    [switch]$EnableProbeGuards,
    [string]$ProbeGuardLabel = "material",
    [string]$ProbeGuardNeedle = "gfx_light_phosphorous_em_i1024",
    [int]$ProbeGuardDelayMs = 15000,
    [int]$ProbeGuardMax = 1,
    [string]$Name = "offline_player",
    [string]$Mod = "bo3_rev",
    [string]$BuildRootName = "",
    [string]$GameDir = "Z:\Games\t6-clean\pluto_t6_full_game",
    [string]$PlutoniumDir = "C:\Users\Ahmed\AppData\Local\Plutonium",
    [string]$RepoDir = "",
    [ValidateRange(0, 16)]
    [int]$MonitorIndex = 2,
    [switch]$HiddenWorker,
    [switch]$SkipAssetValidation,
    [string]$ResolvedSourceReportPath = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoDir)) {
    $RepoDir = Split-Path -Parent $PSScriptRoot
}

$RepoDir = [System.IO.Path]::GetFullPath($RepoDir)
$GameDir = [System.IO.Path]::GetFullPath($GameDir)
$PlutoniumDir = [System.IO.Path]::GetFullPath($PlutoniumDir)

function Start-HiddenSelfLaunch {
    $argList = @(
        "-ExecutionPolicy", "Bypass",
        "-File", $PSCommandPath,
        "-HiddenWorker"
    )

    foreach ($entry in $PSBoundParameters.GetEnumerator()) {
        $name = [string]$entry.Key
        if ($name -eq "HiddenWorker") {
            continue
        }

        $value = $entry.Value
        if ($value -is [System.Management.Automation.SwitchParameter]) {
            if ($value.IsPresent) {
                $argList += "-$name"
            }
            continue
        }

        if ($value -is [System.Array] -and -not ($value -is [string])) {
            foreach ($item in $value) {
                $argList += "-$name"
                $argList += [string]$item
            }
            continue
        }

        $argList += "-$name"
        $argList += [string]$value
    }

    Start-Process -FilePath "powershell" -ArgumentList $argList -WindowStyle Hidden | Out-Null
}

if ($Launch -and $MonitorIndex -gt 0 -and -not $HiddenWorker) {
    Start-HiddenSelfLaunch
    Write-Host "Launching hidden restart helper for monitor $MonitorIndex." -ForegroundColor Green
    return
}

$modName = ""
if ($Mod) {
    $modName = $Mod.Trim()
}

if ([string]::IsNullOrWhiteSpace($BuildRootName)) {
    if ($modName -eq "bo3_rev" -or [string]::IsNullOrWhiteSpace($modName)) {
        $BuildRootName = "bo3_rev_idg_probe"
    } else {
        $BuildRootName = "{0}_idg_probe" -f $modName
    }
}

function Copy-ItemSafe {
    param(
        [string]$Source,
        [string]$Destination
    )
    try {
        $resolvedSource = (Resolve-Path $Source -ErrorAction Stop).Path
        $resolvedDestination = [System.IO.Path]::GetFullPath($Destination)
        if ([string]::Equals($resolvedSource, $resolvedDestination, [System.StringComparison]::OrdinalIgnoreCase)) {
            return
        }
    }
    catch {
    }
    $dstDir = Split-Path -Parent $Destination
    if (-not (Test-Path $dstDir)) {
        New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
    }

    $leaf = Split-Path -Leaf $Destination
    $sanitizeText = $leaf.EndsWith(".gsc", [System.StringComparison]::OrdinalIgnoreCase) -or
        $leaf.EndsWith(".csc", [System.StringComparison]::OrdinalIgnoreCase) -or
        $leaf.EndsWith(".gsc.in", [System.StringComparison]::OrdinalIgnoreCase) -or
        $leaf.EndsWith(".csc.in", [System.StringComparison]::OrdinalIgnoreCase)

    if ($sanitizeText) {
        $bytes = [System.IO.File]::ReadAllBytes($Source)
        if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
            $trimmed = New-Object byte[] ($bytes.Length - 3)
            [Array]::Copy($bytes, 3, $trimmed, 0, $trimmed.Length)
            [System.IO.File]::WriteAllBytes($Destination, $trimmed)
        }
        else {
            [System.IO.File]::WriteAllBytes($Destination, $bytes)
        }
    }
    else {
        Copy-Item -Path $Source -Destination $Destination -Force
    }
    Write-Host "Synced: $Destination"
}

function Copy-DirectoryFilesSafe {
    param(
        [string]$SourceDir,
        [string]$DestinationDir,
        [string]$Filter = "*"
    )
    if (-not (Test-Path $SourceDir)) {
        return
    }
    New-Item -ItemType Directory -Path $DestinationDir -Force | Out-Null
    Get-ChildItem -Path $SourceDir -File -Filter $Filter | ForEach-Object {
        Copy-ItemSafe -Source $_.FullName -Destination (Join-Path $DestinationDir $_.Name)
    }
}

function Move-PathToLocalQuarantine {
    param(
        [string]$SourcePath,
        [string]$QuarantineRoot,
        [string]$Prefix
    )

    if ([string]::IsNullOrWhiteSpace($SourcePath) -or -not (Test-Path $SourcePath)) {
        return
    }

    $safePrefix = if ([string]::IsNullOrWhiteSpace($Prefix)) { "quarantine" } else { $Prefix }
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $destRoot = Join-Path $QuarantineRoot $stamp
    $destDir = Join-Path $destRoot $safePrefix
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    $destPath = Join-Path $destDir (Split-Path -Path $SourcePath -Leaf)
    if (Test-Path $destPath) {
        Remove-Item -LiteralPath $destPath -Recurse -Force
    }
    Move-Item -LiteralPath $SourcePath -Destination $destPath
    Write-Host "Quarantined runtime override -> $destPath"
}

function Get-SharedText {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return ""
    }

    $stream = $null
    try {
        $stream = New-Object System.IO.FileStream($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
        $bytes = New-Object byte[] $stream.Length
        [void]$stream.Read($bytes, 0, $bytes.Length)
        return [System.Text.Encoding]::UTF8.GetString($bytes)
    }
    finally {
        if ($stream) {
            $stream.Dispose()
        }
    }
}

function Get-LogVariantPaths {
    param([string]$Path)

    $paths = New-Object System.Collections.Generic.List[string]
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return @()
    }

    if (Test-Path $Path) {
        $paths.Add((Get-Item $Path).FullName)
    }

    $parent = Split-Path -Parent $Path
    $leaf = Split-Path -Leaf $Path
    if (-not [string]::IsNullOrWhiteSpace($parent) -and (Test-Path $parent)) {
        $escapedLeaf = [regex]::Escape($leaf)
        $variants = Get-ChildItem -Path $parent -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match ("^{0}\.\d+$" -f $escapedLeaf) } |
            Sort-Object LastWriteTime, Name -Descending
        foreach ($variant in @($variants)) {
            if (-not $paths.Contains($variant.FullName)) {
                $paths.Add($variant.FullName)
            }
        }
    }

    return @($paths)
}

function Get-LatestLogVariantPath {
    param([string]$Path)

    $variants = @(Get-LogVariantPaths -Path $Path)
    if ($variants.Count -eq 0) {
        return ""
    }

    $latest = $variants |
        ForEach-Object { Get-Item $_ } |
        Sort-Object LastWriteTime, Name -Descending |
        Select-Object -First 1
    if ($null -eq $latest) {
        return ""
    }

    return $latest.FullName
}

function Get-LogSnapshot {
    param([string]$Path)

    $resolvedPath = Get-LatestLogVariantPath -Path $Path
    $exists = -not [string]::IsNullOrWhiteSpace($resolvedPath)
    $length = 0
    if ($exists) {
        $length = (Get-Item $resolvedPath).Length
    }

    return @{
        Path = $Path
        ResolvedPath = $resolvedPath
        Exists = $exists
        Length = $length
    }
}

function Get-LogDeltaText {
    param([hashtable]$Snapshot)

    $resolvedPath = Get-LatestLogVariantPath -Path $Snapshot.Path
    if ([string]::IsNullOrWhiteSpace($resolvedPath) -or -not (Test-Path $resolvedPath)) {
        return ""
    }

    $stream = $null
    try {
        $stream = New-Object System.IO.FileStream($resolvedPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
        $startOffset = 0
        if ($Snapshot.Exists -and `
            -not [string]::IsNullOrWhiteSpace($Snapshot.ResolvedPath) -and `
            [string]::Equals($Snapshot.ResolvedPath, $resolvedPath, [System.StringComparison]::OrdinalIgnoreCase)) {
            $startOffset = [Math]::Min([int64]$Snapshot.Length, $stream.Length)
        }

        $remaining = $stream.Length - $startOffset
        if ($remaining -le 0) {
            return ""
        }

        [void]$stream.Seek($startOffset, [System.IO.SeekOrigin]::Begin)
        $bytes = New-Object byte[] $remaining
        [void]$stream.Read($bytes, 0, $bytes.Length)
        return [System.Text.Encoding]::UTF8.GetString($bytes)
    }
    finally {
        if ($stream) {
            $stream.Dispose()
        }
    }
}

function Wait-ForProbeAttachReady {
    param(
        [hashtable[]]$ConsoleLogSnapshots,
        [string]$AttachGate,
        [int]$TimeoutSec,
        [int]$FallbackDelayMs
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $fallbackAt = (Get-Date).AddMilliseconds($FallbackDelayMs)
    $markers = switch ($AttachGate) {
        "first_raise_begin" {
            @("anim_probe:first_raise_begin")
        }
        "idle_begin" {
            @("anim_probe:idle_begin")
        }
        "fire_begin" {
            @("anim_probe:fire_begin")
        }
        "connect" {
            @("[bo3_rev][connect]")
        }
        "grant" {
            @("[bo3_rev][grant]")
        }
        default {
            @(
                "Loading fastfile mod_patch",
                "execing ffprobe_autorun.cfg",
                "Loading fastfile ui_zm",
                "Loading fastfile common_zm"
            )
        }
    }
    $gateLabel = switch ($AttachGate) {
        "first_raise_begin" { "first_raise_begin markers" }
        "idle_begin" { "idle_begin markers" }
        "fire_begin" { "fire_begin markers" }
        "connect" { "connect markers" }
        "grant" { "grant markers" }
        default { "startup markers" }
    }

    while ((Get-Date) -lt $deadline) {
        foreach ($snapshot in @($ConsoleLogSnapshots)) {
            if ($null -eq $snapshot -or [string]::IsNullOrWhiteSpace([string]$snapshot.Path)) {
                continue
            }
            $text = Get-LogDeltaText -Snapshot $snapshot
            foreach ($marker in $markers) {
                if ($text -like "*$marker*") {
                    Write-Host "Probe attach gate reached: $marker source=$($snapshot.Path)"
                    return
                }
            }
        }

        if ((Get-Date) -ge $fallbackAt) {
            Write-Warning "Probe attach gate timed out on $gateLabel; falling back to delayed attach after ${FallbackDelayMs}ms."
            return
        }

        Start-Sleep -Milliseconds 500
    }

    Write-Warning "Probe attach gate did not see $gateLabel within ${TimeoutSec}s; continuing with delayed attach."
}

$bootstrapperName = "plutonium-bootstrapper-win32"
$plutoniumProcessNamePatterns = @(
    "plutonium-bootstrapper-win32",
    "plutonium*",
    "t6zm*"
)
$root = $RepoDir
$buildRoot = Join-Path $root ("_build\{0}" -f $BuildRootName)
$outputRoot = Join-Path $buildRoot "output"
$modRoot = if ($modName) { Join-Path $root ("mods\{0}" -f $modName) } else { "" }
$runtimeQuarantineRoot = Join-Path $root "_build\runtime_quarantine\game_mods"
$stockZoneControlQuarantineRoot = Join-Path $root "_build\runtime_quarantine\stock_survival_zone_control"
$appDataModRoot = if ($modName) { Join-Path $PlutoniumDir ("storage\t6\mods\{0}" -f $modName) } else { "" }
$generatedClientRoot = Join-Path $buildRoot "clientscripts\mp"
$probeRoot = Join-Path $root "native\fx_runtime_probe"
$probeBinRoot = Join-Path $probeRoot "bin\x86\Release"
$probeLogPath = Join-Path $probeBinRoot "fx_runtime_probe.log"
$probeLatestBuildJson = Join-Path $probeBinRoot "fx_runtime_probe_latest_build.json"
$probeGuardConfigPath = Join-Path $probeRoot "active_guard_config.txt"
$probeModeConfigPath = Join-Path $probeRoot "active_probe_mode.txt"
$modConsoleLogPath = Join-Path $appDataModRoot "console_zm.log"
$modGamesLogPath = Join-Path $appDataModRoot "games_mp.log"

if (-not $SkipAssetValidation) {
    $expectedZombieIpaks = @(
        (Join-Path $root "zone\all\code_post_gfx_zm.ipak"),
        (Join-Path $root "zone\all\common_zm.ipak"),
        (Join-Path $root "zone\all\ui_zm.ipak"),
        (Join-Path $root "zone\all\zm_transit.ipak"),
        (Join-Path $root "zone\all\zm_transit_patch.ipak")
    )
    $missingZombieIpaks = @($expectedZombieIpaks | Where-Object { -not (Test-Path $_) })
    if ($missingZombieIpaks.Count -gt 0) {
        Write-Warning ("Expected zombie content ipaks missing from install: {0}" -f ($missingZombieIpaks -join ", "))
        Write-Warning "Stock and modded first-person visuals may be incomplete until the base game content is restored."
    }
}
$staleMpClientscriptFiles = @(
    "_callbacks.csc",
    "_load.csc",
    "_trophy_system.csc",
    "_dogs.csc",
    "_rcbomb.csc",
    "_qrdrone.csc",
    "_ai_tank.csc",
    "_missile_swarm.csc"
)
$staleCarrierMapScriptFiles = @(
    (Join-Path $modRoot "maps\mp\zm_transit.gsc"),
    (Join-Path $modRoot "maps\mp\zm_cosmodrome_standard.gsc"),
    (Join-Path $appDataModRoot "maps\mp\zm_transit.gsc"),
    (Join-Path $appDataModRoot "maps\mp\zm_cosmodrome_standard.gsc")
)
$skipModLoadSync = ($env:ROGUE_SKIP_MOD_LOAD_SYNC -eq "1")
$skipSurvivalSync = ($env:ROGUE_SKIP_SURVIVAL_SYNC -eq "1") -or $UseStockSurvivalZone
$skipModPatchSync = ($env:ROGUE_SKIP_MOD_PATCH_SYNC -eq "1")
$skipClientScriptSync = ($env:ROGUE_SKIP_CLIENTSCRIPT_SYNC -eq "1")
$syncGeneratedServantClientOverride = $SyncGeneratedClientOverrides -or ($env:ROGUE_SYNC_GENERATED_CLIENTSCRIPT_OVERRIDES -eq "1")
$syncCarrierMapScripts = ($env:ROGUE_SYNC_CARRIER_MAP_SCRIPTS -eq "1")
$syncTransitClientScript = ($env:ROGUE_SYNC_TRANSIT_CLIENTSCRIPT -ne "0")

if ($UseStockSurvivalZone) {
    $skipClientScriptSync = $true
    $syncGeneratedServantClientOverride = $false
    $syncCarrierMapScripts = $false
    $syncTransitClientScript = $false
}

$fallbackModRoot = $null
if (Test-Path $runtimeQuarantineRoot) {
    $latestQuarantine = Get-ChildItem $runtimeQuarantineRoot -Directory | Sort-Object Name -Descending | Select-Object -First 1
    if ($latestQuarantine) {
        $candidate = if ($modName) { Join-Path $latestQuarantine.FullName $modName } else { "" }
        if (Test-Path $candidate) {
            $fallbackModRoot = $candidate
            Write-Host "Fallback mod root available: $fallbackModRoot"
        }
    }
}

function Resolve-SourcePath {
    param(
        [string[]]$Candidates
    )

    foreach ($candidate in $Candidates) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    return $Candidates[0]
}

function Get-SourceOriginLabel {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return "missing"
    }

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $fullPathLower = $fullPath.ToLowerInvariant()

    $classify = @(
        @{ Root = $modRoot; Label = "repo_mod" },
        @{ Root = $buildRoot; Label = "build_output" },
        @{ Root = $generatedClientRoot; Label = "generated_clientscripts" },
        @{ Root = $fallbackModRoot; Label = "fallback_quarantine" },
        @{ Root = $appDataModRoot; Label = "appdata_runtime" }
    )

    foreach ($entry in $classify) {
        $rootPath = [string]$entry.Root
        if ([string]::IsNullOrWhiteSpace($rootPath)) {
            continue
        }

        $rootFull = [System.IO.Path]::GetFullPath($rootPath).ToLowerInvariant()
        if ($fullPathLower.StartsWith($rootFull)) {
            return [string]$entry.Label
        }
    }

    return "external"
}

function Write-ResolvedSourceSummary {
    param(
        [string]$Label,
        [string]$Path
    )

    $origin = Get-SourceOriginLabel -Path $Path
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path $Path)) {
        Write-Warning ("Runtime source missing label={0} path={1}" -f $Label, $Path)
        return
    }

    $message = "Runtime source label={0} origin={1} path={2}" -f $Label, $origin, $Path
    if ($origin -eq "fallback_quarantine") {
        Write-Warning $message
    } else {
        Write-Host $message
    }
}

function New-ResolvedSourceRecord {
    param(
        [string]$Label,
        [string]$Path
    )

    $origin = Get-SourceOriginLabel -Path $Path
    $exists = -not [string]::IsNullOrWhiteSpace($Path) -and (Test-Path $Path)
    $size = 0
    $sha256 = ""

    if ($exists) {
        $item = Get-Item -LiteralPath $Path
        $size = [int64]$item.Length
        $sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
    }

    return [ordered]@{
        label = $Label
        path = $Path
        origin = $origin
        exists = $exists
        size = $size
        sha256 = $sha256
    }
}

$modScriptSource = Resolve-SourcePath @(
    (Join-Path $modRoot "scripts\mod_i_am_mod.gsc"),
    (Join-Path $buildRoot "scripts\mod_i_am_mod.gsc"),
    $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "scripts\mod_i_am_mod.gsc" })
)
$zmClientSource = Resolve-SourcePath @(
    (Join-Path $modRoot "clientscripts\mp\zombies\_zm.csc"),
    $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "clientscripts\mp\zombies\_zm.csc" })
)
$zmPlayersClientSource = Resolve-SourcePath @(
    (Join-Path $modRoot "clientscripts\mp\zombies\_players.csc"),
    $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "clientscripts\mp\zombies\_players.csc" })
)
$farmgirlSource = Resolve-SourcePath @(
    (Join-Path $modRoot "character\c_transit_player_farmgirl.gsc"),
    $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "character\c_transit_player_farmgirl.gsc" })
)
$oldmanSource = Resolve-SourcePath @(
    (Join-Path $modRoot "character\c_transit_player_oldman.gsc"),
    $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "character\c_transit_player_oldman.gsc" })
)
$engineerSource = Resolve-SourcePath @(
    (Join-Path $modRoot "character\c_transit_player_engineer.gsc"),
    $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "character\c_transit_player_engineer.gsc" })
)
$reporterSource = Resolve-SourcePath @(
    (Join-Path $modRoot "character\c_transit_player_reporter.gsc"),
    $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "character\c_transit_player_reporter.gsc" })
)
$spawnerSource = Resolve-SourcePath @(
    (Join-Path $modRoot "scripts\mp\zombies\_zm_spawner.gsc"),
    (Join-Path $modRoot "maps\mp\zombies\_zm_spawner.gsc"),
    $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "maps\mp\zombies\_zm_spawner.gsc" }),
    $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "scripts\mp\zombies\_zm_spawner.gsc" })
)
if (
    [string]::Equals($modName, "blackops3servant", [System.StringComparison]::OrdinalIgnoreCase) -or
    [System.Environment]::GetEnvironmentVariable("ROGUE_ALLOW_SERVER_SPAWNER_SYNC", "Process") -ne "1"
) {
    $spawnerSource = ""
}
if ($UseStockSurvivalZone) {
    $farmgirlSource = ""
    $oldmanSource = ""
    $engineerSource = ""
    $reporterSource = ""
}
$vehicleClientSource = Resolve-SourcePath @(
    (Join-Path $modRoot "clientscripts\mp\_vehicle.csc")
)
$dogsClientSource = Resolve-SourcePath @(
    (Join-Path $modRoot "clientscripts\mp\_dogs.csc")
)
$rcbombClientSource = Resolve-SourcePath @(
    (Join-Path $modRoot "clientscripts\mp\_rcbomb.csc")
)
$qrdroneClientSource = Resolve-SourcePath @(
    (Join-Path $modRoot "clientscripts\mp\_qrdrone.csc")
)
$aiTankClientSource = Resolve-SourcePath @(
    (Join-Path $modRoot "clientscripts\mp\_ai_tank.csc")
)
$missileSwarmClientSource = Resolve-SourcePath @(
    (Join-Path $modRoot "clientscripts\mp\_missile_swarm.csc")
)
$transitClientSource = Resolve-SourcePath @(
    (Join-Path $modRoot "clientscripts\mp\zm_transit.csc"),
    (Join-Path $generatedClientRoot "zm_transit.csc"),
    $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "clientscripts\mp\zm_transit.csc" })
)
$transitCarrierSource = Resolve-SourcePath @(
    (Join-Path $modRoot "maps\mp\zm_transit.gsc"),
    $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "maps\mp\zm_transit.gsc" })
)
$cosmodromeStandardSource = Resolve-SourcePath @(
    (Join-Path $modRoot "maps\mp\zm_cosmodrome_standard.gsc"),
    $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "maps\mp\zm_cosmodrome_standard.gsc" })
)
$mainLobbySource = Resolve-SourcePath @(
    (Join-Path $modRoot "ui\t6\mainlobby.lua")
)
$mainMenuSource = Resolve-SourcePath @(
    (Join-Path $modRoot "ui_mp\t6\mainmenu.lua")
)
$preferExistingModZoneSource = ($modName -and -not [string]::Equals($modName, "bo3_rev", [System.StringComparison]::OrdinalIgnoreCase))
$survivalRuntimeSource = if ($preferExistingModZoneSource) {
    Resolve-SourcePath @(
        (Join-Path $modRoot "zone\all\so_zsurvival_zm_transit.ff"),
        (Join-Path $outputRoot "so_zsurvival_zm_transit.ff"),
        $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "zone\all\so_zsurvival_zm_transit.ff" })
    )
} else {
    Resolve-SourcePath @(
        (Join-Path $outputRoot "so_zsurvival_zm_transit.ff"),
        (Join-Path $modRoot "zone\all\so_zsurvival_zm_transit.ff"),
        $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "zone\all\so_zsurvival_zm_transit.ff" })
    )
}
$survivalRuntimeIpakSource = if ($preferExistingModZoneSource) {
    Resolve-SourcePath @(
        (Join-Path $modRoot "zone\all\so_zsurvival_zm_transit.ipak"),
        (Join-Path $outputRoot "so_zsurvival_zm_transit.ipak"),
        $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "zone\all\so_zsurvival_zm_transit.ipak" })
    )
} else {
    Resolve-SourcePath @(
        (Join-Path $outputRoot "so_zsurvival_zm_transit.ipak"),
        (Join-Path $modRoot "zone\all\so_zsurvival_zm_transit.ipak"),
        $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "zone\all\so_zsurvival_zm_transit.ipak" })
    )
}
$modLoadRuntimeSource = if ($preferExistingModZoneSource) {
    Resolve-SourcePath @(
        (Join-Path $modRoot "zone\all\mod_load.ff"),
        (Join-Path $outputRoot "mod_load.ff"),
        $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "zone\all\mod_load.ff" })
    )
} else {
    Resolve-SourcePath @(
        (Join-Path $outputRoot "mod_load.ff"),
        (Join-Path $modRoot "zone\all\mod_load.ff"),
        $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "zone\all\mod_load.ff" })
    )
}
$modPatchRuntimeSource = if ($preferExistingModZoneSource) {
    Resolve-SourcePath @(
        (Join-Path $modRoot "zone\all\mod_patch.ff"),
        (Join-Path $outputRoot "mod_patch.ff"),
        $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "zone\all\mod_patch.ff" })
    )
} else {
    Resolve-SourcePath @(
        (Join-Path $outputRoot "mod_patch.ff"),
        (Join-Path $modRoot "zone\all\mod_patch.ff"),
        $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "zone\all\mod_patch.ff" })
    )
}
$modLoadIpakRuntimeSource = if ($preferExistingModZoneSource) {
    Resolve-SourcePath @(
        (Join-Path $modRoot "zone\all\mod_load.ipak"),
        (Join-Path $outputRoot "mod_load.ipak"),
        $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "zone\all\mod_load.ipak" })
    )
} else {
    Resolve-SourcePath @(
        (Join-Path $outputRoot "mod_load.ipak"),
        (Join-Path $modRoot "zone\all\mod_load.ipak"),
        $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "zone\all\mod_load.ipak" })
    )
}

$buildOutputModLoad = Join-Path $outputRoot "mod_load.ff"
$buildOutputModLoadIpak = Join-Path $outputRoot "mod_load.ipak"
if (-not $preferExistingModZoneSource) {
    if (-not (Test-Path $buildOutputModLoad)) {
        $skipModLoadSync = $true
        $modLoadRuntimeSource = $buildOutputModLoad
        $modLoadIpakRuntimeSource = $buildOutputModLoadIpak
        Write-Host "Current build did not emit mod_load.ff; stale mod_load sync disabled for this run."
    }
}
if (-not (Test-Path $modLoadRuntimeSource)) {
    $skipModLoadSync = $true
    $modLoadRuntimeSource = $buildOutputModLoad
    $modLoadIpakRuntimeSource = $buildOutputModLoadIpak
    Write-Host "Resolved mod_load.ff source is missing; mod_load sync disabled for this run."
}

function Get-LatestQuarantinedGametypeRawDir {
    param([string]$StorageRoot)

    if ([string]::IsNullOrWhiteSpace($StorageRoot) -or -not (Test-Path $StorageRoot)) {
        return ""
    }

    $parents = @(Get-ChildItem -Path $StorageRoot -Directory -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "_temp_disabled_raw*" -or $_.Name -eq "_manual_quarantine" } |
        Sort-Object LastWriteTime -Descending)

    foreach ($parent in $parents) {
        $direct = Join-Path $parent.FullName "raw\maps\mp\gametypes_zm"
        if (Test-Path $direct) {
            return $direct
        }

        foreach ($child in @(Get-ChildItem -Path $parent.FullName -Directory -Force -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)) {
            $candidate = Join-Path $child.FullName "raw\maps\mp\gametypes_zm"
            if (Test-Path $candidate) {
                return $candidate
            }
        }
    }

    return ""
}

$quarantinedGametypeRawDir = Get-LatestQuarantinedGametypeRawDir -StorageRoot (Join-Path $PlutoniumDir "storage\t6")
$gametypeRawSourceDir = Resolve-SourcePath @(
    (Join-Path $modRoot "maps\mp\gametypes_zm"),
    $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "maps\mp\gametypes_zm" }),
    (Join-Path $PlutoniumDir "storage\t6\maps\mp\gametypes_zm"),
    $quarantinedGametypeRawDir
)

Write-ResolvedSourceSummary -Label "mod_i_am_mod" -Path $modScriptSource
Write-ResolvedSourceSummary -Label "_zm.csc" -Path $zmClientSource
Write-ResolvedSourceSummary -Label "_players.csc" -Path $zmPlayersClientSource
Write-ResolvedSourceSummary -Label "farmgirl" -Path $farmgirlSource
Write-ResolvedSourceSummary -Label "oldman" -Path $oldmanSource
Write-ResolvedSourceSummary -Label "engineer" -Path $engineerSource
Write-ResolvedSourceSummary -Label "reporter" -Path $reporterSource
Write-ResolvedSourceSummary -Label "_zm_spawner.gsc" -Path $spawnerSource
Write-ResolvedSourceSummary -Label "_vehicle.csc" -Path $vehicleClientSource
Write-ResolvedSourceSummary -Label "_dogs.csc" -Path $dogsClientSource
Write-ResolvedSourceSummary -Label "_rcbomb.csc" -Path $rcbombClientSource
Write-ResolvedSourceSummary -Label "_qrdrone.csc" -Path $qrdroneClientSource
Write-ResolvedSourceSummary -Label "_ai_tank.csc" -Path $aiTankClientSource
Write-ResolvedSourceSummary -Label "_missile_swarm.csc" -Path $missileSwarmClientSource
Write-ResolvedSourceSummary -Label "zm_transit.csc" -Path $transitClientSource
Write-ResolvedSourceSummary -Label "zm_transit.gsc" -Path $transitCarrierSource
Write-ResolvedSourceSummary -Label "zm_cosmodrome_standard.gsc" -Path $cosmodromeStandardSource
Write-ResolvedSourceSummary -Label "runtime_so_zsurvival_zm_transit.ff" -Path $survivalRuntimeSource
Write-ResolvedSourceSummary -Label "runtime_so_zsurvival_zm_transit.ipak" -Path $survivalRuntimeIpakSource
Write-ResolvedSourceSummary -Label "runtime_mod_load.ff" -Path $modLoadRuntimeSource
Write-ResolvedSourceSummary -Label "runtime_mod_patch.ff" -Path $modPatchRuntimeSource
if ($syncGeneratedServantClientOverride) {
    Write-Host "Generated Servant client override: enabled"
} else {
    Write-Host "Generated Servant client override: disabled (contract overrides still sync; stale Servant client helper will be removed)"
}

$resolvedSourceReportEntries = @(
    (New-ResolvedSourceRecord -Label "mod_i_am_mod" -Path $modScriptSource),
    (New-ResolvedSourceRecord -Label "_zm.csc" -Path $zmClientSource),
    (New-ResolvedSourceRecord -Label "_players.csc" -Path $zmPlayersClientSource),
    (New-ResolvedSourceRecord -Label "farmgirl" -Path $farmgirlSource),
    (New-ResolvedSourceRecord -Label "oldman" -Path $oldmanSource),
    (New-ResolvedSourceRecord -Label "engineer" -Path $engineerSource),
    (New-ResolvedSourceRecord -Label "reporter" -Path $reporterSource),
    (New-ResolvedSourceRecord -Label "_zm_spawner.gsc" -Path $spawnerSource),
    (New-ResolvedSourceRecord -Label "_vehicle.csc" -Path $vehicleClientSource),
    (New-ResolvedSourceRecord -Label "_dogs.csc" -Path $dogsClientSource),
    (New-ResolvedSourceRecord -Label "_rcbomb.csc" -Path $rcbombClientSource),
    (New-ResolvedSourceRecord -Label "_qrdrone.csc" -Path $qrdroneClientSource),
    (New-ResolvedSourceRecord -Label "_ai_tank.csc" -Path $aiTankClientSource),
    (New-ResolvedSourceRecord -Label "_missile_swarm.csc" -Path $missileSwarmClientSource),
    (New-ResolvedSourceRecord -Label "zm_transit.csc" -Path $transitClientSource),
    (New-ResolvedSourceRecord -Label "zm_transit.gsc" -Path $transitCarrierSource),
    (New-ResolvedSourceRecord -Label "zm_cosmodrome_standard.gsc" -Path $cosmodromeStandardSource),
    (New-ResolvedSourceRecord -Label "runtime_so_zsurvival_zm_transit.ff" -Path $survivalRuntimeSource),
    (New-ResolvedSourceRecord -Label "runtime_so_zsurvival_zm_transit.ipak" -Path $survivalRuntimeIpakSource),
    (New-ResolvedSourceRecord -Label "runtime_mod_load.ff" -Path $modLoadRuntimeSource),
    (New-ResolvedSourceRecord -Label "runtime_mod_patch.ff" -Path $modPatchRuntimeSource)
)

if (-not [string]::IsNullOrWhiteSpace($ResolvedSourceReportPath)) {
    $reportDir = Split-Path -Parent $ResolvedSourceReportPath
    if (-not [string]::IsNullOrWhiteSpace($reportDir) -and -not (Test-Path $reportDir)) {
        New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
    }

    $resolvedSourceReport = [ordered]@{
        generated_at = (Get-Date).ToString("o")
        mod = $modName
        launch = [bool]$Launch
        inject_probe = [bool]$InjectProbe
        probe_mode = $ProbeMode
        map = $Map
        ui_mapname = $UiMapName
        ui_gametype = $UiGametype
        ui_zm_gamemodegroup = $UiZmGamemodeGroup
        ui_map_start_location = $UiMapStartLocation
        g_gametype = $GGametype
        sync_flags = [ordered]@{
            use_stock_survival_zone = [bool]$UseStockSurvivalZone
            sync_base_zone_all = [bool]$SyncBaseZoneAll
            sync_generated_client_overrides = [bool]$SyncGeneratedClientOverrides
            skip_asset_validation = [bool]$SkipAssetValidation
            skip_mod_load_sync = [bool]$skipModLoadSync
            skip_mod_patch_sync = [bool]$skipModPatchSync
            skip_script_sync = [bool]$skipScriptSync
            skip_survival_sync = [bool]$skipSurvivalSync
            sync_generated_servant_client_override = [bool]$syncGeneratedServantClientOverride
        }
        source_roots = [ordered]@{
            repo_mod = $modRoot
            build_output = $buildRoot
            generated_clientscripts = $generatedClientRoot
            fallback_quarantine = $fallbackModRoot
            appdata_runtime = $appDataModRoot
        }
        resolved_sources = $resolvedSourceReportEntries
    }

    $resolvedSourceReport | ConvertTo-Json -Depth 8 | Set-Content -Path $ResolvedSourceReportPath -Encoding UTF8
    Write-Host "Resolved source report: $ResolvedSourceReportPath"
}

$runtimeFiles = @(
    @{
        Source = $survivalRuntimeSource
        Required = $true
        Skip = $skipSurvivalSync
        Destinations = @(
            (Join-Path $modRoot "zone\all\so_zsurvival_zm_transit.ff"),
            (Join-Path $appDataModRoot "zone\all\so_zsurvival_zm_transit.ff")
        )
    },
    @{
        Source = $survivalRuntimeIpakSource
        Required = $false
        Skip = $skipSurvivalSync
        Destinations = @(
            (Join-Path $modRoot "zone\all\so_zsurvival_zm_transit.ipak"),
            (Join-Path $appDataModRoot "zone\all\so_zsurvival_zm_transit.ipak")
        )
    },
    @{
        Source = $modLoadRuntimeSource
        Required = $true
        Skip = $skipModLoadSync
        Destinations = @(
            (Join-Path $modRoot "zone\all\mod_load.ff"),
            (Join-Path $appDataModRoot "zone\all\mod_load.ff")
        )
    },
    @{
        Source = $modPatchRuntimeSource
        Required = $false
        Skip = $skipModPatchSync
        Destinations = @(
            (Join-Path $modRoot "zone\all\mod_patch.ff"),
            (Join-Path $appDataModRoot "zone\all\mod_patch.ff")
        )
    },
    @{
        Source = $modLoadIpakRuntimeSource
        Required = $false
        Skip = $skipModLoadSync
        Destinations = @(
            (Join-Path $modRoot "zone\all\mod_load.ipak"),
            (Join-Path $appDataModRoot "zone\all\mod_load.ipak")
        )
    }
)

if ($SyncBaseZoneAll) {
    $runtimeFiles[0].Destinations = @(
        (Join-Path $root "zone\all\so_zsurvival_zm_transit.ff"),
        (Join-Path $modRoot "zone\all\so_zsurvival_zm_transit.ff"),
        (Join-Path $appDataModRoot "zone\all\so_zsurvival_zm_transit.ff")
    )
    $runtimeFiles[1].Destinations = @(
        (Join-Path $root "zone\all\so_zsurvival_zm_transit.ipak"),
        (Join-Path $modRoot "zone\all\so_zsurvival_zm_transit.ipak"),
        (Join-Path $appDataModRoot "zone\all\so_zsurvival_zm_transit.ipak")
    )
    $runtimeFiles[2].Destinations = @(
        (Join-Path $root "zone\all\mod_load.ff"),
        (Join-Path $modRoot "zone\all\mod_load.ff"),
        (Join-Path $appDataModRoot "zone\all\mod_load.ff")
    )
    $runtimeFiles[3].Destinations = @(
        (Join-Path $root "zone\all\mod_patch.ff"),
        (Join-Path $modRoot "zone\all\mod_patch.ff"),
        (Join-Path $appDataModRoot "zone\all\mod_patch.ff")
    )
    $runtimeFiles[4].Destinations = @(
        (Join-Path $root "zone\all\mod_load.ipak"),
        (Join-Path $modRoot "zone\all\mod_load.ipak"),
        (Join-Path $appDataModRoot "zone\all\mod_load.ipak")
    )
}

if ($UseStockSurvivalZone) {
    Write-Host "Stock survival-zone control enabled. Using base install so_zsurvival_zm_transit.ff and quarantining mod overrides."

    $stockZoneEntries = @()
    if ($modRoot) {
        $stockZoneEntries += @(
            @{ Path = (Join-Path $modRoot "zone\all\so_zsurvival_zm_transit.ff"); Prefix = "repo_mod" },
            @{ Path = (Join-Path $modRoot "zone\all\so_zsurvival_zm_transit.ipak"); Prefix = "repo_mod" }
        )
    }
    if ($appDataModRoot) {
        $stockZoneEntries += @(
            @{ Path = (Join-Path $appDataModRoot "zone\all\so_zsurvival_zm_transit.ff"); Prefix = "appdata_mod" },
            @{ Path = (Join-Path $appDataModRoot "zone\all\so_zsurvival_zm_transit.ipak"); Prefix = "appdata_mod" }
        )
    }

    foreach ($entry in $stockZoneEntries) {
        Move-PathToLocalQuarantine -SourcePath $entry.Path -QuarantineRoot $stockZoneControlQuarantineRoot -Prefix $entry.Prefix
    }

    $stockSurvivalSource = Join-Path $GameDir "zone\all\so_zsurvival_zm_transit.ff"
    if (Test-Path $stockSurvivalSource) {
        Write-Host "Stock survival source -> $stockSurvivalSource"
    } else {
        Write-Warning "Stock survival source missing: $stockSurvivalSource"
    }

    foreach ($staleDir in @(
        (Join-Path $appDataModRoot "character"),
        (Join-Path $appDataModRoot "maps\mp\gametypes_zm"),
        (Join-Path $appDataModRoot "raw")
    )) {
        if (Test-Path $staleDir) {
            Remove-Item -Path $staleDir -Recurse -Force
            Write-Host "Removed stock-survival stale runtime tree: $staleDir"
        }
    }
}

$scriptFiles = @(
    @{
        Source = $modScriptSource
        RemoveIfMissing = $false
        Destinations = @(
            Join-Path $appDataModRoot "scripts\mod_i_am_mod.gsc"
        )
    },
    @{
        Source = $farmgirlSource
        RemoveIfMissing = $true
        Destinations = @(
            Join-Path $appDataModRoot "character\c_transit_player_farmgirl.gsc"
        )
    },
    @{
        Source = $oldmanSource
        RemoveIfMissing = $true
        Destinations = @(
            Join-Path $appDataModRoot "character\c_transit_player_oldman.gsc"
        )
    },
    @{
        Source = $engineerSource
        RemoveIfMissing = $true
        Destinations = @(
            Join-Path $appDataModRoot "character\c_transit_player_engineer.gsc"
        )
    },
    @{
        Source = $reporterSource
        RemoveIfMissing = $true
        Destinations = @(
            Join-Path $appDataModRoot "character\c_transit_player_reporter.gsc"
        )
    },
    @{
        Source = $spawnerSource
        RemoveIfMissing = $true
        Destinations = @(
            (Join-Path $appDataModRoot "maps\mp\zombies\_zm_spawner.gsc")
        )
    },
    @{
        Source = $vehicleClientSource
        RemoveIfMissing = $true
        Skip = $skipClientScriptSync
        Destinations = @(
            Join-Path $appDataModRoot "clientscripts\mp\_vehicle.csc"
        )
    },
    @{
        Source = $dogsClientSource
        RemoveIfMissing = $true
        Skip = $true
        Destinations = @(
            Join-Path $appDataModRoot "clientscripts\mp\_dogs.csc"
        )
    },
    @{
        Source = $rcbombClientSource
        RemoveIfMissing = $true
        Skip = $true
        Destinations = @(
            Join-Path $appDataModRoot "clientscripts\mp\_rcbomb.csc"
        )
    },
    @{
        Source = $qrdroneClientSource
        RemoveIfMissing = $true
        Skip = $true
        Destinations = @(
            Join-Path $appDataModRoot "clientscripts\mp\_qrdrone.csc"
        )
    },
    @{
        Source = $aiTankClientSource
        RemoveIfMissing = $true
        Skip = $true
        Destinations = @(
            Join-Path $appDataModRoot "clientscripts\mp\_ai_tank.csc"
        )
    },
    @{
        Source = $missileSwarmClientSource
        RemoveIfMissing = $true
        Skip = $true
        Destinations = @(
            Join-Path $appDataModRoot "clientscripts\mp\_missile_swarm.csc"
        )
    },
    @{
        Source = $transitCarrierSource
        RemoveIfMissing = $true
        Skip = (-not $syncCarrierMapScripts)
        Destinations = @(
            Join-Path $appDataModRoot "maps\mp\zm_transit.gsc"
        )
    },
    @{
        Source = $cosmodromeStandardSource
        RemoveIfMissing = $true
        Skip = (-not $syncCarrierMapScripts)
        Destinations = @(
            Join-Path $appDataModRoot "maps\mp\zm_cosmodrome_standard.gsc"
        )
    },
    @{
        Source = $transitClientSource
        RemoveIfMissing = $true
        Skip = ($skipClientScriptSync -or -not $syncTransitClientScript)
        Destinations = @(
            Join-Path $appDataModRoot "clientscripts\mp\zm_transit.csc"
        )
    },
    @{
        Source = (Join-Path $generatedClientRoot "_visionset_mgr.csc")
        RemoveIfMissing = $true
        Skip = $skipClientScriptSync
        Destinations = @(
            Join-Path $appDataModRoot "clientscripts\mp\_visionset_mgr.csc"
        )
    },
    @{
        Source = (Join-Path $generatedClientRoot "zombies\_bo3_rev_servant_fx_v3.csc")
        RemoveIfMissing = $true
        Skip = ($skipClientScriptSync -or -not $syncGeneratedServantClientOverride)
        Destinations = @(
            Join-Path $appDataModRoot "clientscripts\mp\zombies\_bo3_rev_servant_fx_v3.csc"
        )
    },
    @{
        Source = $zmClientSource
        RemoveIfMissing = $true
        Skip = $skipClientScriptSync
        Destinations = @(
            Join-Path $appDataModRoot "clientscripts\mp\zombies\_zm.csc"
        )
    },
    @{
        Source = $zmPlayersClientSource
        RemoveIfMissing = $true
        Skip = $skipClientScriptSync
        Destinations = @(
            Join-Path $appDataModRoot "clientscripts\mp\zombies\_players.csc"
        )
    },
    @{
        Source = $mainLobbySource
        RemoveIfMissing = $true
        Destinations = @(
            Join-Path $appDataModRoot "ui\t6\mainlobby.lua"
        )
    },
    @{
        Source = $mainMenuSource
        RemoveIfMissing = $true
        Destinations = @(
            Join-Path $appDataModRoot "ui_mp\t6\mainmenu.lua"
        )
    }
)

function Get-PlutoniumFamilyProcesses {
    $all = @()
    foreach ($pattern in $plutoniumProcessNamePatterns) {
        $all += Get-Process -Name $pattern -ErrorAction SilentlyContinue
    }
    $all | Sort-Object Id -Unique
}

Write-Host "Stopping Plutonium if running..."
# Avoid Win32_Process/CIM here: on this machine it can hang before launch.
# Stale injector waiters are non-critical, so skip that detection and rely on
# the explicit probe launch later in the script.

$runningBeforeStop = Get-PlutoniumFamilyProcesses
if ($runningBeforeStop) {
    foreach ($proc in $runningBeforeStop) {
        try {
            & taskkill /PID $proc.Id /T /F | Out-Null
            Write-Host "Stopped process tree pid=$($proc.Id) name=$($proc.ProcessName)"
        } catch {
            Write-Warning ("taskkill failed for pid {0} ({1}): {2}" -f $proc.Id, $proc.ProcessName, $_.Exception.Message)
            try {
                Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                Write-Host "Force-stopped pid=$($proc.Id) name=$($proc.ProcessName)"
            } catch {
                Write-Warning ("Stop-Process fallback failed for pid {0} ({1}): {2}" -f $proc.Id, $proc.ProcessName, $_.Exception.Message)
            }
        }
    }
}

$deadline = (Get-Date).AddSeconds(10)
while ($true) {
    $remaining = Get-PlutoniumFamilyProcesses
    if (-not $remaining) {
        break
    }
    if ((Get-Date) -gt $deadline) {
        $summary = ($remaining | ForEach-Object { "{0}:{1}" -f $_.ProcessName, $_.Id }) -join ", "
        throw "Timed out waiting for Plutonium family to exit. Remaining: $summary"
    }
    foreach ($proc in $remaining) {
        try {
            & taskkill /PID $proc.Id /T /F | Out-Null
        } catch {
        }
    }
    Start-Sleep -Milliseconds 250
}

Write-Host "Syncing runtime files..."
foreach ($entry in $runtimeFiles) {
    $skipEntry = $false
    if ($entry.ContainsKey("Skip")) {
        $skipEntry = [bool]$entry.Skip
    }
    if ($skipEntry) {
        foreach ($dst in $entry.Destinations) {
            if (Test-Path $dst) {
                Remove-Item -Path $dst -Force
                Write-Host "Removed skipped runtime artifact: $dst"
            }
        }
        continue
    }
    $required = $true
    if ($entry.ContainsKey("Required")) {
        $required = [bool]$entry.Required
    }
    if (-not (Test-Path $entry.Source)) {
        if ($required) {
            throw "Missing source artifact: $($entry.Source)"
        }
        Write-Host "Skipping optional artifact: $($entry.Source)"
        continue
    }
    foreach ($dst in $entry.Destinations) {
        Copy-ItemSafe -Source $entry.Source -Destination $dst
    }
}

Write-Host "Syncing loose scripts..."
foreach ($entry in $scriptFiles) {
    $skipEntry = $false
    if ($entry.ContainsKey("Skip")) {
        $skipEntry = [bool]$entry.Skip
    }
    if ($skipEntry) {
        $removeIfMissing = $false
        if ($entry.ContainsKey("RemoveIfMissing")) {
            $removeIfMissing = [bool]$entry.RemoveIfMissing
        }
        if ($removeIfMissing) {
            foreach ($dst in $entry.Destinations) {
                if (Test-Path $dst) {
                    Remove-Item -Path $dst -Force
                    Write-Host "Removed skipped script: $dst"
                }
            }
        }
        continue
    }
    $entrySource = [string]$entry.Source
    if ([string]::IsNullOrWhiteSpace($entrySource) -or -not (Test-Path $entrySource)) {
        $removeIfMissing = $false
        if ($entry.ContainsKey("RemoveIfMissing")) {
            $removeIfMissing = [bool]$entry.RemoveIfMissing
        }
        if ($removeIfMissing) {
            foreach ($dst in $entry.Destinations) {
                if (Test-Path $dst) {
                    Remove-Item -Path $dst -Force
                    Write-Host "Removed stale script: $dst"
                }
            }
        }
        continue
    }
    foreach ($dst in $entry.Destinations) {
        Copy-ItemSafe -Source $entrySource -Destination $dst
    }
}

if (-not $skipClientScriptSync) {
    $mpClientscriptDstRoot = Join-Path $appDataModRoot "clientscripts\mp"
    New-Item -ItemType Directory -Path $mpClientscriptDstRoot -Force | Out-Null
    foreach ($staleClientscriptName in $staleMpClientscriptFiles) {
        $stalePath = Join-Path $mpClientscriptDstRoot $staleClientscriptName
        if (Test-Path $stalePath) {
            Remove-Item -Path $stalePath -Force
            Write-Host "Removed stale MP clientscript: $stalePath"
        }
    }
}

$skipGametypeRawSync = $env:ROGUE_SKIP_GAMETYPE_RAW_SYNC -and $env:ROGUE_SKIP_GAMETYPE_RAW_SYNC -notin @("0", "false", "False")
$gametypeRawDestinations = @(
    (Join-Path $modRoot "maps\mp\gametypes_zm"),
    (Join-Path $appDataModRoot "maps\mp\gametypes_zm")
)

if ($skipGametypeRawSync) {
    foreach ($dstDir in $gametypeRawDestinations) {
        if (Test-Path $dstDir) {
            Remove-Item -Path $dstDir -Recurse -Force
            Write-Host "Removed stale gametype rawfiles: $dstDir"
        }
    }
}

if (-not $syncCarrierMapScripts) {
    foreach ($stalePath in $staleCarrierMapScriptFiles) {
        if (Test-Path $stalePath) {
            Remove-Item -Path $stalePath -Force
            Write-Host "Removed stale carrier map script: $stalePath"
        }
    }
}

if (-not $skipGametypeRawSync -and (Test-Path $gametypeRawSourceDir)) {
    Write-Host "Syncing gametype rawfiles..."
    foreach ($dstDir in $gametypeRawDestinations) {
        Copy-DirectoryFilesSafe -SourceDir $gametypeRawSourceDir -DestinationDir $dstDir -Filter "*.txt"
    }
}

if (-not $Launch) {
    Write-Host "Sync complete. Use -Launch to relaunch automatically."
    exit 0
}

$launchScript = Join-Path $root "tools\launch_t6_offline.ps1"
if (-not (Test-Path $launchScript)) {
    throw "Missing launch script: $launchScript"
}

if ($InjectProbe) {
    $injectScript = Join-Path $root "native\fx_runtime_probe\inject_latest.ps1"
    if (-not (Test-Path $injectScript)) {
        throw "Missing probe injector: $injectScript"
    }
    $injectArgs = $null
    $expectedProbeBuild = ""
    if (Test-Path $probeLatestBuildJson) {
        try {
            $probeMeta = Get-Content $probeLatestBuildJson -Raw | ConvertFrom-Json
            $expectedProbeBuild = [string]$probeMeta.build_id
        } catch {
        }
    }
    if (Test-Path $probeLogPath) {
        Remove-Item -Path $probeLogPath -Force
        Write-Host "Cleared old probe log: $probeLogPath"
    }
    if (Test-Path $probeGuardConfigPath) {
        Remove-Item -Path $probeGuardConfigPath -Force
    }
    @($ProbeMode) | Set-Content -Path $probeModeConfigPath -Encoding ASCII
    if (-not (Test-Path $probeModeConfigPath)) {
        throw "Failed to write probe mode config: $probeModeConfigPath"
    }
    Write-Host "Probe mode config: $probeModeConfigPath"
    Get-Content $probeModeConfigPath | ForEach-Object { Write-Host "  $_" }
    if ($expectedProbeBuild) {
        Write-Host "Expecting probe build: $expectedProbeBuild"
    }
    $injectArgs = @(
        "-ExecutionPolicy", "Bypass",
        "-File", $injectScript,
        "-ProcessName", "plutonium-bootstrapper-win32.exe",
        "-Wait"
    )
    if ($EnableProbeGuards) {
        @(
            "enabled=1"
            "label=$ProbeGuardLabel"
            "needle=$ProbeGuardNeedle"
            "delay_ms=$ProbeGuardDelayMs"
            "max_targets=$ProbeGuardMax"
        ) | Set-Content -Path $probeGuardConfigPath -Encoding ASCII
        if (-not (Test-Path $probeGuardConfigPath)) {
            throw "Failed to write probe guard config: $probeGuardConfigPath"
        }
        Write-Host "Probe guard config: $probeGuardConfigPath"
        Get-Content $probeGuardConfigPath | ForEach-Object { Write-Host "  $_" }
        Write-Host "Probe guards: enabled label=$ProbeGuardLabel needle=$ProbeGuardNeedle delay_ms=$ProbeGuardDelayMs max=$ProbeGuardMax"
    } else {
        Write-Host "Probe guards: disabled"
    }
}

Write-Host "Launching game..."
$attachGateSnapshots = @(
    (Get-LogSnapshot -Path $modConsoleLogPath),
    (Get-LogSnapshot -Path $modGamesLogPath),
    (Get-LogSnapshot -Path "C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\main\console_zm.log")
)
$launchArgs = @(
    "-ExecutionPolicy", "Bypass",
    "-File", $launchScript,
    "-Name", $Name,
    "-Mod", $Mod,
    "-RepoDir", $RepoDir,
    "-GameDir", $GameDir,
    "-PlutoniumDir", $PlutoniumDir
)
$launchArgs += @("-MonitorIndex", $MonitorIndex)
if ($MonitorIndex -gt 0) {
    $launchArgs += @("-HiddenWorker")
}
if ($Map -and $Map.Trim().Length -gt 0) {
    $launchArgs += @("-Map", $Map)
    if (-not $UiMapName -or $UiMapName.Trim().Length -eq 0) {
        $launchArgs += @("-UiMapName", $Map)
    }
    if (-not $UiGametype -or $UiGametype.Trim().Length -eq 0) {
        $launchArgs += @("-UiGametype", "zclassic")
    }
    if (-not $UiZmGamemodeGroup -or $UiZmGamemodeGroup.Trim().Length -eq 0) {
        $launchArgs += @("-UiZmGamemodeGroup", "zsurvival")
    }
    if (-not $GGametype -or $GGametype.Trim().Length -eq 0) {
        $launchArgs += @("-GGametype", "zclassic")
    }
}
if ($UiGametype -and $UiGametype.Trim().Length -gt 0) {
    $launchArgs += @("-UiGametype", $UiGametype)
}
if ($UiZmGamemodeGroup -and $UiZmGamemodeGroup.Trim().Length -gt 0) {
    $launchArgs += @("-UiZmGamemodeGroup", $UiZmGamemodeGroup)
}
if ($UiMapStartLocation -and $UiMapStartLocation.Trim().Length -gt 0) {
    $launchArgs += @("-UiMapStartLocation", $UiMapStartLocation)
}
if ($UiMapName -and $UiMapName.Trim().Length -gt 0) {
    $launchArgs += @("-UiMapName", $UiMapName)
}
if ($GGametype -and $GGametype.Trim().Length -gt 0) {
    $launchArgs += @("-GGametype", $GGametype)
}
if ($ExecCfg -and $ExecCfg.Trim().Length -gt 0) {
    $launchArgs += @("-ExecCfg", $ExecCfg)
}
foreach ($cmd in $ExtraCommands) {
    if (-not $cmd) {
        continue
    }
    $trimmed = $cmd.Trim()
    if ($trimmed.Length -eq 0) {
        continue
    }
    $launchArgs += @("-ExtraCommands", $trimmed)
}
powershell @launchArgs

if ($InjectProbe) {
    Wait-ForProbeAttachReady -ConsoleLogSnapshots $attachGateSnapshots -AttachGate $ProbeAttachGate -TimeoutSec $ProbeAttachTimeoutSec -FallbackDelayMs $ProbeAttachDelayMs
    Write-Host "Injecting probe after startup gate..."
    Start-Process powershell -ArgumentList $injectArgs | Out-Null
}

if ($InjectProbe -and (Test-Path $probeLatestBuildJson)) {
    $expectedProbeBuild = ""
    try {
        $probeMeta = Get-Content $probeLatestBuildJson -Raw | ConvertFrom-Json
        $expectedProbeBuild = [string]$probeMeta.build_id
    } catch {
    }

    if ($expectedProbeBuild) {
        Write-Host "Waiting for probe attach confirmation..."
        $deadline = (Get-Date).AddSeconds(20)
        $confirmed = $false
        while ((Get-Date) -lt $deadline) {
            if (Test-Path $probeLogPath) {
                $loadedLine = Select-String -Path $probeLogPath -Pattern "fx_runtime_probe loaded pid=.* build=$([regex]::Escape($expectedProbeBuild))" -SimpleMatch:$false -ErrorAction SilentlyContinue | Select-Object -Last 1
                if ($loadedLine) {
                    Write-Host "Probe attached: $($loadedLine.Line)" -ForegroundColor Green
                    $confirmed = $true
                    break
                }
            }
            Start-Sleep -Milliseconds 500
        }

        if (-not $confirmed) {
            throw "Probe attach was not confirmed for build $expectedProbeBuild. Check $probeLogPath."
        }
    }
}
