from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC = spec_from_file_location(
    "audit_v9_resume_determinism",
    PROJECT_ROOT / "scripts" / "audit_v9_resume_determinism.py",
)
assert SPEC is not None and SPEC.loader is not None
AUDIT = module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class V9ResumeDeterminismTests(unittest.TestCase):
    def test_synthetic_checkpoint_resume_matches_uninterrupted_run(self) -> None:
        report = AUDIT.run_audit(device="cpu", synthetic=True)
        self.assertEqual(report["status"], "pass")
        self.assertTrue(all(report["checks"].values()))
        self.assertEqual(report["optimizer_steps"], 6)
        self.assertEqual(report["next_step"]["uninterrupted"], report["next_step"]["resumed"])


if __name__ == "__main__":
    unittest.main()
