<#
.SYNOPSIS
Read-only monitor for long-running local AI4science training jobs on Windows.

.DESCRIPTION
The script never starts, stops, resumes, or modifies a training process. It only:
  - discovers matching Python processes;
  - samples NVIDIA GPU utilization and memory through nvidia-smi;
  - watches the most recently modified log/checkpoint/report file;
  - checks free disk space;
  - writes a local heartbeat JSON and CSV history under .monitoring/.

Typical use from the repository root:

  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\monitor_training.ps1 `
    -WatchPath ".\xrd_robustness\outputs" `
    -IntervalSeconds 20 `
    -ShowLogTail

To narrow process matching, pass a regular expression found in the training command line:

  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\monitor_training.ps1 `
    -WatchPath ".\xrd_robustness\outputs\v9_resnet_js_four_run" `
    -ProcessPattern "v9_resnet_js_four_run|lambda.?60" `
    -ShowLogTail

Use -Once for a one-shot status check.
#>

[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [string]$WatchPath = "",
    [string]$LogPath = "",
    [string]$ProcessPattern = "",
    [ValidateRange(5, 3600)]
    [int]$IntervalSeconds = 30,
    [ValidateRange(1, 1440)]
    [int]$StaleMinutes = 30,
    [ValidateRange(1, 1440)]
    [int]$GpuIdleMinutes = 10,
    [ValidateRange(1, 1000)]
    [int]$LowDiskGB = 10,
    [ValidateRange(1, 100)]
    [int]$LogTailLines = 12,
    [switch]$ShowLogTail,
    [switch]$NoBeep,
    [switch]$Once
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-FullPath {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [string]$BasePath = ""
    )

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }

    if ([string]::IsNullOrWhiteSpace($BasePath)) {
        $BasePath = (Get-Location).Path
    }

    return [System.IO.Path]::GetFullPath((Join-Path $BasePath $Path))
}

function Find-NvidiaSmi {
    $command = Get-Command "nvidia-smi.exe" -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        return $command.Source
    }

    $candidates = @(
        "$env:ProgramFiles\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
        "$env:SystemRoot\System32\nvidia-smi.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return $candidate
        }
    }

    return $null
}

function Get-GpuSnapshot {
    param([string]$NvidiaSmi)

    if ([string]::IsNullOrWhiteSpace($NvidiaSmi)) {
        return @()
    }

    try {
        $rows = & $NvidiaSmi `
            --query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw `
            --format=csv,noheader,nounits 2>$null

        $result = @()
        foreach ($row in $rows) {
            $parts = $row -split ",\s*"
            if ($parts.Count -lt 7) {
                continue
            }

            $result += [pscustomobject]@{
                index         = [int]$parts[0]
                name          = $parts[1]
                utilization   = [double]$parts[2]
                memory_used   = [double]$parts[3]
                memory_total  = [double]$parts[4]
                temperature_c = [double]$parts[5]
                power_w       = [double]$parts[6]
            }
        }
        return $result
    }
    catch {
        return @()
    }
}

function Get-TrainingProcesses {
    param(
        [string]$Pattern,
        [string]$RepositoryRoot
    )

    $pythonProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match "^(python|pythonw)(\.exe)?$" }

    if (-not [string]::IsNullOrWhiteSpace($Pattern)) {
        $pythonProcesses = $pythonProcesses |
            Where-Object { ($_.CommandLine -as [string]) -match $Pattern }
    }
    else {
        $escapedRepo = [regex]::Escape($RepositoryRoot)
        $pythonProcesses = $pythonProcesses |
            Where-Object {
                $commandLine = $_.CommandLine -as [string]
                $commandLine -match $escapedRepo -or
                $commandLine -match "AI4science" -or
                $commandLine -match "xrd_robustness"
            }
    }

    return @($pythonProcesses | ForEach-Object {
        [pscustomobject]@{
            pid          = [int]$_.ProcessId
            name         = $_.Name
            created_at   = if ($null -ne $_.CreationDate) { $_.CreationDate.ToString("o") } else { $null }
            command_line = $_.CommandLine
        }
    })
}

function Get-LatestTrackedFile {
    param([string]$Root)

    if (-not (Test-Path -LiteralPath $Root)) {
        return $null
    }

    $extensions = @(
        ".log", ".txt", ".json", ".jsonl", ".csv",
        ".pt", ".pth", ".ckpt", ".npz", ".yaml", ".yml"
    )

    try {
        return Get-ChildItem -LiteralPath $Root -File -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $extensions -contains $_.Extension.ToLowerInvariant() } |
            Sort-Object LastWriteTimeUtc -Descending |
            Select-Object -First 1
    }
    catch {
        return $null
    }
}

