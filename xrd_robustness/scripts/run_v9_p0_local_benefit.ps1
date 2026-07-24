param(
    [int]$Repeats = 12,
    [int]$WorkerCount = 4,
    [int]$PrefetchBatches = 4,
    [string]$PythonExe = "E:\AI4science\.venvs\xrd_tools\Scripts\python.exe",
    [string]$Output = "reports\v9_p0_local_benefit.json"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

if (-not (Test-Path $PythonExe -PathType Leaf)) {
    throw "Python executable not found: $PythonExe"
}
if ($Repeats -lt 1 -or $Repeats -gt 50) {
    throw "Repeats must be between 1 and 50."
}
if ($WorkerCount -lt 1) {
    throw "WorkerCount must be positive."
}
if ($PrefetchBatches -lt 1) {
    throw "PrefetchBatches must be positive."
}

$env:PYTHONPATH = (Join-Path $ProjectRoot "src")

Write-Host "[1/3] Running focused utility tests..."
& $PythonExe -m unittest discover -s tests -p "test_v9_local_benefit.py" -v
if ($LASTEXITCODE -ne 0) {
    throw "Focused P0 utility tests failed. Diagnostic was not started."
}

Write-Host "[2/3] Running Train-only P0 local-benefit diagnostic..."
Write-Host "This rebuilds one five-epoch ERM state in memory and writes no checkpoint."
& $PythonExe scripts\audit_v9_local_benefit.py `
    --device cuda `
    --repeats $Repeats `
    --worker-count $WorkerCount `
    --prefetch-batches $PrefetchBatches `
    --output $Output
if ($LASTEXITCODE -ne 0) {
    throw "P0 diagnostic failed. Review the terminal traceback; no formal run was authorized."
}

$ResolvedOutput = (Resolve-Path $Output).Path
$Hash = (Get-FileHash -Algorithm SHA256 $ResolvedOutput).Hash
Write-Host "[3/3] Complete."
Write-Host "Report: $ResolvedOutput"
Write-Host "SHA256: $Hash"
Write-Host "Send the JSON report and SHA256 back for scientific interpretation."
