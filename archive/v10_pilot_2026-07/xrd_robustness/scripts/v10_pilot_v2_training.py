"""Learned-state pretraining and matched branch optimization for V10 Pilot v2."""
from __future__ import annotations

from collections import defaultdict
import copy
import math
import time
from typing import Any, Mapping, Sequence

import numpy as np
import torch
from torch.nn import functional as F

from audit_v9_learned_state_scale import BATCH_SIZE, _autocast, _labels_tensor, _set_seed
from v10_pilot_config import (
    LAMBDA_PERTURB_TARGET,
    LAMBDA_RES_TARGET,
    RAMP_EPOCHS,
    SEED,
    WARMUP_EPOCHS,
)
from v10_pilot_targets import measurement_delta_tensor
from v10_pilot_training import PilotTrainStream, new_optimizer
from xrd_robustness.models import PAMPT, PAMPTConfig
from xrd_robustness.training import (
    PerturbationDeltaRegressor,
    ResidualClassifier,
    dynamic_perturbation_supervised_residual,
    dynamic_residual,
    residual_lambda_schedule,
)

BRANCH_STREAM_EPOCH_OFFSET = 10_000
BRANCH_KEY_BASE_OFFSET = 10_000_000


def _mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("cannot average an empty sequence")
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def _all_finite(result: Mapping[str, torch.Tensor]) -> bool:
    return all(bool(torch.isfinite(value.detach()).all()) for value in result.values())


def pretrain_erm_epoch(
    *,
    model: PAMPT,
    optimizer: torch.optim.Optimizer,
    stream: PilotTrainStream,
    train_ids: Sequence[str],
    labels: Mapping[str, int],
    device: torch.device,
    epoch_index: int,
    amp_enabled: bool,
) -> dict[str, Any]:
    """Train one full-Train paired-ERM epoch before any auxiliary objective."""
    model.train()
    losses: list[float] = []
    correct = 0
    examples = 0
    steps = 0
    started = time.perf_counter()
    for batch_ids, first, second, _, _ in stream.batches(
        train_ids,
        stream_epoch=epoch_index,
        key_base=epoch_index * 100_000,
    ):
        x1 = torch.from_numpy(np.ascontiguousarray(first)).float().to(device)
        x2 = torch.from_numpy(np.ascontiguousarray(second)).float().to(device)
        target = _labels_tensor(batch_ids, labels, device)
        _set_seed(SEED + epoch_index * 100_000 + steps, device)
        optimizer.zero_grad(set_to_none=True)
        with _autocast(device, amp_enabled):
            output1 = model(x1)
            output2 = model(x2)
            loss = 0.5 * (
                F.cross_entropy(output1["logits"], target)
                + F.cross_entropy(output2["logits"], target)
            )
        if not bool(torch.isfinite(loss.detach())):
            raise FloatingPointError(
                f"non-finite pretraining loss at epoch {epoch_index + 1}, step {steps + 1}"
            )
        loss.backward()
        optimizer.step()
        count = len(batch_ids)
        losses.append(float(loss.detach().float()))
        correct += int((output1["logits"].detach().argmax(-1) == target).sum())
        correct += int((output2["logits"].detach().argmax(-1) == target).sum())
        examples += count
        steps += 1
        if steps % 100 == 0:
            print(
                f"v10-v2 pretrain epoch={epoch_index + 1} step={steps} "
                f"of={math.ceil(len(train_ids) / BATCH_SIZE)}",
                flush=True,
            )
    return {
        "epoch": epoch_index + 1,
        "optimizer_steps": steps,
        "mother_structures": examples,
        "paired_spectra": 2 * examples,
        "classification_ce": _mean(losses),
        "classification_accuracy_across_two_views": correct / (2 * examples),
        "runtime_seconds": time.perf_counter() - started,
    }


