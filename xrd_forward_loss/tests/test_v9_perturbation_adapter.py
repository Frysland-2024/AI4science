import json
import unittest
from pathlib import Path

import numpy as np
import torch

from pxrd_forward_loss.losses import clean_reference_paired_losses
from pxrd_forward_loss.perturbation_data import condition_arrays
from xrd_robustness.measurement_models import (
    apply_noise_model,
    generate_background_profile,
)
from xrd_robustness.physics import PhysicsParameters, PhysicsParameterSampler
from xrd_robustness.simulator import SimulationGrid, simulate_from_peak_table


class _LinearForward:
    def transformed(self, full_q):
        q = full_q[:, :2]
        return torch.stack((q[:, 0] + 0.5 * q[:, 1], q[:, 0] - q[:, 1]), dim=1)


class V9PerturbationAdapterTests(unittest.TestCase):
    def test_poisson_gaussian_counts_have_expected_mean_and_variance(self):
        expected = np.full(50000, 0.5, dtype=np.float64)
        observed, metadata = apply_noise_model(
            expected,
            rng=np.random.default_rng(1401),
            model="poisson_gaussian",
            poisson_count_scale=5000.0,
            electronic_noise_std_counts=2.0,
        )
        expected_variance = 0.5 / 5000.0 + (2.0 / 5000.0) ** 2
        self.assertAlmostEqual(float(np.mean(observed)), 0.5, delta=2.5e-4)
        self.assertAlmostEqual(float(np.var(observed)), expected_variance, delta=expected_variance * 0.03)
        self.assertEqual(metadata["noise_model"], "poisson_gaussian")
        self.assertEqual(metadata["electronic_noise_std_counts"], 2.0)

    def test_smooth_background_is_nonnegative_and_low_frequency(self):
        axis = np.linspace(10.0, 80.0, 3501)
        background, metadata = generate_background_profile(
            axis,
            0.008,
            model="polynomial",
            order=2,
            variation=0.2,
            floor_fraction=0.1,
            rng=np.random.default_rng(1402),
        )
        self.assertTrue(np.isfinite(background).all())
        self.assertGreaterEqual(float(background.min()), 0.0)
        self.assertAlmostEqual(float(background.max()), 0.008, places=7)
        self.assertLess(float(np.max(np.abs(np.diff(background, n=2)))), 1e-5)
        self.assertEqual(metadata["background_model"], "polynomial")

    def test_v9_renderer_preserves_area_when_broadening(self):
        grid = SimulationGrid()
        common = dict(
            background_to_peak_ratio=0.0,
            noise_std_ratio=0.0,
            background_type="flat",
            severity_level=1,
            background_active=False,
            noise_active=False,
            preferred_orientation_active=False,
        )
        narrow = PhysicsParameters(0.0, 0.08, **common)
        broad = PhysicsParameters(0.0, 0.12, **common)
        narrow_profile = simulate_from_peak_table(
            [25.0, 43.0], [100.0, 57.0], narrow,
            rng_seed=7, grid=grid, normalize=False,
        )
        broad_profile = simulate_from_peak_table(
            [25.0, 43.0], [100.0, 57.0], broad,
            rng_seed=7, grid=grid, normalize=False,
        )
        narrow_area = float(np.trapezoid(narrow_profile, grid.values))
        broad_area = float(np.trapezoid(broad_profile, grid.values))
        self.assertLess(abs(broad_area / narrow_area - 1.0), 0.01)

    def test_zero_shift_moves_all_peak_centroids_by_one_global_offset(self):
        grid = SimulationGrid(two_theta_min=20.0, two_theta_max=60.0, step=0.002)
        common = dict(
            fwhm_deg=0.08,
            background_to_peak_ratio=0.0,
            noise_std_ratio=0.0,
            background_type="flat",
            severity_level=1,
            background_active=False,
            noise_active=False,
            preferred_orientation_active=False,
        )
        unshifted = PhysicsParameters(0.0, **common)
        shift_deg = 0.05
        shifted = PhysicsParameters(shift_deg, **common)
        positions = [30.0, 46.0]
        intensities = [100.0, 70.0]
        base = simulate_from_peak_table(
            positions, intensities, unshifted, rng_seed=8, grid=grid, normalize=False
        )
        moved = simulate_from_peak_table(
            positions, intensities, shifted, rng_seed=8, grid=grid, normalize=False
        )
        for center in positions:
            window = (grid.values >= center - 0.3) & (grid.values <= center + 0.3)
            base_centroid = float(np.sum(grid.values[window] * base[window]) / np.sum(base[window]))
            moved_centroid = float(np.sum(grid.values[window] * moved[window]) / np.sum(moved[window]))
            self.assertAlmostEqual(moved_centroid - base_centroid, shift_deg, delta=0.001)

    def test_phase_profiles_disable_march_dollase_and_stage_operators(self):
        root = Path(__file__).resolve().parents[1]
        config = json.loads((root / "configs/v9_disturbance_clean_reference_pilot.json").read_text())
        sampler = PhysicsParameterSampler.from_mapping(
            {"run_seed": 20261044, "profiles": config["v9_profiles"]}
        )
        phase1, _ = sampler.sample(
            "phase1_noise_background", epoch=0, global_step=0,
            material_id="mp-1007758", view_id=1,
        )
        phase2, _ = sampler.sample(
            "phase2_add_broadening_and_zero_shift", epoch=0, global_step=0,
            material_id="mp-1007758", view_id=1,
        )
        self.assertEqual(phase1.active_perturbation_names, ("background", "noise"))
        self.assertEqual(set(phase2.active_perturbation_names), {"zero_shift", "peak_broadening", "background", "noise"})
        self.assertFalse(phase1.preferred_orientation_active)
        self.assertFalse(phase2.preferred_orientation_active)
        self.assertEqual(phase1.noise_stage, "before_normalization")
        self.assertEqual(phase2.noise_stage, "before_normalization")

    def test_conditions_share_labels_and_clean_target(self):
        arrays = {
            "q": np.array([[0.2, -0.3]], dtype=np.float32),
            "clean_profile": np.array([[0.1, 0.2]], dtype=np.float32),
            "observed_profile_simple": np.array([[0.11, 0.21]], dtype=np.float32),
            "observed_profile_v9": np.array([[0.4, 0.5]], dtype=np.float32),
        }
        simple = condition_arrays(arrays, "simple")
        v9 = condition_arrays(arrays, "v9")
        np.testing.assert_array_equal(simple["q"], v9["q"])
        np.testing.assert_array_equal(simple["clean"], v9["clean"])
        self.assertFalse(np.array_equal(simple["noisy"], v9["noisy"]))

    def test_clean_reference_loss_backpropagates_through_forward_model(self):
        predicted = torch.tensor([[0.15, -0.1]], dtype=torch.float64, requires_grad=True)
        target_q = torch.tensor([[0.1, -0.05]], dtype=torch.float64)
        clean = torch.tensor([[0.03, 0.2]], dtype=torch.float64)
        losses = clean_reference_paired_losses(
            predicted,
            target_q,
            clean,
            forward_model=_LinearForward(),
            reconstruction_weight=1.0,
        )
        losses["total"].backward()
        self.assertTrue(torch.isfinite(predicted.grad).all())
        self.assertGreater(float(torch.linalg.vector_norm(predicted.grad)), 0.0)
        self.assertTrue(torch.isfinite(losses["reconstruction"]))


if __name__ == "__main__":
    unittest.main()
