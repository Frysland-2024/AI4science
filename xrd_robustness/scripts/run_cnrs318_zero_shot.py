#!/usr/bin/env python3
"""Run the frozen CNRS318 zero-shot evaluation (10 frozen checkpoints).

For each of the five Dynamic ERM and five JS checkpoints, predict the 318 frozen
parents and emit one prediction row per (seed, method, parent).  The primary analysis
uses the five independent seeds; a soft-voting ensemble is only a deployment-side extra.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xrd_robustness.experiment import assert_model_fingerprint, load_checkpoint  # noqa: E402
from xrd_robustness.models import ML4PXRDResNet1D, ML4PXRDResNet1DConfig  # noqa: E402

CONFIG_PATH = ROOT / "configs/real.cnrs318.zero_shot.frozen.json"
EXPERIMENT_PATH = ROOT / "configs/experiment.public.json"
EVAL_MANIFEST = ROOT / "manifests/cnrs318_eval_manifest.csv"
INPUTS_PATH = ROOT / "outputs/cnrs318_zero_shot/cnrs318_inputs.npz"
OUTPUT_ROOT = ROOT / "outputs/cnrs318_zero_shot"
CHECKPOINT_ROOT = ROOT / "outputs/simulated_test_checkpoints/checkpoints"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def method_for_run_id(run_id: str) -> tuple[str, str]:
    if "dynamic_erm" in run_id:
        return "ordinary_dynamic_augmentation", "Dynamic ERM"
    if "js_lambda_60" in run_id:
        return "js_consistency_transfer", "JS Consistency"
    raise ValueError(f"unknown run id: {run_id}")


def run_specs(config: dict[str, Any]) -> list[dict[str, Any]]:
    experiment = json.loads(EXPERIMENT_PATH.read_text(encoding="utf-8"))
    specs: list[dict[str, Any]] = []
    for pair in experiment["runs"]:
        seed = int(pair["training_seed"])
        for run_id in (pair["dynamic_erm_run_id"], pair["js_run_id"]):
            method_id, method_name = method_for_run_id(run_id)
            expected = config["checkpoints"].get(run_id)
            if not expected:
                raise ValueError(f"run id missing from frozen config: {run_id}")
            specs.append(
                {
                    "training_seed": seed,
                    "run_id": run_id,
                    "method_id": method_id,
                    "method_name": method_name,
                    "checkpoint_sha256": expected,
                }
            )
    if len(specs) != 10:
        raise ValueError(f"expected 10 run specs, got {len(specs)}")
    return specs


def _device(value: str) -> torch.device:
    if value == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(value)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    return device


def execute(
    *,
    config_path: Path = CONFIG_PATH,
    eval_manifest: Path = EVAL_MANIFEST,
    inputs_path: Path = INPUTS_PATH,
    checkpoint_root: Path = CHECKPOINT_ROOT,
    output_root: Path = OUTPUT_ROOT,
    batch_size: int = 128,
    device_name: str = "auto",
) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    class_order = list(config["class_order"])
    if not inputs_path.is_file():
        raise RuntimeError("run prepare_cnrs318_eval.py before zero-shot inference")
    archive = np.load(inputs_path, allow_pickle=False)
    matrix = archive["spectra"]
    n_parents = int(config["total_parents"])
    if matrix.shape != (n_parents, int(config["input_length"])):
        raise RuntimeError(f"inputs shape {matrix.shape} does not match frozen config")
    manifest_rows = list(csv_reader(eval_manifest))
    if len(manifest_rows) != n_parents:
        raise RuntimeError("eval manifest length does not match inputs")
    dataset_manifest_sha256 = sha256(eval_manifest)

    device = _device(device_name)
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / "predictions.ndjson"
    rows: list[dict[str, Any]] = []

    for spec in run_specs(config):
        checkpoint_path = checkpoint_root / spec["run_id"] / "best.ckpt"
        if not checkpoint_path.is_file():
            raise RuntimeError(f"missing checkpoint: {checkpoint_path}")
        observed = sha256(checkpoint_path)
        if observed != spec["checkpoint_sha256"]:
            raise RuntimeError(
                f"checkpoint changed: {spec['run_id']} {observed} != {spec['checkpoint_sha256']}"
            )
        model_config = ML4PXRDResNet1DConfig(model_id="18")
        model = ML4PXRDResNet1D(model_config)
        payload = load_checkpoint(checkpoint_path, model=model, map_location="cpu")
        assert_model_fingerprint(model, model_config, payload["model_fingerprint"])
        model.to(device)
        model.eval()

        probabilities = np.zeros((n_parents, len(class_order)), dtype=np.float32)
        with torch.inference_mode():
            for start in range(0, n_parents, batch_size):
                stop = min(start + batch_size, n_parents)
                batch = torch.from_numpy(np.array(matrix[start:stop], copy=True))
                context = (
                    torch.autocast(device_type="cuda", dtype=torch.float16)
                    if device.type == "cuda"
                    else nullcontext()
                )
                with context:
                    logits = model(batch.to(device))["logits"]
                    probabilities[start:stop] = (
                        torch.softmax(logits, dim=-1).float().cpu().numpy()
                    )

        predictions = probabilities.argmax(axis=1)
        confidence = probabilities.max(axis=1)
        for index, manifest_row in enumerate(manifest_rows):
            rows.append(
                {
                    "seed": spec["training_seed"],
                    "method_id": spec["method_id"],
                    "method_name": spec["method_name"],
                    "profile": "cnrs318_zero_shot",
                    "scan_id": manifest_row["representative_scan_id"],
                    "parent_structure_id": manifest_row["parent_id"],
                    "true_crystal_system": manifest_row["crystal_system"],
                    "label_index": int(manifest_row["label_index"]),
                    "prediction_index": int(predictions[index]),
                    "probabilities": [float(v) for v in probabilities[index]],
                    "confidence": float(confidence[index]),
                    "manual_review_status": "not_planned",
                    "checkpoint_sha256": spec["checkpoint_sha256"],
                    "dataset_manifest_sha256": dataset_manifest_sha256,
                }
            )
        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()

    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    report = {
        "schema_version": "cnrs318-zero-shot-predictions-v1",
        "status": "completed",
        "n_parents": n_parents,
        "n_runs": 10,
        "n_rows": len(rows),
        "class_order": class_order,
        "predictions_sha256": sha256(output_path),
        "dataset_manifest_sha256": dataset_manifest_sha256,
    }
    (output_root / "predictions_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def csv_reader(path: Path) -> list[dict[str, str]]:
    import csv

    return list(csv.DictReader(path.open(encoding="utf-8-sig")))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run frozen CNRS318 zero-shot inference")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--eval-manifest", type=Path, default=EVAL_MANIFEST)
    parser.add_argument("--inputs", type=Path, default=INPUTS_PATH)
    parser.add_argument("--checkpoint-root", type=Path, default=CHECKPOINT_ROOT)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--device", default="auto")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = execute(
        config_path=args.config.resolve(),
        eval_manifest=args.eval_manifest.resolve(),
        inputs_path=args.inputs.resolve(),
        checkpoint_root=args.checkpoint_root.resolve(),
        output_root=args.output_root.resolve(),
        batch_size=args.batch_size,
        device_name=args.device,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
