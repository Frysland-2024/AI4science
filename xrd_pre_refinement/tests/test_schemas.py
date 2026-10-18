import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from xrd_pre_refinement.baseline import rank_single_phase_templates
from xrd_pre_refinement.observation import parse_observation
from xrd_pre_refinement.reporting import build_report


ROOT = Path(__file__).resolve().parents[1]


def _schema(name):
    schema = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_empty_and_demo_family_configs_validate_and_track_structure_hashes():
    index = json.loads((ROOT / "configs" / "registry.json").read_text(encoding="utf-8"))
    _schema("registry_index.schema.json").validate(index)
    validator = _schema("family_registry.schema.json")
    for path in sorted((ROOT / "configs" / "families").glob("*.json")):
        family = json.loads(path.read_text(encoding="utf-8"))
        validator.validate(family)
        for candidate in family["candidates"]:
            cif_path = (ROOT / "configs" / candidate["cif_path"]).resolve()
            digest = hashlib.sha256(cif_path.read_bytes()).hexdigest()
            assert digest == candidate["cif_source"]["sha256"]


def test_xrd_observation_schema_and_python_parser_validate_grid_integrity():
    payload = {
        "schema_version": "xrd-observation-v1",
        "sample_id": "simulated-fixture",
        "family_id": None,
        "nominal_composition": None,
        "instrument": {
            "radiation": "Cu Kα1",
            "wavelength_angstrom": 1.5406,
            "two_theta_min_deg": 10.0,
            "two_theta_max_deg": 80.0,
            "step_deg": 0.02,
        },
        "two_theta_deg": [10.0, 10.02, 10.04],
        "intensity": [0.1, 1.0, 0.2],
    }
    _schema("xrd_observation.schema.json").validate(payload)
    observation = parse_observation(payload)
    assert observation.sample_id == "simulated-fixture"
    assert observation.two_theta_deg.shape == observation.intensity.shape
    payload["intensity"] = [0.1, 1.0]
    with pytest.raises(ValueError, match="same length"):
        parse_observation(payload)


def test_engineering_report_shape_validates_against_report_schema():
    ranked = rank_single_phase_templates(
        [1.0, 0.0, 0.0],
        {"A": [0.9, 0.1, 0.0]},
        [{
            "candidate_id": "A",
            "phase_id": "fixture phase",
            "composition": "ABO3",
            "space_group": {"symbol": "P1", "number": 1},
            "cif_path": "A.cif",
            "cif_source": {"citation": "fixture", "url": "fixture", "sha256": "fixture"},
            "parameterization": {"reference_values": {"a_angstrom": 4.0}},
        }],
    )
    report = build_report(
        sample_id="schema-fixture",
        route={"status": "ROUTED", "family_id": "fixture", "composition_status": "MATCH", "review_required": False, "message": "fixture"},
        ranked_candidates=ranked,
        observed_profile=[1.0, 0.0, 0.0],
        two_theta_deg=[10.0, 10.02, 10.04],
        model_id="fixture",
    )
    _schema("pre_refinement_report.schema.json").validate(report)
    forward = report["single_phase_hypotheses"][0]["forward_check"]
    assert forward["reconstructed_profile"] == [0.9, 0.1, 0.0]
    assert forward["residual_observed_minus_reconstructed"] == pytest.approx([0.1, -0.1, 0.0])


def test_pilot_reports_validate_and_main_report_contains_two_candidate_fits():
    validator = _schema("pre_refinement_report.schema.json")
    output = ROOT / "reports" / "pilot_run"
    main = json.loads((output / "pre_refinement_report.json").read_text(encoding="utf-8"))
    mixture = json.loads((output / "synthetic_mix_stress_report.json").read_text(encoding="utf-8"))
    validator.validate(main)
    validator.validate(mixture)

    hypotheses = main["single_phase_hypotheses"]
    assert len(hypotheses) >= 2
    target_length = len(main["observation"]["intensity"])
    for hypothesis in hypotheses[:2]:
        fit = hypothesis["limited_forward_fit"]
        assert fit["fit_success"] is True
        assert fit["normalized_rmse_after"] < fit["normalized_rmse_before"]
        assert len(fit["fitted_forward_profile"]) == target_length
        assert len(fit["residual_observed_minus_fitted"]) == target_length
