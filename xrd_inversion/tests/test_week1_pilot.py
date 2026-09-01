from __future__ import annotations

import math

import numpy as np
from pymatgen.core import Lattice, Structure

from xrd_inversion.week1_pilot import (
    analytic_tetragonal_d,
    fit_gaussian_profile,
    is_conventional_tetragonal_lattice,
    matrix_identifiability,
    offsets_to_lattice,
    parameter_vector_to_physical,
    select_representative_parents,
    summarize_recovery_by_staircase,
)
from xrd_robustness.simulator import render_gaussian_peaks


PARAMETER_CONFIG = {
    "du_half_range": 0.01,
    "dv_half_range": 0.01,
    "delta_half_range_deg": 0.2,
    "fwhm_transform": "log",
    "fwhm_min_deg": 0.08,
    "fwhm_max_deg": 0.2,
}


def test_uv_offsets_preserve_expected_log_coordinates():
    a0, c0 = 4.0, 6.0
    du, dv = 0.007, -0.004
    a, c = offsets_to_lattice(a0, c0, du, dv)
    u0 = (2 * math.log(a0) + math.log(c0)) / 3
    v0 = math.log(c0 / a0)
    assert math.isclose((2 * math.log(a) + math.log(c)) / 3, u0 + du)
    assert math.isclose(math.log(c / a), v0 + dv)


def test_parameter_vector_maps_nominal_measurement_endpoint():
    structure = Structure(Lattice.tetragonal(4.0, 6.0), ["Si"], [[0, 0, 0]])
    result = parameter_vector_to_physical(
        [0.0, 0.0, 0.0, -1.0], structure, PARAMETER_CONFIG
    )
    assert math.isclose(result["a"], 4.0)
    assert math.isclose(result["c"], 6.0)
    assert math.isclose(result["delta_2theta_deg"], 0.0)
    assert math.isclose(result["fwhm_deg"], 0.08)


def test_log_fwhm_center_is_geometric_mean():
    structure = Structure(Lattice.tetragonal(4.0, 6.0), ["Si"], [[0, 0, 0]])
    result = parameter_vector_to_physical(
        [0.0, 0.0, 0.0, 0.0], structure, PARAMETER_CONFIG
    )
    assert math.isclose(result["fwhm_deg"], math.sqrt(0.08 * 0.2))


def test_tetragonal_metric_known_reflections():
    hkls = np.asarray([[1, 0, 0], [0, 0, 1], [1, 1, 0]])
    d = analytic_tetragonal_d(4.0, 6.0, hkls)
    np.testing.assert_allclose(d, [4.0, 6.0, 4.0 / math.sqrt(2.0)])


def test_conventional_cell_gate_is_strict_and_explicit():
    config = {"relative_a_b_tolerance": 1e-6, "angle_tolerance_deg": 1e-6}
    assert is_conventional_tetragonal_lattice(Lattice.tetragonal(4.0, 6.0), config)
    assert not is_conventional_tetragonal_lattice(
        Lattice.from_parameters(4.0, 4.001, 6.0, 90, 90, 90), config
    )


def test_gaussian_fit_recovers_non_grid_center_and_width():
    axis = np.arange(10.0, 80.0 + 0.01, 0.02)
    profile = render_gaussian_peaks(
        [37.073], [100.0], axis, 0.2, normalize=False
    )
    center, fwhm = fit_gaussian_profile(axis, profile)
    assert abs(center - 37.073) < 1e-4
    assert abs(fwhm - 0.2) < 1e-4


def test_representative_selection_is_deterministic_and_train_only():
    rows = []
    for index in range(12):
        rows.append(
            {
                "material_id": f"mp-{index:02d}",
                "formula": "X",
                "split": "validation" if index == 0 else "train",
                "space_group": 75 + index % 4,
                "fingerprint": str(index),
                "a": 3.0 + index * 0.2,
                "c": 4.0 + index * 0.3,
                "c_over_a": (4.0 + index * 0.3) / (3.0 + index * 0.2),
                "nsites": 2 + index,
                "peak_count": 10 + index * 2,
                "restandardized": False,
                "record": {"material_id": f"mp-{index:02d}"},
            }
        )
    first = select_representative_parents(rows, count=5, split="train")
    second = select_representative_parents(rows, count=5, split="train")
    assert [row["material_id"] for row in first] == [
        row["material_id"] for row in second
    ]
    assert all(row["split"] == "train" for row in first)
    assert len({row["material_id"] for row in first}) == 5


def test_identifiability_svd_preserves_range_normalized_sensitivity_scale():
    jacobian = np.asarray([[1000.0, 0.0], [0.0, 1.0], [0.0, 0.0]])
    metrics = matrix_identifiability(jacobian, (0, 1), rank_rcond=1e-6)
    np.testing.assert_allclose(metrics["singular_values"], [1000.0, 1.0])
    assert math.isclose(metrics["condition_number"], 1000.0)
    assert math.isclose(metrics["max_abs_pairwise_cosine"], 0.0)


def test_recovery_gate_requires_every_staircase_to_pass():
    cases = []
    for staircase, parameters, successes in (
        ("S1", ("du", "dv"), (True, False)),
        ("S2", ("du", "dv", "delta"), (True, True)),
        ("S3", ("du", "dv", "delta", "fwhm"), (True, True)),
    ):
        for success in successes:
            cases.append(
                {
                    "staircase": staircase,
                    "success": success,
                    "normalized_absolute_errors": {
                        name: 0.0 if success else 0.2 for name in parameters
                    },
                }
            )
    summary = summarize_recovery_by_staircase(
        cases,
        case_threshold=0.1,
        success_fraction_min=0.75,
        median_max=0.11,
        p90_max=None,
    )
    assert summary["staircases"]["S1"]["status"] == "FAIL"
    assert summary["staircases"]["S2"]["status"] == "PASS"
    assert summary["staircases"]["S3"]["status"] == "PASS"
    assert summary["status"] == "FAIL"
