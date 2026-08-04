#!/usr/bin/env python3
"""
opXRD Candidate Manifest Builder v1
====================================
Builds a candidate manifest from the feasibility audit results, including
deduplication, grouping, and spectral quality metadata.

Usage:
    python build_opxrd_candidate_manifest.py --help
    python build_opxrd_candidate_manifest.py --candidates <candidates.csv> --output <manifest.csv>
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

MANIFEST_VERSION = "opxrd-candidate-manifest-v1"


def parse_args():
    parser = argparse.ArgumentParser(description="opXRD Candidate Manifest Builder v1")
    parser.add_argument("--candidates", required=True,
                        help="Path to candidates CSV from audit")
    parser.add_argument("--output-dir",
                        default=os.path.join(PROJECT_ROOT, "data", "real_xrd", "opxrd_feasibility"),
                        help="Output directory")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    return parser.parse_args()


def normalize_spectrum_hash(two_theta, intensities) -> str:
    """Compute a normalized hash of spectrum data for dedup."""
    if not two_theta or not intensities:
        return ""
    # Normalize to common grid then hash
    key = f"{len(two_theta)}:{len(intensities)}:{sum(two_theta):.2f}:{sum(intensities):.2f}"
    return hashlib.sha256(key.encode()).hexdigest()[:16].upper()


def group_by_contributor_and_family(candidates: List[Dict]) -> Dict[str, List[Dict]]:
    """Group candidates by contributor + family for dedup."""
    groups = defaultdict(list)
    for c in candidates:
        contrib = c.get("contributor", "unknown")
        fm = c.get("family_matches_json", "[]")
        try:
            matches = json.loads(fm) if isinstance(fm, str) else fm
        except json.JSONDecodeError:
            matches = []
        family_ids = sorted(set(m.get("matched_family", "") for m in matches if m.get("matched_family")))
        family_key = ";".join(family_ids) if family_ids else "unmatched"
        group_key = f"{contrib}|{family_key}"
        groups[group_key].append(c)
    return groups


def detect_duplicates(groups: Dict[str, List[Dict]]) -> Dict[str, Any]:
    """Detect potential duplicates within groups using file hashes."""
    file_hashes = defaultdict(list)
    for group_key, records in groups.items():
        for r in records:
            fh = r.get("file_sha256", "")
            if fh:
                file_hashes[group_key].append(fh)

    dup_count = 0
    dup_groups = []
    for group_key, hashes in file_hashes.items():
        hash_counts = defaultdict(int)
        for h in hashes:
            if h:
                hash_counts[h] += 1
        for h, count in hash_counts.items():
            if count > 1:
                dup_count += count - 1
                dup_groups.append({
                    "group": group_key,
                    "hash": h,
                    "duplicate_count": count - 1,
                })

    return {
        "duplicate_file_count": dup_count,
        "duplicate_groups": dup_groups,
    }


def build_manifest(candidates_path: str, output_dir: str):
    """Build candidate manifest with grouping info."""
    os.makedirs(output_dir, exist_ok=True)

    # Load candidates
    with open(candidates_path, "r", encoding="utf-8") as f:
        candidates = list(csv.DictReader(f))

    print(f"Loaded {len(candidates)} candidates")

    # Group by contributor + family
    groups = group_by_contributor_and_family(candidates)

    # Dedup
    dup_info = detect_duplicates(groups)
    print(f"Detected {dup_info['duplicate_file_count']} duplicate files")

    # Compute per-candidate fields
    unique_candidates = []
    seen_hashes = set()
    for c in candidates:
        fh = c.get("file_sha256", "")
        if fh and fh in seen_hashes:
            continue
        if fh:
            seen_hashes.add(fh)

        # Add grouping metadata
        fm = c.get("family_matches_json", "[]")
        try:
            matches = json.loads(fm) if isinstance(fm, str) else fm
        except json.JSONDecodeError:
            matches = []

        primary_family = matches[0].get("matched_family", "") if matches else ""

        c["institution_id"] = c.get("contributor", "unknown")
        c["family_id"] = primary_family
        c["composition_id"] = c.get("family_matches_json", "")[:80]  # placeholder
        c["sample_group_id"] = f"{c.get('contributor', '')}|{primary_family}|{fh[:8] if fh else ''}"
        c["series_group_id"] = ""
        c["scan_id_out"] = c.get("scan_id", "")

        unique_candidates.append(c)

    # Write manifest
    manifest_path = os.path.join(output_dir, "opxrd_candidate_manifest_v1.csv")
    if unique_candidates:
        fields = list(unique_candidates[0].keys())
        with open(manifest_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(unique_candidates)

    # Write dedup report
    dedup_path = os.path.join(output_dir, "opxrd_dedup_audit_v1.json")
    audit = {
        "manifest_version": MANIFEST_VERSION,
        "total_candidates_input": len(candidates),
        "unique_candidates_output": len(unique_candidates),
        "duplicate_file_count": dup_info["duplicate_file_count"],
        "duplicate_groups": dup_info["duplicate_groups"][:100],  # top 100
    }
    with open(dedup_path, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)

    print(f"Manifest: {manifest_path} ({len(unique_candidates)} unique)")
    print(f"Dedup audit: {dedup_path}")

    return manifest_path


def main():
    args = parse_args()
    build_manifest(args.candidates, args.output_dir)


if __name__ == "__main__":
    main()
