param(
    [int]$StructuresPerCrystalSystem = 10,
    [int]$Permutations = 200,
    [int]$WorkerCount = 4,
    [int]$PrefetchBatches = 4,
    [string]$PythonExe = "E:\AI4science\.venvs\xrd_tools\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

if (-not (Test-Path $PythonExe -PathType Leaf)) {
    throw "Python executable not found: $PythonExe"
}

$ProtectedReports = @(
    (Join-Path $ProjectRoot "reports\v9_p0_local_benefit.json"),
    (Join-Path $ProjectRoot "reports\v9_p0_local_benefit_replication_seed1.json"),
    (Join-Path $ProjectRoot "reports\v9_p0_statistical_robustness.json"),
    (Join-Path $ProjectRoot "reports\v9_p0_short_trajectory.json")
)
$ProtectedHashes = @{}
foreach ($Report in $ProtectedReports) {
    if (Test-Path $Report -PathType Leaf) {
        $ProtectedHashes[$Report] = (Get-FileHash -Algorithm SHA256 $Report).Hash
        Write-Host "Protected existing report: $Report"
        Write-Host "SHA256: $($ProtectedHashes[$Report])"
    }
}

$env:PYTHONPATH = (Join-Path $ProjectRoot "src")
$Output = Join-Path $ProjectRoot "reports\v10_p0_measurement_information_gate.json"

Write-Host "[1/2] Running focused V10-P0 utility tests..."
& $PythonExe -m unittest discover -s tests -p "test_v10_p0_measurement_information.py" -v
if ($LASTEXITCODE -ne 0) {
    throw "V10-P0 utility tests failed. No diagnostic was started."
}

Write-Host "[2/2] Running Train-only V10-P0 measurement-information gate on CUDA..."
Write-Host "This rebuilds one five-epoch ERM backbone in memory and writes no checkpoint."
& $PythonExe scripts\audit_v10_p0_measurement_information.py `
    --device cuda `
    --worker-count $WorkerCount `
    --prefetch-batches $PrefetchBatches `
    --structures-per-crystal-system $StructuresPerCrystalSystem `
    --permutations $Permutations `
    --output $Output
if ($LASTEXITCODE -ne 0) {
    throw "V10-P0 measurement-information gate failed."
}

foreach ($Report in $ProtectedHashes.Keys) {
    $After = (Get-FileHash -Algorithm SHA256 $Report).Hash
    if ($After -ne $ProtectedHashes[$Report]) {
        throw "Protected V9 P0 report changed unexpectedly: $Report"
    }
}

Write-Host "V10-P0 gate completed."
Write-Host "Existing V9 P0 reports were preserved."
Write-Host "Output: $Output"
Write-Host "SHA256: $((Get-FileHash -Algorithm SHA256 $Output).Hash)"
