# Native Windows V11 HPO: keep scientific training in one_click_v11.py.
# Usage: powershell -ExecutionPolicy Bypass -File server_migration/start_windows.ps1 -Mode plan|smoke|benchmark|hpo|export
# Auto CPU tuning only for verified Ryzen 9 7945HX + >=30GiB RAM.
# Unknown CPUs (including cuifa until measured) retain conservative defaults.
param(
    [ValidateSet("plan", "smoke", "benchmark", "hpo", "export")]
    [string]$Mode = "plan",
    [string]$Python = "python",
    [string]$Output = "",
    [ValidateSet("auto", "conservative", "ryzen7945hx")]
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
        $resolvedProfile = "conservative"
        try {
            $cpuName = [string](Get-CimInstance Win32_Processor |
                Select-Object -First 1 -ExpandProperty Name)
            $ramBytes = [double](Get-CimInstance Win32_ComputerSystem |
                Select-Object -First 1 -ExpandProperty TotalPhysicalMemory)
            if ($cpuName -match "7945HX" -and $ramBytes -ge 30GB) {
                $resolvedProfile = "ryzen7945hx"
            }
        }
        catch {
            Write-Warning "CPU auto-detection unavailable; using conservative resources."
        }
    }
    if ($resolvedProfile -eq "ryzen7945hx") {
        # 2026-11-09 full-pipeline Windows comparison: 12 workers ~= 168
        # parent/s; 4 workers ~= 82 parent/s, equal paired-spectrum SHA.
        $runtimeDefaults = [ordered]@{
            "--prefetch-workers" = "12"
            "--prefetch-batches" = "4"
            "--worker-peak-cache" = "64"
            "--native-threads" = "1"
        }
    }
    else {
        $runtimeDefaults = [ordered]@{
            "--prefetch-workers" = "2"
            "--prefetch-batches" = "2"
            "--worker-peak-cache" = "256"
            "--native-threads" = "1"
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
    if ($resolvedProfile -eq "ryzen7945hx") {
        # 12-worker full six-profile Validation reached 5.8GiB free on this
        # 32GiB host. Warn rather than silently changing a frozen HPO contract.
        try {
            $freeKiB = [double](Get-CimInstance Win32_OperatingSystem |
                Select-Object -First 1 -ExpandProperty FreePhysicalMemory)
            $availableGiB = [math]::Round(($freeKiB * 1KB) / 1GB, 1)
            if ($availableGiB -lt 14) {
                Write-Warning "CPU12 profile: only $availableGiB GiB RAM currently free; close background apps before long HPO, or choose -CpuProfile conservative BEFORE creating its study."
            }
        }
        catch {
            Write-Warning "Unable to read available RAM; monitor memory during CPU12 HPO."
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
