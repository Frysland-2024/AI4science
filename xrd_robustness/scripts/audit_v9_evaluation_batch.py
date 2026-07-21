#!/usr/bin/env python3
"""Measure registered evaluation batch candidates with synthetic B3 forward passes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any

import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.method_transfer import load_contract  # noqa: E402
from xrd_robustness.models import PAMPT, PAMPTConfig  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        default=str(PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"),
    )
    parser.add_argument("--warmup-iterations", type=int, default=2)
    parser.add_argument("--benchmark-iterations", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260719)
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "reports" / "desktop_acceptance" / "evaluation_batch.json"),
    )
    return parser.parse_args()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    args = parse_args()
    contract_path = Path(args.contract).resolve()
    contract = load_contract(contract_path)
    profile_path = PROJECT_ROOT / str(contract["hardware_profile"]["path"])
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    candidates = [
        int(value)
        for value in profile["desktop_measurement_gate"]["evaluation_batch_candidates"]
    ]
    target_gpu = profile["target"]["gpu"]
    report: dict[str, Any] = {
        "schema_version": "v9-desktop-evaluation-batch-audit-v1",
        "purpose": "synthetic B3 evaluation forward sizing; no dataset, optimizer, checkpoint, or test evaluation",
        "contract": {"path": contract_path.relative_to(PROJECT_ROOT).as_posix(), "sha256": _sha256(contract_path)},
        "implementation_sha256": _sha256(Path(__file__).resolve()),
        "configuration": {
            "candidates": candidates,
            "warmup_iterations": args.warmup_iterations,
            "benchmark_iterations": args.benchmark_iterations,
            "no_dataset_access": True,
            "no_optimizer_step": True,
            "no_checkpoint": True,
        },
    }
    if not torch.cuda.is_available():
        report.update({"status": "fail", "failure_reason": "CUDA unavailable"})
    else:
        device = torch.device("cuda:0")
        observed_gpu = torch.cuda.get_device_name(device)
        model_config = PAMPTConfig(variant=str(contract["model"]["variant"]))
        torch.manual_seed(args.seed)
        torch.set_float32_matmul_precision("high")
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        model = PAMPT(model_config).to(device).eval()
        generator = torch.Generator(device="cpu").manual_seed(args.seed + 1)
        maximum_batch = max(candidates)
        first = torch.rand(maximum_batch, model_config.input_length, generator=generator).to(device)
        second = torch.rand(maximum_batch, model_config.input_length, generator=generator).to(device)
        results: dict[str, Any] = {}
        reference_logits: torch.Tensor | None = None
        for batch_size in candidates:
            try:
                def forward() -> torch.Tensor:
                    with torch.no_grad():
                        return 0.5 * (
                            model(first[:batch_size])["logits"]
                            + model(second[:batch_size])["logits"]
                        )

                for _ in range(args.warmup_iterations):
                    logits = forward()
                torch.cuda.synchronize(device)
                torch.cuda.reset_peak_memory_stats(device)
                started = time.perf_counter()
                for _ in range(args.benchmark_iterations):
                    logits = forward()
                torch.cuda.synchronize(device)
                elapsed = time.perf_counter() - started
                comparison = logits[: min(candidates)].detach().float().cpu()
                if reference_logits is None:
                    reference_logits = comparison
                numerical_match = bool(
                    torch.allclose(reference_logits, comparison, atol=1e-5, rtol=1e-4)
                )
                results[str(batch_size)] = {
                    "status": "pass" if numerical_match else "fail",
                    "numerical_match_on_shared_prefix": numerical_match,
                    "spectra_per_second": (
                        args.benchmark_iterations * batch_size * 2 / max(elapsed, 1e-12)
                    ),
                    "elapsed_seconds": elapsed,
                    "peak_allocated_bytes": int(torch.cuda.max_memory_allocated(device)),
                    "peak_reserved_bytes": int(torch.cuda.max_memory_reserved(device)),
                }
            except torch.cuda.OutOfMemoryError as error:
                results[str(batch_size)] = {"status": "oom", "error": str(error)}
                torch.cuda.empty_cache()
        passing = {
            int(key): value
            for key, value in results.items()
            if value.get("status") == "pass"
        }
        fastest = max(
            passing,
            key=lambda key: passing[key]["spectra_per_second"],
            default=None,
        )
        registered = int(profile["applied"]["evaluation_batch_size"])
        status = "pass" if (
            observed_gpu == target_gpu
            and registered in passing
            and all(value.get("status") == "pass" for value in results.values())
        ) else "fail"
        report.update(
            {
                "status": status,
                "runtime": {"gpu_name": observed_gpu, "target_gpu_match": observed_gpu == target_gpu},
                "results": results,
                "selection": {
                    "registered_default": registered,
                    "fastest_passing": fastest,
                    "recommended": fastest or registered,
                    "automatic_contract_change": False,
                },
            }
        )
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(output)}))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
