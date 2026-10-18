from pathlib import Path

import pytest

from xrd_pre_refinement.parameter_fit import fit_candidate_parameters
from xrd_pre_refinement.registry import load_registry
from xrd_pre_refinement.simulation import simulate_cif


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


@pytest.mark.parametrize("candidate_index", [0, 1])
def test_both_reference_candidates_run_bounded_forward_fit(candidate_index):
    router, config_dir = load_registry(ROOT / "configs" / "registry.json")
    family = router.families["batio3_pilot"]
    instrument = family["instrument"]
    candidates = family["candidates"]
    observation_candidate = next(
        item for item in candidates
        if item["candidate_id"] == family["pilot_observation_candidate"]
    )
    observation_instrument = dict(instrument)
    observation_instrument["_expected_space_group"] = observation_candidate["space_group"]
    observation = simulate_cif(
        config_dir / observation_candidate["cif_path"],
        observation_instrument,
        family["pilot_measurement"],
        seed=812,
        robustness_source=REPO / "xrd_robustness" / "src",
    )

    candidate = candidates[candidate_index]
    fit = fit_candidate_parameters(
        config_dir / candidate["cif_path"],
        observation.intensity,
        instrument,
        family["pilot_measurement"],
        expected_space_group=candidate["space_group"],
        robustness_source=REPO / "xrd_robustness" / "src",
    )

    assert fit["status"] == "LIMITED_FORWARD_FIT_DEMO"
    assert fit["fit_success"] is True
    assert fit["normalized_rmse_after"] < fit["normalized_rmse_before"]
    assert len(fit["fitted_forward_profile"]) == len(observation.intensity)
    assert len(fit["residual_observed_minus_fitted"]) == len(observation.intensity)
    assert fit["parameter_interval"] is None
    for name, value in fit["fitted_values"].items():
        assert fit["search_bounds"][name][0] <= value <= fit["search_bounds"][name][1]
