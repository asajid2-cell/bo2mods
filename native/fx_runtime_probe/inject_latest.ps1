param(
    [string]$ProcessName = "",
    [int]$TargetPid = 0,
    [string]$Configuration = "Release",
    [switch]$Wait
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$binDir = Join-Path $root "bin\x86\$Configuration"
$dll = Get-ChildItem $binDir -Filter "fx_runtime_probe_hook*.dll" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName
$injector = Join-Path $binDir "fx_runtime_probe_injector.exe"
$latestBuildJson = Join-Path $binDir "fx_runtime_probe_latest_build.json"

if (-not $dll -or -not (Test-Path $injector)) {
    throw "Missing built binaries. Run build_x86.ps1 first."
}

$probeBuildId = ""
if (Test-Path $latestBuildJson) {
    try {
        $meta = Get-Content $latestBuildJson -Raw | ConvertFrom-Json
        if ($meta.dll_path -and ((Resolve-Path $meta.dll_path).Path -eq (Resolve-Path $dll).Path)) {
            $probeBuildId = [string]$meta.build_id
        }
    } catch {
    }
}
if ([string]::IsNullOrWhiteSpace($probeBuildId)) {
    $match = [regex]::Match([System.IO.Path]::GetFileNameWithoutExtension($dll), 'fx_runtime_probe_hook_(.+)$')
    if ($match.Success) {
        $probeBuildId = $match.Groups[1].Value
    } else {
        $probeBuildId = "unknown"
    }
}

Write-Host "Selected probe build: $probeBuildId"
Write-Host "Selected probe DLL: $dll"
Write-Host "Probe log: $(Join-Path $binDir 'fx_runtime_probe.log')"

function Resolve-TargetProcess {
    param(
        [string]$RequestedName,
        [int]$CurrentScriptPid,
        [switch]$AllowBootstrapperFallback
    )

    $exeStemLocal = [System.IO.Path]::GetFileNameWithoutExtension($RequestedName)

    $direct = Get-Process -Name $exeStemLocal -ErrorAction SilentlyContinue |
        Where-Object { $_.Id -ne $CurrentScriptPid } |
        Select-Object -First 1
    if ($direct) {
        return $direct
    }

    $all = Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $CurrentScriptPid }

    $named = $all | Where-Object {
        $_.Name -ieq $RequestedName -or $_.Name -ieq "$exeStemLocal.exe"
    } | Select-Object -First 1
    if ($named) {
        return Get-Process -Id $named.ProcessId -ErrorAction SilentlyContinue
    }

    if ($AllowBootstrapperFallback) {
        $tokenHosts = $all | Where-Object {
            $_.Name -ieq "plutonium-bootstrapper-win32.exe" -and
            $_.CommandLine -and
            $_.CommandLine -match [regex]::Escape($exeStemLocal)
        } | Select-Object -First 1
        if ($tokenHosts) {
            return Get-Process -Id $tokenHosts.ProcessId -ErrorAction SilentlyContinue
        }
    }

    $tokenHosts = $all | Where-Object {
        $_.Name -ieq "plutonium-bootstrapper-win32.exe" -and
        $_.CommandLine -and
        (
            $_.CommandLine -match [regex]::Escape($RequestedName) -or
            $_.CommandLine -match [regex]::Escape($exeStemLocal) -or
            ($exeStemLocal -ieq "t6zm" -and $_.CommandLine -match '\bt6zm\b')
        )
    } | Select-Object -First 1
    if ($tokenHosts) {
        return Get-Process -Id $tokenHosts.ProcessId -ErrorAction SilentlyContinue
    }

    return $null
}

if ($TargetPid -gt 0) {
    Write-Host "Injecting probe build $probeBuildId into pid $TargetPid..."
    & $injector --dll $dll --pid $TargetPid
    exit $LASTEXITCODE
}

if ([string]::IsNullOrWhiteSpace($ProcessName)) {
    throw "Provide -ProcessName or -TargetPid."
}

$resolvedProc = Resolve-TargetProcess -RequestedName $ProcessName -CurrentScriptPid $PID

if ($Wait) {
    Write-Host "Waiting for process '$ProcessName'..."
    do {
        if (-not $resolvedProc) {
            $resolvedProc = Resolve-TargetProcess -RequestedName $ProcessName -CurrentScriptPid $PID
        }
        if (-not $resolvedProc) {
            Start-Sleep -Milliseconds 500
        }
    } while (-not $resolvedProc)

    Write-Host "Found $($resolvedProc.ProcessName) (pid=$($resolvedProc.Id)); injecting probe build $probeBuildId..."
}

if ($resolvedProc) {
    & $injector --dll $dll --pid $resolvedProc.Id
    exit $LASTEXITCODE
}

$fallbackProc = Resolve-TargetProcess -RequestedName $ProcessName -CurrentScriptPid $PID -AllowBootstrapperFallback
if ($fallbackProc) {
    Write-Host "Fallback target $($fallbackProc.ProcessName) (pid=$($fallbackProc.Id)); injecting probe build $probeBuildId..."
    & $injector --dll $dll --pid $fallbackProc.Id
    exit $LASTEXITCODE
}

& $injector --dll $dll --name $ProcessName
exit $LASTEXITCODE
