from __future__ import annotations

import math

import numpy as np
import pytest
from pymatgen.core import Lattice, Structure

from xrd_inversion.parameterization import (
    PHYSICAL_PARAMETER_ORDER,
    Q_PARAMETER_ORDER,
    compose_q,
    decode_q,
    encode_q,
    resolve_reference_q,
    split_q,
)
from xrd_inversion.week1_pilot import parameter_vector_to_physical


PARAMETER_CONFIG = {
    "q_bounds": [-1.0, 1.0],
    "du_half_range": 0.01,
    "dv_half_range": 0.01,
    "delta_half_range_deg": 0.2,
    "fwhm_transform": "log",
    "fwhm_min_deg": 0.08,
    "fwhm_max_deg": 0.2,
    "nominal_q": [0.0, 0.0, 0.0, -1.0],
}
FACTORIAL_CONFIG = {"reference_q": [0.0, 0.0, 0.0, -1.0]}
A0 = 4.0
C0 = 6.0


def test_canonical_orders_are_frozen():
    assert Q_PARAMETER_ORDER == ("q_u", "q_v", "q_delta", "q_w")
    assert PHYSICAL_PARAMETER_ORDER == (
        "a_angstrom",
        "c_angstrom",
        "delta_2theta_deg",
        "fwhm_deg",
    )


def test_vectorized_encode_decode_round_trip_preserves_shape_and_float64():
    q = np.asarray(
        [
            [[0.0, 0.0, 0.0, -1.0], [0.5, -0.4, 0.3, 0.2]],
            [[-0.8, 0.7, -0.6, 0.8], [0.1, 0.2, -0.3, -0.4]],
        ],
        dtype=np.float32,
    )
    physical = decode_q(
        q,
        reference_a_angstrom=A0,
        reference_c_angstrom=C0,
        parameter_config=PARAMETER_CONFIG,
    )
    recovered = encode_q(
        physical,
        reference_a_angstrom=A0,
        reference_c_angstrom=C0,
        parameter_config=PARAMETER_CONFIG,
    )
    assert physical.shape == q.shape
    assert recovered.shape == q.shape
    assert physical.dtype == np.float64
    assert recovered.dtype == np.float64
    np.testing.assert_allclose(recovered, q.astype(np.float64), rtol=1e-13, atol=1e-13)


def test_decode_matches_week1_parameter_vector_to_physical():
    structure = Structure(Lattice.tetragonal(A0, C0), ["Si"], [[0, 0, 0]])
    q_batch = np.asarray(
        [
            [0.0, 0.0, 0.0, -1.0],
            [0.4, -0.5, 0.6, 0.25],
            [-0.8, 0.7, -0.3, 0.8],
        ],
        dtype=np.float64,
    )
    decoded = decode_q(
        q_batch,
        reference_a_angstrom=A0,
        reference_c_angstrom=C0,
        parameter_config=PARAMETER_CONFIG,
    )
    expected = []
    for q in q_batch:
        row = parameter_vector_to_physical(q, structure, PARAMETER_CONFIG)
        expected.append(
            [row["a"], row["c"], row["delta_2theta_deg"], row["fwhm_deg"]]
        )
    np.testing.assert_allclose(decoded, np.asarray(expected), rtol=1e-14, atol=1e-14)


def test_absolute_uv_equations_match_encoded_q():
    q = np.asarray([0.35, -0.25, 0.4, 0.6])
    physical = decode_q(
        q,
        reference_a_angstrom=A0,
        reference_c_angstrom=C0,
        parameter_config=PARAMETER_CONFIG,
    )
    a, c, delta, fwhm = physical
    u0 = (2.0 * math.log(A0) + math.log(C0)) / 3.0
    v0 = math.log(C0 / A0)
    u_abs = (2.0 * math.log(a) + math.log(c)) / 3.0
    v_abs = math.log(c / a)
    log_center = 0.5 * (math.log(0.08) + math.log(0.2))
    log_half_range = 0.5 * (math.log(0.2) - math.log(0.08))
    np.testing.assert_allclose(
        [
            (u_abs - u0) / 0.01,
            (v_abs - v0) / 0.01,
            delta / 0.2,
            (math.log(fwhm) - log_center) / log_half_range,
        ],
        q,
        rtol=1e-13,
        atol=1e-13,
    )


def test_split_compose_vectorized_round_trip_and_no_aliasing():
    q = np.arange(24, dtype=np.float64).reshape(3, 2, 4) / 24.0
    theta_s, theta_m = split_q(q)
    assert theta_s.shape == (3, 2, 2)
    assert theta_m.shape == (3, 2, 2)
    recomposed = compose_q(theta_s, theta_m)
    np.testing.assert_array_equal(recomposed, q)
    theta_s[...] = -99.0
    assert not np.any(q == -99.0)


def test_reference_q_is_config_driven_minimum_fwhm_not_q_center():
    reference_q = resolve_reference_q(PARAMETER_CONFIG, FACTORIAL_CONFIG)
    np.testing.assert_array_equal(reference_q, [0.0, 0.0, 0.0, -1.0])
    physical = decode_q(
        reference_q,
        reference_a_angstrom=A0,
        reference_c_angstrom=C0,
        parameter_config=PARAMETER_CONFIG,
    )
    np.testing.assert_allclose(physical, [A0, C0, 0.0, 0.08], rtol=1e-14, atol=1e-14)
    centered = decode_q(
        [0.0, 0.0, 0.0, 0.0],
        reference_a_angstrom=A0,
        reference_c_angstrom=C0,
        parameter_config=PARAMETER_CONFIG,
    )
    assert math.isclose(centered[3], math.sqrt(0.08 * 0.2))


def test_reference_q_rejects_factorial_nominal_drift():
    with pytest.raises(ValueError, match="exactly match"):
        resolve_reference_q(PARAMETER_CONFIG, {"reference_q": [0.0, 0.0, 0.0, 0.0]})


@pytest.mark.parametrize(
    ("operation", "message"),
    [
        (
            lambda: decode_q(
                [0.0, 0.0, 0.0],
                reference_a_angstrom=A0,
                reference_c_angstrom=C0,
                parameter_config=PARAMETER_CONFIG,
            ),
            "shape",
        ),
        (
            lambda: encode_q(
                [A0, C0, 0.0, np.nan],
                reference_a_angstrom=A0,
                reference_c_angstrom=C0,
                parameter_config=PARAMETER_CONFIG,
            ),
            "finite",
        ),
        (
            lambda: encode_q(
                [A0, C0, 0.0, 0.0],
                reference_a_angstrom=A0,
                reference_c_angstrom=C0,
                parameter_config=PARAMETER_CONFIG,
            ),
            "FWHM",
        ),
        (
            lambda: compose_q(np.zeros((2, 2)), np.zeros((3, 2))),
            "identical leading dimensions",
        ),
    ],
)
def test_strict_shape_and_finite_validation(operation, message):
    with pytest.raises(ValueError, match=message):
        operation()
