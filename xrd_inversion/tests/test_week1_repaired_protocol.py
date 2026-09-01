from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

from xrd_inversion import week1_pilot as pilot


ROOT = Path(__file__).resolve().parents[2]


def repaired_config() -> dict:
    return pilot.load_json(ROOT / "xrd_inversion" / "configs" / "week1_repaired_smoke.json")


def test_frozen_sobol_is_nested_and_preserves_inactive_parameters() -> None:
    config = repaired_config()
    config["p2"]["recoverability"]["stage_candidate_counts"] = {
        "S1": 8,
        "S2": 16,
        "S3": 32,
    }
    nominal = np.asarray(config["parameterization"]["nominal_q"], dtype=np.float64)
    s1 = pilot.deterministic_sobol_candidates(pilot.STAIRCASES["S1"], config=config)
    s2 = pilot.deterministic_sobol_candidates(pilot.STAIRCASES["S2"], config=config)
    s3 = pilot.deterministic_sobol_candidates(pilot.STAIRCASES["S3"], config=config)

    assert s1.shape == (8, 4)
    assert s2.shape == (16, 4)
    assert s3.shape == (32, 4)
    np.testing.assert_array_equal(s1[:, :2], s3[:8, :2])
    np.testing.assert_array_equal(s2[:, :3], s3[:16, :3])
    np.testing.assert_array_equal(s1[:, 2:], np.repeat(nominal[None, 2:], 8, axis=0))
    np.testing.assert_array_equal(s2[:, 3], np.repeat(nominal[3], 16))


def test_candidate_ranking_is_stable_and_batch_invariant() -> None:
    candidates = np.arange(20, dtype=np.float64).reshape(5, 4)
    profiles = np.asarray(
        [
            [0.0, 0.0],
            [1.0, 0.0],
            [-1.0, 0.0],
            [0.0, 2.0],
            [0.0, -2.0],
        ],
        dtype=np.float64,
    )
    # profile_transform(zeros) is exactly zero. Candidates 1 and 2 tie;
    # candidate ID must break the tie.
    observed = np.zeros(2, dtype=np.float64)
    one = pilot.rank_multistart_candidates(
        candidates, profiles, observed, top_k=3, score_batch_size=1
    )
    many = pilot.rank_multistart_candidates(
        candidates, profiles, observed, top_k=3, score_batch_size=16
    )

    np.testing.assert_array_equal(one[1], np.asarray([0, 1, 2]))
    np.testing.assert_array_equal(one[1], many[1])
    np.testing.assert_array_equal(one[0], many[0])


def test_recoverability_always_reuses_nominal_solution(monkeypatch) -> None:
    config = repaired_config()
    config["p2"]["recoverability"]["top_k"] = 2
    candidates = np.asarray(
        [[-0.5, -0.5, 0.0, -1.0], [0.5, 0.5, 0.0, -1.0]],
        dtype=np.float64,
    )
    candidate_profiles = np.zeros((2, 3), dtype=np.float64)
    nominal_q = np.asarray(config["parameterization"]["nominal_q"], dtype=np.float64)
    nominal_result = SimpleNamespace(
        cost=0.0,
        success=True,
        status=1,
        nfev=1,
        njev=1,
    )

    def fake_optimize_case(model, start_q, active_indices, observed, *, config):
        del model, active_indices, observed, config
        result = SimpleNamespace(cost=1.0, success=True, status=1, nfev=1, njev=1)
        return np.asarray(start_q, dtype=np.float64), result, {"start_q": list(start_q)}

    monkeypatch.setattr(pilot, "optimize_case", fake_optimize_case)
    recovered, result, diagnostics = pilot.optimize_recoverability_case(
        SimpleNamespace(),
        pilot.STAIRCASES["S1"],
        np.zeros(3, dtype=np.float64),
        config=config,
        candidates=candidates,
        candidate_profiles=candidate_profiles,
        nominal_solution=(nominal_q, nominal_result, {"start_q": nominal_q.tolist()}),
    )

    np.testing.assert_array_equal(recovered, nominal_q)
    assert result is nominal_result
    assert diagnostics["nominal_solution_always_reused"] is True
    assert diagnostics["local_refinements"][0]["candidate_kind"] == "nominal"
    assert len(diagnostics["local_refinements"]) == 3


def test_formal_success_fraction_boundary_is_not_rounded() -> None:
    def cases(successes: int) -> list[dict]:
        rows = []
        for index in range(96):
            rows.append(
                {
                    "success": index < successes,
                    "normalized_absolute_errors": {"du": 0.0},
                }
            )
        return rows

    common = {
        "case_threshold": 0.05,
        "success_fraction_min": 0.9,
        "median_max": 0.01,
        "p90_max": 0.025,
    }
    assert pilot.summarize_recovery_cases(cases(86), **common)["status"] == "FAIL"
    assert pilot.summarize_recovery_cases(cases(87), **common)["status"] == "PASS"


def test_formal_config_is_exact_24_by_4_and_gpu_first() -> None:
    config = pilot.load_json(ROOT / "xrd_inversion" / "configs" / "week1_formal_gate.json")
    assert config["run_kind"] == "formal_gate"
    assert config["sampling"] == {
        "representative_parent_count": 24,
        "classical_recovery_parent_count": 24,
        "trials_per_parent": 4,
        "split": "train",
        "selection": "deterministic_robust_feature_maximin_v1",
    }
    assert config["runtime"]["device"] == "cuda"
    assert config["runtime"]["dtype"] == "float64"
    assert config["runtime"]["allow_tf32"] is False
    assert config["runtime"]["allow_autocast"] is False
