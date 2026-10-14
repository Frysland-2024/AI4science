#!/usr/bin/env python
"""Short GPU benchmark of the matched parent-budget physical training pipeline."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_parent_budget_pair as pair  # noqa: E402
from xrd_robustness.online_views import OnlineViewFactory, TrainingMode  # noqa: E402
from xrd_robustness.perturbation_strategy import IndependentDynamicStrategy  # noqa: E402
from xrd_robustness.training.objectives import TrainingStepConfig  # noqa: E402
from xrd_robustness.training.paired import paired_optimizer_step  # noqa: E402
from xrd_robustness.training_prefetch import DynamicBatchPrefetcher  # noqa: E402
from xrd_robustness.view_manifest import build_parameter_batch  # noqa: E402


def _nvidia_smi() -> str | None:
    try:
        return subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except Exception:
        return None


def _benchmark_setting(
    *,
    data_root: Path,
    output_root: Path,
    base_config: dict[str, Any],
    subset_manifest: Path,
    ranked_parents: Path,
    simulation_path: Path,
    validation_panels: dict[str, np.ndarray],
    validation_labels: np.ndarray,
    device: torch.device,
    workers: int,
    prefetch_batches: int,
    warmup_steps: int,
    measured_steps: int,
) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    prefetch = config["performance"]["dynamic_prefetch"]
    prefetch["worker_processes"] = workers
    prefetch["prefetch_batches"] = prefetch_batches
    runtime = pair._configure_training_runtime(config, device)

    train_rows, _, manifest = pair._load_subset_rows(
        # Benchmark against the largest frozen subset to avoid a warm,
        # frequently repeated 10% peak working set biasing the estimate.
        data_root, subset_manifest, ranked_parents, "100"
    )
    train_by_id = {str(row["material_id"]): row for row in train_rows}
    ordered_ids = manifest["budgets"]["100"]["material_ids"]
    rows_by_id = [train_by_id[material_id] for material_id in ordered_ids]
    records = [pair._record_from_split(row, data_root) for row in rows_by_id]
    simulation = json.loads(simulation_path.read_text(encoding="utf-8"))
    sim_hash = pair.file_hash(simulation_path)
    sampler_config = {**simulation, "run_seed": 20260711}
    sampler = pair.PhysicsParameterSampler.from_mapping(sampler_config)
    rng = pair.CyclicParentSampler(rows_by_id, seed=20260711)
    model_config = pair.ML4PXRDResNet1DConfig(model_id="18")

    torch.manual_seed(20260711)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(20260711)
        torch.cuda.reset_peak_memory_stats(device)
    base = pair.build_model(model_config)
    models = {
        "dynamic_erm": copy.deepcopy(base).to(device),
        "dynamic_js": copy.deepcopy(base).to(device),
    }
    del base
    optimizers = {
        name: torch.optim.AdamW(
            model.parameters(),
            lr=float(config["training"]["learning_rate"]),
            weight_decay=float(config["training"]["weight_decay"]),
            fused=runtime["fused_adamw"],
        )
        for name, model in models.items()
    }
    objective_configs = {
        "dynamic_erm": TrainingStepConfig(TrainingMode.DYNAMIC_ERM, lambda_js=0.0),
        "dynamic_js": TrainingStepConfig(
            TrainingMode.DYNAMIC_JS,
            lambda_js=float(config["matrix"]["lambda_js"]),
        ),
    }
    prefetcher = DynamicBatchPrefetcher(
        worker_count=workers,
        worker_native_threads=int(prefetch["worker_native_threads"]),
        prefetch_batches=prefetch_batches,
        start_method=str(prefetch["multiprocessing_start_method"]),
        data_root=data_root,
        peak_cache_name=str(prefetch["peak_cache_name"]),
        sampler_config=sampler_config,
        quality_gate=bool(prefetch["quality_gate"]),
        quality_gate_config=simulation.get("quality_gates", {}),
        simulation_config_hash=sim_hash,
        profile="train",
    )
    batches: dict[int, list[Any]] = {}
    view_rows: dict[int, list[Any]] = {}
    sample_digest_ok: bool | None = None
    elapsed_prefetch_wait = 0.0
    total_steps = warmup_steps + measured_steps

    def submit(step_index: int) -> None:
        batch_rows = rng.next_batch(int(config["training"]["batch_size_parents"]))
        batch = [pair._record_from_split(row, data_root) for row in batch_rows]
        ids = [record.material_id for record in batch]
        parameter_rows = build_parameter_batch(
            ids,
            sampler,
            profile="train",
            epoch=0,
            global_step=step_index,
            split="train",
        )
        prefetcher.submit(step_index, ids, parameter_rows)
        batches[step_index] = batch
        view_rows[step_index] = parameter_rows

    measured_started: float | None = None
    try:
        for step_index in range(min(prefetch_batches, total_steps)):
            submit(step_index)
        for step_index in range(total_steps):
            waited_at = time.perf_counter()
            rendered = prefetcher.get(step_index)
            waited = time.perf_counter() - waited_at
            batch = batches.pop(step_index)
            parameter_rows = view_rows.pop(step_index)
            if step_index == 0:
                direct_factory = OnlineViewFactory(
                    sampler,
                    strategy=IndependentDynamicStrategy(sampler, config_hash=sim_hash),
                )
                direct_first: list[np.ndarray] = []
                direct_second: list[np.ndarray] = []
                for record in batch:
                    peaks = pair.load_peak_table(record.peak_table_path)
                    by_view = {
                        row.view_id: row
                        for row in parameter_rows
                        if row.material_id == record.material_id
                    }
                    direct_first.append(
                        direct_factory.make_view_from_manifest(
                            peaks, by_view[1]
                        ).xrd
                    )
                    direct_second.append(
                        direct_factory.make_view_from_manifest(
                            peaks, by_view[2]
                        ).xrd
                    )
                sample_digest_ok = bool(
                    np.array_equal(rendered.first, np.stack(direct_first))
                    and np.array_equal(rendered.second, np.stack(direct_second))
                )
                if not sample_digest_ok:
                    raise AssertionError(
                        "multiprocess and direct physical rendering are not bitwise equal"
                    )
            next_index = step_index + prefetch_batches
            if next_index < total_steps:
                submit(next_index)

            x1_cpu = torch.from_numpy(np.asarray(rendered.first, dtype=np.float32))
            x2_cpu = torch.from_numpy(np.asarray(rendered.second, dtype=np.float32))
            target_cpu = torch.tensor([record.label for record in batch], dtype=torch.long)
            x1 = pair._tensor_to_device(
                x1_cpu, device, pin_memory=True, non_blocking=True
            )
            x2 = pair._tensor_to_device(
                x2_cpu, device, pin_memory=True, non_blocking=True
            )
            target = pair._tensor_to_device(
                target_cpu, device, pin_memory=True, non_blocking=True
            )
            if step_index == warmup_steps:
                if device.type == "cuda":
                    torch.cuda.synchronize(device)
                    torch.cuda.reset_peak_memory_stats(device)
                measured_started = time.perf_counter()
            paired_optimizer_step(
                models,
                optimizers,
                objective_configs,
                x1=x1,
                x2=x2,
                target=target,
                autocast_dtype=torch.bfloat16 if runtime["amp_enabled"] else None,
            )
            if measured_started is not None:
                elapsed_prefetch_wait += waited
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        if measured_started is None:
            raise RuntimeError("benchmark did not enter the measured section")
        elapsed = time.perf_counter() - measured_started
    finally:
        prefetcher.close()

    steps_per_second = measured_steps / elapsed
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    validation_started = time.perf_counter()
    validation_seed = int(config["evaluation"]["validation_evaluation_seed"])
    for model in models.values():
        pair._evaluate_model(
            model,
            validation_panels,
            validation_labels,
            seeds=[validation_seed],
            profiles=pair.PROFILES[:7],
            batch_size=int(config["evaluation"]["batch_size"]),
            device=device,
            amp_dtype=None,
            pin_memory=bool(prefetch["pin_memory"]),
            non_blocking_h2d=bool(prefetch["non_blocking_h2d"]),
        )
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    validation_pair_seconds = time.perf_counter() - validation_started
    validation_interval = int(config["training"]["validation_interval_steps"])
    validations_per_cell = int(np.ceil(int(config["training"]["optimizer_steps_per_model"]) / validation_interval))
    training_seconds_per_cell = int(config["training"]["optimizer_steps_per_model"]) / steps_per_second
    estimates = {}
    for method_runs in (8, 24, 40):
        paired_cells = method_runs // 2
        training_seconds = paired_cells * training_seconds_per_cell
        validation_seconds = paired_cells * validations_per_cell * validation_pair_seconds
        estimates[str(method_runs)] = {
            "method_runs": method_runs,
            "paired_cells": paired_cells,
            "training_hours": training_seconds / 3600,
            "validation_hours": validation_seconds / 3600,
            "training_plus_validation_hours": (training_seconds + validation_seconds) / 3600,
            "validation_checks_per_cell": validations_per_cell,
        }
    peak_memory = (
        int(torch.cuda.max_memory_allocated(device)) if device.type == "cuda" else None
    )
    return {
        "workers": workers,
        "prefetch_batches": prefetch_batches,
        "warmup_steps": warmup_steps,
        "measured_steps": measured_steps,
        "elapsed_seconds": elapsed,
        "paired_optimizer_steps_per_second": steps_per_second,
        "parent_occurrences_per_second": steps_per_second * int(config["training"]["batch_size_parents"]),
        "generated_views_per_second": steps_per_second * int(config["training"]["batch_size_parents"]) * 2,
        "prefetch_wait_seconds_in_measured_section": elapsed_prefetch_wait,
        "validation_pair_seconds_per_checkpoint": validation_pair_seconds,
        "validation_checks_per_cell": validations_per_cell,
        "direct_vs_prefetch_render_bitwise_equal": sample_digest_ok,
        "peak_cuda_allocated_bytes": peak_memory,
        "runtime": runtime,
        "time_estimates": estimates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--protocol-config", type=Path, default=PROJECT_ROOT / "configs/parent_budget_efficiency.v1.json")
    parser.add_argument("--subset-manifest", type=Path, default=PROJECT_ROOT / "manifests/parent_budget_efficiency/parent_subsets.v1.json")
    parser.add_argument("--ranked-parents", type=Path, default=PROJECT_ROOT / "manifests/parent_budget_efficiency/ranked_train_parents.v1.csv")
    parser.add_argument("--simulation-config", type=Path, default=PROJECT_ROOT / "configs/simulation.method_transfer.frozen.json")
    parser.add_argument("--warmup-steps", type=int, default=16)
    parser.add_argument("--measured-steps", type=int, default=48)
    parser.add_argument("--settings", nargs="+", default=("8/8", "12/12", "16/16"))
    parser.add_argument("--include-benchmark", action="append", default=[])
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    device = torch.device(
        "cuda" if args.device == "auto" and torch.cuda.is_available() else
        "cpu" if args.device == "auto" else args.device
    )
    if device.type != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("the required end-to-end benchmark needs the available local CUDA GPU")
    data_root = args.data_root.resolve()
    config_path = args.protocol_config.resolve()
    subset_path = args.subset_manifest.resolve()
    ranked_path = args.ranked_parents.resolve()
    simulation_path = args.simulation_config.resolve()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    subset = json.loads(subset_path.read_text(encoding="utf-8"))
    pair._preflight_data_bindings(data_root, subset)

    simulation = json.loads(simulation_path.read_text(encoding="utf-8"))
    validation_cache_started = time.perf_counter()
    panel_index, validation_panels, validation_labels = pair._ensure_eval_cache(
        data_root=data_root,
        cache_root=output_root / "evaluation_cache",
        split_rows=pair.load_split_rows(data_root),
        simulation=simulation,
        eval_seeds=[int(config["evaluation"]["validation_evaluation_seed"])],
        profiles=pair.PROFILES[:7],
        split="validation",
        input_length=int(config["model"]["input_length"]),
    )
    if len(panel_index.get("entries", {})) != len(pair.PROFILES[:7]):
        raise RuntimeError("validation benchmark cache did not contain the seven frozen profiles")
    validation_cache_seconds = time.perf_counter() - validation_cache_started

    results = []
    for setting in args.settings:
        workers, prefetch = (int(value) for value in setting.split("/", maxsplit=1))
        result = _benchmark_setting(
            data_root=data_root,
            output_root=output_root,
            base_config=config,
            subset_manifest=subset_path,
            ranked_parents=ranked_path,
            simulation_path=simulation_path,
            validation_panels=validation_panels,
            validation_labels=validation_labels,
            device=device,
            workers=workers,
            prefetch_batches=prefetch,
            warmup_steps=args.warmup_steps,
            measured_steps=args.measured_steps,
        )
        results.append(result)
        print(json.dumps(result, indent=2, sort_keys=True), flush=True)

    prior_benchmarks = [
        json.loads(Path(path).resolve().read_text(encoding="utf-8"))
        for path in args.include_benchmark
    ]
    prior_results = [
        (str(Path(path).resolve()), item)
        for path, prior in zip(args.include_benchmark, prior_benchmarks, strict=True)
        for item in prior.get("settings", [])
    ]
    current_results = [
        (str(args.output_json.resolve()), item) for item in results
    ]
    all_results = prior_results + current_results
    aggregates: list[dict[str, Any]] = []
    for setting in results:
        matching = [
            item
            for _, item in all_results
            if int(item["workers"]) == int(setting["workers"])
            and int(item["prefetch_batches"]) == int(setting["prefetch_batches"])
        ]
        throughput = float(np.median([item["paired_optimizer_steps_per_second"] for item in matching]))
        validation_seconds = float(
            np.median([item["validation_pair_seconds_per_checkpoint"] for item in matching])
        )
        budget_steps = int(config["training"]["optimizer_steps_per_model"])
        checks = int(np.ceil(budget_steps / int(config["training"]["validation_interval_steps"])))
        estimates = {}
        for method_runs in (8, 24, 40):
            paired_cells = method_runs // 2
            training_seconds = paired_cells * budget_steps / throughput
            validation_total_seconds = paired_cells * checks * validation_seconds
            estimates[str(method_runs)] = {
                "method_runs": method_runs,
                "paired_cells": paired_cells,
                "training_hours": training_seconds / 3600,
                "validation_hours": validation_total_seconds / 3600,
                "training_plus_validation_hours": (
                    training_seconds + validation_total_seconds
                )
                / 3600,
                "validation_checks_per_cell": checks,
            }
        aggregates.append(
            {
                **setting,
                "paired_optimizer_steps_per_second": throughput,
                "parent_occurrences_per_second": throughput
                * int(config["training"]["batch_size_parents"]),
                "generated_views_per_second": throughput
                * int(config["training"]["batch_size_parents"])
                * 2,
                "validation_pair_seconds_per_checkpoint": validation_seconds,
                "peak_cuda_allocated_bytes": max(
                    int(item["peak_cuda_allocated_bytes"] or 0) for item in matching
                ),
                "replicate_count": len(matching),
                "replicate_measurements": [
                    {
                        "source": path,
                        "paired_optimizer_steps_per_second": item[
                            "paired_optimizer_steps_per_second"
                        ],
                        "validation_pair_seconds_per_checkpoint": item[
                            "validation_pair_seconds_per_checkpoint"
                        ],
                    }
                    for path, item in all_results
                    if int(item["workers"]) == int(setting["workers"])
                    and int(item["prefetch_batches"]) == int(setting["prefetch_batches"])
                ],
                "time_estimates": estimates,
            }
        )
    report = {
        "schema_version": "parent-budget-gpu-benchmark-v1",
        "scope": "short_end_to_end_online_physics_h2d_and_paired_backward_benchmark",
        "not_scientific_result": True,
        "gpu": {
            "torch_name": torch.cuda.get_device_name(device),
            "torch_memory_bytes": int(torch.cuda.get_device_properties(device).total_memory),
            "nvidia_smi": _nvidia_smi(),
        },
        "protocol_config_sha256": pair.sha256_file(config_path),
        "subset_manifest_sha256": pair.sha256_file(subset_path),
        "simulation_config_sha256": pair.sha256_file(simulation_path),
        "step_budget_per_cell": int(config["training"]["optimizer_steps_per_model"]),
        "validation_interval_steps": int(config["training"]["validation_interval_steps"]),
        "validation_panel_cache_seconds": validation_cache_seconds,
        "validation_panel_cache_path": str(output_root / "evaluation_cache"),
        "historical_eight_hour_comparison": {
            "source": "user recollection; not verified local wall-time provenance",
            "note": "8/24/40 are individual method-run counts; each paired cell runs ERM and JS together, so the estimate uses 4/12/20 paired cells and excludes one-time panel-cache construction and artifact transfer",
        },
        "settings": aggregates,
        "benchmark_run_count": len(prior_benchmarks) + 1,
        "benchmark_run_sources": [str(Path(path).resolve()) for path in args.include_benchmark]
        + [str(args.output_json.resolve())],
    }
    args.output_json.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.output_json.resolve().write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
