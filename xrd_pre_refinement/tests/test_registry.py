from pathlib import Path

import pytest

from xrd_pre_refinement.registry import load_registry, validate_family


ROOT = Path(__file__).resolve().parents[1]


def test_demo_and_empty_family_configs_load_and_route_by_metadata():
    router, _ = load_registry(ROOT / "configs" / "registry.json")
    assert router.route("family_template").status == "FAMILY_UNCONFIGURED"
    assert router.route("not_registered", "BaTiO3").status == "FAMILY_UNKNOWN"
    assert router.route("batio3_pilot", "BaTiO3").status == "ROUTED"
    assert router.route("batio3_pilot", "PbTiO3").status == "FAMILY_MISMATCH"


def test_unconfigured_family_cannot_smuggle_candidate_structures():
    family = {
        "family_id": "empty",
        "status": "unconfigured",
        "nominal_composition": {},
        "instrument": {
            "wavelength_angstrom": 1.5406,
            "two_theta_min_deg": 10,
            "two_theta_max_deg": 80,
            "step_deg": 0.02,
        },
        "candidates": [{"candidate_id": "not-allowed"}],
    }
    with pytest.raises(ValueError, match="must not contain"):
        validate_family(family)
