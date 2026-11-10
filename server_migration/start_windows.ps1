# Native Windows V11 HPO: keep scientific training in one_click_v11.py.
# Usage: powershell -ExecutionPolicy Bypass -File server_migration/start_windows.ps1 -Mode plan|smoke|benchmark|hpo|export
# Conservative Windows default: laptop-verified 12 workers / 4 queues /
# 64 cached PeakTables, independent of RAM size and CPU model.
# Optional aggressive16 is unverified on cuifa.
param(
    [ValidateSet("plan", "smoke", "benchmark", "gradient", "hpo", "export")]
    [string]$Mode = "plan",
    [string]$Python = "python",
    [string]$Output = "",
    [ValidateSet("auto", "conservative", "ryzen7945hx", "performance12", "aggressive16")]
    [string]$CpuProfile = "auto",
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
    # Choose only engineering resources: never change batch, sampler, seed,
    # HPO epochs, model or loss. The selected resources are frozen in the study
    # contract, so a resume on the same host uses identical options.
    $resolvedProfile = $CpuProfile
    if ($CpuProfile -eq "auto") {
        # No machine-size / CPU-model branching. Keep the same tested
        # 12-worker default on both Windows hosts.
        $resolvedProfile = "conservative"
    }
    if ($resolvedProfile -in @("conservative", "ryzen7945hx", "performance12")) {
        # Actual 7945HX Windows GPU+CPU benchmark: 12 workers ~= 168
        # parent/s vs 4 workers ~= 82; paired-spectrum SHA unchanged.
        # performance12 on cuifa is PROVISIONAL, not an observed speed.
        $runtimeDefaults = [ordered]@{
            "--prefetch-workers" = "12"
            "--prefetch-batches" = "4"
            "--worker-peak-cache" = "64"
            "--native-threads" = "1"
        }
    }
    elseif ($resolvedProfile -eq "aggressive16") {
        # Higher CPU concurrency is explicitly opt-in. Limit worker PeakTable
        # caches on 32GiB RAM; cannot claim this is faster until tested.
        $runtimeDefaults = [ordered]@{
            "--prefetch-workers" = "16"
            "--prefetch-batches" = "4"
            "--worker-peak-cache" = "32"
            "--native-threads" = "1"
        }
    }
    # RTX 4060 real-Train throughput sweep (2026-11-10): the source-
    # compatible effective parent batch is 16, with microbatch 16 (no
    # accumulation). 64-step sustained Train-only throughput was 170.74
    # parents/s (vs 68.17 at micro2); PyTorch reserved peak 0.461 GiB.
    # Larger effective batches (32/64/128/256) were hardware benchmarked,
    # but would CHANGE optimizer statistics and INVALIDATE the frozen
    # 108478-parent Train-only lambda gradient contract. Do NOT auto-upgrade
    # the scientific effective batch simply because GPU RAM permits it.
    # GPU microbatch 16 here is a launcher default, not a Cuifa speed claim.
    if ($Mode -eq "hpo") {
        if (@($RunnerArgs) -notcontains "--batch-size") {
            $RunnerArgs = @($RunnerArgs) + @("--batch-size", "16")
        }
        if (@($RunnerArgs) -notcontains "--microbatch-size") {
            $RunnerArgs = @($RunnerArgs) + @("--microbatch-size", "16")
        }
    }
    # User-supplied flags take precedence individually. Passing --batch-size
    # must not silently reset CPU prefetch settings to generic Python defaults.
    $provided = @($RunnerArgs)
    foreach ($flag in $runtimeDefaults.Keys) {
        if ($provided -notcontains [string]$flag) {
            $RunnerArgs = @($RunnerArgs) + @([string]$flag, [string]$runtimeDefaults[$flag])
        }
    }
    $selectedWorkerIndex = [Array]::IndexOf([string[]]$RunnerArgs, "--prefetch-workers")
    $selectedWorkers = [string]$RunnerArgs[$selectedWorkerIndex + 1]
    if ($resolvedProfile -in @("conservative", "ryzen7945hx", "performance12", "aggressive16")) {
        # Laptop's 12-worker + full Validation run bottomed at 5.8GiB free.
        # A 16-worker Cuifa configuration is untested; fail closed for
        # HPO if it starts with insufficient RAM. NEVER change settings
        # silently after Optuna state has frozen a study contract.
        try {
            $freeKiB = [double](Get-CimInstance Win32_OperatingSystem |
                Select-Object -First 1 -ExpandProperty FreePhysicalMemory)
            $availableGiB = [math]::Round(($freeKiB * 1KB) / 1GB, 1)
            $thresholdGiB = if ($resolvedProfile -eq "aggressive16") { 18 } else { 14 }
            if ($availableGiB -lt $thresholdGiB) {
                $message = "CPU $resolvedProfile profile: only $availableGiB GiB RAM available (recommended >=$thresholdGiB GiB at launch). Close background apps before long training; current resource profile will not be changed."
                if ($Mode -eq "hpo" -and $resolvedProfile -eq "aggressive16") {
                    throw $message
                }
                Write-Warning $message
            }
        }
        catch {
            # Safety guard must propagate, not be swallowed as a benign probe
            # failure; first-party HPO commands should not ignore low RAM.
            if ($Mode -eq "hpo" -and $resolvedProfile -eq "aggressive16") { throw }
            Write-Warning "Unable to verify RAM headroom for $resolvedProfile; monitor memory during the smoke benchmark."
        }
    }
    Write-Output "V11 CPU profile=$resolvedProfile; selected workers=$selectedWorkers; resources are study-bound."
    if ($Mode -eq "plan") {
        Invoke-Python -Arguments (@("server_migration/one_click_v11.py", "--mode", "plan") + $RunnerArgs)
        Write-Output "PLAN complete: no GPU training started."
    }
    elseif ($Mode -eq "smoke") {
        Invoke-Python -Arguments @("server_migration/one_click_v11.py", "--mode", "smoke")
        Invoke-Python -Arguments @("server_migration/windows_cuda_smoke.py")
        Invoke-Python -Arguments @("server_migration/smoke_prefetch.py", "--workers", $selectedWorkers, "--batch-size", "16")
        Write-Output "BOUNDED preflight completed. Full Stage 0 still requires resource/Validation/restart checks."
    }
    elseif ($Mode -eq "gradient") {
        # Laptop-only TRAIN-gradient calibration; NO synthetic Validation
        # rendering, Optuna trial or RRUFF/Test access.
        Invoke-Python -Arguments (@("server_migration/one_click_v11.py", "--mode", "gradient") + $RunnerArgs)
        $evidence = Join-Path $root "server_migration\gradient_gate_v11_train_108478.json"
        if (!(Test-Path $evidence)) {
            throw "Gradient calibration incomplete. No HPO may start without the frozen result."
        }
        Write-Output "TRAIN-only gradient audit completed. Evidence staged at: $evidence"
    }
    else {
        # This is an explicit HPO launch, NOT an implicit result of plan/smoke.
        # Persist exact scientific options for resume. Linux final may change
        # audited CPU-only runtime resources, not the selected HPO parameters.
        Invoke-Python -Arguments (@("server_migration/one_click_v11.py", "--mode", "run") + $RunnerArgs)
        $result = Join-Path $root "server_runs\v11_a0_js_optuna\final_recommendation.json"
        if (!(Test-Path $result)) {
            throw "HPO/confirmation incomplete. Resume with the exact same command; do not export."
        }
        Write-Output "HPO completed; export separately with -Mode export."
    }
}
finally { Pop-Location }
