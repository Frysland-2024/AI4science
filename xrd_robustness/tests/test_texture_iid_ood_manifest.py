import json
import unittest
from pathlib import Path

from xrd_robustness.physics import PhysicsParameterSampler


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TextureManifestTests(unittest.TestCase):
    def test_ood_texture_changes_only_texture_range_contract(self):
        config = json.loads(
            (PROJECT_ROOT / "configs" / "simulation.v7.candidate.json").read_text(
                encoding="utf-8"
            )
        )
        iid = config["profiles"]["in_range"]
        ood = config["profiles"]["ood_texture"]
        for name in (
            "delta_2theta_deg",
            "fwhm_deg",
            "background_to_peak_ratio",
            "noise_std_ratio",
        ):
            self.assertEqual(iid[name], ood[name])
        self.assertNotEqual(iid["preferred_orientation"]["min_value"], ood["preferred_orientation"]["min_value"])
        self.assertEqual(iid["preferred_orientation"]["min_value"], ood["preferred_orientation"]["max_value"])

    def test_v7_samples_are_auditable_and_level0_texture_is_disabled(self):
        v7 = PhysicsParameterSampler.from_json(
            PROJECT_ROOT / "configs" / "simulation.v7.candidate.json"
        )
        texture, _ = v7.sample(
            "ood_texture", epoch=0, global_step=0, material_id="mp-1", view_id=1
        )
        record = texture.to_dict()
        for key in (
            "preferred_orientation_active",
            "preferred_orientation_model",
            "march_parameter",
            "orientation_seed",
            "preferred_orientation_apply_probability",
            "severity_level",
        ):
            self.assertIn(key, record)
        level0, _ = v7.sample(
            "level0", epoch=0, global_step=0, material_id="mp-1", view_id=1
        )
        self.assertFalse(level0.preferred_orientation_active)
        self.assertEqual(level0.march_parameter, 1.0)


if __name__ == "__main__":
    unittest.main()
