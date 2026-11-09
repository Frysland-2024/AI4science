# Native Windows V11 HPO: keep scientific training in one_click_v11.py.
# Usage: powershell -ExecutionPolicy Bypass -File server_migration/start_windows.ps1 -Mode plan|smoke|hpo|export
param(
    [ValidateSet("plan", "smoke", "benchmark", "hpo", "export")]
    [string]$Mode = "plan",
    [string]$Python = "python",
    [string]$Output = "",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RunnerArgs
)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $root
try {
    function Invoke-Python([string[]]$Arguments) {
        & $Python @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Python command failed with exit code $LASTEXITCODE : $($Arguments -join ' ')"
        }
    }
    if ($Mode -eq "export") {
        if (-not $Output) { $Output = Join-Path $root "_local\v11_hpo_handoff.zip" }
        Invoke-Python -Arguments @("server_migration/hpo_handoff.py", "export", "--root", $root, "--archive", $Output)
        Write-Output "HPO handoff created: $Output; transfer privately with SHA256."
        exit 0
    }
    # No source snapshot, Test, or RRUFF required for Windows HPO.
    # These two check the frozen manifest and ideal PeakTables, not model scores.
    $rawStructureManifest = Join-Path $root "structure_library\merged_154975_parent_split_20261103\delivery_validation.json"
    if (Test-Path $rawStructureManifest) {
        Invoke-Python -Arguments @("server_migration/verify_payload.py", "--root", ".", "--check-records")
    }
    else {
        Write-Warning "Raw structure source kit not installed locally; relying on frozen Train/Validation manifest SHA + fully audited PeakTables. Preserve external source-audit receipt."
    }
    Invoke-Python -Arguments @("server_migration/verify_peak_cache.py", "--root", ".", "--fast")
    if ($Mode -eq "benchmark") {
        $benchOutput = Join-Path $root "_local\\v11_batch_benchmark.json"
        Invoke-Python -Arguments (@("server_migration/benchmark_windows_v11.py", "--output", $benchOutput) + $RunnerArgs)
        Write-Output "TRAIN-only bounded batch benchmark: $benchOutput (no HPO launched)."
        exit 0
    }
    # 16 GB VRAM / 32 GB RAM candidate: conservative prefetch by default.
    if (!$RunnerArgs -or $RunnerArgs.Count -eq 0) {
        $RunnerArgs = @("--prefetch-workers", "2", "--prefetch-batches", "2", "--worker-peak-cache", "256")
    }
    if ($Mode -eq "plan") {
        Invoke-Python -Arguments (@("server_migration/one_click_v11.py", "--mode", "plan") + $RunnerArgs)
        Write-Output "PLAN complete: no GPU training started."
    }
    elseif ($Mode -eq "smoke") {
        Invoke-Python -Arguments @("server_migration/one_click_v11.py", "--mode", "smoke")
        Invoke-Python -Arguments @("server_migration/windows_cuda_smoke.py")
        Invoke-Python -Arguments @("server_migration/smoke_prefetch.py", "--workers", "2", "--batch-size", "16")
        Write-Output "BOUNDED preflight completed. Full Stage 0 still requires resource/Validation/restart checks."
    }
    else {
        # This is an explicit HPO launch, NOT an implicit result of plan/smoke.
        # Use the SAME locked options (including worker count, budget and batch)
        # when later calling Linux --final on the imported handoff.
        Invoke-Python -Arguments (@("server_migration/one_click_v11.py", "--mode", "run") + $RunnerArgs)
        $result = Join-Path $root "server_runs\v11_a0_js_optuna\final_recommendation.json"
        if (!(Test-Path $result)) {
            throw "HPO/confirmation incomplete. Resume with the exact same command; do not export."
        }
        Write-Output "HPO completed; export separately with -Mode export."
    }
}
finally { Pop-Location }
