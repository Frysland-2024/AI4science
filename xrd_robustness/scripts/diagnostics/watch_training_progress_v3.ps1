param(
    [Parameter(Mandatory = $true)]
    [string]$RunDir,
    [int]$TargetSteps = 0,
    [int]$PollSeconds = 5
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$RunPath = [System.IO.Path]::GetFullPath($RunDir)
$HistoryPath = Join-Path $RunPath 'history.json'
$ConfigPath = Join-Path $RunPath 'config_resolved.json'
$RunLeaf = Split-Path $RunPath -Leaf
Write-Host "Watching training progress: $RunPath"
Write-Host 'Press Ctrl+C to stop only this watcher; training continues.'
$lastSeenStep = -1
$lastStatus = ''
while ($true) {
    if ($TargetSteps -le 0 -and (Test-Path -LiteralPath $ConfigPath)) {
        try {
            $config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
            if ($null -ne $config.max_optimizer_steps) { $TargetSteps = [int]$config.max_optimizer_steps }
        } catch {}
    }
    $epoch = 0; $step = 0; $trainAccuracy = $null; $trainLoss = $null; $inRangeF1 = $null; $meanOodF1 = $null
    if (Test-Path -LiteralPath $HistoryPath) {
        try {
            $parsed = Get-Content -LiteralPath $HistoryPath -Raw | ConvertFrom-Json
            if ($parsed -is [System.Array]) { $history = $parsed } elseif ($null -eq $parsed) { $history = @() } else { $history = @($parsed) }
            if ($history.Count -gt 0) {
                $last = $history[$history.Count - 1]
                $epoch = [int]$last.epoch
                $step = [int]$last.global_step
                $trainAccuracy = $last.train_accuracy
                $trainLoss = $last.train_loss
                $lastPropertyNames = @($last.PSObject.Properties.Name)
                if ($lastPropertyNames -contains 'in_range' -and $null -ne $last.in_range) {
                    $inRangeF1 = $last.in_range.macro_f1
                }
                if ($lastPropertyNames -contains 'ood' -and $null -ne $last.ood) {
                    $profiles = @('ood_shift_negative','ood_shift_positive','ood_broadening','ood_noise','ood_background','ood_texture')
                    $values = @()
                    $oodPropertyNames = @($last.ood.PSObject.Properties.Name)
                    foreach ($profile in $profiles) {
                        if ($oodPropertyNames -contains $profile) {
                            $panel = $last.ood.$profile
                            if ($null -ne $panel -and $null -ne $panel.macro_f1) { $values += [double]$panel.macro_f1 }
                        }
                    }
                    if ($values.Count -gt 0) { $meanOodF1 = ($values | Measure-Object -Average).Average }
                }
            }
        } catch { Write-Warning "Progress parse failed: $($_.Exception.Message)" }
    }
    $percent = if ($TargetSteps -gt 0) { [math]::Min(100.0, 100.0 * $step / $TargetSteps) } else { 0.0 }
    $parts = @("Epoch $epoch", "Step $step/$TargetSteps")
    if ($null -ne $trainAccuracy) { $parts += ('Train Acc {0:P1}' -f [double]$trainAccuracy) }
    if ($null -ne $trainLoss) { $parts += ('Loss {0:F4}' -f [double]$trainLoss) }
    if ($null -ne $inRangeF1) { $parts += ('ID F1 {0:F4}' -f [double]$inRangeF1) }
    if ($null -ne $meanOodF1) { $parts += ('OOD F1 {0:F4}' -f [double]$meanOodF1) }
    $status = $parts -join ' | '
    Write-Progress -Activity "XRD training: $RunLeaf" -Status $status -PercentComplete $percent
    if ($step -ne $lastSeenStep -or $status -ne $lastStatus) {
        Write-Host ('[{0,6:F2}%] {1}' -f $percent, $status)
        $lastSeenStep = $step; $lastStatus = $status
    }
    if ($TargetSteps -gt 0 -and $step -ge $TargetSteps) { break }
    Start-Sleep -Seconds $PollSeconds
}
Write-Progress -Activity "XRD training: $RunLeaf" -Completed
Write-Host 'Progress watcher finished.'
