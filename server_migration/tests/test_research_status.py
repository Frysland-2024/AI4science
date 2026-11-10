"""No CUDA, private datasets, services, or GPU jobs needed."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "research_status.py"
SPEC = importlib.util.spec_from_file_location("research_status", SRC)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class TestResearchStatus(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.study = Path(self.tmp.name)

    def save(self, relative, value):
        target = self.study / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value), encoding="utf-8")

    def test_new_study_is_decision_not_running(self):
        self.assertEqual(mod.summarize(self.study)["status"], "NEEDS_DECISION")
        (self.study / ".study.lock").write_bytes(b"\x00")
        self.assertEqual(mod.summarize(self.study)["live_runner_lock"], "FREE")

    def test_active_held_lock_only_counts_as_running(self):
        self.save("contract.json", {"max_new_trials": 8})
        with patch.object(mod, "_lock_held", return_value=True):
            self.assertEqual(mod.summarize(self.study)["status"], "RUNNING")

    def test_partial_trials_pause_for_review(self):
        self.save("contract.json", {"max_new_trials": 8})
        self.save("trials/hpo_000/result.json", {"status": "completed"})
        result = mod.summarize(self.study)
        self.assertEqual(result["status"], "NEEDS_DECISION")
        self.assertEqual(result["completed_hpo_trials"], 1)

    def test_malformed_result_blocks(self):
        self.save("contract.json", {"max_new_trials": 8})
        self.save("trials/hpo_000/result.json", {"status": "failed"})
        self.assertEqual(mod.summarize(self.study)["status"], "BLOCKED")

    def test_hpo_completion_waits_for_final_authorization(self):
        self.save("contract.json", {"max_new_trials": 2})
        for i in range(2):
            self.save(f"trials/hpo_{i:03d}/result.json", {"status": "completed"})
            self.save(f"trials/confirm_{i}/result.json", {"status": "completed"})
        self.save("final_recommendation.json", {"status": "hpo_and_confirmation_completed", "hpo_trial_count": 2})
        result = mod.summarize(self.study)
        self.assertEqual(result["status"], "NEEDS_DECISION")
        self.assertEqual(result["stage"], "HPO_CONFIRMED")

    def test_final_does_not_claim_rruff_complete(self):
        self.save("contract.json", {"max_new_trials": 2})
        for i in range(2):
            self.save(f"trials/hpo_{i:03d}/result.json", {"status": "completed"})
            self.save(f"trials/confirm_{i}/result.json", {"status": "completed"})
        self.save("final_recommendation.json", {"status": "hpo_and_confirmation_completed", "hpo_trial_count": 2})
        self.save("final_training_summary.json", {"status": "final_three_seed_training_completed", "runs": [{"seed": 1}, {"seed": 2}, {"seed": 3}]})
        r = mod.summarize(self.study)
        self.assertEqual(r["status"], "COMPLETED")
        self.assertIn("Test/RRUFF", r["boundary"])

    def test_results_without_contract_block(self):
        self.save("trials/hpo_000/result.json", {"status": "completed"})
        self.assertEqual(mod.summarize(self.study)["status"], "BLOCKED")

    def test_final_summary_without_trials_blocks(self):
        self.save("contract.json", {"max_new_trials": 2})
        self.save("final_recommendation.json", {"status": "hpo_and_confirmation_completed", "hpo_trial_count": 2})
        self.save("final_training_summary.json", {"status": "final_three_seed_training_completed", "runs": [{"seed": 1}, {"seed": 2}, {"seed": 3}]})
        self.assertEqual(mod.summarize(self.study)["status"], "BLOCKED")

    def test_missing_confirmation_blocks_false_recommendation(self):
        self.save("contract.json", {"max_new_trials": 1})
        self.save("trials/hpo_000/result.json", {"status": "completed"})
        self.save("final_recommendation.json", {"status": "hpo_and_confirmation_completed", "hpo_trial_count": 1})
        self.assertEqual(mod.summarize(self.study)["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
