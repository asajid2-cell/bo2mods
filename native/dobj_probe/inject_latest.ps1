param(
    [string]$ProcessName = "",
    [int]$TargetPid = 0,
    [string]$Configuration = "Release",
    [switch]$Wait
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$binDir = Join-Path $root "bin\x86\$Configuration"
$dll = Get-ChildItem $binDir -Filter "dobj_probe_hook*.dll" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName
$injector = Join-Path $binDir "dobj_probe_injector.exe"

if (-not $dll -or -not (Test-Path $injector)) {
    throw "Missing built binaries. Run build_x86.ps1 first."
}

function Resolve-TargetProcess {
    param(
        [string]$RequestedName,
        [int]$CurrentScriptPid
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

    $tokenHosts = $all | Where-Object {
        $_.Name -ieq "plutonium-bootstrapper-win32.exe" -and
        $_.CommandLine -and
        $_.CommandLine -match [regex]::Escape($exeStemLocal)
    } | Select-Object -First 1
    if ($tokenHosts) {
        return Get-Process -Id $tokenHosts.ProcessId -ErrorAction SilentlyContinue
    }

    return $null
}

if ($TargetPid -gt 0) {
    & $injector --dll $dll --pid $TargetPid
    exit $LASTEXITCODE
}

if ([string]::IsNullOrWhiteSpace($ProcessName)) {
    throw "Provide -ProcessName or -TargetPid."
}

$exeStem = [System.IO.Path]::GetFileNameWithoutExtension($ProcessName)
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

    Write-Host "Found $($resolvedProc.ProcessName) (pid=$($resolvedProc.Id)); injecting..."
}

if ($resolvedProc) {
    & $injector --dll $dll --pid $resolvedProc.Id
    exit $LASTEXITCODE
}

& $injector --dll $dll --name $ProcessName
exit $LASTEXITCODE
