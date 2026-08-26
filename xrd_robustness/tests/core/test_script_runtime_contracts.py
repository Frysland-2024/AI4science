from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
from pymatgen.core import Lattice, Structure

from xrd_robustness import external_runtime
from xrd_robustness.external_runtime import (
    external_script_issue,
    resolve_python_command,
    virtual_environment_python,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("driver", "helper"),
    [
        ("acquire_mp_structures.py", "standardize_structure_batch.py"),
        ("precompute_peak_tables.py", "precompute_peak_table_batch.py"),
    ],
)
def test_referenced_external_helpers_are_shipped(driver: str, helper: str) -> None:
    source = (PROJECT_ROOT / "scripts" / driver).read_text(encoding="utf-8")
    if helper in source:
        assert (
            PROJECT_ROOT / "scripts" / helper
        ).is_file(), f"{driver} invokes missing helper scripts/{helper}"


@pytest.mark.parametrize(
    "helper",
    ["standardize_structure_batch.py", "precompute_peak_table_batch.py"],
)
def test_external_helpers_load_in_the_test_environment(helper: str) -> None:
    issue = external_script_issue(
        Path(sys.executable),
        PROJECT_ROOT / "scripts" / helper,
        cwd=PROJECT_ROOT,
    )
    assert issue is None


def test_external_runtime_probe_rejects_a_broken_interpreter(tmp_path: Path) -> None:
    broken_python = tmp_path / "python.exe"
    broken_python.write_text("not an interpreter", encoding="utf-8")
    issue = external_script_issue(
        broken_python,
        PROJECT_ROOT / "scripts" / "standardize_structure_batch.py",
        cwd=PROJECT_ROOT,
    )
    assert issue is not None
    assert "could not start" in issue or "exited with code" in issue


def test_python_command_resolution_supports_path_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    discovered = tmp_path / "python"
    monkeypatch.setattr(external_runtime.shutil, "which", lambda _name: str(discovered))
    assert resolve_python_command("python") == discovered.resolve()


def test_virtual_environment_interpreter_uses_platform_layout(tmp_path: Path) -> None:
    interpreter = virtual_environment_python(tmp_path / "environment")
    if external_runtime.os.name == "nt":
        assert interpreter == tmp_path / "environment" / "Scripts" / "python.exe"
    else:
        assert interpreter == tmp_path / "environment" / "bin" / "python"


def test_acquisition_driver_forwards_symmetry_parameters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = PROJECT_ROOT / "scripts" / "acquire_mp_structures.py"
    spec = importlib.util.spec_from_file_location(
        "acquisition_runtime_contract", script
    )
    assert spec is not None and spec.loader is not None
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    monkeypatch.setattr(driver, "PROJECT_ROOT", tmp_path)
    commands: list[list[str]] = []

    def fake_run(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        output = Path(command[command.index("--output") + 1])
        output.write_text('[{"material_id":"contract"}]', encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(driver.subprocess, "run", fake_run)
    document = SimpleNamespace(
        material_id="contract",
        structure=SimpleNamespace(as_dict=lambda: {}),
    )
    rows = driver._external_standardize(
        [document],
        standardizer_python=Path(sys.executable),
        symprec=0.002,
        angle_tolerance=4.25,
    )

    assert rows == {"contract": {"material_id": "contract"}}
    command = commands[0]
    assert command[command.index("--symprec") + 1] == "0.002"
    assert command[command.index("--angle-tolerance") + 1] == "4.25"


def test_external_helper_pipeline_smoke(tmp_path: Path) -> None:
    structure = Structure(Lattice.cubic(5.43), ["Si"], [[0.0, 0.0, 0.0]])
    source = tmp_path / "source.json"
    standardized = tmp_path / "standardized.json"
    peaks = tmp_path / "peaks.json"
    source.write_text(
        json.dumps(
            [
                {
                    "material_id": "smoke-Si",
                    "original_structure": structure.as_dict(),
                }
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            "-s",
            str(PROJECT_ROOT / "scripts" / "standardize_structure_batch.py"),
            "--input",
            str(source),
            "--output",
            str(standardized),
            "--symprec",
            "0.002",
            "--angle-tolerance",
            "4.0",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    standardized_rows = json.loads(standardized.read_text(encoding="utf-8"))
    assert standardized_rows[0]["material_id"] == "smoke-Si"
    assert "error" not in standardized_rows[0]

    subprocess.run(
        [
            sys.executable,
            "-s",
            str(PROJECT_ROOT / "scripts" / "precompute_peak_table_batch.py"),
            "--input",
            str(standardized),
            "--output",
            str(peaks),
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    peak_rows = json.loads(peaks.read_text(encoding="utf-8"))
    assert peak_rows[0]["material_id"] == "smoke-Si"
    assert "error" not in peak_rows[0]
    assert len(peak_rows[0]["positions"]) > 0
    assert len(peak_rows[0]["positions"]) == len(peak_rows[0]["intensities"])
    assert len(peak_rows[0]["hkls"]) == len(peak_rows[0]["multiplicities"])
