"""Recompute the reported pilot metrics from result JSON and saved arrays."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from pxrd_forward_loss.evaluation import q_to_lattice


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _aggregate(values: list[float]):
    return {
        "mean": float(np.mean(values)),
        "sd_sample": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
        "seed_values": values,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args(argv)
    run_dir = args.run_dir.resolve()
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    archive_path = run_dir / "results_full.json.gz"
    results_path = archive_path if archive_path.exists() else run_dir / "results.json"
    results_bytes = gzip.decompress(results_path.read_bytes()) if results_path == archive_path else results_path.read_bytes()
    results = json.loads(results_bytes)
    config = json.loads((root / "xrd_inversion/configs/week1_formal_gate.json").read_text(encoding="utf-8"))
    with np.load(run_dir / "pilot_samples.npz") as archive:
        arrays = {key: archive[key] for key in archive.files}
    records = [
        json.loads(line)
        for line in (run_dir / "sample_records.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    dataset = manifest["dataset"]
    splits = {name: arrays[f"{name}_indices"] for name in ("train", "validation", "test")}
    split_owner = {
        int(index): split
        for split, indices in splits.items()
        for index in indices
    }
    all_split_indices = [int(index) for indices in splits.values() for index in indices]
    splits_are_partition = (
        len(all_split_indices) == len(arrays["q"])
        and len(set(all_split_indices)) == len(arrays["q"])
        and set(all_split_indices) == set(range(len(arrays["q"])))
    )
    record_q = np.asarray(
        [[row["theta_true"]["du_normalized"], row["theta_true"]["dv_normalized"]] for row in records],
        dtype=np.float64,
    )
    q_rounding = float(np.max(np.abs(arrays["q"].astype(np.float64) - record_q)))
    nuisance_types = sorted(set(
        name
        for row in records
        for name in row["nuisance_metadata"]["v9"]["perturbation_types"]
    ))
    no_orientation = all(
        not row["nuisance_metadata"]["v9"]["strengths"]["preferred_orientation_active"]
        for row in records
    )
    record_provenance_matches = all(
        row["config_sha256"] == manifest["config_sha256"]
        and split_owner.get(int(row["sample_index"])) == row["split"]
        and row["clean_profile_sha256"] == hashlib.sha256(
            np.ascontiguousarray(arrays["clean_profile"][int(row["sample_index"])]).tobytes()
        ).hexdigest()
        and row["observed_profile_simple_sha256"] == hashlib.sha256(
            np.ascontiguousarray(arrays["observed_profile_simple"][int(row["sample_index"])]).tobytes()
        ).hexdigest()
        and row["observed_profile_v9_sha256"] == hashlib.sha256(
            np.ascontiguousarray(arrays["observed_profile_v9"][int(row["sample_index"])]).tobytes()
        ).hexdigest()
        for row in records
    )

    parameterization = config["parameterization"]
    test_indices = splits["test"]
    recomputed: dict[str, Any] = {"conditions": {}}
    max_abs_metric_difference = 0.0
    for condition in ("simple", "v9"):
        observed = arrays[f"observed_profile_{condition}"][test_indices]
        condition_result: dict[str, Any] = {}
        for method in ("A", "B"):
            seed_rows = results["conditions"][condition][method]["seeds"]
            metrics_by_seed = {
                key: []
                for key in (
                    "normalized_du_mae",
                    "normalized_dv_mae",
                    "normalized_mean_two_parameter_mae",
                    "a_mae_angstrom",
                    "c_mae_angstrom",
                    "reconstruction_rmse_transformed_clean",
                    "reconstruction_rmse_transformed_observed",
                )
            }
            for row in seed_rows:
                test = row["test"]
                prediction = np.asarray(test["prediction_q"], dtype=np.float64)
                target = np.asarray(test["target_q"], dtype=np.float64)
                global_indices = test_indices
                reconstruction = np.asarray(test["reconstruction_profile"], dtype=np.float64)
                errors = np.abs(prediction - target)
                a0 = float(dataset["lattice_angstrom"]["a"])
                c0 = float(dataset["lattice_angstrom"]["c"])
                a_true, c_true = q_to_lattice(
                    target, a0, c0,
                    float(parameterization["du_half_range"]),
                    float(parameterization["dv_half_range"]),
                )
                a_pred, c_pred = q_to_lattice(
                    prediction, a0, c0,
                    float(parameterization["du_half_range"]),
                    float(parameterization["dv_half_range"]),
                )
                computed = {
                    "normalized_du_mae": float(np.mean(errors[:, 0])),
                    "normalized_dv_mae": float(np.mean(errors[:, 1])),
                    "normalized_mean_two_parameter_mae": float(np.mean(errors)),
                    "a_mae_angstrom": float(np.mean(np.abs(a_pred - a_true))),
                    "c_mae_angstrom": float(np.mean(np.abs(c_pred - c_true))),
                    "reconstruction_rmse_transformed_clean": float(
                        np.sqrt(np.mean((reconstruction - arrays["clean_profile"][global_indices]) ** 2))
                    ),
                    "reconstruction_rmse_transformed_observed": float(
                        np.sqrt(np.mean((reconstruction - observed) ** 2))
                    ),
                }
                for key, value in computed.items():
                    metrics_by_seed[key].append(value)
                    stored = (
                        float(test["reconstruction_rmse_transformed_clean"])
                        if key == "reconstruction_rmse_transformed_clean"
                        else float(test["reconstruction_rmse_transformed_noisy"])
                        if key == "reconstruction_rmse_transformed_observed"
                        else None
                    )
                    if key == "normalized_du_mae":
                        stored = float(test["parameter_mae_normalized"]["du"])
                    elif key == "normalized_dv_mae":
                        stored = float(test["parameter_mae_normalized"]["dv"])
                    elif key == "normalized_mean_two_parameter_mae":
                        stored = float(test["parameter_mae_normalized"]["mean_two_parameter"])
                    elif key == "a_mae_angstrom":
                        stored = float(test["lattice_mae_angstrom"]["a"])
                    elif key == "c_mae_angstrom":
                        stored = float(test["lattice_mae_angstrom"]["c"])
                    max_abs_metric_difference = max(max_abs_metric_difference, abs(value - stored))
            condition_result[method] = {
                key: _aggregate(values) for key, values in metrics_by_seed.items()
            }
        recomputed["conditions"][condition] = condition_result

    validation = {
        "status": "passed" if (
            len(records) == len(arrays["q"])
            and splits_are_partition
            and record_provenance_matches
            and q_rounding <= float(dataset.get("max_q_float32_rounding", 1e-6)) + 1e-12
            and no_orientation
            and max_abs_metric_difference < 1e-10
        ) else "failed",
        "results_json_sha256": hashlib.sha256(results_bytes).hexdigest(),
        "results_source_artifact": (
            "results_full.json.gz (decompressed)" if results_path == archive_path else "results.json"
        ),
        "results_archive_sha256": _sha256(archive_path) if archive_path.exists() else None,
        "dataset_npz_sha256": _sha256(run_dir / "pilot_samples.npz"),
        "sample_records_sha256": _sha256(run_dir / "sample_records.jsonl"),
        "n_samples": len(records),
        "split_counts": {key: int(len(value)) for key, value in splits.items()},
        "splits_are_disjoint_complete_partition": splits_are_partition,
        "sample_provenance_hashes_and_split_match": record_provenance_matches,
        "max_q_record_to_training_array_difference": q_rounding,
        "active_v9_perturbation_types": nuisance_types,
        "march_dollase_disabled_for_all_samples": no_orientation,
        "max_abs_per_seed_metric_difference": max_abs_metric_difference,
        "recomputed_metrics": recomputed,
    }
    output = run_dir / "results_validation.json"
    output.write_text(json.dumps(validation, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=False))
    return 0 if validation["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
