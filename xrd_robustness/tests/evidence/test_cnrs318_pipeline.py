from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_runner():
    path = PROJECT_ROOT / "scripts" / "run_cnrs318_zero_shot.py"
    spec = importlib.util.spec_from_file_location("run_cnrs318_zero_shot", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_preprocessing_handshake_accepts_matching_manifest_and_inputs(tmp_path: Path) -> None:
    runner = _load_runner()
    manifest = tmp_path / "manifest.csv"
    inputs = tmp_path / "inputs.npz"
    report = tmp_path / "preprocessing.json"
    manifest.write_text("parent_id\np1\n", encoding="utf-8")
    inputs.write_bytes(b"frozen-input-bytes")
    payload = {
        "schema_version": "cnrs318-preprocessing-report-v1",
        "eval_manifest_sha256": _sha256(manifest),
        "inputs_sha256": _sha256(inputs),
    }
    report.write_text(json.dumps(payload), encoding="utf-8")

    assert runner.validate_preprocessing_handshake(
        preprocessing_report=report,
        eval_manifest=manifest,
        inputs_path=inputs,
    ) == payload


def test_preprocessing_handshake_rejects_reordered_or_changed_manifest(tmp_path: Path) -> None:
    runner = _load_runner()
    manifest = tmp_path / "manifest.csv"
    inputs = tmp_path / "inputs.npz"
    report = tmp_path / "preprocessing.json"
    manifest.write_text("parent_id\np1\n", encoding="utf-8")
    inputs.write_bytes(b"frozen-input-bytes")
    report.write_text(
        json.dumps(
            {
                "eval_manifest_sha256": _sha256(manifest),
                "inputs_sha256": _sha256(inputs),
            }
        ),
        encoding="utf-8",
    )
    manifest.write_text("parent_id\np2\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="eval_manifest_sha256"):
        runner.validate_preprocessing_handshake(
            preprocessing_report=report,
            eval_manifest=manifest,
            inputs_path=inputs,
        )
