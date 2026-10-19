from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from donut_pxrd import pipeline


class SerialPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.out = self.root / "state"
        self.script = str(Path(pipeline.__file__).resolve())
        self.marker = self.root / "fail-once.marker"
        self.stages = []
        for sid in ("preflight", "exp1", "exp2"):
            output = f"outputs/{sid}.json"
            self.stages.append({
                "id": sid,
                "depends_on": [self.stages[-1]["id"]] if self.stages else [],
                "command": [sys.executable, self.script, "--mock-worker", "--mock-output", output,
                            "--mock-payload", sid],
                "inputs": [], "required_outputs": [output], "verifier": "files", "timeout_seconds": 10,
            })
        self.stages.append({
            "id": "exp3", "depends_on": ["exp2"],
            "command": [sys.executable, self.script, "--mock-worker", "--mock-behavior", "fail-once",
                        "--mock-marker", str(self.marker), "--mock-output", "outputs/exp3.json", "--mock-payload", "exp3"],
            "inputs": [], "required_outputs": ["outputs/exp3.json"], "verifier": "files", "timeout_seconds": 10,
        })
        self.config = {
            "schema": "donut_pxrd_serial_pipeline_v1",
            "study_config_sha256": pipeline.EXPECTED_CONFIG_SHA256,
            "seeds": pipeline.SEEDS,
            "policy": {"q_parent_count": 512, "frozen_split_counts": {"train": 358, "validation": 77, "test": 77},
                       "max_epochs": 30, "test_tuning": False},
            "allowed_external_roots": [], "stages": self.stages,
        }
        self.config_file = self.root / "config.json"
        pipeline.atomic_json(self.config_file, self.config)
        self.cfg, self.digest = pipeline.load_config(self.config_file)

    def tearDown(self):
        self.tmp.cleanup()

    def test_config_order_immutable_hash_and_no_test_tuning(self):
        actual, digest = pipeline.load_config(ROOT / "donut_pxrd/configs/serial_pipeline_v1.json")
        ids = [s["id"] for s in actual["stages"]]
        self.assertEqual(ids, ["preflight", "exp1", "exp2", "exp3a", "exp3b", "exp3c", "texture_ood", "exp4", "report"])
        self.assertEqual(actual["study_config_sha256"], pipeline.EXPECTED_CONFIG_SHA256)
        self.assertFalse(actual["policy"]["test_tuning"])
        self.assertEqual(len(digest), 64)

    def test_validation_rejects_forward_dependency_and_policy_mutation(self):
        bad = dict(self.config)
        bad["stages"] = [dict(self.stages[0], depends_on=["later"])]
        pipeline.atomic_json(self.config_file, bad)
        with self.assertRaises(pipeline.PipelineError):
            pipeline.load_config(self.config_file)
        bad = dict(self.config)
        bad["policy"] = dict(self.config["policy"], test_tuning=True)
        pipeline.atomic_json(self.config_file, bad)
        with self.assertRaises(pipeline.PipelineError):
            pipeline.load_config(self.config_file)

    def test_path_traversal_rejected(self):
        with self.assertRaises(pipeline.PipelineError):
            pipeline.safe_path(self.root, "../escape.txt")

    def test_concurrent_lock_rejected(self):
        lock = pipeline.FileLock(self.root / "exclusive.lock")
        with lock:
            with self.assertRaises(pipeline.PipelineError):
                with pipeline.FileLock(self.root / "exclusive.lock"):
                    pass
        self.assertFalse((self.root / "exclusive.lock").exists())

    def test_run_refuses_existing_training_output(self):
        (self.root / "outputs").mkdir()
        (self.root / "outputs/preflight.json").write_text("existing\n", encoding="utf-8")
        result = pipeline.run_pipeline(self.cfg, self.digest, self.root, self.out, "run", execute=True)
        self.assertEqual(result, 2)
        state = json.loads((self.out / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["stages"]["preflight"]["status"], "BLOCKED")
        self.assertIn("refusing to overwrite", state["stages"]["preflight"]["error"])

    def test_science_output_verifier_rejects_checkpoint_hash_mismatch(self):
        exp = self.root / "donut_pxrd/results/study_v1/exp1"
        checkpoint_root = self.root / "checkpoints"
        exp.mkdir(parents=True)
        checkpoint_root.mkdir()
        data = exp / "data_arrays.npz"
        data.write_bytes(b"synthetic archive placeholder")
        pipeline.atomic_json(exp / "data_manifest.json", {"npz_sha256": pipeline.sha256(data)})
        pipeline.atomic_json(exp / "training_curves.json", {})
        (exp / "test_per_sample.csv").write_text("seed,q_parent_index\n", encoding="utf-8")
        test_indices = list(range(77))
        records = []
        for seed in pipeline.SEEDS:
            checkpoint = checkpoint_root / f"seed{seed}.pt"
            checkpoint.write_bytes(f"checkpoint-{seed}".encode())
            records.append({"seed": seed, "test_indices": test_indices,
                            "checkpoint": str(checkpoint), "checkpoint_sha256": pipeline.sha256(checkpoint)})
        pipeline.atomic_json(exp / "test_per_seed.json", records)
        stage = {"experiment": "exp1"}
        evidence = pipeline.verify_exp(stage, self.root, [checkpoint_root], pipeline.SEEDS)
        self.assertEqual(evidence["seeds_verified"], pipeline.SEEDS)
        self.assertEqual(evidence["test_parent_count"], 77)
        (checkpoint_root / f"seed{pipeline.SEEDS[0]}.pt").write_bytes(b"tampered")
        with self.assertRaises(pipeline.PipelineError):
            pipeline.verify_exp(stage, self.root, [checkpoint_root], pipeline.SEEDS)

    def test_failure_stops_then_resume_skips_verified_and_recovers(self):
        first = pipeline.run_pipeline(self.cfg, self.digest, self.root, self.out, "run", execute=True)
        self.assertEqual(first, 2)
        state_path = self.out / "state.json"
        state1 = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state1["stages"]["exp3"]["status"], "FAILED")
        self.assertEqual(state1["stages"]["exp3"]["exit_code"], 23)
        self.assertEqual(state1["stages"].get("report", {}).get("status", "BLOCKED"), "BLOCKED")
        second = pipeline.run_pipeline(self.cfg, self.digest, self.root, self.out, "resume")
        self.assertEqual(second, 0)
        state2 = json.loads(state_path.read_text(encoding="utf-8"))
        for sid in ("preflight", "exp1", "exp2", "exp3"):
            self.assertEqual(state2["stages"][sid]["status"], "COMPLETE")
        for sid in ("preflight", "exp1", "exp2"):
            self.assertEqual(state2["stages"][sid]["resume_action"], "SKIPPED_VERIFIED")
        self.assertEqual(state2["stages"]["exp3"]["attempts"][0]["exit_code"], 23)
        self.assertEqual(state2["pipeline_status"], "COMPLETE")
        self.assertEqual(list(self.out.rglob("*.tmp")), [])

    def test_stale_artifact_blocks_resume(self):
        self.assertEqual(pipeline.run_pipeline(self.cfg, self.digest, self.root, self.out, "run", execute=True), 2)
        # Fail-once stage blocks the first pass after exp1 has been verified.
        artifact = self.root / "outputs/preflight.json"
        artifact.write_text("tampered\n", encoding="utf-8")
        self.assertEqual(pipeline.run_pipeline(self.cfg, self.digest, self.root, self.out, "resume"), 2)
        state = json.loads((self.out / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["stages"]["preflight"]["status"], "BLOCKED")

    def test_success_exit_without_required_output_is_failed(self):
        stage = {"id": "fake", "depends_on": [], "command": [sys.executable, "-c", "pass"],
                 "inputs": [], "required_outputs": ["missing.txt"], "verifier": "files", "timeout_seconds": 10}
        cfg = dict(self.cfg, stages=[stage])
        self.assertEqual(pipeline.run_pipeline(cfg, self.digest, self.root, self.out, "run", execute=True), 2)
        state = json.loads((self.out / "state.json").read_text(encoding="utf-8"))
        record = state["stages"]["fake"]
        self.assertEqual(record["exit_code"], 0)
        self.assertEqual(record["status"], "FAILED")
        self.assertIn("verification failed", record["error"])

    def test_dry_run_is_deterministic_and_does_not_create_state_or_outputs(self):
        stream1, stream2 = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stream1):
            self.assertEqual(pipeline.run_pipeline(self.cfg, self.digest, self.root, self.out, "run", dry_run=True), 0)
        with contextlib.redirect_stdout(stream2):
            self.assertEqual(pipeline.run_pipeline(self.cfg, self.digest, self.root, self.out, "run", dry_run=True), 0)
        self.assertEqual(stream1.getvalue(), stream2.getvalue())
        self.assertFalse((self.out / "state.json").exists())
        self.assertFalse((self.root / "outputs").exists())


if __name__ == "__main__":
    unittest.main()
