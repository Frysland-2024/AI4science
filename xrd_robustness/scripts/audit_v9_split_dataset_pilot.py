"""Read-only dataset pilot audit for the parent-structure random split.

Checks, without loading any model or spectrum:
1. Train/Validation/Test counts match the frozen 70/15/15 contract.
2. Crystal-system proportions are consistent across splits (stratification).
3. No parent-structure leakage across splits (by parent_structure_id and
   by material_id).
4. Every split contains all seven crystal systems.
5. Parent-level assignment integrity: each material_id appears exactly once,
   and every material_id sharing one parent_structure_id has one split, so
   all derived clean/weak/strong/ID/OOD patterns inherit a single split.
   Cross-checked against the interrupted run's persisted Validation and OOD
   view manifests: every evaluated material_id must belong to Validation.

Output: reports/v9_split_dataset_pilot_audit.json
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "data" / "formal_14060" / "manifests" / "split_manifest.json"
RUN_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "v9_method_transfer_tuning_parent_structure_split_v1"
    / "ordinary_dynamic_augmentation__tuning_seed_20260710"
)
OUTPUT_PATH = PROJECT_ROOT / "reports" / "v9_split_dataset_pilot_audit.json"

EXPECTED_MANIFEST_SHA256 = "b9d3b72e42ea0fd549dae34425ff61d2d650d5dd7fe6f337d747cb952cf43293"
EXPECTED_COUNTS = {"train": 9842, "validation": 2109, "test": 2109}
EXPECTED_SYSTEMS = 7
SPLITS = ("train", "validation", "test")
# Stratification tolerance: max abs difference of a class share between any
# split and the global share, in fraction of the split.
MAX_CLASS_SHARE_DEVIATION = 0.01


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    checks: dict[str, dict] = {}

    manifest_sha = sha256_of(MANIFEST_PATH)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    records = manifest["records"]

    checks["manifest_identity"] = {
        "sha256": manifest_sha,
        "matches_authoritative_hash": manifest_sha == EXPECTED_MANIFEST_SHA256,
        "seed": manifest.get("seed"),
        "split_unit": manifest.get("split_unit"),
        "stratification": manifest.get("stratification"),
        "record_count": len(records),
        "passed": manifest_sha == EXPECTED_MANIFEST_SHA256
        and manifest.get("seed") == 20260726
        and manifest.get("split_unit") == "parent_structure"
        and manifest.get("stratification") == "crystal_system",
    }

    # Check 1: counts.
    split_counts = Counter(r["split"] for r in records)
    checks["split_counts"] = {
        "observed": dict(split_counts),
        "expected": EXPECTED_COUNTS,
        "total": sum(split_counts.values()),
        "passed": dict(split_counts) == EXPECTED_COUNTS
        and sum(split_counts.values()) == 14060,
    }

    # Check 2: stratification consistency.
    global_class = Counter(r["crystal_system"] for r in records)
    total = len(records)
    per_split_class: dict[str, Counter] = {s: Counter() for s in SPLITS}
    for r in records:
        per_split_class[r["split"]][r["crystal_system"]] += 1
    deviations = {}
    max_dev = 0.0
    for split in SPLITS:
        n_split = split_counts[split]
        for system, n_global in global_class.items():
            share_global = n_global / total
            share_split = per_split_class[split].get(system, 0) / n_split
            dev = abs(share_split - share_global)
            deviations[f"{split}:{system}"] = {
                "split_share": round(share_split, 6),
                "global_share": round(share_global, 6),
                "abs_deviation": round(dev, 6),
            }
            max_dev = max(max_dev, dev)
    checks["stratification"] = {
        "global_class_counts": dict(global_class),
        "per_split_class_counts": {s: dict(per_split_class[s]) for s in SPLITS},
        "max_abs_share_deviation": round(max_dev, 6),
        "tolerance": MAX_CLASS_SHARE_DEVIATION,
        "deviations": deviations,
        "passed": max_dev <= MAX_CLASS_SHARE_DEVIATION,
    }

    # Check 3: no parent-structure or material leakage across splits.
    parent_splits: dict[str, set] = defaultdict(set)
    material_splits: dict[str, set] = defaultdict(set)
    for r in records:
        parent_splits[r["parent_structure_id"]].add(r["split"])
        material_splits[r["material_id"]].add(r["split"])
    parent_leaks = {p: sorted(s) for p, s in parent_splits.items() if len(s) > 1}
    material_leaks = {m: sorted(s) for m, s in material_splits.items() if len(s) > 1}
    checks["cross_split_leakage"] = {
        "unique_parent_structures": len(parent_splits),
        "unique_material_ids": len(material_splits),
        "parent_structures_in_multiple_splits": len(parent_leaks),
        "material_ids_in_multiple_splits": len(material_leaks),
        "examples": dict(list(parent_leaks.items())[:5]),
        "passed": not parent_leaks and not material_leaks,
    }

    # Check 4: class completeness per split.
    missing = {
        s: sorted(set(global_class) - set(per_split_class[s]))
        for s in SPLITS
        if set(per_split_class[s]) != set(global_class)
    }
    checks["class_completeness"] = {
        "expected_systems": EXPECTED_SYSTEMS,
        "observed_systems_global": len(global_class),
        "missing_by_split": missing,
        "passed": len(global_class) == EXPECTED_SYSTEMS and not missing,
    }

    # Check 5a: one record per material, one split per parent.
    duplicate_materials = [m for m, c in Counter(r["material_id"] for r in records).items() if c > 1]
    shared_parent_groups = {
        p: len(ms)
        for p, ms in _group_materials_by_parent(records).items()
        if len(ms) > 1
    }
    checks["parent_assignment_integrity"] = {
        "duplicate_material_records": len(duplicate_materials),
        "parents_shared_by_multiple_materials": len(shared_parent_groups),
        "note": "split is assigned at parent level; shared parents are legal "
        "only because leakage check already proves one split per parent",
        "passed": not duplicate_materials,
    }

    # Check 5b: cross-check the interrupted run's persisted view manifests.
    validation_ids = {r["material_id"] for r in records if r["split"] == "validation"}
    train_ids = {r["material_id"] for r in records if r["split"] == "train"}
    test_ids = {r["material_id"] for r in records if r["split"] == "test"}
    view_checks = {}
    view_files = sorted(RUN_DIR.glob("*view_manifest.jsonl")) if RUN_DIR.exists() else []
    all_views_ok = True
    for path in view_files:
        ids = set()
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    ids.add(json.loads(line)["material_id"])
        n_train = len(ids & train_ids)
        n_test = len(ids & test_ids)
        n_val = len(ids & validation_ids)
        ok = n_train == 0 and n_test == 0 and n_val == len(ids)
        all_views_ok = all_views_ok and ok
        view_checks[path.name] = {
            "unique_material_ids": len(ids),
            "in_validation": n_val,
            "in_train": n_train,
            "in_test": n_test,
            "passed": ok,
        }
    checks["run_view_manifest_cross_check"] = {
        "run_dir_present": RUN_DIR.exists(),
        "view_manifests_checked": len(view_files),
        "files": view_checks,
        "passed": bool(view_files) and all_views_ok,
    }

    passed = all(c["passed"] for c in checks.values())
    report = {
        "schema_version": "v9-split-dataset-pilot-audit-v1",
        "manifest_path": str(MANIFEST_PATH),
        "model_loaded": False,
        "spectra_loaded": False,
        "simulated_test_content_accessed": False,
        "checks": checks,
        "status": "pass" if passed else "fail",
    }
    OUTPUT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"status: {report['status']}")
    for name, check in checks.items():
        print(f"  {name}: {'PASS' if check['passed'] else 'FAIL'}")
    print(f"report: {OUTPUT_PATH}")
    return 0 if passed else 1


def _group_materials_by_parent(records: list[dict]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for r in records:
        groups[r["parent_structure_id"]].append(r["material_id"])
    return groups


if __name__ == "__main__":
    raise SystemExit(main())
