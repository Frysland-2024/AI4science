# Research Supervisor (observer only): every 10 minutes on this Windows host.
# Will not start/stop/restart Codex or GPU jobs. Safe to run alongside worker.
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = (Get-Command python -ErrorAction Stop).Source
$name = 'AI4science-Research-Supervisor'

& $python -m research_bridge.supervisor --repo-root $repo --bootstrap
if ($LASTEXITCODE -ne 0) { throw 'Could not bootstrap supervisor. Not installing.' }
& $python -m research_bridge.supervisor --repo-root $repo --once --dry-run
if ($LASTEXITCODE -ne 0) { throw 'Supervisor dry run failed. Not installing.' }

$action = New-ScheduledTaskAction -Execute $python -Argument '-m research_bridge.supervisor --once' -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(2)) -RepetitionInterval (New-TimeSpan -Minutes 10)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 3) -StartWhenAvailable
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Description 'AI4science observer only; statuses and no automatic training' -Force | Out-Null
Write-Host "Registered $name every 10 minutes. It never launches a scientific job."
