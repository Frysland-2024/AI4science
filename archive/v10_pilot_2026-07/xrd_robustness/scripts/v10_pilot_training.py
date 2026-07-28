"""Matched Train-only optimization utilities for the V10 Pilot."""
from __future__ import annotations

from collections import defaultdict
import json
import math
from pathlib import Path
import time
from typing import Any, Iterator, Mapping, Sequence

import numpy as np
import torch
from torch.nn import functional as F

from audit_v9_learned_state_scale import (
    BATCH_SIZE,
    LEARNING_RATE,
    WEIGHT_DECAY,
    _autocast,
    _labels_tensor,
    _set_seed,
)
from v10_pilot_config import (
    LAMBDA_PERTURB_TARGET,
    LAMBDA_RES_TARGET,
    RAMP_EPOCHS,
    SEED,
    WARMUP_EPOCHS,
)
from v10_pilot_targets import measurement_delta_tensor
from xrd_robustness.experiment import file_hash
from xrd_robustness.models import PAMPT
from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.perturbation_strategy import IndependentDynamicStrategy
from xrd_robustness.physics import PhysicsParameterSampler, PhysicsParameters
from xrd_robustness.training import (
    PerturbationDeltaRegressor,
    ResidualClassifier,
    dynamic_perturbation_supervised_residual,
    dynamic_residual,
    residual_lambda_schedule,
)
from xrd_robustness.training_prefetch import DynamicBatchPrefetcher
from xrd_robustness.training_stream import (
    deterministic_epoch_shuffle,
    select_epoch_batch,
)
from xrd_robustness.view_manifest import build_parameter_batch


class PilotTrainStream:
    """Deterministic paired Train renderer that preserves simulator parameters."""

    def __init__(
        self,
        *,
        data_root: Path,
        simulation_path: Path,
        worker_count: int,
        prefetch_batches: int,
    ) -> None:
        self.simulation = json.loads(simulation_path.read_text(encoding="utf-8"))
        self.simulation["run_seed"] = SEED
        self.sampler = PhysicsParameterSampler.from_mapping(self.simulation)
        self.factory = OnlineViewFactory(
            self.sampler,
            quality_gate=True,
            quality_gate_config=self.simulation.get("quality_gates", {}),
            strategy=IndependentDynamicStrategy(
                self.sampler, config_hash=file_hash(simulation_path)
            ),
        )
        self.prefetch_batches = int(prefetch_batches)
        self.prefetcher = DynamicBatchPrefetcher(
            worker_count=worker_count,
            worker_native_threads=1,
            prefetch_batches=prefetch_batches,
            start_method="spawn",
            data_root=data_root,
            peak_cache_name="peak_tables_v7_reflection",
            sampler_config=self.simulation,
            quality_gate=True,
            quality_gate_config=self.simulation.get("quality_gates", {}),
            simulation_config_hash=file_hash(simulation_path),
            profile="train",
        )

    def batches(
        self,
        material_ids: Sequence[str],
        *,
        stream_epoch: int,
        key_base: int,
    ) -> Iterator[
        tuple[
            list[str],
            np.ndarray,
            np.ndarray,
            tuple[PhysicsParameters, ...],
            tuple[PhysicsParameters, ...],
        ]
    ]:
        ordered = deterministic_epoch_shuffle(
            material_ids, seed=SEED, epoch=stream_epoch
        )
        steps = math.ceil(len(ordered) / BATCH_SIZE)

        def submit(step: int) -> None:
            batch_ids = list(
                select_epoch_batch(
                    ordered,
                    step=step,
                    batch_size=BATCH_SIZE,
                    full_batch=False,
                )
            )
            rows = build_parameter_batch(
                batch_ids,
                self.sampler,
                profile="train",
                epoch=stream_epoch,
                global_step=step,
                split="train",
            )
            self.prefetcher.submit(key_base + step, batch_ids, rows)

        for step in range(min(steps, self.prefetch_batches)):
            submit(step)
        for step in range(steps):
            rendered = self.prefetcher.get(key_base + step)
            refill = step + self.prefetch_batches
            if refill < steps:
                submit(refill)
            yield (
                list(rendered.material_ids),
                rendered.first,
                rendered.second,
                rendered.parameters_first,
                rendered.parameters_second,
            )

    def close(self) -> None:
        self.prefetcher.close()


def new_optimizer(parameters: Any, device: torch.device) -> torch.optim.Optimizer:
    return torch.optim.AdamW(
        parameters,
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
        fused=device.type == "cuda",
    )


