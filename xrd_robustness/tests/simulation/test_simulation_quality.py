import unittest

import numpy as np

from xrd_robustness.physics import PhysicsParameters
from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.peak_cache import PeakTable
from xrd_robustness.simulation_quality import inspect_perturbed_view
from xrd_robustness.simulator import SimulationGrid, simulate_from_peak_table
from xrd_robustness.view_manifest import ViewManifestRow


class SimulationQualityTests(unittest.TestCase):
    def test_raw_area_is_stable_when_only_fwhm_changes(self):
        grid = SimulationGrid()
        base_params = PhysicsParameters(0.0, 0.08, 0.0, 0.0, "flat", 0)
        broad_params = PhysicsParameters(0.0, 0.20, 0.0, 0.0, "flat", 1)
        base = simulate_from_peak_table(
            [20.0, 40.0], [100.0, 80.0], base_params, rng_seed=1, grid=grid, normalize=False
        )
        broad = simulate_from_peak_table(
            [20.0, 40.0], [100.0, 80.0], broad_params, rng_seed=1, grid=grid, normalize=False
        )
        self.assertAlmostEqual(float(broad.sum() / base.sum()), 1.0, places=2)

    def test_quality_gate_flags_window_truncation(self):
        grid = SimulationGrid()
        base_params = PhysicsParameters(0.0, 0.08, 0.0, 0.0, "flat", 0)
        shifted_params = PhysicsParameters(-0.5, 0.08, 0.0, 0.0, "flat", 4)
        base = simulate_from_peak_table(
            [10.3, 30.0], [100.0, 20.0], base_params, rng_seed=1, grid=grid, normalize=False
        )
        shifted = simulate_from_peak_table(
            [10.3, 30.0], [100.0, 20.0], shifted_params, rng_seed=1, grid=grid, normalize=False
        )
        quality = inspect_perturbed_view(
            base,
            shifted,
            peak_positions=[10.3, 30.0],
            peak_intensities=[100.0, 20.0],
            grid=grid.values,
            parameters=shifted_params,
        )
        self.assertFalse(quality["passed"])
        self.assertIn("window_intensity_below_threshold", quality["reasons"])
        self.assertTrue(np.isfinite(shifted).all())

    def test_noise_clipping_is_reported_and_bounded(self):
        grid = SimulationGrid()
        parameters = PhysicsParameters(0.0, 0.08, 0.0, 0.05, "flat", 3)
        profile, diagnostics = simulate_from_peak_table(
            [20.0, 40.0],
            [100.0, 80.0],
            parameters,
            rng_seed=7,
            grid=grid,
            normalize=False,
            return_diagnostics=True,
        )
        self.assertIn("clipped_fraction", diagnostics)
        self.assertGreater(float(diagnostics["clipped_fraction"]), 0.0)
        quality = inspect_perturbed_view(
            profile,
            profile,
            peak_positions=[20.0, 40.0],
            peak_intensities=[100.0, 80.0],
            grid=grid.values,
            parameters=parameters,
            simulation_diagnostics=diagnostics,
        )
        self.assertTrue(quality["clipping_ok"])

    def test_training_quality_gate_rejects_invalid_manifest_view(self):
        parameters = PhysicsParameters(-0.5, 0.08, 0.0, 0.0, "flat", 4)
        row = ViewManifestRow(
            split="train",
            epoch=0,
            global_step=0,
            material_id="mp-test",
            view_id=1,
            simulation_seed=11,
            parameters=parameters.to_dict(),
        )
        factory = OnlineViewFactory(
            sampler=None,  # manifest rendering does not resample parameters
            quality_gate=True,
        )
        with self.assertRaisesRegex(ValueError, "quality gate rejected"):
            factory.make_view_from_manifest(
                PeakTable(
                    positions=np.asarray([10.3, 30.0]),
                    intensities=np.asarray([100.0, 20.0]),
                ),
                row,
            )


if __name__ == "__main__":
    unittest.main()
