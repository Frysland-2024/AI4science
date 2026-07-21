#!/usr/bin/env python3
"""Build the portable formal 14,000-structure database.

The command is intentionally an orchestration layer: acquisition, peak-cache
generation, and validation remain separate auditable steps. Use ``--plan-only``
to inspect the exact contract without contacting Materials Project.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.data_layout import project_relative_path, resolve_data_root
from xrd_robustness.mp_credentials import configured_api_key


def _parse_ratios(value: str) -> dict[str, float]:
    values = [float(item.strip()) for item in value.split(",")]
    if len(values) != 3 or any(item < 0 for item in values):
        raise ValueError("split ratios must contain three non-negative values")
    if abs(sum(values) - 1.0) > 1e-9:
        raise ValueError("split ratios must sum to 1")
    return {"train": values[0], "validation": values[1], "test": values[2]}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_script_entrypoint(script: Path, arguments: list[str]) -> None:
    """Run a project script in this already validated interpreter process."""
    previous_argv = sys.argv
    try:
        sys.argv = [str(script), *arguments]
        namespace = runpy.run_path(str(script), run_name=f"_xrd_{script.stem}")
        result = int(namespace["main"]())
    finally:
        sys.argv = previous_argv
    if result != 0:
        raise RuntimeError(f"{script.name} returned {result}")


def _write_dataset_manifest(data_root: Path, *, per_class: int, split_seed: int, ratios: dict[str, float]) -> Path:
    records_path = data_root / "mp_processed" / "structure_records.jsonl"
    records = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines()]
    expected = per_class * 7
    if len(records) != expected:
        raise RuntimeError(f"formal acquisition returned {len(records)} records, expected {expected}")
    class_counts = {}
    for row in records:
        class_counts[row["crystal_system"]] = class_counts.get(row["crystal_system"], 0) + 1
    if set(class_counts.values()) != {per_class} or len(class_counts) != 7:
        raise RuntimeError(f"formal acquisition is not balanced: {class_counts}")
    manifests = data_root / "manifests"
    retrieval = json.loads((manifests / "retrieval_manifest.json").read_text(encoding="utf-8"))
    manifest = {
        "schema_version": "dataset-manifest-v1",
        "status": "built",
        "tier": "formal_14000",
        "dataset_root": project_relative_path(PROJECT_ROOT, data_root),
        "parent_dataset_manifest": None,
        "source": "Materials Project official API",
        "expected_size": expected,
        "per_crystal_system": per_class,
        "crystal_system_count": 7,
        "split_seed": split_seed,
        "split_ratios": ratios,
        "counts": class_counts,
        "selection_policy": retrieval.get("query", {}).get("selection_policy", "unknown"),
        "max_energy_above_hull": retrieval.get("query", {}).get("max_energy_above_hull"),
        "selection_tiers": retrieval.get("counts", {}).get("selection_tiers", {}),
        "split_manifest_sha256": _sha256(manifests / "split_manifest.csv"),
        "artifacts": {
            "records": project_relative_path(PROJECT_ROOT, records_path),
            "structure_manifest": project_relative_path(PROJECT_ROOT, manifests / "structure_manifest.csv"),
            "split_manifest": project_relative_path(PROJECT_ROOT, manifests / "split_manifest.csv"),
            "retrieval_manifest": project_relative_path(PROJECT_ROOT, manifests / "retrieval_manifest.json"),
            "peak_cache_manifest": project_relative_path(PROJECT_ROOT, manifests / "peak_cache_manifest.v7.reflection.csv"),
        },
        "spectra_persisted": False,
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    output = manifests / "dataset_manifest.json"
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default=str(PROJECT_ROOT / "data" / "formal_14000"))
    parser.add_argument("--per-class", type=int, default=2000)
    parser.add_argument("--split-seed", type=int, default=20260711)
    parser.add_argument("--split-ratios", default="0.7,0.15,0.15")
    parser.add_argument("--api-key", default=configured_api_key())
    parser.add_argument(
        "--max-energy-above-hull",
        type=float,
        default=0.1,
        help="Documented near-stable fallback threshold in eV/atom",
    )
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    if args.per_class <= 0:
        raise SystemExit("--per-class must be positive")
    try:
        ratios = _parse_ratios(args.split_ratios)
        data_root = resolve_data_root(PROJECT_ROOT, args.output_root)
    except ValueError as error:
        raise SystemExit(str(error)) from error

    plan = {
        "tier": "formal_14000",
        "dataset_root": project_relative_path(PROJECT_ROOT, data_root),
        "expected_size": args.per_class * 7,
        "per_crystal_system": args.per_class,
        "split_seed": args.split_seed,
        "split_ratios": ratios,
        "source": "Materials Project official API",
        "spectra_persisted": False,
        "api_key_configured": bool(args.api_key),
        "max_energy_above_hull": args.max_energy_above_hull,
        "selection_policy": "stable_then_near_stable_fallback",
    }
    if args.plan_only:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    if not args.api_key:
        raise SystemExit("MP_API_KEY or PMG_MAPI_KEY is required; rerun --plan-only to inspect the contract")
    if data_root.exists() and any(data_root.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty formal data root: {data_root}")
    data_root.mkdir(parents=True, exist_ok=True)

    acquire = [
        "--output-root",
        str(data_root),
        "--per-class-limit",
        str(args.per_class),
        "--split-seed",
        str(args.split_seed),
        "--split-ratios",
        args.split_ratios,
        "--max-energy-above-hull",
        str(args.max_energy_above_hull),
    ]
    _run_script_entrypoint(PROJECT_ROOT / "scripts" / "acquire_mp_structures.py", acquire)
    _run_script_entrypoint(
        PROJECT_ROOT / "scripts" / "precompute_peak_tables.py",
        [
            "--data-root", str(data_root),
            "--cache-name", "peak_tables_v7_reflection",
            "--manifest-name", "peak_cache_manifest.v7.reflection.csv",
            "--failure-name", "peak_cache_failures.v7.reflection.csv",
            "--audit-name", "peak_cache_audit.v7.reflection.json",
        ],
    )
    _write_dataset_manifest(data_root, per_class=args.per_class, split_seed=args.split_seed, ratios=ratios)
    _run_script_entrypoint(
        PROJECT_ROOT / "scripts" / "validate_formal_database.py",
        [
            "--data-root", str(data_root),
            "--expected-size", str(args.per_class * 7),
            "--per-class", str(args.per_class),
        ],
    )
    print(json.dumps({"status": "built", **plan}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
