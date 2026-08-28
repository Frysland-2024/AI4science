#!/usr/bin/env python3
"""Validate and summarize the completed frozen CNRS-318 zero-shot run.

This is the tracked replacement for the former ``tmp/analyze_cnrs318.py``.
It treats the external parent as the bootstrap unit, independently verifies the frozen
manifest, input, prediction, and checkpoint identities, and writes a compact local
audit package under ``outputs/cnrs318_zero_shot/audit``. The original inference report
did not embed every one of those identities, which remains an explicit provenance limit.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))

from xrd_robustness.evaluation.metrics import classification_metrics  # noqa: E402
from xrd_robustness.evaluation.statistics import (  # noqa: E402
    class_stratified_paired_bootstrap,
)


CONFIG_PATH = ROOT / "configs/real.cnrs318.zero_shot.frozen.json"
EVAL_MANIFEST = ROOT / "manifests/cnrs318_eval_manifest.csv"
PARENT_MANIFEST = ROOT / "manifests/cnrs_318_parent_manifest_v2.csv"
RUN_ROOT = ROOT / "outputs/cnrs318_zero_shot"
INPUTS_PATH = RUN_ROOT / "cnrs318_inputs.npz"
PREPROCESSING_MANIFEST = RUN_ROOT / "cnrs318_preprocessing_manifest.csv"
PREPROCESSING_REPORT = RUN_ROOT / "cnrs318_preprocessing_report.json"
PREDICTIONS_PATH = RUN_ROOT / "predictions.ndjson"
PREDICTIONS_REPORT = RUN_ROOT / "predictions_report.json"
CHECKPOINT_ROOT = ROOT / "outputs/simulated_test_checkpoints/checkpoints"
SOURCE_ROOT = REPOSITORY_ROOT / "01_literature/data_resources/opxrd_zenodo_14254270/CNRS"
AUDIT_SUMMARY = ROOT / "data/real_xrd/opxrd_cnrs7cs/cnrs_7cs_audit_summary.json"
OUTPUT_ROOT = RUN_ROOT / "audit"

ERM = "ordinary_dynamic_augmentation"
JS = "js_consistency_transfer"
METHOD_NAMES = {ERM: "Dynamic ERM", JS: "JS Consistency"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def source_sha256(path: Path) -> str:
    """Hash text source canonically so Git checkout line endings do not matter."""
    content = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(content).hexdigest().upper()


def read_csv(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(encoding="utf-8-sig")))


def read_ndjson(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def probability_metrics(rows: Sequence[dict[str, Any]], num_classes: int) -> dict[str, Any]:
    labels = np.asarray([row["label_index"] for row in rows], dtype=np.int64)
    predictions = np.asarray(
        [row["prediction_index"] for row in rows], dtype=np.int64
    )
    probabilities = np.asarray([row["probabilities"] for row in rows], dtype=np.float64)
    base = classification_metrics(
        labels,
        predictions,
        probabilities=probabilities,
        num_classes=num_classes,
    )
    clipped = np.clip(probabilities, 1e-12, 1.0)
    one_hot = np.eye(num_classes, dtype=np.float64)[labels]
    confidence = probabilities.max(axis=1)
    entropy = -np.sum(clipped * np.log(clipped), axis=1)
    return {
        **base,
        "nll": -float(np.mean(np.log(clipped[np.arange(len(labels)), labels]))),
        "brier": float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))),
        "mean_confidence": float(confidence.mean()),
        "mean_entropy": float(entropy.mean()),
    }


def git_state() -> dict[str, Any]:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        return {"head": head, "worktree_dirty": bool(status.strip())}
    except (OSError, subprocess.CalledProcessError):
        return {"head": None, "worktree_dirty": None}


def load_prepare_module() -> Any:
    script = ROOT / "scripts/prepare_cnrs318_eval.py"
    spec = importlib.util.spec_from_file_location("prepare_cnrs318_eval", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load preprocessing code from {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_raw_inputs(
    *,
    config: dict[str, Any],
    eval_rows: Sequence[dict[str, str]],
    spectra: np.ndarray,
    source_root: Path,
) -> dict[str, Any]:
    prepare = load_prepare_module()
    maximum_error = 0.0
    missing: list[str] = []
    for index, row in enumerate(eval_rows):
        source = source_root / f"{row['representative_scan_id']}.json"
        if not source.is_file():
            missing.append(source.name)
            continue
        two_theta, intensities, wavelength = prepare.read_spectrum(source)
        rebuilt = prepare.resample(
            two_theta,
            intensities,
            wavelength,
            target_wavelength=float(config["target_wavelength_angstrom"]),
            two_theta_min=float(config["two_theta_min"]),
            two_theta_max=float(config["two_theta_max"]),
            step=float(config["step_deg"]),
        )
        maximum_error = max(
            maximum_error,
            float(np.max(np.abs(rebuilt - spectra[index]))),
        )
    if missing:
        raise ValueError(f"missing {len(missing)} raw CNRS spectra; first: {missing[0]}")
    return {
        "status": "PASS" if maximum_error == 0.0 else "FAIL",
        "source_files_checked": len(eval_rows),
        "maximum_absolute_error": maximum_error,
    }


def checkpoint_run_id(seed: int, method_id: str) -> str:
    suffix = "dynamic_erm" if method_id == ERM else "js_lambda_60"
    return f"seed_{seed}_{suffix}"


def execute(
    *,
    config_path: Path,
    eval_manifest: Path,
    parent_manifest: Path,
    inputs_path: Path,
    preprocessing_manifest: Path,
    preprocessing_report: Path,
    predictions_path: Path,
    predictions_report: Path,
    checkpoint_root: Path,
    source_root: Path,
    audit_summary_path: Path,
    output_root: Path,
    bootstrap_replicates: int,
    bootstrap_seed: int,
    raw_input_check: bool,
) -> dict[str, Any]:
    required = [
        config_path,
        eval_manifest,
        parent_manifest,
        inputs_path,
        preprocessing_manifest,
        preprocessing_report,
        predictions_path,
        predictions_report,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing required CNRS artifacts: {missing}")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    class_order = list(config["class_order"])
    class_counts = {name: int(value) for name, value in config["class_counts"].items()}
    seeds = [int(seed) for seed in config["training_seeds"]]
    methods = [ERM, JS]
    expected_n = int(config["total_parents"])
    if expected_n != sum(class_counts.values()):
        raise ValueError("frozen total_parents does not equal the class-count sum")

    eval_rows = read_csv(eval_manifest)
    parent_rows = read_csv(parent_manifest)
    preprocessing_rows = read_csv(preprocessing_manifest)
    if not (len(eval_rows) == len(parent_rows) == len(preprocessing_rows) == expected_n):
        raise ValueError("eval, parent, and preprocessing manifests are not all length 318")

    parent_by_id = {row["parent_id"]: row for row in parent_rows}
    if len(parent_by_id) != expected_n:
        raise ValueError("parent manifest contains duplicate parent_id values")
    eval_ids = [row["parent_id"] for row in eval_rows]
    if len(set(eval_ids)) != expected_n:
        raise ValueError("eval manifest contains duplicate parent_id values")
    for index, row in enumerate(eval_rows):
        parent = parent_by_id.get(row["parent_id"])
        preprocessed = preprocessing_rows[index]
        if parent is None:
            raise ValueError(f"unknown eval parent: {row['parent_id']}")
        if str(parent.get("formal_14060_overlap", "")).lower() != "false":
            raise ValueError(f"surviving parent overlaps formal_14060: {row['parent_id']}")
        if str(parent.get("symmetry_stable", "")).lower() != "true":
            raise ValueError(f"unstable symmetry label: {row['parent_id']}")
        parent_identity = (
            parent["representative_scan_id"],
            parent["crystal_system"],
            class_order.index(parent["crystal_system"]),
        )
        eval_identity = (
            row["representative_scan_id"],
            row["crystal_system"],
            int(row["label_index"]),
        )
        if parent_identity != eval_identity:
            raise ValueError(f"parent and eval manifests diverge for {row['parent_id']}")
        if str(row.get("excluded", "")).lower() != "false":
            raise ValueError(f"eval row is marked excluded: {row['parent_id']}")
        expected = (
            row["parent_id"],
            row["representative_scan_id"],
            row["crystal_system"],
            int(row["label_index"]),
        )
        observed = (
            preprocessed["parent_id"],
            preprocessed["scan_id"],
            preprocessed["crystal_system"],
            int(preprocessed["label_index"]),
        )
        if observed != expected:
            raise ValueError(f"preprocessing manifest diverges at row {index}")

    observed_class_counts = Counter(row["crystal_system"] for row in eval_rows)
    if dict(observed_class_counts) != class_counts:
        raise ValueError(
            f"eval manifest class counts {dict(observed_class_counts)} != {class_counts}"
        )

    with np.load(inputs_path, allow_pickle=False) as archive:
        if set(archive.files) != {"spectra"}:
            raise ValueError(f"unexpected NPZ arrays: {archive.files}")
        spectra = np.asarray(archive["spectra"])
    expected_shape = (expected_n, int(config["input_length"]))
    if spectra.shape != expected_shape or spectra.dtype != np.float32:
        raise ValueError(f"input matrix is {spectra.shape}/{spectra.dtype}, expected {expected_shape}/float32")
    if not np.isfinite(spectra).all():
        raise ValueError("input matrix contains NaN or Inf")
    if not np.allclose(spectra.max(axis=1), 1.0):
        raise ValueError("input matrix is not max-normalized per spectrum")
    negative_indices = np.flatnonzero(spectra.min(axis=1) < 0.0)
    negative_spectra = [
        {
            "parent_id": eval_rows[int(index)]["parent_id"],
            "scan_id": eval_rows[int(index)]["representative_scan_id"],
            "minimum": float(spectra[int(index)].min()),
        }
        for index in negative_indices
    ]

    eval_hash = sha256(eval_manifest)
    inputs_hash = sha256(inputs_path)
    preprocessing_metadata = json.loads(preprocessing_report.read_text(encoding="utf-8"))
    prediction_metadata = json.loads(predictions_report.read_text(encoding="utf-8"))
    if preprocessing_metadata["eval_manifest_sha256"] != eval_hash:
        raise ValueError("preprocessing report is bound to a different eval manifest")
    if preprocessing_metadata["inputs_sha256"] != inputs_hash:
        raise ValueError("preprocessing report is bound to a different input NPZ")
    if prediction_metadata["dataset_manifest_sha256"] != eval_hash:
        raise ValueError("prediction report is bound to a different eval manifest")

    prediction_rows = read_ndjson(predictions_path)
    expected_rows = expected_n * len(seeds) * len(methods)
    if len(prediction_rows) != expected_rows:
        raise ValueError(f"found {len(prediction_rows)} predictions, expected {expected_rows}")
    expected_identity = {
        (seed, method, parent_id)
        for seed in seeds
        for method in methods
        for parent_id in eval_ids
    }
    seen_identity: set[tuple[int, str, str]] = set()
    checkpoint_hashes_in_predictions: dict[str, set[str]] = defaultdict(set)
    eval_by_id = {row["parent_id"]: row for row in eval_rows}
    maximum_probability_sum_error = 0.0
    for row in prediction_rows:
        identity = (
            int(row["seed"]),
            str(row["method_id"]),
            str(row["parent_structure_id"]),
        )
        if identity in seen_identity:
            raise ValueError(f"duplicate prediction identity: {identity}")
        seen_identity.add(identity)
        if identity not in expected_identity:
            raise ValueError(f"unexpected prediction identity: {identity}")
        manifest_row = eval_by_id[identity[2]]
        if (
            row["scan_id"] != manifest_row["representative_scan_id"]
            or int(row["label_index"]) != int(manifest_row["label_index"])
            or row["true_crystal_system"] != manifest_row["crystal_system"]
        ):
            raise ValueError(f"prediction metadata differs from manifest: {identity}")
        if row["dataset_manifest_sha256"] != eval_hash:
            raise ValueError(f"prediction row has the wrong manifest hash: {identity}")
        probabilities = np.asarray(row["probabilities"], dtype=np.float64)
        if probabilities.shape != (len(class_order),) or not np.isfinite(probabilities).all():
            raise ValueError(f"invalid probability vector: {identity}")
        if np.any(probabilities < 0.0) or np.any(probabilities > 1.0):
            raise ValueError(f"probabilities outside [0, 1]: {identity}")
        maximum_probability_sum_error = max(
            maximum_probability_sum_error,
            abs(float(probabilities.sum()) - 1.0),
        )
        if not np.isclose(float(probabilities.sum()), 1.0, rtol=0.0, atol=1e-6):
            raise ValueError(f"probabilities do not sum to one: {identity}")
        if int(row["prediction_index"]) != int(probabilities.argmax()):
            raise ValueError(f"prediction_index is not argmax: {identity}")
        if not np.isclose(float(row["confidence"]), float(probabilities.max())):
            raise ValueError(f"confidence is not max(probabilities): {identity}")
        run_id = checkpoint_run_id(identity[0], identity[1])
        expected_checkpoint_hash = str(config["checkpoints"][run_id]).upper()
        if str(row["checkpoint_sha256"]).upper() != expected_checkpoint_hash:
            raise ValueError(f"prediction checkpoint hash differs from config: {identity}")
        checkpoint_hashes_in_predictions[run_id].add(expected_checkpoint_hash)
    if seen_identity != expected_identity:
        raise ValueError("prediction identity set is incomplete")

    observed_predictions_hash = sha256(predictions_path)
    if prediction_metadata["predictions_sha256"] != observed_predictions_hash:
        raise ValueError("prediction report is bound to a different predictions file")

    checkpoint_records: list[dict[str, Any]] = []
    for run_id, expected_hash in config["checkpoints"].items():
        checkpoint_path = checkpoint_root / run_id / "best.ckpt"
        if not checkpoint_path.is_file():
            raise FileNotFoundError(f"missing checkpoint: {checkpoint_path}")
        observed_hash = sha256(checkpoint_path)
        if observed_hash != str(expected_hash).upper():
            raise ValueError(f"checkpoint hash mismatch: {run_id}")
        checkpoint_records.append(
            {
                "run_id": run_id,
                "path": str(checkpoint_path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": observed_hash,
                "verified": True,
            }
        )

    by_method_seed: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in prediction_rows:
        by_method_seed[(str(row["method_id"]), int(row["seed"]))].append(row)
    per_seed_rows: list[dict[str, Any]] = []
    per_seed_metrics: dict[tuple[str, int], dict[str, Any]] = {}
    for method in methods:
        for seed in seeds:
            group = by_method_seed[(method, seed)]
            if len(group) != expected_n:
                raise ValueError(f"{method}/{seed} does not contain 318 predictions")
            metrics = probability_metrics(group, len(class_order))
            per_seed_metrics[(method, seed)] = metrics
            per_seed_rows.append(
                {
                    "seed": seed,
                    "method_id": method,
                    "method_name": METHOD_NAMES[method],
                    "macro_f1": metrics["macro_f1"],
                    "balanced_accuracy": metrics["balanced_accuracy"],
                    "accuracy": metrics["accuracy"],
                    "ece": metrics["ece"],
                    "nll": metrics["nll"],
                    "brier": metrics["brier"],
                    "mean_confidence": metrics["mean_confidence"],
                    "mean_entropy": metrics["mean_entropy"],
                }
            )

    paired_seed_rows = []
    for seed in seeds:
        erm_f1 = float(per_seed_metrics[(ERM, seed)]["macro_f1"])
        js_f1 = float(per_seed_metrics[(JS, seed)]["macro_f1"])
        paired_seed_rows.append(
            {
                "seed": seed,
                "erm_macro_f1": erm_f1,
                "js_macro_f1": js_f1,
                "delta_macro_f1": js_f1 - erm_f1,
            }
        )

    pooled: dict[str, dict[str, Any]] = {}
    pooled_rows: list[dict[str, Any]] = []
    for method in methods:
        group = [row for row in prediction_rows if row["method_id"] == method]
        metrics = probability_metrics(group, len(class_order))
        pooled[method] = metrics
        pooled_rows.append(
            {
                "method_id": method,
                "method_name": METHOD_NAMES[method],
                **{
                    key: metrics[key]
                    for key in (
                        "macro_f1",
                        "balanced_accuracy",
                        "accuracy",
                        "ece",
                        "nll",
                        "brier",
                        "mean_confidence",
                        "mean_entropy",
                        "worst_group_f1",
                    )
                },
            }
        )

    per_class_rows: list[dict[str, Any]] = []
    for class_index, class_name in enumerate(class_order):
        support = class_counts[class_name]
        erm_matrix = np.asarray(pooled[ERM]["confusion_matrix"], dtype=np.int64)
        js_matrix = np.asarray(pooled[JS]["confusion_matrix"], dtype=np.int64)
        record: dict[str, Any] = {
            "class_index": class_index,
            "crystal_system": class_name,
            "support_parents": support,
        }
        for prefix, method, matrix in (("erm", ERM, erm_matrix), ("js", JS, js_matrix)):
            tp = float(matrix[class_index, class_index])
            fp = float(matrix[:, class_index].sum() - tp)
            precision = tp / (tp + fp) if tp + fp else 0.0
            record[f"{prefix}_precision"] = precision
            record[f"{prefix}_recall"] = pooled[method]["per_class_recall"][class_index]
            record[f"{prefix}_f1"] = pooled[method]["per_class_f1"][class_index]
        record["delta_f1"] = record["js_f1"] - record["erm_f1"]
        per_class_rows.append(record)

    bootstrap = class_stratified_paired_bootstrap(
        prediction_rows,
        focus_method_id=JS,
        comparator_method_id=ERM,
        num_classes=len(class_order),
        replicates=bootstrap_replicates,
        random_seed=bootstrap_seed,
    )
    deltas = [float(row["delta_macro_f1"]) for row in paired_seed_rows]

    raw_rebuild = (
        verify_raw_inputs(
            config=config,
            eval_rows=eval_rows,
            spectra=spectra,
            source_root=source_root,
        )
        if raw_input_check
        else {"status": "NOT_RUN"}
    )
    if raw_rebuild["status"] == "FAIL":
        raise ValueError(
            "raw CNRS reconstruction differs from the frozen input NPZ: "
            f"maximum absolute error {raw_rebuild['maximum_absolute_error']}"
        )
    integrity_status = "PASS" if raw_rebuild["status"] == "PASS" else "PARTIAL"

    funnel = [
        {"stage": "raw_cnrs_files", "label": "Raw CNRS files", "count": 1052},
        {"stage": "stable_structure_labels", "label": "Stable structure labels", "count": 886},
        {"stage": "spectrum_unique_candidates", "label": "Spectrum-unique candidates", "count": 476},
        {"stage": "structural_parents", "label": "Structural parents", "count": 323},
        {"stage": "independent_parents", "label": "After formal_14060 exclusion", "count": 318},
    ]
    if audit_summary_path.is_file():
        audit_summary = json.loads(audit_summary_path.read_text(encoding="utf-8"))
        counts = audit_summary["counts"]
        funnel = [
            {"stage": "raw_cnrs_files", "label": "Raw CNRS files", "count": counts["source_files"]},
            {"stage": "stable_structure_labels", "label": "Stable structure labels", "count": counts["stable_recomputed_crystal_system"]},
            {"stage": "spectrum_unique_candidates", "label": "Spectrum-unique candidates", "count": counts["mapped_cu_ka_10_80_broad_unique_eligible"]},
            {"stage": "structural_parents", "label": "Structural parents", "count": counts["mapped_cu_ka_10_80_broad_parent_eligible"]},
            {"stage": "independent_parents", "label": "After formal_14060 exclusion", "count": counts["mapped_cu_ka_10_80_broad_parent_independent_eligible"]},
        ]

    analysis_source = Path(__file__).resolve()
    statistics_source = ROOT / "src/xrd_robustness/evaluation/statistics.py"
    summary = {
        "schema_version": "cnrs318-zero-shot-audit-v2",
        "status": "completed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "domain": {
            "dataset_id": config["dataset_id"],
            "role": "naturally_imbalanced_independent_experimental_domain",
            "analysis": "zero_shot_external_evaluation",
            "adaptation_on_cnrs": False,
            "n_parents": expected_n,
            "class_order": class_order,
            "class_counts": class_counts,
        },
        "headline": {
            "mean_seed_paired_delta_macro_f1": float(np.mean(deltas)),
            "positive_seed_pairs": sum(delta > 0.0 for delta in deltas),
            "total_seed_pairs": len(deltas),
            "class_stratified_paired_bootstrap_95_ci": bootstrap[
                "class_stratified_bootstrap_95_ci"
            ],
            "interpretation": "directional_support_not_stable_replication",
        },
        "integrity": {
            "status": integrity_status,
            "prediction_rows": len(prediction_rows),
            "unique_prediction_identities": len(seen_identity),
            "runs": len(seeds) * len(methods),
            "manifest_rows": len(eval_rows),
            "unique_parents": len(set(eval_ids)),
            "manifest_preprocessing_order_match": True,
            "prediction_manifest_metadata_match": True,
            "probability_argmax_and_confidence_match": True,
            "maximum_probability_sum_error": maximum_probability_sum_error,
            "checkpoint_hashes_verified": len(checkpoint_records),
            "raw_input_rebuild": raw_rebuild,
        },
        "inputs": {
            "shape": list(spectra.shape),
            "dtype": str(spectra.dtype),
            "all_finite": True,
            "all_rows_max_normalized": True,
            "negative_spectrum_count": len(negative_spectra),
            "negative_spectra": negative_spectra,
        },
        "hashes": {
            "frozen_config_sha256": sha256(config_path),
            "eval_manifest_sha256": eval_hash,
            "parent_manifest_sha256": sha256(parent_manifest),
            "inputs_sha256": inputs_hash,
            "predictions_sha256": observed_predictions_hash,
            "analysis_script_sha256": source_sha256(analysis_source),
            "statistics_module_sha256": source_sha256(statistics_source),
            "audit_summary_sha256": sha256(audit_summary_path)
            if audit_summary_path.is_file()
            else None,
        },
        "checkpoint_records": checkpoint_records,
        "per_seed": paired_seed_rows,
        "pooled_metrics": {
            method: {
                key: pooled[method][key]
                for key in (
                    "macro_f1",
                    "balanced_accuracy",
                    "accuracy",
                    "ece",
                    "nll",
                    "brier",
                    "mean_confidence",
                    "mean_entropy",
                    "worst_group_f1",
                )
            }
            for method in methods
        },
        "per_class": per_class_rows,
        "confusion_matrices": {
            method: pooled[method]["confusion_matrix"] for method in methods
        },
        "bootstrap": bootstrap,
        "construction_funnel": funnel,
        "baselines": {
            "uniform_random_accuracy": 1.0 / len(class_order),
            "majority_class": max(class_counts, key=class_counts.get),
            "majority_class_accuracy": max(class_counts.values()) / expected_n,
        },
        "limitations": [
            "Structure-derived labels were not independently verified by manual spectrum-level phase analysis.",
            "The domain is naturally imbalanced; hexagonal has 12 parents.",
            "Two frozen inputs retain negative intensities because the preregistered preprocessing did not clip them.",
            "CNRS labels were never used for model adaptation or selection.",
            "The original prediction report did not embed the input NPZ hash, device, or Git commit; those identities were reconstructed in this post-run audit.",
        ],
        "provenance": {
            "analysis_environment": {
                "python": platform.python_version(),
                "numpy": np.__version__,
            },
            "analysis_git": git_state(),
            "inference_execution_git_commit": None,
            "inference_execution_commit_note": (
                "The original one-time inference did not embed its Git commit; file hashes are the authoritative binding."
            ),
        },
    }

    output_root.mkdir(parents=True, exist_ok=True)
    write_json(output_root / "summary.json", summary)
    write_csv(output_root / "per_seed_metrics.csv", per_seed_rows)
    write_csv(output_root / "paired_seed_macro_f1.csv", paired_seed_rows)
    write_csv(output_root / "pooled_metrics.csv", pooled_rows)
    write_csv(output_root / "per_class_metrics.csv", per_class_rows)
    write_csv(output_root / "construction_funnel.csv", funnel)
    write_csv(
        output_root / "class_distribution.csv",
        [
            {
                "class_index": index,
                "crystal_system": name,
                "support_parents": class_counts[name],
            }
            for index, name in enumerate(class_order)
        ],
    )
    write_json(output_root / "bootstrap.json", bootstrap)
    write_json(output_root / "checkpoint_hashes.json", checkpoint_records)
    (output_root / "README.md").write_text(
        "# CNRS-318 local audit package\n\n"
        "Generated by `scripts/analyze_cnrs318_results.py`. The canonical narrative "
        "is `reports/CNRS_318_RESULTS.md`; this ignored directory contains reproducible "
        "machine-readable tables and the portable technical report.\n\n"
        "- `summary.json`: canonical local machine-readable audit.\n"
        "- `bootstrap.json`: corrected class-stratified paired-parent bootstrap.\n"
        "- `per_seed_metrics.csv`: per-method/per-seed probability and classification metrics.\n"
        "- `paired_seed_macro_f1.csv`: the five primary paired effects.\n"
        "- `pooled_metrics.csv`: descriptive five-seed pooled metrics.\n"
        "- `per_class_metrics.csv`: pooled class metrics with parent support.\n"
        "- `artifact.json` and `report.html`: portable technical audit report.\n",
        encoding="utf-8",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--eval-manifest", type=Path, default=EVAL_MANIFEST)
    parser.add_argument("--parent-manifest", type=Path, default=PARENT_MANIFEST)
    parser.add_argument("--inputs", type=Path, default=INPUTS_PATH)
    parser.add_argument("--preprocessing-manifest", type=Path, default=PREPROCESSING_MANIFEST)
    parser.add_argument("--preprocessing-report", type=Path, default=PREPROCESSING_REPORT)
    parser.add_argument("--predictions", type=Path, default=PREDICTIONS_PATH)
    parser.add_argument("--predictions-report", type=Path, default=PREDICTIONS_REPORT)
    parser.add_argument("--checkpoint-root", type=Path, default=CHECKPOINT_ROOT)
    parser.add_argument("--source-root", type=Path, default=SOURCE_ROOT)
    parser.add_argument("--audit-summary", type=Path, default=AUDIT_SUMMARY)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--bootstrap-replicates", type=int, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260827)
    parser.add_argument(
        "--raw-input-check",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Rebuild all 318 spectra from raw CNRS JSON and compare them to the frozen NPZ.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = execute(
        config_path=args.config.resolve(),
        eval_manifest=args.eval_manifest.resolve(),
        parent_manifest=args.parent_manifest.resolve(),
        inputs_path=args.inputs.resolve(),
        preprocessing_manifest=args.preprocessing_manifest.resolve(),
        preprocessing_report=args.preprocessing_report.resolve(),
        predictions_path=args.predictions.resolve(),
        predictions_report=args.predictions_report.resolve(),
        checkpoint_root=args.checkpoint_root.resolve(),
        source_root=args.source_root.resolve(),
        audit_summary_path=args.audit_summary.resolve(),
        output_root=args.output_root.resolve(),
        bootstrap_replicates=args.bootstrap_replicates,
        bootstrap_seed=args.bootstrap_seed,
        raw_input_check=args.raw_input_check,
    )
    print(json.dumps(summary["headline"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
