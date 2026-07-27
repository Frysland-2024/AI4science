# Foundation Gate 3: source-faithful ML4pXRDs ResNet-18-GN matched Clean comparison.
#
# This launcher does not ask Qoder to author or modify model code. Qoder's role is
# limited to pulling this registered implementation, supervising execution, and
# returning the generated reports unchanged.

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = 'E:\AI4science\xrd_robustness'
$Python = 'E:\AI4science\.venvs\xrd_tools\Scripts\python.exe'
$PamptRunId = 'foundation_clean_erm_100e_es50p3d002__seed_20260710'
$PamptRunDir = Join-Path $ProjectRoot "outputs\v9_foundation_diagnostics\$PamptRunId"
$PamptSummary = Join-Path $PamptRunDir 'clean_early_stopping_summary.json'
$SanityRunId = 'foundation_gate3_ml4pxrd_resnet18_sanity__seed_20260710'
$SanityDir = Join-Path $ProjectRoot "outputs\v9_foundation_diagnostics\$SanityRunId"
$SanityReport = Join-Path $SanityDir 'gate3_resnet_sanity.json'
$RunId = 'foundation_gate3_ml4pxrd_resnet18_clean_100e_es50p3d002__seed_20260710'
$OutputDir = Join-Path $ProjectRoot "outputs\v9_foundation_diagnostics\$RunId"
$Watcher = Join-Path $ProjectRoot 'scripts\diagnostics\watch_training_progress_v3.ps1'
$SanityScript = Join-Path $ProjectRoot 'scripts\diagnostics\gate3_resnet_sanity.py'
$TrainScript = Join-Path $ProjectRoot 'scripts\train_gate3_resnet.py'
$SummaryScript = Join-Path $ProjectRoot 'scripts\diagnostics\summarize_gate3_resnet.py'
$TargetSteps = 61600

Set-Location $ProjectRoot

foreach ($required in @(
    $Python,
    $PamptSummary,
    $Watcher,
    $SanityScript,
    $TrainScript,
    $SummaryScript,
    (Join-Path $ProjectRoot 'src\xrd_robustness\models\ml4pxrd_resnet1d.py'),
    (Join-Path $ProjectRoot 'configs\simulation.v9.method_transfer.frozen.json'),
    (Join-Path $ProjectRoot 'data\formal_14060\manifests\split_manifest.json'),
    (Join-Path $ProjectRoot 'data\formal_14060\manifests\v9_method_transfer_validation.csv')
)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required path is missing: $required"
    }
}

$PamptReport = Get-Content -LiteralPath $PamptSummary -Raw | ConvertFrom-Json
$PamptLevel0 = [double]$PamptReport.selected_best.level0_macro_f1
Write-Host "PAMPT selected best level0 Macro-F1: $PamptLevel0"
if ($PamptLevel0 -ge 0.80) {
    Write-Host 'Gate 3 is not opened because PAMPT passed the registered Clean learnability threshold.'
    Write-Host 'Do not start the ResNet full run; investigate Dynamic training instead.'
    exit 0
}

if (Test-Path -LiteralPath $OutputDir) {
    throw "Refusing to overwrite an existing Gate-3 full run: $OutputDir"
}

$activeTrainer = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -match '^python(w)?\.exe$' -and
        $_.CommandLine -match '(train_v7|train_gate3_resnet|gate3_resnet_sanity)\.py'
    }
if ($activeTrainer) {
    $details = ($activeTrainer | ForEach-Object {
        "PID=$($_.ProcessId) $($_.CommandLine)"
    }) -join "`n"
    throw "Another diagnostic/training process is active. Wait for it or stop it before Gate 3:`n$details"
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

$ReuseSanity = $false
if (Test-Path -LiteralPath $SanityDir) {
    if (-not (Test-Path -LiteralPath $SanityReport)) {
        throw "Existing sanity directory has no report; inspect manually: $SanityDir"
    }
    $ExistingSanity = Get-Content -LiteralPath $SanityReport -Raw | ConvertFrom-Json
    if ($ExistingSanity.status -ne 'pass') {
        throw "Existing Gate-3 sanity report did not pass: $SanityReport"
    }
    $ReuseSanity = $true
    Write-Host "Reusing passed sanity report: $SanityReport"
}

if (-not $ReuseSanity) {
    Write-Host '=== Gate 3A/3B: ResNet source-port sanity gates ==='
    & $Python -s $SanityScript `
      --simulation-config configs/simulation.v9.method_transfer.frozen.json `
      --data-root data/formal_14060 `
      --split-manifest data/formal_14060/manifests/split_manifest.json `
      --peak-cache-name peak_tables_v7_reflection `
      --output-dir $SanityDir `
      --seed 20260710 `
      --tiny-size 32 `
      --batch-size 16 `
      --max-overfit-steps 3000 `
      --check-interval 20 `
      --learning-rate 0.001 `
      --weight-decay 0.0 `
      --required-accuracy 0.95 `
      --device cuda

    $SanityExitCode = $LASTEXITCODE
    if ($SanityExitCode -ne 0) {
        throw "Gate-3 sanity gates failed with exit code $SanityExitCode. Full training is blocked."
    }
}

Write-Host '=== Gate 3C: ML4pXRDs ResNet-18-GN matched Clean run ==='
Write-Host "Output: $OutputDir"
Write-Host 'Only the backbone changes relative to the PAMPT Clean contract.'
Write-Host 'Primary metric: selected best level0 Validation Macro-F1.'
Write-Host 'Rule: minimum 50 epochs; patience 3 validation checks; min_delta 0.002.'

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
    & $Python -s $TrainScript `
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
        throw "Gate-3 ResNet training failed with exit code $TrainExitCode"
    }

    & $Python -s $SummaryScript `
      --run-dir $OutputDir `
      --pampt-summary $PamptSummary `
      --sanity-report $SanityReport `
      --output-json (Join-Path $OutputDir 'gate3_resnet_summary.json') `
      --output-md (Join-Path $OutputDir 'gate3_resnet_summary.md')

    $SummaryExitCode = $LASTEXITCODE
    if ($SummaryExitCode -ne 0) {
        throw "Gate-3 training finished, but summarization failed with exit code $SummaryExitCode"
    }

    Copy-Item -LiteralPath (Join-Path $OutputDir 'gate3_resnet_summary.json') `
      -Destination (Join-Path $OutputDir 'gate3_pampt_vs_resnet.json')
    Copy-Item -LiteralPath (Join-Path $OutputDir 'gate3_resnet_summary.md') `
      -Destination (Join-Path $OutputDir 'gate3_pampt_vs_resnet.md')

    Write-Host '=== Foundation Gate 3 completed ==='
    Write-Host (Join-Path $OutputDir 'gate3_pampt_vs_resnet.md')
}
finally {
    if ($null -ne $WatcherProcess -and -not $WatcherProcess.HasExited) {
        Stop-Process -Id $WatcherProcess.Id -Force -ErrorAction SilentlyContinue
    }
}

exit 0
