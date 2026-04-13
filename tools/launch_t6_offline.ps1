param(
    [string]$Mode = "ZM",
    [string]$Name = "offline_player",
    [string]$GameDir = "Z:\Games\t6-clean\pluto_t6_full_game",
    [string]$PlutoniumDir = "C:\Users\Ahmed\AppData\Local\Plutonium",
    [string]$RepoDir = "",
    [string]$Mod = "bo3_rev",
    [switch]$NoMod,
    [string]$Map = "",
    [string]$UiGametype = "",
    [string]$UiZmGamemodeGroup = "",
    [string]$UiMapStartLocation = "",
    [string]$UiMapName = "",
    [string]$GGametype = "",
    [string]$ExecCfg = "",
    [string[]]$ExtraCommands = @(),
    [switch]$MenuOnly,
    [switch]$SkipAssetValidation,
    [switch]$SkipUiOverrides,
    [switch]$SkipZombieIpakRepair,
    [switch]$SkipLaunchHygiene,
    [ValidateRange(0, 16)]
    [int]$MonitorIndex = 2,
    [ValidateRange(1, 300)]
    [int]$WindowMoveTimeoutSec = 90,
    [ValidateRange(1, 250)]
    [int]$WindowMoveFastPollMs = 2,
    [ValidateRange(50, 1000)]
    [int]$WindowMoveSlowPollMs = 100,
    [ValidateRange(1, 30)]
    [int]$WindowMoveFastPhaseSec = 12,
    [switch]$HiddenWorker,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoDir)) {
    $RepoDir = Split-Path -Parent $PSScriptRoot
}

$RepoDir = [System.IO.Path]::GetFullPath($RepoDir)
$GameDir = [System.IO.Path]::GetFullPath($GameDir)
$PlutoniumDir = [System.IO.Path]::GetFullPath($PlutoniumDir)

$monitorMoveLogPath = Join-Path $PlutoniumDir "storage\t6\launch_monitor_trace.log"

function Write-MonitorMoveTrace {
    param([string]$Message)

    try {
        $logDir = Split-Path -Parent $monitorMoveLogPath
        if (-not (Test-Path $logDir)) {
            New-Item -ItemType Directory -Path $logDir -Force | Out-Null
        }
        $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
        Add-Content -Path $monitorMoveLogPath -Value ("[{0}] {1}" -f $stamp, $Message) -Encoding ASCII
    }
    catch {
    }
}

function Start-HiddenSelfLaunch {
    param(
        [hashtable]$ForwardedParameters
    )

    $hostExe = Join-Path $PSHOME "powershell.exe"
    if (-not (Test-Path $hostExe)) {
        $hostExe = "powershell.exe"
    }

    $argList = @(
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy", "Bypass",
        "-File", $PSCommandPath,
        "-HiddenWorker"
    )

    foreach ($entry in $ForwardedParameters.GetEnumerator()) {
        $name = [string]$entry.Key
        if ($name -in @("HiddenWorker", "DryRun")) {
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

    Write-MonitorMoveTrace ("hidden_worker_spawn host={0} args={1}" -f $hostExe, ($argList -join " "))
    Start-Process -FilePath $hostExe -ArgumentList $argList -WindowStyle Hidden -WorkingDirectory (Split-Path -Parent $PSCommandPath) | Out-Null
}

if ($MonitorIndex -gt 0 -and -not $HiddenWorker -and -not $DryRun) {
    Write-MonitorMoveTrace "launcher_handoff monitor=$MonitorIndex hidden_worker=1"
    Start-HiddenSelfLaunch -ForwardedParameters $script:PSBoundParameters
    Write-Host "Launching hidden helper for monitor $MonitorIndex." -ForegroundColor Green
    return
}

if ($HiddenWorker) {
    Write-MonitorMoveTrace "hidden_worker_begin"
}

function Get-DisplayScreens {
    try {
        Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop
    }
    catch {
        throw "Failed to load System.Windows.Forms for monitor enumeration: $($_.Exception.Message)"
    }

    $screens = [System.Windows.Forms.Screen]::AllScreens
    if ($null -eq $screens -or $screens.Count -le 0) {
        throw "Windows did not report any display screens."
    }

    return @($screens)
}

function Get-TargetScreen {
    param([int]$RequestedMonitorIndex)

    if ($RequestedMonitorIndex -le 0) {
        return $null
    }

    $screens = @(Get-DisplayScreens)
    if ($RequestedMonitorIndex -gt $screens.Count) {
        $available = @()
        for ($i = 0; $i -lt $screens.Count; $i++) {
            $screen = $screens[$i]
            $available += ("{0}:{1}{2}" -f ($i + 1), $screen.DeviceName, $(if ($screen.Primary) { " primary" } else { "" }))
        }
        throw "MonitorIndex $RequestedMonitorIndex is invalid. Windows reports $($screens.Count) monitor(s): $($available -join ', ')"
    }

    return $screens[$RequestedMonitorIndex - 1]
}

function Get-EngineMonitorOrdinal {
    param([int]$RequestedMonitorIndex)

    if ($RequestedMonitorIndex -le 0) {
        return 0
    }

    return [Math]::Max(0, $RequestedMonitorIndex - 1)
}

function Update-OrAppendCfgValue {
    param(
        [System.Collections.Generic.List[string]]$Lines,
        [string]$Name,
        [string]$Value
    )

    $pattern = '^\s*seta?\s+' + [regex]::Escape($Name) + '\s+"?.*"?\s*$'
    $matchIndexes = New-Object System.Collections.Generic.List[int]
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i] -match $pattern) {
            $matchIndexes.Add($i) | Out-Null
        }
    }

    if ($matchIndexes.Count -gt 0) {
        $firstIndex = $matchIndexes[0]
        $Lines[$firstIndex] = ('seta {0} "{1}"' -f $Name, $Value)
        for ($j = $matchIndexes.Count - 1; $j -ge 1; $j--) {
            $Lines.RemoveAt($matchIndexes[$j])
        }
        return
    }

    $Lines.Add(('seta {0} "{1}"' -f $Name, $Value)) | Out-Null
}

