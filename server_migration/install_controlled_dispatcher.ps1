# Install a dormant-by-default local, owner-approved scheduler.
# No GPU/Codex work is enqueued or authorized by this installer.
param(
    [ValidateSet("Status", "Install", "Disable")]
    [string]$Mode = "Status",
    [string]$RepoRoot = "E:\AI4science"
)
$ErrorActionPreference = "Stop"
$taskName = "AI4science-Controlled-Dispatcher"
$root = (Resolve-Path $RepoRoot).Path
$script = Join-Path $root "_local\automation\controlled_dispatcher.py"

if ($Mode -eq "Status") {
    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existing) {
        $info = Get-ScheduledTaskInfo -TaskName $taskName
        Write-Output "Task: $taskName; State: $($existing.State); Last: $($info.LastRunTime); Next: $($info.NextRunTime)"
    }
    else { Write-Output "Task: $taskName; NOT_INSTALLED" }
    if (Test-Path $script) {
        & python $script status --repo-root $root
        if ($LASTEXITCODE -ne 0) { throw "Private dispatcher status failed" }
    }
    else { Write-Output "Private dispatcher source is not staged yet" }
    exit 0
}

if ($Mode -eq "Disable") {
    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existing) {
        Disable-ScheduledTask -TaskName $taskName | Out-Null
        Write-Output "Disabled $taskName (private logs and approvals preserved)"
    }
    else { Write-Output "Nothing to disable" }
    exit 0
}

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    throw "Task already exists; refuse to overwrite the existing scheduler"
}
if (-not (Test-Path $script)) { throw "Expected private pinned source at $script" }
$python = & python -c "import sys; print(sys.executable)"
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $python)) { throw "No verified Python executable" }
$raw = & $python $script status --repo-root $root
if ($LASTEXITCODE -ne 0) { throw "Status preflight failed" }
$state = ($raw -join [Environment]::NewLine) | ConvertFrom-Json
if (@($state.jobs).Count -ne 0) {
    throw "Queue must be empty before installing scheduler. Inspect existing approvals first."
}
$action = New-ScheduledTaskAction -Execute $python -Argument ('"' + $script + '" tick --repo-root "' + $root + '"') -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes 30)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -StartWhenAvailable
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Owner-approved one-shot Codex review / V11 Windows HPO; empty queue does nothing" | Out-Null
Write-Output "INSTALLED: $taskName (every 30min, no approved jobs, no GPU launch)"
