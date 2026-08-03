#!/usr/bin/env python3
"""Benchmark the simulated-Test runner without reading any Test structure."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from typing import Any

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xrd_robustness.models.ml4pxrd_resnet1d import (  # noqa: E402
    ML4PXRDResNet1D,
    ML4PXRDResNet1DConfig,
)
from xrd_robustness.online_views import OnlineViewFactory  # noqa: E402
from xrd_robustness.peak_cache import load_peak_table  # noqa: E402
from xrd_robustness.physics import PhysicsParameterSampler  # noqa: E402
from xrd_robustness.view_manifest import build_offline_view_manifest  # noqa: E402


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(value: np.ndarray) -> str:
    return hashlib.sha256(value.tobytes()).hexdigest().upper()


def benchmark_rendering(sample_count: int) -> tuple[dict[str, Any], np.ndarray]:
    split = read_json(ROOT / "data/formal_14060/manifests/split_manifest.json")
    train_ids = sorted(
        str(row["material_id"]) for row in split["records"] if row["split"] == "train"
    )[:sample_count]
    if len(train_ids) != sample_count:
        raise RuntimeError("insufficient Train structures for benchmark")
    simulation = read_json(ROOT / "configs/simulation.v9.method_transfer.frozen.json")
    simulation["run_seed"] = 909091
    rows = list(
        build_offline_view_manifest(
            train_ids,
            PhysicsParameterSampler.from_mapping(simulation),
            profile="in_range",
            views_per_material=1,
            split="train",
        )
    )
    peaks = {
        material_id: load_peak_table(
            ROOT
            / "data/formal_14060/mp_processed/peak_tables_v7_reflection"
            / f"{material_id}.npz"
        )
        for material_id in train_ids
    }
    factory = OnlineViewFactory(
        PhysicsParameterSampler.from_mapping({**simulation, "run_seed": 0})
    )

    def render(row: Any) -> np.ndarray:
        return factory.make_view_from_manifest(peaks[row.material_id], row).xrd

    results: dict[str, Any] = {}
    reference: np.ndarray | None = None
    for workers in (1, 4, 8, 16):
        started = time.perf_counter()
        if workers == 1:
            values = [render(row) for row in rows]
        else:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                values = list(executor.map(render, rows))
        elapsed = time.perf_counter() - started
        matrix = np.stack(values)
        if reference is None:
            reference = matrix
        results[str(workers)] = {
            "seconds": elapsed,
            "spectra_per_second": sample_count / elapsed,
            "sha256": sha256_bytes(matrix),
            "bit_exact_to_serial": bool(np.array_equal(reference, matrix)),
        }
    fastest = max(results, key=lambda key: results[key]["spectra_per_second"])
    assert reference is not None
    return {
        "split": "train",
        "profile": "in_range",
        "sample_count": sample_count,
        "test_structure_accessed": False,
        "results": results,
        "fastest_worker_count": int(fastest),
    }, reference


def benchmark_gpu(
    iterations: int, utilization_seconds: float, train_spectra: np.ndarray
) -> dict[str, Any]:
    if not torch.cuda.is_available():
        return {"status": "fail", "reason": "CUDA unavailable"}
    device = torch.device("cuda:0")
    torch.manual_seed(909092)
    torch.backends.cudnn.benchmark = True
    torch.backends.cuda.matmul.allow_tf32 = True
    config = ML4PXRDResNet1DConfig()
    model = ML4PXRDResNet1D(config).to(device).eval()
    results: dict[str, Any] = {}
    for batch_size in (128, 256, 512, 768, 1024):
        try:
            host = torch.rand(
                (batch_size, config.input_length),
                dtype=torch.float32,
                pin_memory=True,
            )

            def forward() -> torch.Tensor:
                with torch.inference_mode(), torch.autocast(
                    device_type="cuda", dtype=torch.float16
                ):
                    logits = model(host.to(device, non_blocking=True))["logits"]
                    return torch.softmax(logits, dim=-1).float().cpu()

            for _ in range(3):
                sink = forward()
            torch.cuda.synchronize(device)
            torch.cuda.reset_peak_memory_stats(device)
            started = time.perf_counter()
            for _ in range(iterations):
                sink = forward()
            torch.cuda.synchronize(device)
            elapsed = time.perf_counter() - started
            results[str(batch_size)] = {
                "status": "pass",
                "seconds": elapsed,
                "spectra_per_second": iterations * batch_size / elapsed,
                "peak_allocated_mib": torch.cuda.max_memory_allocated(device) / 2**20,
                "peak_reserved_mib": torch.cuda.max_memory_reserved(device) / 2**20,
            }
            del host, sink
        except torch.cuda.OutOfMemoryError as error:
            results[str(batch_size)] = {"status": "oom", "error": str(error)}
            torch.cuda.empty_cache()
    passing = {
        int(key): value for key, value in results.items() if value["status"] == "pass"
    }
    fastest = max(passing, key=lambda key: passing[key]["spectra_per_second"])
    utilization_samples: list[int] = []
    stop_sampling = threading.Event()

    def sample_utilization() -> None:
        while not stop_sampling.is_set():
            completed = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            utilization_samples.append(int(completed.stdout.strip().splitlines()[0]))
            stop_sampling.wait(0.5)

    host = torch.rand(
        (fastest, config.input_length), dtype=torch.float32, pin_memory=True
    )
    for _ in range(3):
        with torch.inference_mode(), torch.autocast(
            device_type="cuda", dtype=torch.float16
        ):
            sink = model(host.to(device, non_blocking=True))["logits"].float().cpu()
    torch.cuda.synchronize(device)
    sampler = threading.Thread(target=sample_utilization, daemon=True)
    sampler.start()
    deadline = time.perf_counter() + utilization_seconds
    spectra_processed = 0
    while time.perf_counter() < deadline:
        with torch.inference_mode(), torch.autocast(
            device_type="cuda", dtype=torch.float16
        ):
            sink = model(host.to(device, non_blocking=True))["logits"].float().cpu()
        spectra_processed += fastest
    torch.cuda.synchronize(device)
    stop_sampling.set()
    sampler.join(timeout=2)
    equivalence_size = min(fastest, len(train_spectra))
    direct_input = np.asarray(train_spectra[:equivalence_size])
    pinned_input = torch.empty(direct_input.shape, dtype=torch.float32, pin_memory=True)
    pinned_input.numpy()[:] = direct_input
    with torch.inference_mode(), torch.autocast(
        device_type="cuda", dtype=torch.float16
    ):
        direct_probabilities = torch.softmax(
            model(torch.as_tensor(direct_input, device=device))["logits"], dim=-1
        ).float()
        pinned_probabilities = torch.softmax(
            model(pinned_input.to(device, non_blocking=True))["logits"], dim=-1
        ).float()
    direct_probabilities = direct_probabilities.cpu().numpy()
    pinned_probabilities = pinned_probabilities.cpu().numpy()
    maximum_difference = float(
        np.max(np.abs(direct_probabilities - pinned_probabilities))
    )
    inference_equivalence = {
        "split": "train",
        "sample_count": equivalence_size,
        "test_structure_accessed": False,
        "predicted_classes_identical": bool(
            np.array_equal(
                direct_probabilities.argmax(axis=1),
                pinned_probabilities.argmax(axis=1),
            )
        ),
        "maximum_probability_difference": maximum_difference,
        "allclose_at_1e_6": bool(
            np.allclose(
                direct_probabilities,
                pinned_probabilities,
                atol=1e-6,
                rtol=1e-6,
            )
        ),
    }
    return {
        "status": "pass",
        "gpu": torch.cuda.get_device_name(device),
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "synthetic_input_only": True,
        "test_structure_accessed": False,
        "results": results,
        "fastest_batch_size": fastest,
        "sustained_utilization": {
            "seconds": utilization_seconds,
            "samples_percent": utilization_samples,
            "mean_percent": float(np.mean(utilization_samples)),
            "minimum_percent": min(utilization_samples),
            "maximum_percent": max(utilization_samples),
            "spectra_processed": spectra_processed,
        },
        "old_vs_cached_input_equivalence": inference_equivalence,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-count", type=int, default=256)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--utilization-seconds", type=float, default=8.0)
    parser.add_argument(
        "--output",
        default=str(
            ROOT / "reports/v9_resnet_js_simulated_test_performance_audit_20260803.json"
        ),
    )
    args = parser.parse_args()
    rendering, train_spectra = benchmark_rendering(args.sample_count)
    gpu = benchmark_gpu(args.iterations, args.utilization_seconds, train_spectra)
    fastest_render = rendering["results"][str(rendering["fastest_worker_count"])]
    fastest_gpu = gpu["results"][str(gpu["fastest_batch_size"])]
    frozen_spectra = 3 * 12 * 2109
    checkpoint_inferences = frozen_spectra * 10
    report = {
        "schema_version": "v9-resnet-js-simulated-test-performance-audit-v1",
        "status": (
            "pass"
            if gpu["status"] == "pass"
            and gpu["old_vs_cached_input_equivalence"]["allclose_at_1e_6"]
            and gpu["old_vs_cached_input_equivalence"]["predicted_classes_identical"]
            and all(row["bit_exact_to_serial"] for row in rendering["results"].values())
            else "fail"
        ),
        "scope": "Train-only renderer and synthetic GPU throughput benchmark; no Test spectrum or metric used",
        "rendering": rendering,
        "gpu": gpu,
        "selection": {
            "renderer_workers": rendering["fastest_worker_count"],
            "evaluation_batch_size": gpu["fastest_batch_size"],
            "reason": "highest measured end-to-end throughput on this machine",
        },
        "estimated_work": {
            "unique_frozen_spectra": frozen_spectra,
            "original_redundant_render_count": checkpoint_inferences,
            "optimized_render_count": frozen_spectra,
            "checkpoint_inference_count": checkpoint_inferences,
            "optimized_render_seconds": frozen_spectra
            / fastest_render["spectra_per_second"],
            "optimized_gpu_seconds": checkpoint_inferences
            / fastest_gpu["spectra_per_second"],
        },
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": report["status"], "output": str(output)}))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
