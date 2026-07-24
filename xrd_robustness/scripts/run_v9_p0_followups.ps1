param(
    [int]$ReplicationRepeats = 12,
    [int]$TrajectoryRepeats = 6,
    [int]$TrajectorySteps = 5,
    [int]$WorkerCount = 4,
    [int]$PrefetchBatches = 4,
    [string]$PythonExe = "E:\AI4science\.venvs\xrd_tools\Scripts\python.exe",
    [switch]$SkipReplication,
    [switch]$SkipTrajectory
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

if (-not (Test-Path $PythonExe -PathType Leaf)) {
    throw "Python executable not found: $PythonExe"
}

$Original = Join-Path $ProjectRoot "reports\v9_p0_local_benefit.json"
if (-not (Test-Path $Original -PathType Leaf)) {
    throw "Original P0 report not found: $Original"
}
$OriginalHashBefore = (Get-FileHash -Algorithm SHA256 $Original).Hash
Write-Host "Original P0 report is protected and will not be overwritten."
Write-Host "Original: $Original"
Write-Host "Original SHA256: $OriginalHashBefore"

$env:PYTHONPATH = (Join-Path $ProjectRoot "src")

$StatisticsOutput = Join-Path $ProjectRoot "reports\v9_p0_statistical_robustness.json"
$ReplicationOutput = Join-Path $ProjectRoot "reports\v9_p0_local_benefit_replication_seed1.json"
$TrajectoryOutput = Join-Path $ProjectRoot "reports\v9_p0_short_trajectory.json"

Write-Host "[1/4] Running focused follow-up utility tests..."
& $PythonExe -m unittest discover -s tests -p "test_v9_p0_followups.py" -v
if ($LASTEXITCODE -ne 0) {
    throw "Follow-up utility tests failed. No diagnostic was started."
}

Write-Host "[2/4] Running CPU-only clustered bootstrap and leave-one-profile-out analysis..."
& $PythonExe scripts\analyze_v9_p0_statistical_robustness.py `
    --input $Original `
    --output $StatisticsOutput
if ($LASTEXITCODE -ne 0) {
    throw "Statistical robustness analysis failed."
}

if (-not $SkipReplication) {
    Write-Host "[3/4] Running independent-seed Train-only P0 replication on CUDA..."
    & $PythonExe scripts\audit_v9_p0_independent_replication.py `
        --device cuda `
        --repeats $ReplicationRepeats `
        --worker-count $WorkerCount `
        --prefetch-batches $PrefetchBatches `
        --output $ReplicationOutput
    if ($LASTEXITCODE -ne 0) {
        throw "Independent-seed replication failed."
    }
} else {
    Write-Host "[3/4] Independent-seed replication skipped by request."
}

if (-not $SkipTrajectory) {
    Write-Host "[4/4] Running matched Train-only short trajectory on CUDA..."
    & $PythonExe scripts\audit_v9_p0_short_trajectory.py `
        --device cuda `
        --steps $TrajectorySteps `
        --repeats $TrajectoryRepeats `
        --worker-count $WorkerCount `
        --prefetch-batches $PrefetchBatches `
        --output $TrajectoryOutput
    if ($LASTEXITCODE -ne 0) {
        throw "Short-trajectory diagnostic failed."
    }
} else {
    Write-Host "[4/4] Short trajectory skipped by request."
}

$OriginalHashAfter = (Get-FileHash -Algorithm SHA256 $Original).Hash
if ($OriginalHashAfter -ne $OriginalHashBefore) {
    throw "Protected original P0 report hash changed unexpectedly. Stop and investigate."
}

Write-Host "All requested follow-ups completed."
Write-Host "Original preserved: $Original"
Write-Host "Original SHA256 unchanged: $OriginalHashAfter"
Write-Host "New reports and SHA256 values:"
Write-Host "  $StatisticsOutput"
Write-Host "  $((Get-FileHash -Algorithm SHA256 $StatisticsOutput).Hash)"
if (-not $SkipReplication) {
    Write-Host "  $ReplicationOutput"
    Write-Host "  $((Get-FileHash -Algorithm SHA256 $ReplicationOutput).Hash)"
}
if (-not $SkipTrajectory) {
    Write-Host "  $TrajectoryOutput"
    Write-Host "  $((Get-FileHash -Algorithm SHA256 $TrajectoryOutput).Hash)"
}
