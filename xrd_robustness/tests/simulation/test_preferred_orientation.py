import unittest

import numpy as np

from xrd_robustness.physics import PhysicsParameterSampler, PhysicsParameters
from xrd_robustness.preferred_orientation import apply_preferred_orientation
from xrd_robustness.simulation_interfaces import PeakTable
from xrd_robustness.simulator import SimulationGrid, simulate_from_peak_table


def _table() -> PeakTable:
    return PeakTable(
        positions=np.asarray([20.0, 30.0, 40.0, 50.0]),
        intensities=np.asarray([100.0, 45.0, 60.0, 30.0]),
        hkls=np.asarray([[1, 0, 0], [2, 0, 0], [0, 1, 0], [1, 1, 0]]),
        multiplicities=np.asarray([2, 1, 2, 4]),
        reciprocal_vectors=np.asarray(
            [[1.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0]]
        ),
        reflection_peak_indices=np.asarray([0, 1, 2, 3]),
    )


def _params(r: float, *, seed: int = 13, preferred_hkl=(1, 0, 0)) -> PhysicsParameters:
    return PhysicsParameters(
        delta_2theta_deg=0.0,
        fwhm_deg=0.12,
        background_to_peak_ratio=0.0,
        noise_std_ratio=0.0,
        background_type="flat",
        severity_level=1,
        zero_shift_active=False,
        broadening_active=True,
        background_active=False,
        noise_active=False,
        preferred_orientation_active=True,
        march_parameter=r,
        preferred_hkl=preferred_hkl,
        orientation_seed=seed,
        preferred_orientation_apply_probability=1.0,
    )


class PreferredOrientationTests(unittest.TestCase):
    def test_r_one_is_exact_reflection_intensity_identity(self):
        table = _table()
        modified, resolved, diagnostics = apply_preferred_orientation(table, _params(1.0))
        np.testing.assert_array_equal(modified, table.intensities)
        self.assertEqual(resolved.preferred_hkl, (1, 0, 0))
        self.assertEqual(diagnostics["intensity_factor_min"], 1.0)
        self.assertEqual(diagnostics["intensity_factor_max"], 1.0)

    def test_collinear_hkl_families_change_coherently(self):
        modified, _, diagnostics = apply_preferred_orientation(_table(), _params(0.7))
        factors = modified / _table().intensities
        self.assertAlmostEqual(float(factors[0]), float(factors[1]))
        self.assertGreater(float(factors[0]), float(factors[2]))
        self.assertLess(diagnostics["intensity_factor_min"], diagnostics["intensity_factor_max"])

    def test_only_relative_intensity_changes_not_peak_position_or_width(self):
        table = _table()
        base = _params(1.0)
        textured = _params(0.7)
        base_profile = simulate_from_peak_table(
            table.positions,
            table.intensities,
            base,
            rng_seed=9,
            reflection_table=table,
            normalize=False,
        )
        texture_profile = simulate_from_peak_table(
            table.positions,
            table.intensities,
            textured,
            rng_seed=9,
            reflection_table=table,
            normalize=False,
        )
        axis = SimulationGrid().values
        for center in table.positions:
            mask = np.abs(axis - center) <= 0.5
            local_axis = axis[mask]
            first = base_profile[mask]
            second = texture_profile[mask]
            self.assertEqual(float(local_axis[np.argmax(first)]), float(local_axis[np.argmax(second)]))
            first_width = np.count_nonzero(first >= 0.5 * np.max(first))
            second_width = np.count_nonzero(second >= 0.5 * np.max(second))
            self.assertEqual(first_width, second_width)

    def test_replay_resolves_same_axis_and_parameter(self):
        config = {
            "run_seed": 77,
            "profiles": {
                "texture": {
                    "severity_level": 1,
                    "background_type": "flat",
                    "delta_2theta_deg": {"distribution": "fixed", "min_value": 0.0, "max_value": 0.0},
                    "fwhm_deg": {"distribution": "fixed", "min_value": 0.08, "max_value": 0.08},
                    "background_to_peak_ratio": {"distribution": "fixed", "min_value": 0.0, "max_value": 0.0},
                    "noise_std_ratio": {"distribution": "fixed", "min_value": 0.0, "max_value": 0.0},
                    "preferred_orientation": {"enabled": True, "distribution": "uniform", "min_value": 0.6, "max_value": 0.9, "apply_probability": 1.0},
                }
            },
        }
        sampler = PhysicsParameterSampler.from_mapping(config)
        first, _ = sampler.sample("texture", epoch=2, global_step=3, material_id="mp-1", view_id=1)
        second, _ = sampler.sample("texture", epoch=2, global_step=3, material_id="mp-1", view_id=1)
        _, first_resolved, _ = apply_preferred_orientation(_table(), first)
        _, second_resolved, _ = apply_preferred_orientation(_table(), second)
        self.assertEqual(first_resolved.preferred_hkl, second_resolved.preferred_hkl)
        self.assertEqual(first_resolved.march_parameter, second_resolved.march_parameter)
        different, _ = sampler.sample("texture", epoch=2, global_step=3, material_id="mp-1", view_id=2)
        self.assertNotEqual(first.march_parameter, different.march_parameter)

    def test_missing_hkl_metadata_fails_instead_of_pointwise_scaling(self):
        legacy = PeakTable(np.asarray([20.0]), np.asarray([100.0]))
        with self.assertRaisesRegex(ValueError, "reflection metadata"):
            apply_preferred_orientation(legacy, _params(0.7))


if __name__ == "__main__":
    unittest.main()

