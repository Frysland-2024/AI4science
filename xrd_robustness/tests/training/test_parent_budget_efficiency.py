from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import torch
from torch import nn

from xrd_robustness.online_views import TrainingMode
from xrd_robustness.parent_budget_efficiency import (
    BUDGETS,
    CyclicParentSampler,
    canonical_json_bytes,
    expected_exposure,
    identity_hash,
    validate_parent_split,
)
from xrd_robustness.training.objectives import TrainingStepConfig, run_training_step
from xrd_robustness.training import paired as paired_module
from xrd_robustness.training.paired import paired_optimizer_step


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_DIR = PROJECT_ROOT / "manifests" / "parent_budget_efficiency"


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest().upper()


def test_frozen_parent_manifest_has_exact_nested_stratified_budgets() -> None:
    manifest_path = MANIFEST_DIR / "parent_subsets.v1.json"
    ranked_path = MANIFEST_DIR / "ranked_train_parents.v1.csv"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "frozen_before_training"
    assert manifest["ranked_train_file"]["sha256"] == _sha256(ranked_path.read_bytes())
    with ranked_path.open("r", newline="", encoding="utf-8") as handle:
        ranked = list(csv.DictReader(handle))
    assert len(ranked) == BUDGETS["100"]
    assert len({row["parent_structure_id"] for row in ranked}) == BUDGETS["100"]
    assert len({row["material_id"] for row in ranked}) == BUDGETS["100"]

    previous_parents: set[str] = set()
    previous_materials: set[str] = set()
    for budget in ("10", "25", "50", "100"):
        row = manifest["budgets"][budget]
        parent_ids = row["parent_structure_ids"]
        material_ids = row["material_ids"]
        assert len(parent_ids) == BUDGETS[budget]
        assert len(set(parent_ids)) == BUDGETS[budget]
        assert len(set(material_ids)) == BUDGETS[budget]
        assert row["parent_ids_sha256"] == identity_hash(parent_ids)
        assert row["material_ids_sha256"] == identity_hash(material_ids)
        assert sum(row["class_counts"].values()) == BUDGETS[budget]
        assert previous_parents.issubset(parent_ids)
        assert previous_materials.issubset(material_ids)
        current = [
            item["material_id"]
            for item in ranked
            if item["material_id"] in set(material_ids)
        ]
        assert current == material_ids
        previous_parents = set(parent_ids)
        previous_materials = set(material_ids)
    assert set(manifest["budgets"]["100"]["material_ids"]) == set(
        item["material_id"] for item in ranked
    )
    assert manifest["official_split"]["validation_count"] == 2109
    assert manifest["official_split"]["test_count"] == 2109


def test_parent_split_rejects_duplicate_physical_parent_before_count_check() -> None:
    rows = [
        {
            "material_id": "mp-a",
            "parent_structure_id": "same-parent",
            "crystal_system": "cubic",
            "split": "train",
        },
        {
            "material_id": "mp-b",
            "parent_structure_id": "same-parent",
            "crystal_system": "cubic",
            "split": "test",
        },
    ]
    with pytest.raises(ValueError, match="duplicate physical parent"):
        validate_parent_split(rows)


def test_cyclic_sampler_is_deterministic_and_never_returns_short_batches() -> None:
    rows = [
        {"material_id": f"mp-{index}", "parent_structure_id": f"p-{index}"}
        for index in range(5)
    ]
    first = CyclicParentSampler(rows, seed=20260711)
    replay = CyclicParentSampler(rows, seed=20260711)
    batches_a = [first.next_batch(4) for _ in range(4)]
    batches_b = [replay.next_batch(4) for _ in range(4)]
    ids = lambda batches: [[row["material_id"] for row in batch] for batch in batches]
    assert ids(batches_a) == ids(batches_b)
    assert all(len(batch) == 4 for batch in batches_a)
    assert first.occurrences == 16
    assert first.cycle >= 2


def test_frozen_step_budget_implies_equal_occurrences_and_two_views() -> None:
    assert expected_exposure(49280, 16) == {
        "optimizer_steps": 49280,
        "parent_occurrences": 788480,
        "views": 1576960,
    }


class _TinyModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.linear = nn.Linear(4, 3)

    def forward(self, values: torch.Tensor) -> dict[str, torch.Tensor]:
        return {"logits": self.linear(values.flatten(start_dim=1))}


def _smoke_render(step: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    base = torch.arange(16, dtype=torch.float32).reshape(4, 4) / 16 + step / 10
    return base, base.flip(1) + 0.125, torch.tensor([0, 1, 2, 0], dtype=torch.long)


def _smoke_stream_hashes() -> tuple[str, str]:
    samples = hashlib.sha256()
    views = hashlib.sha256()
    for step in range(1, 4):
        x1, x2, target = _smoke_render(step)
        samples.update(hashlib.sha256(canonical_json_bytes([step, 4])).digest())
        views.update(
            hashlib.sha256(
                canonical_json_bytes(
                    [step, x1.numpy().tolist(), x2.numpy().tolist(), target.numpy().tolist()]
                )
            ).digest()
        )
    return samples.hexdigest(), views.hexdigest()


def test_three_step_paired_smoke_shares_identical_two_views(monkeypatch: pytest.MonkeyPatch) -> None:
    torch.manual_seed(10)
    initial = _TinyModel()
    models = {"dynamic_erm": _TinyModel(), "dynamic_js": _TinyModel()}
    for model in models.values():
        model.load_state_dict(initial.state_dict())
    optimizers = {
        name: torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        for name, model in models.items()
    }
    configs = {
        "dynamic_erm": TrainingStepConfig(TrainingMode.DYNAMIC_ERM, lambda_js=0.0),
        "dynamic_js": TrainingStepConfig(TrainingMode.DYNAMIC_JS, lambda_js=60.0),
    }
    original = paired_module.run_training_step
    seen: list[tuple[int, int, int]] = []

    def traced(config, model, *, x1, x2, target):
        seen.append((id(x1), id(x2), id(target)))
        return original(config, model, x1=x1, x2=x2, target=target)

    monkeypatch.setattr(paired_module, "run_training_step", traced)
    stream_a = hashlib.sha256()
    stream_b = hashlib.sha256()
    occurrences = views = 0
    for step in range(1, 4):
        x1, x2, target = _smoke_render(step)
        batch_digest = hashlib.sha256(
            canonical_json_bytes(
                [
                    step,
                    x1.numpy().tolist(),
                    x2.numpy().tolist(),
                    target.numpy().tolist(),
                ]
            )
        ).digest()
        sample_digest = hashlib.sha256(canonical_json_bytes([step, 4])).digest()
        stream_a.update(sample_digest)
        stream_b.update(batch_digest)
        paired_optimizer_step(models, optimizers, configs, x1=x1, x2=x2, target=target)
        occurrences += len(target)
        views += 2 * len(target)
    assert len(seen) == 6
    for erm, js in zip(seen[::2], seen[1::2], strict=True):
        assert erm == js
    assert occurrences == 12
    assert views == 24
    replayed = _smoke_stream_hashes()
    assert (stream_a.hexdigest(), stream_b.hexdigest()) == replayed
    assert replayed == _smoke_stream_hashes()
    assert any(
        not torch.equal(models["dynamic_erm"].state_dict()[key], models["dynamic_js"].state_dict()[key])
        for key in models["dynamic_erm"].state_dict()
    )
