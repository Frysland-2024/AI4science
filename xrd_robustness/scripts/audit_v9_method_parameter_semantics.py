"""Audit the mathematical semantics of the V9-T method-specific parameters.

The audit is data-free and does not start a training run.  It checks the exact
objective implementations used by V9-T and records the distinction between the
order-invariant production residual and the signed residual reserved for the
deferred perturbation-regression path.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import torch
from torch import nn
from torch.nn import functional as F


PROJECT_ROOT = Path(__file__).resolve().parents[1]

from xrd_robustness.training.objectives import (  # noqa: E402
    ResidualClassifier,
    dynamic_erm,
    dynamic_js,
    dynamic_residual,
    js_divergence,
    l2_normalize_embedding,
    residual_confusion_kl,
    residual_lambda_schedule,
    signed_measurement_residual,
    symmetric_measurement_residual,
)


class _TinyBackbone(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.encoder = nn.Linear(5, 8, bias=False)
        self.classifier = nn.Linear(8, 7, bias=False)

    def forward(self, inputs: torch.Tensor) -> dict[str, torch.Tensor]:
        embedding = torch.tanh(self.encoder(inputs))
        return {
            "logits": self.classifier(embedding),
            "pooled_embedding": embedding,
        }


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _state_sha256(module: nn.Module) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(module.state_dict().items()):
        digest.update(name.encode("utf-8"))
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest().upper()


def _one_step_hash(
    initial_state: dict[str, torch.Tensor],
    x1: torch.Tensor,
    x2: torch.Tensor,
    labels: torch.Tensor,
    *,
    objective: str,
) -> str:
    model = _TinyBackbone().to(x1.device)
    model.load_state_dict(initial_state)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.05)
    if objective == "erm":
        result = dynamic_erm(model, x1, x2, labels)
        optimizer.zero_grad(set_to_none=True)
        result["total"].backward()
        optimizer.step()
    elif objective == "js_zero":
        result = dynamic_js(model, x1, x2, labels, lambda_js=0.0)
        optimizer.zero_grad(set_to_none=True)
        result["total"].backward()
        optimizer.step()
    elif objective == "residual_zero":
        torch.manual_seed(20260723)
        head = ResidualClassifier(8, depth=1).to(x1.device)
        head_optimizer = torch.optim.SGD(head.parameters(), lr=0.05)
        dynamic_residual(
            model,
            head,
            x1,
            x2,
            labels,
            optimizer_main=optimizer,
            optimizer_res=head_optimizer,
            lambda_res=0.0,
        )
    else:  # pragma: no cover - defensive branch
        raise ValueError(f"unsupported objective: {objective}")
    return _state_sha256(model)


def run_audit(*, device_name: str = "cpu") -> dict[str, Any]:
    device = torch.device(device_name)
    torch.manual_seed(20260722)
    x1 = torch.tensor(
        [
            [0.1, 0.2, 0.3, 0.4, 0.5],
            [0.5, 0.4, 0.3, 0.2, 0.1],
            [0.3, 0.1, 0.4, 0.2, 0.6],
            [0.7, 0.2, 0.1, 0.5, 0.3],
        ],
        device=device,
    )
    x2 = torch.tensor(
        [
            [0.2, 0.1, 0.4, 0.3, 0.6],
            [0.4, 0.5, 0.2, 0.3, 0.2],
            [0.2, 0.3, 0.5, 0.1, 0.7],
            [0.6, 0.3, 0.2, 0.4, 0.1],
        ],
        device=device,
    )
    labels = torch.tensor([0, 1, 2, 3], device=device)

    model = _TinyBackbone().to(device)
    initial_state = copy.deepcopy(model.state_dict())
    erm_hash = _one_step_hash(initial_state, x1, x2, labels, objective="erm")
    js_zero_hash = _one_step_hash(initial_state, x1, x2, labels, objective="js_zero")
    residual_zero_hash = _one_step_hash(
        initial_state, x1, x2, labels, objective="residual_zero"
    )

    first_logits = torch.tensor(
        [[2.0, 0.1, -0.2, 0.3, -0.4, 0.7, -0.1], [0.2, 1.4, 0.0, -0.3, 0.5, -0.2, 0.1]],
        device=device,
    )
    second_logits = torch.tensor(
        [[0.1, 1.7, -0.1, 0.2, 0.0, -0.5, 0.3], [0.4, 0.2, 1.3, -0.2, 0.1, 0.0, -0.4]],
        device=device,
    )
    js_forward = js_divergence(first_logits, second_logits)
    js_swapped = js_divergence(second_logits, first_logits)
    js_self = js_divergence(first_logits, first_logits)
    js_duplicated = js_divergence(first_logits.repeat(2, 1), second_logits.repeat(2, 1))
    extreme_first = torch.tensor([[50.0, -50.0, -50.0, -50.0, -50.0, -50.0, -50.0]], device=device)
    extreme_second = torch.tensor([[-50.0, 50.0, -50.0, -50.0, -50.0, -50.0, -50.0]], device=device)
    js_extreme = js_divergence(extreme_first, extreme_second)

    embedding_first = model(x1)["pooled_embedding"]
    embedding_second = model(x2)["pooled_embedding"]
    production_residual = symmetric_measurement_residual(embedding_first, embedding_second)
    production_swapped = symmetric_measurement_residual(embedding_second, embedding_first)
    signed_residual = signed_measurement_residual(embedding_first, embedding_second)
    signed_swapped = signed_measurement_residual(embedding_second, embedding_first)
    zero_normalized = l2_normalize_embedding(torch.zeros(3, 8, device=device))

    torch.manual_seed(20260724)
    residual_head = ResidualClassifier(8, depth=1).to(device)
    forward_decorrelation = residual_confusion_kl(residual_head(production_residual))
    swapped_decorrelation = residual_confusion_kl(residual_head(production_swapped))
    duplicated_decorrelation = residual_confusion_kl(
        residual_head(production_residual).repeat(2, 1)
    )

    uniform_logits = torch.zeros(4, 7, device=device)
    peaked_logits = torch.tensor(
        [[5.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0]],
        device=device,
        requires_grad=True,
    )
    uniform_kl = residual_confusion_kl(uniform_logits)
    peaked_kl = residual_confusion_kl(peaked_logits)
    peaked_probabilities = F.softmax(peaked_logits, dim=-1)
    peaked_entropy = -(
        peaked_probabilities * F.log_softmax(peaked_logits, dim=-1)
    ).sum(dim=-1).mean()
    entropy_identity = math.log(7.0) - float(peaked_entropy.detach())
    entropy_before = float(peaked_entropy.detach())
    entropy_optimizer = torch.optim.SGD([peaked_logits], lr=0.5)
    entropy_optimizer.zero_grad(set_to_none=True)
    peaked_kl.backward()
    entropy_optimizer.step()
    probabilities_after = F.softmax(peaked_logits, dim=-1)
    entropy_after = float(
        -(
            probabilities_after * F.log_softmax(peaked_logits, dim=-1)
        ).sum(dim=-1).mean().detach()
    )

    for parameter in residual_head.parameters():
        parameter.requires_grad_(False)
    model.zero_grad(set_to_none=True)
    backbone_independence = residual_confusion_kl(
        residual_head(
            symmetric_measurement_residual(
                model(x1)["pooled_embedding"], model(x2)["pooled_embedding"]
            )
        )
    )
    backbone_gradient = torch.autograd.grad(
        backbone_independence, model.encoder.weight, retain_graph=False
    )[0]
    for parameter in residual_head.parameters():
        parameter.requires_grad_(True)
    probe_logits = residual_head(production_residual.detach())
    probe_loss = F.cross_entropy(probe_logits, labels)
    probe_gradient = torch.autograd.grad(probe_loss, tuple(residual_head.parameters()))

    classification = F.cross_entropy(first_logits, torch.tensor([0, 1], device=device))
    classification_duplicated = F.cross_entropy(
        first_logits.repeat(2, 1), torch.tensor([0, 1, 0, 1], device=device)
    )
    schedule = [
        residual_lambda_schedule(epoch, target=0.1, warmup_epochs=2, ramp_epochs=3)
        for epoch in range(7)
    ]
    formal_head = ResidualClassifier(128, depth=1)

    checks = {
        "js_zero_weight_backbone_update_equals_dynamic_erm": js_zero_hash == erm_hash,
        "js_swap_symmetric": bool(torch.equal(js_forward, js_swapped)),
        "js_identical_predictions_zero": bool(float(js_self) <= 1e-7),
        "js_non_negative": bool(float(js_forward) >= -1e-7),
        "js_batchmean_duplicate_invariant": bool(torch.allclose(js_forward, js_duplicated, atol=1e-7, rtol=0.0)),
        "js_natural_log_bound_ln2": bool(-1e-7 <= float(js_extreme) <= math.log(2.0) + 1e-6),
        "classification_batchmean_duplicate_invariant": bool(torch.allclose(classification, classification_duplicated, atol=1e-7, rtol=0.0)),
        "residual_zero_weight_backbone_update_equals_dynamic_erm": residual_zero_hash == erm_hash,
        "v9_production_residual_swap_invariant": bool(torch.equal(production_residual, production_swapped)),
        "deferred_signed_residual_swap_antisymmetric": bool(torch.equal(signed_residual, -signed_swapped)),
        "v9_decorrelation_objective_swap_invariant": bool(torch.equal(forward_decorrelation, swapped_decorrelation)),
        "residual_normalization_finite_for_zero_vectors": bool(torch.isfinite(zero_normalized).all()),
        "residual_confusion_batchmean_duplicate_invariant": bool(torch.allclose(forward_decorrelation, duplicated_decorrelation, atol=1e-7, rtol=0.0)),
        "residual_uniform_prediction_has_zero_kl": bool(abs(float(uniform_kl)) <= 1e-6),
        "residual_peaked_prediction_has_positive_kl": bool(float(peaked_kl.detach()) > 0.0),
        "residual_kl_equals_log_classes_minus_entropy": bool(abs(float(peaked_kl.detach()) - entropy_identity) <= 1e-6),
        "minimizing_residual_kl_increases_entropy": entropy_after > entropy_before,
        "residual_gradient_reaches_backbone": bool(float(backbone_gradient.norm()) > 0.0),
        "residual_probe_gradient_reaches_head": bool(sum(float(item.norm()) for item in probe_gradient) > 0.0),
        "residual_warmup_and_ramp_exact": bool(torch.allclose(torch.tensor(schedule), torch.tensor([0.0, 0.0, 0.1 / 3.0, 0.2 / 3.0, 0.1, 0.1, 0.1]), atol=1e-8, rtol=0.0)),
        "residual_head_depth_one_is_single_linear_layer": isinstance(formal_head.network, nn.Linear),
        "residual_head_formal_parameter_count_is_903": sum(parameter.numel() for parameter in formal_head.parameters()) == 903,
    }
    return {
        "schema_version": "v9-method-parameter-semantics-audit-v1",
        "status": "pass" if all(checks.values()) else "fail",
        "scope": "data_free_objective_semantics",
        "formal_training_runs_started": 0,
        "validation_used": False,
        "simulated_test_used": False,
        "real_test_used": False,
        "candidate_selection_performed": False,
        "device": str(device),
        "input_hashes": {
            "audit_script": _file_sha256(Path(__file__).resolve()),
            "objective_source": _file_sha256(
                PROJECT_ROOT / "src" / "xrd_robustness" / "training" / "objectives.py"
            ),
        },
        "mathematical_scale": {
            "log_base": "natural",
            "js_range": [0.0, math.log(2.0)],
            "seven_class_cross_entropy_at_uniform_prediction": math.log(7.0),
            "residual_confusion_kl_range": [0.0, math.log(7.0)],
            "residual_confusion_identity": "KL(q||Uniform(7)) = ln(7) - H(q)",
        },
        "residual_contract": {
            "v9_production": "abs(L2Norm(z1) - L2Norm(z2)); invariant to view order",
            "deferred_signed_path": "L2Norm(z2) - L2Norm(z1); sign reverses under view swap",
            "scientific_interpretation": "V9-T decorrelates class information from residual magnitude and does not claim a signed perturbation delta",
        },
        "residual_schedule_epochs_0_to_6": schedule,
        "zero_weight_backbone_hashes": {
            "dynamic_erm": erm_hash,
            "js_zero": js_zero_hash,
            "residual_zero": residual_zero_hash,
        },
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "reports" / "v9_method_semantics_audit.json"),
    )
    args = parser.parse_args()
    report = run_audit(device_name=args.device)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(output), "checks": report["checks"]}, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
