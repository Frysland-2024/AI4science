# Cheap preflight for the foundation diagnostic code.
#
# This script does not train a model. It first runs the report generator's
# synthetic self-test, then reproduces the known metrics from the completed
# 30-epoch Dynamic ERM split pilot.

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = 'E:\AI4science\xrd_robustness'
$Python = 'E:\AI4science\.venvs\xrd_tools\Scripts\python.exe'
$SummaryScript = Join-Path $ProjectRoot 'scripts\diagnostics\summarize_training_run.py'
$DynamicRun = Join-Path $ProjectRoot 'outputs\v9_split_pilot_erm_30e\split_pilot_dynamic_erm_30e__seed_20260710'
$ReportJson = Join-Path $ProjectRoot 'reports\v9_foundation_dynamic_split_pilot_summary.json'
$ReportMarkdown = Join-Path $ProjectRoot 'reports\v9_foundation_dynamic_split_pilot_summary.md'

Set-Location $ProjectRoot

foreach ($required in @($Python, $SummaryScript, (Join-Path $DynamicRun 'history.json'))) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required preflight path is missing: $required"
    }
}

Write-Host '=== Foundation diagnostics preflight: synthetic self-test ==='
& $Python -s $SummaryScript --run-dir $DynamicRun --self-test
if ($LASTEXITCODE -ne 0) {
    throw "Synthetic summary self-test failed with exit code $LASTEXITCODE"
}

Write-Host '=== Foundation diagnostics preflight: reproduce existing Dynamic pilot ==='
& $Python -s $SummaryScript `
    --run-dir $DynamicRun `
    --output-json $ReportJson `
    --output-md $ReportMarkdown
if ($LASTEXITCODE -ne 0) {
    throw "Existing-run summary failed with exit code $LASTEXITCODE"
}

$Report = Get-Content -LiteralPath $ReportJson -Raw | ConvertFrom-Json
$Final = $Report.evaluation.final
$ExpectedId = 0.4212
$ExpectedOod = 0.3557
$Tolerance = 0.0006

$IdError = [math]::Abs([double]$Final.in_range_macro_f1 - $ExpectedId)
$OodError = [math]::Abs([double]$Final.mean_single_factor_ood_macro_f1 - $ExpectedOod)
if ($IdError -gt $Tolerance) {
    throw "Dynamic pilot ID reproduction failed: observed=$($Final.in_range_macro_f1), expected~=$ExpectedId"
}
if ($OodError -gt $Tolerance) {
    throw "Dynamic pilot OOD reproduction failed: observed=$($Final.mean_single_factor_ood_macro_f1), expected~=$ExpectedOod"
}

Write-Host '=== PREFLIGHT PASS ==='
Write-Host "Reproduced final Dynamic ID Macro-F1: $($Final.in_range_macro_f1)"
Write-Host "Reproduced final mean single-factor OOD Macro-F1: $($Final.mean_single_factor_ood_macro_f1)"
Write-Host "Report: $ReportMarkdown"
exit 0
