import importlib.util
from pathlib import Path
import unittest

import numpy as np
import torch
from torch import nn

from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.simulation_interfaces import PeakTable
from xrd_robustness.structure_data import CRYSTAL_SYSTEMS
from xrd_robustness.view_manifest import build_parameter_stream, index_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "train_v7_batched_test", PROJECT_ROOT / "scripts" / "train_v7.py"
)
assert SPEC and SPEC.loader
TRAIN_V7 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRAIN_V7)


class TinyEvaluationModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        torch.manual_seed(11)
        self.linear = nn.Linear(16, 7)
        self.forward_calls = 0

    def forward(self, x):
        self.forward_calls += 1
        pooled = torch.nn.functional.adaptive_avg_pool1d(x.unsqueeze(1), 16).squeeze(1)
        embedding = torch.tanh(pooled)
        return {
            "logits": self.linear(embedding),
            "pooled_embedding": embedding,
            "main_tokens": embedding.unsqueeze(1),
            "prior_tokens": None,
        }


def _range(value):
    return {
        "distribution": "fixed",
        "min_value": value,
        "max_value": value,
        "apply_probability": 1.0,
    }


def _table(scale):
    return PeakTable(
        positions=np.asarray([20.0, 30.0, 40.0]),
        intensities=np.asarray([100.0, 60.0, 30.0]) * scale,
        hkls=np.asarray([[1, 0, 0], [0, 1, 0], [1, 1, 0]]),
        multiplicities=np.asarray([2, 2, 4]),
        reciprocal_vectors=np.asarray(
            [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0]]
        ),
        reflection_peak_indices=np.asarray([0, 1, 2]),
    )


class BatchedEvaluationTests(unittest.TestCase):
    def test_batching_preserves_predictions_and_reduces_forward_calls(self):
        sampler = PhysicsParameterSampler.from_mapping(
            {
                "run_seed": 17,
                "profiles": {
                    "test": {
                        "severity_level": 1,
                        "background_type": "flat",
                        "delta_2theta_deg": _range(0.0),
                        "fwhm_deg": _range(0.08),
                        "background_to_peak_ratio": _range(0.0),
                        "noise_std_ratio": _range(0.0),
                        "preferred_orientation": {
                            "enabled": True,
                            "model": "march_dollase",
                            "distribution": "fixed",
                            "min_value": 0.8,
                            "max_value": 0.8,
                            "apply_probability": 1.0,
                        },
                    }
                },
            }
        )
        ids = [f"material-{index:02d}" for index in range(14)]
        records = {
            material_id: {"crystal_system": CRYSTAL_SYSTEMS[index % 7]}
            for index, material_id in enumerate(ids)
        }
        peaks = {material_id: _table(1.0 + index / 20.0) for index, material_id in enumerate(ids)}
        rows = build_parameter_stream(
            ids, sampler, profile="test", epochs=1, steps_per_epoch=1, split="test"
        )
        factory = OnlineViewFactory(sampler)
        model = TinyEvaluationModel().eval()
        sequential = TRAIN_V7._predict_paired_views(
            model,
            ids,
            records,
            index=index_manifest(rows),
            peaks=peaks,
            factory=factory,
            device=torch.device("cpu"),
            evaluation_batch_size=1,
        )
        sequential_calls = model.forward_calls
        model.forward_calls = 0
        batched = TRAIN_V7._predict_paired_views(
            model,
            ids,
            records,
            index=index_manifest(rows),
            peaks=peaks,
            factory=factory,
            device=torch.device("cpu"),
            evaluation_batch_size=7,
        )
        np.testing.assert_array_equal(sequential["labels"], batched["labels"])
        np.testing.assert_array_equal(sequential["predictions"], batched["predictions"])
        np.testing.assert_allclose(
            sequential["probabilities"], batched["probabilities"], rtol=1e-6, atol=1e-6
        )
        self.assertEqual(sequential_calls, 28)
        self.assertEqual(model.forward_calls, 4)


if __name__ == "__main__":
    unittest.main()
