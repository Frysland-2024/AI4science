"""Repo-scoped Skill asset checks. Safe and offline, no API or GPU calls."""
from pathlib import Path
import unittest
SKILLS = Path(__file__).resolve().parents[1] / ".agents" / "skills"
class TestPersonalScienceSkills(unittest.TestCase):
    def test_skill_entrypoints(self):
        for name in ("materials-investigation", "paper-lookup", "database-lookup", "pymatgen"):
            with self.subTest(name=name):
                p = SKILLS / name / "SKILL.md"
                self.assertTrue(p.is_file(), str(p))
                t = p.read_text(encoding="utf-8")
                self.assertTrue(t.startswith("---\n"), p)
                self.assertIn("\nname: " + name + "\n", t, p)
    def test_critical_resources(self):
        for p in (
            "K_DENSE_LICENSE.md",
            "paper-lookup/references/openalex.md",
            "paper-lookup/references/crossref.md",
            "paper-lookup/scripts/openalex_abstract.py",
            "paper-lookup/scripts/paginate.py",
            "database-lookup/references/cod.md",
            "database-lookup/references/materials-project.md",
            "database-lookup/references/retrieval-contract.md",
            "pymatgen/references/materials_project_api.md",
            "pymatgen/scripts/structure_analyzer.py",
            "pymatgen/scripts/mp_query.py",
        ):
            with self.subTest(path=p):
                self.assertTrue((SKILLS / p).is_file(), p)
if __name__ == "__main__":
    unittest.main()
