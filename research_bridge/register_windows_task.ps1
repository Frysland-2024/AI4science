# Optional opt-in: Windows Task Scheduler checks for one approved issue every 5 min.
# Run only AFTER validating Codex ChatGPT login, gh login, and one supervised run.
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$name = 'AI4science-Codex-Bridge'
$powershell = (Get-Command powershell.exe -ErrorAction Stop).Source
$runner = Join-Path $PSScriptRoot 'run_scheduled.ps1'
$action = New-ScheduledTaskAction -Execute $powershell -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $runner + '"') -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(2)) -RepetitionInterval (New-TimeSpan -Minutes 5)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -StartWhenAvailable
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Description 'Read-only GitHub -> Codex task bridge' -Force | Out-Null
Write-Host "Registered $name for the current user. Use Get-ScheduledTask to inspect it."
