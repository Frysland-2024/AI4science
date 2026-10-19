#!/usr/bin/env python3
"""Compare the pinned CIF starting point with multistart physical refinement.

This runner is gated on the predeclared Stage 2 real-profile gate. It consumes
only the 12 predeclared non-frozen Grossular development profiles and writes
derived metrics, never source spectra.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from pxrd_router_mvp.grossular_project import (
    GROSSULAR_CANDIDATE,
    PROFILE,
    fit_multistart_a,
    load_development_sample,
)


def _mean(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def _median(values: list[float]) -> float | None:
    return float(np.median(values)) if values else None


def run(stage2_path: Path, archive_root: Path, frozen_manifest: Path,
        frozen_split: Path) -> dict:
    stage2 = json.loads(stage2_path.read_text(encoding="utf-8"))
    if stage2.get("real_development", {}).get("status") != "GO_GATE_PASS":
        raise ValueError("Stage 3 physical baselines require the predeclared Stage 2 gate to pass")
    expected_ids = list(PROFILE["development_sample_ids"])
    by_id = {row["sample_id"]: row for row in stage2["real_development"]["samples"]}
    if set(by_id) != set(expected_ids):
        raise ValueError("Stage 2 result IDs do not match the pinned development population")

    rows = []
    for sample_id in expected_ids:
        sample = load_development_sample(sample_id, archive_root,
                                         frozen_manifest=frozen_manifest,
                                         frozen_split=frozen_split)
        stage2_row = by_id[sample_id]
        wavelength = float(stage2_row["wavelength_used_angstrom"])
        fwhm = float(stage2_row["fit"]["fwhm_deg_fixed"])
        shift = float(stage2_row["fit"]["zero_shift_deg_fixed"])
        baseline = fit_multistart_a(sample.two_theta, sample.intensity, wavelength,
                                    fwhm_deg=fwhm, zero_shift_deg=shift)
        ref_a = float(sample.cell_reference_for_posthoc_only["a"]["value"])
        cif_a = float(GROSSULAR_CANDIDATE.load().a)
        cif_rmse = float(stage2_row["fit"]["initial_score_rmse"])
        rows.append({
            "sample_id": sample_id,
            "raw_member_sha256": sample.raw_member_sha256,
            "wavelength_proxy_angstrom": wavelength,
            "comparison": {
                "cif_initial_a_angstrom": cif_a,
                "cif_initial_rmse": cif_rmse,
                "cif_initial_abs_error_vs_posthoc_reference_angstrom": abs(cif_a - ref_a),
                "multistart_lbfgsb_a_angstrom": baseline["best_a_angstrom"],
                "multistart_lbfgsb_rmse": baseline["score_rmse"],
                "multistart_lbfgsb_abs_error_vs_posthoc_reference_angstrom": abs(baseline["best_a_angstrom"] - ref_a),
                "rmse_improvement_vs_cif_initial": cif_rmse - baseline["score_rmse"],
                "abs_error_change_vs_cif_initial_angstrom": abs(cif_a - ref_a) - abs(baseline["best_a_angstrom"] - ref_a),
            },
            "optimizer": {
                "name": "scipy.optimize.minimize(method=L-BFGS-B), five fixed starts",
                "starts_fraction_of_cif_a": list(baseline["starts_fraction_of_cif_a"]),
                "bounds_angstrom": list(baseline["bounds_angstrom"]),
                "attempts": baseline["attempts"],
                "evaluations": baseline["evaluations"],
                "elapsed_seconds": baseline["elapsed_seconds"],
                "success": baseline["success"],
                "free_structural_parameters": baseline["free_structural_parameters"],
                "scale_background_are_linear_nuisance_terms": True,
            },
            "reference_role": "posthoc_RRUFF_refinement_estimate_only_not_ground_truth",
        })

    cif_rmses = [r["comparison"]["cif_initial_rmse"] for r in rows]
    fit_rmses = [r["comparison"]["multistart_lbfgsb_rmse"] for r in rows]
    cif_errors = [r["comparison"]["cif_initial_abs_error_vs_posthoc_reference_angstrom"] for r in rows]
    fit_errors = [r["comparison"]["multistart_lbfgsb_abs_error_vs_posthoc_reference_angstrom"] for r in rows]
    runtimes = [r["optimizer"]["elapsed_seconds"] for r in rows]
    summary = {
        "sample_count": len(rows),
        "cif_initial": {
            "mean_full_profile_rmse": _mean(cif_rmses),
            "median_full_profile_rmse": _median(cif_rmses),
            "mean_abs_a_error_vs_posthoc_reference_angstrom": _mean(cif_errors),
            "median_abs_a_error_vs_posthoc_reference_angstrom": _median(cif_errors),
        },
        "multistart_lbfgsb": {
            "mean_full_profile_rmse": _mean(fit_rmses),
            "median_full_profile_rmse": _median(fit_rmses),
            "mean_abs_a_error_vs_posthoc_reference_angstrom": _mean(fit_errors),
            "median_abs_a_error_vs_posthoc_reference_angstrom": _median(fit_errors),
            "rmse_improved_count": sum(after < before for before, after in zip(cif_rmses, fit_rmses, strict=True)),
            "reference_error_improved_count": sum(after < before for before, after in zip(cif_errors, fit_errors, strict=True)),
            "success_count": sum(bool(r["optimizer"]["success"]) for r in rows),
            "failure_count": sum(not bool(r["optimizer"]["success"]) for r in rows),
            "mean_runtime_seconds": _mean(runtimes),
            "median_runtime_seconds": _median(runtimes),
        },
        "interpretation": (
            "Exploratory development comparison only. RRUFF refined cells are posthoc reference estimates; "
            "they are not exact ground truth and were not used by the fit."
        ),
    }
    return {
        "schema_version": 1,
        "stage": "3_baselines_and_protocol_only",
        "status": "COMPLETED_NO_TRAINING",
        "gate_source": str(stage2_path),
        "gate_status": "GO_GATE_PASS",
        "cif_sha256": GROSSULAR_CANDIDATE.sha256,
        "population": expected_ids,
        "settings": {
            "free_structural_parameter": "a_angstrom",
            "fixed_instrument_settings_from_stage2": True,
            "data": "same 12 predeclared non-frozen development profiles",
            "no_test_or_locked_test_data": True,
        },
        "summary": summary,
        "samples": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage2-result", type=Path, required=True)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--frozen-manifest", type=Path, required=True)
    parser.add_argument("--frozen-split", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.stage2_result, args.archive_root, args.frozen_manifest, args.frozen_split)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
