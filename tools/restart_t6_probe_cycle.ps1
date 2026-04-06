param(
    [switch]$Launch,
    [switch]$InjectProbe,
    [switch]$ModOnly,
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
    [string]$Name = "ffprobe_offline",
    [string]$Mod = "bo3_rev",
    [string]$GameDir = "Z:\Games\pluto_t6_full_game",
    [string]$PlutoniumDir = "C:\Users\Ahmed\AppData\Local\Plutonium"
)

$ErrorActionPreference = "Stop"

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
    Copy-Item -Path $Source -Destination $Destination -Force
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
$root = $GameDir
$buildRoot = Join-Path $root "_build\bo3_rev_idg_probe"
$outputRoot = Join-Path $buildRoot "output"
$modRoot = Join-Path $root "mods\bo3_rev"
$runtimeQuarantineRoot = Join-Path $root "_build\runtime_quarantine\game_mods"
$appDataModRoot = Join-Path $PlutoniumDir "storage\t6\mods\bo3_rev"
$generatedClientRoot = Join-Path $buildRoot "clientscripts\mp"
$probeRoot = Join-Path $root "native\fx_runtime_probe"
$probeBinRoot = Join-Path $probeRoot "bin\x86\Release"
$probeLogPath = Join-Path $probeBinRoot "fx_runtime_probe.log"
$probeLatestBuildJson = Join-Path $probeBinRoot "fx_runtime_probe_latest_build.json"
$probeGuardConfigPath = Join-Path $probeRoot "active_guard_config.txt"
$probeModeConfigPath = Join-Path $probeRoot "active_probe_mode.txt"
$modConsoleLogPath = Join-Path $appDataModRoot "console_zm.log"
$modGamesLogPath = Join-Path $appDataModRoot "games_mp.log"
$skipModLoadSync = ($env:ROGUE_SKIP_MOD_LOAD_SYNC -eq "1")
$skipSurvivalSync = ($env:ROGUE_SKIP_SURVIVAL_SYNC -eq "1")
$skipModPatchSync = ($env:ROGUE_SKIP_MOD_PATCH_SYNC -eq "1")
$skipClientScriptSync = ($env:ROGUE_SKIP_CLIENTSCRIPT_SYNC -eq "1")

$fallbackModRoot = $null
if (Test-Path $runtimeQuarantineRoot) {
    $latestQuarantine = Get-ChildItem $runtimeQuarantineRoot -Directory | Sort-Object Name -Descending | Select-Object -First 1
    if ($latestQuarantine) {
        $candidate = Join-Path $latestQuarantine.FullName "bo3_rev"
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

$modScriptSource = Resolve-SourcePath @(
    (Join-Path $modRoot "scripts\mod_i_am_mod.gsc"),
    (Join-Path $buildRoot "scripts\mod_i_am_mod.gsc"),
    $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "scripts\mod_i_am_mod.gsc" })
)
$zmClientSource = Resolve-SourcePath @(
    (Join-Path $modRoot "clientscripts\mp\zombies\_zm.csc"),
    $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "clientscripts\mp\zombies\_zm.csc" })
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
    $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "scripts\mp\zombies\_zm_spawner.gsc" })
)
$mainLobbySource = Resolve-SourcePath @(
    (Join-Path $modRoot "ui\t6\mainlobby.lua"),
    $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "ui\t6\mainlobby.lua" })
)
$mainMenuSource = Resolve-SourcePath @(
    (Join-Path $modRoot "ui_mp\t6\mainmenu.lua"),
    $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "ui_mp\t6\mainmenu.lua" })
)
$gametypeRawSourceDir = Resolve-SourcePath @(
    (Join-Path $modRoot "maps\mp\gametypes_zm"),
    $(if ($fallbackModRoot) { Join-Path $fallbackModRoot "maps\mp\gametypes_zm" }),
    (Join-Path $PlutoniumDir "storage\t6\maps\mp\gametypes_zm")
)

