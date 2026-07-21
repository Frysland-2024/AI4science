"""Differentiable V7 objectives and adversarial residual training."""

from __future__ import annotations

from typing import Callable

import torch
from torch import nn
from torch.nn import functional as F


def _model_output(model: nn.Module, x: torch.Tensor) -> dict[str, torch.Tensor | None]:
    output = model(x)
    if isinstance(output, dict):
        if "logits" not in output or "pooled_embedding" not in output:
            raise ValueError("backbone output must contain logits and pooled_embedding")
        return output
    # Keep small tensor-only test models usable alongside the structured backbone contract.
    return {
        "logits": output,
        "pooled_embedding": output,
        "main_tokens": output.unsqueeze(1),
        "prior_tokens": None,
    }


def js_divergence(first_logits: torch.Tensor, second_logits: torch.Tensor) -> torch.Tensor:
    first_log = F.log_softmax(first_logits, dim=-1)
    second_log = F.log_softmax(second_logits, dim=-1)
    first = first_log.exp()
    second = second_log.exp()
    midpoint = 0.5 * (first + second)
    midpoint_log = midpoint.clamp_min(1e-12).log()
    return 0.5 * (
        F.kl_div(midpoint_log, first, reduction="batchmean")
        + F.kl_div(midpoint_log, second, reduction="batchmean")
    )


def fixed_erm(
    model: nn.Module,
    x_fixed: torch.Tensor,
    target: torch.Tensor,
    *,
    x_fixed_second: torch.Tensor | None = None,
    classification_loss: Callable = F.cross_entropy,
) -> dict[str, torch.Tensor]:
    output = _model_output(model, x_fixed)
    logits = output["logits"]
    assert logits is not None
    second_logits = None
    if x_fixed_second is None:
        classification = classification_loss(logits, target)
    else:
        second_logits = _model_output(model, x_fixed_second)["logits"]
        assert second_logits is not None
        classification = 0.5 * (
            classification_loss(logits, target)
            + classification_loss(second_logits, target)
        )
    zero = classification.new_zeros(())
    result = {
        "logits_first": logits,
        "classification": classification,
        "consistency": zero,
        "total": classification,
    }
    if second_logits is not None:
        result["logits_second"] = second_logits
    return result


def dynamic_erm(
    model: nn.Module,
    x1: torch.Tensor,
    x2: torch.Tensor,
    target: torch.Tensor,
    *,
    classification_loss: Callable = F.cross_entropy,
) -> dict[str, torch.Tensor]:
    output1 = _model_output(model, x1)
    output2 = _model_output(model, x2)
    logits1 = output1["logits"]
    logits2 = output2["logits"]
    assert logits1 is not None and logits2 is not None
    classification = 0.5 * (
        classification_loss(logits1, target) + classification_loss(logits2, target)
    )
    zero = classification.new_zeros(())
    return {
        "logits_first": logits1,
        "logits_second": logits2,
        "classification": classification,
        "consistency": zero,
        "total": classification,
    }


def dynamic_consistency(
    model: nn.Module,
    x1: torch.Tensor,
    x2: torch.Tensor,
    target: torch.Tensor,
    *,
    consistency_weight: float,
    classification_loss: Callable = F.cross_entropy,
) -> dict[str, torch.Tensor]:
    if consistency_weight < 0:
        raise ValueError("consistency_weight must be non-negative")
    output1 = _model_output(model, x1)
    output2 = _model_output(model, x2)
    logits1 = output1["logits"]
    logits2 = output2["logits"]
    assert logits1 is not None and logits2 is not None
    classification = 0.5 * (
        classification_loss(logits1, target) + classification_loss(logits2, target)
    )
    consistency = js_divergence(logits1, logits2)
    return {
        "logits_first": logits1,
        "logits_second": logits2,
        "classification": classification,
        "consistency": consistency,
        "total": classification + consistency_weight * consistency,
    }


def dynamic_js(
    model: nn.Module,
    x1: torch.Tensor,
    x2: torch.Tensor,
    target: torch.Tensor,
    *,
    lambda_js: float,
    classification_loss: Callable = F.cross_entropy,
) -> dict[str, torch.Tensor]:
    """Project name for output-level JS consistency."""
    return dynamic_consistency(
        model,
        x1,
        x2,
        target,
        consistency_weight=lambda_js,
        classification_loss=classification_loss,
    )


class ResidualClassifier(nn.Module):
    """Small classifier used by the two-step residual objective."""

    def __init__(self, embedding_dim: int, *, depth: int = 1, num_classes: int = 7) -> None:
        super().__init__()
        if depth not in {1, 2}:
            raise ValueError("residual classifier depth must be 1 or 2")
        if depth == 1:
            self.network = nn.Linear(embedding_dim, num_classes)
        else:
            self.network = nn.Sequential(
                nn.Linear(embedding_dim, embedding_dim),
                nn.GELU(),
                nn.Linear(embedding_dim, num_classes),
            )

    def forward(self, residual: torch.Tensor) -> torch.Tensor:
        return self.network(residual)


