from __future__ import annotations

import unittest

import numpy as np

from pxrd_router_mvp.crystal import render
from pxrd_router_mvp.grossular_project import (
    GROSSULAR_CANDIDATE,
    PROFILE,
    fit_multistart_a,
    fit_single_a,
    load_candidate,
)


class GrossularProjectTests(unittest.TestCase):
    def test_cif_is_hash_pinned_and_cubic_garnet_parses(self):
        crystal = load_candidate()
        self.assertEqual(GROSSULAR_CANDIDATE.sha256, GROSSULAR_CANDIDATE.expected_sha256)
        self.assertEqual(crystal.crystal_system, "cubic")
        self.assertAlmostEqual(crystal.a, 11.847, places=4)
        self.assertEqual({atom.element for atom in crystal.atoms}, {"Ca", "Al", "Si", "O"})
        self.assertEqual(PROFILE["structure_template"]["same_specimen_as_any_rruff_profile"], False)

    def test_synthetic_profile_recovers_only_free_lattice_parameter(self):
        crystal = load_candidate()
        x = np.arange(5.0, 90.0001, 0.04)
        wavelength = 1.540562
        truth_a = 11.93
        profile = render(crystal, x, wavelength, a=truth_a, c=truth_a, zero_shift=0.0, fwhm=0.14)
        rng = np.random.default_rng(20261019)
        y = np.clip(0.02 + 0.94 * profile + rng.normal(0.0, 0.001, len(profile)), 0.0, None)
        result = fit_single_a(x, y, wavelength, fwhm_deg=0.14, zero_shift_deg=0.0)
        self.assertTrue(result.success)
        self.assertLessEqual(abs(result.fitted_a_angstrom - truth_a), 0.01)
        self.assertLess(result.score_rmse, result.initial_score_rmse)
        self.assertEqual(result.summary()["free_structural_parameters"], ["a_angstrom"])

    def test_multistart_lbfgsb_recovers_synthetic_a_within_pinned_bounds(self):
        crystal = load_candidate()
        x = np.arange(5.0, 90.0001, 0.08)
        truth_a = 11.93
        y = render(crystal, x, 1.540562, a=truth_a, c=truth_a, zero_shift=0.0, fwhm=0.14)
        result = fit_multistart_a(x, y, 1.540562)
        lower, upper = result["bounds_angstrom"]
        self.assertTrue(result["success"])
        self.assertGreaterEqual(result["best_a_angstrom"], lower)
        self.assertLessEqual(result["best_a_angstrom"], upper)
        self.assertLessEqual(abs(result["best_a_angstrom"] - truth_a), 0.01)
        self.assertEqual(result["free_structural_parameters"], ["a_angstrom"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
