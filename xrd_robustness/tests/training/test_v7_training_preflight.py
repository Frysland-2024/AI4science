import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import ANY, patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "train_v7_preflight_test",
    PROJECT_ROOT / "scripts" / "train_v7.py",
)
assert SPEC and SPEC.loader
TRAINER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRAINER)


class V7TrainingPreflightTests(unittest.TestCase):
    def _write_records(self, data_root: Path, count: int) -> None:
        path = data_root / "mp_processed" / "structure_records.jsonl"
        path.parent.mkdir(parents=True)
        with path.open("w", encoding="utf-8") as handle:
            for index in range(count):
                split = "train" if index < count - 2 else ("validation" if index == count - 2 else "test")
                row = {
                    "material_id": f"mp-{index}",
                    "structure_fingerprint": f"fp-{index}",
                    "crystal_system": "cubic",
                    "split": split,
                }
                handle.write(json.dumps(row) + "\n")

    def test_formal_14060_without_subset_loads_the_full_tier(self):
        with tempfile.TemporaryDirectory() as directory:
            data_root = Path(directory)
            self._write_records(data_root, 14060)
            records = TRAINER._load_records(14060, data_root)
            self.assertEqual(len(records), 14060)
            self.assertIn("mp-14059", records)

    def test_formal_14060_rejects_wrong_root_size(self):
        with tempfile.TemporaryDirectory() as directory:
            data_root = Path(directory)
            self._write_records(data_root, 3)
            with self.assertRaisesRegex(ValueError, "expected 14060"):
                TRAINER._load_records(14060, data_root)

    def test_git_commit_resolves_from_parent_repository(self):
        commit = TRAINER._git_commit(PROJECT_ROOT)
        self.assertEqual(len(commit), 40)
        self.assertTrue(all(character in "0123456789abcdef" for character in commit))

    def test_posthoc_train_probe_uses_the_train_scientific_split(self):
        initial_rows = [
            SimpleNamespace(material_id="mp-1"),
            SimpleNamespace(material_id="mp-1"),
        ]
        accepted_rows = [object(), object()]
        with (
            patch.object(
                TRAINER, "build_parameter_stream", return_value=initial_rows
            ) as build,
            patch.object(
                TRAINER,
                "render_accepted_training_row",
                side_effect=[(object(), accepted_rows[0]), (object(), accepted_rows[1])],
            ) as render,
        ):
            rows = TRAINER._build_posthoc_train_probe_rows(
                ["mp-1"],
                object(),
                profile="train",
                peaks={"mp-1": object()},
                factory=object(),
            )
        self.assertEqual(rows, accepted_rows)
        build.assert_called_once_with(
            ["mp-1"],
            ANY,
            profile="train",
            epochs=1,
            steps_per_epoch=1,
            split="train",
        )
        self.assertEqual(render.call_count, 2)


if __name__ == "__main__":
    unittest.main()