function Set-LaunchMonitorConfig {
    param(
        [string]$PlayersRoot,
        [string]$Mode,
        [string]$ModName,
        [int]$RequestedMonitorIndex
    )

    if ($RequestedMonitorIndex -le 0 -or [string]::IsNullOrWhiteSpace($PlayersRoot) -or -not (Test-Path $PlayersRoot)) {
        return
    }

    $targetScreen = Get-TargetScreen -RequestedMonitorIndex $RequestedMonitorIndex
    $engineMonitorOrdinal = Get-EngineMonitorOrdinal -RequestedMonitorIndex $RequestedMonitorIndex
    $cfgLeaf = if ($Mode.ToUpperInvariant() -eq "ZM") { "plutonium_zm.cfg" } else { "plutonium_mp.cfg" }
    $candidateCfgs = New-Object System.Collections.Generic.List[string]

    $globalCfg = Join-Path $PlayersRoot $cfgLeaf
    $candidateCfgs.Add($globalCfg) | Out-Null
    if (-not [string]::IsNullOrWhiteSpace($ModName)) {
        $modCfg = Join-Path $PlayersRoot ("mods\{0}\{1}" -f $ModName, $cfgLeaf)
        $candidateCfgs.Add($modCfg) | Out-Null
    }

    foreach ($cfgPath in $candidateCfgs) {
        $cfgDir = Split-Path -Parent $cfgPath
        if (-not (Test-Path $cfgDir)) {
            New-Item -ItemType Directory -Path $cfgDir -Force | Out-Null
        }

        $lines = New-Object System.Collections.Generic.List[string]
        if (Test-Path $cfgPath) {
            foreach ($line in @(Get-Content -Path $cfgPath -ErrorAction SilentlyContinue)) {
                $lines.Add([string]$line) | Out-Null
            }
        }

        Update-OrAppendCfgValue -Lines $lines -Name "r_monitor" -Value $engineMonitorOrdinal
        Update-OrAppendCfgValue -Lines $lines -Name "vid_xpos" -Value $targetScreen.Bounds.X
        Update-OrAppendCfgValue -Lines $lines -Name "vid_ypos" -Value $targetScreen.Bounds.Y

        Set-Content -Path $cfgPath -Value $lines -Encoding ASCII
        Write-Host "Seeded monitor config: $cfgPath -> monitor=$engineMonitorOrdinal xpos=$($targetScreen.Bounds.X) ypos=$($targetScreen.Bounds.Y)"
    }
}

function Reset-LaunchMonitorWindowCoords {
    param(
        [string]$PlayersRoot,
        [string]$Mode,
        [string]$ModName
    )

    if ([string]::IsNullOrWhiteSpace($PlayersRoot) -or -not (Test-Path $PlayersRoot)) {
        return
    }

    $cfgLeaf = if ($Mode.ToUpperInvariant() -eq "ZM") { "plutonium_zm.cfg" } else { "plutonium_mp.cfg" }
    $candidateCfgs = New-Object System.Collections.Generic.List[string]
    $candidateCfgs.Add((Join-Path $PlayersRoot $cfgLeaf)) | Out-Null
    if (-not [string]::IsNullOrWhiteSpace($ModName)) {
        $candidateCfgs.Add((Join-Path $PlayersRoot ("mods\{0}\{1}" -f $ModName, $cfgLeaf))) | Out-Null
    }

    foreach ($cfgPath in $candidateCfgs) {
        if (-not (Test-Path $cfgPath)) {
            continue
        }

        $lines = New-Object System.Collections.Generic.List[string]
        foreach ($line in @(Get-Content -Path $cfgPath -ErrorAction SilentlyContinue)) {
            $lines.Add([string]$line) | Out-Null
        }

        Update-OrAppendCfgValue -Lines $lines -Name "vid_xpos" -Value 0
        Update-OrAppendCfgValue -Lines $lines -Name "vid_ypos" -Value 0
        Set-Content -Path $cfgPath -Value $lines -Encoding ASCII
        Write-Host "Reset monitor coords: $cfgPath -> xpos=0 ypos=0"
    }
}

function Ensure-WindowMoveInterop {
    if ("LaunchWindowInterop.NativeMethods" -as [type]) {
        return
    }

    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

namespace LaunchWindowInterop
{
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    public static class NativeMethods
    {
        public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

        [DllImport("user32.dll", SetLastError = true)]
        public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

        [DllImport("user32.dll", SetLastError = true)]
        public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);

        [DllImport("user32.dll", SetLastError = true)]
        public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);

        [DllImport("user32.dll", SetLastError = true)]
        public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

        [DllImport("user32.dll", SetLastError = true)]
        public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

        [DllImport("user32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        public static extern bool IsWindowVisible(IntPtr hWnd);
    }
}
"@
}

function Get-VisibleTopLevelWindowsForPids {
    param([int[]]$Pids)

    $results = New-Object System.Collections.Generic.List[object]
    if ($null -eq $Pids -or $Pids.Count -eq 0) {
        return @()
    }

    $pidSet = @{}
    foreach ($candidatePid in $Pids) {
        if ($candidatePid -gt 0) {
            $pidSet[[uint32]$candidatePid] = $true
        }
    }
    if ($pidSet.Count -eq 0) {
        return @()
    }

    $callback = [LaunchWindowInterop.NativeMethods+EnumWindowsProc]{
        param([IntPtr]$hWnd, [IntPtr]$lParam)
        $ownerPid = [uint32]0
        [void][LaunchWindowInterop.NativeMethods]::GetWindowThreadProcessId($hWnd, [ref]$ownerPid)
        if ($pidSet.ContainsKey($ownerPid) -and [LaunchWindowInterop.NativeMethods]::IsWindowVisible($hWnd)) {
            $results.Add([pscustomobject]@{
                Pid = [int]$ownerPid
                Handle = $hWnd
            }) | Out-Null
        }
        return $true
    }

    [void][LaunchWindowInterop.NativeMethods]::EnumWindows($callback, [IntPtr]::Zero)
    return @($results.ToArray())
}

