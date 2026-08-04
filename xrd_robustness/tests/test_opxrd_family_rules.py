"""
Tests for ferroelectric material family matching rules.
"""
import json
import os
import sys
import unittest
from collections import defaultdict

import yaml

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FAMILY_RULES = os.path.join(SCRIPT_DIR, "configs", "opxrd_ferroelectric_family_rules_v1.yaml")


class TestFamilyRulesConfig(unittest.TestCase):
    """Test the family rules YAML configuration."""

    @classmethod
    def setUpClass(cls):
        with open(DEFAULT_FAMILY_RULES, "r", encoding="utf-8") as f:
            cls.config = yaml.safe_load(f)

    def test_config_version(self):
        """Test config has correct schema version."""
        self.assertEqual(self.config.get("schema_version"), "opxrd-family-rules-v1")

    def test_families_not_empty(self):
        """Test that families list is not empty."""
        families = self.config.get("families", [])
        self.assertGreater(len(families), 0, "No families defined")

    def test_each_family_has_id(self):
        """Test each family has a unique family_id."""
        ids = set()
        for fam in self.config.get("families", []):
            fid = fam.get("family_id")
            self.assertIsNotNone(fid, f"Family missing family_id: {fam.get('family_name', 'UNKNOWN')}")
            self.assertNotIn(fid, ids, f"Duplicate family_id: {fid}")
            ids.add(fid)

    def test_each_family_has_rules(self):
        """Test each family has at least one matching rule."""
        for fam in self.config.get("families", []):
            rules = fam.get("rules", [])
            self.assertIsNotNone(rules, f"Family {fam.get('family_id')} missing rules")
            self.assertGreater(len(rules), 0,
                               f"Family {fam.get('family_id')} has no rules")

    def test_each_rule_has_fields(self):
        """Test each rule has required fields."""
        required = ["rule_id", "method", "confidence"]
        for fam in self.config.get("families", []):
            for rule in fam.get("rules", []):
                for field in required:
                    self.assertIn(field, rule,
                                  f"Rule {rule.get('rule_id', '?')} missing {field}")

    def test_valid_methods(self):
        """Test that all rules use valid matching methods."""
        valid_methods = {"formula_match", "element_set_match", "name_match"}
        for fam in self.config.get("families", []):
            for rule in fam.get("rules", []):
                method = rule.get("method", "")
                self.assertIn(method, valid_methods, f"Invalid method: {method}")

    def test_valid_confidence(self):
        """Test that all rules have valid confidence levels."""
        valid = {"high", "medium", "low"}
        for fam in self.config.get("families", []):
            for rule in fam.get("rules", []):
                conf = rule.get("confidence", "")
                self.assertIn(conf, valid, f"Invalid confidence: {conf}")

    def test_formula_rules_have_patterns(self):
        """Test that formula_match rules have patterns."""
        for fam in self.config.get("families", []):
            for rule in fam.get("rules", []):
                if rule["method"] == "formula_match":
                    patterns = rule.get("patterns", [])
                    self.assertGreater(len(patterns), 0,
                                       f"Formula rule {rule['rule_id']} has no patterns")

    def test_element_set_rules_have_required(self):
        """Test that element_set_match rules have require_elements."""
        for fam in self.config.get("families", []):
            for rule in fam.get("rules", []):
                if rule["method"] == "element_set_match":
                    self.assertIn("require_elements", rule,
                                  f"Element set rule {rule['rule_id']} missing require_elements")

    def test_families_have_categories(self):
        """Test each family has a valid category."""
        valid_categories = {"strict_ferroelectric", "ferroelectric_related", "uncertain", "exclude"}
        for fam in self.config.get("families", []):
            cat = fam.get("category", "")
            self.assertIn(cat, valid_categories,
                          f"Family {fam.get('family_id')} has invalid category: {cat}")

    def test_element_family_index_consistency(self):
        """Test that element family index entries correspond to real families."""
        index = self.config.get("element_family_index", {})
        family_ids = {f["family_id"] for f in self.config.get("families", [])}
        for element, refs in index.items():
            for ref in refs:
                self.assertIn(ref, family_ids,
                              f"Element index references unknown family: {ref}")


class TestSpecificFamilyRules(unittest.TestCase):
    """Test specific ferroelectric families for critical matching."""

    @classmethod
    def setUpClass(cls):
        with open(DEFAULT_FAMILY_RULES, "r", encoding="utf-8") as f:
            cls.config = yaml.safe_load(f)
        cls.families = {f["family_id"]: f for f in cls.config.get("families", [])}

    def test_batio3_matches(self):
        """Test BaTiO3 family matches expected compositions."""
        fam = self.families.get("BaTiO3_doped")
        self.assertIsNotNone(fam)
        # Check key patterns exist
        formula_rule = next((r for r in fam["rules"] if r["method"] == "formula_match"), None)
        self.assertIsNotNone(formula_rule, "BaTiO3_doped missing formula_match rule")
        patterns = [p.lower() for p in formula_rule.get("patterns", [])]
        self.assertIn("batio3", patterns)

    def test_pzt_matches(self):
        """Test PZT family matches expected compositions."""
        fam = self.families.get("PZT")
        self.assertIsNotNone(fam)
        has_pzt = any("PZT" in str(r.get("patterns", [])) for r in fam["rules"])
        self.assertTrue(has_pzt, "PZT family should match PZT patterns")

    def test_bifeo3_matches(self):
        """Test BiFeO3 family matches."""
        fam = self.families.get("BiFeO3")
        self.assertIsNotNone(fam)

    def test_linbo3_matches(self):
        """Test LiNbO3 family matches."""
        fam = self.families.get("LiNbO3")
        self.assertIsNotNone(fam)

    def test_knn_matches(self):
        """Test KNN family matches."""
        fam = self.families.get("KNN")
        self.assertIsNotNone(fam)

    def test_aurivillius_has_name_rules(self):
        """Test Aurivillius family has name-based matching."""
        fam = self.families.get("Aurivillius")
        self.assertIsNotNone(fam)
        has_name = any(r["method"] == "name_match" for r in fam["rules"])
        self.assertTrue(has_name, "Aurivillius should have name_match rules")

    def test_exclusion_rules(self):
        """Test that exclusion rules are properly defined."""
        global_excl = self.config.get("global_exclusions", [])
        self.assertGreater(len(global_excl), 0, "No global exclusions defined")
        expected_reasons = {"exclude_non_oxide", "exclude_polymer_organic", "exclude_metals"}
        found_reasons = {e.get("rule_id", "") for e in global_excl}
        self.assertTrue(expected_reasons.issubset(found_reasons),
                        f"Missing exclusion rules: {expected_reasons - found_reasons}")


