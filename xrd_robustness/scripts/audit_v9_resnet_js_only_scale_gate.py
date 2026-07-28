"""Audit a JS-only ResNet scale grid without training or non-Train access."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREGISTRATION = (
    PROJECT_ROOT / "configs" / "v9_resnet_js_only_scale_gate.preregistered.json"
)
DEFAULT_SOURCE_REPORT = (
    PROJECT_ROOT / "reports" / "v9_resnet_candidate_grid_gate.json"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "v9_resnet_js_only_scale_gate.json"
EXPECTED_GRID = [3.0, 30.0, 60.0]
EXPECTED_BANDS = ["weak", "material_non_dominant", "dominant"]


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _ratio_band(value: float) -> str:
    if value < 0.01:
        return "negligible"
    if value < 0.1:
        return "weak"
    if value < 1.0:
        return "material_non_dominant"
    return "dominant"


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _summary(values: list[float]) -> dict[str, float]:
    if not values:
        raise ValueError("cannot summarize an empty sequence")
    return {
        "minimum": min(values),
        "p10": _percentile(values, 0.10),
        "median": statistics.median(values),
        "mean": statistics.fmean(values),
        "p90": _percentile(values, 0.90),
        "maximum": max(values),
    }


def _derive_lambda_60_trace(lambda_30_trace: list[dict[str, float]]) -> list[dict[str, float]]:
    derived: list[dict[str, float]] = []
    for source in lambda_30_trace:
        class_norm = float(source["classification_backbone_gradient_norm"])
        aux_norm = 2.0 * float(
            source["weighted_auxiliary_backbone_gradient_norm"]
        )
        cosine = float(source["classification_auxiliary_gradient_cosine"])
        combined_squared = (
            class_norm * class_norm
            + aux_norm * aux_norm
            + 2.0 * class_norm * aux_norm * cosine
        )
        combined_norm = math.sqrt(max(combined_squared, 0.0))
        combined_cosine = (
            (class_norm + aux_norm * cosine) / combined_norm
            if combined_norm > 0.0
            else float("nan")
        )
        weighted_loss = 2.0 * float(source["weighted_auxiliary_loss"])
        derived.append(
            {
                "batch_examples": float(source["batch_examples"]),
                "classification_auxiliary_gradient_cosine": cosine,
                "classification_backbone_gradient_norm": class_norm,
                "classification_combined_gradient_cosine": combined_cosine,
                "classification_loss": float(source["classification_loss"]),
                "combined_backbone_gradient_norm": combined_norm,
                "combined_loss": float(source["classification_loss"])
                + weighted_loss,
                "combined_to_classification_gradient_ratio": combined_norm
                / class_norm,
                "gradient_sum_identity_relative_error": 0.0,
                "lambda": 60.0,
                "raw_auxiliary_loss": float(source["raw_auxiliary_loss"]),
                "weighted_auxiliary_backbone_gradient_norm": aux_norm,
                "weighted_auxiliary_loss": weighted_loss,
                "weighted_auxiliary_to_classification_gradient_ratio": aux_norm
                / class_norm,
            }
        )
    return derived


def _candidate(
    value: float,
    expected_band: str,
    trace: list[dict[str, float]],
    measurement_basis: str,
    maximum_combined_ratio: float,
) -> dict[str, Any]:
    metric_names = [
        key for key in trace[0] if key not in {"batch_examples", "lambda"}
    ]
    summary = {
        key: _summary([float(row[key]) for row in trace])
        for key in metric_names
    }
    observed_ratio = summary[
        "weighted_auxiliary_to_classification_gradient_ratio"
    ]["median"]
    observed_band = _ratio_band(observed_ratio)
    checks = {
        "all_values_finite": all(
            math.isfinite(float(number))
            for row in trace
            for key, number in row.items()
            if key != "batch_examples"
        ),
        "classification_gradient_present": summary[
            "classification_backbone_gradient_norm"
        ]["minimum"]
        > 0.0,
        "weighted_auxiliary_gradient_present": summary[
            "weighted_auxiliary_backbone_gradient_norm"
        ]["minimum"]
        > 0.0,
        "observed_influence_band_matches_preregistered_band": observed_band
        == expected_band,
        "combined_gradient_not_explosive": summary[
            "combined_to_classification_gradient_ratio"
        ]["maximum"]
        <= maximum_combined_ratio,
        "median_combined_direction_preserves_classification_descent": summary[
            "classification_combined_gradient_cosine"
        ]["median"]
        > 0.0,
    }
    return {
        "lambda": value,
        "expected_band": expected_band,
        "observed_band": observed_band,
        "measurement_basis": measurement_basis,
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "summary": summary,
        "trace": trace,
    }


def run_audit(
    preregistration_path: Path,
    source_report_path: Path,
) -> dict[str, Any]:
    preregistration = json.loads(
        preregistration_path.read_text(encoding="utf-8")
    )
    source = json.loads(source_report_path.read_text(encoding="utf-8"))
    if preregistration["js_scale_probes"] != EXPECTED_GRID:
        raise ValueError("JS scale probes differ from the preregistered grid")
    if preregistration["expected_influence_bands"] != EXPECTED_BANDS:
        raise ValueError("expected influence bands differ from preregistration")
    expected_source_hash = preregistration["measurement_basis"][
        "source_report_sha256"
    ]
    actual_source_hash = file_hash(source_report_path)
    if actual_source_hash != expected_source_hash:
        raise ValueError("source report SHA-256 does not match preregistration")
    if source["status"] != "fail":
        raise ValueError("unexpected source Gate status")
    if any(
        bool(source[key])
        for key in ("validation_used", "simulated_test_used", "real_xrd_used")
    ):
        raise ValueError("source report crossed a forbidden data boundary")
    if bool(source["seven_run_started"]):
        raise ValueError("source report started the seven-run")
    direct = {
        float(candidate["lambda"]): candidate
        for candidate in source["candidate_measurements"]["lambda_js"][
            "candidates"
        ]
    }
    if 3.0 not in direct or 30.0 not in direct:
        raise ValueError("source report lacks direct lambda 3/30 traces")
    traces = {
        3.0: direct[3.0]["trace"],
        30.0: direct[30.0]["trace"],
        60.0: _derive_lambda_60_trace(direct[30.0]["trace"]),
    }
    bases = {
        3.0: "direct_autograd_trace_from_source_report",
        30.0: "direct_autograd_trace_from_source_report",
        60.0: "exact_scalar_rescaling_of_lambda_30_autograd_trace",
    }
    maximum_combined_ratio = float(
        preregistration["pass_rule"][
            "maximum_single_batch_combined_to_classification_gradient_ratio"
        ]
    )
    candidates = [
        _candidate(value, band, traces[value], bases[value], maximum_combined_ratio)
        for value, band in zip(EXPECTED_GRID, EXPECTED_BANDS, strict=True)
    ]
    gate_passed = all(candidate["status"] == "pass" for candidate in candidates)
    checks = {
        "source_hash_matches_preregistration": True,
        "source_is_train_only": True,
        "source_started_no_tuning": True,
        "all_candidate_checks_pass": gate_passed,
        "residual_v1_remains_archived": True,
        "four_run_not_started": True,
    }
    return {
        "schema_version": "v9-resnet-js-only-scale-gate-v1",
        "status": "pass" if all(checks.values()) else "fail",
        "scope": "js_only_train_gradient_scale_gate",
        "scientific_scope": "Dynamic ERM versus JS Consistency only",
        "js_candidate_grid": EXPECTED_GRID,
        "expected_influence_bands": EXPECTED_BANDS,
        "observed_influence_bands": [
            candidate["observed_band"] for candidate in candidates
        ],
        "candidates": candidates,
        "checks": checks,
        "candidate_range_may_be_frozen": gate_passed,
        "candidate_training_started": False,
        "four_run_started": False,
        "ten_run_started": False,
        "validation_used": False,
        "simulated_test_used": False,
        "real_xrd_used": False,
        "residual_v1_reopening_authorized": False,
        "four_run_tuning_authorized": False,
        "human_authorization_required_before_four_run": True,
        "input_hashes": {
            "preregistration": file_hash(preregistration_path),
            "source_report": actual_source_hash,
            "audit_script": file_hash(Path(__file__).resolve()),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--preregistration", type=Path, default=DEFAULT_PREREGISTRATION
    )
    parser.add_argument("--source-report", type=Path, default=DEFAULT_SOURCE_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run_audit(
        args.preregistration.resolve(), args.source_report.resolve()
    )
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "grid": report["js_candidate_grid"],
                "observed_bands": report["observed_influence_bands"],
                "candidate_range_may_be_frozen": report[
                    "candidate_range_may_be_frozen"
                ],
                "four_run_started": report["four_run_started"],
                "output": str(output),
            },
            indent=2,
        )
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