function Move-LaunchWindowToMonitor {
    param(
        [int]$PrimaryPid,
        [datetime]$LaunchStartTime,
        [int]$RequestedMonitorIndex,
        [int]$TimeoutSec,
        [int]$FastPollMs,
        [int]$SlowPollMs,
        [int]$FastPhaseSec
    )

    if ($RequestedMonitorIndex -le 0) {
        return
    }

    $targetScreen = Get-TargetScreen -RequestedMonitorIndex $RequestedMonitorIndex
    Ensure-WindowMoveInterop

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $fastDeadline = (Get-Date).AddSeconds($FastPhaseSec)
    $candidateNames = @("plutonium-bootstrapper-win32", "BlackOps2")
    $movedAny = $false
    $seenMoved = @{}

    Write-MonitorMoveTrace ("monitor_guard_begin target_monitor={0} bounds={1},{2} {3}x{4} timeout_sec={5} fast_poll_ms={6} slow_poll_ms={7} fast_phase_sec={8}" -f $RequestedMonitorIndex, $targetScreen.Bounds.X, $targetScreen.Bounds.Y, $targetScreen.Bounds.Width, $targetScreen.Bounds.Height, $TimeoutSec, $FastPollMs, $SlowPollMs, $FastPhaseSec)

    while ((Get-Date) -lt $deadline) {
        $candidates = New-Object System.Collections.Generic.List[System.Diagnostics.Process]

        try {
            $primaryProcess = Get-Process -Id $PrimaryPid -ErrorAction Stop
            $candidates.Add($primaryProcess)
        }
        catch {
        }

        foreach ($candidateName in $candidateNames) {
            $procs = Get-Process -Name $candidateName -ErrorAction SilentlyContinue |
                Where-Object {
                    try {
                        $_.StartTime -ge $LaunchStartTime.AddSeconds(-2)
                    }
                    catch {
                        $false
                    }
                } |
                Sort-Object StartTime -Descending
            foreach ($proc in @($procs)) {
                if (-not ($candidates | Where-Object { $_.Id -eq $proc.Id })) {
                    $candidates.Add($proc)
                }
            }
        }

        $candidatePids = @($candidates | Sort-Object StartTime -Descending | Select-Object -ExpandProperty Id -Unique)
        $windows = @(Get-VisibleTopLevelWindowsForPids -Pids $candidatePids)
        if ($windows.Count -gt 0) {
            Write-MonitorMoveTrace ("window_scan pids={0} visible_windows={1}" -f ($candidatePids -join ","), $windows.Count)
        }
        foreach ($windowInfo in $windows) {
            $handle = [IntPtr]$windowInfo.Handle
            $rect = New-Object LaunchWindowInterop.RECT
            $hasRect = [LaunchWindowInterop.NativeMethods]::GetWindowRect($handle, [ref]$rect)

            $width = if ($hasRect) { [Math]::Max(640, $rect.Right - $rect.Left) } else { $targetScreen.Bounds.Width }
            $height = if ($hasRect) { [Math]::Max(480, $rect.Bottom - $rect.Top) } else { $targetScreen.Bounds.Height }
            $targetWidth = [Math]::Min($width, $targetScreen.Bounds.Width)
            $targetHeight = [Math]::Min($height, $targetScreen.Bounds.Height)
            $targetX = $targetScreen.Bounds.X + [Math]::Max(0, [Math]::Floor(($targetScreen.Bounds.Width - $targetWidth) / 2))
            $targetY = $targetScreen.Bounds.Y + [Math]::Max(0, [Math]::Floor(($targetScreen.Bounds.Height - $targetHeight) / 2))

            $isAlreadyOnTarget = $hasRect -and `
                $rect.Left -ge $targetScreen.Bounds.X -and `
                $rect.Left -lt ($targetScreen.Bounds.X + $targetScreen.Bounds.Width) -and `
                $rect.Top -ge $targetScreen.Bounds.Y -and `
                $rect.Top -lt ($targetScreen.Bounds.Y + $targetScreen.Bounds.Height)

            $seenKey = "$($windowInfo.Pid):$handle"
            if (-not $isAlreadyOnTarget -or -not $seenMoved.ContainsKey($seenKey)) {
                if (-not $isAlreadyOnTarget) {
                    [void][LaunchWindowInterop.NativeMethods]::ShowWindowAsync($handle, 0)
                }
                $flags = 0x0004 -bor 0x0010 -bor 0x0040
                $setResult = [LaunchWindowInterop.NativeMethods]::SetWindowPos($handle, [IntPtr]::Zero, $targetX, $targetY, $targetWidth, $targetHeight, $flags)
                if (-not $setResult) {
                    $win32Error = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
                    Write-Warning "Found launch window pid=$($windowInfo.Pid) but failed to move it to monitor $RequestedMonitorIndex (Win32Error=$win32Error)."
                    Write-MonitorMoveTrace ("window_move_failed pid={0} hwnd={1} win32_error={2}" -f $windowInfo.Pid, $handle, $win32Error)
                }
                else {
                    [void][LaunchWindowInterop.NativeMethods]::ShowWindowAsync($handle, 9)
                    Write-Host ("Moved launch window pid={0} hwnd={1} to monitor {2} ({3},{4} {5}x{6})" -f $windowInfo.Pid, $handle, $RequestedMonitorIndex, $targetX, $targetY, $targetWidth, $targetHeight) -ForegroundColor Green
                    Write-MonitorMoveTrace ("window_move_success pid={0} hwnd={1} target_monitor={2} rect={3},{4},{5},{6}" -f $windowInfo.Pid, $handle, $RequestedMonitorIndex, $targetX, $targetY, $targetWidth, $targetHeight)
                    $movedAny = $true
                    $seenMoved[$seenKey] = $true
                }
            }
        }

        $sleepMs = if ((Get-Date) -lt $fastDeadline) { $FastPollMs } else { $SlowPollMs }
        Start-Sleep -Milliseconds $sleepMs
    }

    if (-not $movedAny) {
        Write-Warning "Monitor move requested for monitor $RequestedMonitorIndex, but no Plutonium window was found within $TimeoutSec seconds."
        Write-MonitorMoveTrace ("monitor_guard_end moved_any=0")
    }
    else {
        Write-MonitorMoveTrace ("monitor_guard_end moved_any=1")
    }
}

$modName = ""
if ($NoMod) {
    $modName = ""
} elseif ($Mod) {
    $modName = $Mod.Trim()
    if ($modName -in @("none", "<none>", "stock")) {
        $modName = ""
    }
}

$globalStorageRoot = Join-Path $PlutoniumDir "storage\t6"
$launchQuarantineRoot = Join-Path $globalStorageRoot "_runtime_quarantine\launch_hygiene"

