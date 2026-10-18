"""CPU-only contract tests; these tests do not execute CUDA or training."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pxrd_autolab import benchmark_gpu, run
from pxrd_autolab.physics_gates import REQUIRED_GATES

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "forward_ab_pilot.json"
BENCH_CONFIG = ROOT / "configs" / "forward_speed_benchmark.json"


class PXRDAutoLabTests(unittest.TestCase):
    def test_forward_runner_blocks_without_runtime_physics_evidence_and_backend(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            code = run.write_outputs(CONFIG, output, "a" * 40)
            self.assertEqual(code, 3)
            gate = json.loads((output / "gate_report.json").read_text(encoding="utf-8"))
            metrics = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
            manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
            report = (output / "TECHNICAL_REPORT.md").read_text(encoding="utf-8")
            self.assertEqual(gate["status"], "BLOCKED_MISSING_EVIDENCE")
            self.assertEqual({item["id"] for item in gate["gates"]}, set(REQUIRED_GATES))
            self.assertTrue(all(item["status"] != "PASS" for item in gate["gates"]))
            self.assertFalse(gate["a_b_authorized"])
            self.assertEqual(metrics["status"], "BLOCKED_MISSING_IMPLEMENTATION")
            self.assertFalse(metrics["training_started"])
            self.assertFalse(manifest["scientific_certification"])
            self.assertIn("BLOCKED_MISSING_IMPLEMENTATION", report)

    def test_config_does_not_accept_a_user_supplied_backend(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        config["reviewed_backend"] = {"command": "python arbitrary.py"}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaises(ValueError):
                run.read_config(path)

    def test_benchmark_records_blocked_cuda_result_without_substituting_cpu(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            with patch.object(benchmark_gpu, "benchmark_cuda", return_value={
                "status": "BLOCKED_NO_GPU", "metrics": {}, "reason": "CUDA unavailable"}):
                code = benchmark_gpu.write_outputs(BENCH_CONFIG, output, "b" * 40)
            self.assertEqual(code, 3)
            metrics = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["status"], "BLOCKED_NO_GPU")
            self.assertEqual(metrics["metrics"], {})
            self.assertFalse(metrics["scientific_training"])
            self.assertIn("CUDA unavailable", (output / "TECHNICAL_REPORT.md").read_text(encoding="utf-8"))

    def test_configs_are_strict_and_match_registered_presets(self):
        config = run.read_config(CONFIG)
        self.assertEqual(config["preset"], "forward_ab")
        self.assertEqual(config["scientific_training_budget_seconds"], 7200)
        benchmark = benchmark_gpu.load_config(BENCH_CONFIG)
        self.assertEqual(benchmark["preset"], "forward_speed_benchmark")
        with tempfile.TemporaryDirectory() as temp:
            invalid = Path(temp) / "config.json"
            invalid.write_text(json.dumps({**config, "executable": "arbitrary"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                run.read_config(invalid)


if __name__ == "__main__":
    unittest.main()
