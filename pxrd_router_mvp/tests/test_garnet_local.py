from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from pxrd_router_mvp.garnet_local import (
    COD_CIF_SHA256,
    COD_FORMULA,
    COD_SPACE_GROUP_NUMBER,
    _load_grossular_cif,
    available_garnet_samples,
    load_garnet_spectrum,
    parse_xy_raw_numeric_rows,
    sample_profile,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
GROSSULAR_CIF = REPO_ROOT / "pxrd_router_mvp" / "candidates" / "Grossular_COD_9001871.cif"


class GarnetRegistryTests(unittest.TestCase):
    def test_registry_is_composition_aware_and_limited_to_grossular(self):
        samples = available_garnet_samples()
        self.assertEqual([sample.sample_id for sample in samples], ["R040066-1", "R050036-1", "R060382-1"])
        self.assertTrue(all(sample.mineral_name == "Grossular" for sample in samples))
        self.assertEqual(len({sample.measured_chemistry for sample in samples}), 3)
        self.assertEqual(len({sample.locality for sample in samples}), 3)
        with self.assertRaisesRegex(ValueError, "only the three curated Grossular"):
            sample_profile("R060125")
        with self.assertRaisesRegex(ValueError, "only the three curated Grossular"):
            sample_profile("R060452")

    def test_xy_parser_discards_header_even_when_it_contains_cell_parameters(self):
        raw = (
            "##TITLE=not-a-cell-input\n"
            "##CELL PARAMETERS=a: 999.999 b: 999.999 c: 999.999\n"
            "##WAVELENGTH=must-not-be-read\n"
            + "\n".join(f"{5 + i * 0.01:.2f},{100 + i}" for i in range(120))
        ).encode("utf-8")
        x, y = parse_xy_raw_numeric_rows(raw)
        self.assertEqual(len(x), 120)
        self.assertAlmostEqual(float(x[0]), 5.0)
        self.assertAlmostEqual(float(x[-1]), 6.19)
        self.assertEqual(float(y[0]), 100.0)

    def test_cif_is_pinned_and_physically_grossular(self):
        structure, calculator, digest, path = _load_grossular_cif(GROSSULAR_CIF)
        self.assertEqual(digest, COD_CIF_SHA256)
        self.assertEqual(structure.composition.reduced_formula, "Ca3Al2(SiO4)3")
        self.assertEqual(structure.get_space_group_info(symprec=1e-2)[1], COD_SPACE_GROUP_NUMBER)
        self.assertAlmostEqual(structure.lattice.a, 11.619)
        self.assertEqual(calculator.wavelength, 1.541838)
        self.assertTrue(path.is_file())
        self.assertEqual(COD_FORMULA, "Ca3Al2Si3O12")

    def test_local_archive_loads_only_curated_real_spectra(self):
        root = os.environ.get("PXRD_GARNET_TEST_ARCHIVE_ROOT")
        if not root:
            self.skipTest("PXRD_GARNET_TEST_ARCHIVE_ROOT is optional local RRUFF data")
        for sample in available_garnet_samples():
            with self.subTest(sample=sample.sample_id):
                spectrum = load_garnet_spectrum(sample.sample_id, root)
                self.assertGreaterEqual(len(spectrum.two_theta), 8000)
                self.assertEqual(len(spectrum.two_theta), len(spectrum.intensity))
                self.assertTrue(np.all(np.diff(spectrum.two_theta) > 0))
                self.assertFalse(hasattr(spectrum, "a_ref_angstrom"))
                self.assertAlmostEqual(spectrum.wavelength_angstrom, 1.541838)

    def test_run_opens_reference_only_after_optimizer_returns(self):
        from pxrd_router_mvp import garnet_local

        events = []
        x = np.linspace(5, 90, 120)
        spectrum = garnet_local.GarnetSpectrum("R040066-1", x, np.ones_like(x), 1.541838, "fixture")
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "XY_RAW.zip").touch()

            def load_spectrum(*args, **kwargs):
                events.append("spectrum")
                return spectrum

            def fit(*args, **kwargs):
                events.append("fit")
                return object()

            def load_reference(*args, **kwargs):
                events.append("reference")
                return object()

            with patch.object(garnet_local, "load_garnet_spectrum", side_effect=load_spectrum), \
                 patch.object(garnet_local, "fit_grossular_spectrum", side_effect=fit), \
                 patch.object(garnet_local, "load_posthoc_reference", side_effect=load_reference), \
                 patch.object(garnet_local, "evaluate_posthoc", side_effect=lambda *args: events.append("evaluate") or object()), \
                 patch.object(garnet_local, "_save_diagnostics", side_effect=lambda *args: events.append("save")):
                garnet_local.run_garnet_pilot("R040066", folder, GROSSULAR_CIF, folder)
        self.assertEqual(events, ["spectrum", "fit", "reference", "evaluate", "save"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
