from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC = spec_from_file_location(
    "audit_v9_method_parameter_semantics",
    PROJECT_ROOT / "scripts" / "audit_v9_method_parameter_semantics.py",
)
assert SPEC is not None and SPEC.loader is not None
AUDIT = module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class V9MethodParameterSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = AUDIT.run_audit(device_name="cpu")

    def test_all_registered_semantic_checks_pass(self) -> None:
        self.assertEqual(self.report["status"], "pass")
        self.assertTrue(all(self.report["checks"].values()))

    def test_audit_does_not_use_selection_or_test_data(self) -> None:
        self.assertFalse(self.report["validation_used"])
        self.assertFalse(self.report["simulated_test_used"])
        self.assertFalse(self.report["real_test_used"])
        self.assertFalse(self.report["candidate_selection_performed"])
        self.assertEqual(self.report["formal_training_runs_started"], 0)

    def test_v9_and_deferred_residual_semantics_are_not_conflated(self) -> None:
        contract = self.report["residual_contract"]
        self.assertIn("invariant", contract["v9_production"])
        self.assertIn("sign reverses", contract["deferred_signed_path"])

    def test_theoretical_ranges_use_natural_log(self) -> None:
        scale = self.report["mathematical_scale"]
        self.assertEqual(scale["log_base"], "natural")
        self.assertGreater(scale["js_range"][1], 0.69)
        self.assertLess(scale["js_range"][1], 0.70)
        self.assertGreater(scale["residual_confusion_kl_range"][1], 1.94)
        self.assertLess(scale["residual_confusion_kl_range"][1], 1.95)


if __name__ == "__main__":
    unittest.main()
