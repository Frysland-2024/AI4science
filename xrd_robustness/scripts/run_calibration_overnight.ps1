param(
    [string]$Python = "python",
    [int]$BatchSize = 128,
    [string]$Device = "auto"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

$OutputRoot = Join-Path $ProjectRoot "outputs\calibration_analysis"
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogPath = Join-Path $OutputRoot "overnight_$Timestamp.log"

# Keep Windows awake while the Python process is running. The display may still turn off.
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class SleepControl {
    [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
"@

$ES_CONTINUOUS = [uint32]0x80000000
$ES_SYSTEM_REQUIRED = [uint32]0x00000001
[SleepControl]::SetThreadExecutionState($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED) | Out-Null

try {
    Write-Host "Calibration audit starting. You can leave this window open and go to sleep."
    Write-Host "Project: $ProjectRoot"
    Write-Host "Log: $LogPath"
    Write-Host "Python: $Python | device=$Device | batch-size=$BatchSize"

    & $Python ".\scripts\analyze_calibration.py" `
        --device $Device `
        --batch-size $BatchSize 2>&1 | Tee-Object -FilePath $LogPath

    $ExitCode = $LASTEXITCODE
    if ($ExitCode -ne 0) {
        throw "Calibration audit exited with code $ExitCode. See $LogPath"
    }

    Write-Host ""
    Write-Host "Done. Tomorrow open:"
    Write-Host (Join-Path $OutputRoot "REPORT.md")
    Write-Host "Summary JSON:"
    Write-Host (Join-Path $OutputRoot "summary.json")
}
finally {
    [SleepControl]::SetThreadExecutionState($ES_CONTINUOUS) | Out-Null
}
