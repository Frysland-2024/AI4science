from __future__ import annotations

import unittest
import os

import numpy as np

from pxrd_router_mvp.candidates import available_candidates
from pxrd_router_mvp.classifier_adapter import load_optional_prior
from pxrd_router_mvp.crystal import render
from pxrd_router_mvp.demo import run_demo
from pxrd_router_mvp.io import read_spectrum_bytes, validate_spectrum
from pxrd_router_mvp.router import route


class InputTests(unittest.TestCase):
    def test_csv_header_and_numeric_columns(self):
        data = b"angle,intensity\n10,0\n11,1\n12,2\n13,1\n14,0\n15,0\n16,0\n17,0\n18,0\n19,0\n20,0\n21,0\n22,0\n23,0\n24,0\n25,0\n"
        spectrum = read_spectrum_bytes(data, wavelength_angstrom=1.5406, x_column="angle", y_column="intensity")
        self.assertEqual(len(spectrum.two_theta), 16)

    def test_descending_axis_is_reversed_and_duplicates_rejected(self):
        descending = validate_spectrum(np.arange(20, 4, -1), np.arange(16), 1.5406)
        self.assertTrue(np.all(np.diff(descending.two_theta) > 0))
        with self.assertRaisesRegex(ValueError, "strictly monotonic"):
            validate_spectrum([*range(10, 18), 17, *range(18, 25)], np.ones(16), 1.5406)

    def test_negative_intensity_and_nonpositive_wavelength_rejected(self):
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            validate_spectrum(np.arange(16), [-1] + [1]*15, 1.5406)
        with self.assertRaisesRegex(ValueError, "wavelength"):
            validate_spectrum(np.arange(16), np.ones(16), 0)


class PhysicalPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = available_candidates()
        cls.axis = np.arange(10.0, 80.0001, 0.08)
        cls.wavelength = 1.5406

    def test_all_three_sourced_cifs_parse_and_render(self):
        self.assertEqual(len(self.candidates), 3)
        self.assertTrue(all(candidate.sha256 == candidate.expected_sha256 for candidate in self.candidates))
        self.assertEqual([candidate.load().crystal_system for candidate in self.candidates], ["tetragonal", "cubic", "cubic"])
        for candidate in self.candidates:
            profile = render(candidate.load(), self.axis, self.wavelength, fwhm=0.14)
            self.assertTrue(np.isfinite(profile).all())
            self.assertGreater(float(profile.max()), 0.99)
            self.assertGreater(int(np.count_nonzero(profile > 0.01)), 4)

    def test_known_profile_routes_and_refines_each_material(self):
        rng = np.random.default_rng(713)
        for candidate in self.candidates:
            with self.subTest(candidate=candidate.id):
                crystal = candidate.load()
                truth_a = crystal.a * 1.003
                truth_c = crystal.c * 0.998 if crystal.crystal_system == "tetragonal" else truth_a
                clean = render(crystal, self.axis, self.wavelength, a=truth_a, c=truth_c,
                               zero_shift=0.018, fwhm=0.16)
                observed = np.clip(0.02 + 0.96 * clean + rng.normal(0, 0.002, len(clean)), 0, None)
                result = route(self.axis, observed, self.wavelength)
                self.assertEqual(result.results[0].candidate_id, candidate.id)
                fit = next(value for value in result.results if value.candidate_id == candidate.id)
                self.assertTrue(fit.success)
                self.assertLess(abs(fit.a_angstrom - truth_a), 0.01)
                if truth_c != truth_a:
                    self.assertIsNotNone(fit.c_angstrom)
                    self.assertLess(abs(fit.c_angstrom - truth_c), 0.01)
                self.assertLess(abs(fit.zero_shift_deg - 0.018), 0.01)
                self.assertEqual(set(result.evaluated_candidate_ids), {c.id for c in self.candidates})

    def test_classifier_is_optional_and_cannot_exclude_candidates(self):
        status = load_optional_prior()
        self.assertFalse(status.available)
        candidate = self.candidates[1]
        crystal = candidate.load()
        profile = render(crystal, self.axis, self.wavelength, fwhm=0.15)
        prior = {"cubic": 0.0, "tetragonal": 1.0}
        result = route(self.axis, 0.02 + profile, self.wavelength, crystal_system_prior=prior)
        self.assertEqual(set(result.evaluated_candidate_ids), {c.id for c in self.candidates})
        self.assertIn(candidate.id, [fit.candidate_id for fit in result.results])

    def test_filename_does_not_change_ranking(self):
        candidate = self.candidates[2]
        crystal = candidate.load()
        profile = render(crystal, self.axis, self.wavelength, fwhm=0.15)
        a = route(self.axis, profile, self.wavelength)
        b = route(self.axis, profile.copy(), self.wavelength)
        from pxrd_router_mvp.io import validate_spectrum
        input_a = validate_spectrum(self.axis, profile, self.wavelength, source_label="MgO.csv")
        input_b = validate_spectrum(self.axis, profile, self.wavelength, source_label="BaTiO3.csv")
        self.assertNotEqual(input_a.source_label, input_b.source_label)
        self.assertTrue(np.array_equal(input_a.intensity, input_b.intensity))
        self.assertEqual([x.candidate_id for x in a.results], [x.candidate_id for x in b.results])
        self.assertEqual([x.score_rmse for x in a.results], [x.score_rmse for x in b.results])

    def test_demo_reproducible_and_marked_simulated(self):
        a = run_demo()
        b = run_demo()
        self.assertEqual(a, b)
        self.assertIn("SIMULATED", a["data_label"])
        self.assertFalse(a["classifier"]["available"])


class RruffLocalAdapterTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("PXRD_RRUFF_TEST_ROOT"), "local RRUFF tree is optional")
    def test_adaptation_records_load_with_recorded_wavelength_and_held_reference(self):
        from pxrd_router_mvp.rruff_local import load_local_example
        root = os.environ["PXRD_RRUFF_TEST_ROOT"]
        for rruff_id, mineral, system in (("R050045", "Fluorite", "cubic"), ("R060745", "Rutile", "tetragonal")):
            with self.subTest(rruff_id=rruff_id):
                example = load_local_example(root, rruff_id)
                self.assertEqual(example.mineral, mineral)
                self.assertEqual(example.crystal_system, system)
                self.assertEqual(example.wavelength_triplet, (1.541838, 1.540562, 1.544390))
                self.assertEqual(example.selected_wavelength_angstrom, 1.541838)
                self.assertEqual(example.refinement_reference_wavelength_angstrom, 1.540562)
                self.assertIn("posthoc_reference_only", example.refinement_role)
                self.assertEqual(len(example.spectrum.two_theta), 3501)

    @unittest.skipUnless(os.environ.get("PXRD_RRUFF_TEST_ROOT"), "local RRUFF tree is optional")
    def test_real_routing_is_adaptation_only_and_every_candidate_is_scored(self):
        from pxrd_router_mvp.rruff_local import route_local_example
        payload = route_local_example(os.environ["PXRD_RRUFF_TEST_ROOT"], "R050045")
        self.assertFalse(payload["frozen_locked_test_used"])
        self.assertIn("posthoc_reference_only", payload["posthoc_reference_role"])
        self.assertEqual(payload["real_demo_status"], "real_demo_requires_better_forward")
        self.assertIn("does not contain", payload["real_demo_warning"])
        self.assertEqual(len(payload["evaluated_candidate_ids"]), 3)
        self.assertEqual(len(payload["ranking"]), 3)

    @unittest.skipUnless(os.environ.get("PXRD_RRUFF_TEST_ROOT") and os.environ.get("PXRD_CLASSIFIER_CHECKPOINT"), "local classifier checkpoint is optional")
    def test_verified_classifier_infers_without_filtering_candidates(self):
        from pxrd_router_mvp.rruff_local import load_local_example
        from pxrd_router_mvp.classifier_adapter import load_optional_prior
        example = load_local_example(os.environ["PXRD_RRUFF_TEST_ROOT"], "R050045")
        status = load_optional_prior(
            os.environ["PXRD_CLASSIFIER_CHECKPOINT"],
            two_theta=example.spectrum.two_theta, intensity=example.spectrum.intensity,
            wavelength_angstrom=example.selected_wavelength_angstrom,
        )
        self.assertTrue(status.available, status.message)
        self.assertAlmostEqual(sum(status.probabilities), 1.0, places=5)
        self.assertEqual(len(status.probabilities), 7)

    def test_locked_test_or_other_ids_are_never_loadable(self):
        from pxrd_router_mvp.rruff_local import load_local_example
        with self.assertRaisesRegex(ValueError, "only the adaptation examples"):
            load_local_example(".", "R050031")


if __name__ == "__main__":
    unittest.main(verbosity=2)