def clone_learned_branches(
    *,
    base_model: PAMPT,
    base_optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> tuple[
    dict[str, PAMPT],
    ResidualClassifier,
    ResidualClassifier,
    PerturbationDeltaRegressor,
    dict[str, torch.optim.Optimizer],
]:
    """Clone model and main-optimizer state after the learned-state gates pass."""
    model_state = copy.deepcopy(base_model.state_dict())
    optimizer_state = copy.deepcopy(base_optimizer.state_dict())
    models = {
        "erm": PAMPT(PAMPTConfig(variant="b3")).to(device),
        "v9_residual": PAMPT(PAMPTConfig(variant="b3")).to(device),
        "v10_supervised": PAMPT(PAMPTConfig(variant="b3")).to(device),
    }
    for model in models.values():
        model.load_state_dict(model_state)

    _set_seed(SEED + 40_000, device)
    head_template = ResidualClassifier(models["erm"].config.embed_dim, depth=1).to(device)
    head_state = copy.deepcopy(head_template.state_dict())
    v9_head = ResidualClassifier(models["erm"].config.embed_dim, depth=1).to(device)
    v10_head = ResidualClassifier(models["erm"].config.embed_dim, depth=1).to(device)
    v9_head.load_state_dict(head_state)
    v10_head.load_state_dict(head_state)
    del head_template

    _set_seed(SEED + 50_000, device)
    perturbation_regressor = PerturbationDeltaRegressor(
        models["erm"].config.embed_dim, output_dim=4, depth=1
    ).to(device)

    optimizers = {
        "erm": new_optimizer(models["erm"].parameters(), device),
        "v9_main": new_optimizer(models["v9_residual"].parameters(), device),
        "v9_aux": new_optimizer(v9_head.parameters(), device),
        "v10_main": new_optimizer(models["v10_supervised"].parameters(), device),
        "v10_aux": new_optimizer(
            list(v10_head.parameters()) + list(perturbation_regressor.parameters()),
            device,
        ),
    }
    for key in ("erm", "v9_main", "v10_main"):
        optimizers[key].load_state_dict(copy.deepcopy(optimizer_state))
    return models, v9_head, v10_head, perturbation_regressor, optimizers


def train_matched_branch_epoch(
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
    branch_epoch_index: int,
    amp_enabled: bool,
) -> dict[str, Any]:
    """Run one matched post-pretraining ERM/V9/V10 epoch."""
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
        branch_epoch_index,
        target=LAMBDA_RES_TARGET,
        warmup_epochs=WARMUP_EPOCHS,
        ramp_epochs=RAMP_EPOCHS,
    )
    lambda_perturb = residual_lambda_schedule(
        branch_epoch_index,
        target=LAMBDA_PERTURB_TARGET,
        warmup_epochs=WARMUP_EPOCHS,
        ramp_epochs=RAMP_EPOCHS,
    )
    stream_epoch = BRANCH_STREAM_EPOCH_OFFSET + branch_epoch_index
    key_base = BRANCH_KEY_BASE_OFFSET + branch_epoch_index * 100_000
    steps = 0
    for batch_ids, first, second, parameters_first, parameters_second in stream.batches(
        train_ids,
        stream_epoch=stream_epoch,
        key_base=key_base,
    ):
        x1 = torch.from_numpy(np.ascontiguousarray(first)).float().to(device)
        x2 = torch.from_numpy(np.ascontiguousarray(second)).float().to(device)
        target = _labels_tensor(batch_ids, labels, device)
        perturbation_delta = measurement_delta_tensor(
            parameters_first, parameters_second, device=device
        )
        branch_seed = SEED + stream_epoch * 100_000 + steps

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
                    f"non-finite value in {branch} at branch epoch "
                    f"{branch_epoch_index + 1}, step {steps + 1}"
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
                f"v10-v2 branch epoch={branch_epoch_index + 1} step={steps} "
                f"of={math.ceil(len(train_ids) / BATCH_SIZE)}",
                flush=True,
            )
    return {
        "epoch": branch_epoch_index + 1,
        "optimizer_steps_per_branch": steps,
        "lambda_res": lambda_res,
        "lambda_perturb": lambda_perturb,
        "stream_epoch": stream_epoch,
        "branches": {
            branch: {key: _mean(values) for key, values in metrics.items()}
            for branch, metrics in trace.items()
        },
        "runtime_seconds": time.perf_counter() - started,
    }
