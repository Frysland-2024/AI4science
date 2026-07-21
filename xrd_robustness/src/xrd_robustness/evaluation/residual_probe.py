"""Independent post-hoc residual probe protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch
from torch import nn
from torch.nn import functional as F

from ..training.objectives import signed_measurement_residual, symmetric_measurement_residual


@dataclass(frozen=True)
class ProbeConfig:
    hidden_dim: int = 128
    epochs: int = 50
    learning_rate: float = 1e-3
    weight_decay: float = 0.0
    patience: int = 10
    num_classes: int = 7


class PostHocResidualProbe(nn.Module):
    def __init__(self, input_dim: int, config: ProbeConfig = ProbeConfig()) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, config.hidden_dim),
            nn.GELU(),
            nn.Linear(config.hidden_dim, config.num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)


def frozen_model_residuals(
    model: nn.Module,
    first: torch.Tensor,
    second: torch.Tensor,
    *,
    signed: bool = False,
) -> torch.Tensor:
    model.eval()
    with torch.no_grad():
        output_first = model(first)
        output_second = model(second)
        if not isinstance(output_first, dict) or not isinstance(output_second, dict):
            raise ValueError("post-hoc probe requires a V7 structured backbone output")
        residual_function = signed_measurement_residual if signed else symmetric_measurement_residual
        return residual_function(
            output_first["pooled_embedding"],
            output_second["pooled_embedding"],
        )


def train_posthoc_residual_probe(
    residual_train: torch.Tensor,
    labels_train: torch.Tensor,
    residual_validation: torch.Tensor,
    labels_validation: torch.Tensor,
    residual_test: torch.Tensor,
    labels_test: torch.Tensor,
    *,
    config: ProbeConfig = ProbeConfig(),
    seed: int = 0,
) -> dict[str, Any]:
    """Train only on train residuals; validation selects stopping and test stays untouched."""
    torch.manual_seed(seed)
    probe = PostHocResidualProbe(residual_train.shape[-1], config)
    optimizer = torch.optim.AdamW(
        probe.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay
    )
    best_state = None
    best_validation = float("inf")
    stale = 0
    for _ in range(config.epochs):
        probe.train()
        optimizer.zero_grad(set_to_none=True)
        train_loss = F.cross_entropy(probe(residual_train), labels_train)
        train_loss.backward()
        optimizer.step()
        probe.eval()
        with torch.no_grad():
            validation_loss = float(F.cross_entropy(probe(residual_validation), labels_validation))
        if validation_loss < best_validation:
            best_validation = validation_loss
            best_state = {key: value.detach().clone() for key, value in probe.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= config.patience:
                break
    if best_state is not None:
        probe.load_state_dict(best_state)
    probe.eval()
    with torch.no_grad():
        test_logits = probe(residual_test)
        predictions = test_logits.argmax(dim=-1)
    accuracy = float((predictions == labels_test).float().mean())
    return {
        "probe": probe,
        "test_accuracy": accuracy,
        "test_macro_f1": _macro_f1(labels_test, predictions, config.num_classes),
        "validation_loss": best_validation,
    }


def _macro_f1(labels: torch.Tensor, predictions: torch.Tensor, num_classes: int) -> float:
    scores = []
    for class_index in range(num_classes):
        tp = ((labels == class_index) & (predictions == class_index)).sum().item()
        fp = ((labels != class_index) & (predictions == class_index)).sum().item()
        fn = ((labels == class_index) & (predictions != class_index)).sum().item()
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return float(sum(scores) / num_classes)
