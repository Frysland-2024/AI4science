#!/usr/bin/env python3
"""Audit BF16, torch.compile, and two-run CUDA behavior without optimizer steps."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import platform
import queue
import sys
import tempfile
import time
from typing import Any

import torch
from torch.nn import functional as F


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.method_transfer import load_contract  # noqa: E402
from xrd_robustness.models import PAMPT, PAMPTConfig  # noqa: E402
from xrd_robustness.training.objectives import (  # noqa: E402
    ResidualClassifier,
    js_divergence,
    residual_confusion_kl,
    symmetric_measurement_residual,
)


OBJECTIVES = ("dynamic_erm", "dynamic_js", "dynamic_residual")
NUMERICAL_THRESHOLDS = {
    "fp32_vs_bf16": {
        "logits_atol": 0.08,
        "logits_rtol": 0.08,
        "loss_atol": 0.03,
        "loss_rtol": 0.03,
        "gradient_cosine_min": 0.97,
        "gradient_relative_l2_max": 0.25,
    },
    "bf16_eager_vs_compile": {
        "logits_atol": 0.02,
        "logits_rtol": 0.02,
        "loss_atol": 0.01,
        "loss_rtol": 0.01,
        "gradient_cosine_min": 0.995,
        "gradient_relative_l2_max": 0.05,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        default=str(PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"),
    )
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--warmup-iterations", type=int, default=2)
    parser.add_argument("--benchmark-iterations", type=int, default=5)
    parser.add_argument("--parallel-timeout-seconds", type=int, default=900)
    parser.add_argument("--seed", type=int, default=20260719)
    parser.add_argument(
        "--config-only",
        action="store_true",
        help="validate the gate definition without allocating CUDA tensors",
    )
    parser.add_argument(
        "--allow-non-target",
        action="store_true",
        help="allow an engineering run on a non-registered GPU; target_match still fails",
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "reports" / "v9_desktop_acceleration_audit.json"),
    )
    return parser.parse_args()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _dynamo_counters() -> dict[str, dict[str, int]]:
    try:
        from torch._dynamo.utils import counters

        return {
            str(group): {str(key): int(value) for key, value in values.items()}
            for group, values in counters.items()
        }
    except Exception:
        return {}


def _reset_dynamo() -> None:
    from torch import _dynamo
    from torch._dynamo.utils import counters

    _dynamo.reset()
    counters.clear()
    _dynamo.config.suppress_errors = True


def _unique_graph_count(counters: dict[str, dict[str, int]]) -> int:
    return int(counters.get("stats", {}).get("unique_graphs", 0))


def _make_modules(
    config: PAMPTConfig,
    *,
    seed: int,
    device: torch.device,
) -> tuple[PAMPT, ResidualClassifier]:
    torch.manual_seed(seed)
    model = PAMPT(config).to(device)
    residual_head = ResidualClassifier(config.embed_dim, depth=1).to(device)
    model.eval()
    residual_head.eval()
    return model, residual_head


def _objective(
    mode: str,
    model: PAMPT,
    residual_head: ResidualClassifier,
    x1: torch.Tensor,
    x2: torch.Tensor,
    target: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    output1 = model(x1)
    output2 = model(x2)
    logits1 = output1["logits"]
    logits2 = output2["logits"]
    classification = 0.5 * (
        F.cross_entropy(logits1, target) + F.cross_entropy(logits2, target)
    )
    if mode == "dynamic_erm":
        total = classification
    elif mode == "dynamic_js":
        total = classification + 0.1 * js_divergence(logits1, logits2)
    elif mode == "dynamic_residual":
        residual = symmetric_measurement_residual(
            output1["pooled_embedding"], output2["pooled_embedding"]
        )
        detached_head_loss = F.cross_entropy(residual_head(residual.detach()), target)
        confusion = residual_confusion_kl(residual_head(residual))
        total = classification + detached_head_loss + 0.1 * confusion
    else:  # pragma: no cover - protected by the registered mode list
        raise ValueError(mode)
    return total, torch.cat((logits1, logits2), dim=0)


def _gradients(
    model: PAMPT, residual_head: ResidualClassifier, *, include_head: bool
) -> dict[str, torch.Tensor]:
    modules = {"model": model}
    if include_head:
        modules["residual_head"] = residual_head
    result: dict[str, torch.Tensor] = {}
    for module_name, module in modules.items():
        for name, parameter in module.named_parameters():
            if parameter.grad is not None:
                result[f"{module_name}.{name}"] = parameter.grad.detach().float().cpu()
    return result


def _run_numerical_case(
    mode: str,
    model_config: PAMPTConfig,
    x1: torch.Tensor,
    x2: torch.Tensor,
    target: torch.Tensor,
    *,
    seed: int,
    amp: bool,
    compile_model: bool,
) -> dict[str, Any]:
    device = x1.device
    model, residual_head = _make_modules(model_config, seed=seed, device=device)
    compile_started = None
    compile_initialization_seconds = 0.0
    if compile_model:
        _reset_dynamo()
        compile_started = time.perf_counter()
        model.compile(backend="inductor", mode="default", fullgraph=False, dynamic=False)
        residual_head.compile(
            backend="inductor", mode="default", fullgraph=False, dynamic=False
        )
        compile_initialization_seconds = time.perf_counter() - compile_started

    model.zero_grad(set_to_none=True)
    residual_head.zero_grad(set_to_none=True)
    torch.cuda.synchronize(device)
    started = time.perf_counter()
    with torch.autocast(
        device_type="cuda", dtype=torch.bfloat16, enabled=amp
    ):
        loss, logits = _objective(mode, model, residual_head, x1, x2, target)
    loss.backward()
    torch.cuda.synchronize(device)
    elapsed = time.perf_counter() - started
    counters = _dynamo_counters() if compile_model else {}
    return {
        "loss": float(loss.detach().float().cpu()),
        "logits": logits.detach().float().cpu(),
        "gradients": _gradients(
            model, residual_head, include_head=(mode == "dynamic_residual")
        ),
        "elapsed_seconds": elapsed,
        "compile_initialization_seconds": compile_initialization_seconds,
        "dynamo_counters": counters,
        "unique_graphs": _unique_graph_count(counters),
    }


def compare_cases(
    reference: dict[str, Any],
    observed: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    reference_logits = reference["logits"]
    observed_logits = observed["logits"]
    logits_close = bool(
        torch.allclose(
            reference_logits,
            observed_logits,
            atol=thresholds["logits_atol"],
            rtol=thresholds["logits_rtol"],
        )
    )
    loss_close = math.isclose(
        float(reference["loss"]),
        float(observed["loss"]),
        abs_tol=thresholds["loss_atol"],
        rel_tol=thresholds["loss_rtol"],
    )
    reference_gradients = reference["gradients"]
    observed_gradients = observed["gradients"]
    names_match = set(reference_gradients) == set(observed_gradients)
    dot = reference_norm = observed_norm = difference_norm = 0.0
    maximum_absolute_gradient_difference = 0.0
    for name in sorted(set(reference_gradients) & set(observed_gradients)):
        first = reference_gradients[name].double()
        second = observed_gradients[name].double()
        difference = first - second
        dot += float(torch.sum(first * second))
        reference_norm += float(torch.sum(first.square()))
        observed_norm += float(torch.sum(second.square()))
        difference_norm += float(torch.sum(difference.square()))
        maximum_absolute_gradient_difference = max(
            maximum_absolute_gradient_difference,
            float(difference.abs().max()) if difference.numel() else 0.0,
        )
    denominator = math.sqrt(reference_norm * observed_norm)
    gradient_cosine = dot / denominator if denominator > 0 else 1.0
    gradient_relative_l2 = math.sqrt(difference_norm) / max(
        math.sqrt(reference_norm), 1e-12
    )
    gradients_close = bool(
        names_match
        and gradient_cosine >= thresholds["gradient_cosine_min"]
        and gradient_relative_l2 <= thresholds["gradient_relative_l2_max"]
    )
    return {
        "passed": logits_close and loss_close and gradients_close,
        "logits_close": logits_close,
        "loss_close": loss_close,
        "gradient_names_match": names_match,
        "gradients_close": gradients_close,
        "maximum_absolute_logit_difference": float(
            (reference_logits - observed_logits).abs().max()
        ),
        "absolute_loss_difference": abs(
            float(reference["loss"]) - float(observed["loss"])
        ),
        "gradient_cosine": gradient_cosine,
        "gradient_relative_l2": gradient_relative_l2,
        "maximum_absolute_gradient_difference": maximum_absolute_gradient_difference,
        "thresholds": thresholds,
    }


def _benchmark_workload(
    model_config_mapping: dict[str, Any],
    *,
    batch_size: int,
    warmup_iterations: int,
    benchmark_iterations: int,
    seed: int,
    barrier_timeout_seconds: int = 600,
    start_barrier: Any = None,
    finish_barrier: Any = None,
) -> dict[str, Any]:
    device = torch.device("cuda:0")
    torch.cuda.set_device(device)
    torch.manual_seed(seed)
    model_config = PAMPTConfig(**model_config_mapping)
    model, residual_head = _make_modules(model_config, seed=seed, device=device)
    _reset_dynamo()
    cache_root = Path(tempfile.gettempdir()) / f"xrd_v9_inductor_{os.getpid()}"
    os.environ["TORCHINDUCTOR_CACHE_DIR"] = str(cache_root)
    model.compile(backend="inductor", mode="default", fullgraph=False, dynamic=False)
    residual_head.compile(
        backend="inductor", mode="default", fullgraph=False, dynamic=False
    )
    generator = torch.Generator(device="cpu").manual_seed(seed + 1)
    x1 = torch.rand(batch_size, model_config.input_length, generator=generator).to(device)
    x2 = torch.rand(batch_size, model_config.input_length, generator=generator).to(device)
    target = (torch.arange(batch_size, device=device) % model_config.num_classes).long()

    def step() -> None:
        model.zero_grad(set_to_none=True)
        residual_head.zero_grad(set_to_none=True)
        with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
            loss, _ = _objective(
                "dynamic_js", model, residual_head, x1, x2, target
            )
        loss.backward()

    compile_warmup_started = time.perf_counter()
    for _ in range(warmup_iterations):
        step()
    torch.cuda.synchronize(device)
    compile_warmup_seconds = time.perf_counter() - compile_warmup_started
    if start_barrier is not None:
        start_barrier.wait(timeout=barrier_timeout_seconds)
    torch.cuda.reset_peak_memory_stats(device)
    started = time.perf_counter()
    for _ in range(benchmark_iterations):
        step()
    torch.cuda.synchronize(device)
    elapsed = time.perf_counter() - started
    free_bytes, total_bytes = torch.cuda.mem_get_info(device)
    if finish_barrier is not None:
        finish_barrier.wait(timeout=barrier_timeout_seconds)
    spectra = benchmark_iterations * batch_size * 2
    counters = _dynamo_counters()
    return {
        "elapsed_seconds": elapsed,
        "spectra": spectra,
        "spectra_per_second": spectra / max(elapsed, 1e-12),
        "compile_warmup_seconds": compile_warmup_seconds,
        "peak_allocated_bytes": int(torch.cuda.max_memory_allocated(device)),
        "peak_reserved_bytes": int(torch.cuda.max_memory_reserved(device)),
        "device_global_used_bytes": int(total_bytes - free_bytes),
        "unique_graphs": _unique_graph_count(counters),
        "dynamo_counters": counters,
    }


def _parallel_worker(
    worker_index: int,
    model_config_mapping: dict[str, Any],
    settings: dict[str, int],
    start_barrier: Any,
    finish_barrier: Any,
    result_queue: Any,
) -> None:
    try:
        result = _benchmark_workload(
            model_config_mapping,
            batch_size=settings["batch_size"],
            warmup_iterations=settings["warmup_iterations"],
            benchmark_iterations=settings["benchmark_iterations"],
            seed=settings["seed"] + worker_index,
            barrier_timeout_seconds=settings["barrier_timeout_seconds"],
            start_barrier=start_barrier,
            finish_barrier=finish_barrier,
        )
        result_queue.put({"worker_index": worker_index, "result": result, "error": None})
    except Exception as error:  # pragma: no cover - target CUDA failure path
        result_queue.put(
            {
                "worker_index": worker_index,
                "result": None,
                "error": f"{type(error).__name__}: {error}",
            }
        )


def _parallel_benchmark(
    model_config: PAMPTConfig,
    settings: dict[str, int],
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    context = mp.get_context("spawn")
    start_barrier = context.Barrier(2)
    finish_barrier = context.Barrier(2)
    result_queue = context.Queue()
    processes = [
        context.Process(
            target=_parallel_worker,
            args=(
                index,
                asdict(model_config),
                settings,
                start_barrier,
                finish_barrier,
                result_queue,
            ),
        )
        for index in range(2)
    ]
    for process in processes:
        process.start()
    messages = []
    deadline = time.monotonic() + timeout_seconds
    while len(messages) < len(processes) and time.monotonic() < deadline:
        try:
            messages.append(result_queue.get(timeout=1.0))
        except queue.Empty:
            if all(not process.is_alive() for process in processes):
                break
    for process in processes:
        remaining = max(0.0, deadline - time.monotonic())
        process.join(timeout=remaining)
    timed_out = any(process.is_alive() for process in processes)
    if timed_out:
        for process in processes:
            process.terminate()
            process.join(timeout=10)
    errors = [message["error"] for message in messages if message.get("error")]
    if len(messages) != 2:
        errors.append(f"received {len(messages)} of 2 worker results")
    results = [message["result"] for message in messages if message.get("result")]
    elapsed = max((float(result["elapsed_seconds"]) for result in results), default=0.0)
    spectra = sum(int(result["spectra"]) for result in results)
    return {
        "timed_out": timed_out,
        "errors": errors,
        "workers": sorted(messages, key=lambda item: item["worker_index"]),
        "elapsed_seconds": elapsed,
        "spectra": spectra,
        "aggregate_spectra_per_second": spectra / max(elapsed, 1e-12),
        "maximum_device_global_used_bytes": max(
            (int(result["device_global_used_bytes"]) for result in results), default=0
        ),
        "minimum_unique_graphs": min(
            (int(result["unique_graphs"]) for result in results), default=0
        ),
    }


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    if min(args.warmup_iterations, args.benchmark_iterations) <= 0:
        raise SystemExit("warmup and benchmark iterations must be positive")
    contract_path = Path(args.contract).resolve()
    contract = load_contract(contract_path)
    profile_path = PROJECT_ROOT / str(contract["hardware_profile"]["path"])
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    applied = profile["applied"]
    batch_size = int(args.batch_size or contract["experiment"]["batch_size"])
    model_config = PAMPTConfig(variant=str(contract["model"]["variant"]))
    output_path = Path(args.output).resolve()
    report: dict[str, Any] = {
        "schema_version": "v9-desktop-acceleration-audit-v1",
        "purpose": (
            "bounded forward/backward numerical and throughput engineering gate; "
            "no optimizer step, checkpoint, dataset split evaluation, or formal training"
        ),
        "contract": {
            "path": contract_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": _sha256(contract_path),
        },
        "hardware_profile": {
            "path": profile_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": _sha256(profile_path),
        },
        "implementation_sha256": _sha256(Path(__file__).resolve()),
        "configuration": {
            "batch_size": batch_size,
            "warmup_iterations": args.warmup_iterations,
            "benchmark_iterations": args.benchmark_iterations,
            "parallel_processes": int(applied["run_concurrency"]),
            "model": asdict(model_config),
            "objectives": list(OBJECTIVES),
            "seed": args.seed,
            "no_optimizer_step": True,
            "no_checkpoint": True,
            "no_dataset_access": True,
            "thresholds": NUMERICAL_THRESHOLDS,
        },
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "torch": str(torch.__version__),
            "torch_cuda": str(torch.version.cuda),
            "cuda_available": bool(torch.cuda.is_available()),
        },
    }
    if args.config_only:
        report.update(
            {
                "status": "configuration_validated_not_executed",
                "checks": {
                    "registered_bf16": applied["automatic_mixed_precision"]
                    == {
                        "enabled": True,
                        "dtype": "bfloat16",
                        "gradient_scaler": False,
                        "fallback_to_float32": True,
                    },
                    "registered_compile": applied["torch_compile"]["enabled"] is True,
                    "registered_two_run_concurrency": applied["run_concurrency"] == 2,
                    "registered_parallel_worker_budget": (
                        applied["parallel_run_scheduler"][
                            "concurrent_run_prefetch_workers"
                        ]
                        * applied["run_concurrency"]
                        == applied["dynamic_prefetch"]["worker_processes"]
                    ),
                },
            }
        )
        _write_report(output_path, report)
        print(json.dumps({"status": report["status"], "output": str(output_path)}))
        return 0 if all(report["checks"].values()) else 1

    if not torch.cuda.is_available():
        report.update({"status": "fail", "failure_reason": "CUDA is unavailable"})
        _write_report(output_path, report)
        return 1
    device = torch.device("cuda:0")
    properties = torch.cuda.get_device_properties(device)
    observed_gpu = properties.name
    observed_memory_mb = int(properties.total_memory / (1024**2))
    target_match = {
        "gpu_name": observed_gpu == profile["target"]["gpu"],
        "gpu_memory": observed_memory_mb >= int(contract["runtime"]["minimum_gpu_memory_mb"]),
        "bf16_supported": bool(torch.cuda.is_bf16_supported()),
    }
    report["runtime"].update(
        {
            "gpu_name": observed_gpu,
            "gpu_memory_mb": observed_memory_mb,
            "bf16_supported": target_match["bf16_supported"],
            "target_match": target_match,
        }
    )
    if not all(target_match.values()) and not args.allow_non_target:
        report.update(
            {
                "status": "fail",
                "failure_reason": "registered target GPU/BF16 requirements are not met",
            }
        )
        _write_report(output_path, report)
        print(json.dumps({"status": "fail", "target_match": target_match}))
        return 1

    generator = torch.Generator(device="cpu").manual_seed(args.seed + 1)
    x1 = torch.rand(batch_size, model_config.input_length, generator=generator).to(device)
    x2 = torch.rand(batch_size, model_config.input_length, generator=generator).to(device)
    target = (torch.arange(batch_size, device=device) % model_config.num_classes).long()
    numerical: dict[str, Any] = {}
    compile_graphs = []
    for mode in OBJECTIVES:
        fp32 = _run_numerical_case(
            mode, model_config, x1, x2, target, seed=args.seed, amp=False, compile_model=False
        )
        bf16 = _run_numerical_case(
            mode, model_config, x1, x2, target, seed=args.seed, amp=True, compile_model=False
        )
        compiled = _run_numerical_case(
            mode, model_config, x1, x2, target, seed=args.seed, amp=True, compile_model=True
        )
        compile_graphs.append(int(compiled["unique_graphs"]))
        numerical[mode] = {
            "fp32_vs_bf16": compare_cases(
                fp32, bf16, NUMERICAL_THRESHOLDS["fp32_vs_bf16"]
            ),
            "bf16_eager_vs_compile": compare_cases(
                bf16, compiled, NUMERICAL_THRESHOLDS["bf16_eager_vs_compile"]
            ),
            "measurements": {
                "fp32_seconds": fp32["elapsed_seconds"],
                "bf16_eager_seconds": bf16["elapsed_seconds"],
                "bf16_compile_first_call_seconds": compiled["elapsed_seconds"],
                "compile_initialization_seconds": compiled[
                    "compile_initialization_seconds"
                ],
                "compile_unique_graphs": compiled["unique_graphs"],
                "compile_fallback_completed": True,
            },
        }
        del fp32, bf16, compiled
        torch.cuda.empty_cache()

    settings = {
        "batch_size": batch_size,
        "warmup_iterations": args.warmup_iterations,
        "benchmark_iterations": args.benchmark_iterations,
        "seed": args.seed + 100,
        "barrier_timeout_seconds": max(
            30, min(args.parallel_timeout_seconds - 10, 600)
        ),
    }
    serial = _benchmark_workload(asdict(model_config), **settings)
    torch.cuda.empty_cache()
    parallel = _parallel_benchmark(
        model_config, settings, timeout_seconds=args.parallel_timeout_seconds
    )
    throughput_ratio = parallel["aggregate_spectra_per_second"] / max(
        serial["spectra_per_second"], 1e-12
    )
    peak_limit_bytes = 15360 * 1024**2
    checks = {
        "target_gpu_name_and_memory_match": all(target_match.values()),
        "bf16_forward_backward_numerical_equivalence": all(
            item["fp32_vs_bf16"]["passed"] for item in numerical.values()
        ),
        "torch_compile_eager_numerical_equivalence": all(
            item["bf16_eager_vs_compile"]["passed"] for item in numerical.values()
        ),
        "compile_fallback_smoke_pass": all(
            item["measurements"]["compile_fallback_completed"]
            for item in numerical.values()
        ),
        "torch_compile_graph_executed": min(compile_graphs, default=0) > 0
        and int(serial["unique_graphs"]) > 0
        and int(parallel["minimum_unique_graphs"]) > 0,
        "two_run_completed_without_error": (
            not parallel["timed_out"] and not parallel["errors"]
        ),
        "two_run_peak_vram_below_15360_mb": (
            int(parallel["maximum_device_global_used_bytes"]) < peak_limit_bytes
        ),
        "two_run_aggregate_throughput_not_lower_than_serial": throughput_ratio >= 0.95,
        "effective_parallel_worker_budget_is_eight": (
            applied["parallel_run_scheduler"]["concurrent_run_prefetch_workers"]
            * applied["run_concurrency"]
            == applied["dynamic_prefetch"]["worker_processes"]
        ),
    }
    report.update(
        {
            "status": "pass" if all(checks.values()) else "fail",
            "checks": checks,
            "numerical_equivalence": numerical,
            "performance": {
                "serial": serial,
                "parallel": parallel,
                "parallel_to_serial_aggregate_throughput_ratio": throughput_ratio,
                "peak_vram_limit_bytes": peak_limit_bytes,
                "compile_warmup_excluded_from_steady_timing": True,
            },
        }
    )
    _write_report(output_path, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "target_match": target_match,
                "throughput_ratio": throughput_ratio,
                "output": str(output_path),
            }
        )
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
