"""Portable project-relative data-root resolution helpers."""

from __future__ import annotations

from pathlib import Path


def resolve_data_root(project_root: Path, value: str | Path | None = None) -> Path:
    """Resolve a data root and keep it inside the project directory."""
    root = (project_root / "data") if value is None else Path(value)
    if not root.is_absolute():
        root = project_root / root
    root = root.resolve()
    project_root = project_root.resolve()
    if not root.is_relative_to(project_root):
        raise ValueError(f"data root must be inside project root: {root}")
    return root


def project_relative_path(project_root: Path, path: Path) -> str:
    """Return a stable forward-slash path for manifests and run metadata."""
    return path.resolve().relative_to(project_root.resolve()).as_posix()
