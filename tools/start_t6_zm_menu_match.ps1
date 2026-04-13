param(
    [string]$ProcessNamePattern = "plutonium-bootstrapper-win32",
    [string]$WindowTitlePattern = "Plutonium T6 Zombies*",
    [ValidateRange(0, 30)]
    [int]$InitialDelaySec = 2,
    [ValidateRange(10, 5000)]
    [int]$KeyDelayMs = 350,
    [string[]]$Keys = @("{UP}", "{ENTER}")
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName Microsoft.VisualBasic
Add-Type -AssemblyName System.Windows.Forms

$pinvoke = @"
using System;
using System.Runtime.InteropServices;

public static class CodexStartMatchWin32 {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@

Add-Type -TypeDefinition $pinvoke

$proc = Get-Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.MainWindowHandle -ne 0 -and
        $_.ProcessName -like $ProcessNamePattern -and
        ($_.MainWindowTitle -like $WindowTitlePattern)
    } |
    Sort-Object StartTime -Descending |
    Select-Object -First 1

if (-not $proc) {
    throw "Could not find game window matching $ProcessNamePattern / $WindowTitlePattern"
}

[void][CodexStartMatchWin32]::ShowWindow($proc.MainWindowHandle, 9)
[void][CodexStartMatchWin32]::SetForegroundWindow($proc.MainWindowHandle)
[Microsoft.VisualBasic.Interaction]::AppActivate($proc.Id) | Out-Null

if ($InitialDelaySec -gt 0) {
    Start-Sleep -Seconds $InitialDelaySec
}

foreach ($key in $Keys) {
    [Microsoft.VisualBasic.Interaction]::AppActivate($proc.Id) | Out-Null
    [System.Windows.Forms.SendKeys]::SendWait($key)
    Start-Sleep -Milliseconds $KeyDelayMs
}

Write-Host ("Sent keys to PID {0}: {1}" -f $proc.Id, ($Keys -join ", "))
