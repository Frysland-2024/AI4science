"""Offline tests for the PR Hygiene Gate."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.pr_hygiene_gate import Change, audit, parse_git_diff

def rationale(*paths):
    return (
        "Document rationale:\n"
        + "\n".join(paths)
        + "\nThis document cannot be merged into the existing README or current "
          "state file: it describes a distinct public interface with testable contracts.\n"
    )

def evidence_rationale(*paths):
    return (
        "Evidence rationale:\n"
        + "\n".join(paths)
        + "\nThese are reproducible reports for completed experiments, with run IDs "
          "and structured logs rather than routine implementation diaries.\n"
    )

class HygieneGateTests(unittest.TestCase):
    def test_normal_code_and_test_pr(self):
        w, e, m = audit([Change("src/model.py", "M", 80, 4),
                         Change("tests/test_model.py", "M", 23, 2)])
        self.assertEqual((w, e), ([], []))
        self.assertEqual(m["code_added"], 103)

    def test_new_general_doc_needs_rationale(self):
        _, e, _ = audit([Change("docs/NEW.md", "A", 65)])
        self.assertTrue(any("Document rationale" in item for item in e))

    def test_rationale_allows_one_new_doc(self):
        _, e, _ = audit([Change("docs/NEW.md", "A", 65)],
                        body=rationale("docs/NEW.md"))
        self.assertEqual(e, [])

    def test_rationale_must_name_each_doc(self):
        _, e, _ = audit([Change("docs/A.md", "A", 20),
                         Change("docs/B.md", "A", 20)],
                        body=rationale("docs/A.md"))
        self.assertTrue(any("Document rationale" in item for item in e))

    def test_two_docs_warn_with_rationale(self):
        paths = ("docs/A.md", "docs/B.md")
        w, e, _ = audit([Change(x, "A", 20) for x in paths],
                         body=rationale(*paths))
        self.assertEqual(e, [])
        self.assertTrue(any("2 new" in item for item in w))

    def test_three_docs_block_even_if_justified(self):
        paths = ("docs/A.md", "docs/B.md", "docs/C.md")
        _, e, _ = audit([Change(x, "A", 20) for x in paths],
                        body=rationale(*paths))
        self.assertTrue(any("3+" in item for item in e))

    def test_report_exception_with_rationale(self):
        path = "xrd_robustness/reports/VALIDATION_2.md"
        w, e, m = audit([Change(path, "A", 1250)],
                        body=evidence_rationale(path))
        self.assertEqual((w, e), ([], []))
        self.assertEqual(m["evidence_md_added"], 1250)

    def test_report_without_evidence_rationale_warns(self):
        w, e, _ = audit([Change("docs/RRUFF_EXTRA_AUDIT.md", "A", 1100)])
        self.assertEqual(e, [])
        self.assertTrue(any("Evidence rationale" in item for item in w))

    def test_history_archive_lane(self):
        w, e, m = audit([Change("docs/archive/OLD_CASE.md", "A", 1000)],
                        body=evidence_rationale("docs/archive/OLD_CASE.md"))
        self.assertEqual((w, e), ([], []))
        self.assertEqual(m["new_general_md"], 0)

    def test_large_general_doc_blocks(self):
        _, e, _ = audit([Change("docs/NEW.md", "A", 901)],
                        body=rationale("docs/NEW.md"))
        self.assertTrue(any("limit 900" in item for item in e))

    def test_general_growth_warns(self):
        w, e, _ = audit([Change("docs/REVIEWER_GUIDE.md", "M", 310)])
        self.assertEqual(e, [])
        self.assertTrue(any("310" in item for item in w))

    def test_code_pr_with_document_dominance_warns(self):
        w, e, _ = audit([Change("docs/REVIEWER_GUIDE.md", "M", 180),
                         Change("src/run.py", "M", 10),
                         Change("tests/test_run.py", "M", 15)])
        self.assertEqual(e, [])
        self.assertTrue(any("3x" in item for item in w))

    def test_code_without_tests_warns(self):
        w, e, _ = audit([Change("src/run.py", "M", 35)])
        self.assertEqual(e, [])
        self.assertTrue(any("without changed tests" in item for item in w))

    def test_doc_only_fix_is_valid(self):
        w, e, _ = audit([Change("README.md", "M", 12, 15)],
                        title="docs: fix dead link")
        self.assertEqual((w, e), ([], []))

    def test_claimed_implementation_without_code_warns(self):
        w, e, _ = audit([Change("docs/PLAN.md", "M", 25)],
                        title="Feature implemented")
        self.assertEqual(e, [])
        self.assertTrue(any("claims implementation" in item for item in w))

    def test_current_state_duplicated_without_link_warns(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "docs").mkdir()
            (root / "docs/NEW.md").write_text(
                "The official primary benchmark is RRUFF-Cu1011.\n",
                encoding="utf-8",
            )
            w, e, _ = audit([Change("docs/NEW.md", "A", 12)],
                            body=rationale("docs/NEW.md"), root=root)
            self.assertEqual(e, [])
            self.assertTrue(any("CURRENT_STATE" in item for item in w))

    def test_current_state_link_suppresses_duplication_warning(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "docs").mkdir()
            (root / "docs/NEW.md").write_text(
                "The official primary benchmark is RRUFF-Cu1011. "
                "See [Current state](CURRENT_STATE.md).\n", encoding="utf-8")
            w, e, _ = audit([Change("docs/NEW.md", "A", 12)],
                            body=rationale("docs/NEW.md"), root=root)
            self.assertEqual(e, [])
            self.assertFalse(any("CURRENT_STATE" in item for item in w))

    def test_unicode_and_zero_added_line_numstat(self):
        name_bytes = "A\0资料/新.md\0M\0src/a.py\0".encode()
        stats_bytes = "10\t0\t资料/新.md\00\t3\tsrc/a.py\0".encode()
        changes = parse_git_diff(name_bytes, stats_bytes)
        self.assertEqual([(x.path, x.added) for x in changes],
                         [("src/a.py", 0), ("资料/新.md", 10)])

    def test_rename_is_not_a_new_document(self):
        names = b"R095\0docs/old.md\0docs/new.md\0"
        stats = b"1\t0\t\0docs/old.md\0docs/new.md\0"
        changes = parse_git_diff(names, stats)
        self.assertEqual(changes, [Change("docs/new.md", "R", 1)])
        self.assertEqual(audit(changes)[2]["new_general_md"], 0)

    def test_binary_result_artifact(self):
        changes = parse_git_diff(
            b"A\0xrd_robustness/reports/metrics.npz\0",
            b"-\t-\txrd_robustness/reports/metrics.npz\0",
        )
        self.assertEqual(changes[0].added, 0)
        self.assertEqual(audit(changes)[2]["changed_machine_evidence_files"], 1)

if __name__ == "__main__":
    unittest.main()
