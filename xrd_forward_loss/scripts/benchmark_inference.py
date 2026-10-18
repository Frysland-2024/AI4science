"""Measure architecture-level inference throughput on the recorded GPU."""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import torch

from pxrd_forward_loss.data import build_dataset, read_json
from pxrd_forward_loss.model import ParameterRegressor, compose_full_q


def main():
    root = Path(__file__).resolve().parents[2]
    config = read_json(root / "xrd_forward_loss/configs/pilot.json")
    if not torch.cuda.is_available():
        raise RuntimeError("inference benchmark requires CUDA")
    device = torch.device("cuda")
    arrays, _, _, forward, _ = build_dataset(root, config)
    model = ParameterRegressor().to(device).eval()
    inputs = torch.as_tensor(arrays["noisy"][arrays["test_indices"]], dtype=torch.float32, device=device)
    repeats = 25
    batch_size = 32

    def nn_pass():
        return torch.cat([model(inputs[i : i + batch_size]) for i in range(0, len(inputs), batch_size)])

    @torch.no_grad()
    def full_pass():
        q = nn_pass()
        profiles = []
        for i in range(0, len(q), 16):
            profiles.append(forward.transformed(compose_full_q(q[i : i + 16].to(torch.float64))))
        return q, torch.cat(profiles)

    with torch.no_grad():
        for _ in range(4):
            nn_pass()
            full_pass()
        torch.cuda.synchronize()
        start = time.perf_counter()
        for _ in range(repeats):
            nn_pass()
        torch.cuda.synchronize()
        nn_seconds = (time.perf_counter() - start) / repeats
        start = time.perf_counter()
        for _ in range(repeats):
            full_pass()
        torch.cuda.synchronize()
        full_seconds = (time.perf_counter() - start) / repeats
    output = {
        "status": "ARCHITECTURE_THROUGHPUT_BENCHMARK",
        "checkpoint": "random initialization; this is a shape-matched throughput benchmark, not final trained-model quality or checkpoint timing",
        "device": torch.cuda.get_device_name(device),
        "test_shape": [int(len(inputs)), int(inputs.shape[-1])],
        "batch_size": batch_size,
        "repeats": repeats,
        "nn_seconds_per_77_profiles": nn_seconds,
        "nn_milliseconds_per_profile": 1000.0 * nn_seconds / len(inputs),
        "nn_plus_forward_seconds_per_77_profiles": full_seconds,
        "nn_plus_forward_milliseconds_per_profile": 1000.0 * full_seconds / len(inputs),
        "peak_memory_allocated_mb": float(torch.cuda.max_memory_allocated(device) / (1024**2)),
    }
    output_path = root / "xrd_forward_loss/reports/pilot_20261018/inference_benchmark.json"
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
