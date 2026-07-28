param(
    [switch]$PreflightOnly
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = 'E:\AI4science\xrd_robustness'
$Python = 'E:\AI4science\.venvs\xrd_tools\Scripts\python.exe'
$Contract = Join-Path $ProjectRoot 'configs\v9_resnet_js_four_run.preregistered.json'
$Authorization = Join-Path $ProjectRoot 'configs\v9_resnet_js_four_run.authorization.json'
$OutputRoot = Join-Path $ProjectRoot 'outputs\v9_resnet_js_four_run_tuning_v1'
$Registry = Join-Path $OutputRoot 'registry.json'
$SummaryScript = Join-Path $ProjectRoot 'scripts\summarize_v9_resnet_js_four_run.py'
$TargetSteps = 61600
$SingleFactorProfiles = 'ood_shift_negative,ood_shift_positive,ood_broadening,ood_noise,ood_background,ood_texture'

Set-Location $ProjectRoot

foreach ($required in @(
    $Python,
    $Contract,
    $Authorization,
    $SummaryScript,
    (Join-Path $ProjectRoot 'scripts\train_cnn_contract_diagnostic.py'),
    (Join-Path $ProjectRoot 'configs\simulation.v9.method_transfer.frozen.json'),
    (Join-Path $ProjectRoot 'configs\evaluation.v9.method_transfer.json'),
    (Join-Path $ProjectRoot 'data\formal_14060\manifests\split_manifest.json'),
    (Join-Path $ProjectRoot 'data\formal_14060\manifests\v9_method_transfer_validation.csv')
)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required path is missing: $required"
    }
}

$contractPayload = Get-Content -LiteralPath $Contract -Raw | ConvertFrom-Json
$authorizationPayload = Get-Content -LiteralPath $Authorization -Raw | ConvertFrom-Json
$contractHash = (Get-FileHash -LiteralPath $Contract -Algorithm SHA256).Hash
if ($authorizationPayload.status -ne 'authorized_for_serial_validation_tuning') {
    throw 'Four-run authorization record is not active.'
}
if ($authorizationPayload.preregistered_contract.sha256 -ne $contractHash) {
    throw 'Authorization record does not match the preregistered contract hash.'
}
foreach ($sourceGroup in @(
    $authorizationPayload.optimized_generation_sources,
    $authorizationPayload.execution_sources
)) {
    foreach ($source in $sourceGroup.PSObject.Properties.Value) {
        $sourcePath = Join-Path $ProjectRoot ([string]$source.path)
        if (-not (Test-Path -LiteralPath $sourcePath)) {
            throw "Registered execution source is missing: $sourcePath"
        }
        $sourceHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
        if ($sourceHash -ne [string]$source.sha256) {
            throw "Registered execution source hash mismatch: $sourcePath"
        }
    }
}
if ($authorizationPayload.optimization_gate.status -ne 'passed' -or
    -not $authorizationPayload.optimization_gate.exact_spectrum_arrays -or
    [double]$authorizationPayload.optimization_gate.maximum_absolute_spectrum_difference -ne 0.0) {
    throw 'Online-generation optimization equivalence Gate is not passed.'
}
if ($contractPayload.execution.four_run_enabled) {
    throw 'The preregistration itself must remain immutable and fail-closed.'
}
if ($contractPayload.runs.Count -ne 4) {
    throw 'Preregistered run count is not four.'
}

$activeTrainer = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -match '^python(w)?\.exe$' -and
        $_.CommandLine -match 'train_(v7|cnn_contract_diagnostic)\.py'
    }
if ($activeTrainer) {
    $details = ($activeTrainer | ForEach-Object {
        "PID=$($_.ProcessId) $($_.CommandLine)"
    }) -join "`n"
    throw "Another training process is active:`n$details"
}
if ($PreflightOnly) {
    Write-Host 'FOUR_RUN_EXECUTION_PREFLIGHT_PASS'
    exit 0
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

New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
if (Test-Path -LiteralPath $Registry) {
    $registryPayload = Get-Content -LiteralPath $Registry -Raw | ConvertFrom-Json
} else {
    $registryPayload = [ordered]@{
        schema_version = 'v9-resnet-js-four-run-registry-v1'
        contract_sha256 = $contractHash
        execution = 'serial'
        runs = @()
    }
}

foreach ($run in $contractPayload.runs) {
    $runId = [string]$run.run_id
    $runDir = Join-Path $OutputRoot $runId
    $resultsPath = Join-Path $runDir 'results.json'
    if (Test-Path -LiteralPath $resultsPath) {
        Write-Host "=== Already completed; skipping $runId ==="
        continue
    }
    if (Test-Path -LiteralPath $runDir) {
        throw "Incomplete run directory exists and requires explicit recovery: $runDir"
    }

    $mode = if ($run.method -eq 'ordinary_dynamic_augmentation') {
        'dynamic_erm'
    } elseif ($run.method -eq 'js_consistency_transfer') {
        'dynamic_js'
    } else {
        throw "Unsupported method in frozen contract: $($run.method)"
    }
    $lambdaJs = ([double]$run.lambda_js).ToString(
        [System.Globalization.CultureInfo]::InvariantCulture
    )

    $entry = [ordered]@{
        run_id = $runId
        method = [string]$run.method
        lambda_js = [double]$run.lambda_js
        status = 'running'
        started_at = (Get-Date).ToString('o')
        completed_at = $null
        exit_code = $null
    }
    $registryPayload.runs += $entry
    $registryPayload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Registry -Encoding UTF8

    Write-Host "=== Starting $runId ($mode, lambda_js=$($run.lambda_js)) ==="
    & $Python -s scripts/train_cnn_contract_diagnostic.py `
      --mode $mode `
      --simulation-config configs/simulation.v9.method_transfer.frozen.json `
      --train-profile train `
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
      --early-stopping-ood-profiles $SingleFactorProfiles `
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
      --study-contract configs/v9_resnet_js_four_run.preregistered.json `
      --evaluation-contract configs/evaluation.v9.method_transfer.json `
      --run-id $runId `
      --learning-rate 0.0001 `
      --weight-decay 0.0001 `
      --lambda-js $lambdaJs `
      --device cuda `
      --output-dir $runDir `
      --run-dir-exact `
      --development-only `
      --allow-tf32 `
      --cudnn-benchmark `
      --cudnn-deterministic `
      --fused-adamw `
      --amp `
      --amp-dtype bfloat16 `
      --amp-fallback-to-float32 `
      --cnn-preprocessing identity `
      --cnn-optimizer adamw `
      --cnn-lr-schedule constant `
      --cnn-lr-warmup-steps 0 `
      --cnn-total-steps $TargetSteps `
      --cnn-preregistration $Contract

    $entry.exit_code = $LASTEXITCODE
    $entry.completed_at = (Get-Date).ToString('o')
    $entry.status = if ($LASTEXITCODE -eq 0) { 'completed' } else { 'failed' }
    $registryPayload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Registry -Encoding UTF8
    if ($LASTEXITCODE -ne 0) {
        throw "Run $runId failed with exit code $LASTEXITCODE"
    }
}

& $Python -s $SummaryScript --output-root $OutputRoot
if ($LASTEXITCODE -ne 0) {
    throw "Four-run summarization failed with exit code $LASTEXITCODE"
}
Write-Host '=== Four-run completed and summarized ==='
