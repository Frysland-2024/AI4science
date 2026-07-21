param(
    [Parameter(Mandatory = $true)]
    [string]$DestinationRoot,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ManifestPath = Join-Path $ProjectRoot "reports\v9_desktop_migration_manifest.json"

if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "Migration manifest is missing: $ManifestPath"
}

$Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($Manifest.status -ne "ready_for_copy") {
    throw "Migration manifest is not ready_for_copy: $($Manifest.status)"
}

$FileManifestPath = Join-Path $ProjectRoot $Manifest.file_manifest.path
if (-not (Test-Path -LiteralPath $FileManifestPath -PathType Leaf)) {
    throw "Migration file list is missing: $FileManifestPath"
}

$DestinationFull = [System.IO.Path]::GetFullPath($DestinationRoot)
$SourceBoundary = $ProjectRoot.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
$DestinationBoundary = $DestinationFull.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
$Rows = @(Import-Csv -LiteralPath $FileManifestPath -Encoding UTF8)
$ControlFiles = @(
    "reports/v9_desktop_migration_manifest.json",
    "reports/v9_desktop_migration_files.csv"
)
$RelativePaths = @($Rows.path) + $ControlFiles

Write-Output "source=$ProjectRoot"
Write-Output "destination=$DestinationFull"
Write-Output "payload_files=$($Rows.Count)"
Write-Output "what_if=$([bool]$WhatIf)"

$Copied = 0
foreach ($RelativePath in $RelativePaths) {
    $SourcePath = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $RelativePath))
    if (-not $SourcePath.StartsWith($SourceBoundary, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Source path escapes project root: $RelativePath"
    }
    if (-not (Test-Path -LiteralPath $SourcePath -PathType Leaf)) {
        throw "Source payload file is missing: $RelativePath"
    }
    $DestinationPath = [System.IO.Path]::GetFullPath((Join-Path $DestinationFull $RelativePath))
    if (-not $DestinationPath.StartsWith($DestinationBoundary, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Destination path escapes destination root: $RelativePath"
    }
    if (-not $WhatIf) {
        $DestinationDirectory = Split-Path -Parent $DestinationPath
        [System.IO.Directory]::CreateDirectory($DestinationDirectory) | Out-Null
        [System.IO.File]::Copy($SourcePath, $DestinationPath, $true)
    }
    $Copied += 1
}

Write-Output "selected_files=$Copied"
if ($WhatIf) {
    Write-Output "Dry run complete; no files were copied."
}
else {
    Write-Output "Copy complete. On the desktop, run:"
    Write-Output "powershell -ExecutionPolicy Bypass -File scripts/bootstrap_v9_desktop_environment.ps1"
    Write-Output "powershell -ExecutionPolicy Bypass -File scripts/desktop_first_boot_v9.ps1"
}
