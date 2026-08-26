"""Validation helpers for optional Python subprocess environments."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess


def resolve_python_command(value: str | Path) -> Path:
    """Resolve a Python path while preserving support for commands on ``PATH``."""
    raw = str(value)
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute() and candidate.parent == Path("."):
        discovered = shutil.which(raw)
        if discovered is not None:
            return Path(discovered).resolve()
    return candidate.resolve()


def virtual_environment_python(environment: Path) -> Path:
    """Return the conventional interpreter path for the current platform."""
    relative = Path("Scripts/python.exe") if os.name == "nt" else Path("bin/python")
    return environment / relative


def external_script_issue(
    python: Path,
    script: Path,
    *,
    cwd: Path,
    timeout_seconds: float = 30.0,
) -> str | None:
    """Return why an interpreter cannot load a helper script, or ``None``."""
    if not python.is_file():
        return f"interpreter is missing: {python}"
    if not script.is_file():
        return f"helper script is missing: {script}"
    try:
        completed = subprocess.run(
            [str(python), "-s", str(script), "--help"],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return f"runtime probe timed out after {timeout_seconds:g} seconds"
    except OSError as error:
        return f"runtime probe could not start: {error}"
    if completed.returncode == 0:
        return None
    detail = (completed.stderr or completed.stdout).strip().replace("\n", " ")
    if len(detail) > 300:
        detail = detail[:297] + "..."
    suffix = f": {detail}" if detail else ""
    return f"runtime probe exited with code {completed.returncode}{suffix}"
