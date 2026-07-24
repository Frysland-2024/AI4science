param(
    [int]$Epochs = 3,
    [int]$TrainStructuresPerClass = 200,
    [int]$PanelStructuresPerClass = 10,
    [int]$Permutations = 100,
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

$GateReport = Join-Path $ProjectRoot "reports\v10_p0_measurement_information_gate.json"
if (-not (Test-Path $GateReport -PathType Leaf)) {
    throw "V10-P0 prerequisite report not found: $GateReport"
}

$ProtectedReports = @(
    Get-ChildItem (Join-Path $ProjectRoot "reports") -File |
        Where-Object {
            $_.Name -like "v9_p0*.json" -or
            $_.Name -eq "v10_p0_measurement_information_gate.json"
        }
)
$ProtectedHashes = @{}
foreach ($Report in $ProtectedReports) {
    $ProtectedHashes[$Report.FullName] = (Get-FileHash -Algorithm SHA256 $Report.FullName).Hash
}

$env:PYTHONPATH = (Join-Path $ProjectRoot "src")
Write-Host "[1/2] Running V10 Pilot utility tests..."
& $PythonExe -m unittest discover -s tests -p "test_v10_train_only_pilot.py" -v
if ($LASTEXITCODE -ne 0) {
    throw "V10 Pilot utility tests failed. Pilot was not started."
}

$Output = Join-Path $ProjectRoot "reports\v10_train_only_pilot.json"
Write-Host "[2/2] Running matched Train-only V10 Pilot on CUDA..."
& $PythonExe scripts\audit_v10_train_only_pilot.py `
    --device cuda `
    --epochs $Epochs `
    --train-structures-per-class $TrainStructuresPerClass `
    --panel-structures-per-class $PanelStructuresPerClass `
    --permutations $Permutations `
    --worker-count $WorkerCount `
    --prefetch-batches $PrefetchBatches `
    --output $Output
if ($LASTEXITCODE -ne 0) {
    throw "V10 Train-only Pilot failed."
}

foreach ($Path in $ProtectedHashes.Keys) {
    $After = (Get-FileHash -Algorithm SHA256 $Path).Hash
    if ($After -ne $ProtectedHashes[$Path]) {
        throw "Protected report hash changed unexpectedly: $Path"
    }
}

Write-Host "V10 Train-only Pilot completed."
Write-Host "Protected P0 reports were preserved."
Write-Host "Output: $Output"
Write-Host "SHA256: $((Get-FileHash -Algorithm SHA256 $Output).Hash)"