Write-ResolvedSourceSummary -Label "mod_i_am_mod" -Path $modScriptSource
Write-ResolvedSourceSummary -Label "_zm.csc" -Path $zmClientSource
Write-ResolvedSourceSummary -Label "farmgirl" -Path $farmgirlSource
Write-ResolvedSourceSummary -Label "oldman" -Path $oldmanSource
Write-ResolvedSourceSummary -Label "engineer" -Path $engineerSource
Write-ResolvedSourceSummary -Label "reporter" -Path $reporterSource
Write-ResolvedSourceSummary -Label "_zm_spawner.gsc" -Path $spawnerSource

$baseZoneTargets = @()
if (-not $ModOnly) {
    $baseZoneTargets = @(
        (Join-Path $root "zone\all\so_zsurvival_zm_transit.ff"),
        (Join-Path $root "zone\all\mod_load.ff"),
        (Join-Path $root "zone\all\mod_patch.ff"),
        (Join-Path $root "zone\all\mod_load.ipak")
    )
}

$runtimeFiles = @(
    @{
        Source = Join-Path $outputRoot "so_zsurvival_zm_transit.ff"
        Required = $true
        Skip = $skipSurvivalSync
        Destinations = @(
            (Join-Path $modRoot "zone\all\so_zsurvival_zm_transit.ff"),
            (Join-Path $appDataModRoot "zone\all\so_zsurvival_zm_transit.ff")
        )
    },
    @{
        Source = Join-Path $outputRoot "mod_load.ff"
        Required = $true
        Skip = $skipModLoadSync
        Destinations = @(
            (Join-Path $modRoot "zone\all\mod_load.ff"),
            (Join-Path $appDataModRoot "zone\all\mod_load.ff")
        )
    },
    @{
        Source = Join-Path $outputRoot "mod_patch.ff"
        Required = $false
        Skip = $skipModPatchSync
        Destinations = @(
            (Join-Path $modRoot "zone\all\mod_patch.ff"),
            (Join-Path $appDataModRoot "zone\all\mod_patch.ff")
        )
    },
    @{
        Source = Join-Path $outputRoot "mod_load.ipak"
        Required = $false
        Skip = $skipModLoadSync
        Destinations = @(
            (Join-Path $modRoot "zone\all\mod_load.ipak"),
            (Join-Path $appDataModRoot "zone\all\mod_load.ipak")
        )
    }
)

if (-not $ModOnly) {
    $runtimeFiles[0].Destinations = @(
        (Join-Path $root "zone\all\so_zsurvival_zm_transit.ff"),
        (Join-Path $modRoot "zone\all\so_zsurvival_zm_transit.ff"),
        (Join-Path $appDataModRoot "zone\all\so_zsurvival_zm_transit.ff")
    )
    $runtimeFiles[1].Destinations = @(
        (Join-Path $root "zone\all\mod_load.ff"),
        (Join-Path $modRoot "zone\all\mod_load.ff"),
        (Join-Path $appDataModRoot "zone\all\mod_load.ff")
    )
    $runtimeFiles[2].Destinations = @(
        (Join-Path $root "zone\all\mod_patch.ff"),
        (Join-Path $modRoot "zone\all\mod_patch.ff"),
        (Join-Path $appDataModRoot "zone\all\mod_patch.ff")
    )
    $runtimeFiles[3].Destinations = @(
        (Join-Path $root "zone\all\mod_load.ipak"),
        (Join-Path $modRoot "zone\all\mod_load.ipak"),
        (Join-Path $appDataModRoot "zone\all\mod_load.ipak")
    )
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
            Join-Path $appDataModRoot "scripts\mp\zombies\_zm_spawner.gsc"
        )
    },
    @{
        Source = (Join-Path $generatedClientRoot "zm_transit.csc")
        RemoveIfMissing = $true
        Skip = $skipClientScriptSync
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
        Skip = $skipClientScriptSync
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
    if (-not (Test-Path $entry.Source)) {
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
        Copy-ItemSafe -Source $entry.Source -Destination $dst
    }
}

if (Test-Path $gametypeRawSourceDir) {
    Write-Host "Syncing gametype rawfiles..."
    foreach ($dstDir in @(
        (Join-Path $modRoot "maps\mp\gametypes_zm"),
        (Join-Path $appDataModRoot "maps\mp\gametypes_zm")
    )) {
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
    "-Mod", $Mod
)
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
