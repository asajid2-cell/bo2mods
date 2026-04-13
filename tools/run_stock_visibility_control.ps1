param(
    [string]$Weapon = "mg08_zm",
    [string]$StarterWeapon = "m1911_zm",
    [string]$Mod = "bo3_rev",
    [string]$BuildRootName = "",
    [string]$AnimProbePhase = "",
    [switch]$Launch,
    [switch]$UseStockSurvivalZone,
    [switch]$UseOfficialTransitClientscript,
    [switch]$ForceStockShell,
    [string]$ForcedStockShell = "c_zom_engineer_viewhands",
    [switch]$CaptureScreenshot,
    [int]$CaptureDelaySec = 30,
    [int]$MarkerTimeoutSec = 45,
    [switch]$KillAfterCapture,
    [string]$Map = "zm_transit",
    [string]$UiMapName = "zm_transit",
    [string]$UiGametype = "zclassic",
    [string]$UiZmGamemodeGroup = "zsurvival",
    [string]$UiMapStartLocation = "town",
    [string]$GGametype = "zclassic",
    [string]$Name = "offline_player",
    [string]$GameDir = "",
    [string]$PlutoniumDir = "C:\Users\Ahmed\AppData\Local\Plutonium",
    [ValidateRange(0, 16)]
    [int]$MonitorIndex = 2
)

$ErrorActionPreference = "Stop"

$modName = if ([string]::IsNullOrWhiteSpace($Mod)) { "bo3_rev" } else { $Mod.Trim() }
if ([string]::IsNullOrWhiteSpace($BuildRootName)) {
    if ($modName -eq "bo3_rev") {
        $BuildRootName = "bo3_rev_idg_probe"
    }
    else {
        $BuildRootName = "{0}_idg_probe" -f $modName
    }
}

$root = Split-Path -Parent $PSScriptRoot
$forceStockShellEnabled = $ForceStockShell.IsPresent
if ([string]::IsNullOrWhiteSpace($GameDir)) {
    $GameDir = $root
}
$buildScript = Join-Path $root "_build\build_bo3_rev_idg_probe.py"
$restartScript = Join-Path $root "tools\restart_t6_probe_cycle.ps1"
$repoScriptPath = Join-Path $root ("mods\{0}\scripts\mod_i_am_mod.gsc" -f $modName)
$workScriptPath = Join-Path $root ("_build\{0}\scripts\mod_i_am_mod.gsc" -f $BuildRootName)
$appDataScriptPath = "C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\mods\$modName\scripts\mod_i_am_mod.gsc"
$repoTransitClientPath = Join-Path $root ("mods\{0}\clientscripts\mp\zm_transit.csc" -f $modName)
$workTransitClientPath = Join-Path $root ("_build\{0}\clientscripts\mp\zm_transit.csc" -f $BuildRootName)
$appDataTransitClientPath = "C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\mods\$modName\clientscripts\mp\zm_transit.csc"
$officialTransitClientPath = Join-Path $root "t6-scripts-official\ZM1\Maps\Tranzit\clientscripts\mp\zm_transit.csc"
$runtimeDossierScript = Join-Path $root "tools\capture_runtime_dossier.ps1"
$buildReportPath = Join-Path $root ("_build\{0}\build_report.json" -f $BuildRootName)
$archiveRoot = Join-Path $root "_build\visibility_live"
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$runDir = Join-Path $archiveRoot ("{0}_{1}_stock_control" -f $stamp, $modName)
$storageRoot = Join-Path $PlutoniumDir "storage\t6"
$gamesLog = "C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\mods\$modName\games_mp.log"
$consoleLog = "C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\mods\$modName\console_zm.log"

foreach ($required in @($buildScript, $restartScript, $runtimeDossierScript)) {
    if (-not (Test-Path $required)) {
        throw "Missing required path: $required"
    }
}

