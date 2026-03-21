param(
    [string]$Configuration = "Release"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$outDir = Join-Path $root "bin\x86\$Configuration"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$buildInfoHeader = Join-Path $root "fx_runtime_probe_build_info.h"
$latestBuildJson = Join-Path $outDir "fx_runtime_probe_latest_build.json"

$vcvars = "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars32.bat"
if (-not (Test-Path $vcvars)) {
    throw "Missing vcvars32.bat at $vcvars"
}

$dllSrc = Join-Path $root "fx_runtime_probe_hook.cpp"
$exeSrc = Join-Path $root "fx_runtime_probe_injector.cpp"
$dllOut = Join-Path $outDir "fx_runtime_probe_hook_$stamp.dll"
$exeOut = Join-Path $outDir "fx_runtime_probe_injector.exe"

@"
#pragma once
#define PROBE_BUILD_ID "$stamp"
"@ | Set-Content -Path $buildInfoHeader -Encoding ASCII

$commonFlags = "/nologo /std:c++17 /EHsc /MT /W3 /DWIN32 /D_WINDOWS"
if ($Configuration -ieq "Debug") {
    $commonFlags = "/nologo /std:c++17 /EHsc /MTd /Zi /Od /W3 /DWIN32 /D_WINDOWS /D_DEBUG"
}

$dllCmd = "cl $commonFlags /LD `"$dllSrc`" /link /OUT:`"$dllOut`""
$exeCmd = "cl $commonFlags `"$exeSrc`" /link /OUT:`"$exeOut`""
$full = "@echo off && call `"$vcvars`" >nul && cd /d `"$root`" && $dllCmd && $exeCmd"

cmd.exe /c $full
if ($LASTEXITCODE -ne 0) {
    throw "Build failed with exit code $LASTEXITCODE"
}

$meta = [ordered]@{
    build_id = $stamp
    configuration = $Configuration
    dll = [System.IO.Path]::GetFileName($dllOut)
    dll_path = $dllOut
    injector = [System.IO.Path]::GetFileName($exeOut)
    injector_path = $exeOut
    built_utc = (Get-Date).ToUniversalTime().ToString("o")
}
$meta | ConvertTo-Json | Set-Content -Path $latestBuildJson -Encoding UTF8

Write-Host "Built:"
Write-Host "  $dllOut"
Write-Host "  $exeOut"
Write-Host "Probe build id: $stamp"