function Select-AutoWatchPath {
    param([string]$RepositoryRoot)

    $candidateRelativePaths = @(
        "xrd_robustness\outputs",
        "xrd_robustness\runs",
        "xrd_robustness\artifacts",
        "xrd_robustness\checkpoints",
        "xrd_robustness\reports"
    )

    $ranked = @()
    foreach ($relativePath in $candidateRelativePaths) {
        $candidate = Join-Path $RepositoryRoot $relativePath
        if (-not (Test-Path -LiteralPath $candidate -PathType Container)) {
            continue
        }

        $latest = Get-LatestTrackedFile -Root $candidate
        $ranked += [pscustomobject]@{
            path       = $candidate
            latest_utc = if ($null -ne $latest) { $latest.LastWriteTimeUtc } else { [datetime]::MinValue }
        }
    }

    if ($ranked.Count -gt 0) {
        return ($ranked | Sort-Object latest_utc -Descending | Select-Object -First 1).path
    }

    return (Join-Path $RepositoryRoot "xrd_robustness")
}

function Get-FreeDiskGB {
    param([string]$Path)

    try {
        $root = [System.IO.Path]::GetPathRoot($Path)
        $drive = New-Object System.IO.DriveInfo($root)
        return [math]::Round($drive.AvailableFreeSpace / 1GB, 2)
    }
    catch {
        return $null
    }
}

function Write-Heartbeat {
    param(
        [Parameter(Mandatory = $true)]$Snapshot,
        [Parameter(Mandatory = $true)][string]$StateDirectory
    )

    $jsonPath = Join-Path $StateDirectory "latest_status.json"
    $csvPath = Join-Path $StateDirectory "history.csv"

    $Snapshot | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

    $csvRow = [pscustomobject]@{
        timestamp                 = $Snapshot.timestamp
        state                     = $Snapshot.state
        process_count             = $Snapshot.process_count
        process_ids               = ($Snapshot.processes.pid -join ";")
        gpu_utilization_max       = $Snapshot.gpu_utilization_max
        gpu_memory_used_max_mb    = $Snapshot.gpu_memory_used_max_mb
        latest_file               = $Snapshot.latest_file
        latest_file_age_minutes   = $Snapshot.latest_file_age_minutes
        free_disk_gb              = $Snapshot.free_disk_gb
        warnings                  = ($Snapshot.warnings -join " | ")
    }

    if (Test-Path -LiteralPath $csvPath) {
        $csvRow | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Append -Encoding UTF8
    }
    else {
        $csvRow | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8
    }
}

function Invoke-AlertBeep {
    if ($NoBeep) {
        return
    }

    try {
        [console]::Beep(900, 250)
        Start-Sleep -Milliseconds 100
        [console]::Beep(700, 350)
    }
    catch {
        # Some terminals do not support Console.Beep. Monitoring continues.
    }
}

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Resolve-FullPath -Path (Join-Path $PSScriptRoot "..")
}
else {
    $RepoRoot = Resolve-FullPath -Path $RepoRoot
}

if (-not (Test-Path -LiteralPath $RepoRoot -PathType Container)) {
    throw "Repository root does not exist: $RepoRoot"
}

if ([string]::IsNullOrWhiteSpace($WatchPath)) {
    $WatchPath = Select-AutoWatchPath -RepositoryRoot $RepoRoot
}
else {
    $WatchPath = Resolve-FullPath -Path $WatchPath -BasePath $RepoRoot
}

if (-not [string]::IsNullOrWhiteSpace($LogPath)) {
    $LogPath = Resolve-FullPath -Path $LogPath -BasePath $RepoRoot
}

$stateDirectory = Join-Path $RepoRoot ".monitoring"
New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null

$nvidiaSmi = Find-NvidiaSmi
$gpuIdleStartedAt = $null
$previousState = ""

Write-Host ""
Write-Host "AI4science local training monitor" -ForegroundColor Cyan
Write-Host "Repository : $RepoRoot"
Write-Host "Watch path : $WatchPath"
Write-Host "State files: $stateDirectory"
Write-Host "Process regex: $(if ([string]::IsNullOrWhiteSpace($ProcessPattern)) { '<auto: repo/xrd_robustness>' } else { $ProcessPattern })"
Write-Host "nvidia-smi: $(if ($null -eq $nvidiaSmi) { '<not found>' } else { $nvidiaSmi })"
Write-Host "Read-only: this script never starts, stops, or resumes training." -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop monitoring only; the training process is not touched."
Write-Host ""