New-Item -ItemType Directory -Path $runDir -Force | Out-Null
$repoInputQuarantineRoot = Join-Path $runDir "repo_mod_quarantine"
$runtimeDlcQuarantineRoot = Join-Path $runDir "runtime_dlc_quarantine"
$dlcLoadFfEntries = @(
    @{ RelativePath = "zone\\all\\dlczm0_load_zm.ff"; Label = "dlczm0_load_zm_ff" },
    @{ RelativePath = "zone\\all\\dlc1_load_zm.ff"; Label = "dlc1_load_zm_ff" },
    @{ RelativePath = "zone\\all\\dlc2_load_zm.ff"; Label = "dlc2_load_zm_ff" },
    @{ RelativePath = "zone\\all\\dlc3_load_zm.ff"; Label = "dlc3_load_zm_ff" },
    @{ RelativePath = "zone\\all\\dlc4_load_zm.ff"; Label = "dlc4_load_zm_ff" },
    @{ RelativePath = "zone\\all\\dlc0dd_load_zm.ff"; Label = "dlc0dd_load_zm_ff" },
    @{ RelativePath = "zone\\all\\seasonpass_load_zm.ff"; Label = "seasonpass_load_zm_ff" },
    @{ RelativePath = "zone\\english\\en_dlczm0_load_zm.ff"; Label = "en_dlczm0_load_zm_ff" },
    @{ RelativePath = "zone\\english\\en_dlc1_load_zm.ff"; Label = "en_dlc1_load_zm_ff" },
    @{ RelativePath = "zone\\english\\en_dlc2_load_zm.ff"; Label = "en_dlc2_load_zm_ff" },
    @{ RelativePath = "zone\\english\\en_dlc3_load_zm.ff"; Label = "en_dlc3_load_zm_ff" },
    @{ RelativePath = "zone\\english\\en_dlc4_load_zm.ff"; Label = "en_dlc4_load_zm_ff" },
    @{ RelativePath = "zone\\english\\en_dlc0dd_load_zm.ff"; Label = "en_dlc0dd_load_zm_ff" },
    @{ RelativePath = "zone\\english\\en_seasonpass_load_zm.ff"; Label = "en_seasonpass_load_zm_ff" }
)

function Set-StockControlEnv {
    param(
        [string]$Name,
        [string]$Value
    )

    [System.Environment]::SetEnvironmentVariable($Name, $Value, "Process")
    Set-Item -Path ("Env:{0}" -f $Name) -Value $Value
}

function Copy-IfExists {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path $Source)) {
        return
    }

    $destDir = Split-Path -Parent $Destination
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }

    Copy-Item -LiteralPath $Source -Destination $Destination -Force
}

function Move-PathIfExists {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path $Source)) {
        return $false
    }

    $destDir = Split-Path -Parent $Destination
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }

    Move-Item -LiteralPath $Source -Destination $Destination -Force
    return $true
}

function Quarantine-PathIfExists {
    param(
        [string]$Source,
        [string]$QuarantineRoot,
        [string]$Label
    )

    if (-not (Test-Path $Source)) {
        return $null
    }

    $destination = Join-Path $QuarantineRoot $Label
    $moved = Move-PathIfExists -Source $Source -Destination $destination
    if (-not $moved) {
        return $null
    }

    return [ordered]@{
        source = $Source
        quarantine = $destination
        label = $Label
    }
}

