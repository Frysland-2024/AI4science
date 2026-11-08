"""PR hygiene should constrain prose sprawl, not legitimate experiment evidence."""
from __future__ import annotations
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_pr_hygiene.py"
spec = importlib.util.spec_from_file_location("pr_hygiene", SCRIPT)
guard = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(guard)


def change(path, added=10, status="A"):
    return {"path": path, "status": status, "added": added, "removed": 0}


class PRHygieneTests(unittest.TestCase):
    def check(self, files, title="docs: review", body="", existing=None):
        return guard.inspect(files, title, body, existing)

    def test_git_numstat_unicode_zero_and_tabs(self):
        from unittest.mock import patch

        # -z prevents core.quotePath from changing Unicode paths and ensures
        # tabs inside filenames cannot be mistaken for numstat separators.
        names = "A\0资料/新.md\0M\0src/a.py\0A\0docs/with\ttab.md\0"
        stats = "10\t0\t资料/新.md\00\t3\tsrc/a.py\02\t0\tdocs/with\ttab.md\0"
        with patch.object(guard, "git", side_effect=[names, stats]):
            actual = guard.changes_from_git("old", "new")
        self.assertEqual(actual, [
            change("资料/新.md", 10, "A"),
            {"path": "src/a.py", "status": "M", "added": 0, "removed": 3},
            change("docs/with\ttab.md", 2, "A"),
        ])

    def test_git_numstat_binary_file(self):
        from unittest.mock import patch

        with patch.object(guard, "git", side_effect=[
            "M\0reports/weights.npz\0",
            "-\t-\treports/weights.npz\0",
        ]):
            actual = guard.changes_from_git("old", "new")
        self.assertEqual(actual, [{
            "path": "reports/weights.npz", "status": "M",
            "added": 0, "removed": 0,
        }])

    def test_code_only_passes(self):
        errors, _, report = self.check([change("xrd_robustness/src/model.py", 70)],
                                        title="feat: train adapter")
        self.assertEqual(errors, [])
        self.assertEqual(report["source_changed_files"], 1)

    def test_one_new_prose_doc_requires_rationale(self):
        errors, _, _ = self.check([change("docs/NEW_PIPELINE_PLAN.md")])
        self.assertTrue(any("Docs rationale:" in x for x in errors))

    def test_rationale_avoids_failure_for_one_doc(self):
        reason = "Docs rationale: A distinct external protocol is necessary because the existing current-state file only records execution status."
        errors, _, _ = self.check([change("docs/NEW_PROTOCOL.md")], body=reason)
        self.assertEqual(errors, [])

    def test_three_new_docs_need_exception(self):
        files = [change(f"docs/note_{n}.md") for n in range(3)]
        reason = "Docs rationale: These explain experimental methodology rather than current research status."
        errors, _, _ = self.check(files, body=reason)
        self.assertTrue(any("limit" in x for x in errors))
        errors, _, _ = self.check(files, body=reason + "\nDocs exception: Separate experiment protocols are frozen for independently auditable study arms and cannot be merged.")
        self.assertEqual(errors, [])

    def test_archived_and_evidence_docs_exempt(self):
        files = [change("archive/2026/NOTES.md", 600), change("xrd_robustness/reports/RESULTS.md", 700),
                 change("docs/archive/old_protocol.md", 200)]
        errors, _, stats = self.check(files)
        self.assertEqual(errors, [])
        self.assertEqual(stats["evidence_and_archives_exempt"], 3)

    def test_large_narrative_diff_needs_exception(self):
        files = [change("docs/CURRENT_STATE.md", 450, "M")]
        errors, _, _ = self.check(files)
        self.assertTrue(any("budget" in x for x in errors))

    def test_history_write_requires_material_decision(self):
        files = [change("docs/PROJECT_HISTORY.md", 12, "M")]
        errors, _, _ = self.check(files)
        self.assertTrue(any("Research decision:" in x for x in errors))
        errors, _, _ = self.check(files, body="Research decision: A pre-existing methodological claim has been corrected against original experiment logs.")
        self.assertEqual(errors, [])

    def test_feature_pr_cannot_be_markdown_only(self):
        files = [change("README.md", 30, "M")]
        errors, _, _ = self.check(files, title="feat: implement new V11 trainer")
        self.assertTrue(any("no source/config/test" in x for x in errors))

    def test_plain_documentation_pr_is_allowed(self):
        files = [change("README.md", 30, "M")]
        errors, _, _ = self.check(files, title="docs: clarify benchmark")
        self.assertEqual(errors, [])

    def test_docs_heavy_source_pr_warns_not_fails(self):
        files = [change("README.md", 190, "M"), change("xrd_robustness/train.py", 10, "M")]
        errors, warnings, _ = self.check(files, title="feat: improve trainer")
        self.assertEqual(errors, [])
        self.assertTrue(any("Document-to-source" in x for x in warnings))

    def test_new_near_duplicate_filename_warns(self):
        reason = "Docs rationale: A separate protocol is proposed because it is independently frozen for reproducibility."
        files = [change("docs/PXRD_V11_PIPELINE_PLAN_20261109.md")]
        _, warnings, _ = self.check(files, body=reason,
                                    existing=["docs/PXRD_V11_PIPELINE_PLAN_20261103.md"])
        self.assertTrue(any("resembles existing" in x for x in warnings))

    def test_existing_markdown_modification_needs_no_new_docs_justification(self):
        files = [change("docs/README.md", 20, "M")]
        errors, _, stats = self.check(files)
        self.assertEqual(errors, [])
        self.assertEqual(stats["new_narrative_md"], 0)


if __name__ == "__main__":
    unittest.main()
