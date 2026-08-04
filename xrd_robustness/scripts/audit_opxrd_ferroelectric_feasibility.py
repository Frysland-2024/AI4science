#!/usr/bin/env python3
"""
opXRD Ferroelectric Feasibility Auditor v1
===========================================
Model-blind audit of opXRD experimental PXRD data for ferroelectric-related
functional oxide/ceramic crystal-system classification feasibility.

Reads the opXRD metadata manifest (from download_opxrd_metadata.py) and:
  1. Applies ferroelectric family matching rules
  2. Maps space groups to crystal systems
  3. Applies experimental spectrum quality filters
  4. Generates comprehensive feasibility statistics
  5. Produces machine-readable and human-readable reports

Constraints:
  - No model checkpoints loaded
  - No real-XRD inference run
  - RRUFF-371 not modified
  - JS-only mainline, simulated training/test remain frozen

Usage:
    python audit_opxrd_ferroelectric_feasibility.py --help
    python audit_opxrd_ferroelectric_feasibility.py --manifest <path> --family-rules <path> --filter-config <path>
    python audit_opxrd_ferroelectric_feasibility.py --manifest <path> --dry-run
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

# ----------------------------------------------------------
# Paths relative to this script
# ----------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_MANIFEST = os.path.join(PROJECT_ROOT, "data", "real_xrd", "opxrd", "opxrd_metadata_manifest_v1.csv")
DEFAULT_FAMILY_RULES = os.path.join(PROJECT_ROOT, "configs", "opxrd_ferroelectric_family_rules_v1.yaml")
DEFAULT_FILTER_CONFIG = os.path.join(PROJECT_ROOT, "configs", "opxrd_feasibility_filters_v1.yaml")
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "reports")

AUDIT_VERSION = "opxrd-ferroelectric-feasibility-v1"
TARGET_CRYSTAL_SYSTEMS = [
    "triclinic", "monoclinic", "orthorhombic",
    "tetragonal", "trigonal", "hexagonal", "cubic"
]


# ----------------------------------------------------------
# Space group mapping
# ----------------------------------------------------------
def build_sg_range_map(ranges: Dict[str, List[int]]) -> Dict[int, str]:
    """Build a lookup dict from space group number to crystal system."""
    mapping = {}
    for system, bounds in ranges.items():
        if len(bounds) == 2:
            for sg in range(bounds[0], bounds[1] + 1):
                mapping[sg] = system
    return mapping


def build_sg_symbol_map(symbol_map: Dict[str, List[str]]) -> Dict[str, str]:
    """Build a lookup from normalized space group symbol to crystal system."""
    mapping = {}
    for system, symbols in symbol_map.items():
        for sym in symbols:
            normalized = normalize_sg_symbol(sym)
            mapping[normalized] = system
    return mapping


def normalize_sg_symbol(symbol: str) -> str:
    """Normalize a space group symbol for comparison."""
    if not symbol:
        return ""
    s = symbol.strip()
    # Remove spaces
    s = s.replace(" ", "")
    # Standardize subscripts
    s = s.replace("_", "")
    # Remove parentheses
    s = s.replace("(", "").replace(")", "")
    # Remove colons
    s = s.replace(":", "")
    # Standardize overbar notation
    s = s.replace("\u0305", "").replace("\u203e", "").replace("bar", "")
    # Common: "P21/c" -> "P21c"
    s = s.replace("/", "")
    return s.upper()


# ----------------------------------------------------------
# Element and formula parsing
# ----------------------------------------------------------
ELEMENT_PATTERN = re.compile(r'([A-Z][a-z]?)')
NUMBER_PATTERN = re.compile(r'([A-Z][a-z]?)(\d*\.?\d*)')


def parse_elements(formula: str) -> Set[str]:
    """Extract unique elements from a chemical formula string."""
    elements = set()
    for match in ELEMENT_PATTERN.finditer(formula):
        elem = match.group(1)
        if len(elem) <= 2 and elem[0].isupper():
            elements.add(elem)
    return elements


def normalize_formula(formula: str) -> str:
    """Normalize a chemical formula string for comparison."""
    if not formula:
        return ""
    s = formula.strip()
    # Remove whitespace
    s = re.sub(r'\s+', '', s)
    # Remove isotope prefixes like "2H", "18O"
    # Keep the element mapping simple
    return s


# ----------------------------------------------------------
# Family matching engine
# ----------------------------------------------------------
class FamilyMatcher:
    """Applies family matching rules from the family rules config."""

    def __init__(self, rules_config: Dict[str, Any]):
        self.families = rules_config.get("families", [])
        self.global_exclusions = rules_config.get("global_exclusions", [])
        self.labels = rules_config.get("classification_labels", {})

    def match_record(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Match a single metadata record to material families."""
        matches = []
        composition = record.get("chemical_composition", "")
        if not composition:
            return matches

        elements = parse_elements(composition)
        if not elements:
            return matches

        # Check global exclusions first
        for excl in self.global_exclusions:
            if self._check_global_exclusion(excl, elements, record):
                return [{
                    "family_id": "global_exclusion",
                    "matched_family": None,
                    "match_method": "global_exclusion",
                    "match_confidence": "high",
                    "manual_review_required": False,
                    "exclusion_reason": excl.get("reason", excl.get("rule_id", ""))
                }]

        for family in self.families:
            family_matches = self._match_family(family, elements, composition, record)
            matches.extend(family_matches)

        return matches

    def _check_global_exclusion(self, excl: Dict, elements: Set[str], record: Dict) -> bool:
        """Check if a record matches a global exclusion rule."""
        rule_id = excl.get("rule_id", "")

        if rule_id == "exclude_non_oxide":
            return "O" not in elements

        if rule_id == "exclude_metals":
            return ("O" not in elements and
                    "S" not in elements and
                    "F" not in elements and
                    "Cl" not in elements and
                    "Br" not in elements and
                    "I" not in elements)

        if rule_id == "exclude_polymer_organic":
            allowed = {"C", "H", "N", "O", "S", "Cl", "Br", "I", "F"}
            return elements.issubset(allowed) and "C" in elements

        if rule_id == "exclude_common_nonFE_minerals":
            # Check tags and institution metadata for mineral names
            tags = record.get("tags", "") or ""
            meta_raw = record.get("metadata_raw", "") or ""
            label_raw = record.get("label_raw", "") or ""
            composition = record.get("chemical_composition", "") or ""
            combined = f"{tags} {meta_raw} {label_raw} {composition}"
            patterns = excl.get("patterns", [])
            return any(p.lower() in combined.lower() for p in patterns)

        return False

    def _match_family(self, family: Dict, elements: Set[str],
                      composition: str, record: Dict) -> List[Dict[str, Any]]:
        """Try all matching rules for a single family."""
        results = []
        for rule in family.get("rules", []):
            method = rule.get("method", "")
            confidence = rule.get("confidence", "medium")
            manual_review = rule.get("manual_review", True)
            matched = False

            if method == "formula_match":
                matched = self._match_formula(rule, composition.lower())
            elif method == "element_set_match":
                matched = self._match_element_set(rule, elements)
            elif method == "name_match":
                matched = self._match_name(rule, record)
            else:
                continue

            if matched:
                # Check family-level exclusions
                excluded = False
                for excl_pattern in family.get("exclusions", []):
                    if excl_pattern.lower() in composition.lower():
                        excluded = True
                        break

                if not excluded:
                    results.append({
                        "family_rule_id": rule["rule_id"],
                        "matched_family": family["family_id"],
                        "family_name": family["family_name"],
                        "category": family.get("category", "uncertain"),
                        "match_method": method,
                        "match_confidence": confidence,
                        "manual_review_required": manual_review,
                    })
        return results

    def _match_formula(self, rule: Dict, composition_lower: str) -> bool:
        """Check if composition string matches formula patterns."""
        patterns = rule.get("patterns", [])
        require_elements = set(rule.get("require_elements", []))
        require_any = rule.get("require_any", [])

        if not patterns:
            return False

        # Must match at least one pattern
        pattern_match = any(p.lower() in composition_lower for p in patterns)
        if not pattern_match:
            return False

        # Extract elements from composition
        comp_elements = parse_elements(composition_lower.upper())

        # Required elements check
        if require_elements and not require_elements.issubset(comp_elements):
            return False

        # Require any check
        if require_any:
            # Check that at least one of require_any matches as a substring
            if not any(any_token.lower() in composition_lower for any_token in require_any):
                return False

        return True

    def _match_element_set(self, rule: Dict, elements: Set[str]) -> bool:
        """Check if elements match required and allowed sets."""
        require_elements = set(rule.get("require_elements", []))
        require_any = set(rule.get("require_any_elements", []))
        allow_extra = set(rule.get("allow_extra_elements", []))
        max_extra = rule.get("max_extra_elements", 5)

        if not require_elements:
            return False

        # Must have all required elements
        if not require_elements.issubset(elements):
            return False

        # Must have at least one of require_any
        if require_any and not require_any.intersection(elements):
            return False

        # Extra elements check
        extra = elements - require_elements
        if allow_extra:
            forbidden = extra - allow_extra
            if forbidden:
                return False

        if len(extra) > max_extra:
            return False

        return True

    def _match_name(self, rule: Dict, record: Dict) -> bool:
        """Match based on material names and aliases."""
        patterns = rule.get("patterns", [])
        tags = record.get("tags", "") or ""
        meta_raw = record.get("metadata_raw", "") or ""
        label_raw = record.get("label_raw", "") or ""
        composition = record.get("chemical_composition", "") or ""
        combined = f"{tags} {meta_raw} {label_raw} {composition}"
        return any(p.lower() in combined.lower() for p in patterns)


