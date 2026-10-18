"""Recover plots and report from a completed pilot whose plot step failed.

This utility never retrains and never edits saved results or training histories.
It preserves the failed manifest before marking the recovered run complete.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from run_v9_perturbation_pilot import save_plots, save_json, _write_report


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args(argv)
    run_dir = args.run_dir.resolve()
    manifest_path = run_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "failed":
        raise ValueError("artifact recovery is restricted to a failed run manifest")
    results_path = run_dir / "results_full.json.gz"
    if not results_path.is_file():
        results_path = run_dir / "results.json"
    if not results_path.is_file() or not (run_dir / "training_histories.json").is_file():
        raise FileNotFoundError("completed training result and history files are required")
    if (run_dir / "run_manifest_pre_plot_recovery.json").exists():
        raise FileExistsError("pre-recovery manifest snapshot already exists")

    histories_path = run_dir / "training_histories.json"
    results_archive_hash_before = sha256_file(results_path)
    results_bytes_before = (
        gzip.decompress(results_path.read_bytes())
        if results_path.suffix == ".gz"
        else results_path.read_bytes()
    )
    results_hash_before = hashlib.sha256(results_bytes_before).hexdigest()
    histories_hash_before = sha256_file(histories_path)
    shutil.copy2(manifest_path, run_dir / "run_manifest_pre_plot_recovery.json")

    results: dict[str, Any] = json.loads(results_bytes_before)
    config = json.loads((run_dir / "pilot_config.json").read_text(encoding="utf-8"))
    with np.load(run_dir / "pilot_samples.npz") as archive:
        arrays = {key: archive[key] for key in archive.files}
    abs_errors = {
        f"{condition}_{method}": [
            np.abs(
                np.asarray(seed_row["test"]["prediction_q"], dtype=np.float64)
                - np.asarray(seed_row["test"]["target_q"], dtype=np.float64)
            )
            for seed_row in results["conditions"][condition][method]["seeds"]
        ]
        for condition in ("simple", "v9")
        for method in ("A", "B")
    }
    dataset = manifest["dataset"]
    grid = dataset["two_theta_grid"]
    count = int(round((grid["two_theta_max"] - grid["two_theta_min"]) / grid["step"])) + 1
    axis = float(grid["two_theta_min"]) + np.arange(count) * float(grid["step"])
    axis[-1] = float(grid["two_theta_max"])
    test_indices = np.asarray(arrays["test_indices"], dtype=np.int64)
    save_plots(run_dir, arrays, results, abs_errors, axis, test_indices)
    _write_report(
        run_dir,
        phase=manifest["phase"],
        metadata=dataset,
        gates=manifest["gates"],
        smoke=manifest["smoke"],
        results=results,
        config=config,
    )
    results_bytes_after = (
        gzip.decompress(results_path.read_bytes())
        if results_path.suffix == ".gz"
        else results_path.read_bytes()
    )
    results_hash_after = hashlib.sha256(results_bytes_after).hexdigest()
    results_archive_hash_after = sha256_file(results_path)
    histories_hash_after = sha256_file(histories_path)
    if (
        results_hash_after != results_hash_before
        or results_archive_hash_after != results_archive_hash_before
        or histories_hash_after != histories_hash_before
    ):
        raise RuntimeError("recovery unexpectedly changed immutable result or history JSON")

    recovery = {
        "recovered_at_utc": datetime.now(timezone.utc).isoformat(),
        "original_status": "failed",
        "original_error": manifest.get("error"),
        "reason": "training and result serialization completed; only Matplotlib boxplot label keyword was incompatible",
        "result_json_sha256_before_and_after": results_hash_after,
        "result_archive_sha256_before_and_after": results_archive_hash_before,
        "history_json_sha256_before_and_after": histories_hash_after,
        "original_manifest_snapshot": "run_manifest_pre_plot_recovery.json",
        "generated_artifacts": ["parameter_error.png", "xrd_overlay.png", "TECHNICAL_REPORT.md"],
    }
    save_json(run_dir / "artifact_recovery_record.json", recovery)
    manifest["status"] = "complete"
    manifest["completion_note"] = "Training completed before a plotting API error; plots/report were recovered without retraining or changing result/history JSON."
    manifest["postprocessing_recovery"] = recovery
    manifest["artifacts"].update({
        "pre_recovery_manifest": "run_manifest_pre_plot_recovery.json",
        "artifact_recovery_record": "artifact_recovery_record.json",
        "results": "results_summary.json" if (run_dir / "results_summary.json").exists() else results_path.name,
        "full_results_archive": results_path.name if results_path.suffix == ".gz" else None,
        "histories": "training_histories.json",
        "failure_cases": "failure_cases.json",
        "results_validation": "results_validation.json",
        "parameter_error_plot": "parameter_error.png",
        "xrd_overlay_plot": "xrd_overlay.png",
        "technical_report": "TECHNICAL_REPORT.md",
    })
    save_json(manifest_path, manifest)
    with (run_dir / "run.log").open("a", encoding="utf-8") as handle:
        handle.write(
            f"{recovery['recovered_at_utc']} INFO recovered plots and report; training result hashes unchanged\n"
        )
    print(json.dumps(recovery, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