class PerturbationDeltaRegressor(nn.Module):
    """Decode simulator-known perturbation differences from a signed residual."""

    def __init__(self, embedding_dim: int, *, output_dim: int = 2, depth: int = 1) -> None:
        super().__init__()
        if output_dim <= 0:
            raise ValueError("perturbation output_dim must be positive")
        if depth not in {1, 2}:
            raise ValueError("perturbation regressor depth must be 1 or 2")
        if depth == 1:
            self.network = nn.Linear(embedding_dim, output_dim)
        else:
            self.network = nn.Sequential(
                nn.Linear(embedding_dim, embedding_dim),
                nn.GELU(),
                nn.Linear(embedding_dim, output_dim),
            )

    def forward(self, residual: torch.Tensor) -> torch.Tensor:
        return self.network(residual)


def l2_normalize_embedding(embedding: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
    return embedding / (embedding.norm(dim=-1, keepdim=True) + eps)


def symmetric_measurement_residual(
    first: torch.Tensor,
    second: torch.Tensor,
    *,
    eps: float = 1e-8,
) -> torch.Tensor:
    """Absolute difference of normalized views; invariant to view order."""
    return torch.abs(l2_normalize_embedding(first, eps) - l2_normalize_embedding(second, eps))


def signed_measurement_residual(
    first: torch.Tensor,
    second: torch.Tensor,
    *,
    eps: float = 1e-8,
) -> torch.Tensor:
    """Signed normalized residual ``second - first`` for predicting ``z2 - z1``."""
    return l2_normalize_embedding(second, eps) - l2_normalize_embedding(first, eps)


def residual_confusion_kl(logits: torch.Tensor, *, num_classes: int = 7) -> torch.Tensor:
    """Compute KL(q || uniform) in the project-defined direction."""
    if logits.shape[-1] != num_classes:
        raise ValueError("residual classifier output does not match num_classes")
    probabilities = F.softmax(logits, dim=-1)
    log_probabilities = F.log_softmax(logits, dim=-1)
    log_uniform = -torch.log(torch.tensor(float(num_classes), device=logits.device, dtype=logits.dtype))
    return torch.sum(probabilities * (log_probabilities - log_uniform), dim=-1).mean()


def residual_lambda_schedule(
    epoch: int,
    *,
    target: float = 0.1,
    warmup_epochs: int = 5,
    ramp_epochs: int = 5,
) -> float:
    if target < 0 or warmup_epochs < 0 or ramp_epochs < 0:
        raise ValueError("residual schedule values must be non-negative")
    if epoch < warmup_epochs:
        return 0.0
    if ramp_epochs == 0:
        return target
    progress = min(1.0, (epoch - warmup_epochs + 1) / ramp_epochs)
    return float(target * progress)


def dynamic_residual(
    model: nn.Module,
    residual_classifier: ResidualClassifier,
    x1: torch.Tensor,
    x2: torch.Tensor,
    target: torch.Tensor,
    *,
    optimizer_main: torch.optim.Optimizer,
    optimizer_res: torch.optim.Optimizer,
    lambda_res: float,
    classification_loss: Callable = F.cross_entropy,
) -> dict[str, torch.Tensor]:
    """Run one Step A/Step B residual-decorrelation update."""
    if lambda_res < 0:
        raise ValueError("lambda_res must be non-negative")

    # Compute the two backbone views once.  Step A consumes detached embeddings;
    # Step B reuses the same graph, so the auxiliary update never doubles the
    # backbone-forward budget.
    output1 = _model_output(model, x1)
    output2 = _model_output(model, x2)
    logits1 = output1["logits"]
    logits2 = output2["logits"]
    embedding1 = output1["pooled_embedding"]
    embedding2 = output2["pooled_embedding"]
    assert logits1 is not None and logits2 is not None
    assert embedding1 is not None and embedding2 is not None
    residual_detached = symmetric_measurement_residual(
        embedding1.detach(), embedding2.detach()
    )
    optimizer_res.zero_grad(set_to_none=True)
    probe_logits = residual_classifier(residual_detached)
    probe_loss = classification_loss(probe_logits, target)
    probe_loss.backward()
    optimizer_res.step()

    # Step B: freeze only residual-head parameters, preserving input gradients through it.
    previous_requires_grad = [parameter.requires_grad for parameter in residual_classifier.parameters()]
    for parameter in residual_classifier.parameters():
        parameter.requires_grad_(False)
    optimizer_main.zero_grad(set_to_none=True)
    residual = symmetric_measurement_residual(embedding1, embedding2)
    classification = 0.5 * (
        classification_loss(logits1, target) + classification_loss(logits2, target)
    )
    confusion_logits = residual_classifier(residual)
    independence = residual_confusion_kl(confusion_logits)
    total = classification + lambda_res * independence
    total.backward()
    optimizer_main.step()
    for parameter, requires_grad in zip(residual_classifier.parameters(), previous_requires_grad, strict=True):
        parameter.requires_grad_(requires_grad)

    return {
        "logits_first": logits1,
        "logits_second": logits2,
        "pooled_embedding_first": embedding1,
        "pooled_embedding_second": embedding2,
        "residual": residual.detach(),
        "classification": classification.detach(),
        "probe": probe_loss.detach(),
        "independence": independence.detach(),
        "total": total.detach(),
    }


def dynamic_perturbation_supervised_residual(
    model: nn.Module,
    residual_classifier: ResidualClassifier,
    perturbation_regressor: PerturbationDeltaRegressor,
    x1: torch.Tensor,
    x2: torch.Tensor,
    target: torch.Tensor,
    perturbation_delta: torch.Tensor,
    *,
    optimizer_main: torch.optim.Optimizer,
    optimizer_aux: torch.optim.Optimizer,
    lambda_perturb: float,
    lambda_res: float,
    classification_loss: Callable = F.cross_entropy,
    perturbation_loss: Callable = F.smooth_l1_loss,
) -> dict[str, torch.Tensor]:
    """One paired update with nuisance supervision and residual class decorrelation.

    The backbone is evaluated exactly twice. Auxiliary heads first learn from a
    detached residual; the encoder then learns a residual that remains predictive
    of the known perturbation delta but uninformative about crystal-system class.
    """
    if lambda_perturb < 0 or lambda_res < 0:
        raise ValueError("perturbation and residual weights must be non-negative")

    output1 = _model_output(model, x1)
    output2 = _model_output(model, x2)
    logits1 = output1["logits"]
    logits2 = output2["logits"]
    embedding1 = output1["pooled_embedding"]
    embedding2 = output2["pooled_embedding"]
    assert logits1 is not None and logits2 is not None
    assert embedding1 is not None and embedding2 is not None
    if perturbation_delta.ndim != 2 or perturbation_delta.shape[0] != target.shape[0]:
        raise ValueError("perturbation_delta must have shape [batch, target_dim]")

    residual_detached = signed_measurement_residual(
        embedding1.detach(), embedding2.detach()
    )
    optimizer_aux.zero_grad(set_to_none=True)
    probe_logits = residual_classifier(residual_detached)
    probe_loss = classification_loss(probe_logits, target)
    predicted_delta_detached = perturbation_regressor(residual_detached)
    if predicted_delta_detached.shape != perturbation_delta.shape:
        raise ValueError("perturbation regressor output does not match perturbation target")
    decoder_loss = perturbation_loss(predicted_delta_detached, perturbation_delta)
    (probe_loss + decoder_loss).backward()
    optimizer_aux.step()

    auxiliary_modules = (residual_classifier, perturbation_regressor)
    previous_requires_grad = [
        [parameter.requires_grad for parameter in module.parameters()]
        for module in auxiliary_modules
    ]
    for module in auxiliary_modules:
        for parameter in module.parameters():
            parameter.requires_grad_(False)

    optimizer_main.zero_grad(set_to_none=True)
    residual = signed_measurement_residual(embedding1, embedding2)
    classification = 0.5 * (
        classification_loss(logits1, target) + classification_loss(logits2, target)
    )
    predicted_delta = perturbation_regressor(residual)
    perturbation = perturbation_loss(predicted_delta, perturbation_delta)
    independence = residual_confusion_kl(residual_classifier(residual))
    total = classification + lambda_perturb * perturbation + lambda_res * independence
    total.backward()
    optimizer_main.step()

    for module, states in zip(auxiliary_modules, previous_requires_grad, strict=True):
        for parameter, requires_grad in zip(module.parameters(), states, strict=True):
            parameter.requires_grad_(requires_grad)

    return {
        "logits_first": logits1.detach(),
        "logits_second": logits2.detach(),
        "pooled_embedding_first": embedding1.detach(),
        "pooled_embedding_second": embedding2.detach(),
        "residual": residual.detach(),
        "predicted_perturbation_delta": predicted_delta.detach(),
        "classification": classification.detach(),
        "probe": probe_loss.detach(),
        "decoder": decoder_loss.detach(),
        "perturbation": perturbation.detach(),
        "independence": independence.detach(),
        "total": total.detach(),
    }