def _all_finite(result: Mapping[str, torch.Tensor]) -> bool:
    return all(bool(torch.isfinite(value.detach()).all()) for value in result.values())


def _mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("cannot average an empty sequence")
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def train_epoch(
    *,
    models: Mapping[str, PAMPT],
    v9_head: ResidualClassifier,
    v10_head: ResidualClassifier,
    perturbation_regressor: PerturbationDeltaRegressor,
    optimizers: Mapping[str, torch.optim.Optimizer],
    stream: PilotTrainStream,
    train_ids: Sequence[str],
    labels: Mapping[str, int],
    device: torch.device,
    epoch_index: int,
    amp_enabled: bool,
) -> dict[str, Any]:
    for model in models.values():
        model.train()
    v9_head.train()
    v10_head.train()
    perturbation_regressor.train()
    trace: dict[str, dict[str, list[float]]] = {
        branch: defaultdict(list) for branch in models
    }
    started = time.perf_counter()
    lambda_res = residual_lambda_schedule(
        epoch_index,
        target=LAMBDA_RES_TARGET,
        warmup_epochs=WARMUP_EPOCHS,
        ramp_epochs=RAMP_EPOCHS,
    )
    lambda_perturb = residual_lambda_schedule(
        epoch_index,
        target=LAMBDA_PERTURB_TARGET,
        warmup_epochs=WARMUP_EPOCHS,
        ramp_epochs=RAMP_EPOCHS,
    )
    steps = 0
    for (
        batch_ids,
        first,
        second,
        parameters_first,
        parameters_second,
    ) in stream.batches(
        train_ids,
        stream_epoch=epoch_index,
        key_base=epoch_index * 100_000,
    ):
        x1 = torch.from_numpy(np.ascontiguousarray(first)).float().to(device)
        x2 = torch.from_numpy(np.ascontiguousarray(second)).float().to(device)
        target = _labels_tensor(batch_ids, labels, device)
        perturbation_delta = measurement_delta_tensor(
            parameters_first, parameters_second, device=device
        )
        branch_seed = SEED + epoch_index * 100_000 + steps

        _set_seed(branch_seed, device)
        optimizers["erm"].zero_grad(set_to_none=True)
        with _autocast(device, amp_enabled):
            output1 = models["erm"](x1)
            output2 = models["erm"](x2)
            erm_classification = 0.5 * (
                F.cross_entropy(output1["logits"], target)
                + F.cross_entropy(output2["logits"], target)
            )
        erm_classification.backward()
        optimizers["erm"].step()
        erm_result = {
            "classification": erm_classification.detach(),
            "total": erm_classification.detach(),
        }

        _set_seed(branch_seed, device)
        with _autocast(device, amp_enabled):
            v9_result = dynamic_residual(
                models["v9_residual"],
                v9_head,
                x1,
                x2,
                target,
                optimizer_main=optimizers["v9_main"],
                optimizer_res=optimizers["v9_aux"],
                lambda_res=lambda_res,
            )

        _set_seed(branch_seed, device)
        with _autocast(device, amp_enabled):
            v10_result = dynamic_perturbation_supervised_residual(
                models["v10_supervised"],
                v10_head,
                perturbation_regressor,
                x1,
                x2,
                target,
                perturbation_delta,
                optimizer_main=optimizers["v10_main"],
                optimizer_aux=optimizers["v10_aux"],
                lambda_perturb=lambda_perturb,
                lambda_res=lambda_res,
            )

        branch_results = {
            "erm": erm_result,
            "v9_residual": v9_result,
            "v10_supervised": v10_result,
        }
        for branch, result in branch_results.items():
            if not _all_finite(result):
                raise FloatingPointError(
                    f"non-finite value in {branch} at epoch "
                    f"{epoch_index + 1}, step {steps + 1}"
                )
            for key in (
                "classification",
                "probe",
                "decoder",
                "perturbation",
                "independence",
                "total",
            ):
                if key in result:
                    trace[branch][key].append(float(result[key].detach().float()))
        steps += 1
        if steps % 25 == 0:
            print(
                f"pilot epoch={epoch_index + 1} step={steps} "
                f"of={math.ceil(len(train_ids) / BATCH_SIZE)}",
                flush=True,
            )
    return {
        "epoch": epoch_index + 1,
        "optimizer_steps_per_branch": steps,
        "lambda_res": lambda_res,
        "lambda_perturb": lambda_perturb,
        "branches": {
            branch: {key: _mean(values) for key, values in metrics.items()}
            for branch, metrics in trace.items()
        },
        "runtime_seconds": time.perf_counter() - started,
    }
