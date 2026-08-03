from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_v9_resnet_js_four_run_preflight.py"
SPEC = importlib.util.spec_from_file_location("four_run_preflight", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FourRunPreflightTest(unittest.TestCase):
    def test_locked_contract_refuses_completed_output_root(self) -> None:
        contract = ROOT / "configs" / "v9_resnet_js_four_run.preregistered.json"
        plan, report = MODULE.run_audit(contract)
        self.assertEqual(report["status"], "fail")
        self.assertFalse(report["checks"]["no_four_run_output_root_exists"])
        self.assertTrue(
            all(
                passed
                for name, passed in report["checks"].items()
                if name != "no_four_run_output_root_exists"
            )
        )
        self.assertFalse(report["four_run_started"])
        self.assertEqual(len(plan["runs"]), 4)
        self.assertEqual(
            [row["lambda_js"] for row in plan["runs"]], [0.0, 3.0, 30.0, 60.0]
        )
        self.assertTrue(all(row["state"] == "planned_not_started" for row in plan["runs"]))

    def test_execution_unlock_fails_closed(self) -> None:
        source = ROOT / "configs" / "v9_resnet_js_four_run.preregistered.json"
        contract = json.loads(source.read_text(encoding="utf-8"))
        contract["execution"]["four_run_enabled"] = True
        with tempfile.TemporaryDirectory() as directory:
            mutated = Path(directory) / "contract.json"
            mutated.write_text(json.dumps(contract), encoding="utf-8")
            _, report = MODULE.run_audit(mutated)
        self.assertEqual(report["status"], "fail")
        self.assertFalse(report["checks"]["four_run_locked"])


if __name__ == "__main__":
    unittest.main()
