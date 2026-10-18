# Launched by Windows Task Scheduler; no API credentials are needed.
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$logDir = Join-Path $repo '.git\research_bridge'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$log = Join-Path $logDir 'scheduled.log'
$previous = Join-Path $logDir 'scheduled.previous.log'
if ((Test-Path $log) -and (Get-Item $log).Length -gt 2097152) {
    Move-Item -Path $log -Destination $previous -Force
}
$python = (Get-Command python -ErrorAction Stop).Source
"[$(Get-Date -Format o)] START worker --once" | Out-File -FilePath $log -Append -Encoding utf8
Push-Location $repo
try {
    & $python -m research_bridge.worker --once *>> $log
    $exitCode = $LASTEXITCODE
} catch {
    $_.Exception.Message | Out-File -FilePath $log -Append -Encoding utf8
    $exitCode = 1
} finally {
    Pop-Location
}
"[$(Get-Date -Format o)] END exit=$exitCode" | Out-File -FilePath $log -Append -Encoding utf8
exit $exitCode