class TestFamilyRuleMatching(unittest.TestCase):
    """Test end-to-end matching for representative compositions."""

    @classmethod
    def setUpClass(cls):
        with open(DEFAULT_FAMILY_RULES, "r", encoding="utf-8") as f:
            cls.config = yaml.safe_load(f)

    def _find_matches(self, composition: str) -> list:
        """Simple inline matching for testing."""
        import re
        elements = set()
        for match in re.finditer(r'([A-Z][a-z]?)', composition):
            elements.add(match.group(1))

        matches = []
        for family in self.config.get("families", []):
            for rule in family.get("rules", []):
                method = rule.get("method", "")

                if method == "formula_match":
                    patterns = rule.get("patterns", [])
                    require_elements = set(rule.get("require_elements", []))
                    require_any = rule.get("require_any", [])
                    if any(p.lower() in composition.lower() for p in patterns):
                        if require_elements.issubset(elements):
                            if not require_any or any(a.lower() in composition.lower() for a in require_any):
                                matches.append({
                                    "family_rule_id": rule["rule_id"],
                                    "matched_family": family["family_id"],
                                    "family_name": family["family_name"],
                                    "category": family.get("category", "uncertain"),
                                })
                                break

                elif method == "element_set_match":
                    require_elements = set(rule.get("require_elements", []))
                    require_any = set(rule.get("require_any_elements", []))
                    allow_extra = set(rule.get("allow_extra_elements", []))
                    max_extra = rule.get("max_extra_elements", 999)
                    if require_elements.issubset(elements):
                        if not require_any or require_any.intersection(elements):
                            extra = elements - require_elements
                            if allow_extra and extra - allow_extra:
                                continue
                            if len(extra) > max_extra:
                                continue
                            matches.append({
                                "family_rule_id": rule["rule_id"],
                                "matched_family": family["family_id"],
                                "family_name": family["family_name"],
                                "category": family.get("category", "uncertain"),
                            })
                            break

        return matches

    def test_batio3_matches(self):
        """BaTiO3 should match BaTiO3 family."""
        matches = self._find_matches("BaTiO3")
        family_ids = {m["matched_family"] for m in matches}
        self.assertIn("BaTiO3_doped", family_ids)

    def test_pzt_matches(self):
        """Pb(Zr0.52Ti0.48)O3 should match PZT."""
        matches = self._find_matches("Pb(Zr0.52Ti0.48)O3")
        family_ids = {m["matched_family"] for m in matches}
        self.assertIn("PZT", family_ids)

    def test_bifeo3_matches(self):
        """BiFeO3 should match BiFeO3 family."""
        matches = self._find_matches("BiFeO3")
        family_ids = {m["matched_family"] for m in matches}
        self.assertIn("BiFeO3", family_ids)

    def test_linbo3_matches(self):
        """LiNbO3 should match LiNbO3 family."""
        matches = self._find_matches("LiNbO3")
        family_ids = {m["matched_family"] for m in matches}
        self.assertIn("LiNbO3", family_ids)

    def test_knn_matches(self):
        """(K0.5Na0.5)NbO3 should match KNN."""
        matches = self._find_matches("(K0.5Na0.5)NbO3")
        family_ids = {m["matched_family"] for m in matches}
        self.assertIn("KNN", family_ids)

    def test_srtio3_not_strict_fe(self):
        """SrTiO3 should match SrTiO3_related, and be ferroelectric_related, not strict."""
        matches = self._find_matches("SrTiO3")
        family_ids = {m["matched_family"] for m in matches}
        self.assertIn("SrTiO3_related", family_ids)
        for m in matches:
            if m["matched_family"] == "SrTiO3_related":
                self.assertEqual(m["category"], "ferroelectric_related")

    def test_sio2_no_match(self):
        """SiO2 should not match any ferroelectric family."""
        matches = self._find_matches("SiO2")
        self.assertEqual(len(matches), 0, "SiO2 should not match FE families")

    def test_nacl_no_match(self):
        """NaCl should not match any ferroelectric family."""
        matches = self._find_matches("NaCl")
        self.assertEqual(len(matches), 0, "NaCl should not match FE families")

    def test_bnt_matches(self):
        """Bi0.5Na0.5TiO3 should match BNT."""
        matches = self._find_matches("Bi0.5Na0.5TiO3")
        family_ids = {m["matched_family"] for m in matches}
        self.assertIn("BNT", family_ids)

    def test_pmn_matches(self):
        """Pb(Mg1/3Nb2/3)O3 should match relaxor FE."""
        matches = self._find_matches("Pb(Mg1/3Nb2/3)O3")
        family_ids = {m["matched_family"] for m in matches}
        self.assertIn("Relaxor_FE", family_ids)


if __name__ == "__main__":
    unittest.main()
