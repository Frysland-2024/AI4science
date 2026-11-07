"""Exercise the frozen-input checks using synthetic spectra only."""

import csv
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np

from xrd_robustness.evaluation import rruff_cu1011


class FrozenInputsTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.manifest = Path(directory.name) / "primary.csv"
        self.inputs = Path(directory.name) / "primary.npz"
        self.ids = np.array([f"synthetic-{i}" for i in range(1011)])
        self.indices = np.repeat(np.arange(7), [97, 334, 211, 45, 129, 76, 119])
        self.systems = np.array(rruff_cu1011.CRYSTAL_SYSTEMS)[self.indices]
        self.spectra = np.ones((1011, 3501), dtype=np.float32)
        self.observed = np.ones(self.spectra.shape, dtype=bool)

    def write_inputs(self, *, ids=None, indices=None):
        with self.manifest.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(("sample_variant_id", "final_candidate_system", "v11_label_index"))
            writer.writerows(zip(
                self.ids, self.systems, self.indices if indices is None else indices, strict=True,
            ))
        np.savez_compressed(
            self.inputs, sample_ids=self.ids if ids is None else ids,
            crystal_system_labels=self.systems, xrd_input=self.spectra,
            observation_mask=self.observed,
        )

    def load_fixture(self):
        # Use the synthetic bundle digests to exercise checks after the hash gate.
        with patch.multiple(
            rruff_cu1011,
            MANIFEST_SHA256=hashlib.sha256(self.manifest.read_bytes()).hexdigest(),
            INPUTS_SHA256=hashlib.sha256(self.inputs.read_bytes()).hexdigest(),
        ):
            return rruff_cu1011.load_frozen_inputs(self.manifest, self.inputs)

    def test_rejects_unfrozen_files(self):
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            rruff_cu1011.load_frozen_inputs(self.manifest, self.inputs)

    def test_returns_ordered_inputs(self):
        self.write_inputs()
        ids, spectra, indices = self.load_fixture()
        np.testing.assert_array_equal(ids, self.ids)
        np.testing.assert_array_equal(spectra, self.spectra)
        np.testing.assert_array_equal(indices, self.indices)

    def test_rejects_reordered_ids(self):
        self.write_inputs(ids=self.ids[::-1])
        with self.assertRaisesRegex(ValueError, "ordered primary manifest"):
            self.load_fixture()

    def test_rejects_wrong_class_index(self):
        self.write_inputs(indices=(self.indices + 1) % 7)
        with self.assertRaisesRegex(ValueError, "model class order"):
            self.load_fixture()

    def test_rejects_unobserved_bin(self):
        self.observed[0, -1] = False
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, "covered by source measurements"):
            self.load_fixture()

    def test_rejects_invalid_values(self):
        for value, message in ((float("nan"), "finite"), (-1, "nonnegative"), (2, "max-normalized")):
            with self.subTest(value=value):
                self.spectra[0, 0] = value
                self.write_inputs()
                with self.assertRaisesRegex(ValueError, message):
                    self.load_fixture()
