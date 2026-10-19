from __future__ import annotations

import inspect
import math

import numpy as np
import pytest
import torch
from pymatgen.core import Lattice, Structure

from pxrd_forward_loss.measurement_closure import (
    expected_profile,
    measurement_reconstruction_loss,
)
from pxrd_forward_loss.measurement_sampling import (
    sample_q_bank,
    sample_v9_nuisance_bank,
    split_assignment,
    split_q_indices,
)


def _transformed(profile: np.ndarray) -> np.ndarray:
    values = np.asarray(profile, dtype=np.float64)
    return np.log1p(100.0 * values) / math.log(101.0)


def _v9_expected(context, q: tuple[float, float], eta: tuple[float, ...]) -> np.ndarray:
    from xrd_robustness.physics import PhysicsParameters
    from xrd_robustness.simulator import SimulationGrid, ideal_peak_table, simulate_from_peak_table

    root, config, reference, _ = context
    fwd_cfg = config["parameterization"]
    u0 = (2 * math.log(reference.lattice.a) + math.log(reference.lattice.c)) / 3
    v0 = math.log(reference.lattice.c / reference.lattice.a)
    u = u0 + q[0] * fwd_cfg["du_half_range"]
    v = v0 + q[1] * fwd_cfg["dv_half_range"]
    a, c = math.exp(u - v / 3), math.exp(u + 2 * v / 3)
    varied = Structure(
        lattice=Lattice.tetragonal(a, c),
        species=[site.species for site in reference],
        coords=reference.frac_coords,
        coords_are_cartesian=False,
    )
    raw_grid = config["grid"]
    grid = SimulationGrid(
        two_theta_min=float(raw_grid["two_theta_min"]),
        two_theta_max=float(raw_grid["two_theta_max"]),
        step=float(raw_grid["step"]),
        wavelength=float(raw_grid["wavelength_angstrom"]),
    )
    pad = float(raw_grid["peak_calculation_padding_deg"])
    padded = SimulationGrid(
        two_theta_min=grid.two_theta_min - pad,
        two_theta_max=grid.two_theta_max + pad,
        step=grid.step,
        wavelength=grid.wavelength,
    )
    delta, fwhm, amp = eta[:3]
    params = PhysicsParameters(
        delta_2theta_deg=delta,
        fwhm_deg=fwhm,
        background_to_peak_ratio=amp,
        noise_std_ratio=0.0,
        background_type="polynomial",
        severity_level=2,
        zero_shift_active=abs(delta) > 0,
        broadening_active=abs(fwhm - 0.08) > 1e-12,
        background_active=amp > 0,
        noise_active=False,
        background_order=2,
        background_variation=0.0,
        background_floor_fraction=0.10,
        noise_model="poisson_gaussian",
        noise_stage="before_normalization",
        poisson_count_scale=30000.0,
        electronic_noise_std_counts=0.0,
        preferred_orientation_active=False,
    )
    peaks = ideal_peak_table(varied, padded)
    profile = simulate_from_peak_table(
        peaks.positions,
        peaks.intensities,
        params,
        rng_seed=7,
        grid=grid,
        normalize=True,
        reflection_table=peaks,
    )
    return _transformed(profile)


@pytest.mark.parametrize(
    "eta",
    [
        (0.0, 0.08, 0.0),
        (0.045, 0.08, 0.0),
        (0.0, 0.12, 0.0),
        (0.0, 0.08, 0.006),
        (0.045, 0.12, 0.006),
    ],
)
def test_measurement_expected_matches_independent_v9(closure_context, eta):
    _, _, _, forward = closure_context
    q = (0.2, -0.15)
    q_tensor = torch.tensor([q], dtype=torch.float64, device="cuda")
    eta_tensor = torch.tensor([eta], dtype=torch.float64, device="cuda")
    with torch.no_grad():
        torch_profile = expected_profile(forward, q_tensor, eta_tensor)[0].cpu().numpy()
    v9_profile = _v9_expected(closure_context, q, eta)
    difference = torch_profile - v9_profile
    assert float(np.max(np.abs(difference))) <= 2e-6
    assert float(np.sqrt(np.mean(difference**2))) <= 2e-7


def test_clean_closure_and_nuisance_effects(closure_context):
    _, _, _, forward = closure_context
    q = torch.tensor([[0.18, -0.22]], dtype=torch.float64, device="cuda")
    clean_eta = torch.tensor([[0.0, 0.08, 0.0]], dtype=torch.float64, device="cuda")
    full_q = torch.cat((q, torch.zeros((1, 1), device="cuda", dtype=torch.float64), -torch.ones((1, 1), device="cuda", dtype=torch.float64)), dim=1)
    with torch.no_grad():
        clean = expected_profile(forward, q, clean_eta)
        baseline_raw = forward.render(full_q, compatibility=True)
        baseline = torch.log1p(100.0 * baseline_raw) / math.log(101.0)
        shifted = expected_profile(
            forward, q, torch.tensor([[0.04, 0.08, 0.0]], dtype=torch.float64, device="cuda")
        )
        broad = expected_profile(
            forward, q, torch.tensor([[0.0, 0.12, 0.0]], dtype=torch.float64, device="cuda")
        )
        background = expected_profile(
            forward, q, torch.tensor([[0.0, 0.08, 0.006]], dtype=torch.float64, device="cuda")
        )
    assert torch.max(torch.abs(clean - baseline)).item() < 2e-6
    assert torch.linalg.vector_norm(shifted - clean).item() > 1e-3
    assert torch.linalg.vector_norm(broad - clean).item() > 1e-3
    assert torch.linalg.vector_norm(background - clean).item() > 1e-3
    assert torch.isfinite(torch.stack((clean, shifted, broad, background))).all()
    assert torch.min(background) >= 0


