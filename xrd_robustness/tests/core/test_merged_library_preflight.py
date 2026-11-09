from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
PRECOMPUTE_PATH = ROOT / "scripts" / "precompute_peak_tables.py"
MANIFEST_PATH = ROOT / "scripts" / "build_merged_library_training_manifest.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


precompute = _load_module("merged_precompute", PRECOMPUTE_PATH)
manifest_builder = _load_module("merged_manifest_builder", MANIFEST_PATH)


class MergedLibraryPreflightTests(unittest.TestCase):
    def test_precompute_adapts_gzipped_merged_schema_and_preserves_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "train_structures.jsonl.gz"
            row = {
                "material_id": "mp-1",
                "structure": {"lattice": {}, "sites": []},
                "source_structure_fingerprint": "source-fp-1",
            }
            with gzip.open(source, "wt", encoding="utf-8") as stream:
                stream.write(json.dumps(row) + "\n")
            records, counts = precompute._load_structure_records(source)
        self.assertEqual(records[0]["material_id"], "mp-1")
        self.assertEqual(records[0]["standardized_structure"], row["structure"])
        self.assertEqual(records[0]["structure_fingerprint"], "source-fp-1")
        self.assertNotIn("structure", records[0])
        self.assertEqual(counts, {
            "structure_to_standardized_structure": 1,
            "source_fingerprint_to_structure_fingerprint": 1,
        })

    def test_precompute_rejects_missing_structure_or_fingerprint(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "records.jsonl"
            source.write_text(json.dumps({"material_id": "mp-1"}) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "standardized_structure or structure"):
                precompute._load_structure_records(source)
            source.write_text(json.dumps({
                "material_id": "mp-1", "structure": {"sites": []}
            }) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "requires structure_fingerprint"):
                precompute._load_structure_records(source)

    @staticmethod
    def _write_shard(path: Path, rows: list[dict]) -> None:
        with gzip.open(path, "wt", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row, sort_keys=True) + "\n")

    def _make_manifest_fixture(self, root: Path):
        source = root / "source"
        source.mkdir()
        cache_root = root / "cache"
        rows_by_split = {
            "train": [
                {"material_id": "train-1", "split": "train", "crystal_system": "cubic",
                 "structure_fingerprint": "fp-t1", "parent_structure_id": "pt1"},
                {"material_id": "train-2", "split": "train", "crystal_system": "tetragonal",
                 "structure_fingerprint": "fp-t2", "parent_structure_id": "pt2"},
            ],
            "validation": [
                {"material_id": "val-1", "split": "validation", "crystal_system": "monoclinic",
                 "structure_fingerprint": "fp-v1", "parent_structure_id": "pv1"},
            ],
            "test": [
                {"material_id": "test-1", "split": "test", "crystal_system": "triclinic",
                 "structure_fingerprint": "fp-x1", "parent_structure_id": "px1"},
            ],
        }
        cache_name = "peak_tables_v7_reflection"
        for split, rows in rows_by_split.items():
            self._write_shard(source / f"{split}_structures.jsonl.gz", rows)
            if split == "test":
                continue
            split_root = cache_root / split
            cache_dir = split_root / "mp_processed" / cache_name
            manifest_dir = split_root / "manifests"
            cache_dir.mkdir(parents=True)
            manifest_dir.mkdir(parents=True)
            cache_rows = []
            for row in rows:
                payload = ("peak-table:" + row["material_id"]).encode()
                cache_path = cache_dir / f'{row["material_id"]}.npz'
                cache_path.write_bytes(payload)
                cache_rows.append({
                    "material_id": row["material_id"],
                    "structure_fingerprint": row["structure_fingerprint"],
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                })
            manifest_file = manifest_dir / "peak_cache_manifest.v7.reflection.csv"
            with manifest_file.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(cache_rows[0]))
                writer.writeheader()
                writer.writerows(cache_rows)
            summary = {
                "status": "completed",
                "cache_name": cache_name,
                "source_record_count": len(rows),
                "completed_count": len(rows),
                "skipped_count": 0,
                "manifest_sha256": hashlib.sha256(manifest_file.read_bytes()).hexdigest(),
            }
            (manifest_dir / "peak_cache_summary.v7.reflection.json").write_text(
                json.dumps(summary), encoding="utf-8"
            )
        return source, cache_root, rows_by_split

    def test_manifest_contains_exact_train_validation_ids_and_excludes_test(self):
        with tempfile.TemporaryDirectory() as temp:
            source, cache_root, _ = self._make_manifest_fixture(Path(temp))
            with patch.object(sys, "argv", [
                str(MANIFEST_PATH), "--source-dir", str(source),
                "--cache-root", str(cache_root),
            ]):
                self.assertEqual(manifest_builder.main(), 0)
            output = cache_root / "training_records.v1.jsonl"
            records = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual({row["material_id"] for row in records},
                             {"train-1", "train-2", "val-1"})
            self.assertNotIn("test-1", {row["material_id"] for row in records})
            self.assertEqual({row["split"] for row in records}, {"train", "validation"})

    def test_manifest_rejects_parent_leakage_and_peak_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            source, cache_root, rows = self._make_manifest_fixture(Path(temp))
            rows["validation"][0]["parent_structure_id"] = "pt1"
            self._write_shard(source / "validation_structures.jsonl.gz", rows["validation"])
            with patch.object(sys, "argv", [
                str(MANIFEST_PATH), "--source-dir", str(source),
                "--cache-root", str(cache_root),
            ]):
                with self.assertRaisesRegex(SystemExit, "parent .* leaks across"):
                    manifest_builder.main()
        with tempfile.TemporaryDirectory() as temp:
            source, cache_root, _ = self._make_manifest_fixture(Path(temp))
            peak = (cache_root / "train" / "mp_processed" /
                    "peak_tables_v7_reflection" / "train-1.npz")
            peak.write_bytes(b"x" * len(peak.read_bytes()))
            with patch.object(sys, "argv", [
                str(MANIFEST_PATH), "--source-dir", str(source),
                "--cache-root", str(cache_root),
            ]):
                with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                    manifest_builder.main()


if __name__ == "__main__":
    unittest.main()
