from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from pxrd_router_mvp.garnet_audit import (
    audit_garnet_archives,
    exact_id,
    parse_refinement_output,
    write_audit,
)


class GarnetAuditParserTests(unittest.TestCase):
    def test_exact_id_preserves_subnumber(self):
        self.assertEqual(exact_id("Grossular__R060452-1__Powder__Xray_Data_XY_RAW.txt"), "R060452-1")

    def test_refinement_uncertainties_and_complete_cell(self):
        parsed = parse_refinement_output("""
Symmetry constraint is: CUBIC
Wavelength #1 = 1.541838
Wavelength #2 = 1.540562
MACHINE ERROR: -0.062
a = 11.8517(2)
b = 11.8517(2)
c = 11.8517(2)
alpha = 90.000(0)
beta = 90.000(0)
gamma = 90.000(0)
""")
        self.assertTrue(parsed["complete_six"])
        self.assertTrue(parsed["complete_esd_six"])
        self.assertAlmostEqual(parsed["cell"]["a"]["value"], 11.8517)
        self.assertAlmostEqual(parsed["cell"]["a"]["esd"], 0.0002)
        self.assertEqual(parsed["wavelengths"], [1.541838, 1.540562])

    def test_archive_audit_writes_derived_record_without_extracting_raw(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "archives"
            root.mkdir()
            sid = "R040065-1"
            member_base = f"Grossular__{sid}__Powder__"
            raw = "##NAMES=Grossular\n##RRUFFID=R040065\n##IDEAL CHEMISTRY=Ca3 Al2 Si3 O12\n##MEASURED CHEMISTRY=Ca3 Al2 Si3 O12\n##DIFFRACTION SAMPLE DESCRIPTION=Powder\n##CELL PARAMETERS=a: 11.8517 b: 11.8517 c: 11.8517\n" + "".join(f"{i/100 + 5:.2f}, {i % 7 + 1}.0\n" for i in range(120))
            outputs = {
                "XY_RAW.zip": {member_base + "Xray_Data_XY_RAW__raw.txt": raw},
                "Refinement_Output_Data.zip": {member_base + "Cell_Refinement_Output_Data__out.txt": """
Symmetry constraint is: CUBIC
Wavelength #1 = 1.541838
MACHINE ERROR: -0.062
a = 11.8517(2)
b = 11.8517(2)
c = 11.8517(2)
alpha = 90.000(0)
beta = 90.000(0)
gamma = 90.000(0)
"""},
                "Refinement_Data.zip": {member_base + "Cell_Refinement_Data__peaks.txt": "R040065\nCubic\n1.541838 1.540562 1.544390\n30 4 0 0 2\n31 4 1 0 2\n"},
                "DIF.zip": {member_base + "DIF_File__dif.txt": "SPACE GROUP: Ia-3d\nCELL PARAMETERS: 11.8517 11.8517 11.8517 90 90 90\nX-RAY WAVELENGTH: 1.541838\n"},
                "cif.zip": {"Grossular__0001570.cif": """
data_test
_chemical_name_mineral Grossular
_chemical_formula_sum 'Ca3 Al2 Si3 O12'
_space_group_IT_number 230
_cell_length_a 11.8515
_cell_length_b 11.8515
_cell_length_c 11.8515
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
"""},
            }
            for archive, members in outputs.items():
                with zipfile.ZipFile(root / archive, "w") as zf:
                    for name, text in members.items():
                        zf.writestr(name, text)
            rows, summary = audit_garnet_archives(root, scope_ids=[sid])
            self.assertEqual(summary["scope_count"], 1)
            self.assertTrue(rows[0]["raw_valid_powder_profile"])
            self.assertEqual(rows[0]["raw_point_count"], 120)
            self.assertTrue(rows[0]["raw_cell_header_present_not_used_for_fit"])
            self.assertEqual(rows[0]["refinement_parse_status"], "complete_six")
            self.assertEqual(rows[0]["refinement_data_member_count"], 1)
            self.assertGreaterEqual(rows[0]["cif_compatible_candidate_count"], 1)
            self.assertFalse(rows[0]["cif_identity_is_same_specimen_confirmed"])
            output = Path(tmp) / "derived"
            write_audit(rows, summary, output)
            self.assertTrue((output / "garnet44_independent_review.csv").is_file())
            self.assertFalse((output / "raw.txt").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
