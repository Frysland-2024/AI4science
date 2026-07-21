import unittest

import numpy as np

from xrd_robustness.physics import PhysicsParameters
from xrd_robustness.simulator import SimulationGrid, simulate_from_peak_table


class SimulatorTests(unittest.TestCase):
    def setUp(self):
        self.params = PhysicsParameters(
            delta_2theta_deg=0.0,
            fwhm_deg=0.08,
            background_to_peak_ratio=0.0,
            noise_std_ratio=0.0,
            background_type="flat",
            severity_level=0,
        )

    def test_grid_and_fixed_simulation_are_reproducible(self):
        grid = SimulationGrid()
        first = simulate_from_peak_table([20.0, 40.0], [100.0, 30.0], self.params, rng_seed=7)
        second = simulate_from_peak_table([20.0, 40.0], [100.0, 30.0], self.params, rng_seed=7)
        self.assertEqual(len(grid.values), 3501)
        self.assertEqual(grid.values[0], 10.0)
        self.assertEqual(grid.values[-1], 80.0)
        np.testing.assert_array_equal(first, second)
        self.assertTrue(np.isfinite(first).all())
        self.assertGreaterEqual(float(first.min()), 0.0)
        self.assertEqual(float(first.max()), 1.0)

    def test_zero_offset_moves_every_peak_by_the_same_amount(self):
        shifted_params = PhysicsParameters(
            delta_2theta_deg=0.10,
            fwhm_deg=0.08,
            background_to_peak_ratio=0.0,
            noise_std_ratio=0.0,
            background_type="flat",
            severity_level=1,
        )
        grid = SimulationGrid().values
        original = simulate_from_peak_table(
            [20.0, 40.0], [100.0, 80.0], self.params, rng_seed=7
        )
        shifted = simulate_from_peak_table(
            [20.0, 40.0], [100.0, 80.0], shifted_params, rng_seed=7
        )

        def local_maximum(profile, center):
            index = int(round((center - grid[0]) / 0.02))
            window = slice(index - 10, index + 11)
            return index - 10 + int(np.argmax(profile[window]))

        movements = [
            local_maximum(shifted, center + 0.10) - local_maximum(original, center)
            for center in (20.0, 40.0)
        ]
        self.assertEqual(movements, [5, 5])


if __name__ == "__main__":
    unittest.main()
