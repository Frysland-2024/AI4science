#!/usr/bin/env python3
"""Frozen CNRS-318 structure-linked simulation-to-experiment gap analysis.

For each frozen CNRS parent, rebuild the deposited structure, render one frozen
`level0` PXRD profile, pair it with the already prepared experimental CNRS input,
and compare the ten frozen Dynamic-ERM / JS checkpoints.

This script does not train, tune, adapt, calibrate, select, or modify any model.
CNRS phase metadata were not manually verified spectrum-by-spectrum, so the
pairs are described as *structure-linked simulated–experimental pairs*.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from audit_opxrd_cnrs_7cs import load_single_phase_structure  # noqa: E402
from run_cnrs318_zero_shot import _device, sha256, validate_preprocessing_handshake  # noqa: E402
from xrd_robustness.experiment import assert_model_fingerprint, load_checkpoint  # noqa: E402
from xrd_robustness.models import ML4PXRDResNet1D, ML4PXRDResNet1DConfig  # noqa: E402
from xrd_robustness.physics import PhysicsParameterSampler  # noqa: E402
from xrd_robustness.simulator import SimulationGrid, simulate_structure  # noqa: E402

CONFIG = ROOT / "configs/real.cnrs318.zero_shot.frozen.json"
EXPERIMENT = ROOT / "configs/experiment.public.json"
EVAL_MANIFEST = ROOT / "manifests/cnrs318_eval_manifest.csv"
REAL_INPUTS = ROOT / "outputs/cnrs318_zero_shot/cnrs318_inputs.npz"
PREPROCESS_REPORT = ROOT / "outputs/cnrs318_zero_shot/cnrs318_preprocessing_report.json"
SOURCE_ROOT = ROOT.parent / "01_literature/data_resources/opxrd_zenodo_14254270/CNRS"
CHECKPOINT_ROOT = ROOT / "outputs/simulated_test_checkpoints/checkpoints"
OUTPUT_ROOT = ROOT / "outputs/cnrs_sim_real_analysis"

ERM_ID = "ordinary_dynamic_augmentation"
JS_ID = "js_consistency_transfer"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def method_for_run_id(run_id: str) -> tuple[str, str]:
    if "dynamic_erm" in run_id:
        return ERM_ID, "Dynamic ERM"
    if "js_lambda_60" in run_id:
        return JS_ID, "JS Consistency"
    raise ValueError(f"unknown frozen run id: {run_id}")


def run_specs(config: dict[str, Any], experiment_path: Path) -> list[dict[str, Any]]:
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    specs: list[dict[str, Any]] = []
    for pair in experiment["runs"]:
        seed = int(pair["training_seed"])
        for run_id in (pair["dynamic_erm_run_id"], pair["js_run_id"]):
            method_id, method_name = method_for_run_id(run_id)
            expected_sha = config["checkpoints"].get(run_id)
            if not expected_sha:
                raise RuntimeError(f"checkpoint hash missing for {run_id}")
            specs.append(
                {
                    "seed": seed,
                    "run_id": run_id,
                    "method_id": method_id,
                    "method_name": method_name,
                    "checkpoint_sha256": expected_sha,
                }
            )
    if len(specs) != 10:
        raise RuntimeError(f"expected 10 frozen checkpoints, got {len(specs)}")
    return specs


def load_real_inputs(
    config: dict[str, Any],
    eval_manifest: Path,
    inputs_path: Path,
    preprocess_report: Path,
) -> tuple[np.ndarray, list[dict[str, str]]]:
    validate_preprocessing_handshake(
        preprocessing_report=preprocess_report,
        eval_manifest=eval_manifest,
        inputs_path=inputs_path,
    )
    matrix = np.asarray(np.load(inputs_path, allow_pickle=False)["spectra"], dtype=np.float32)
    rows = read_csv(eval_manifest)
    expected = (int(config["total_parents"]), int(config["input_length"]))
    if matrix.shape != expected or len(rows) != expected[0]:
        raise RuntimeError(f"frozen CNRS inputs/manifest do not match {expected}")
    if not np.isfinite(matrix).all():
        raise RuntimeError("frozen CNRS inputs contain non-finite values")
    return matrix, rows


def build_level0_simulation(
    config: dict[str, Any],
    experiment_path: Path,
    manifest_rows: list[dict[str, str]],
    source_root: Path,
) -> tuple[np.ndarray, list[dict[str, Any]], Path]:
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    sim_path = ROOT / experiment["config_paths"]["simulation"]
    simulation = json.loads(sim_path.read_text(encoding="utf-8"))
    sampler = PhysicsParameterSampler.from_mapping(simulation)
    grid = SimulationGrid(
        two_theta_min=float(config["two_theta_min"]),
        two_theta_max=float(config["two_theta_max"]),
        step=float(config["step_deg"]),
        wavelength=float(config["target_wavelength_angstrom"]),
    )
    matrix = np.zeros(
        (int(config["total_parents"]), int(config["input_length"])),
        dtype=np.float32,
    )
    provenance: list[dict[str, Any]] = []
    for position, row in enumerate(manifest_rows):
        parent_id = row["parent_id"]
        scan_id = row["representative_scan_id"]
        source_path = source_root / f"{scan_id}.json"
        if not source_path.is_file():
            raise RuntimeError(f"missing CNRS source record: {source_path}")
        structure = load_single_phase_structure(source_path)
        params, view_seed = sampler.sample(
            "level0",
            epoch=0,
            global_step=0,
            material_id=parent_id,
            view_id=0,
        )
        spectrum = np.asarray(
            simulate_structure(structure, params, rng_seed=view_seed, grid=grid),
            dtype=np.float32,
        )
        if spectrum.shape != (matrix.shape[1],) or not np.isfinite(spectrum).all():
            raise RuntimeError(f"invalid level0 simulation for {parent_id}")
        matrix[position] = spectrum
        provenance.append(
            {
                "position": position,
                "parent_id": parent_id,
                "scan_id": scan_id,
                "crystal_system": row["crystal_system"],
                "label_index": int(row["label_index"]),
                "view_seed": int(view_seed),
            }
        )
    return matrix, provenance, sim_path


def infer(
    model: ML4PXRDResNet1D,
    matrix: np.ndarray,
    *,
    device: torch.device,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    probabilities = np.zeros((len(matrix), model.config.num_classes), dtype=np.float32)
    embeddings = np.zeros((len(matrix), model.config.embed_dim), dtype=np.float32)
    model.eval()
    with torch.inference_mode():
        for start in range(0, len(matrix), batch_size):
            stop = min(start + batch_size, len(matrix))
            batch = torch.from_numpy(np.array(matrix[start:stop], copy=True)).to(device)
            context = (
                torch.autocast(device_type="cuda", dtype=torch.float16)
                if device.type == "cuda"
                else nullcontext()
            )
            with context:
                output = model(batch)
            probabilities[start:stop] = (
                torch.softmax(output["logits"], dim=-1).float().cpu().numpy()
            )
            embeddings[start:stop] = output["pooled_embedding"].float().cpu().numpy()
    return probabilities, embeddings


def cosine_distance(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    first = np.asarray(first, dtype=np.float64)
    second = np.asarray(second, dtype=np.float64)
    numerator = np.sum(first * second, axis=1)
    denominator = np.linalg.norm(first, axis=1) * np.linalg.norm(second, axis=1)
    if np.any(denominator <= 0):
        raise RuntimeError("zero-norm embedding encountered")
    return 1.0 - np.clip(numerator / denominator, -1.0, 1.0)


def js_divergence(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    first = np.asarray(first, dtype=np.float64)
    second = np.asarray(second, dtype=np.float64)
    first = first / first.sum(axis=1, keepdims=True)
    second = second / second.sum(axis=1, keepdims=True)
    midpoint = 0.5 * (first + second)
    result = np.zeros(first.shape[0], dtype=np.float64)
    for values in (first, second):
        mask = values > 0
        term = np.zeros_like(values)
        term[mask] = values[mask] * np.log(values[mask] / midpoint[mask])
        result += 0.5 * term.sum(axis=1)
    return result


def true_margin(probabilities: np.ndarray, labels: np.ndarray) -> np.ndarray:
    probabilities = np.asarray(probabilities, dtype=np.float64)
    labels = np.asarray(labels, dtype=np.int64)
    true_values = probabilities[np.arange(len(labels)), labels]
    other = probabilities.copy()
    other[np.arange(len(labels)), labels] = -np.inf
    return true_values - np.max(other, axis=1)


def build_rows(
    spec: dict[str, Any],
    manifest: list[dict[str, str]],
    sim_p: np.ndarray,
    real_p: np.ndarray,
    sim_z: np.ndarray,
    real_z: np.ndarray,
) -> list[dict[str, Any]]:
    labels = np.asarray([int(row["label_index"]) for row in manifest], dtype=np.int64)
    sim_pred = sim_p.argmax(axis=1)
    real_pred = real_p.argmax(axis=1)
    sim_margin = true_margin(sim_p, labels)
    real_margin = true_margin(real_p, labels)
    cos = cosine_distance(sim_z, real_z)
    pjs = js_divergence(sim_p, real_p)
    rows: list[dict[str, Any]] = []
    for i, meta in enumerate(manifest):
        label = int(labels[i])
        rows.append(
            {
                "seed": int(spec["seed"]),
                "method_id": spec["method_id"],
                "method_name": spec["method_name"],
                "parent_id": meta["parent_id"],
                "scan_id": meta["representative_scan_id"],
                "crystal_system": meta["crystal_system"],
                "label_index": label,
                "embedding_cosine_distance": float(cos[i]),
                "prediction_js_divergence": float(pjs[i]),
                "prediction_flip": int(sim_pred[i] != real_pred[i]),
                "sim_prediction_index": int(sim_pred[i]),
                "real_prediction_index": int(real_pred[i]),
                "sim_correct": int(sim_pred[i] == label),
                "real_correct": int(real_pred[i] == label),
                "sim_true_probability": float(sim_p[i, label]),
                "real_true_probability": float(real_p[i, label]),
                "true_probability_drop": float(sim_p[i, label] - real_p[i, label]),
                "sim_true_margin": float(sim_margin[i]),
                "real_true_margin": float(real_margin[i]),
                "true_margin_drop": float(sim_margin[i] - real_margin[i]),
                "checkpoint_sha256": spec["checkpoint_sha256"],
            }
        )
    return rows


def mean(rows: list[dict[str, Any]], field: str) -> float:
    return float(np.mean([float(row[field]) for row in rows]))


def summarize(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((int(row["seed"]), str(row["method_id"])), []).append(row)

    per_method: list[dict[str, Any]] = []
    for (seed, method_id), members in sorted(groups.items()):
        per_method.append(
            {
                "seed": seed,
                "method_id": method_id,
                "method_name": members[0]["method_name"],
                "mean_embedding_cosine_distance": mean(members, "embedding_cosine_distance"),
                "mean_prediction_js_divergence": mean(members, "prediction_js_divergence"),
                "prediction_flip_rate": mean(members, "prediction_flip"),
                "mean_true_probability_drop": mean(members, "true_probability_drop"),
                "mean_true_margin_drop": mean(members, "true_margin_drop"),
                "sim_accuracy": mean(members, "sim_correct"),
                "real_accuracy": mean(members, "real_correct"),
            }
        )

    indexed = {(int(row["seed"]), str(row["method_id"])): row for row in per_method}
    paired: list[dict[str, Any]] = []
    for seed in sorted({int(row["seed"]) for row in per_method}):
        erm = indexed[(seed, ERM_ID)]
        js = indexed[(seed, JS_ID)]
        paired.append(
            {
                "seed": seed,
                "delta_embedding_cosine_distance_js_minus_erm": (
                    js["mean_embedding_cosine_distance"]
                    - erm["mean_embedding_cosine_distance"]
                ),
                "delta_prediction_js_divergence_js_minus_erm": (
                    js["mean_prediction_js_divergence"]
                    - erm["mean_prediction_js_divergence"]
                ),
                "delta_prediction_flip_rate_js_minus_erm": (
                    js["prediction_flip_rate"] - erm["prediction_flip_rate"]
                ),
                "delta_true_probability_drop_js_minus_erm": (
                    js["mean_true_probability_drop"] - erm["mean_true_probability_drop"]
                ),
                "delta_true_margin_drop_js_minus_erm": (
                    js["mean_true_margin_drop"] - erm["mean_true_margin_drop"]
                ),
            }
        )
    return per_method, paired


def execute(args: argparse.Namespace) -> dict[str, Any]:
    config = json.loads(args.config.read_text(encoding="utf-8"))
    observed_experiment_sha = sha256(args.experiment)
    expected_experiment_sha = config.get("hashes", {}).get("experiment_config_sha256")
    if expected_experiment_sha and observed_experiment_sha != expected_experiment_sha:
        raise RuntimeError(
            f"experiment config changed: {observed_experiment_sha} != {expected_experiment_sha}"
        )

    real, manifest = load_real_inputs(
        config, args.eval_manifest, args.real_inputs, args.preprocess_report
    )
    simulated, provenance, sim_config_path = build_level0_simulation(
        config, args.experiment, manifest, args.source_root
    )

    args.output_root.mkdir(parents=True, exist_ok=True)
    simulated_path = args.output_root / "cnrs318_level0_simulated_inputs.npz"
    np.savez(simulated_path, spectra=simulated)
    write_csv(args.output_root / "simulation_provenance.csv", provenance)

    device = _device(args.device)
    rows: list[dict[str, Any]] = []
    for spec in run_specs(config, args.experiment):
        checkpoint = args.checkpoint_root / spec["run_id"] / "best.ckpt"
        if not checkpoint.is_file():
            raise RuntimeError(f"missing checkpoint: {checkpoint}")
        observed = sha256(checkpoint)
        if observed != spec["checkpoint_sha256"]:
            raise RuntimeError(
                f"checkpoint changed for {spec['run_id']}: {observed} "
                f"!= {spec['checkpoint_sha256']}"
            )

        model_config = ML4PXRDResNet1DConfig(model_id="18")
        model = ML4PXRDResNet1D(model_config)
        payload = load_checkpoint(checkpoint, model=model, map_location="cpu")
        assert_model_fingerprint(model, model_config, payload["model_fingerprint"])
        model.to(device)

        sim_p, sim_z = infer(model, simulated, device=device, batch_size=args.batch_size)
        real_p, real_z = infer(model, real, device=device, batch_size=args.batch_size)
        rows.extend(build_rows(spec, manifest, sim_p, real_p, sim_z, real_z))

        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()

    expected_rows = int(config["total_parents"]) * 10
    if len(rows) != expected_rows:
        raise RuntimeError(f"expected {expected_rows} rows, got {len(rows)}")

    paired_metrics = args.output_root / "paired_metrics.csv"
    write_csv(paired_metrics, rows)
    per_method, paired = summarize(rows)
    write_csv(args.output_root / "seed_method_summary.csv", per_method)
    write_csv(args.output_root / "seed_paired_deltas.csv", paired)

    summary = {
        "schema_version": "cnrs318-sim-real-gap-v1",
        "status": "completed",
        "role": "post_hoc_frozen_representation_diagnostic",
        "pairing_term": "structure-linked simulated-experimental pairs",
        "n_parents": int(config["total_parents"]),
        "n_frozen_runs": 10,
        "simulation_profile": "level0",
        "metric_direction": {
            "embedding_cosine_distance": "lower sim-to-real gap is better",
            "prediction_js_divergence": "lower sim-to-real gap is better",
            "prediction_flip_rate": "lower sim-to-real gap is better",
            "true_probability_drop": "lower drop is better",
            "true_margin_drop": "lower drop is better",
        },
        "seed_method_summary": per_method,
        "seed_paired_deltas_js_minus_erm": paired,
        "hashes": {
            "config_sha256": sha256(args.config),
            "experiment_sha256": observed_experiment_sha,
            "eval_manifest_sha256": sha256(args.eval_manifest),
            "real_inputs_sha256": sha256(args.real_inputs),
            "preprocess_report_sha256": sha256(args.preprocess_report),
            "simulation_config_sha256": sha256(sim_config_path),
            "simulated_inputs_sha256": sha256(simulated_path),
            "paired_metrics_sha256": sha256(paired_metrics),
        },
        "runtime": {
            "device": str(device),
            "autocast": "float16" if device.type == "cuda" else "disabled",
            "torch_version": torch.__version__,
            "numpy_version": np.__version__,
        },
        "limitations": [
            "CNRS simulated counterparts are linked through deposited structures, not manual spectrum-level phase verification.",
            "The five matched training seeds are repeated model evaluations on one CNRS domain, not five independent datasets.",
            "No training, tuning, adaptation, calibration fitting, or model selection occurs in this analysis.",
        ],
    }
    (args.output_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Frozen CNRS structure-linked simulation-to-experiment gap analysis"
    )
    p.add_argument("--config", type=Path, default=CONFIG)
    p.add_argument("--experiment", type=Path, default=EXPERIMENT)
    p.add_argument("--eval-manifest", type=Path, default=EVAL_MANIFEST)
    p.add_argument("--real-inputs", type=Path, default=REAL_INPUTS)
    p.add_argument("--preprocess-report", type=Path, default=PREPROCESS_REPORT)
    p.add_argument("--source-root", type=Path, default=SOURCE_ROOT)
    p.add_argument("--checkpoint-root", type=Path, default=CHECKPOINT_ROOT)
    p.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    p.add_argument("--batch-size", type=int, default=128)
    p.add_argument("--device", default="auto")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    for name in (
        "config",
        "experiment",
        "eval_manifest",
        "real_inputs",
        "preprocess_report",
        "source_root",
        "checkpoint_root",
        "output_root",
    ):
        setattr(args, name, getattr(args, name).resolve())
    summary = execute(args)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