function Restore-QuarantinedPaths {
    param([object[]]$Records)

    foreach ($record in @($Records)) {
        if ($null -eq $record) {
            continue
        }

        $quarantine = [string]$record.quarantine
        $source = [string]$record.source
        if ([string]::IsNullOrWhiteSpace($quarantine) -or [string]::IsNullOrWhiteSpace($source)) {
            continue
        }

        if (-not (Test-Path $quarantine)) {
            continue
        }

        $restored = Move-PathIfExists -Source $quarantine -Destination $source
        if ($restored) {
            Write-Host "Restored runtime DLC load FF -> $source"
        }
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

function Get-LogSnapshot {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return @{
            Path = $Path
            Exists = $false
            Length = 0
        }
    }

    return @{
        Path = $Path
        Exists = $true
        Length = (Get-Item $Path).Length
    }
}

function Get-LogDeltaText {
    param([hashtable]$Snapshot)

    if (-not (Test-Path $Snapshot.Path)) {
        return ""
    }

    $stream = $null
    try {
        $stream = New-Object System.IO.FileStream($Snapshot.Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
        $startOffset = 0
        if ($Snapshot.Exists) {
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

function Wait-ForLogMarker {
    param(
        [hashtable[]]$Snapshots,
        [string[]]$Markers,
        [int]$TimeoutSec
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        foreach ($snapshot in $Snapshots) {
            $text = Get-LogDeltaText -Snapshot $snapshot
            if ([string]::IsNullOrWhiteSpace($text)) {
                continue
            }

            foreach ($marker in $Markers) {
                if ($text.Contains($marker)) {
                    return $marker
                }
            }
        }

        Start-Sleep -Milliseconds 500
    }

    return ""
}

function Capture-PrimaryScreen {
    param([string]$Path)

    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    $bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
    $bitmap = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.CopyFromScreen($bounds.X, $bounds.Y, 0, 0, $bitmap.Size)
        $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

function Capture-GameWindow {
    param(
        [string]$Path,
        [int]$TimeoutSec = 15
    )

    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    if (-not ("StockVisibility.NativeMethods" -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;

namespace StockVisibility
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

        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        public static extern bool IsWindowVisible(IntPtr hWnd);

        [DllImport("user32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        public static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);

        [DllImport("user32.dll")]
        public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
    }
}
'@
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $candidateNames = @("plutonium-bootstrapper-win32", "plutonium-bootstrapper-win64", "BlackOps2")
    $selected = $null

    while ((Get-Date) -lt $deadline -and $null -eq $selected) {
        $candidates = @{}
        foreach ($name in $candidateNames) {
            foreach ($proc in @(Get-Process -Name $name -ErrorAction SilentlyContinue)) {
                $candidates[[uint32]$proc.Id] = $proc
            }
        }

        $windowCandidates = New-Object System.Collections.Generic.List[object]
        $callback = [StockVisibility.NativeMethods+EnumWindowsProc]{
            param($handle, $lParam)

            if (-not [StockVisibility.NativeMethods]::IsWindowVisible($handle)) {
                return $true
            }

            [uint32]$windowProcessId = 0
            [void][StockVisibility.NativeMethods]::GetWindowThreadProcessId($handle, [ref]$windowProcessId)
            if (-not $candidates.ContainsKey($windowProcessId)) {
                return $true
            }

            $rect = New-Object StockVisibility.RECT
            if (-not [StockVisibility.NativeMethods]::GetWindowRect($handle, [ref]$rect)) {
                return $true
            }

            $width = [Math]::Max(0, $rect.Right - $rect.Left)
            $height = [Math]::Max(0, $rect.Bottom - $rect.Top)
            if ($width -lt 200 -or $height -lt 150) {
                return $true
            }

            $titleBuilder = New-Object System.Text.StringBuilder 512
            [void][StockVisibility.NativeMethods]::GetWindowText($handle, $titleBuilder, $titleBuilder.Capacity)
            $classBuilder = New-Object System.Text.StringBuilder 256
            [void][StockVisibility.NativeMethods]::GetClassName($handle, $classBuilder, $classBuilder.Capacity)
            $title = $titleBuilder.ToString()
            $className = $classBuilder.ToString()
            $process = $candidates[$windowProcessId]

            $priority = 0
            if ($className -eq "CoDBlackOps") { $priority += 1000 }
            if ($title -like "Plutonium T6 Zombies*") { $priority += 250 }
            if ($className -eq "ConsoleWindowClass") { $priority -= 1000 }

            $windowCandidates.Add([pscustomobject]@{
                ProcessName = $process.ProcessName
                ProcessId = $process.Id
                Handle = $handle
                Left = $rect.Left
                Top = $rect.Top
                Width = $width
                Height = $height
                Area = [int64]$width * [int64]$height
                Priority = $priority
                Title = $title
                ClassName = $className
            }) | Out-Null

            return $true
        }

        [void][StockVisibility.NativeMethods]::EnumWindows($callback, [IntPtr]::Zero)

        $selected = $windowCandidates |
            Sort-Object -Property @(
                @{ Expression = "Priority"; Descending = $true },
                @{ Expression = "Area"; Descending = $true }
            ) |
            Select-Object -First 1
        if ($null -eq $selected) {
            Start-Sleep -Milliseconds 500
        }
    }

    if ($null -eq $selected) {
        Capture-PrimaryScreen -Path $Path
        return [ordered]@{
            method = "virtual_screen_fallback"
            process_name = ""
            process_id = 0
            left = 0
            top = 0
            width = 0
            height = 0
        }
    }

    $bitmap = New-Object System.Drawing.Bitmap($selected.Width, $selected.Height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.CopyFromScreen($selected.Left, $selected.Top, 0, 0, $bitmap.Size)
        $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }

    return [ordered]@{
        method = "game_window_rect"
        process_name = $selected.ProcessName
        process_id = $selected.ProcessId
        title = $selected.Title
        class_name = $selected.ClassName
        left = $selected.Left
        top = $selected.Top
        width = $selected.Width
        height = $selected.Height
    }
}

function Get-FileRecord {
    param([string]$Path)

    $exists = -not [string]::IsNullOrWhiteSpace($Path) -and (Test-Path $Path)
    $size = 0
    $sha256 = ""
    $read_error = ""
    if ($exists) {
        try {
            $item = Get-Item -LiteralPath $Path
            $size = [int64]$item.Length
            $sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
        }
        catch {
            $read_error = $_.Exception.Message
        }
    }

    return [ordered]@{
        path = $Path
        exists = $exists
        size = $size
        sha256 = $sha256
        read_error = $read_error
    }
}

function Capture-ChangedLogFiles {
    param(
        [string]$Root,
        [string]$DestinationRoot,
        [datetime]$NotBefore
    )

    $records = @()
    if (-not (Test-Path $Root)) {
        return $records
    }

    $captureRoot = Join-Path $DestinationRoot "log_capture"
    New-Item -ItemType Directory -Path $captureRoot -Force | Out-Null

    $rootWithSlash = $Root.TrimEnd('\') + '\'
    $logs = Get-ChildItem -Path $Root -Recurse -File -Include *.log -ErrorAction SilentlyContinue |
        Where-Object {
            $_.LastWriteTime -ge $NotBefore -and
            $_.FullName -notlike "*\\_runtime_quarantine\\*" -and
            $_.FullName -notlike "*\\_manual_quarantine\\*"
        }

    foreach ($log in $logs) {
        $relativePath = $log.FullName
        if ($relativePath.StartsWith($rootWithSlash, [System.StringComparison]::OrdinalIgnoreCase)) {
            $relativePath = $relativePath.Substring($rootWithSlash.Length)
        }

        $destination = Join-Path $captureRoot $relativePath
        $destDir = Split-Path -Parent $destination
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }

        Copy-Item -LiteralPath $log.FullName -Destination $destination -Force
        $records += [ordered]@{
            source = $log.FullName
            relative_path = $relativePath
            copied_to = $destination
            length = $log.Length
            last_write_time = $log.LastWriteTime.ToString("o")
        }
    }

    return $records
}

function Get-GscReturnValue {
    param(
        [string]$Text,
        [string]$FunctionName
    )

    if ([string]::IsNullOrWhiteSpace($Text) -or [string]::IsNullOrWhiteSpace($FunctionName)) {
        return $null
    }

    $pattern = "(?ms)\b{0}\s*\(\)\s*\{{\s*return\s+([^;]+);" -f [regex]::Escape($FunctionName)
    $match = [regex]::Match($Text, $pattern)
    if (-not $match.Success) {
        return $null
    }

    $value = $match.Groups[1].Value.Trim()
    if ($value.StartsWith('"') -and $value.EndsWith('"')) {
        return $value.Trim('"')
    }

    return $value
}

function Get-ModScriptSummary {
    param([string]$Path)

    $record = Get-FileRecord -Path $Path
    if (-not $record.exists) {
        return $record
    }

    $text = Get-SharedText -Path $Path
    $record["build_tag"] = Get-GscReturnValue -Text $text -FunctionName "bo3_rev_build_tag"
    $record["probe_weapon"] = Get-GscReturnValue -Text $text -FunctionName "bo3_rev_probe_weapon"
    $record["starter_weapon"] = Get-GscReturnValue -Text $text -FunctionName "bo3_rev_starter_weapon"
    $record["probe_mode"] = Get-GscReturnValue -Text $text -FunctionName "bo3_rev_probe_mode"
    $record["native_probe_mode"] = Get-GscReturnValue -Text $text -FunctionName "bo3_rev_native_probe_mode"
    $record["probe_model_asset"] = Get-GscReturnValue -Text $text -FunctionName "bo3_rev_probe_model_asset"
    $record["probe_world_model_asset"] = Get-GscReturnValue -Text $text -FunctionName "bo3_rev_probe_world_model_asset"
    $record["anim_phase"] = Get-GscReturnValue -Text $text -FunctionName "bo3_rev_anim_phase"
    $record["run_label"] = Get-GscReturnValue -Text $text -FunctionName "bo3_rev_run_label"
    $record["visibility_recovery_enabled"] = Get-GscReturnValue -Text $text -FunctionName "bo3_rev_visibility_recovery_enabled"
    $record["force_stock_shell"] = Get-GscReturnValue -Text $text -FunctionName "bo3_rev_force_stock_shell_enabled"
    $record["forced_stock_shell"] = Get-GscReturnValue -Text $text -FunctionName "bo3_rev_forced_stock_shell"
    return $record
}

function Get-BuildReportSummary {
    param([string]$Path)

    $record = Get-FileRecord -Path $Path
    if (-not $record.exists) {
        return $record
    }

    $json = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    $record["build_tag"] = $json.build_tag
    $record["weapon_probe"] = [ordered]@{
        asset = $json.weapon_probe.asset
        source_asset = $json.weapon_probe.source_asset
        starter_weapon = $json.weapon_probe.starter_weapon
        gun_model_mode = $json.weapon_probe.gun_model_mode
        force_stock_shell = $json.weapon_probe.force_stock_shell
        forced_stock_shell = $json.weapon_probe.forced_stock_shell
        run_label = $json.weapon_probe.run_label
    }
    $record["staged_fields"] = $json.weapon_probe.staged_fields
    $record["first_person_composition"] = [ordered]@{
        active_components = $json.first_person_composition.active_components
        predicted_totals = $json.first_person_composition.predicted_totals
    }
    $record["runtime_outputs"] = [ordered]@{
        runtime_ff = $json.outputs.runtime_ff
        runtime_ipak = $json.outputs.runtime_ipak
        mod_load_ff = $json.outputs.mod_load_ff
        mod_patch_ff = $json.outputs.mod_patch_ff
    }
    return $record
}

function Get-LogSignalSummary {
    param(
        [string]$Path,
        [string]$BuildTag
    )

    $record = Get-FileRecord -Path $Path
    if (-not $record.exists) {
        return $record
    }

    $patterns = @(
        "\[bo3_rev\]\[(start|connect|grant|idle_begin|first_raise_begin)\]",
        "stage=visibility_recover_(begin|sample|success|fail)"
    )
    if (-not [string]::IsNullOrWhiteSpace($BuildTag)) {
        $patterns = @([regex]::Escape($BuildTag)) + $patterns
    }

    $matches = @(Select-String -Path $Path -Pattern $patterns -AllMatches -ErrorAction SilentlyContinue | Select-Object -Last 60)
    $record["signals"] = @($matches | ForEach-Object { $_.Line.Trim() })
    return $record
}

$forceUniqueProbeAsset = [System.Environment]::GetEnvironmentVariable("ROGUE_FORCE_UNIQUE_PROBE_ASSET", "Process") -eq "1"
$runtimeProbeWeaponAsset = $Weapon
if ($forceUniqueProbeAsset) {
    $sanitizedWeaponAsset = (($Weapon -replace '[^A-Za-z0-9_]', '_').Trim('_'))
    if ([string]::IsNullOrWhiteSpace($sanitizedWeaponAsset)) {
        $sanitizedWeaponAsset = "probe_weapon"
    }
    $runtimeProbeWeaponAsset = ("bo3r_probe_{0}" -f $sanitizedWeaponAsset.ToLowerInvariant())
}

$effectiveAnimProbePhase = $AnimProbePhase
if ([string]::IsNullOrWhiteSpace($effectiveAnimProbePhase)) {
    $effectiveAnimProbePhase = [System.Environment]::GetEnvironmentVariable("ROGUE_ANIM_PROBE_PHASE", "Process")
}
if ([string]::IsNullOrWhiteSpace($effectiveAnimProbePhase)) {
    $effectiveAnimProbePhase = "off"
}

Set-StockControlEnv -Name "ROGUE_PROBE_SHELL" -Value $Weapon
Set-StockControlEnv -Name "ROGUE_STARTER_WEAPON" -Value $StarterWeapon
Set-StockControlEnv -Name "ROGUE_SOURCE_WEAPON_ASSET" -Value $Weapon
Set-StockControlEnv -Name "ROGUE_WEAPON_ASSET" -Value $runtimeProbeWeaponAsset
Set-StockControlEnv -Name "ROGUE_MOD_NAME" -Value $modName
Set-StockControlEnv -Name "ROGUE_BUILD_ROOT_NAME" -Value $BuildRootName
Set-StockControlEnv -Name "ROGUE_GUN_MODEL_MODE" -Value "base"
Set-StockControlEnv -Name "ROGUE_USE_BO3_IDG_ANIMS" -Value "0"
Set-StockControlEnv -Name "ROGUE_BO3_ANIM_STAGE" -Value "off"
Set-StockControlEnv -Name "ROGUE_USE_REBAKED_BO3_XANIMS" -Value "0"
Set-StockControlEnv -Name "ROGUE_BO3_ANIM_RUNTIME_BACKEND" -Value "semantic_names"
Set-StockControlEnv -Name "ROGUE_ANIM_PROBE_PHASE" -Value $effectiveAnimProbePhase
Set-StockControlEnv -Name "ROGUE_SKIP_GAMETYPE_RAW_SYNC" -Value "1"
Set-StockControlEnv -Name "ROGUE_FORCE_STOCK_SHELL" -Value $(if ($forceStockShellEnabled) { "1" } else { "0" })
Set-StockControlEnv -Name "ROGUE_FORCED_STOCK_SHELL" -Value $ForcedStockShell
Set-StockControlEnv -Name "ROGUE_FORCE_LOW_HANDMODEL" -Value "0"
Set-StockControlEnv -Name "ROGUE_USE_CUSTOM_IDG_VIEWHANDS" -Value "0"
Set-StockControlEnv -Name "ROGUE_STOCK_SURVIVOR_HANDMODEL" -Value "c_zom_hazmat_viewhands"
Set-StockControlEnv -Name "ROGUE_ENABLE_SERVANT_FIRE_WATCHER" -Value "0"
Set-StockControlEnv -Name "ROGUE_USE_STOCK_SURVIVOR_CARRIER" -Value "1"
Set-StockControlEnv -Name "ROGUE_SKIP_UI_OVERRIDES" -Value "1"
Set-StockControlEnv -Name "ROGUE_DISABLE_SANITIZED_RAW_RESTORE" -Value "1"
Set-StockControlEnv -Name "ROGUE_RESTORE_GLOBAL_GAMETYPE_RAW" -Value "0"
Set-StockControlEnv -Name "ROGUE_USE_BO3_RAW_FX" -Value "0"
Set-StockControlEnv -Name "ROGUE_BO3_RAW_FX_STAGE" -Value "off"
Set-StockControlEnv -Name "ROGUE_USE_BO3_SERVANT_CLIENT_FX" -Value "0"
Set-StockControlEnv -Name "ROGUE_CLIENT_FFPROBE_ASSET" -Value ""
Set-StockControlEnv -Name "ROGUE_USE_BO3_FX_LOAD_FF" -Value "0"
Set-StockControlEnv -Name "ROGUE_INCLUDE_FX_DEBUG_PROBES" -Value "0"
Set-StockControlEnv -Name "ROGUE_NATIVE_PROBE_MODE" -Value "safe"
Set-StockControlEnv -Name "ROGUE_PROBE_ONLY_FAST_PATH" -Value "0"
Set-StockControlEnv -Name "ROGUE_USE_FULL_ZONE_SOURCE" -Value "1"
Set-StockControlEnv -Name "ROGUE_USE_MAP_FULL_ZONE_SOURCE" -Value "0"
Set-StockControlEnv -Name "ROGUE_SYNC_TRANSIT_CLIENTSCRIPT" -Value "1"
Set-StockControlEnv -Name "ROGUE_SYNC_CARRIER_MAP_SCRIPTS" -Value "0"
Set-StockControlEnv -Name "ROGUE_ALLOW_STRIPPED_SURVIVAL_FF" -Value "0"
Set-StockControlEnv -Name "ROGUE_DEPLOY_TO_MOD" -Value "1"
Set-StockControlEnv -Name "ROGUE_DEPLOY_TO_BASE" -Value "0"
Set-StockControlEnv -Name "ROGUE_SKIP_MOD_LOAD_SYNC" -Value "0"
Set-StockControlEnv -Name "ROGUE_SKIP_MOD_PATCH_SYNC" -Value "1"
Set-StockControlEnv -Name "ROGUE_SKIP_SCRIPT_SYNC" -Value "0"
Set-StockControlEnv -Name "ROGUE_REQUIRE_APPDATA_SYNC" -Value "1"
Set-StockControlEnv -Name "ROGUE_ALLOW_SERVER_SPAWNER_SYNC" -Value "1"
Set-StockControlEnv -Name "ROGUE_RUN_LABEL" -Value "stock_visibility_control"
Set-StockControlEnv -Name "ROGUE_SCRIPT_ONLY_SYNC" -Value "0"
Set-StockControlEnv -Name "ROGUE_ENABLE_VISIBILITY_RECOVERY" -Value "1"
Set-StockControlEnv -Name "ROGUE_BUILD_TAG" -Value ("stockctl_{0}" -f $stamp)

foreach ($legacyRepoPath in @(
    (Join-Path $root ("mods\{0}\ui" -f $modName)),
    (Join-Path $root ("mods\{0}\ui_mp" -f $modName)),
    (Join-Path $root ("mods\{0}\maps\mp\gametypes_zm" -f $modName))
)) {
    if (Test-Path $legacyRepoPath) {
        $relativePath = $legacyRepoPath.Substring($root.Length).TrimStart('\')
        $archivedPath = Join-Path $repoInputQuarantineRoot $relativePath
        if (Move-PathIfExists -Source $legacyRepoPath -Destination $archivedPath) {
            Write-Host "Quarantined repo baseline override: $legacyRepoPath -> $archivedPath"
        }
    }
}

Write-Host "Building stock visibility control..."
& python $buildScript
if ($LASTEXITCODE -ne 0) {
    throw "Stock visibility control build failed with exit code $LASTEXITCODE"
}

if ($UseOfficialTransitClientscript) {
    if (-not (Test-Path $officialTransitClientPath)) {
        throw "Missing official transit clientscript: $officialTransitClientPath"
    }

    Copy-Item -LiteralPath $officialTransitClientPath -Destination $repoTransitClientPath -Force
    Copy-Item -LiteralPath $officialTransitClientPath -Destination $workTransitClientPath -Force
}

$resolvedSourceReportPath = Join-Path $runDir "resolved_sources.json"

$summary = [ordered]@{
    built_at = (Get-Date).ToString("o")
    build_tag = ("stockctl_{0}" -f $stamp)
    mod = $modName
    build_root_name = $BuildRootName
    weapon = $Weapon
    use_stock_survival_zone = [bool]$UseStockSurvivalZone
    effective_runtime_mode = "built_runtime_override"
    use_official_transit_clientscript = [bool]$UseOfficialTransitClientscript
    launch = [bool]$Launch
    capture_screenshot = [bool]$CaptureScreenshot
    map = $Map
    ui_mapname = $UiMapName
    ui_gametype = $UiGametype
    ui_zm_gamemodegroup = $UiZmGamemodeGroup
    ui_map_start_location = $UiMapStartLocation
    g_gametype = $GGametype
    monitor_index = $MonitorIndex
}

if ($Launch) {
    $gamesSnapshot = Get-LogSnapshot -Path $gamesLog
    $consoleSnapshot = Get-LogSnapshot -Path $consoleLog
    $quarantinedDlcLoadFfs = @()
    foreach ($entry in $dlcLoadFfEntries) {
        $sourcePath = Join-Path $GameDir $entry.RelativePath
        $record = Quarantine-PathIfExists -Source $sourcePath -QuarantineRoot $runtimeDlcQuarantineRoot -Label $entry.Label
        if ($null -ne $record) {
            $quarantinedDlcLoadFfs += $record
            Write-Host "Quarantined runtime DLC load FF -> $sourcePath"
        }
    }
    $summary["quarantined_dlc_load_ffs"] = @($quarantinedDlcLoadFfs | ForEach-Object { $_.source })
}

$restartArgs = @(
    "-ExecutionPolicy", "Bypass",
    "-File", $restartScript,
    "-ModOnly",
    "-Mod", $modName,
    "-BuildRootName", $BuildRootName,
    "-RepoDir", $root,
    "-GameDir", $GameDir,
    "-PlutoniumDir", $PlutoniumDir,
    "-ResolvedSourceReportPath", $resolvedSourceReportPath
)

if ($UseStockSurvivalZone) {
    $restartArgs += "-UseStockSurvivalZone"
}

if ($Launch) {
    $restartArgs += @(
        "-Launch",
        "-Map", $Map,
        "-UiMapName", $UiMapName,
        "-UiGametype", $UiGametype,
        "-UiZmGamemodeGroup", $UiZmGamemodeGroup,
        "-UiMapStartLocation", $UiMapStartLocation,
        "-GGametype", $GGametype,
        "-Name", $Name,
        "-MonitorIndex", $MonitorIndex
    )
}

$quarantinedDlcLoadFfs = @($quarantinedDlcLoadFfs)
try {
    $launchStart = Get-Date
    Write-Host "Syncing stock visibility control..."
    & powershell @restartArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Stock visibility control restart helper failed with exit code $LASTEXITCODE"
    }

    Copy-IfExists -Source $buildReportPath -Destination (Join-Path $runDir "build_report.json")
    Copy-IfExists -Source $repoScriptPath -Destination (Join-Path $runDir "mod_i_am_mod.repo.gsc")
    Copy-IfExists -Source $workScriptPath -Destination (Join-Path $runDir "mod_i_am_mod.work.gsc")
    Copy-IfExists -Source $appDataScriptPath -Destination (Join-Path $runDir "mod_i_am_mod.appdata.gsc")
    if (Test-Path (Join-Path $root ("mods\{0}\maps\mp\zombies\_zm_spawner.gsc" -f $modName))) {
        Copy-IfExists -Source (Join-Path $root ("mods\{0}\maps\mp\zombies\_zm_spawner.gsc" -f $modName)) -Destination (Join-Path $runDir "_zm_spawner.repo.gsc")
    } else {
        Copy-IfExists -Source (Join-Path $root ("mods\{0}\scripts\mp\zombies\_zm_spawner.gsc" -f $modName)) -Destination (Join-Path $runDir "_zm_spawner.repo.gsc")
    }
    if (Test-Path ("C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\mods\{0}\maps\mp\zombies\_zm_spawner.gsc" -f $modName)) {
        Copy-IfExists -Source ("C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\mods\{0}\maps\mp\zombies\_zm_spawner.gsc" -f $modName) -Destination (Join-Path $runDir "_zm_spawner.appdata.gsc")
    } else {
        Copy-IfExists -Source ("C:\Users\Ahmed\AppData\Local\Plutonium\storage\t6\mods\{0}\scripts\mp\zombies\_zm_spawner.gsc" -f $modName) -Destination (Join-Path $runDir "_zm_spawner.appdata.gsc")
    }
    Copy-IfExists -Source $repoTransitClientPath -Destination (Join-Path $runDir "zm_transit.repo.csc")
    Copy-IfExists -Source $workTransitClientPath -Destination (Join-Path $runDir "zm_transit.work.csc")
    Copy-IfExists -Source $appDataTransitClientPath -Destination (Join-Path $runDir "zm_transit.appdata.csc")

    if ($Launch) {
        $marker = Wait-ForLogMarker -Snapshots @($gamesSnapshot, $consoleSnapshot) -Markers @("stage=post_shell_give", "[bo3_rev][idle_begin]", "[bo3_rev][grant]") -TimeoutSec $MarkerTimeoutSec
        if (-not [string]::IsNullOrWhiteSpace($marker)) {
            $summary["marker_seen"] = $marker
        }

        if ($CaptureScreenshot) {
            Start-Sleep -Seconds $CaptureDelaySec
            $screenshotPath = Join-Path $runDir "window.png"
            $captureInfo = Capture-GameWindow -Path $screenshotPath
            $summary["screenshot"] = $screenshotPath
            $summary["screenshot_capture"] = $captureInfo
        }

        Copy-IfExists -Source $gamesLog -Destination (Join-Path $runDir "games_mp.log")
        Copy-IfExists -Source $consoleLog -Destination (Join-Path $runDir "console_zm.log")
        (Get-LogDeltaText -Snapshot $gamesSnapshot) | Set-Content -Path (Join-Path $runDir "games_mp.delta.log") -Encoding UTF8
        (Get-LogDeltaText -Snapshot $consoleSnapshot) | Set-Content -Path (Join-Path $runDir "console_zm.delta.log") -Encoding UTF8
        $capturedLogs = @(Capture-ChangedLogFiles -Root $storageRoot -DestinationRoot $runDir -NotBefore $launchStart)
        $capturedLogs | ConvertTo-Json -Depth 4 | Set-Content -Path (Join-Path $runDir "log_capture_manifest.json") -Encoding UTF8
        $summary["captured_logs"] = $capturedLogs
        & powershell -ExecutionPolicy Bypass -File $runtimeDossierScript -Label ("stock_control_{0}" -f $stamp) -RepoDir $root -GameDir $GameDir -PlutoniumDir $PlutoniumDir -Mod $modName -OutPath (Join-Path $runDir "runtime_dossier.postlaunch.json")

        if ($KillAfterCapture) {
            Get-Process "plutonium-bootstrapper-win32" -ErrorAction SilentlyContinue | Stop-Process -Force
            Get-Process "plutonium-bootstrapper-win64" -ErrorAction SilentlyContinue | Stop-Process -Force
            $summary["killed_after_capture"] = $true
        }
    }
}
finally {
    Restore-QuarantinedPaths -Records $quarantinedDlcLoadFfs
}

$resolvedSourceReport = $null
if (Test-Path $resolvedSourceReportPath) {
    $resolvedSourceReport = Get-Content -LiteralPath $resolvedSourceReportPath -Raw | ConvertFrom-Json
}

$buildReportSummary = Get-BuildReportSummary -Path $buildReportPath
$effectiveBuildTag = [string]$buildReportSummary.build_tag
if ([string]::IsNullOrWhiteSpace($effectiveBuildTag)) {
    $effectiveBuildTag = [string]$summary.build_tag
}

$engineInputDossier = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    requested_lane = $summary
    effective_build_tag = $effectiveBuildTag
    build_report = $buildReportSummary
    rendered_scripts = [ordered]@{
        repo = Get-ModScriptSummary -Path $repoScriptPath
        work = Get-ModScriptSummary -Path $workScriptPath
        appdata = Get-ModScriptSummary -Path $appDataScriptPath
    }
    transit_clientscript = [ordered]@{
        repo = Get-FileRecord -Path $repoTransitClientPath
        work = Get-FileRecord -Path $workTransitClientPath
        appdata = Get-FileRecord -Path $appDataTransitClientPath
    }
    resolved_sources = $resolvedSourceReport
    live_logs = [ordered]@{
        games_mp = Get-LogSignalSummary -Path $gamesLog -BuildTag $effectiveBuildTag
        console_zm = Get-LogSignalSummary -Path $consoleLog -BuildTag $effectiveBuildTag
    }
}

$summary | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $runDir "run_summary.json") -Encoding UTF8
$engineInputDossier | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $runDir "engine_input_dossier.json") -Encoding UTF8
Write-Host "Stock visibility control artifacts: $runDir"
