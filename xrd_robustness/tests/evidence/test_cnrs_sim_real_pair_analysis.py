from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "analyze_cnrs_sim_real_pairs.py"


def load_module():
    spec = importlib.util.spec_from_file_location("cnrs_sim_real_analysis", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cosine_distance_identity_and_orthogonal() -> None:
    module = load_module()
    first = np.asarray([[1.0, 0.0], [1.0, 0.0]])
    second = np.asarray([[1.0, 0.0], [0.0, 1.0]])
    observed = module.cosine_distance(first, second)
    assert np.allclose(observed, [0.0, 1.0])


def test_js_divergence_identity_and_disjoint() -> None:
    module = load_module()
    first = np.asarray([[0.8, 0.2], [1.0, 0.0]])
    second = np.asarray([[0.8, 0.2], [0.0, 1.0]])
    observed = module.js_divergence(first, second)
    assert math.isclose(float(observed[0]), 0.0, abs_tol=1e-12)
    assert math.isclose(float(observed[1]), math.log(2.0), rel_tol=1e-12)


def test_true_margin() -> None:
    module = load_module()
    probabilities = np.asarray([[0.7, 0.2, 0.1], [0.3, 0.6, 0.1]])
    labels = np.asarray([0, 1])
    observed = module.true_margin(probabilities, labels)
    assert np.allclose(observed, [0.5, 0.3])


def test_seed_summary_uses_js_minus_erm_direction() -> None:
    module = load_module()
    rows = []
    for method_id, method_name, gap in (
        (module.ERM_ID, "Dynamic ERM", 0.4),
        (module.JS_ID, "JS Consistency", 0.2),
    ):
        rows.append(
            {
                "seed": 1,
                "method_id": method_id,
                "method_name": method_name,
                "embedding_cosine_distance": gap,
                "prediction_js_divergence": gap,
                "prediction_flip": gap,
                "true_probability_drop": gap,
                "true_margin_drop": gap,
                "sim_correct": 1.0,
                "real_correct": 1.0,
            }
        )
    _, paired = module.summarize(rows)
    assert len(paired) == 1
    assert math.isclose(
        paired[0]["delta_embedding_cosine_distance_js_minus_erm"], -0.2
    )
    assert math.isclose(
        paired[0]["delta_prediction_js_divergence_js_minus_erm"], -0.2
    )
