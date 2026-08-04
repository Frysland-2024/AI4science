#!/usr/bin/env python3
"""
opXRD Few-Shot Split Proposer v1
=================================
Generates a split proposal (support / adaptation validation / external test)
from the candidate manifest and grouping audit.

Does NOT freeze the split — only generates a proposal for review.
Does NOT train models or access checkpoints.

Usage:
    python propose_opxrd_fewshot_split.py --help
    python propose_opxrd_fewshot_split.py --manifest <candidate_manifest.csv> --output <proposal.json>
"""

import argparse
import csv
import json
import os
import random
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

TARGET_CRYSTAL_SYSTEMS = [
    "triclinic", "monoclinic", "orthorhombic",
    "tetragonal", "trigonal", "hexagonal", "cubic"
]

FIVE_CLASS_SYSTEMS = ["monoclinic", "orthorhombic", "tetragonal", "trigonal", "cubic"]


def parse_args():
    parser = argparse.ArgumentParser(description="opXRD Few-Shot Split Proposer v1")
    parser.add_argument("--manifest", required=True,
                        help="Path to candidate manifest CSV")
    parser.add_argument("--output-dir",
                        default=os.path.join(PROJECT_ROOT, "reports"))
    parser.add_argument("--seed", type=int, default=20260804,
                        help="Split seed (default: 20260804)")
    parser.add_argument("--mode", choices=["seven", "five"], default="seven",
                        help="Target crystal system count (default: seven)")
    parser.add_argument("--support-per-class", type=int, default=5,
                        help="Support samples per class (default: 5)")
    parser.add_argument("--adapt-val-per-class", type=int, default=5,
                        help="Adaptation validation samples per class (default: 5)")
    parser.add_argument("--test-per-class", type=int, default=15,
                        help="External test samples per class (default: 15)")
    parser.add_argument("--disjoint-mode", choices=["composition", "family", "none"], default="composition",
                        help="Group-disjoint mode (default: composition)")
    return parser.parse_args()


