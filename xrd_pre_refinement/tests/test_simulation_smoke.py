from pathlib import Path

import pytest

from xrd_pre_refinement.registry import load_registry
from xrd_pre_refinement.simulation import simulate_cif


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


@pytest.mark.parametrize("candidate_index", [0, 1])
def test_batio3_cif_symmetry_and_profile_smoke(candidate_index):
    router, config_dir = load_registry(ROOT / "configs" / "registry.json")
    family = router.families["batio3_pilot"]
    candidate = family["candidates"][candidate_index]
    instrument = dict(family["instrument"])
    instrument["_expected_space_group"] = candidate["space_group"]
    pattern = simulate_cif(
        config_dir / candidate["cif_path"],
        instrument,
        family["pilot_measurement"],
        seed=100 + candidate_index,
        robustness_source=REPO / "xrd_robustness" / "src",
    )
    assert pattern.space_group_symbol == candidate["space_group"]["symbol"]
    assert pattern.space_group_number == candidate["space_group"]["number"]
    assert pattern.two_theta_deg.shape == pattern.intensity.shape
    assert pattern.intensity.max() == pytest.approx(1.0)
    assert (pattern.intensity >= 0).all()