function Move-PathToLaunchQuarantine {
    param(
        [string]$SourcePath,
        [string]$Label
    )

    if ([string]::IsNullOrWhiteSpace($SourcePath) -or -not (Test-Path $SourcePath)) {
        return
    }

    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $destRoot = Join-Path $launchQuarantineRoot $stamp
    New-Item -ItemType Directory -Path $destRoot -Force | Out-Null
    $destPath = Join-Path $destRoot (Split-Path -Path $SourcePath -Leaf)
    if (Test-Path $destPath) {
        Remove-Item -LiteralPath $destPath -Recurse -Force
    }
    Move-Item -LiteralPath $SourcePath -Destination $destPath
    Write-Host "Quarantined $Label -> $destPath"
}

function Get-LatestQuarantineSubpath {
    param([string]$LeafName)

    if ([string]::IsNullOrWhiteSpace($LeafName) -or -not (Test-Path $globalStorageRoot)) {
        return ""
    }

    $candidates = New-Object System.Collections.Generic.List[string]
    $searchParents = Get-ChildItem -Path $globalStorageRoot -Directory -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "_temp_disabled_loose*" -or $_.Name -eq "_manual_quarantine" }

    foreach ($parent in @($searchParents | Sort-Object Name -Descending)) {
        $direct = Join-Path $parent.FullName $LeafName
        if (Test-Path $direct) {
            $candidates.Add($direct)
        }
        foreach ($child in @(Get-ChildItem -Path $parent.FullName -Directory -Force -ErrorAction SilentlyContinue | Sort-Object Name -Descending)) {
            $candidate = Join-Path $child.FullName $LeafName
            if (Test-Path $candidate) {
                $candidates.Add($candidate)
            }
        }
    }

    if ($candidates.Count -gt 0) {
        return $candidates[0]
    }

    return ""
}

function Restore-GlobalSupportTreeIfMissing {
    param([string]$LeafName)

    if ([string]::IsNullOrWhiteSpace($LeafName)) {
        return
    }

    $destPath = Join-Path $globalStorageRoot $LeafName
    if (Test-Path $destPath) {
        return
    }

    $sourcePath = Get-LatestQuarantineSubpath -LeafName $LeafName
    if ([string]::IsNullOrWhiteSpace($sourcePath) -or -not (Test-Path $sourcePath)) {
        return
    }

    $destParent = Split-Path -Parent $destPath
    if (-not (Test-Path $destParent)) {
        New-Item -ItemType Directory -Path $destParent -Force | Out-Null
    }

    Copy-Item -LiteralPath $sourcePath -Destination $destPath -Recurse -Force
    Write-Host "Restored global support tree: $destPath <- $sourcePath"
}

function Get-LatestQuarantinedRawRoot {
    if (-not (Test-Path $globalStorageRoot)) {
        return ""
    }

    $candidates = New-Object System.Collections.Generic.List[string]
    $searchParents = Get-ChildItem -Path $globalStorageRoot -Directory -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "_temp_disabled_raw*" -or $_.Name -eq "_manual_quarantine" }

    foreach ($parent in @($searchParents | Sort-Object Name -Descending)) {
        $direct = Join-Path $parent.FullName "raw"
        if (Test-Path $direct) {
            $candidates.Add($direct)
        }
        foreach ($child in @(Get-ChildItem -Path $parent.FullName -Directory -Force -ErrorAction SilentlyContinue | Sort-Object Name -Descending)) {
            $candidate = Join-Path $child.FullName "raw"
            if (Test-Path $candidate) {
                $candidates.Add($candidate)
            }
        }
    }

    if ($candidates.Count -gt 0) {
        return $candidates[0]
    }

    return ""
}

