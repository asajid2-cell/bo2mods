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
    [ValidateSet("safe", "render_opacity_focus", "xanim_focus", "xanim_consumer_focus")]
    [string]$ProbeMode = "safe",
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
    $dstDir = Split-Path -Parent $Destination
    if (-not (Test-Path $dstDir)) {
        New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
    }
    Copy-Item -Path $Source -Destination $Destination -Force
    Write-Host "Synced: $Destination"
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

function Wait-ForProbeAttachReady {
    param(
        [string[]]$ConsoleLogPaths,
        [int]$TimeoutSec,
        [int]$FallbackDelayMs
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $fallbackAt = (Get-Date).AddMilliseconds($FallbackDelayMs)
    $markers = @(
        "Loading fastfile mod_patch",
        "execing ffprobe_autorun.cfg",
        "Loading fastfile ui_zm",
        "Loading fastfile common_zm"
    )

    while ((Get-Date) -lt $deadline) {
        foreach ($consoleLogPath in @($ConsoleLogPaths)) {
            if ([string]::IsNullOrWhiteSpace($consoleLogPath)) {
                continue
            }
            $text = Get-SharedText -Path $consoleLogPath
            foreach ($marker in $markers) {
                if ($text -like "*$marker*") {
                    Write-Host "Probe attach gate reached: $marker source=$consoleLogPath"
                    return
                }
            }
        }

        if ((Get-Date) -ge $fallbackAt) {
            Write-Warning "Probe attach gate timed out on startup markers; falling back to delayed attach after ${FallbackDelayMs}ms."
            return
        }

        Start-Sleep -Milliseconds 500
    }

    Write-Warning "Probe attach gate did not see startup markers within ${TimeoutSec}s; continuing with delayed attach."
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
$appDataModRoot = Join-Path $PlutoniumDir "storage\t6\mods\bo3_rev"
$generatedClientRoot = Join-Path $buildRoot "clientscripts\mp"
$probeRoot = Join-Path $root "native\fx_runtime_probe"
$probeBinRoot = Join-Path $probeRoot "bin\x86\Release"
$probeLogPath = Join-Path $probeBinRoot "fx_runtime_probe.log"
$probeLatestBuildJson = Join-Path $probeBinRoot "fx_runtime_probe_latest_build.json"
$probeGuardConfigPath = Join-Path $probeRoot "active_guard_config.txt"
$probeModeConfigPath = Join-Path $probeRoot "active_probe_mode.txt"
$modConsoleLogPath = Join-Path $appDataModRoot "console_zm.log"
$skipModLoadSync = ($env:ROGUE_SKIP_MOD_LOAD_SYNC -eq "1")
$skipSurvivalSync = ($env:ROGUE_SKIP_SURVIVAL_SYNC -eq "1")
$skipModPatchSync = ($env:ROGUE_SKIP_MOD_PATCH_SYNC -eq "1")
$skipClientScriptSync = ($env:ROGUE_SKIP_CLIENTSCRIPT_SYNC -eq "1")

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
        Source = Join-Path $modRoot "scripts\mod_i_am_mod.gsc"
        RemoveIfMissing = $false
        Destinations = @(
            Join-Path $appDataModRoot "scripts\mod_i_am_mod.gsc"
        )
    },
    @{
        Source = Join-Path $modRoot "character\c_transit_player_farmgirl.gsc"
        RemoveIfMissing = $true
        Destinations = @(
            Join-Path $appDataModRoot "character\c_transit_player_farmgirl.gsc"
        )
    },
    @{
        Source = Join-Path $modRoot "character\c_transit_player_oldman.gsc"
        RemoveIfMissing = $true
        Destinations = @(
            Join-Path $appDataModRoot "character\c_transit_player_oldman.gsc"
        )
    },
    @{
        Source = Join-Path $modRoot "character\c_transit_player_engineer.gsc"
        RemoveIfMissing = $true
        Destinations = @(
            Join-Path $appDataModRoot "character\c_transit_player_engineer.gsc"
        )
    },
    @{
        Source = Join-Path $modRoot "character\c_transit_player_reporter.gsc"
        RemoveIfMissing = $true
        Destinations = @(
            Join-Path $appDataModRoot "character\c_transit_player_reporter.gsc"
        )
    },
    @{
        Source = Join-Path $modRoot "scripts\mp\zombies\_zm_spawner.gsc"
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
        Source = Join-Path $modRoot "clientscripts\mp\zombies\_zm.csc"
        RemoveIfMissing = $true
        Skip = $skipClientScriptSync
        Destinations = @(
            Join-Path $appDataModRoot "clientscripts\mp\zombies\_zm.csc"
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
    Wait-ForProbeAttachReady -ConsoleLogPaths @($modConsoleLogPath, "C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\main\console_zm.log") -TimeoutSec $ProbeAttachTimeoutSec -FallbackDelayMs $ProbeAttachDelayMs
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
