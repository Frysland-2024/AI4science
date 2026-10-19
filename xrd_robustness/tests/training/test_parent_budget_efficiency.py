from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys

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
    normalized_text_file_hash,
    text_file_hash_variants,
    validate_parent_split,
)
from xrd_robustness.training.objectives import TrainingStepConfig, run_training_step
from xrd_robustness.training import paired as paired_module
from xrd_robustness.training.paired import paired_optimizer_step


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_DIR = PROJECT_ROOT / "manifests" / "parent_budget_efficiency"
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from analyze_parent_budget_matrix import (  # noqa: E402
    CANONICAL_REPORT,
    _analysis_output_paths,
    _assert_pair_provenance,
    _equivalent_parent_estimates,
    _guard_completed_archive,
    _pairing_exposure_record,
    _summarize_pairing_exposure,
)
from run_parent_budget_matrix import (  # noqa: E402
    _complete_pair,
    _expected_pair_metadata,
)
from run_parent_budget_pair import _ensure_eval_cache  # noqa: E402


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


def test_text_config_hash_is_stable_across_line_endings(tmp_path: Path) -> None:
    lf_path = tmp_path / "simulation-lf.json"
    crlf_path = tmp_path / "simulation-crlf.json"
    content = b'{\n  "profiles": []\n}\n'
    lf_path.write_bytes(content)
    crlf_path.write_bytes(content.replace(b"\n", b"\r\n"))

    assert normalized_text_file_hash(lf_path) == normalized_text_file_hash(crlf_path)
    assert normalized_text_file_hash(lf_path) in text_file_hash_variants(crlf_path)


def test_evaluation_cache_binding_uses_the_supplied_simulation_hash(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    split_manifest = data_root / "manifests" / "split_manifest.json"
    split_manifest.parent.mkdir(parents=True)
    split_manifest.write_text("{}", encoding="utf-8")
    cache_root = tmp_path / "cache"

    index, panels, labels = _ensure_eval_cache(
        data_root=data_root,
        cache_root=cache_root,
        split_rows=[],
        simulation={},
        simulation_config_sha256="A" * 64,
        eval_seeds=[],
        profiles=[],
        split="validation",
        input_length=4,
    )
    assert index["bindings"]["simulation_config_sha256"] == "A" * 64
    assert panels == {}
    assert labels.size == 0

    with pytest.raises(ValueError, match="bindings changed"):
        _ensure_eval_cache(
            data_root=data_root,
            cache_root=cache_root,
            split_rows=[],
            simulation={},
            simulation_config_sha256="B" * 64,
            eval_seeds=[],
            profiles=[],
            split="validation",
            input_length=4,
        )


def test_completed_pair_rejects_changed_protocol_or_data_hashes(tmp_path: Path) -> None:
    seed = 20260711
    budget = "10"
    expected = _expected_pair_metadata(
        seed=seed,
        budget=budget,
        data_subset_sha256="D" * 64,
        protocol_config_sha256="P" * 64,
        parent_subset_manifest_sha256="S" * 64,
        ranked_train_file_sha256="R" * 64,
        simulation_config_sha256="C" * 64,
    )
    result_path = tmp_path / f"seed_{seed}" / "parents_984" / "result.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_text(
        json.dumps({"status": "completed", **expected}),
        encoding="utf-8",
    )

    assert _complete_pair(tmp_path, seed, budget, expected=expected)
    changed = {**expected, "simulation_config_sha256": "X" * 64}
    with pytest.raises(ValueError, match="incompatible provenance"):
        _complete_pair(tmp_path, seed, budget, expected=changed)


def test_curve_crossings_use_parent_counts_not_percentages() -> None:
    by_budget = {}
    for budget in ("10", "25", "50", "100"):
        erm_value = 0.5 if budget == "25" else 0.4
        js_value = 0.8 if budget == "10" else 0.45
        by_budget[budget] = {
            "methods": {
                "dynamic_erm": {
                    "mean": {"single_factor_ood_macro_f1": erm_value},
                    "per_seed": {
                        str(seed): {"single_factor_ood_macro_f1": erm_value}
                        for seed in (1, 2, 3, 4, 5)
                    },
                },
                "dynamic_js": {
                    "mean": {"single_factor_ood_macro_f1": js_value},
                    "per_seed": {
                        str(seed): {"single_factor_ood_macro_f1": js_value}
                        for seed in (1, 2, 3, 4, 5)
                    },
                },
            }
        }

    estimates = _equivalent_parent_estimates({"by_budget": by_budget}, complete_matrix=True)
    crossing = estimates["estimates"][0]
    assert crossing["erm_parent_count"] == BUDGETS["25"]
    assert crossing["js_parent_count"] == BUDGETS["10"]
    assert crossing["erm_budget_percent"] == 25
    assert crossing["js_budget_percent"] == 10


