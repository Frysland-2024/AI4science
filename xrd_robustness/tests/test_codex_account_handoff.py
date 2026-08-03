from __future__ import annotations

import json
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

from scripts.prepare_codex_account_handoff import ARTIFACT_ROLES
from scripts.prepare_v9_desktop_migration import COPY_ROOTS


class CodexAccountHandoffTests(unittest.TestCase):
    def test_authoritative_handoff_is_in_migration_scope(self) -> None:
        self.assertIn("CODEX_HANDOFF.md", COPY_ROOTS)
        self.assertIn("CODEX_HANDOFF.md", ARTIFACT_ROLES)

    def test_handoff_declares_completed_test_and_closed_retry_boundaries(self) -> None:
        text = (PROJECT_ROOT / "CODEX_HANDOFF.md").read_text(encoding="utf-8")
        required_phrases = (
            "Validation-only replication completed",
            "没有观察到 Test 指标",
            "`simulated_test_accessed = true`",
            "`simulated_test_result_available = true`",
            "`identical_retry_started = true`",
            "`identical_retry_completed = true`",
            "`identical_retry_authorized = true`",
            "10/10 checkpoints",
            "94.25%",
            "不得重跑",
            "reports/v9_resnet_js_simulated_test_results_20260803.md",
            "real XRD",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_zero_state_pointer_does_not_authorize_training(self) -> None:
        state = json.loads(
            (
                PROJECT_ROOT
                / "outputs"
                / "v9_method_transfer_tuning"
                / "desktop_restart_state.json"
            ).read_text(encoding="utf-8")
        )
        self.assertFalse(state["authorization"]["development_tuning"])
        self.assertFalse(state["authorization"]["formal_training"])
        self.assertFalse(state["authorization"]["simulated_test"])
        self.assertFalse(state["authorization"]["real_test"])
        self.assertEqual(state["execution_state"]["completed_tuning_runs"], 0)
        self.assertEqual(state["execution_state"]["checkpoint_files"], 0)


if __name__ == "__main__":
    unittest.main()
