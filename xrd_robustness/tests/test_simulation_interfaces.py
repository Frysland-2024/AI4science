import unittest

import numpy as np

from xrd_robustness.physics import PhysicsParams, PhysicsParameters
from xrd_robustness.simulation_interfaces import PeakTable
from xrd_robustness.simulator import GaussianProfileRenderer, SimulationGrid


class SimulationInterfaceTests(unittest.TestCase):
    def test_physics_alias_preserves_public_type(self):
        self.assertIs(PhysicsParams, PhysicsParameters)

    def test_renderer_contract_replays_first_release_perturbations(self):
        peak_table = PeakTable(
            positions=np.asarray([20.0, 40.0]),
            intensities=np.asarray([100.0, 30.0]),
        )
        params = PhysicsParams(
            delta_2theta_deg=0.1,
            fwhm_deg=0.12,
            background_to_peak_ratio=0.01,
            noise_std_ratio=0.01,
            background_type="polynomial",
            severity_level=1,
        )
        renderer = GaussianProfileRenderer(SimulationGrid())
        first = renderer.render(peak_table, params, rng_seed=17)
        second = renderer.render(peak_table, params, rng_seed=17)
        np.testing.assert_array_equal(first, second)
        self.assertEqual(first.shape, (3501,))

    def test_peak_table_rejects_unsorted_or_nonpositive_reflections(self):
        with self.assertRaises(ValueError):
            PeakTable(np.asarray([40.0, 20.0]), np.asarray([1.0, 1.0]))
        with self.assertRaises(ValueError):
            PeakTable(np.asarray([20.0]), np.asarray([0.0]))

    def test_first_release_operator_provenance_binds_config_hash(self):
        records = GaussianProfileRenderer().provenance(config_hash="abc123")
        self.assertEqual(
            [record.name for record in records],
            ["zero_shift", "peak_broadening", "background", "noise"],
        )
        self.assertTrue(all(record.config_hash == "abc123" for record in records))
        self.assertTrue(all(record.source for record in records))
        self.assertEqual(
            [record.formula_version for record in records],
            [
                "axis-offset-v1",
                "gaussian-area-stable-v1",
                "smooth-floor-polynomial-or-gp-v2",
                "gaussian-or-poisson-count-readout-v2",
            ],
        )


if __name__ == "__main__":
    unittest.main()
