param(
    [int]$PollSeconds = 30,
    [int]$RequiredConsecutiveIdleChecks = 3,
    [int]$MinimumFreeMemoryMiB = 5500,
    [int]$MaximumUtilizationPercent = 20
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = "E:\AI4science\.venvs\xrd_tools\Scripts\python.exe"
$Runner = Join-Path $ProjectRoot "scripts\run_v9_method_transfer.py"
$Plan = Join-Path $ProjectRoot "reports\v9_method_transfer_tuning_plan.json"
$IdleChecks = 0

Set-Location $ProjectRoot
Write-Output "[$(Get-Date -Format o)] V9-T tuning queue started."
Write-Output "Waiting for GPU free memory >= $MinimumFreeMemoryMiB MiB and utilization <= $MaximumUtilizationPercent% for $RequiredConsecutiveIdleChecks consecutive checks."

while ($IdleChecks -lt $RequiredConsecutiveIdleChecks) {
    $Raw = & nvidia-smi --query-gpu=memory.free,utilization.gpu --format=csv,noheader,nounits
    if ($LASTEXITCODE -ne 0 -or -not $Raw) {
        throw "nvidia-smi GPU query failed"
    }
    $Parts = $Raw.Split(",")
    $FreeMemoryMiB = [int]$Parts[0].Trim()
    $UtilizationPercent = [int]$Parts[1].Trim()
    if (
        $FreeMemoryMiB -ge $MinimumFreeMemoryMiB -and
        $UtilizationPercent -le $MaximumUtilizationPercent
    ) {
        $IdleChecks += 1
    }
    else {
        $IdleChecks = 0
    }
    Write-Output "[$(Get-Date -Format o)] free_mib=$FreeMemoryMiB utilization_percent=$UtilizationPercent idle_checks=$IdleChecks/$RequiredConsecutiveIdleChecks"
    if ($IdleChecks -lt $RequiredConsecutiveIdleChecks) {
        Start-Sleep -Seconds $PollSeconds
    }
}

Write-Output "[$(Get-Date -Format o)] GPU idle gate passed; starting seven Validation-only tuning runs."
& $Python -s $Runner tune-run --plan $Plan --confirm-development-tuning
$ExitCode = $LASTEXITCODE
Write-Output "[$(Get-Date -Format o)] V9-T tuning process exited with code $ExitCode."
exit $ExitCode