while ($true) {
    $now = Get-Date
    $processes = Get-TrainingProcesses -Pattern $ProcessPattern -RepositoryRoot $RepoRoot
    $gpus = Get-GpuSnapshot -NvidiaSmi $nvidiaSmi
    $latestFile = Get-LatestTrackedFile -Root $WatchPath
    $freeDiskGB = Get-FreeDiskGB -Path $RepoRoot

    $gpuUtilizationMax = if ($gpus.Count -gt 0) {
        [double](($gpus | Measure-Object utilization -Maximum).Maximum)
    }
    else {
        $null
    }

    $gpuMemoryUsedMax = if ($gpus.Count -gt 0) {
        [double](($gpus | Measure-Object memory_used -Maximum).Maximum)
    }
    else {
        $null
    }

    if ($processes.Count -gt 0 -and $null -ne $gpuUtilizationMax -and $gpuUtilizationMax -lt 5) {
        if ($null -eq $gpuIdleStartedAt) {
            $gpuIdleStartedAt = $now
        }
    }
    else {
        $gpuIdleStartedAt = $null
    }

    $latestFileAgeMinutes = $null
    if ($null -ne $latestFile) {
        $latestFileAgeMinutes = [math]::Round(($now.ToUniversalTime() - $latestFile.LastWriteTimeUtc).TotalMinutes, 2)
    }

    $warnings = @()
    $state = "RUNNING"

    if ($processes.Count -eq 0) {
        $state = "PROCESS_NOT_FOUND"
        $warnings += "No matching Python training process was found."
    }

    if ($null -ne $latestFileAgeMinutes -and $latestFileAgeMinutes -ge $StaleMinutes) {
        if ($state -eq "RUNNING") {
            $state = "FILE_STALE"
        }
        $warnings += "The newest tracked file has not changed for $latestFileAgeMinutes minutes."
    }

    if ($null -ne $gpuIdleStartedAt) {
        $gpuIdleAgeMinutes = ($now - $gpuIdleStartedAt).TotalMinutes
        if ($gpuIdleAgeMinutes -ge $GpuIdleMinutes) {
            if ($state -eq "RUNNING") {
                $state = "GPU_IDLE"
            }
            $warnings += "GPU utilization has stayed below 5% for $([math]::Round($gpuIdleAgeMinutes, 2)) minutes. Validation or CPU-side rendering can also cause this."
        }
    }

    if ($null -ne $freeDiskGB -and $freeDiskGB -lt $LowDiskGB) {
        if ($state -eq "RUNNING") {
            $state = "LOW_DISK"
        }
        $warnings += "Only $freeDiskGB GB of free disk space remains."
    }

    if ($null -eq $nvidiaSmi) {
        $warnings += "nvidia-smi was not found; GPU telemetry is unavailable."
    }

    $snapshot = [pscustomobject]@{
        timestamp               = $now.ToString("o")
        state                   = $state
        repository_root         = $RepoRoot
        watch_path              = $WatchPath
        process_pattern         = $ProcessPattern
        process_count           = $processes.Count
        processes               = $processes
        gpu_count               = $gpus.Count
        gpus                    = $gpus
        gpu_utilization_max     = $gpuUtilizationMax
        gpu_memory_used_max_mb  = $gpuMemoryUsedMax
        latest_file             = if ($null -ne $latestFile) { $latestFile.FullName } else { $null }
        latest_file_modified_at = if ($null -ne $latestFile) { $latestFile.LastWriteTime.ToString("o") } else { $null }
        latest_file_age_minutes = $latestFileAgeMinutes
        free_disk_gb            = $freeDiskGB
        warnings                = $warnings
    }

    Write-Heartbeat -Snapshot $snapshot -StateDirectory $stateDirectory

    $stateColor = switch ($state) {
        "RUNNING" { "Green" }
        "FILE_STALE" { "Yellow" }
        "GPU_IDLE" { "Yellow" }
        "LOW_DISK" { "Red" }
        default { "Red" }
    }

    Write-Host ("[{0}] " -f $now.ToString("yyyy-MM-dd HH:mm:ss")) -NoNewline
    Write-Host $state -ForegroundColor $stateColor -NoNewline
    Write-Host (" | proc={0}" -f $processes.Count) -NoNewline

    if ($null -ne $gpuUtilizationMax) {
        Write-Host (" | gpu={0:N0}% mem={1:N0}MB" -f $gpuUtilizationMax, $gpuMemoryUsedMax) -NoNewline
    }

    if ($null -ne $latestFile) {
        Write-Host (" | latest={0} ({1:N1}m)" -f $latestFile.Name, $latestFileAgeMinutes) -NoNewline
    }

    if ($null -ne $freeDiskGB) {
        Write-Host (" | disk={0:N1}GB" -f $freeDiskGB)
    }
    else {
        Write-Host ""
    }

    foreach ($warning in $warnings) {
        Write-Host "  WARNING: $warning" -ForegroundColor Yellow
    }

    if ($ShowLogTail) {
        $effectiveLogPath = $LogPath
        if ([string]::IsNullOrWhiteSpace($effectiveLogPath) -and $null -ne $latestFile -and $latestFile.Extension -in @(".log", ".txt", ".jsonl")) {
            $effectiveLogPath = $latestFile.FullName
        }

        if (-not [string]::IsNullOrWhiteSpace($effectiveLogPath) -and (Test-Path -LiteralPath $effectiveLogPath -PathType Leaf)) {
            Write-Host "  ---- tail: $effectiveLogPath ----" -ForegroundColor DarkGray
            Get-Content -LiteralPath $effectiveLogPath -Tail $LogTailLines -ErrorAction SilentlyContinue |
                ForEach-Object { Write-Host "  $_" }
            Write-Host "  --------------------------------" -ForegroundColor DarkGray
        }
    }

    if ($state -ne "RUNNING" -and $state -ne $previousState) {
        Invoke-AlertBeep
    }
    $previousState = $state

    if ($Once) {
        break
    }

    Start-Sleep -Seconds $IntervalSeconds
}
