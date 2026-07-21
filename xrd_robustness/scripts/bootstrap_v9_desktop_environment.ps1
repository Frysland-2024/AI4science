param(
    [string]$EnvironmentRoot = "E:\AI4science\.venvs\xrd_tools",
    [string]$BasePython = "py",
    [switch]$PlanOnly
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$EnvironmentRoot = [System.IO.Path]::GetFullPath($EnvironmentRoot)
$PythonExecutable = Join-Path $EnvironmentRoot "Scripts\python.exe"
$Commands = @(
    @($BasePython, "-3.11", "-m", "venv", $EnvironmentRoot),
    @($PythonExecutable, "-m", "pip", "install", "--upgrade", "pip"),
    @($PythonExecutable, "-m", "pip", "install", "numpy==2.0.2"),
    @(
        $PythonExecutable, "-m", "pip", "install", "torch==2.5.1+cu124",
        "--index-url", "https://download.pytorch.org/whl/cu124"
    ),
    @($PythonExecutable, "-m", "pip", "check")
)

Write-Output "environment_root=$EnvironmentRoot"
Write-Output "plan_only=$([bool]$PlanOnly)"
foreach ($Command in $Commands) {
    Write-Output ("command=" + ($Command -join " "))
}
if ($PlanOnly) {
    Write-Output "Plan validation complete; no environment or package was changed."
    exit 0
}

if (-not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {
    & $BasePython -3.11 -m venv $EnvironmentRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create Python 3.11 environment"
    }
}

& $PythonExecutable -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
& $PythonExecutable -m pip install numpy==2.0.2
if ($LASTEXITCODE -ne 0) { throw "NumPy installation failed" }
& $PythonExecutable -m pip install torch==2.5.1+cu124 --index-url https://download.pytorch.org/whl/cu124
if ($LASTEXITCODE -ne 0) { throw "CUDA PyTorch installation failed" }
& $PythonExecutable -m pip check
if ($LASTEXITCODE -ne 0) { throw "pip check failed" }

$VsWhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
$VisualStudioRoot = $null
if (Test-Path -LiteralPath $VsWhere -PathType Leaf) {
    $VisualStudioRoot = & $VsWhere -latest -products * `
        -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
        -property installationPath
}
$MsvcDiscoverable = [bool](Get-Command cl.exe -ErrorAction SilentlyContinue) -or `
    -not [string]::IsNullOrWhiteSpace([string]$VisualStudioRoot)

$Probe = @'
import json, sys, torch
print(json.dumps({
    "python": sys.version.split()[0],
    "torch": str(torch.__version__),
    "cuda": str(torch.version.cuda),
    "cuda_available": bool(torch.cuda.is_available()),
    "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    "gpu_memory_mb": int(torch.cuda.get_device_properties(0).total_memory/(1024**2)) if torch.cuda.is_available() else 0,
    "bf16": bool(torch.cuda.is_available() and torch.cuda.is_bf16_supported()),
}))
'@
$Observed = (& $PythonExecutable -c $Probe | Select-Object -Last 1) | ConvertFrom-Json
$Checks = [ordered]@{
    python_version = $Observed.python -eq "3.11.9"
    torch_version = $Observed.torch -eq "2.5.1+cu124"
    cuda_runtime = $Observed.cuda -eq "12.4"
    cuda_available = [bool]$Observed.cuda_available
    gpu_name = $Observed.gpu -eq "NVIDIA GeForce RTX 4070 Ti SUPER"
    gpu_memory = [int]$Observed.gpu_memory_mb -ge 15000
    bf16_supported = [bool]$Observed.bf16
    pip_check = $true
    msvc_toolchain_discoverable = $MsvcDiscoverable
}
$Failed = @($Checks.GetEnumerator() | Where-Object { -not $_.Value })
$Report = [ordered]@{
    schema_version = "v9-desktop-environment-bootstrap-v1"
    status = if ($Failed.Count -eq 0) { "pass" } else { "fail" }
    project_root = $ProjectRoot
    environment_root = $EnvironmentRoot
    observed = $Observed
    visual_studio_root = [string]$VisualStudioRoot
    checks = $Checks
    failed_checks = @($Failed | ForEach-Object Key)
}
$Output = Join-Path $ProjectRoot "reports\desktop_environment_bootstrap.json"
$ReportJson = ($Report | ConvertTo-Json -Depth 6) + [System.Environment]::NewLine
[System.IO.File]::WriteAllText(
    $Output,
    $ReportJson,
    [System.Text.UTF8Encoding]::new($false)
)
Write-Output "status=$($Report.status)"
Write-Output "report=$Output"
if ($Failed.Count -ne 0) { exit 1 }
