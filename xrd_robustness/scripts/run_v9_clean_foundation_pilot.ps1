# Gate 1 foundation diagnostic: PAMPT-B3 Clean ERM, fixed 30-epoch budget.
#
# Purpose:
#   1. Test whether the current data/rendering/backbone can learn the minimally
#      perturbed level0 task.
#   2. Preserve in_range and all existing OOD panels for matched comparison.
#
# This is isolated development evidence. It does not touch the registered 7-run
# queue, simulated Test, real XRD, real adaptation, or V10.

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = 'E:\AI4science\xrd_robustness'
$Python = 'E:\AI4science\.venvs\xrd_tools\Scripts\python.exe'
$RunId = 'foundation_clean_erm_30e__seed_20260710'
$OutputDir = Join-Path $ProjectRoot "outputs\v9_foundation_diagnostics\$RunId"

Set-Location $ProjectRoot

foreach ($required in @(
    $Python,
    (Join-Path $ProjectRoot 'scripts\train_v7.py'),
    (Join-Path $ProjectRoot 'scripts\diagnostics\summarize_training_run.py'),
    (Join-Path $ProjectRoot 'configs\simulation.v9.method_transfer.frozen.json'),
    (Join-Path $ProjectRoot 'data\formal_14060\manifests\split_manifest.json')
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
    $details = ($activeTrainer | ForEach-Object { "PID=$($_.ProcessId) $($_.CommandLine)" }) -join "`n"
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

Write-Host '=== Gate 1: PAMPT-B3 Clean ERM foundation pilot ==='
Write-Host "Output: $OutputDir"
Write-Host 'Training profile: level0 (minimally perturbed; not mathematically noise-free)'
Write-Host 'Evaluation: level0 + in_range + the existing OOD panels'

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
  --epochs 30 `
  --max-optimizer-steps 18480 `
  --validation-interval-steps 6160 `
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
    throw "Clean foundation pilot failed with exit code $TrainExitCode"
}

& $Python -s scripts/diagnostics/summarize_training_run.py `
  --run-dir $OutputDir `
  --output-json (Join-Path $OutputDir 'foundation_diagnostic_summary.json') `
  --output-md (Join-Path $OutputDir 'foundation_diagnostic_summary.md')

$SummaryExitCode = $LASTEXITCODE
if ($SummaryExitCode -ne 0) {
    throw "Training finished, but diagnostic summarization failed with exit code $SummaryExitCode"
}

Write-Host '=== Gate 1 completed ==='
Write-Host (Join-Path $OutputDir 'foundation_diagnostic_summary.md')
exit 0
