#!/usr/bin/env python3
"""Independent-seed replication of the frozen Train-only V9 P0 diagnostic.

The original report is never overwritten. This wrapper changes the Train-only
random seed before rebuilding the five-epoch ERM state, sampling local batches,
and rendering perturbations, then delegates the scientific protocol to
``audit_v9_local_benefit.run_audit``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import audit_v9_learned_state_scale as learned_state  # noqa: E402
import audit_v9_local_benefit as p0  # noqa: E402


ORIGINAL_REPORT = PROJECT_ROOT / "reports" / "v9_p0_local_benefit.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "v9_p0_local_benefit_replication_seed1.json"
DEFAULT_SEED_OFFSET = 100_003


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--repeats", type=int, default=p0.DEFAULT_REPEATS)
    parser.add_argument("--worker-count", type=int, default=4)
    parser.add_argument("--prefetch-batches", type=int, default=4)
    parser.add_argument("--seed-offset", type=int, default=DEFAULT_SEED_OFFSET)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output).resolve()
    original = ORIGINAL_REPORT.resolve()
    if output == original:
        raise SystemExit("replication output must not overwrite the original P0 report")
    if args.seed_offset == 0:
        raise SystemExit("--seed-offset must be non-zero for an independent replication")

    original_hash_before = _sha256(original) if original.is_file() else None
    base_seed = int(p0.SEED)
    replication_seed = base_seed + int(args.seed_offset)

    # Functions imported into p0 from learned_state retain learned_state's module
    # globals, while p0's own sampling/rendering helpers use p0.SEED. Patch both.
    learned_state.SEED = replication_seed
    p0.SEED = replication_seed

    report = p0.run_audit(
        device_name=args.device,
        repeats=args.repeats,
        worker_count=args.worker_count,
        prefetch_batches=args.prefetch_batches,
    )
    report["schema_version"] = "v9-p0-local-benefit-independent-replication-v1"
    report["replication"] = {
        "base_seed": base_seed,
        "seed_offset": int(args.seed_offset),
        "effective_seed": replication_seed,
        "independent_training_initialization": True,
        "independent_train_order": True,
        "independent_local_batches": True,
        "independent_perturbation_stream": True,
        "original_report_path": original.as_posix(),
        "original_report_sha256_before": original_hash_before,
        "original_report_overwritten": False,
        "not_a_formal_performance_conclusion": True,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    original_hash_after = _sha256(original) if original.is_file() else None
    if original_hash_before != original_hash_after:
        output.unlink(missing_ok=True)
        raise RuntimeError("original P0 report changed during replication; new output removed")

    print(f"Original preserved: {original}")
    print(f"Original SHA256: {original_hash_after}")
    print(f"Replication seed: {replication_seed}")
    print(f"Wrote: {output}")
    print(json.dumps(report["descriptive_flags"], indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
