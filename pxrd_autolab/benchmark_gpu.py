"""Benchmark actual CUDA matrix multiplication; this is not scientific training."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import platform
import statistics
import sys
import time
from pathlib import Path


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    expected = {"schema_version", "preset", "matrix_sizes", "warmup", "repeats",
                "dtype", "minimum_free_vram_bytes"}
    if not isinstance(config, dict) or set(config) != expected:
        raise ValueError("Config fields do not match the reviewed benchmark schema")
    if config["preset"] != "forward_speed_benchmark":
        raise ValueError("Incorrect benchmark preset")
    if config["dtype"] != "float32" or not config["matrix_sizes"]:
        raise ValueError("Only the reviewed float32 matrix benchmark is supported")
    return config


def benchmark_cuda(config: dict) -> dict:
    try:
        import torch
    except ImportError:
        return {"status": "BLOCKED_NO_TORCH", "metrics": {},
                "reason": "The configured Python environment does not provide PyTorch."}
    if not torch.cuda.is_available():
        return {"status": "BLOCKED_NO_GPU", "metrics": {},
                "reason": "CUDA is unavailable; no CPU result is substituted."}
    device = torch.device("cuda:0")
    free_before, total = torch.cuda.mem_get_info(device)
    props = torch.cuda.get_device_properties(device)
    environment = {
        "python": platform.python_version(), "platform": platform.platform(),
        "torch": torch.__version__, "cuda_runtime": torch.version.cuda,
        "device_name": props.name, "compute_capability": list(torch.cuda.get_device_capability(device)),
        "total_vram_bytes": int(total), "free_vram_before_bytes": int(free_before),
    }
    if free_before < config["minimum_free_vram_bytes"]:
        return {"status": "BLOCKED_LOW_VRAM", "environment": environment,
                "metrics": {}, "reason": "Free VRAM is below the benchmark config threshold."}
    results = []
    for size in config["matrix_sizes"]:
        a = torch.randn((size, size), device=device, dtype=torch.float32)
        b = torch.randn((size, size), device=device, dtype=torch.float32)
        for _ in range(config["warmup"]):
            torch.mm(a, b)
        torch.cuda.synchronize(device)
        samples = []
        for _ in range(config["repeats"]):
            start = torch.cuda.Event(enable_timing=True)
            end = torch.cuda.Event(enable_timing=True)
            start.record()
            torch.mm(a, b)
            end.record()
            torch.cuda.synchronize(device)
            samples.append(start.elapsed_time(end) / 1000.0)
        median_seconds = statistics.median(samples)
        results.append({
            "matrix_size": int(size), "operation": "float32 square matrix multiplication",
            "repeats": len(samples), "median_seconds": median_seconds,
            "median_tflops": (2.0 * size ** 3 / median_seconds / 1e12) if median_seconds else None,
            "samples_seconds": samples,
        })
        del a, b
    torch.cuda.synchronize(device)
    free_after, _ = torch.cuda.mem_get_info(device)
    environment["free_vram_after_bytes"] = int(free_after)
    return {"status": "PASS", "environment": environment,
            "metrics": {"cuda_matrix_multiplication": results},
            "measured_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "scientific_training": False}


def write_outputs(config_path: Path, output_dir: Path, source_commit: str) -> int:
    config = load_config(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    result = benchmark_cuda(config)
    config_sha = hashlib.sha256(config_path.read_bytes()).hexdigest()
    metrics = {
        "schema_version": 1, "status": result["status"], "preset": config["preset"],
        "source_commit": source_commit, "config_sha256": config_sha,
        "environment": result.get("environment", {}), "metrics": result.get("metrics", {}),
        "reason": result.get("reason"), "measured_utc": result.get("measured_utc"),
        "scientific_training": False,
    }
    gate_report = {
        "schema_version": 1, "status": result["status"],
        "summary": "Hardware benchmark only; no scientific gates or training were run.",
        "gates": [], "source_commit": source_commit,
    }
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "gate_report.json").write_text(json.dumps(gate_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "run_manifest.json").write_text(json.dumps({
        "schema_version": 1, "status": result["status"], "preset": config["preset"],
        "source_commit": source_commit, "config_sha256": config_sha,
        "entrypoint": "pxrd_autolab/benchmark_gpu.py",
        "entrypoint_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scientific_training": False, "scientific_certification": False,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# CUDA matrix benchmark", "", f"Status: **{result['status']}**", "",
             "This measures CUDA float32 matrix multiplication throughput. It is not a training run or scientific result.", ""]
    if result.get("reason"):
        lines.append("Reason: " + result["reason"])
    elif result.get("environment"):
        env = result["environment"]
        lines.extend([f"- Device: {env['device_name']}", f"- CUDA: {env['cuda_runtime']}",
                      f"- Free VRAM before: {env['free_vram_before_bytes']} bytes"])
        lines.extend(f"- n={m['matrix_size']}: {m['median_tflops']:.4f} TFLOP/s median"
                     for m in result.get("metrics", {}).get("cuda_matrix_multiplication", []))
    (output_dir / "TECHNICAL_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if result["status"] == "PASS" else 3


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--source-commit", default="unknown")
    args = parser.parse_args(argv)
    try:
        return write_outputs(args.config.resolve(), args.output_dir.resolve(), args.source_commit)
    except Exception as exc:
        print("Benchmark failed:", str(exc)[:400], file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
