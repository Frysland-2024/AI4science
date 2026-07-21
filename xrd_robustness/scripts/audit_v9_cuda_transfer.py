#!/usr/bin/env python3
"""Audit pinned-memory and non-blocking CPU-to-CUDA transfer without training."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import sys
import time

import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--megabytes", type=int, default=16)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "reports" / "v9_cuda_transfer_audit.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.megabytes <= 0 or args.iterations <= 0:
        raise SystemExit("--megabytes and --iterations must be positive")

    report: dict[str, object] = {
        "schema_version": "v9-cuda-transfer-audit-v1",
        "purpose": "pinned-memory and non-blocking H2D smoke audit; no training",
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "cuda_available": bool(torch.cuda.is_available()),
        },
        "configuration": {
            "payload_megabytes": args.megabytes,
            "iterations": args.iterations,
            "pin_memory": True,
            "non_blocking_h2d": True,
        },
    }

    exit_code = 1
    if not torch.cuda.is_available():
        report.update(
            {
                "status": "fail",
                "failure_reason": "CUDA is unavailable in the selected interpreter",
            }
        )
    else:
        device = torch.device("cuda:0")
        properties = torch.cuda.get_device_properties(device)
        element_count = args.megabytes * 1024 * 1024 // torch.tensor([], dtype=torch.float32).element_size()
        source = torch.arange(element_count, dtype=torch.float32).pin_memory()
        destination = torch.empty_like(source, device=device)

        destination.copy_(source, non_blocking=True)
        torch.cuda.synchronize(device)
        started = time.perf_counter()
        for _ in range(args.iterations):
            destination.copy_(source, non_blocking=True)
        torch.cuda.synchronize(device)
        elapsed_seconds = time.perf_counter() - started

        observed = destination.cpu()
        exact_match = bool(torch.equal(source, observed))
        source_is_pinned = bool(source.is_pinned())
        transferred_bytes = source.numel() * source.element_size() * args.iterations
        gib_per_second = transferred_bytes / max(elapsed_seconds, 1e-12) / (1024**3)
        passed = source_is_pinned and exact_match
        report.update(
            {
                "status": "pass" if passed else "fail",
                "device": {
                    "name": properties.name,
                    "compute_capability": f"{properties.major}.{properties.minor}",
                    "total_memory_bytes": properties.total_memory,
                },
                "checks": {
                    "source_is_pinned": source_is_pinned,
                    "exact_round_trip_match": exact_match,
                    "non_blocking_copy_completed_after_synchronize": True,
                },
                "measurement": {
                    "elapsed_seconds": elapsed_seconds,
                    "transferred_bytes": transferred_bytes,
                    "effective_gib_per_second": gib_per_second,
                    "interpretation": "smoke measurement only; rerun on the target desktop",
                },
            }
        )
        exit_code = 0 if passed else 1

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    print(f"report={output_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
