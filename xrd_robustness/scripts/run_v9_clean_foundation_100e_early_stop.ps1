# Gate 1 continuation diagnostic: PAMPT-B3 Clean ERM with registered early stopping.
#
# Scientific question:
#   Was the 30-epoch Clean result merely undertrained?
#
# Maximum budget remains 100 epochs / 61,600 steps. Early stopping is evaluated
# every 10 epochs on level0 Validation Macro-F1, with in_range Macro-F1 used only
# as the built-in tie-breaker. No learning-rate, optimizer, scheduler, backbone,
# split, seed, rendering, normalization, batch, or panel change is introduced.

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = 'E:\AI4science\xrd_robustness'
$Python = 'E:\AI4science\.venvs\xrd_tools\Scripts\python.exe'
$RunId = 'foundation_clean_erm_100e_es50p3d002__seed_20260710'
$OutputDir = Join-Path $ProjectRoot "outputs\v9_foundation_diagnostics\$RunId"
$Watcher = Join-Path $ProjectRoot 'scripts\diagnostics\watch_training_progress_v3.ps1'
$SummaryScript = Join-Path $ProjectRoot 'scripts\diagnostics\summarize_early_stopped_clean_run.py'
$TargetSteps = 61600

Set-Location $ProjectRoot

foreach ($required in @(
    $Python,
    (Join-Path $ProjectRoot 'scripts\train_v7.py'),
    $Watcher,
    $SummaryScript,
    (Join-Path $ProjectRoot 'configs\simulation.v9.method_transfer.frozen.json'),
    (Join-Path $ProjectRoot 'data\formal_14060\manifests\split_manifest.json'),
    (Join-Path $ProjectRoot 'data\formal_14060\manifests\v9_method_transfer_validation.csv')
)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required path is missing: $required"
    }
}

if (Test-Path -LiteralPath $OutputDir) {
    throw "Refusing to overwrite an existing diagnostic run: $OutputDir"
}

$activeTrainer = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -match '^python(w)?\.exe$' -and
        $_.CommandLine -match 'scripts[\\/]train_v7\.py'
    }
if ($activeTrainer) {
    $details = ($activeTrainer | ForEach-Object {
        "PID=$($_.ProcessId) $($_.CommandLine)"
    }) -join "`n"
    throw "Another train_v7.py process is active. Stop it before this diagnostic:`n$details"
}

foreach ($name in @(
    'OMP_NUM_THREADS',
    'MKL_NUM_THREADS',
    'OPENBLAS_NUM_THREADS',
    'NUMEXPR_NUM_THREADS',
    'VECLIB_MAXIMUM_THREADS',
    'BLIS_NUM_THREADS'
)) {
    Set-Item -Path "Env:$name" -Value '2'
}
$env:CUDA_MODULE_LOADING = 'LAZY'

Write-Host '=== Gate 1 extension: PAMPT-B3 Clean ERM, max 100e with early stopping ==='
Write-Host "Output: $OutputDir"
Write-Host 'Primary stopping metric: level0 Validation Macro-F1'
Write-Host 'Rule: minimum 50 epochs; patience 3 validation checks; min_delta 0.002'
Write-Host 'Validation interval: every 10 epochs; maximum budget: 100 epochs'
Write-Host 'A separate PowerShell progress window will open automatically.'

$watchArguments = @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', $Watcher,
    '-RunDir', $OutputDir,
    '-TargetSteps', "$TargetSteps"
)
$WatcherProcess = Start-Process -FilePath 'powershell.exe' `
    -ArgumentList $watchArguments `
    -PassThru

try {
    & $Python -s scripts/train_v7.py `
      --mode clean_erm `
      --simulation-config configs/simulation.v9.method_transfer.frozen.json `
      --train-profile train `
      --clean-profile level0 `
      --in-range-profile in_range `
      --ood-profiles level0,ood_shift_negative,ood_shift_positive,ood_broadening,ood_noise,ood_background,ood_texture,ood_combo_shift_broadening,ood_combo_background_noise,ood_combo_texture_shift,ood_all `
      --variant b3 `
      --dataset-size 14060 `
      --data-root data/formal_14060 `
      --split-manifest data/formal_14060/manifests/split_manifest.json `
      --peak-cache-name peak_tables_v7_reflection `
      --epochs 100 `
      --max-optimizer-steps $TargetSteps `
      --validation-interval-steps 6160 `
      --early-stopping `
      --early-stopping-min-epochs 50 `
      --early-stopping-patience 3 `
      --early-stopping-min-delta 0.002 `
      --early-stopping-ood-profiles level0 `
      --batch-size 16 `
      --evaluation-batch-size 256 `
      --dynamic-prefetch-workers 16 `
      --dynamic-prefetch-batches 16 `
      --dynamic-prefetch-worker-native-threads 1 `
      --dynamic-prefetch-start-method spawn `
      --pin-memory `
      --non-blocking-h2d `
      --main-process-intraop-threads 2 `
      --main-process-interop-threads 1 `
      --float32-matmul-precision high `
      --seed 20260710 `
      --evaluation-seed 20260720 `
      --development-subset-manifest data/formal_14060/manifests/v9_method_transfer_validation.csv `
      --study-contract configs/algorithm.v9.method_transfer.json `
      --evaluation-contract configs/evaluation.v9.method_transfer.json `
      --run-id $RunId `
      --device cuda `
      --output-dir $OutputDir `
      --run-dir-exact `
      --development-only `
      --allow-tf32 `
      --cudnn-benchmark `
      --cudnn-deterministic `
      --fused-adamw `
      --amp `
      --amp-dtype bfloat16 `
      --amp-fallback-to-float32

    $TrainExitCode = $LASTEXITCODE
    if ($TrainExitCode -ne 0) {
        throw "Clean early-stopping diagnostic failed with exit code $TrainExitCode"
    }

    & $Python -s $SummaryScript `
      --run-dir $OutputDir `
      --output-json (Join-Path $OutputDir 'clean_early_stopping_summary.json') `
      --output-md (Join-Path $OutputDir 'clean_early_stopping_summary.md')

    $SummaryExitCode = $LASTEXITCODE
    if ($SummaryExitCode -ne 0) {
        throw "Training finished, but early-stopping summarization failed with exit code $SummaryExitCode"
    }

    Write-Host '=== Gate 1 Clean early-stopping diagnostic completed ==='
    Write-Host (Join-Path $OutputDir 'clean_early_stopping_summary.md')
}
finally {
    if ($null -ne $WatcherProcess -and -not $WatcherProcess.HasExited) {
        Stop-Process -Id $WatcherProcess.Id -Force -ErrorAction SilentlyContinue
    }
}

exit 0
