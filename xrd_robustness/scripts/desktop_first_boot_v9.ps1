param(
    [string]$PythonExecutable,
    [string]$AcceptanceRoot,
    [switch]$PlanOnly
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ContractPath = Join-Path $ProjectRoot "configs\algorithm.v9.method_transfer.json"
$Contract = Get-Content -LiteralPath $ContractPath -Raw -Encoding UTF8 | ConvertFrom-Json

function Enable-MsvcEnvironment {
    if (Get-Command cl.exe -ErrorAction SilentlyContinue) {
        return
    }
    $VsWhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
    if (-not (Test-Path -LiteralPath $VsWhere -PathType Leaf)) {
        throw "MSVC Build Tools are missing. Install Visual Studio 2022 C++ Build Tools, then rerun desktop first boot."
    }
    $InstallRoot = & $VsWhere -latest -products * `
        -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
        -property installationPath
    $DevCmd = Join-Path ([string]$InstallRoot) "Common7\Tools\VsDevCmd.bat"
    if ([string]::IsNullOrWhiteSpace([string]$InstallRoot) -or `
        -not (Test-Path -LiteralPath $DevCmd -PathType Leaf)) {
        throw "Visual Studio 2022 C++ toolchain was not found. Install the x64 C++ Build Tools workload."
    }
    $EnvironmentLines = & cmd.exe /s /c "`"$DevCmd`" -arch=x64 -host_arch=x64 >nul && set"
    foreach ($Line in $EnvironmentLines) {
        $Separator = $Line.IndexOf('=')
        if ($Separator -gt 0) {
            $Name = $Line.Substring(0, $Separator)
            $Value = $Line.Substring($Separator + 1)
            [System.Environment]::SetEnvironmentVariable($Name, $Value, "Process")
        }
    }
    if (-not (Get-Command cl.exe -ErrorAction SilentlyContinue)) {
        throw "MSVC environment initialization completed without exposing cl.exe."
    }
}

if ([string]::IsNullOrWhiteSpace($PythonExecutable)) {
    $ConfiguredPython = [string]$Contract.runtime.python_executable
    if ([System.IO.Path]::IsPathRooted($ConfiguredPython)) {
        $PythonExecutable = [System.IO.Path]::GetFullPath($ConfiguredPython)
    }
    else {
        $PythonExecutable = [System.IO.Path]::GetFullPath(
            (Join-Path $ProjectRoot $ConfiguredPython)
        )
    }
}
else {
    $PythonExecutable = [System.IO.Path]::GetFullPath($PythonExecutable)
}
if ([string]::IsNullOrWhiteSpace($AcceptanceRoot)) {
    $AcceptanceRoot = Join-Path $ProjectRoot "reports\desktop_acceptance"
}
else {
    $AcceptanceRoot = [System.IO.Path]::GetFullPath($AcceptanceRoot)
}

$Steps = @(
    @{
        Name = "migration_verification"
        Arguments = @(
            "-s", "scripts\verify_v9_desktop_migration.py",
            "--root", $ProjectRoot,
            "--output", (Join-Path $AcceptanceRoot "migration_verification.json")
        )
    },
    @{
        Name = "runtime_environment"
        Arguments = @(
            "-s", "scripts\audit_v9_runtime_environment.py",
            "--output", (Join-Path $AcceptanceRoot "environment.json")
        )
    },
    @{
        Name = "contract_preflight"
        Arguments = @(
            "-s", "scripts\run_v9_method_transfer.py", "preflight",
            "--output", (Join-Path $AcceptanceRoot "preflight.json")
        )
    },
    @{
        Name = "hardware_configuration"
        Arguments = @(
            "-s", "scripts\audit_v9_desktop_hardware_config.py",
            "--output", (Join-Path $AcceptanceRoot "hardware_config.json")
        )
    },
    @{
        Name = "prefetch_8x8"
        Arguments = @(
            "-s", "scripts\audit_v9_dynamic_prefetch.py",
            "--batches", "16", "--workers", "8", "--prefetch-batches", "8",
            "--output", (Join-Path $AcceptanceRoot "prefetch_8x8.json")
        )
    },
    @{
        Name = "prefetch_4x8"
        Arguments = @(
            "-s", "scripts\audit_v9_dynamic_prefetch.py",
            "--batches", "16", "--workers", "4", "--prefetch-batches", "8",
            "--output", (Join-Path $AcceptanceRoot "prefetch_4x8.json")
        )
    },
    @{
        Name = "full_prefetch_candidate_matrix"
        Arguments = @(
            "-s", "scripts\audit_v9_prefetch_matrix.py",
            "--batches", "16", "--repeats", "2",
            "--evidence-root", (Join-Path $AcceptanceRoot "prefetch_matrix"),
            "--output", (Join-Path $AcceptanceRoot "prefetch_matrix.json")
        )
    },
    @{
        Name = "cuda_transfer"
        Arguments = @(
            "-s", "scripts\audit_v9_cuda_transfer.py",
            "--output", (Join-Path $AcceptanceRoot "cuda_transfer.json")
        )
    },
    @{
        Name = "evaluation_batch_candidates"
        Arguments = @(
            "-s", "scripts\audit_v9_evaluation_batch.py",
            "--output", (Join-Path $AcceptanceRoot "evaluation_batch.json")
        )
    },
    @{
        Name = "bf16_compile_parallel_acceleration"
        Arguments = @(
            "-s", "scripts\audit_v9_desktop_acceleration.py",
            "--output", (Join-Path $AcceptanceRoot "acceleration.json")
        )
    },
    @{
        Name = "final_readiness"
        Arguments = @(
            "-s", "scripts\audit_v9_desktop_readiness.py",
            "--acceptance-root", $AcceptanceRoot,
            "--migration-verification", (Join-Path $AcceptanceRoot "migration_verification.json"),
            "--output", (Join-Path $AcceptanceRoot "desktop_readiness.json")
        )
    }
)

Write-Output "project_root=$ProjectRoot"
Write-Output "python=$PythonExecutable"
Write-Output "acceptance_root=$AcceptanceRoot"
Write-Output "plan_only=$([bool]$PlanOnly)"
Write-Output "formal_training_commands=0"

if (-not $PlanOnly) {
    if (-not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {
        throw "Frozen desktop Python is missing: $PythonExecutable. Run bootstrap_v9_desktop_environment.ps1 first."
    }
    Enable-MsvcEnvironment
    [System.IO.Directory]::CreateDirectory($AcceptanceRoot) | Out-Null
}

Push-Location $ProjectRoot
try {
    foreach ($Step in $Steps) {
        $Rendered = $Step.Arguments -join " "
        Write-Output "step=$($Step.Name)"
        Write-Output "command=$PythonExecutable $Rendered"
        if ($PlanOnly) {
            continue
        }
        & $PythonExecutable @($Step.Arguments)
        if ($LASTEXITCODE -ne 0) {
            throw "Desktop acceptance step failed: $($Step.Name), exit=$LASTEXITCODE"
        }
    }
}
finally {
    Pop-Location
}

if ($PlanOnly) {
    Write-Output "Plan validation complete; no command was executed and no report was written."
}
else {
    $ReadinessPath = Join-Path $AcceptanceRoot "desktop_readiness.json"
    $Readiness = Get-Content -LiteralPath $ReadinessPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Output "desktop_readiness=$($Readiness.status)"
    Write-Output "Training remains stopped. Explicit user authorization is still required before tune-run."
}
