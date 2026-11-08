"""Tests: the guard catches explicit contradictions and ignores archives."""
from __future__ import annotations
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_docs_consistency.py"
spec = importlib.util.spec_from_file_location("doc_guard", SCRIPT)
guard = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(guard)

class DocsGuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.put("AGENTS.md", """# AGENTS
## Current research direction (2026-11-09)
**Active:** PXRD seven-crystal-system classification. First complete [Issue #61](https://github.com/example) (readiness); only then consider [Issue #55](https://github.com/example) (HPO).
## Historical policy
The old freeze is archived.
""")
        self.put("docs/CURRENT_STATE.md", """2026-11-09: 没有启动 HPO。
**Decision: RRUFF-Cu1011 is the official prospective PRIMARY seven-system real-domain benchmark**.
""")
        for filename in guard.PUBLIC_DOCS:
            self.put(filename, "# Current project\nPrimary RRUFF-Cu1011 benchmark.\n")

    def put(self, filename, text):
        path = self.root / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def issues(self):
        return guard.inspect(self.root)

    def test_current_state_passes(self):
        self.assertEqual(self.issues(), [])

    def test_old_writeup_freeze_fails(self):
        self.put("docs/REVIEWER_GUIDE.md", "RRUFF-Cu1011. No new experiments are in scope.\n")
        self.assertTrue(any("freeze" in x for x in self.issues()))

    def test_old_primary_benchmark_fails(self):
        self.put("README.md", "Our primary RRUFF-1034 benchmark; historical RRUFF-Cu1011.\n")
        self.assertTrue(any("RRUFF-1034" in x and "primary" in x for x in self.issues()))

    def test_archived_cohort_is_not_a_violation(self):
        self.put("README.md", "Primary RRUFF-Cu1011, historical RRUFF-1034 was superseded.\n")
        self.assertEqual(self.issues(), [])

    def test_unrun_v11_completion_fails(self):
        self.put("README.md", "RRUFF-Cu1011. V11 training completed.\n")
        self.assertTrue(any("claimed complete" in x for x in self.issues()))

    def test_broken_link_fails(self):
        self.put("README.md", "RRUFF-Cu1011. [missing](docs/nonexistent.md)\n")
        self.assertTrue(any("broken local link" in x for x in self.issues()))

    def test_external_and_anchor_links_are_ignored(self):
        self.put("README.md", "RRUFF-Cu1011. [external](https://example.com) [jump](#top)\n")
        self.assertEqual(self.issues(), [])

    def test_archived_file_is_excluded(self):
        self.put("docs/PROJECT_HISTORY.md", "No new experiments are in scope. Primary RRUFF-1034.\n")
        self.assertEqual(self.issues(), [])

    def test_missing_authority_fails(self):
        (self.root / "AGENTS.md").unlink()
        self.assertTrue(any("required current document" in x for x in self.issues()))

if __name__ == "__main__":
    unittest.main()
