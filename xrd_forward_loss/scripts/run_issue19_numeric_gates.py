"""P1/P2 differentiability, nuisance identifiability and smoke Gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import scipy.optimize
import torch
import torch.nn.functional as F
from pymatgen.core import Lattice, Structure

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / "xrd_inversion" / "src"),
    str(ROOT / "xrd_robustness" / "src"),
    str(ROOT / "xrd_forward_loss" / "src"),
]
from pxrd_forward_loss.measurement_closure import expected_profile  # noqa: E402
from xrd_inversion.gpu_forward import CachedTetragonalGPUForward  # noqa: E402
from xrd_robustness.physics import PhysicsParameters  # noqa: E402
from xrd_robustness.simulator import SimulationGrid, ideal_peak_table, simulate_from_peak_table  # noqa: E402


def transform(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    return np.log1p(100.0 * values) / math.log(101.0)


def q_to_lattice(structure: Structure, q: np.ndarray, forward_config: dict) -> tuple[float, float]:
    pc = forward_config["parameterization"]
    u0 = (2.0 * math.log(structure.lattice.a) + math.log(structure.lattice.c)) / 3.0
    v0 = math.log(structure.lattice.c / structure.lattice.a)
    u = u0 + float(q[0]) * float(pc["du_half_range"])
    v = v0 + float(q[1]) * float(pc["dv_half_range"])
    return math.exp(u - v / 3.0), math.exp(u + 2.0 * v / 3.0)


def structure_at_q(structure: Structure, q: np.ndarray, forward_config: dict) -> Structure:
    a, c = q_to_lattice(structure, q, forward_config)
    return Structure(
        lattice=Lattice.tetragonal(a, c),
        species=[site.species for site in structure],
        coords=structure.frac_coords,
        coords_are_cartesian=False,
    )


def expected_q_eta(z: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    q = 0.8 * z[:2]
    delta = 0.06 * z[2]
    fwhm = 0.08 + 0.05 * (z[3] + 1.0) / 2.0
    bg = 0.01 * (z[4] + 1.0) / 2.0
    eta = torch.stack((delta, fwhm, bg))
    return q[None, :], eta[None, :]


def optimize_profile(
    forward,
    target: torch.Tensor,
    start: np.ndarray,
    *,
    fit_nuisance: bool,
    maxiter: int = 80,
) -> dict:
    size = 5 if fit_nuisance else 2
    bounds = [(-1.0, 1.0)] * size if fit_nuisance else [(-0.8, 0.8)] * 2

    def objective(values: np.ndarray):
        variable = torch.tensor(values, dtype=torch.float64, device="cuda", requires_grad=True)
        if fit_nuisance:
            q, eta = expected_q_eta(variable)
        else:
            q = variable[None, :]
            eta = torch.tensor([[0.0, 0.08, 0.0]], dtype=torch.float64, device="cuda")
        prediction = expected_profile(forward, q, eta)
        loss = F.mse_loss(prediction, target)
        gradient = torch.autograd.grad(loss, variable)[0]
        return float(loss.detach().item()), gradient.detach().cpu().numpy().astype(np.float64)

    result = scipy.optimize.minimize(
        objective,
        np.asarray(start, dtype=np.float64),
        method="L-BFGS-B",
        jac=True,
        bounds=bounds,
        options={"maxiter": maxiter, "ftol": 1e-12, "gtol": 1e-9, "maxls": 30},
    )
    if fit_nuisance:
        q, eta = expected_q_eta(torch.tensor(result.x, dtype=torch.float64, device="cuda"))
        q_value = q.detach().cpu().numpy()[0]
        eta_value = eta.detach().cpu().numpy()[0]
        return {
            "success": bool(result.success),
            "message": str(result.message),
            "iterations": int(result.nit),
            "evaluations": int(result.nfev),
            "loss": float(result.fun),
            "z": result.x.tolist(),
            "q": q_value.tolist(),
            "eta": eta_value.tolist(),
            "at_bound": bool(np.any(np.isclose(np.abs(result.x), 1.0, atol=1e-5))),
        }
    return {
        "success": bool(result.success),
        "message": str(result.message),
        "iterations": int(result.nit),
        "evaluations": int(result.nfev),
        "loss": float(result.fun),
        "q": result.x.tolist(),
        "at_bound": bool(np.any(np.isclose(np.abs(result.x), 0.8, atol=1e-5))),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--p0", required=True, type=Path)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("xrd_forward_loss/measurement_closure/configs/issue19_batio3_v2_numericrun.json"),
    )
    args = parser.parse_args()
    if not args.output.exists():
        raise FileNotFoundError(args.output)
    if (args.output / "p1_numeric_gates.json").exists():
        raise FileExistsError("p1_numeric_gates.json already exists; use a new run directory")
    p0 = json.loads(args.p0.read_text(encoding="utf-8"))
    if not p0.get("passed"):
        raise RuntimeError("P0 did not pass; P1/P2 are not authorized to continue")
    cfg_path = args.config if args.config.is_absolute() else ROOT / args.config
    closure_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    forward_config_path = ROOT / closure_cfg["forward"]["config"]
    forward_cfg = json.loads(forward_config_path.read_text(encoding="utf-8"))
    structure = Structure.from_file(ROOT / closure_cfg["source"]["cif"])
    forward = CachedTetragonalGPUForward(
        structure,
        grid_config=forward_cfg["grid"],
        parameter_config=forward_cfg["parameterization"],
        device="cuda",
        dtype=torch.float64,
    )
    numeric_started = time.perf_counter()

    grid_cfg = forward_cfg["grid"]
    grid = SimulationGrid(
        two_theta_min=float(grid_cfg["two_theta_min"]),
        two_theta_max=float(grid_cfg["two_theta_max"]),
        step=float(grid_cfg["step"]),
        wavelength=float(grid_cfg["wavelength_angstrom"]),
    )
    pad = float(grid_cfg["peak_calculation_padding_deg"])
    padded = SimulationGrid(
        two_theta_min=grid.two_theta_min - pad,
        two_theta_max=grid.two_theta_max + pad,
        step=grid.step,
        wavelength=grid.wavelength,
    )

    q_true = np.asarray([0.20, -0.15], dtype=np.float64)
    eta_true = np.asarray([0.04, 0.12, 0.006], dtype=np.float64)
    q_tensor = torch.tensor(q_true[None, :], device="cuda", dtype=torch.float64)
    eta_tensor = torch.tensor(eta_true[None, :], device="cuda", dtype=torch.float64)
    with torch.no_grad():
        target = expected_profile(forward, q_tensor, eta_tensor)

    # Pymatgen/V9 independent measurement-operator checks: clean, shift,
    # broadening, smooth background, and all active operators together.
    cases = [
        ("clean", (0.0, 0.08, 0.0)),
        ("shift", (0.045, 0.08, 0.0)),
        ("broadening", (0.0, 0.12, 0.0)),
        ("background", (0.0, 0.08, 0.006)),
        ("combined", (0.045, 0.12, 0.006)),
    ]
    v9_rows = []
    for name, eta_values in cases:
        eta_case = torch.tensor([eta_values], device="cuda", dtype=torch.float64)
        with torch.no_grad():
            predicted = expected_profile(forward, q_tensor, eta_case)[0].cpu().numpy()
        varied = structure_at_q(structure, q_true, forward_cfg)
        params = PhysicsParameters(
            delta_2theta_deg=eta_values[0],
            fwhm_deg=eta_values[1],
            background_to_peak_ratio=eta_values[2],
            noise_std_ratio=0.0,
            background_type="polynomial",
            severity_level=2,
            zero_shift_active=eta_values[0] != 0,
            broadening_active=eta_values[1] != 0.08,
            background_active=eta_values[2] > 0,
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
        v9 = simulate_from_peak_table(
            peaks.positions,
            peaks.intensities,
            params,
            rng_seed=17,
            grid=grid,
            normalize=True,
            reflection_table=peaks,
        )
        delta = predicted - transform(v9)
        v9_rows.append(
            {
                "case": name,
                "max_abs_error": float(np.max(np.abs(delta))),
                "rmse": float(np.sqrt(np.mean(delta**2))),
            }
        )

    # Autograd/central-FD end-to-end scalar mismatch gradient for all q/eta
    # parameters. The fixed target has different q and eta, avoiding a
    # vacuous zero-loss derivative check.
    q0 = torch.tensor([[0.18, -0.22]], dtype=torch.float64, device="cuda", requires_grad=True)
    eta0 = torch.tensor([[0.025, 0.115, 0.006]], dtype=torch.float64, device="cuda", requires_grad=True)
    q_target = torch.tensor([[0.24, -0.13]], dtype=torch.float64, device="cuda")
    eta_target = torch.tensor([[0.01, 0.105, 0.005]], dtype=torch.float64, device="cuda")
    with torch.no_grad():
        profile_target = expected_profile(forward, q_target, eta_target)
    loss0 = F.mse_loss(expected_profile(forward, q0, eta0), profile_target)
    grad_q, grad_eta = torch.autograd.grad(loss0, (q0, eta0))
    gradient = torch.cat((grad_q.flatten(), grad_eta.flatten())).detach().cpu().numpy()
    base_values = np.concatenate((q0.detach().cpu().numpy().ravel(), eta0.detach().cpu().numpy().ravel()))
    fd_steps = np.asarray([1e-4, 1e-4, 1e-4, 1e-5, 1e-4])

    def scalar_loss(values: np.ndarray) -> float:
        qv = torch.tensor(values[:2][None, :], dtype=torch.float64, device="cuda")
        etav = torch.tensor(values[2:][None, :], dtype=torch.float64, device="cuda")
        with torch.no_grad():
            return float(F.mse_loss(expected_profile(forward, qv, etav), profile_target).item())

    fd = np.zeros(5, dtype=np.float64)
    for index, step in enumerate(fd_steps):
        plus = base_values.copy()
        minus = base_values.copy()
        plus[index] += step
        minus[index] -= step
        fd[index] = (scalar_loss(plus) - scalar_loss(minus)) / (2.0 * step)
    relative = np.abs(gradient - fd) / np.maximum.reduce(
        (np.abs(gradient), np.abs(fd), np.full(5, 1e-10))
    )

    # Scale all five active coordinates to their frozen ranges, then compute
    # the local forward Jacobian, singular values, and normalized correlations.
    z_true = np.asarray(
        [
            q_true[0] / 0.8,
            q_true[1] / 0.8,
            eta_true[0] / 0.06,
            2 * (eta_true[1] - 0.08) / 0.05 - 1,
            2 * eta_true[2] / 0.01 - 1,
        ],
        dtype=np.float64,
    )
    z_tensor = torch.tensor(z_true, dtype=torch.float64, device="cuda")

    def z_profile(z):
        q, eta = expected_q_eta(z)
        return expected_profile(forward, q, eta)[0]

    with torch.enable_grad():
        jac = torch.func.jacfwd(z_profile)(z_tensor).detach().cpu().numpy()
    column_norms = np.linalg.norm(jac, axis=0)
    normalized_jac = jac / np.maximum(column_norms[None, :], 1e-15)
    correlations = normalized_jac.T @ normalized_jac
    singular_values = np.linalg.svd(jac, compute_uv=False)
    condition = float(singular_values[0] / max(singular_values[-1], 1e-15))
    max_correlation = float(np.max(np.abs(correlations - np.eye(5))))

    # Oracle diagnostic: true q and eta are used only to construct a known
    # expected target and to check the gradient at its exact generating point.
    q_oracle = torch.tensor(q_true[None, :], dtype=torch.float64, device="cuda", requires_grad=True)
    oracle_loss = F.mse_loss(expected_profile(forward, q_oracle, eta_tensor), target)
    oracle_gradient = torch.autograd.grad(oracle_loss, q_oracle)[0].detach().cpu().numpy()[0]

    # Mismatched legacy clean-vs-observed diagnostic and a bounded q-only fit.
    mismatch_fit = optimize_profile(forward, target, q_true.copy(), fit_nuisance=False)
    mismatch_q = np.asarray(mismatch_fit["q"])
    mismatch_gradient_var = torch.tensor(q_true, dtype=torch.float64, device="cuda", requires_grad=True)
    eta_ref = torch.tensor([[0.0, 0.08, 0.0]], dtype=torch.float64, device="cuda")
    mismatch_loss = F.mse_loss(expected_profile(forward, mismatch_gradient_var[None, :], eta_ref), target)
    mismatch_gradient = torch.autograd.grad(mismatch_loss, mismatch_gradient_var)[0].detach().cpu().numpy()

    # Non-oracle profile fitting: optimization sees only expected input profile
    # and candidate q/eta. Multiple distinct initial values expose degeneracies.
    starts = [
        np.asarray([0.60, -0.50, -0.70, -0.80, -0.60]),
        np.asarray([-0.50, 0.50, 0.70, 0.80, 0.80]),
    ]
    profile_fits = [optimize_profile(forward, target, start, fit_nuisance=True) for start in starts]
    profile_rows = []
    for fit in profile_fits:
        q_error = np.abs(np.asarray(fit["q"]) - q_true)
        normalized_eta_error = np.abs(
            np.asarray(fit["z"])[2:] - z_true[2:]
        )
        profile_rows.append(
            {
                **fit,
                "q_abs_error": q_error.tolist(),
                "q_max_abs_error": float(np.max(q_error)),
                "eta_normalized_abs_error": normalized_eta_error.tolist(),
                "eta_normalized_max_abs_error": float(np.max(normalized_eta_error)),
            }
        )

    # Fixed-seed Poisson expectation audit. Normalizing each random draw means
    # one realization cannot equal the deterministic transformed expectation.
    raw_mean = np.expm1(target.detach().cpu().numpy()[0] * math.log(101.0)) / 100.0
    rng = np.random.default_rng(20261044)
    samples = []
    single = None
    for _ in range(64):
        counts = rng.poisson(raw_mean * 30000.0)
        noisy = counts / max(float(np.max(counts)), 1.0)
        transformed_noisy = transform(noisy)
        samples.append(transformed_noisy)
        if single is None:
            single = transformed_noisy
    mc_mean = np.mean(samples, axis=0)
    mc_rmse = float(np.sqrt(np.mean((mc_mean - target.detach().cpu().numpy()[0]) ** 2)))
    single_rmse = float(np.sqrt(np.mean((single - target.detach().cpu().numpy()[0]) ** 2)))

    p1_gate_thresholds = closure_cfg["gates"]
    gates = {
        "p0_passed": bool(p0["passed"]),
        "v9_measurement_profile_parity_passed": bool(
            max(row["max_abs_error"] for row in v9_rows)
            <= p1_gate_thresholds["p1_measurement_profile_max_abs_max"]
            and max(row["rmse"] for row in v9_rows)
            <= p1_gate_thresholds["p1_measurement_profile_rmse_max"]
        ),
        "gradient_fd_passed": bool(np.max(relative) <= p1_gate_thresholds["p1_gradient_fd_relative_max"]),
        "nuisance_local_identifiability_passed": bool(
            np.isfinite(condition)
            and condition <= p1_gate_thresholds["p1_unknown_nuisance_jacobian_condition_max"]
            and max_correlation <= p1_gate_thresholds["p1_unknown_nuisance_max_abs_column_correlation"]
        ),
        "non_oracle_profile_recovery_passed": bool(
            all(
                row["q_max_abs_error"] <= p1_gate_thresholds["p1_profile_recovery_q_max_abs"]
                and row["eta_normalized_max_abs_error"]
                <= p1_gate_thresholds["p1_profile_recovery_nuisance_normalized_max_abs"]
                and not row["at_bound"]
                for row in profile_rows
            )
        ),
        "noise_expectation_mc_passed": bool(mc_rmse <= p1_gate_thresholds["p2_expected_noise_mc_rmse_max"]),
    }
    gates["all_physics_and_unknown_nuisance_gates_passed"] = all(gates.values())

    report = {
        "stage": "P1_P2_NUMERICAL_GATES",
        "source_config": str(cfg_path.resolve().relative_to(ROOT)),
        "source_config_sha256": hashlib.sha256(cfg_path.read_bytes()).hexdigest(),
        "p0_reference": str(args.p0.resolve().relative_to(ROOT)),
        "target_definition": "deterministic expected profile only; no sampled detector noise is fitted",
        "unknown_nuisance_degrees_of_freedom": {
            "q": ["du", "dv"],
            "eta": ["2theta zero shift", "FWHM", "background amplitude"],
            "count_noise": "stochastic observation process, not an estimated realization",
            "scale": "excluded after per-profile maximum normalization; unidentifiable gauge",
        },
        "v9_expected_profile_parity": {"thresholds": {"max_abs": 2e-6, "rmse": 2e-7}, "cases": v9_rows},
        "gradient_finite_difference": {
            "coordinates": ["du", "dv", "delta_deg", "fwhm_deg", "background_ratio"],
            "autograd": gradient.tolist(),
            "central_finite_difference": fd.tolist(),
            "steps": fd_steps.tolist(),
            "relative_errors": relative.tolist(),
            "max_relative_error": float(np.max(relative)),
            "passed": gates["gradient_fd_passed"],
        },
        "oracle_diagnostic": {
            "eta_true_used_only_for_diagnostic": True,
            "q_true": q_true.tolist(),
            "eta_true": eta_true.tolist(),
            "loss_at_truth": float(oracle_loss.detach().item()),
            "q_gradient_at_truth": oracle_gradient.tolist(),
        },
        "mismatched_clean_vs_observed": {
            "clean_eta_reference": [0.0, 0.08, 0.0],
            "observed_expected_eta": eta_true.tolist(),
            "loss_at_true_q": float(mismatch_loss.detach().item()),
            "gradient_du_dv_at_true_q": mismatch_gradient.tolist(),
            "q_only_best_fit": mismatch_fit,
            "q_bias": (mismatch_q - q_true).tolist(),
            "true_lattice_angstrom": list(q_to_lattice(structure, q_true, forward_cfg)),
            "biased_lattice_angstrom": list(q_to_lattice(structure, mismatch_q, forward_cfg)),
            "descent_gradient_bias_cosine": float(
                np.dot(-mismatch_gradient, mismatch_q - q_true)
                / max(np.linalg.norm(mismatch_gradient) * np.linalg.norm(mismatch_q - q_true), 1e-15)
            ),
        },
        "unknown_nuisance_identifiability": {
            "scaled_coordinates": ["du/0.8", "dv/0.8", "delta/0.06deg", "width/[0.08,0.13]", "background/[0,0.01]"],
            "jacobian_column_norms": column_norms.tolist(),
            "singular_values": singular_values.tolist(),
            "condition_number": condition,
            "max_abs_column_correlation": max_correlation,
            "column_correlation_matrix": correlations.tolist(),
            "thresholds": {
                "condition_number_max": p1_gate_thresholds["p1_unknown_nuisance_jacobian_condition_max"],
                "max_abs_column_correlation": p1_gate_thresholds["p1_unknown_nuisance_max_abs_column_correlation"],
            },
        },
        "non_oracle_profile_fitting": {
            "method": "bounded L-BFGS-B over normalized q and eta; inputs are expected profile and candidate parameters only",
            "starts": [start.tolist() for start in starts],
            "fits": profile_rows,
            "eta_true_used_by_optimizer": False,
            "q_true_used_by_optimizer": False,
        },
        "noise_expectation": {
            "poisson_count_scale": 30000,
            "readout_noise": "not required for this Poisson-only repeated-draw check; V9 config includes bounded Gaussian readout",
            "replicates": len(samples),
            "single_realization_transformed_rmse": single_rmse,
            "mc_mean_transformed_rmse": mc_rmse,
            "passed": gates["noise_expectation_mc_passed"],
        },
        "elapsed_seconds": time.perf_counter() - numeric_started,
        "gates": gates,
    }
    report["passed"] = bool(gates["all_physics_and_unknown_nuisance_gates_passed"])
    (args.output / "p1_numeric_gates.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    z_scan = np.linspace(q_true[0] - 0.2, q_true[0] + 0.2, 41)
    expected_curve = []
    mismatched_curve = []
    with torch.no_grad():
        for du in z_scan:
            q_scan = torch.tensor([[du, q_true[1]]], device="cuda", dtype=torch.float64)
            expected_curve.append(float(F.mse_loss(expected_profile(forward, q_scan, eta_tensor), target).item()))
            mismatched_curve.append(float(F.mse_loss(expected_profile(forward, q_scan, eta_ref), target).item()))
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    ax.plot(z_scan, expected_curve, label="measurement-aware expected profile, eta fixed to truth")
    ax.plot(z_scan, mismatched_curve, label="clean reference vs perturbed expected observation")
    ax.axvline(q_true[0], color="black", linestyle="--", linewidth=1, label="true du")
    ax.set_xlabel("du normalized")
    ax.set_ylabel("transformed-profile MSE")
    ax.set_title("Issue #19 BaTiO3 local q–measurement mismatch diagnostic")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(args.output / "p1_q_profile_scan.png", dpi=160)
    plt.close(fig)

    print(json.dumps({"passed": report["passed"], "gates": gates, "report": report}, indent=2))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
