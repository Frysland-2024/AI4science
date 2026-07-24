#!/usr/bin/env python3
"""Post-hoc statistical robustness checks for the frozen V9 P0 result.

This script is read-only with respect to the original P0 JSON. It computes:

1. repeat-clustered bootstrap confidence intervals, treating each repeat as the
   independent sampling unit instead of treating six OOD profiles within the
   same repeat as independent;
2. leave-one-profile-out sensitivity for the six single-factor OOD profiles;
3. per-profile contribution summaries.

It does not retrain a model, access Validation/Test/real XRD, select lambda, or
modify the original report.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "reports" / "v9_p0_local_benefit.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "v9_p0_statistical_robustness.json"
CANDIDATES = ("js", "residual")
SINGLE_FACTOR_PROFILES = (
    "ood_shift_negative",
    "ood_shift_positive",
    "ood_broadening",
    "ood_noise",
    "ood_background",
    "ood_texture",
)
DEFAULT_DRAWS = 10_000
DEFAULT_SEED = 20260724


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _summary(values: Sequence[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        raise ValueError("cannot summarize an empty sequence")
    return {
        "count": int(array.size),
        "mean": float(array.mean()),
        "median": float(np.median(array)),
        "minimum": float(array.min()),
        "maximum": float(array.max()),
        "positive_sign_rate": float((array > 0).mean()),
    }


def _bootstrap_mean(
    values: Sequence[float], *, draws: int, seed: int
) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        raise ValueError("cannot bootstrap an empty sequence")
    generator = np.random.default_rng(seed)
    indexes = generator.integers(0, array.size, size=(draws, array.size))
    means = array[indexes].mean(axis=1)
    return {
        "draws": int(draws),
        "sampling_unit_count": int(array.size),
        "mean": float(array.mean()),
        "lower_95": float(np.quantile(means, 0.025)),
        "upper_95": float(np.quantile(means, 0.975)),
    }


def _candidate_benefit(row: Mapping[str, Any], candidate: str) -> float:
    return float(row["benefit_vs_erm"][candidate]["classification_ce"])


def _repeat_means(
    rows: Sequence[Mapping[str, Any]],
    *,
    candidate: str,
    included_profiles: Sequence[str],
) -> dict[int, float]:
    included = set(included_profiles)
    grouped: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        profile = str(row["profile"])
        if profile in included:
            grouped[int(row["repeat"])].append(_candidate_benefit(row, candidate))
    if not grouped:
        raise ValueError("no rows matched the requested profiles")
    expected = len(included)
    for repeat, values in grouped.items():
        if len(values) != expected:
            raise ValueError(
                f"repeat {repeat} has {len(values)} included profiles; expected {expected}"
            )
    return {repeat: float(np.mean(values)) for repeat, values in sorted(grouped.items())}


def analyze_report(
    report: Mapping[str, Any], *, draws: int = DEFAULT_DRAWS, seed: int = DEFAULT_SEED
) -> dict[str, Any]:
    rows = list(report.get("rows", []))
    if not rows:
        raise ValueError("input report has no rows")
    observed_profiles = {str(row["profile"]) for row in rows}
    missing = sorted(set(SINGLE_FACTOR_PROFILES) - observed_profiles)
    if missing:
        raise ValueError(f"input report lacks registered single-factor profiles: {missing}")

    clustered: dict[str, Any] = {}
    leave_one_out: dict[str, Any] = {}
    per_profile: dict[str, Any] = {}

    for candidate_index, candidate in enumerate(CANDIDATES):
        repeat_means = _repeat_means(
            rows,
            candidate=candidate,
            included_profiles=SINGLE_FACTOR_PROFILES,
        )
        repeat_values = list(repeat_means.values())
        clustered[candidate] = {
            "repeat_level_values": repeat_means,
            "summary": _summary(repeat_values),
            "repeat_clustered_bootstrap_95": _bootstrap_mean(
                repeat_values,
                draws=draws,
                seed=seed + candidate_index * 1000,
            ),
        }

        leave_one_out[candidate] = {}
        for profile_index, omitted in enumerate(SINGLE_FACTOR_PROFILES):
            kept = [profile for profile in SINGLE_FACTOR_PROFILES if profile != omitted]
            omitted_repeat_means = _repeat_means(
                rows,
                candidate=candidate,
                included_profiles=kept,
            )
            values = list(omitted_repeat_means.values())
            leave_one_out[candidate][omitted] = {
                "included_profiles": kept,
                "summary": _summary(values),
                "repeat_clustered_bootstrap_95": _bootstrap_mean(
                    values,
                    draws=draws,
                    seed=seed + candidate_index * 1000 + 100 + profile_index,
                ),
            }

        per_profile[candidate] = {}
        for profile_index, profile in enumerate(SINGLE_FACTOR_PROFILES):
            values = [
                _candidate_benefit(row, candidate)
                for row in rows
                if str(row["profile"]) == profile
            ]
            per_profile[candidate][profile] = {
                "summary": _summary(values),
                "repeat_bootstrap_95": _bootstrap_mean(
                    values,
                    draws=draws,
                    seed=seed + candidate_index * 1000 + 500 + profile_index,
                ),
            }

    flags = {}
    for candidate in CANDIDATES:
        full_ci = clustered[candidate]["repeat_clustered_bootstrap_95"]
        loo_lower_bounds = [
            leave_one_out[candidate][profile]["repeat_clustered_bootstrap_95"][
                "lower_95"
            ]
            for profile in SINGLE_FACTOR_PROFILES
        ]
        flags[candidate] = {
            "clustered_mean_positive": full_ci["mean"] > 0,
            "clustered_lower_95_above_zero": full_ci["lower_95"] > 0,
            "all_leave_one_profile_out_lower_95_above_zero": all(
                value > 0 for value in loo_lower_bounds
            ),
            "minimum_leave_one_profile_out_lower_95": float(min(loo_lower_bounds)),
            "not_a_formal_performance_conclusion": True,
        }

    return {
        "schema_version": "v9-p0-statistical-robustness-v1",
        "scope": "post-hoc statistics on the frozen Train-only P0 report",
        "sampling_policy": {
            "primary_unit": "repeat",
            "reason": "six OOD profiles generated within one repeat are treated as correlated measurements",
            "bootstrap_draws": int(draws),
            "bootstrap_seed": int(seed),
        },
        "single_factor_profiles": list(SINGLE_FACTOR_PROFILES),
        "repeat_clustered_analysis": clustered,
        "leave_one_profile_out": leave_one_out,
        "per_profile_analysis": per_profile,
        "descriptive_flags": flags,
        "formal_boundaries": {
            "model_training_performed": False,
            "validation_used": False,
            "simulated_test_used": False,
            "real_xrd_used": False,
            "lambda_selected": False,
            "formal_claim_allowed": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--draws", type=int, default=DEFAULT_DRAWS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    if input_path == output_path:
        raise SystemExit("--output must differ from --input; the original P0 report is immutable")
    if args.draws < 1000:
        raise SystemExit("--draws must be at least 1000")
    before_hash = _sha256(input_path)
    report = json.loads(input_path.read_text(encoding="utf-8"))
    result = analyze_report(report, draws=args.draws, seed=args.seed)
    result["input_report"] = {
        "path": input_path.as_posix(),
        "sha256_before": before_hash,
        "immutable": True,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    after_hash = _sha256(input_path)
    if after_hash != before_hash:
        output_path.unlink(missing_ok=True)
        raise RuntimeError("original P0 report changed during analysis; output was removed")
    result["input_report"]["sha256_after"] = after_hash
    result["input_report"]["unchanged"] = True
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Original preserved: {input_path}")
    print(f"Original SHA256: {before_hash}")
    print(f"Wrote: {output_path}")
    print(json.dumps(result["descriptive_flags"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
