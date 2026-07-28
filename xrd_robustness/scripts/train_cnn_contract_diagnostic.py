#!/usr/bin/env python3
"""Run a preregistered ResNet CNN-contract diagnostic through train_v7."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np
import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.models.ml4pxrd_resnet1d import (  # noqa: E402
    ML4PXRDResNet1D,
    ML4PXRDResNet1DConfig,
)


CUSTOM_ARGUMENTS = {
    "--cnn-preprocessing": ("identity", {"identity", "sqrt"}),
    "--cnn-optimizer": ("adamw", {"adamw", "adam"}),
    "--cnn-lr-schedule": ("constant", {"constant", "warmup_cosine"}),
    "--cnn-lr-warmup-steps": ("0", None),
    "--cnn-total-steps": (None, None),
    "--cnn-preregistration": (None, None),
}


def _extract_custom_arguments() -> dict[str, str | None]:
    resolved: dict[str, str | None] = {}
    remaining = [sys.argv[0]]
    index = 1
    while index < len(sys.argv):
        token = sys.argv[index]
        if token not in CUSTOM_ARGUMENTS:
            remaining.append(token)
            index += 1
            continue
        if index + 1 >= len(sys.argv):
            raise SystemExit(f"{token} requires a value")
        value = sys.argv[index + 1]
        default, choices = CUSTOM_ARGUMENTS[token]
        if choices is not None and value not in choices:
            raise SystemExit(f"{token} must be one of {sorted(choices)}")
        resolved[token[2:].replace("-", "_")] = value
        index += 2
    for token, (default, _) in CUSTOM_ARGUMENTS.items():
        resolved.setdefault(token[2:].replace("-", "_"), default)
    sys.argv[:] = remaining
    return resolved


def _argument_value(name: str) -> str | None:
    try:
        index = sys.argv.index(name)
    except ValueError:
        return None
    if index + 1 >= len(sys.argv):
        raise SystemExit(f"{name} requires a value")
    return sys.argv[index + 1]


def _load_train_v7_module():
    path = PROJECT_ROOT / "scripts" / "train_v7.py"
    spec = importlib.util.spec_from_file_location("xrd_cnn_contract_train_v7", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import training entry point: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _resnet_config_factory(*args: Any, **kwargs: Any) -> ML4PXRDResNet1DConfig:
    unexpected = set(kwargs) - {"variant"}
    if unexpected or len(args) > 1:
        raise TypeError("unexpected ResNet configuration arguments")
    return ML4PXRDResNet1DConfig(model_id="18")


def _sqrt_values(values: np.ndarray) -> np.ndarray:
    return np.sqrt(np.clip(values, 0.0, None), dtype=np.float32)


def _install_preprocessing(train_v7: Any, preprocessing: str) -> None:
    if preprocessing == "identity":
        return
    original_numpy_batch_to_device = train_v7._numpy_batch_to_device
    original_make_pair_batch = train_v7._make_pair_batch

    def numpy_batch_to_device(values: np.ndarray, *args: Any, **kwargs: Any):
        return original_numpy_batch_to_device(_sqrt_values(values), *args, **kwargs)

    def make_pair_batch(*args: Any, **kwargs: Any):
        result = original_make_pair_batch(*args, **kwargs)
        return (torch.sqrt(torch.clamp_min(result[0], 0.0)),
                torch.sqrt(torch.clamp_min(result[1], 0.0)), *result[2:])

    train_v7._numpy_batch_to_device = numpy_batch_to_device
    train_v7._make_pair_batch = make_pair_batch


def _install_optimizer(
    train_v7: Any,
    *,
    optimizer_name: str,
    schedule_name: str,
    warmup_steps: int,
    total_steps: int,
) -> None:
    if schedule_name == "warmup_cosine" and not (0 < warmup_steps < total_steps):
        raise SystemExit("warmup_cosine requires 0 < warmup steps < total steps")

    def optimizer_factory(
        parameters: Any,
        *,
        learning_rate: float,
        weight_decay: float,
        fused: bool,
    ):
        if optimizer_name == "adamw":
            optimizer = torch.optim.AdamW(
                parameters,
                lr=learning_rate,
                weight_decay=weight_decay,
                fused=fused,
            )
        else:
            optimizer = torch.optim.Adam(
                parameters,
                lr=learning_rate,
                weight_decay=weight_decay,
                fused=fused,
            )
        if schedule_name == "constant":
            return optimizer

        original_step = optimizer.step
        step_count = 0

        def scheduled_step(*args: Any, **kwargs: Any):
            nonlocal step_count
            step_count += 1
            if step_count <= warmup_steps:
                factor = step_count / warmup_steps
            else:
                progress = (step_count - warmup_steps) / (total_steps - warmup_steps)
                factor = 0.5 * (1.0 + math.cos(math.pi * min(progress, 1.0)))
            for group in optimizer.param_groups:
                group["lr"] = learning_rate * factor
            return original_step(*args, **kwargs)

        optimizer.step = scheduled_step
        return optimizer

    train_v7._adamw = optimizer_factory


def _write_run_contract(custom: dict[str, str | None], exit_code: int) -> None:
    output_dir = _argument_value("--output-dir")
    if output_dir is None:
        return
    run_dir = Path(output_dir)
    if "--run-dir-exact" not in sys.argv:
        run_id = _argument_value("--run-id")
        if run_id:
            run_dir /= run_id
    preregistration = Path(str(custom["cnn_preregistration"])).resolve()
    payload = {
        "schema_version": "v9-cnn-contract-diagnostic-run-v1",
        "status": "completed" if exit_code == 0 else "failed",
        "exit_code": exit_code,
        "preprocessing": custom["cnn_preprocessing"],
        "optimizer": custom["cnn_optimizer"],
        "lr_schedule": custom["cnn_lr_schedule"],
        "lr_warmup_steps": int(str(custom["cnn_lr_warmup_steps"])),
        "total_steps": int(str(custom["cnn_total_steps"])),
        "preregistration_path": str(preregistration),
        "preregistration_sha256": hashlib.sha256(preregistration.read_bytes()).hexdigest(),
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "cnn_contract_diagnostic.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    custom = _extract_custom_arguments()
    if _argument_value("--mode") not in {"clean_erm", "dynamic_erm", "dynamic_js"}:
        raise SystemExit(
            "CNN-contract wrapper permits only clean_erm, dynamic_erm, or dynamic_js"
        )
    if _argument_value("--variant") not in {None, "b3"}:
        raise SystemExit("ResNet wrapper requires legacy argument --variant b3")
    if custom["cnn_total_steps"] is None or custom["cnn_preregistration"] is None:
        raise SystemExit("--cnn-total-steps and --cnn-preregistration are required")

    train_v7 = _load_train_v7_module()
    train_v7.PAMPTConfig = _resnet_config_factory
    train_v7.PAMPT = ML4PXRDResNet1D
    _install_preprocessing(train_v7, str(custom["cnn_preprocessing"]))
    _install_optimizer(
        train_v7,
        optimizer_name=str(custom["cnn_optimizer"]),
        schedule_name=str(custom["cnn_lr_schedule"]),
        warmup_steps=int(str(custom["cnn_lr_warmup_steps"])),
        total_steps=int(str(custom["cnn_total_steps"])),
    )
    exit_code = int(train_v7.main())
    _write_run_contract(custom, exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
