#!/usr/bin/env python3
"""
opXRD Grouping Auditor v1
==========================
Audits sample grouping, deduplication, and time-series detection in
opXRD candidate data. Produces a grouping audit report.

Granularities:
  institution -> family -> composition -> sample_group -> series -> scan

Usage:
    python audit_opxrd_grouping.py --help
    python audit_opxrd_grouping.py --manifest <candidate_manifest.csv> --output <report.json>
"""

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)


def parse_args():
    parser = argparse.ArgumentParser(description="opXRD Grouping Auditor v1")
    parser.add_argument("--manifest", required=True,
                        help="Path to candidate manifest CSV")
    parser.add_argument("--output-dir",
                        default=os.path.join(PROJECT_ROOT, "reports"))
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def normalize_composition(comp: str) -> str:
    """Normalize chemical composition for grouping."""
    if not comp:
        return ""
    # Remove whitespace, standardize
    s = comp.strip()
    # Sort element tokens for canonical form
    import re
    tokens = re.findall(r'([A-Z][a-z]?\d*\.?\d*)', s)
    # Simple normalization: just strip whitespace and lowercase
    return s.replace(" ", "").replace("_", "")


def build_hierarchy(candidates: List[Dict]) -> Dict[str, Any]:
    """Build the sample grouping hierarchy from candidate records."""
    hierarchy = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

    for c in candidates:
        inst = c.get("institution_id", c.get("contributor", "unknown"))
        family = c.get("family_id", "unknown")
        comp = c.get("composition_id", "unknown")
        sample = c.get("sample_group_id", c.get("scan_id", "unknown"))

        hierarchy[inst][family][comp][sample].append(c)

    return hierarchy


def count_unique(hierarchy: Dict) -> Dict[str, Any]:
    """Count unique entities at each level of the hierarchy."""
    institutions = set()
    families = set()
    compositions = set()
    samples = set()
    scans = 0

    for inst, fam_dict in hierarchy.items():
        institutions.add(inst)
        for fam, comp_dict in fam_dict.items():
            families.add(f"{inst}|{fam}")
            for comp, sample_dict in comp_dict.items():
                compositions.add(f"{inst}|{fam}|{comp}")
                for sample, scans_list in sample_dict.items():
                    samples.add(f"{inst}|{fam}|{comp}|{sample}")
                    scans += len(scans_list)

    return {
        "unique_institutions": len(institutions),
        "unique_families": len(families),
        "unique_compositions": len(compositions),
        "unique_sample_groups": len(samples),
        "total_scans": scans,
        "scan_to_sample_ratio": round(scans / max(len(samples), 1), 2),
        "composition_to_family_ratio": round(len(compositions) / max(len(families), 1), 2),
    }


def detect_time_series(candidates: List[Dict]) -> Dict[str, Any]:
    """Detect potential time-series measurements by filename patterns."""
    series_patterns = defaultdict(list)

    for c in candidates:
        fname = c.get("source_file", c.get("scan_id", ""))
        # Look for common patterns: _T1, _T2, scan_001, etc.
        base = fname.rsplit("_", 1)[0] if "_" in fname else fname
        series_patterns[base].append(c)

    series_groups = []
    for base, scans in series_patterns.items():
        if len(scans) >= 3:
            series_groups.append({
                "base_name": base,
                "scan_count": len(scans),
                "contributor": scans[0].get("contributor", "unknown"),
            })

    return {
        "potential_series_groups": len(series_groups),
        "total_scans_in_series": sum(g["scan_count"] for g in series_groups),
        "series_details": series_groups[:50],  # top 50
    }


def audit_grouping(manifest_path: str, output_dir: str):
    """Run the full grouping audit."""
    os.makedirs(output_dir, exist_ok=True)

    with open(manifest_path, "r", encoding="utf-8") as f:
        candidates = list(csv.DictReader(f))

    print(f"Loaded {len(candidates)} candidates for grouping audit")

    # Build hierarchy
    hierarchy = build_hierarchy(candidates)

    # Count unique
    counts = count_unique(hierarchy)

    # Time series detection
    time_series = detect_time_series(candidates)

    # By crystal system grouping
    cs_groups = defaultdict(lambda: {
        "scans": 0,
        "families": set(),
        "institutions": set(),
        "compositions": set(),
    })
    for c in candidates:
        cs = c.get("crystal_system", "unknown")
        cs_groups[cs]["scans"] += 1
        cs_groups[cs]["families"].add(c.get("family_id", "unknown"))
        cs_groups[cs]["institutions"].add(c.get("contributor", "unknown"))
        comp_raw = c.get("family_matches_json", "")
        cs_groups[cs]["compositions"].add(comp_raw[:80])

    cs_summary = {}
    for cs, info in sorted(cs_groups.items()):
        cs_summary[cs] = {
            "scans": info["scans"],
            "num_families": len(info["families"]),
            "num_institutions": len(info["institutions"]),
            "num_unique_composition_signatures": len(info["compositions"]),
            "families": sorted(info["families"]),
            "institutions": sorted(info["institutions"]),
        }

    # Assemble report
    report = {
        "audit_version": "opxrd-grouping-audit-v1",
        "manifest_path": manifest_path,
        "total_candidates": len(candidates),
        "unique_counts": counts,
        "by_crystal_system": cs_summary,
        "time_series_analysis": time_series,
        "warnings": [],
    }

    if counts["scan_to_sample_ratio"] > 5:
        report["warnings"].append(
            f"High scan-to-sample ratio ({counts['scan_to_sample_ratio']}): "
            "many scans may be from few samples."
        )

    if time_series["total_scans_in_series"] > len(candidates) * 0.3:
        report["warnings"].append(
            "Over 30% of scans may belong to time series; "
            "independent sample count may be overestimated."
        )

    # Save report
    report_path = os.path.join(output_dir, "opxrd_ferroelectric_grouping_audit_v1.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Grouping audit: {report_path}")
    print(f"\n=== Grouping Summary ===")
    print(f"Total scans:              {counts['total_scans']}")
    print(f"Unique sample groups:     {counts['unique_sample_groups']}")
    print(f"Unique compositions:      {counts['unique_compositions']}")
    print(f"Unique families:          {counts['unique_families']}")
    print(f"Unique institutions:      {counts['unique_institutions']}")
    print(f"Scan/sample ratio:        {counts['scan_to_sample_ratio']}")
    print(f"Potential series groups:  {time_series['potential_series_groups']}")
    if report["warnings"]:
        print(f"\nWarnings:")
        for w in report["warnings"]:
            print(f"  - {w}")

    return report


def main():
    args = parse_args()
    if not os.path.exists(args.manifest):
        print(f"ERROR: Manifest not found: {args.manifest}", file=sys.stderr)
        sys.exit(1)
    audit_grouping(args.manifest, args.output_dir)


if __name__ == "__main__":
    main()