# ----------------------------------------------------------
# Crystal system labeler
# ----------------------------------------------------------
class CrystalSystemLabeler:
    """Maps space group information to crystal systems."""

    def __init__(self, filter_config: Dict[str, Any]):
        sg_ranges = filter_config.get("space_group_mapping", {})
        sg_symbols = filter_config.get("space_group_symbol_map", {})
        self.sg_number_map = build_sg_range_map(sg_ranges)
        self.sg_symbol_map = build_sg_symbol_map(sg_symbols)

    def determine_crystal_system(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Determine crystal system from available labels."""
        result = {
            "crystal_system": None,
            "space_group_number": record.get("space_group_number"),
            "space_group_symbol": record.get("space_group_symbol"),
            "label_source": None,
            "label_confidence": None,
            "label_conflict": False,
            "manual_review_required": False,
        }

        sg_num = record.get("space_group_number")
        sg_sym = record.get("space_group_symbol")

        # Handle empty string / None / non-numeric
        try:
            sg_num_int = int(sg_num) if sg_num is not None and sg_num != "" else None
        except (ValueError, TypeError):
            sg_num_int = None

        system_from_num = None
        system_from_sym = None

        if sg_num_int is not None:
            system_from_num = self.sg_number_map.get(sg_num_int)
            if system_from_num:
                result["label_source"] = "space_group_number"

        if sg_sym is not None and sg_sym != "":
            normalized = normalize_sg_symbol(str(sg_sym))
            system_from_sym = self.sg_symbol_map.get(normalized)
            if system_from_sym:
                if result["label_source"] is None:
                    result["label_source"] = "space_group_symbol"

        # Conflict detection
        if system_from_num and system_from_sym:
            if system_from_num != system_from_sym:
                result["label_conflict"] = True
                result["manual_review_required"] = True
                # Prefer number
                result["crystal_system"] = system_from_num
                result["label_confidence"] = "medium"
            else:
                result["crystal_system"] = system_from_num
                result["label_confidence"] = "high"
        elif system_from_num:
            result["crystal_system"] = system_from_num
            result["label_confidence"] = "high" if sg_num_int is not None else "medium"
        elif system_from_sym:
            result["crystal_system"] = system_from_sym
            result["label_confidence"] = "medium"

        return result


# ----------------------------------------------------------
# Quality filter
# ----------------------------------------------------------
class QualityFilter:
    """Applies experimental spectrum quality filters."""

    def __init__(self, filter_config: Dict[str, Any]):
        self.config = filter_config.get("quality_filters", {})

    def check(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Check a record against quality filters. Returns (passed, reasons)."""
        reasons = []

        # Check if simulated
        if record.get("is_simulated") is True:
            reasons.append("simulated_pattern")

        # Data points
        n = record.get("two_theta_count", 0)
        min_pts = self.config.get("minimum_data_points", 50)
        if n < min_pts:
            reasons.append("insufficient_points")

        # 2theta range
        tmin = record.get("two_theta_min")
        tmax = record.get("two_theta_max")
        if tmin is not None and tmax is not None:
            if tmax - tmin < self.config.get("minimum_2theta_range", 5.0):
                reasons.append("narrow_2theta_range")

        # Monotonic
        if self.config.get("require_monotonic_axis", True):
            if not record.get("two_theta_monotonic", True):
                reasons.append("non_monotonic_axis")

        # Nonzero intensity
        nz_frac = record.get("intensity_nonzero_fraction")
        if nz_frac is not None:
            if nz_frac == 0:
                reasons.append("no_intensity")
            elif nz_frac < (1 - self.config.get("max_zero_fraction", 0.95)):
                reasons.append("too_many_zeros")

        # Model range overlap
        if tmin is not None and tmax is not None:
            model_min = self.config.get("model_2theta_min", 5.0)
            model_max = self.config.get("model_2theta_max", 60.0)
            overlap = min(tmax, model_max) - max(tmin, model_min)
            total_range = tmax - tmin
            if total_range > 0 and overlap / total_range < self.config.get("min_overlap_fraction", 0.3):
                reasons.append("no_overlap_with_model_range")

        # Space group label
        if record.get("space_group_number") is None and record.get("space_group_symbol") is None:
            reasons.append("no_space_group_label")

        return {
            "passed": len(reasons) == 0,
            "reasons": reasons,
        }


# ----------------------------------------------------------
# Main audit engine
# ----------------------------------------------------------
class FeasibilityAuditor:
    """Orchestrates the full feasibility audit."""

    def __init__(self, manifest_path: str, family_rules_path: str, filter_config_path: str):
        self.manifest_path = manifest_path
        self.records = []
        self.results = []

        # Load configs
        with open(family_rules_path, "r", encoding="utf-8") as f:
            self.family_rules = yaml.safe_load(f)
        with open(filter_config_path, "r", encoding="utf-8") as f:
            self.filter_config = yaml.safe_load(f)

        # Initialize engines
        self.matcher = FamilyMatcher(self.family_rules)
        self.labeler = CrystalSystemLabeler(self.filter_config)
        self.qfilter = QualityFilter(self.filter_config)

    def load_manifest(self):
        """Load the metadata manifest CSV."""
        print(f"Loading manifest: {self.manifest_path}")
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.records = list(reader)

        # Convert numeric fields
        for r in self.records:
            for field in ["space_group_number", "two_theta_count", "intensity_count",
                          "num_phases", "file_size_bytes"]:
                if field in r and r[field]:
                    try:
                        if field == "file_size_bytes":
                            r[field] = int(r[field])
                        elif field in ("space_group_number", "two_theta_count",
                                       "intensity_count", "num_phases"):
                            r[field] = int(float(r[field]))
                    except (ValueError, TypeError):
                        r[field] = None
            for field in ["two_theta_min", "two_theta_max", "intensity_nonzero_fraction"]:
                if field in r and r[field]:
                    try:
                        r[field] = float(r[field])
                    except (ValueError, TypeError):
                        r[field] = None
            for field in ["is_simulated"]:
                if field in r and r[field]:
                    v = r[field].strip().lower()
                    if v == "true":
                        r[field] = True
                    elif v == "false":
                        r[field] = False
                    elif v == "none":
                        r[field] = None

        print(f"Loaded {len(self.records)} records")

    def audit(self):
        """Run the full audit on all records."""
        print("Running feasibility audit...")
        start = time.time()

        for i, record in enumerate(self.records):
            if (i + 1) % 10000 == 0:
                print(f"  Audited {i+1}/{len(self.records)} records...")

            result = self._audit_one(record)
            self.results.append(result)

        elapsed = time.time() - start
        print(f"Audited {len(self.results)} records in {elapsed:.1f}s")

    def _audit_one(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Audit a single metadata record."""
        result = {
            "scan_id": record.get("scan_id", ""),
            "contributor": record.get("contributor", ""),
            "source_file": record.get("source_file", ""),
            "file_sha256": record.get("file_sha256", ""),
        }

        # Quality filter
        qc = self.qfilter.check(record)
        result["qc_passed"] = qc["passed"]
        result["qc_reasons"] = qc["reasons"]

        # Crystal system labeling
        cs = self.labeler.determine_crystal_system(record)
        result.update(cs)

        # Family matching
        if record.get("chemical_composition"):
            family_matches = self.matcher.match_record(record)
        else:
            family_matches = []

        result["family_matches"] = family_matches
        result["num_matches"] = len(family_matches)

        # Determine best classification
        best_category = None
        for m in family_matches:
            cat = m.get("category", "uncertain")
            if best_category is None:
                best_category = cat
            elif cat == "strict_ferroelectric":
                best_category = cat
            elif cat == "ferroelectric_related" and best_category != "strict_ferroelectric":
                best_category = cat
            elif cat == "uncertain" and best_category not in ("strict_ferroelectric", "ferroelectric_related"):
                best_category = cat

        if not family_matches and record.get("chemical_composition"):
            best_category = "exclude"
        elif not family_matches:
            best_category = "exclude"

        result["classification"] = best_category or "exclude"

        # Determine if candidate
        is_candidate = (
            qc["passed"] and
            result["crystal_system"] is not None and
            best_category in ("strict_ferroelectric", "ferroelectric_related")
        )
        result["is_candidate"] = is_candidate

        return result

    def generate_statistics(self) -> Dict[str, Any]:
        """Generate comprehensive statistics from audit results."""
        stats = {
            "audit_version": AUDIT_VERSION,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "manifest_path": self.manifest_path,
            "total_records": len(self.results),
        }

        # Overall counts
        total = len(self.results)
        simulated = sum(1 for r in self.results if any("simulated_pattern" in qc for qc in [r.get("qc_reasons", [])]))
        experimental = total - simulated

        qc_passed = sum(1 for r in self.results if r["qc_passed"])
        with_cs = sum(1 for r in self.results if r["crystal_system"] is not None)
        with_cs_and_qc = sum(1 for r in self.results if r["crystal_system"] is not None and r["qc_passed"])
        candidates = sum(1 for r in self.results if r["is_candidate"])

        strict_fe = sum(1 for r in self.results if r["classification"] == "strict_ferroelectric" and r["qc_passed"] and r["crystal_system"])
        fe_related = sum(1 for r in self.results if r["classification"] == "ferroelectric_related" and r["qc_passed"] and r["crystal_system"])

        stats["overall"] = {
            "total_records": total,
            "simulated_records": simulated,
            "experimental_records": experimental,
            "qc_passed_records": qc_passed,
            "with_crystal_system": with_cs,
            "with_cs_and_qc_passed": with_cs_and_qc,
            "candidate_records": candidates,
            "strict_ferroelectric_candidates": strict_fe,
            "ferroelectric_related_candidates": fe_related,
        }

        # By crystal system
        cs_stats = defaultdict(lambda: {
            "raw_records": 0,
            "candidate_records": 0,
            "label_reliable_records": 0,
            "label_conflicts": 0,
            "strict_ceramic_count": 0,
            "relaxed_domain_count": 0,
            "manual_review_count": 0,
        })
        for r in self.results:
            cs = r.get("crystal_system")
            if cs:
                cs_stats[cs]["raw_records"] += 1
                if r.get("label_confidence") == "high":
                    cs_stats[cs]["label_reliable_records"] += 1
                if r.get("label_conflict"):
                    cs_stats[cs]["label_conflicts"] += 1
                if r.get("is_candidate"):
                    cs_stats[cs]["candidate_records"] += 1
                    if r["classification"] == "strict_ferroelectric":
                        cs_stats[cs]["strict_ceramic_count"] += 1
                    elif r["classification"] == "ferroelectric_related":
                        cs_stats[cs]["relaxed_domain_count"] += 1
                if r.get("manual_review_required"):
                    cs_stats[cs]["manual_review_count"] += 1
        stats["by_crystal_system"] = {k: dict(v) for k, v in sorted(cs_stats.items())}

        # By family
        family_stats = defaultdict(lambda: {
            "records": 0,
            "candidates": 0,
            "crystal_systems": set(),
            "contributors": set(),
            "classification": None,
        })
        for r in self.results:
            for m in r.get("family_matches", []):
                fid = m.get("matched_family", "")
                if fid and fid != "global_exclusion":
                    family_stats[fid]["records"] += 1
                    if r["is_candidate"]:
                        family_stats[fid]["candidates"] += 1
                    if r.get("crystal_system"):
                        family_stats[fid]["crystal_systems"].add(r["crystal_system"])
                    family_stats[fid]["contributors"].add(r.get("contributor", ""))
                    family_stats[fid]["classification"] = m.get("category", "")
        stats["by_family"] = {
            k: {
                "records": v["records"],
                "candidates": v["candidates"],
                "crystal_systems": sorted(v["crystal_systems"]),
                "num_crystal_systems": len(v["crystal_systems"]),
                "contributors": sorted(v["contributors"]),
                "num_contributors": len(v["contributors"]),
                "classification": v["classification"],
            }
            for k, v in sorted(family_stats.items())
        }

        # By contributor
        contrib_stats = defaultdict(lambda: {
            "records": 0,
            "candidates": 0,
            "with_labels": 0,
        })
        for r in self.results:
            c = r.get("contributor", "unknown")
            contrib_stats[c]["records"] += 1
            if r["is_candidate"]:
                contrib_stats[c]["candidates"] += 1
            if r["crystal_system"]:
                contrib_stats[c]["with_labels"] += 1
        stats["by_contributor"] = {k: dict(v) for k, v in sorted(contrib_stats.items())}

        # Exclusion reasons
        exclusion_counts = Counter()
        for r in self.results:
            for reason in r.get("qc_reasons", []):
                exclusion_counts[reason] += 1
            if r["classification"] == "exclude" and not r.get("qc_reasons"):
                exclusion_counts["not_target_domain"] += 1
        stats["exclusion_reasons"] = dict(exclusion_counts.most_common())

        # Shortcut risk analysis
        shortcut = self._compute_shortcut_risks()
        stats["shortcut_risk"] = shortcut

        # Go/No-Go decision
        gate = self._compute_gate_decision(stats)
        stats["gate_decision"] = gate

        return stats

    def _compute_shortcut_risks(self) -> Dict[str, Any]:
        """Compute shortcut risk metrics: P(family|cs), P(institution|cs), P(project|cs)."""
        candidates = [r for r in self.results if r["is_candidate"]]

        # P(material_family | crystal_system)
        cs_family = defaultdict(Counter)
        for r in candidates:
            cs = r.get("crystal_system")
            if not cs:
                continue
            for m in r.get("family_matches", []):
                fid = m.get("matched_family", "")
                if fid and fid != "global_exclusion":
                    cs_family[cs][fid] += 1

        # P(institution | crystal_system)
        cs_inst = defaultdict(Counter)
        for r in candidates:
            cs = r.get("crystal_system")
            if cs:
                cs_inst[cs][r.get("contributor", "unknown")] += 1

        # P(composition | crystal_system) — top 3 compositions per class
        cs_comp = defaultdict(Counter)
        for r in candidates:
            cs = r.get("crystal_system")
            if cs:
                # Use first family match as composition proxy
                for m in r.get("family_matches", []):
                    if m.get("matched_family"):
                        cs_comp[cs][m["matched_family"]] += 1
                        break

        # Identify high-risk shortcuts
        risks = []
        for cs in TARGET_CRYSTAL_SYSTEMS:
            families = cs_family.get(cs, Counter())
            institutions = cs_inst.get(cs, Counter())

            total_f = sum(families.values())
            total_i = sum(institutions.values())
            top_family = families.most_common(1)
            top_inst = institutions.most_common(1)

            risk_level = "LOW"
            risk_reasons = []

            if top_family and total_f > 0:
                p_top_family = top_family[0][1] / total_f
                if p_top_family > 0.5:
                    risk_level = "HIGH"
                    risk_reasons.append(f"P({top_family[0][0]}|{cs}) = {p_top_family:.2f}")

            if top_inst and total_i > 0:
                p_top_inst = top_inst[0][1] / total_i
                if p_top_inst > 0.5:
                    if risk_level != "HIGH":
                        risk_level = "MEDIUM"
                    risk_reasons.append(f"P({top_inst[0][0]}|{cs}) = {p_top_inst:.2f}")

            risks.append({
                "crystal_system": cs,
                "total_candidates": total_f,
                "risk_level": risk_level,
                "risk_reasons": risk_reasons,
                "top_family": top_family[0] if top_family else None,
                "top_institution": top_inst[0] if top_inst else None,
            })

        return {
            "cs_family_distribution": {k: dict(v.most_common(5)) for k, v in cs_family.items()},
            "cs_institution_distribution": {k: dict(v.most_common(5)) for k, v in cs_inst.items()},
            "risks": risks,
            "any_high_risk": any(r["risk_level"] == "HIGH" for r in risks),
        }

    def _compute_gate_decision(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Compute Go/No-Go decision based on pre-specified gates."""
        cs_stats = stats.get("by_crystal_system", {})

        # For seven-class gate
        seven_class_pass = True
        seven_class_details = {}

        for cs in TARGET_CRYSTAL_SYSTEMS:
            scs = cs_stats.get(cs, {})
            # We need to estimate unique samples. Since we haven't done grouping yet,
            # use candidate_records as a rough proxy with a conservative deflator.
            # The actual independent sample count requires grouping analysis.
            candidates = scs.get("candidate_records", 0)
            # Conservative estimate: assume 3:1 ratio of scans to samples
            est_samples = candidates // 3

            families = stats.get("by_family", {})
            cs_families = set()
            for fid, finfo in families.items():
                if cs in finfo.get("crystal_systems", []):
                    cs_families.add(fid)

            detail = {
                "candidate_records": candidates,
                "estimated_independent_samples": max(est_samples, 0),
                "num_families": len(cs_families),
                "families": sorted(cs_families),
            }

            detail["meets_25_samples"] = detail["estimated_independent_samples"] >= 25
            detail["meets_3_families"] = detail["num_families"] >= 3

            if not detail["meets_25_samples"] or not detail["meets_3_families"]:
                seven_class_pass = False

            seven_class_details[cs] = detail

        # For five-class gate
        five_class_systems = ["monoclinic", "orthorhombic", "tetragonal", "trigonal", "cubic"]
        five_class_pass = True
        five_class_details = {}

        for cs in five_class_systems:
            detail = seven_class_details.get(cs, {})
            five_class_details[cs] = detail
            if not detail.get("meets_25_samples", False) or not detail.get("meets_3_families", False):
                five_class_pass = False

        # Determine overall decision
        if seven_class_pass:
            decision = "SEVEN_CLASS_GO"
            note = "All seven crystal systems meet the minimum 25-sample and 3-family requirements."
        elif five_class_pass:
            decision = "FIVE_CLASS_GO"
            note = "Five crystal systems (monoclinic, orthorhombic, tetragonal, trigonal, cubic) meet requirements."
        elif any(
            seven_class_details.get(cs, {}).get("meets_25_samples", False) and
            seven_class_details.get(cs, {}).get("meets_3_families", False)
            for cs in TARGET_CRYSTAL_SYSTEMS
        ):
            decision = "REDUCED_CLASS_GO"
            note = "Some crystal systems meet requirements but fewer than five."
        else:
            decision = "NO_GO"
            note = "No crystal system meets both the 25-sample and 3-family requirements."

        return {
            "decision": decision,
            "note": note,
            "seven_class_details": seven_class_details,
            "five_class_details": five_class_details,
            "seven_class_pass": seven_class_pass,
            "five_class_pass": five_class_pass,
        }

    def save_reports(self, output_dir: str):
        """Save all report files."""
        os.makedirs(output_dir, exist_ok=True)

        stats = self.generate_statistics()

        # JSON summary
        summary_path = os.path.join(output_dir, "opxrd_ferroelectric_feasibility_v1_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"Summary: {summary_path}")

        # Candidates CSV
        candidates = [r for r in self.results if r["is_candidate"]]
        cand_path = os.path.join(output_dir, "opxrd_ferroelectric_candidates_v1.csv")
        self._write_candidates_csv(candidates, cand_path)
        print(f"Candidates: {cand_path} ({len(candidates)} records)")

        # Exclusions CSV
        excluded = [r for r in self.results if not r["is_candidate"]]
        excl_path = os.path.join(output_dir, "opxrd_ferroelectric_exclusions_v1.csv")
        self._write_exclusions_csv(excluded, excl_path)
        print(f"Exclusions: {excl_path} ({len(excluded)} records)")

        # Conflicts CSV
        conflicts = [r for r in self.results if r.get("label_conflict")]
        conf_path = os.path.join(output_dir, "opxrd_ferroelectric_conflicts_v1.csv")
        self._write_conflicts_csv(conflicts, conf_path)
        print(f"Conflicts: {conf_path} ({len(conflicts)} records)")

        # Class counts CSV
        class_path = os.path.join(output_dir, "opxrd_ferroelectric_class_counts_v1.csv")
        self._write_class_counts_csv(stats, class_path)
        print(f"Class counts: {class_path}")

        # Family counts CSV
        family_path = os.path.join(output_dir, "opxrd_ferroelectric_family_counts_v1.csv")
        self._write_family_counts_csv(stats, family_path)
        print(f"Family counts: {family_path}")

        return stats

    def _write_candidates_csv(self, candidates: List[Dict], path: str):
        fields = ["scan_id", "contributor", "crystal_system", "space_group_number",
                  "space_group_symbol", "classification", "label_confidence",
                  "label_conflict", "qc_reasons",
                  "family_matches_json"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for r in candidates:
                row = {k: r.get(k) for k in fields if k != "family_matches_json"}
                row["family_matches_json"] = json.dumps(r.get("family_matches", []), ensure_ascii=False)
                row["qc_reasons"] = ";".join(r.get("qc_reasons", []))
                writer.writerow(row)

    def _write_exclusions_csv(self, excluded: List[Dict], path: str):
        fields = ["scan_id", "contributor", "crystal_system", "classification",
                  "qc_reasons", "parse_error", "quality_warnings"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for r in excluded:
                row = {k: r.get(k) for k in fields}
                row["qc_reasons"] = ";".join(r.get("qc_reasons", []))
                writer.writerow(row)

    def _write_conflicts_csv(self, conflicts: List[Dict], path: str):
        fields = ["scan_id", "contributor", "crystal_system", "space_group_number",
                  "space_group_symbol", "label_source"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for r in conflicts:
                writer.writerow({k: r.get(k) for k in fields})

    def _write_class_counts_csv(self, stats: Dict, path: str):
        fields = [
            "crystal_system", "raw_records", "candidate_records",
            "label_reliable_records", "label_conflicts",
            "strict_ceramic_count", "relaxed_domain_count",
            "manual_review_count"
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for cs in TARGET_CRYSTAL_SYSTEMS:
                row = {"crystal_system": cs}
                row.update(stats["by_crystal_system"].get(cs, {}))
                writer.writerow(row)

    def _write_family_counts_csv(self, stats: Dict, path: str):
        fields = ["family_id", "records", "candidates", "num_crystal_systems",
                  "crystal_systems", "num_contributors", "contributors",
                  "classification"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for fid, finfo in sorted(stats.get("by_family", {}).items()):
                row = {"family_id": fid}
                row.update(finfo)
                row["crystal_systems"] = ";".join(finfo.get("crystal_systems", []))
                row["contributors"] = ";".join(finfo.get("contributors", []))
                writer.writerow(row)


# ----------------------------------------------------------
# CLI
# ----------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="opXRD Ferroelectric Feasibility Auditor v1"
    )
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST,
                        help="Path to opXRD metadata CSV manifest")
    parser.add_argument("--family-rules", default=DEFAULT_FAMILY_RULES,
                        help="Path to ferroelectric family rules YAML")
    parser.add_argument("--filter-config", default=DEFAULT_FILTER_CONFIG,
                        help="Path to feasibility filter config YAML")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                        help="Output directory for reports")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate configs and manifest without full audit")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    return parser.parse_args()


def main():
    args = parse_args()

    # Validate config files exist
    for path, name in [(args.family_rules, "Family rules"),
                        (args.filter_config, "Filter config")]:
        if not os.path.exists(path):
            print(f"ERROR: {name} not found: {path}", file=sys.stderr)
            sys.exit(1)

    print(f"Manifest:      {args.manifest}")
    print(f"Family rules:  {args.family_rules}")
    print(f"Filter config: {args.filter_config}")
    print(f"Output dir:    {args.output_dir}")

    if args.dry_run:
        print("DRY RUN — validating configs only.")
        with open(args.family_rules, "r", encoding="utf-8") as f:
            rules = yaml.safe_load(f)
        print(f"  Families loaded: {len(rules.get('families', []))}")
        with open(args.filter_config, "r", encoding="utf-8") as f:
            filters = yaml.safe_load(f)
        print(f"  Filter sections: {list(filters.keys())}")
        if os.path.exists(args.manifest):
            print(f"  Manifest found: {args.manifest}")
        else:
            print(f"  Manifest NOT YET BUILT (expected at {args.manifest})")
        print("Dry run complete. Configuration valid.")
        return

    if not os.path.exists(args.manifest):
        print(f"ERROR: Manifest not found: {args.manifest}", file=sys.stderr)
        print("Run download_opxrd_metadata.py first to build the manifest.", file=sys.stderr)
        sys.exit(1)

    # Run audit
    auditor = FeasibilityAuditor(args.manifest, args.family_rules, args.filter_config)
    auditor.load_manifest()
    auditor.audit()
    stats = auditor.save_reports(args.output_dir)

    # Print key results
    gate = stats["gate_decision"]
    overall = stats["overall"]
    print(f"\n{'='*60}")
    print(f"FEASIBILITY AUDIT RESULT")
    print(f"{'='*60}")
    print(f"Total records:          {overall['total_records']}")
    print(f"Experimental records:   {overall['experimental_records']}")
    print(f"QC passed:              {overall['qc_passed_records']}")
    print(f"With crystal system:    {overall['with_crystal_system']}")
    print(f"Candidates:             {overall['candidate_records']}")
    print(f"Strict FE candidates:   {overall['strict_ferroelectric_candidates']}")
    print(f"FE-related candidates:  {overall['ferroelectric_related_candidates']}")
    print(f"\n--- Gate Decision ---")
    print(f"Decision:               {gate['decision']}")
    print(f"Seven-class pass:       {gate['seven_class_pass']}")
    print(f"Five-class pass:        {gate['five_class_pass']}")
    print(f"Note:                   {gate['note']}")
    print(f"\n--- Crystal System Counts ---")
    for cs in TARGET_CRYSTAL_SYSTEMS:
        detail = gate["seven_class_details"].get(cs, {})
        print(f"  {cs:12s}: {detail.get('candidate_records', 0):5d} records, "
              f"~{detail.get('estimated_independent_samples', 0):3d} samples, "
              f"{detail.get('num_families', 0):2d} families")
    print(f"\nShortcut risk:          {'HIGH' if stats['shortcut_risk']['any_high_risk'] else 'LOW/MEDIUM'}")

    if stats["shortcut_risk"]["any_high_risk"]:
        for risk in stats["shortcut_risk"]["risks"]:
            if risk["risk_level"] == "HIGH":
                print(f"  HIGH risk: {risk['crystal_system']} - {risk['risk_reasons']}")


if __name__ == "__main__":
    main()