def test_pairing_audit_archives_counts_and_stream_hashes() -> None:
    expected = expected_exposure(12, 4)
    run_result = {
        "expected_exposure_per_method": expected,
        "actual_exposure": {
            "optimizer_steps_per_method": expected["optimizer_steps"],
            "parent_occurrences_per_method": expected["parent_occurrences"],
            "views_per_method": expected["views"],
            "expected": expected,
            "full_batches_only": True,
            "same_shared_batch_for_erm_and_js": True,
            "rendered_once_for_pair": True,
            "samples_stream_sha256": "A" * 64,
            "paired_two_view_stream_sha256": "B" * 64,
        },
    }

    record = _pairing_exposure_record(run_result, seed=20260711, budget="10")
    audit = _summarize_pairing_exposure([record])
    assert record["status"] == "verified"
    assert record["parent_count"] == 984
    assert record["samples_stream_sha256"] == "A" * 64
    assert record["paired_two_view_stream_sha256"] == "B" * 64
    assert audit["verified_pairs"] == 1


def test_partial_analysis_stages_outputs_and_protects_completed_archive(tmp_path: Path) -> None:
    output_root = tmp_path / "run"
    staged_dir, staged_report = _analysis_output_paths(
        output_root, None, complete_matrix=False
    )
    assert staged_dir == (output_root / "analysis").resolve()
    assert staged_report != CANONICAL_REPORT

    custom_dir = tmp_path / "custom"
    custom_output, custom_report = _analysis_output_paths(
        output_root, custom_dir, complete_matrix=False
    )
    assert custom_output == custom_dir.resolve()
    assert custom_report == custom_dir.resolve() / "PARENT_BUDGET_EFFICIENCY.md"

    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    results_path = archive_dir / "results.json"
    results_path.write_text(
        json.dumps({
            "status": "completed",
            "provenance": {"input_fingerprint": {"protocol": "old"}},
        }),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="partial analysis cannot replace"):
        _guard_completed_archive(
            results_path,
            archive_dir / "PARENT_BUDGET_EFFICIENCY.md",
            {"status": "partial", "provenance": {"input_fingerprint": {"protocol": "new"}}},
            complete_matrix=False,
        )


def test_analyzer_accepts_only_line_ending_variants_of_legacy_input_hashes() -> None:
    subset_manifest = {"budgets": {"10": {"ordered_parent_ids_sha256": "D" * 64}}}
    fingerprint = {
        "protocol_config_sha256": "P" * 64,
        "subset_manifest_sha256": "S" * 64,
        "ranked_train_file_sha256": "R" * 64,
        "simulation_config_sha256": "C" * 64,
    }
    variants = {
        "protocol_config_sha256": {"P" * 64, "p" * 64},
        "parent_subset_manifest_sha256": {"S" * 64},
        "ranked_train_file_sha256": {"R" * 64},
        "simulation_config_sha256": {"C" * 64, "c" * 64},
    }
    run_result = {
        "training_seed": 20260711,
        "budget_percent": 10,
        "unique_parent_count": 984,
        "data_subset_sha256": "D" * 64,
        "protocol_config_sha256": "p" * 64,
        "parent_subset_manifest_sha256": "S" * 64,
        "ranked_train_file_sha256": "R" * 64,
        "simulation_config_sha256": "c" * 64,
    }

    _assert_pair_provenance(
        run_result,
        seed=20260711,
        budget="10",
        subset_manifest=subset_manifest,
        input_fingerprint=fingerprint,
        input_hash_variants=variants,
    )
    run_result["protocol_config_sha256"] = "Q" * 64
    with pytest.raises(ValueError, match="incompatible provenance"):
        _assert_pair_provenance(
            run_result,
            seed=20260711,
            budget="10",
            subset_manifest=subset_manifest,
            input_fingerprint=fingerprint,
            input_hash_variants=variants,
        )
