# Windows Task Scheduler: check GitHub every 30 minutes for approved tasks.
# Requires previously verified GitHub CLI + Codex ChatGPT login and one supervised run.
# Does not wake PC, does not run while powered off, and does not auto-merge PRs.
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = (Get-Command python -ErrorAction Stop).Source
$name = 'AI4science-Codex-Bridge'
$action = New-ScheduledTaskAction -Execute $python -Argument '-m research_bridge.worker --once' -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(2)) -RepetitionInterval (New-TimeSpan -Minutes 30)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -StartWhenAvailable
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Description 'Approved read-only / draft-PR research task bridge (30m)' -Force | Out-Null
Write-Host "Registered $name every 30 minutes with no fixed execution time limit. Use Get-ScheduledTask to inspect."

