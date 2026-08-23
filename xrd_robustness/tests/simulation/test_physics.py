import unittest

from xrd_robustness.physics import (
    ParameterProfile,
    PhysicsParameterSampler,
    build_frozen_perturbation_manifest,
    stable_view_seed,
)


def _activation_range(min_value, max_value, probability):
    return {
        "distribution": "fixed" if min_value == max_value else "uniform",
        "min_value": min_value,
        "max_value": max_value,
        "apply_probability": probability,
    }


def _range(low, high, distribution="uniform"):
    return {
        "distribution": distribution,
        "min_value": low,
        "max_value": high,
        "apply_probability": 1.0,
    }


def _sampler():
    return PhysicsParameterSampler.from_mapping(
        {
            "run_seed": 19,
            "profiles": {
                "test": {
                    "severity_level": 2,
                    "background_type": "flat",
                    "delta_2theta_deg": _range(-0.1, 0.1),
                    "fwhm_deg": _range(0.05, 0.2),
                    "background_to_peak_ratio": _range(0.0, 0.03),
                    "noise_std_ratio": _range(0.0, 0.02),
                }
            },
        }
    )


class PhysicsTests(unittest.TestCase):
    def test_seed_uses_epoch_step_material_and_view(self):
        base = stable_view_seed(1, 2, 3, "mp-1", 1)
        self.assertEqual(base, stable_view_seed(1, 2, 3, "mp-1", 1))
        self.assertNotEqual(base, stable_view_seed(1, 3, 3, "mp-1", 1))
        self.assertNotEqual(base, stable_view_seed(1, 2, 4, "mp-1", 1))
        self.assertNotEqual(base, stable_view_seed(1, 2, 3, "mp-1", 2))

    def test_unconfigured_scientific_profile_fails_closed(self):
        with self.assertRaises(ValueError):
            _sampler().sample(
                "train",
                epoch=0,
                global_step=0,
                material_id="mp-1",
                view_id=1,
            )

    def test_frozen_manifest_is_reproducible_and_traceable(self):
        sampler = _sampler()
        first = build_frozen_perturbation_manifest(["mp-2", "mp-1"], sampler, profile="test")
        second = build_frozen_perturbation_manifest(["mp-1", "mp-2"], sampler, profile="test")
        self.assertEqual(first, second)
        self.assertEqual(len(first), 4)
        self.assertIn("simulation_seed", first[0])
        self.assertIn("delta_2theta_deg", first[0]["perturbation_parameters"])
        self.assertEqual(first[0]["severity_level"], 2)

    def test_polynomial_background_profile_is_supported(self):
        sampler = PhysicsParameterSampler.from_mapping(
            {
                "run_seed": 7,
                "profiles": {
                    "candidate": {
                        "severity_level": 1,
                        "background_type": "polynomial",
                        "delta_2theta_deg": _range(0.0, 0.0, "fixed"),
                        "fwhm_deg": _range(0.1, 0.1, "fixed"),
                        "background_to_peak_ratio": _range(0.02, 0.02, "fixed"),
                        "noise_std_ratio": _range(0.0, 0.0, "fixed"),
                    }
                },
            }
        )
        parameters, _ = sampler.sample(
            "candidate", epoch=0, global_step=0, material_id="mp-1", view_id=1
        )
        self.assertEqual(parameters.background_type, "polynomial")


class ProbabilityActivationTests(unittest.TestCase):
    """Operator-activation checks merged from the retired standalone module."""

    @staticmethod
    def _profile(probability):
        return ParameterProfile.from_mapping(
            {
                "delta_2theta_deg": _activation_range(0.1, 0.1, probability),
                "fwhm_deg": _activation_range(0.2, 0.2, probability),
                "background_to_peak_ratio": _activation_range(0.02, 0.02, probability),
                "noise_std_ratio": _activation_range(0.01, 0.01, probability),
                "background_type": "polynomial",
                "severity_level": 1,
            }
        )

    def test_probability_zero_disables_all_operators(self):
        params = self._profile(0.0).sample(17)
        self.assertEqual(params.delta_2theta_deg, 0.0)
        self.assertEqual(params.fwhm_deg, 0.08)
        self.assertEqual(params.background_to_peak_ratio, 0.0)
        self.assertEqual(params.noise_std_ratio, 0.0)
        self.assertEqual(params.active_perturbation_names, ())

    def test_probability_one_enables_all_operators(self):
        params = self._profile(1.0).sample(17)
        self.assertEqual(
            params.active_perturbation_names,
            ("zero_shift", "peak_broadening", "background", "noise"),
        )

    def test_probability_sampling_is_reproducible(self):
        self.assertEqual(
            self._profile(0.5).sample(17).to_dict(),
            self._profile(0.5).sample(17).to_dict(),
        )


if __name__ == "__main__":
    unittest.main()