def test_simple_linear_background_condition_is_finite_and_distinct(closure_context):
    _, _, _, forward = closure_context
    q = torch.tensor([[0.12, -0.08]], dtype=torch.float64, device="cuda")
    eta = torch.tensor([[0.0, 0.08, 200.0 / 30000.0]], dtype=torch.float64, device="cuda")
    with torch.no_grad():
        v9 = expected_profile(forward, q, eta, background_shape_mode="v9_polynomial")
        simple = expected_profile(
            forward, q, eta, background_shape_mode="simple_linear_counts"
        )
    assert torch.isfinite(simple).all()
    assert torch.max(torch.abs(simple - v9)).item() > 1e-5


def test_autograd_matches_central_finite_difference(closure_context):
    _, _, _, forward = closure_context
    q0 = torch.tensor([[0.18, -0.22]], dtype=torch.float64, device="cuda")
    eta0 = torch.tensor([[0.025, 0.115, 0.006]], dtype=torch.float64, device="cuda")
    target_q = torch.tensor([[0.24, -0.13]], dtype=torch.float64, device="cuda")
    target_eta = torch.tensor([[0.01, 0.105, 0.005]], dtype=torch.float64, device="cuda")
    with torch.no_grad():
        target = expected_profile(forward, target_q, target_eta)

    q = q0.detach().clone().requires_grad_(True)
    eta = eta0.detach().clone().requires_grad_(True)
    loss = torch.mean((expected_profile(forward, q, eta) - target) ** 2)
    grad_q, grad_eta = torch.autograd.grad(loss, (q, eta))
    analytic = torch.cat((grad_q.flatten(), grad_eta.flatten())).detach().cpu().numpy()
    values = torch.cat((q0.flatten(), eta0.flatten())).detach().cpu().numpy()
    steps = np.asarray([1e-4, 1e-4, 1e-4, 1e-5, 1e-4])

    def evaluate(candidate: np.ndarray) -> float:
        q_value = torch.tensor(candidate[:2][None, :], dtype=torch.float64, device="cuda")
        eta_value = torch.tensor(candidate[2:][None, :], dtype=torch.float64, device="cuda")
        with torch.no_grad():
            return float(torch.mean((expected_profile(forward, q_value, eta_value) - target) ** 2).item())

    finite = np.empty_like(analytic)
    for index, step in enumerate(steps):
        plus = values.copy()
        minus = values.copy()
        plus[index] += step
        minus[index] -= step
        finite[index] = (evaluate(plus) - evaluate(minus)) / (2 * step)
    relative = np.abs(analytic - finite) / np.maximum.reduce(
        (np.abs(analytic), np.abs(finite), np.full_like(analytic, 1e-10))
    )
    assert np.isfinite(analytic).all() and np.isfinite(finite).all()
    assert np.max(relative) <= 0.01


def test_expected_profile_is_noise_expectation_not_random_realization(closure_context):
    _, _, _, forward = closure_context
    q = torch.tensor([[0.12, 0.08]], dtype=torch.float64, device="cuda")
    eta = torch.tensor([[0.0, 0.08, 0.005]], dtype=torch.float64, device="cuda")
    with torch.no_grad():
        expected = expected_profile(forward, q, eta)[0].cpu().numpy()
    raw_mean = np.expm1(expected * math.log(101.0)) / 100.0
    rng = np.random.default_rng(20261044)
    counts = rng.poisson(raw_mean * 30000.0)
    observed = counts / max(float(counts.max()), 1.0)
    observed_transformed = _transformed(observed)
    assert np.sqrt(np.mean((observed_transformed - expected) ** 2)) > 0
    assert not np.array_equal(observed_transformed, expected)
    records = []
    for _ in range(64):
        sample = rng.poisson(raw_mean * 30000.0)
        sample = sample / max(float(sample.max()), 1.0)
        records.append(_transformed(sample))
    mc_rmse = float(np.sqrt(np.mean((np.mean(records, axis=0) - expected) ** 2)))
    assert mc_rmse <= 0.02


def test_unknown_nuisance_loss_has_no_truth_input():
    signature = inspect.signature(measurement_reconstruction_loss)
    assert "eta_true" not in signature.parameters
    assert list(signature.parameters)[:4] == [
        "forward_model", "predicted_q", "predicted_eta", "observed_profile"
    ]


def test_lattice_truth_split_and_nuisance_streams_are_independent():
    q_first = sample_q_bank(512, seed=20261041)
    q_repeated = sample_q_bank(512, seed=20261041)
    eta_first = sample_v9_nuisance_bank(512, seed=20261043)
    eta_changed = sample_v9_nuisance_bank(512, seed=20261044)
    split = split_q_indices(512, seed=20261042)
    assignment = split_assignment(split, 512)
    assert np.array_equal(q_first, q_repeated)
    assert not np.array_equal(eta_first, eta_changed)
    assert len(split["train"]) == 358
    assert len(split["validation"]) == 77
    assert len(split["test"]) == 77
    assert len(set(assignment)) == 3
    # The APIs take independent seeds and no q labels enter nuisance sampling.
    assert eta_first.shape == (512, 3)
    assert np.all((-0.06 <= eta_first[:, 0]) & (eta_first[:, 0] <= 0.06))
    assert np.all((0.11 <= eta_first[:, 1]) & (eta_first[:, 1] <= 0.13))