function Copy-RawSupportEntry {
    param(
        [string]$SourceRoot,
        [string]$RelativePath
    )

    if ([string]::IsNullOrWhiteSpace($SourceRoot) -or [string]::IsNullOrWhiteSpace($RelativePath)) {
        return
    }

    $sourcePath = Join-Path $SourceRoot $RelativePath
    if (-not (Test-Path $sourcePath)) {
        return
    }

    $destPath = Join-Path $globalStorageRoot ("raw\" + $RelativePath)
    $destParent = Split-Path -Parent $destPath
    if (-not (Test-Path $destParent)) {
        New-Item -ItemType Directory -Path $destParent -Force | Out-Null
    }

    Copy-Item -LiteralPath $sourcePath -Destination $destPath -Recurse -Force
    Write-Host "Restored sanitized raw support: $destPath <- $sourcePath"
}

function Restore-SanitizedRawSupport {
    $disableRestore = [System.Environment]::GetEnvironmentVariable("ROGUE_DISABLE_SANITIZED_RAW_RESTORE", "Process")
    if ($disableRestore -eq "1") {
        Write-Host "Sanitized raw restore disabled by ROGUE_DISABLE_SANITIZED_RAW_RESTORE=1"
        return
    }

    $rawSourceRoot = Get-LatestQuarantinedRawRoot
    if ([string]::IsNullOrWhiteSpace($rawSourceRoot) -or -not (Test-Path $rawSourceRoot)) {
        return
    }

    foreach ($relativePath in @(
        "localizedstrings\en_patch_mp.str",
        "localizedstrings\en_patch_zm.str"
    )) {
        Copy-RawSupportEntry -SourceRoot $rawSourceRoot -RelativePath $relativePath
    }

    $restoreGlobalGametypeRaw = [System.Environment]::GetEnvironmentVariable("ROGUE_RESTORE_GLOBAL_GAMETYPE_RAW", "Process")
    if ($restoreGlobalGametypeRaw -and $restoreGlobalGametypeRaw -notin @("0", "false", "False")) {
        Copy-RawSupportEntry -SourceRoot $rawSourceRoot -RelativePath "maps\mp\gametypes_zm"
    }
}

function Restore-ActiveModRawSupport {
    param(
        [string]$AppDataModRoot,
        [string]$RepoModRoot
    )

    if ([string]::IsNullOrWhiteSpace($globalStorageRoot)) {
        return
    }

    $gametypeSource = @(
        $(if (-not [string]::IsNullOrWhiteSpace($AppDataModRoot)) { Join-Path $AppDataModRoot "maps\mp\gametypes_zm" }),
        $(if (-not [string]::IsNullOrWhiteSpace($RepoModRoot)) { Join-Path $RepoModRoot "maps\mp\gametypes_zm" })
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and (Test-Path $_) } | Select-Object -First 1

    if ([string]::IsNullOrWhiteSpace($gametypeSource)) {
        return
    }

    $destPath = Join-Path $globalStorageRoot "raw\maps\mp\gametypes_zm"
    $destParent = Split-Path -Parent $destPath
    if (-not (Test-Path $destParent)) {
        New-Item -ItemType Directory -Path $destParent -Force | Out-Null
    }

    Copy-Item -LiteralPath $gametypeSource -Destination $destPath -Recurse -Force
    Write-Host "Restored active mod raw support: $destPath <- $gametypeSource"
}

function Read-FirstMatchFromFile {
    param(
        [string]$Path,
        [string]$Pattern
    )

    if ([string]::IsNullOrWhiteSpace($Path) -or [string]::IsNullOrWhiteSpace($Pattern) -or -not (Test-Path $Path)) {
        return ""
    }

    $content = Get-Content -Path $Path -Raw -ErrorAction SilentlyContinue
    if ([string]::IsNullOrWhiteSpace($content)) {
        return ""
    }

    $match = [regex]::Match($content, $Pattern, [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if (-not $match.Success -or $match.Groups.Count -lt 2) {
        return ""
    }

    return [string]$match.Groups[1].Value
}

function Reset-ModRuntimeLogs {
    param([string]$ModRoot)

    if ([string]::IsNullOrWhiteSpace($ModRoot) -or -not (Test-Path $ModRoot)) {
        return
    }

    foreach ($name in @("games_mp.log", "console_zm.log")) {
        foreach ($candidate in @(Get-ChildItem -Path $ModRoot -Filter ($name + "*") -File -Force -ErrorAction SilentlyContinue)) {
            Remove-Item -LiteralPath $candidate.FullName -Force -ErrorAction SilentlyContinue
            Write-Host "Removed stale mod log: $($candidate.FullName)"
        }
    }
}

function Write-DeployedModRuntimeSummary {
    param(
        [string]$ModRoot,
        [string]$Label = "ModRuntime"
    )

    if ([string]::IsNullOrWhiteSpace($ModRoot) -or -not (Test-Path $ModRoot)) {
        return
    }

    $scriptPath = Join-Path $ModRoot "scripts\mod_i_am_mod.gsc"
    if (-not (Test-Path $scriptPath)) {
        Write-Host "$Label script: missing ($scriptPath)" -ForegroundColor Yellow
        return
    }

    $buildTag = Read-FirstMatchFromFile -Path $scriptPath -Pattern 'return\s+"([^"]+)";' # fallback to first return
    $buildTagSpecific = Read-FirstMatchFromFile -Path $scriptPath -Pattern 'bo3_rev_build_tag\(\)[\s\S]*?return\s+"([^"]+)";'
    if (-not [string]::IsNullOrWhiteSpace($buildTagSpecific)) {
        $buildTag = $buildTagSpecific
    }
    $probeWeapon = Read-FirstMatchFromFile -Path $scriptPath -Pattern 'bo3_rev_probe_weapon\(\)[\s\S]*?return\s+"([^"]+)";'
    $shellEnabled = Read-FirstMatchFromFile -Path $scriptPath -Pattern 'bo3_rev_force_stock_shell_enabled\(\)[\s\S]*?return\s+([01]);'
    $forcedShell = Read-FirstMatchFromFile -Path $scriptPath -Pattern 'bo3_rev_forced_stock_shell\(\)[\s\S]*?return\s+"([^"]+)";'

    Write-Host "$Label script: $scriptPath"
    if (-not [string]::IsNullOrWhiteSpace($buildTag)) {
        Write-Host "BuildTag:     $buildTag"
    }
    if (-not [string]::IsNullOrWhiteSpace($probeWeapon)) {
        Write-Host "ProbeWeapon:  $probeWeapon"
    }
    if (-not [string]::IsNullOrWhiteSpace($shellEnabled)) {
        Write-Host "ShellForce:   $shellEnabled"
    }
    if (-not [string]::IsNullOrWhiteSpace($forcedShell)) {
        Write-Host "ForcedShell:  $forcedShell"
    }

    $zoneRoot = Join-Path $ModRoot "zone\all"
    $zoneFiles = @()
    if (Test-Path $zoneRoot) {
        $zoneFiles = @(
            Get-ChildItem -Path $zoneRoot -File -Force -ErrorAction SilentlyContinue |
                Where-Object { $_.Extension -in @(".ff", ".ipak") } |
                Sort-Object Name
        )
    }
    Write-Host ("{0}Zone:   {1} file(s) in {2}" -f $Label, $zoneFiles.Count, $zoneRoot)
    foreach ($file in $zoneFiles | Select-Object -First 8) {
        Write-Host ("  - {0} ({1} bytes)" -f $file.Name, $file.Length)
    }
}

function Write-PrelaunchRuntimeManifest {
    param(
        [string]$RepoRoot,
        [string]$GameRoot,
        [string]$PlutoniumRoot,
        [string]$ModName,
        [string]$ModeName,
        [string]$MapName,
        [string]$ExecCfgName,
        [string[]]$LaunchArgs
    )

    $captureScript = Join-Path $RepoRoot "tools\capture_runtime_dossier.ps1"
    if (-not (Test-Path $captureScript)) {
        return
    }

    $manifestRoot = Join-Path $RepoRoot "_build\launch_manifests"
    if (-not (Test-Path $manifestRoot)) {
        New-Item -ItemType Directory -Path $manifestRoot -Force | Out-Null
    }

    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $safeLabel = if ([string]::IsNullOrWhiteSpace($ModName)) { "stock" } else { $ModName }
    $outPath = Join-Path $manifestRoot ("{0}_{1}_prelaunch.json" -f $stamp, $safeLabel)

    $captureArgs = @(
        "-ExecutionPolicy", "Bypass",
        "-File", $captureScript,
        "-Label", ("prelaunch_{0}" -f $safeLabel),
        "-GameDir", $GameRoot,
        "-PlutoniumDir", $PlutoniumRoot,
        "-RepoDir", $RepoRoot,
        "-OutPath", $outPath,
        "-SkipLogs"
    )
    if (-not [string]::IsNullOrWhiteSpace($ModName)) {
        $captureArgs += @("-Mod", $ModName)
    }

    & powershell @captureArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Prelaunch runtime manifest capture failed with exit code $LASTEXITCODE"
        return
    }

    $manifest = Get-Content -Path $outPath -Raw | ConvertFrom-Json
    $launchMetadata = [pscustomobject]@{
        mode = $ModeName
        map = $MapName
        exec_cfg = $ExecCfgName
        launch_args = @($LaunchArgs)
    }
    $manifest | Add-Member -NotePropertyName "launch" -NotePropertyValue $launchMetadata -Force
    $manifest | ConvertTo-Json -Depth 10 | Set-Content -Path $outPath -Encoding UTF8
    Write-Host "Prelaunch manifest: $outPath"
}

$bootstrapper = Join-Path $PlutoniumDir "bin\plutonium-bootstrapper-win32.exe"
if (-not (Test-Path $bootstrapper)) {
    throw "Missing Plutonium bootstrapper: $bootstrapper"
}

$baseIpak = Join-Path $GameDir "zone\all\base.ipak"
if (-not (Test-Path $baseIpak)) {
    throw "Missing Black Ops 2 game path: $baseIpak"
}

if (-not $SkipZombieIpakRepair -and $Mode.ToUpperInvariant() -eq "ZM" -and $env:ROGUE_ENABLE_ZOMBIE_IPAK_REPAIR -eq "1") {
    $repairScript = Join-Path $RepoDir "tools\repair_t6_zm_install_ipaks.ps1"
    if (Test-Path $repairScript) {
        & powershell -ExecutionPolicy Bypass -File $repairScript -GameDir $GameDir
        if ($LASTEXITCODE -ne 0) {
            throw "Zombie ipak repair failed with exit code $LASTEXITCODE"
        }
    }
}

if (-not $SkipAssetValidation) {
    $expectedZombieRuntime = @(
        (Join-Path $GameDir "zone\all\patch_zm.ff"),
        (Join-Path $GameDir "zone\all\code_post_gfx_zm.ff"),
        (Join-Path $GameDir "zone\all\common_zm.ff"),
        (Join-Path $GameDir "zone\all\zm_transit.ff"),
        (Join-Path $GameDir "zone\all\so_zsurvival_zm_transit.ff")
    )
    $missingZombieRuntime = @($expectedZombieRuntime | Where-Object { -not (Test-Path $_) })
    if ($missingZombieRuntime.Count -gt 0) {
        Write-Warning ("Expected core zombie runtime files missing from install: {0}" -f ($missingZombieRuntime -join ", "))
    }

}

if (-not $SkipLaunchHygiene -and (Test-Path $globalStorageRoot)) {
    Move-PathToLaunchQuarantine -SourcePath (Join-Path $globalStorageRoot "raw") -Label "global raw overrides"
    Move-PathToLaunchQuarantine -SourcePath (Join-Path $globalStorageRoot "maps") -Label "global maps overrides"
    Move-PathToLaunchQuarantine -SourcePath (Join-Path $globalStorageRoot "scripts") -Label "global scripts overrides"
    Move-PathToLaunchQuarantine -SourcePath (Join-Path $globalStorageRoot "zone") -Label "global zone overrides"
    Move-PathToLaunchQuarantine -SourcePath (Join-Path $globalStorageRoot "ui") -Label "global ui overrides"
    Move-PathToLaunchQuarantine -SourcePath (Join-Path $globalStorageRoot "ui_mp") -Label "global ui_mp overrides"
    Move-PathToLaunchQuarantine -SourcePath (Join-Path $globalStorageRoot "images") -Label "global image overrides"
    Move-PathToLaunchQuarantine -SourcePath (Join-Path $globalStorageRoot "ffprobe_autorun.cfg") -Label "global autorun cfg"
    Restore-SanitizedRawSupport
    if (-not $modName) {
        Move-PathToLaunchQuarantine -SourcePath (Join-Path $globalStorageRoot "players\ffprobe_autorun.cfg") -Label "player autorun cfg"
    }
}

$appDataModRoot = if ($modName) { Join-Path $PlutoniumDir ("storage\t6\mods\{0}" -f $modName) } else { "" }
$repoModRoot = if ($modName) { Join-Path $RepoDir ("mods\{0}" -f $modName) } else { "" }
if (-not $SkipLaunchHygiene -and $modName) {
    Restore-ActiveModRawSupport -AppDataModRoot $appDataModRoot -RepoModRoot $repoModRoot
}
$skipUiOverridesEnv = $env:ROGUE_SKIP_UI_OVERRIDES
$skipUiOverridesEffective = $SkipUiOverrides -or ($skipUiOverridesEnv -and $skipUiOverridesEnv -notin @("0", "false", "False"))
$allowServerSpawnerSyncEnv = $env:ROGUE_ALLOW_SERVER_SPAWNER_SYNC
$allowServerSpawnerSync = $allowServerSpawnerSyncEnv -and $allowServerSpawnerSyncEnv -in @("1", "true", "True")
$uiOverrideEntries = @()
$staleCarrierMapScriptFiles = @()
$uiOverrideEntries = if ($modName -and -not $skipUiOverridesEffective) {
    @(
        @{
            Source = (Join-Path $repoModRoot "ui\t6\mainlobby.lua")
            Destination = (Join-Path $appDataModRoot "ui\t6\mainlobby.lua")
        },
        @{
            Source = (Join-Path $repoModRoot "ui_mp\t6\mainmenu.lua")
            Destination = (Join-Path $appDataModRoot "ui_mp\t6\mainmenu.lua")
        }
    )
} else {
    @()
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
$staleCarrierMapScriptFiles = if ($modName) {
    @(
        (Join-Path $repoModRoot "maps\mp\zm_transit.gsc"),
        (Join-Path $repoModRoot "maps\mp\zm_cosmodrome_standard.gsc"),
        (Join-Path $appDataModRoot "maps\mp\zm_transit.gsc"),
        (Join-Path $appDataModRoot "maps\mp\zm_cosmodrome_standard.gsc")
    )
} else {
    @()
}
$staleServerScriptFiles = if ($modName) {
    if ($allowServerSpawnerSync) {
        @(
            (Join-Path $appDataModRoot "scripts\mp\zombies\_zm_spawner.gsc")
        )
    } else {
        @(
            (Join-Path $appDataModRoot "maps\mp\zombies\_zm_spawner.gsc"),
            (Join-Path $appDataModRoot "scripts\mp\zombies\_zm_spawner.gsc")
        )
    }
} else {
    @()
}

foreach ($uiEntry in $uiOverrideEntries) {
    $src = [string]$uiEntry.Source
    $dst = [string]$uiEntry.Destination
    if ([string]::IsNullOrWhiteSpace($dst)) {
        continue
    }
    if (-not [string]::IsNullOrWhiteSpace($src) -and (Test-Path $src)) {
        $dstDir = Split-Path -Parent $dst
        if (-not (Test-Path $dstDir)) {
            New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
        }
        Copy-Item -Path $src -Destination $dst -Force
        Write-Host "Synced UI override: $dst"
    } elseif (Test-Path $dst) {
        Remove-Item -Path $dst -Force
        Write-Host "Removed stale UI override: $dst"
    }
}

$mpClientscriptRoot = if ($repoModRoot) { Join-Path $repoModRoot "clientscripts\mp" } else { "" }
$mpClientscriptDstRoot = if ($appDataModRoot) { Join-Path $appDataModRoot "clientscripts\mp" } else { "" }
if ($modName -and -not (Test-Path $mpClientscriptDstRoot)) {
    New-Item -ItemType Directory -Path $mpClientscriptDstRoot -Force | Out-Null
}

if ($mpClientscriptDstRoot) {
    foreach ($staleClientscriptName in $staleMpClientscriptFiles) {
        $stalePath = Join-Path $mpClientscriptDstRoot $staleClientscriptName
        if ($stalePath -and (Test-Path $stalePath)) {
            Remove-Item -Path $stalePath -Force
            Write-Host "Removed stale MP clientscript: $stalePath"
        }
    }
}

foreach ($stalePath in $staleCarrierMapScriptFiles) {
    if ($stalePath -and (Test-Path $stalePath)) {
        Remove-Item -Path $stalePath -Force
        Write-Host "Removed stale carrier map script: $stalePath"
    }
}

foreach ($stalePath in $staleServerScriptFiles) {
    if ($stalePath -and (Test-Path $stalePath)) {
        Remove-Item -Path $stalePath -Force
        Write-Host "Removed stale server script override: $stalePath"
    }
}

if ($allowServerSpawnerSync -and $modName -and $repoModRoot) {
    $serverScriptSrc = ""
    foreach ($candidate in @(
        (Join-Path $repoModRoot "scripts\mp\zombies\_zm_spawner.gsc"),
        (Join-Path $repoModRoot "maps\mp\zombies\_zm_spawner.gsc")
    )) {
        if (Test-Path $candidate) {
            $serverScriptSrc = $candidate
            break
        }
    }

    foreach ($serverScriptDst in @(
        (Join-Path $appDataModRoot "maps\mp\zombies\_zm_spawner.gsc")
    )) {
        if ($serverScriptSrc) {
            $serverScriptDstDir = Split-Path -Parent $serverScriptDst
            if (-not (Test-Path $serverScriptDstDir)) {
                New-Item -ItemType Directory -Path $serverScriptDstDir -Force | Out-Null
            }
            Copy-Item -Path $serverScriptSrc -Destination $serverScriptDst -Force
            Write-Host "Synced server script override: $serverScriptDst"
        }
    }
}

if ($modName -and (Test-Path $mpClientscriptRoot)) {
    if (-not (Test-Path $mpClientscriptDstRoot)) {
        New-Item -ItemType Directory -Path $mpClientscriptDstRoot -Force | Out-Null
    }
    foreach ($clientscriptName in @("_vehicle.csc", "zm_transit.csc")) {
        $src = Join-Path $mpClientscriptRoot $clientscriptName
        if (Test-Path $src) {
            $dst = Join-Path $mpClientscriptDstRoot $clientscriptName
            Copy-Item -Path $src -Destination $dst -Force
            Write-Host "Synced MP clientscript override: $dst"
        }
    }
}

if ($modName) {
    $servantFxSrc = Join-Path $repoModRoot "clientscripts\mp\zombies\_bo3_rev_servant_fx_v3.csc"
    $servantFxDst = Join-Path $appDataModRoot "clientscripts\mp\zombies\_bo3_rev_servant_fx_v3.csc"
    if (Test-Path $servantFxSrc) {
        $servantFxDstDir = Split-Path -Parent $servantFxDst
        if (-not (Test-Path $servantFxDstDir)) {
            New-Item -ItemType Directory -Path $servantFxDstDir -Force | Out-Null
        }
        Copy-Item -Path $servantFxSrc -Destination $servantFxDst -Force
        Write-Host "Synced servant FX clientscript override: $servantFxDst"
    }
}

if (-not $SkipLaunchHygiene -and $modName) {
    Reset-ModRuntimeLogs -ModRoot $appDataModRoot
}

$modeId = switch ($Mode.ToUpperInvariant()) {
    "ZM" { "t6zm" }
    "MP" { "t6mp" }
    default { throw "Unsupported mode '$Mode'. Use ZM or MP." }
}

if ($MonitorIndex -gt 0) {
    Reset-LaunchMonitorWindowCoords -PlayersRoot (Join-Path $PlutoniumDir "storage\t6\players") -Mode $Mode -ModName $modName
}

$args = @(
    $modeId
    $GameDir
    "+name"
    $Name
    "-lan"
)

if ($modName) {
    $args += @("+set", "fs_game", "mods/$modName", "+seta", "fs_game", "mods/$modName")
} else {
    $args += @("+set", "fs_game", '""', "+seta", "fs_game", '""')
}

if ($UiGametype -and $UiGametype.Trim().Length -gt 0) {
    $args += @("+set", "ui_gametype", $UiGametype)
}

if ($UiZmGamemodeGroup -and $UiZmGamemodeGroup.Trim().Length -gt 0) {
    $args += @("+set", "ui_zm_gamemodegroup", $UiZmGamemodeGroup)
}

if ($UiMapStartLocation -and $UiMapStartLocation.Trim().Length -gt 0) {
    $args += @("+set", "ui_zm_mapstartlocation", $UiMapStartLocation)
}

if ($UiMapName -and $UiMapName.Trim().Length -gt 0) {
    $args += @("+set", "ui_mapname", $UiMapName)
}

if ($GGametype -and $GGametype.Trim().Length -gt 0) {
    $args += @("+set", "g_gametype", $GGametype)
}

if ($ExecCfg -and $ExecCfg.Trim().Length -gt 0) {
    $args += @("+exec", $ExecCfg)
}

if (-not $MenuOnly -and $Map -and $Map.Trim().Length -gt 0) {
    $args += @("+map", $Map)
}

foreach ($cmd in $ExtraCommands) {
    if (-not $cmd) {
        continue
    }
    $trimmed = $cmd.Trim()
    if ($trimmed.Length -eq 0) {
        continue
    }
    if ($trimmed.StartsWith("+")) {
        $parts = $trimmed.Split(" ", 2)
        $args += $parts[0]
        if ($parts.Length -gt 1 -and $parts[1].Trim().Length -gt 0) {
            $args += $parts[1].Trim()
        }
    } else {
        $args += @("+$trimmed")
    }
}

Write-Host "Launching offline Plutonium..." -ForegroundColor Cyan
Write-Host "Bootstrapper: $bootstrapper"
Write-Host "Mode:        $modeId"
Write-Host "RepoDir:     $RepoDir"
Write-Host "GameDir:     $GameDir"
Write-Host "Name:        $Name"
Write-Host "LAN:         enabled"
if ($modName) {
    Write-Host "Mod:         mods/$modName"
    Write-DeployedModRuntimeSummary -ModRoot $appDataModRoot -Label "AppData"
    $gameModRoot = Join-Path $GameDir ("mods\{0}" -f $modName)
    Write-DeployedModRuntimeSummary -ModRoot $gameModRoot -Label "Game"
    $repoZoneRoot = Join-Path $repoModRoot "zone\all"
    $gameZoneRoot = Join-Path $gameModRoot "zone\all"
    $repoZoneFiles = @()
    $gameZoneFiles = @()
    if (Test-Path $repoZoneRoot) {
        $repoZoneFiles = @(Get-ChildItem -Path $repoZoneRoot -File -Force -ErrorAction SilentlyContinue | Where-Object { $_.Extension -in @(".ff", ".ipak") })
    }
    if (Test-Path $gameZoneRoot) {
        $gameZoneFiles = @(Get-ChildItem -Path $gameZoneRoot -File -Force -ErrorAction SilentlyContinue | Where-Object { $_.Extension -in @(".ff", ".ipak") })
    }
    Write-Host ("RepoZone:     {0} file(s) in {1}" -f $repoZoneFiles.Count, $repoZoneRoot)
    Write-Host ("GameZone:     {0} file(s) in {1}" -f $gameZoneFiles.Count, $gameZoneRoot)
    if ((-not (Test-Path (Join-Path $appDataModRoot "scripts\\mod_i_am_mod.gsc"))) -and $gameZoneFiles.Count -gt 0) {
        Write-Warning "AppData mod content is missing, but GameDir\\mods\\$modName exists. This launch will resolve against the game-runtime mod folder and can easily load a stale build."
    }
    if ($repoZoneFiles.Count -eq 0 -and $gameZoneFiles.Count -eq 0 -and -not (Test-Path (Join-Path $appDataModRoot "zone\all\so_zsurvival_zm_transit.ff"))) {
        Write-Warning "No deployed mod-zone fastfiles are present for this mod. This launch will run loose scripts/UI against stock map/survival content, not a coherent custom runtime."
    }
} else {
    Write-Host "Mod:         <none>"
}
if ($UiGametype -and $UiGametype.Trim().Length -gt 0) {
    Write-Host "Gametype:    $UiGametype"
}
if ($UiZmGamemodeGroup -and $UiZmGamemodeGroup.Trim().Length -gt 0) {
    Write-Host "GameGroup:   $UiZmGamemodeGroup"
}
if ($UiMapStartLocation -and $UiMapStartLocation.Trim().Length -gt 0) {
    Write-Host "Location:    $UiMapStartLocation"
}
if ($UiMapName -and $UiMapName.Trim().Length -gt 0) {
    Write-Host "UiMapName:   $UiMapName"
}
if ($GGametype -and $GGametype.Trim().Length -gt 0) {
    Write-Host "g_gametype:  $GGametype"
}
if ($MonitorIndex -gt 0) {
    $targetScreen = Get-TargetScreen -RequestedMonitorIndex $MonitorIndex
    Write-Host "Monitor:     $MonitorIndex ($($targetScreen.DeviceName))"
}
if ($ExecCfg -and $ExecCfg.Trim().Length -gt 0) {
    Write-Host "ExecCfg:     $ExecCfg"
}
if (-not $MenuOnly -and $Map -and $Map.Trim().Length -gt 0) {
    Write-Host "Map:         $Map"
}
if ($MenuOnly) {
    Write-Host "MenuOnly:    true"
}
if ($ExtraCommands -and $ExtraCommands.Count -gt 0) {
    Write-Host "Extra:       $($ExtraCommands -join ' | ')"
}

if ($DryRun) {
    Write-Host "CommandLine:  `"$bootstrapper`" $($args -join ' ')" -ForegroundColor Yellow
    return
}

Write-PrelaunchRuntimeManifest -RepoRoot $RepoDir -GameRoot $GameDir -PlutoniumRoot $PlutoniumDir -ModName $modName -ModeName $modeId -MapName $Map -ExecCfgName $ExecCfg -LaunchArgs $args

$launchStartTime = Get-Date
$launchProcess = Start-Process -FilePath $bootstrapper -ArgumentList $args -WorkingDirectory $PlutoniumDir -PassThru
Move-LaunchWindowToMonitor -PrimaryPid $launchProcess.Id -LaunchStartTime $launchStartTime -RequestedMonitorIndex $MonitorIndex -TimeoutSec $WindowMoveTimeoutSec -FastPollMs $WindowMoveFastPollMs -SlowPollMs $WindowMoveSlowPollMs -FastPhaseSec $WindowMoveFastPhaseSec