def load_candidates(manifest_path: str) -> List[Dict[str, Any]]:
    """Load candidate records and group by crystal system."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        records = list(csv.DictReader(f))

    # Group by crystal system
    by_cs = defaultdict(list)
    for r in records:
        cs = r.get("crystal_system", "")
        if cs in TARGET_CRYSTAL_SYSTEMS:
            by_cs[cs].append(r)

    return by_cs


def get_group_key(record: Dict, mode: str) -> str:
    """Get the group key for disjoint splitting."""
    if mode == "composition":
        # Use chemical composition + family as group
        fm = record.get("family_matches_json", "[]")
        try:
            matches = json.loads(fm) if isinstance(fm, str) else fm
        except json.JSONDecodeError:
            matches = []
        primary = matches[0].get("matched_family", "") if matches else ""
        return f"{record.get('contributor', '')}|{primary}"
    elif mode == "family":
        fm = record.get("family_matches_json", "[]")
        try:
            matches = json.loads(fm) if isinstance(fm, str) else fm
        except json.JSONDecodeError:
            matches = []
        return matches[0].get("matched_family", "") if matches else record.get("family_id", "")
    else:
        return record.get("scan_id", "")


def propose_split(by_cs: Dict[str, List[Dict]], args) -> Dict[str, Any]:
    """Generate a split proposal."""
    random.seed(args.seed)

    target_systems = TARGET_CRYSTAL_SYSTEMS if args.mode == "seven" else FIVE_CLASS_SYSTEMS

    support_samples = {}
    adapt_val_samples = {}
    test_samples = {}
    insufficient_classes = []
    family_count_by_class = {}

    for cs in target_systems:
        records = by_cs.get(cs, [])
        if not records:
            insufficient_classes.append(cs)
            support_samples[cs] = []
            adapt_val_samples[cs] = []
            test_samples[cs] = []
            continue

        # Group records by composition/family
        groups = defaultdict(list)
        for r in records:
            gk = get_group_key(r, args.disjoint_mode)
            groups[gk].append(r)

        group_keys = list(groups.keys())
        random.shuffle(group_keys)

        # Count families
        families = set()
        for r in records:
            fm = r.get("family_matches_json", "[]")
            try:
                matches = json.loads(fm) if isinstance(fm, str) else fm
            except json.JSONDecodeError:
                matches = []
            for m in matches:
                if m.get("matched_family"):
                    families.add(m["matched_family"])
        family_count_by_class[cs] = len(families)

        # Try to allocate: support -> adapt_val -> test
        needed = args.support_per_class + args.adapt_val_per_class + args.test_per_class
        available_groups = len(group_keys)

        if available_groups < needed:
            print(f"WARNING: {cs}: {available_groups} groups available, {needed} needed")

        support_out = []
        adapt_out = []
        test_out = []

        for gk in group_keys:
            group_records = groups[gk]
            # Take one representative per group
            if len(support_out) < args.support_per_class:
                support_out.append(group_records[0])
            elif len(adapt_out) < args.adapt_val_per_class:
                adapt_out.append(group_records[0])
            elif len(test_out) < args.test_per_class:
                test_out.append(group_records[0])
            else:
                break

        support_samples[cs] = support_out
        adapt_val_samples[cs] = adapt_out
        test_samples[cs] = test_out

        # Check sufficiency
        if (len(support_out) < args.support_per_class or
            len(adapt_out) < args.adapt_val_per_class or
            len(test_out) < args.test_per_class):
            insufficient_classes.append(cs)

    # Compile proposal
    proposal = {
        "proposal_version": "opxrd-fewshot-split-proposal-v1",
        "split_seed": args.seed,
        "mode": args.mode,
        "disjoint_mode": args.disjoint_mode,
        "target_per_class": {
            "support": args.support_per_class,
            "adaptation_validation": args.adapt_val_per_class,
            "external_test": args.test_per_class,
        },
        "classes_fully_allocated": [cs for cs in target_systems if cs not in insufficient_classes],
        "classes_insufficient": insufficient_classes,
        "feasible": len(insufficient_classes) == 0,
        "family_counts": family_count_by_class,
        "allocation": {
            "support": {
                cs: {
                    "count": len(support_samples[cs]),
                    "scan_ids": [s.get("scan_id", "") for s in support_samples[cs]],
                    "families": list(set(
                        s.get("family_id", "")
                        for s in support_samples[cs]
                    )),
                }
                for cs in target_systems
            },
            "adaptation_validation": {
                cs: {
                    "count": len(adapt_val_samples[cs]),
                    "scan_ids": [s.get("scan_id", "") for s in adapt_val_samples[cs]],
                }
                for cs in target_systems
            },
            "external_test": {
                cs: {
                    "count": len(test_samples[cs]),
                    "scan_ids": [s.get("scan_id", "") for s in test_samples[cs]],
                }
                for cs in target_systems
            },
        },
        "scientific_notes": [
            "This is a PROPOSAL only. The split is NOT frozen.",
            "No model training or inference has been performed.",
            "Split must be frozen and audited before any model access.",
            "Same sample_group must not cross split boundaries.",
            "Family-disjoint constraint: composition-level by default.",
        ],
    }

    # Try family-disjoint sensitivity split
    if args.disjoint_mode == "composition":
        # Generate family-disjoint variant
        family_disjoint_feasible = True
        for cs in target_systems:
            if family_count_by_class.get(cs, 0) < 3:
                family_disjoint_feasible = False
                break

        proposal["family_disjoint_sensitivity"] = {
            "feasible": family_disjoint_feasible,
            "note": "Family-disjoint split feasible" if family_disjoint_feasible
                    else "Not enough independent families per class for family-disjoint split",
            "min_families_per_class": min(family_count_by_class.values()) if family_count_by_class else 0,
        }

    return proposal


def main():
    args = parse_args()

    if not os.path.exists(args.manifest):
        print(f"ERROR: Manifest not found: {args.manifest}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading candidates from: {args.manifest}")
    by_cs = load_candidates(args.manifest)

    for cs in TARGET_CRYSTAL_SYSTEMS:
        print(f"  {cs}: {len(by_cs.get(cs, []))} candidates")

    proposal = propose_split(by_cs, args)

    os.makedirs(args.output_dir, exist_ok=True)
    proposal_path = os.path.join(args.output_dir, "opxrd_ferroelectric_split_proposal_v1.json")
    with open(proposal_path, "w", encoding="utf-8") as f:
        json.dump(proposal, f, indent=2, ensure_ascii=False)

    print(f"\nSplit proposal: {proposal_path}")
    print(f"Feasible: {proposal['feasible']}")
    print(f"Insufficient classes: {proposal['classes_insufficient']}")
    print(f"Fully allocated: {proposal['classes_fully_allocated']}")

    for cs in (TARGET_CRYSTAL_SYSTEMS if args.mode == "seven" else FIVE_CLASS_SYSTEMS):
        alloc = proposal["allocation"]
        sup = alloc["support"].get(cs, {}).get("count", 0)
        av = alloc["adaptation_validation"].get(cs, {}).get("count", 0)
        te = alloc["external_test"].get(cs, {}).get("count", 0)
        print(f"  {cs:12s}: support={sup}, adapt_val={av}, test={te}")


if __name__ == "__main__":
    main()
