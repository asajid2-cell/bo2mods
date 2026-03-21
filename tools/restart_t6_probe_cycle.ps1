param(
    [switch]$Launch,
    [switch]$InjectProbe,
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

$bootstrapperName = "plutonium-bootstrapper-win32"
$root = $GameDir
$buildRoot = Join-Path $root "_build\bo3_rev_idg_probe"
$outputRoot = Join-Path $buildRoot "output"
$modRoot = Join-Path $root "mods\bo3_rev"
$appDataModRoot = Join-Path $PlutoniumDir "storage\t6\mods\bo3_rev"
$probeRoot = Join-Path $root "native\fx_runtime_probe"
$probeBinRoot = Join-Path $probeRoot "bin\x86\Release"
$probeLogPath = Join-Path $probeBinRoot "fx_runtime_probe.log"
$probeLatestBuildJson = Join-Path $probeBinRoot "fx_runtime_probe_latest_build.json"
$probeGuardConfigPath = Join-Path $probeRoot "active_guard_config.txt"

$runtimeFiles = @(
    @{
        Source = Join-Path $outputRoot "so_zsurvival_zm_transit.ff"
        Destinations = @(
            Join-Path $root "zone\all\so_zsurvival_zm_transit.ff"
            Join-Path $modRoot "zone\all\so_zsurvival_zm_transit.ff"
            Join-Path $appDataModRoot "zone\all\so_zsurvival_zm_transit.ff"
        )
    },
    @{
        Source = Join-Path $outputRoot "mod_load.ff"
        Destinations = @(
            Join-Path $root "zone\all\mod_load.ff"
            Join-Path $modRoot "zone\all\mod_load.ff"
            Join-Path $appDataModRoot "zone\all\mod_load.ff"
        )
    },
    @{
        Source = Join-Path $outputRoot "mod_load.ipak"
        Destinations = @(
            Join-Path $root "zone\all\mod_load.ipak"
            Join-Path $modRoot "zone\all\mod_load.ipak"
            Join-Path $appDataModRoot "zone\all\mod_load.ipak"
        )
    }
)

$scriptFiles = @(
    @{
        Source = Join-Path $modRoot "scripts\mod_i_am_mod.gsc"
        Destinations = @(
            Join-Path $appDataModRoot "scripts\mod_i_am_mod.gsc"
        )
    },
    @{
        Source = Join-Path $modRoot "clientscripts\mp\zm_transit.csc"
        Destinations = @(
            Join-Path $appDataModRoot "clientscripts\mp\zm_transit.csc"
        )
    },
    @{
        Source = Join-Path $modRoot "clientscripts\mp\_visionset_mgr.csc"
        Destinations = @(
            Join-Path $appDataModRoot "clientscripts\mp\_visionset_mgr.csc"
        )
    },
    @{
        Source = Join-Path $modRoot "clientscripts\mp\zombies\_bo3_rev_servant_fx_v3.csc"
        Destinations = @(
            Join-Path $appDataModRoot "clientscripts\mp\zombies\_bo3_rev_servant_fx_v3.csc"
        )
    }
)

Write-Host "Stopping Plutonium if running..."
$staleInjectors = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    ($_.Name -ieq "powershell.exe" -or $_.Name -ieq "pwsh.exe" -or $_.Name -ieq "powershell_ise.exe") -and
    $_.CommandLine -and
    $_.CommandLine -match "inject_latest\.ps1"
}
foreach ($proc in $staleInjectors) {
    try {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
        Write-Host "Stopped stale injector waiter pid=$($proc.ProcessId)"
    } catch {
        Write-Warning ("Failed to stop stale injector waiter {0}: {1}" -f $proc.ProcessId, $_.Exception.Message)
    }
}

$runningBeforeStop = Get-Process -Name $bootstrapperName -ErrorAction SilentlyContinue
if ($runningBeforeStop) {
    try {
        $runningBeforeStop | Stop-Process -Force -ErrorAction Stop
    } catch {
        Write-Warning ("Stop-Process failed for {0}: {1}" -f $bootstrapperName, $_.Exception.Message)
        try {
            & taskkill /IM "$bootstrapperName.exe" /F | Out-Null
        } catch {
            Write-Warning ("taskkill fallback failed for {0}: {1}" -f $bootstrapperName, $_.Exception.Message)
        }
    }
}

$deadline = (Get-Date).AddSeconds(10)
while (Get-Process -Name $bootstrapperName -ErrorAction SilentlyContinue) {
    if ((Get-Date) -gt $deadline) {
        throw "Timed out waiting for $bootstrapperName to exit."
    }
    Start-Sleep -Milliseconds 250
}

Write-Host "Syncing runtime files..."
foreach ($entry in $runtimeFiles) {
    if (-not (Test-Path $entry.Source)) {
        throw "Missing source artifact: $($entry.Source)"
    }
    foreach ($dst in $entry.Destinations) {
        Copy-ItemSafe -Source $entry.Source -Destination $dst
    }
}

Write-Host "Syncing loose scripts..."
foreach ($entry in $scriptFiles) {
    if (-not (Test-Path $entry.Source)) {
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
        Start-Process powershell -ArgumentList $injectArgs | Out-Null
        Write-Host "Probe guards: enabled label=$ProbeGuardLabel needle=$ProbeGuardNeedle delay_ms=$ProbeGuardDelayMs max=$ProbeGuardMax"
    } else {
        Start-Process powershell -ArgumentList $injectArgs | Out-Null
        Write-Host "Probe guards: disabled"
    }
}

Write-Host "Launching game..."
powershell -ExecutionPolicy Bypass -File $launchScript -Name $Name -Mod $Mod

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
