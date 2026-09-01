from __future__ import annotations

from pathlib import Path

import numpy as np
from pymatgen.core import Lattice, Structure

from xrd_inversion.factorial_dataset import (
    FactorialBlockDataset,
    FactorialTensorBundle,
    build_eval_manifest,
    build_factorial_manifest,
    corner_q_values,
    training_channel_statistics,
    validate_factorial_manifest,
    validate_tensor_bundle,
)
from xrd_inversion.week1_pilot import ParentContext


def _context(material_id: str, a: float) -> ParentContext:
    structure = Structure(Lattice.tetragonal(a, 1.5 * a), ["Si"], [[0, 0, 0]])
    return ParentContext(
        material_id=material_id,
        formula="Si",
        split="train",
        space_group=123,
        fingerprint=f"fingerprint-{material_id}",
        structure=structure,
        peak_count=10,
        cache_path=Path(f"{material_id}.npz"),
        cache_sha256="0" * 64,
    )


def _config() -> dict:
    return {
        "dataset_seed": 2026090101,
        "parameterization": {
            "q_bounds": [-1.0, 1.0],
            "truth_q_range": [-0.8, 0.8],
            "du_half_range": 0.01,
            "dv_half_range": 0.01,
            "delta_half_range_deg": 0.2,
            "fwhm_transform": "log",
            "fwhm_min_deg": 0.08,
            "fwhm_max_deg": 0.2,
            "nominal_q": [0.0, 0.0, 0.0, -1.0],
        },
        "grid": {"two_theta_min": 10.0, "two_theta_max": 80.0, "step": 0.02},
        "factorial": {
            "blocks_per_parent": 2,
            "training_blocks_per_parent": 1,
            "reference_q": [0.0, 0.0, 0.0, -1.0],
            "corner_order": ["x11", "x12", "x21", "x22"],
        },
        "execution_boundary": {
            "validation_access": False,
            "test_access": False,
            "independent_renderer_access": False,
        },
    }


def test_manifest_freezes_complete_train_only_2x2_blocks() -> None:
    contexts = [_context("p1", 4.0), _context("p2", 5.0)]
    selected = [
        {"selection_rank": index} for index in range(1, len(contexts) + 1)
    ]
    manifest = build_factorial_manifest(
        contexts,
        selected,
        {"structure_splits_retained": ["train"]},
        _config(),
    )
    validate_factorial_manifest(manifest)
    assert manifest["counts"] == {
        "parents": 2,
        "blocks_per_parent": 2,
        "training_blocks_per_parent": 1,
        "evaluation_blocks_per_parent": 1,
        "blocks": 4,
        "spectra": 16,
    }
    assert {row["split"] for row in manifest["parents"]} == {"train"}
    assert [row["subset"] for row in manifest["blocks"]].count("training") == 2
    assert [row["subset"] for row in manifest["blocks"]].count("sanity_eval") == 2

    for block in manifest["blocks"]:
        q = corner_q_values(block)
        np.testing.assert_array_equal(q[0, 0, :2], q[0, 1, :2])
        np.testing.assert_array_equal(q[1, 0, :2], q[1, 1, :2])
        np.testing.assert_array_equal(q[0, 0, 2:], q[1, 0, 2:])
        np.testing.assert_array_equal(q[0, 1, 2:], q[1, 1, 2:])

    evaluation = build_eval_manifest(manifest)
    assert evaluation["scope"] == "train_parent_internal_unseen_intervention_sanity_only"
    assert evaluation["formal_generalization_claim"] is False
    assert evaluation["counts"] == {"blocks": 2, "spectra": 8}


def test_block_bundle_preserves_channel_and_pair_axes() -> None:
    rng = np.random.default_rng(5)
    observed = rng.normal(size=(3, 2, 2, 7)).astype(np.float32)
    reference = rng.normal(size=(3, 2, 2, 7)).astype(np.float32)
    inputs = np.stack((observed, reference, observed - reference), axis=3)
    theta_s_state = rng.uniform(-0.8, 0.8, size=(3, 2, 2)).astype(np.float64)
    theta_m_state = rng.uniform(-0.8, 0.8, size=(3, 2, 2)).astype(np.float64)
    theta_s = np.repeat(theta_s_state[:, :, None, :], 2, axis=2)
    theta_m = np.repeat(theta_m_state[:, None, :, :], 2, axis=1)
    bundle = FactorialTensorBundle(
        inputs=inputs,
        theta_s=theta_s,
        theta_m=theta_m,
        parent_id=np.asarray(["p1", "p1", "p2"]),
        parent_a=np.asarray([4.0, 4.0, 5.0]),
        parent_c=np.asarray([6.0, 6.0, 7.5]),
        block_id=np.asarray([0, 1, 0]),
        subset=np.asarray(["training", "training", "sanity_eval"]),
        manifest_sha256="a" * 64,
    )
    validate_tensor_bundle(bundle)
    mean, std = training_channel_statistics(bundle, [0, 1])
    dataset = FactorialBlockDataset(bundle, [0, 1], mean, std)
    sample = dataset[0]
    assert sample["inputs"].shape == (2, 2, 3, 7)
    assert sample["theta_s"].shape == (2, 2, 2)
    assert sample["theta_m"].shape == (2, 2, 2)
    assert sample["parent_id"] == "p1"
