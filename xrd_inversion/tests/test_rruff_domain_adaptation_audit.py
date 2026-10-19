import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_rruff_domain_adaptation as audit  # noqa: E402


class RruffAuditParserTests(unittest.TestCase):
    def test_sample_id_keeps_subnumber_and_rejects_non_rruff_id(self):
        self.assertEqual(audit.sample_id_from_member("Grossular__R040065-1__Powder__XY.txt"), "R040065-1")
        self.assertIsNone(audit.sample_id_from_member("Drug__D120011-1__Powder__XY.txt"))
        self.assertEqual(audit.base_sample_id("R040065-1"), "R040065")


    def test_refined_cell_notation_preserves_esd_scale(self):
        self.assertEqual(audit.parse_refined_number("11.8517(2)"), (11.8517, 0.0002))
        self.assertEqual(audit.parse_refined_number("18.070(1)"), (18.07, 0.001))
        self.assertEqual(audit.parse_refined_number("90."), (90.0, None))


    def test_xy_comma_profile_is_parsed_and_fingerprinted(self):
        result = audit.parse_xy_profile("##NAMES=Demo\n5.00, 2.0\n5.01, 4.0\n5.02, 3.0\n")
        self.assertTrue(result["valid"])
        self.assertEqual(result["point_count"], 3)
        self.assertEqual(result["two_theta_min"], 5.0)
        self.assertEqual(result["two_theta_max"], 5.02)
        self.assertEqual(len(result["numeric_trace_sha256"]), 64)


    def test_refinement_output_parses_multiple_cells_on_one_line(self):
        parsed = audit.parse_refinement_output(
            "Symmetry constraint is: CUBIC\n"
            "Wavelength #1 = 1.541838\nMACHINE ERROR: -0.062\n"
            "rmse = 0.0000629\n"
            "A = 11.8517(2) B = 11.8517(2) C = 11.8517(2)\n"
            "Alpha = 90 Beta = 90 Gamma = 90\n"
        )
        self.assertEqual(parsed["crystal_system"], "cubic")
        self.assertEqual(parsed["cell"]["a"], {"value": 11.8517, "uncertainty": 0.0002})
        self.assertEqual(parsed["cell"]["c"]["value"], 11.8517)
        self.assertEqual(parsed["cell"]["gamma"]["value"], 90.0)
        self.assertEqual(parsed["wavelengths"], [1.541838])
        self.assertEqual(parsed["machine_error"], -0.062)
        self.assertEqual(parsed["rmse_raw"], 0.0000629)


    def test_cif_metric_inference_and_amcsd_code_link(self):
        cif = audit.parse_cif(
        "_chemical_name_mineral 'Grossular'\n"
        "_database_code_amcsd 0001570\n"
        "_chemical_formula_sum 'Al2 Ca3 Si3 O12'\n"
        "_cell_length_a 11.690\n_cell_length_b 11.690\n_cell_length_c 11.690\n"
        "_cell_angle_alpha 90\n_cell_angle_beta 90\n_cell_angle_gamma 90\n"
        "_symmetry_space_group_name_H-M 'I a -3 d'\n",
        "Grossular__0001570.cif",
    )
        self.assertEqual(cif["amcsd_code"], "0001570")
        self.assertEqual(cif["system"], "cubic")
        self.assertEqual(cif["system_source"], "inferred_from_cell_metric")


    def test_dif_code_and_profile_kind_are_not_name_only_evidence(self):
        dif = audit.parse_dif(
        "Grossular\nDiffraction data computed using the structure from the paper\n"
        "CELL PARAMETERS: 11.69 11.69 11.69 90 90 90\nSPACE GROUP: I a -3 d\n"
        "_database_code_amcsd 0001570\n"
    )
        self.assertEqual(dif["amcsd_code"], "0001570")
        self.assertEqual(audit.classify_profile_kind("Single crystal, powder profile is calculated"), "calculated_profile")
        self.assertEqual(audit.classify_profile_kind("Powder, using Mo radiation"), "experimental_powder_candidate")
        self.assertTrue(audit.profile_has_mixture_caveat("Powder, mixed with quartz"))
        self.assertFalse(audit.profile_has_mixture_caveat("Powder, using Mo radiation"))
        self.assertEqual(audit.family_for_name("Grossular"), "Garnet")


if __name__ == "__main__":
    unittest.main()
