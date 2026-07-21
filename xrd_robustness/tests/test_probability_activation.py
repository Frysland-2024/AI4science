import unittest

from xrd_robustness.physics import ParameterProfile


def _range(min_value, max_value, probability):
    return {
        "distribution": "fixed" if min_value == max_value else "uniform",
        "min_value": min_value,
        "max_value": max_value,
        "apply_probability": probability,
    }


class ProbabilityActivationTests(unittest.TestCase):
    def _profile(self, probability):
        return ParameterProfile.from_mapping(
            {
                "delta_2theta_deg": _range(0.1, 0.1, probability),
                "fwhm_deg": _range(0.2, 0.2, probability),
                "background_to_peak_ratio": _range(0.02, 0.02, probability),
                "noise_std_ratio": _range(0.01, 0.01, probability),
                "background_type": "polynomial",
                "severity_level": 1,
            }
        )

    def test_probability_zero_disables_all_operators_and_restores_baseline_width(self):
        params = self._profile(0.0).sample(17)
        self.assertEqual(params.delta_2theta_deg, 0.0)
        self.assertEqual(params.fwhm_deg, 0.08)
        self.assertEqual(params.background_to_peak_ratio, 0.0)
        self.assertEqual(params.noise_std_ratio, 0.0)
        self.assertEqual(params.active_perturbation_count, 0)
        self.assertEqual(params.active_perturbation_names, ())

    def test_probability_one_always_enables_all_operators(self):
        params = self._profile(1.0).sample(17)
        self.assertEqual(params.active_perturbation_count, 4)
        self.assertEqual(
            params.active_perturbation_names,
            ("zero_shift", "peak_broadening", "background", "noise"),
        )

    def test_probability_sampling_is_reproducible(self):
        first = self._profile(0.5).sample(17).to_dict()
        second = self._profile(0.5).sample(17).to_dict()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
