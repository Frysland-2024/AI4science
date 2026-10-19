#!/usr/bin/env python3
"""Run the bounded Grossular synthetic gate and non-frozen RRUFF dev check."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks

from pxrd_router_mvp.crystal import render
from pxrd_router_mvp.grossular_project import (
    GROSSULAR_CANDIDATE,
    PROFILE,
    fit_multistart_a,
    fit_single_a,
    load_candidate,
    load_development_sample,
)


def _peak_alignment(x: np.ndarray, observed: np.ndarray, predicted: np.ndarray, *,
                    top_n: int, tolerance_deg: float) -> dict:
    y = observed / float(np.max(observed))
    p = predicted / float(np.max(predicted))
    observed_peaks, _ = find_peaks(y, prominence=0.03, distance=5)
    model_peaks, _ = find_peaks(p, prominence=0.03, distance=5)
    selected = sorted(model_peaks, key=lambda idx: p[idx], reverse=True)[:top_n]
    offsets = []
    for idx in selected:
        if len(observed_peaks):
            nearest = int(observed_peaks[np.argmin(np.abs(x[observed_peaks] - x[idx]))])
            offsets.append({
                "predicted_two_theta_deg": float(x[idx]),
                "nearest_measured_two_theta_deg": float(x[nearest]),
                "absolute_offset_deg": float(abs(x[nearest] - x[idx])),
                "within_gate": bool(abs(x[nearest] - x[idx]) <= tolerance_deg),
            })
        else:
            offsets.append({"predicted_two_theta_deg": float(x[idx]), "nearest_measured_two_theta_deg": None,
                            "absolute_offset_deg": None, "within_gate": False})
    matched = sum(bool(entry["within_gate"]) for entry in offsets)
    return {"predicted_peak_count_checked": len(offsets), "matched_count": matched,
            "match_fraction": matched / len(offsets) if offsets else 0.0,
            "tolerance_deg": tolerance_deg, "peak_offsets": offsets}


def run_synthetic_gate() -> dict:
    crystal = load_candidate()
    cfg = PROFILE["forward_model"]
    x = np.arange(5.0, 90.0001, 0.04)
    truth_a = 11.93
    wavelength = float(cfg["fixed_wavelength_angstrom"])
    generated = render(crystal, x, wavelength, a=truth_a, c=truth_a,
                       zero_shift=float(cfg["fixed_zero_shift_deg"]),
                       fwhm=float(cfg["fixed_fwhm_deg"]))
    rng = np.random.default_rng(20261019)
    y = np.clip(0.02 + 0.94 * generated + rng.normal(0, 0.001, len(x)), 0.0, None)
    fit = fit_single_a(x, y, wavelength,
                       fwhm_deg=float(cfg["fixed_fwhm_deg"]),
                       zero_shift_deg=float(cfg["fixed_zero_shift_deg"]))
    limit = float(PROFILE["real_explanation_gate_predeclared"]["synthetic_a_recovery_abs_error_angstrom_max"])
    error = abs(fit.fitted_a_angstrom - truth_a)
    return {"status": "PASS" if fit.success and error <= limit else "FAIL",
            "known_a_angstrom": truth_a, "fitted_a_angstrom": fit.fitted_a_angstrom,
            "absolute_error_angstrom": error, "predeclared_limit_angstrom": limit,
            "rmse": fit.score_rmse, "fit": fit.summary(),
            "seed": 20261019, "synthetic_only": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--frozen-manifest", type=Path, required=True)
    parser.add_argument("--frozen-split", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    crystal = load_candidate()
    synthetic = run_synthetic_gate()
    payload = {
        "schema_version": 1,
        "project_id": PROFILE["project_id"],
        "cif_sha256": GROSSULAR_CANDIDATE.sha256,
        "synthetic_gate": synthetic,
        "real_development": {"status": "NOT_RUN_SYNTHETIC_GATE_FAILED", "samples": []},
    }
    if synthetic["status"] != "PASS":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"synthetic_gate": synthetic["status"], "real_development": "not run"}, ensure_ascii=False))
        return 2

    fixed_wavelength = float(PROFILE["forward_model"]["fixed_wavelength_angstrom"])
    fixed_fwhm = float(PROFILE["forward_model"]["fixed_fwhm_deg"])
    fixed_shift = float(PROFILE["forward_model"]["fixed_zero_shift_deg"])
    gate = PROFILE["real_explanation_gate_predeclared"]
    ids = list(PROFILE["development_sample_ids"])
    samples = []
    errors = []
    for sample_id in ids:
        try:
            samples.append(load_development_sample(sample_id, args.archive_root,
                                                   frozen_manifest=args.frozen_manifest,
                                                   frozen_split=args.frozen_split))
        except Exception as exc:
            errors.append({"sample_id": sample_id, "error": f"{type(exc).__name__}: {exc}"})

    results = []
    for sample in samples:
        # The same predeclared wavelength and instrument settings are held fixed
        # for every sample. The refinement reference is accessed only after the
        # profile has been fit and is used as posthoc context.
        fit = fit_single_a(sample.two_theta, sample.intensity, fixed_wavelength,
                           fwhm_deg=fixed_fwhm, zero_shift_deg=fixed_shift)
        alignment = _peak_alignment(sample.two_theta, sample.intensity, fit.predicted,
                                    top_n=int(gate["predicted_reflections_to_check_per_profile"]),
                                    tolerance_deg=float(gate["measured_peak_match_window_deg"]))
        posthoc = sample.cell_reference_for_posthoc_only["a"]
        results.append({
            "sample_id": sample.sample_id,
            "mineral_name": sample.mineral_name,
            "measured_chemistry": sample.measured_chemistry,
            "description": sample.sample_description,
            "raw_member_sha256": sample.raw_member_sha256,
            "point_count": sample.point_count,
            "two_theta_range_deg": [sample.two_theta_min_deg, sample.two_theta_max_deg],
            "wavelength_used_angstrom": fixed_wavelength,
            "wavelength_proxy_from_same_id_refinement_output_angstrom": sample.wavelength_proxy_from_refinement_angstrom,
            "fit": fit.summary(),
            "peak_alignment": alignment,
            "posthoc_reference_a_angstrom": posthoc["value"],
            "posthoc_reference_esd_a_angstrom": posthoc["esd"],
            "posthoc_fit_minus_reference_angstrom": fit.fitted_a_angstrom - posthoc["value"],
            "posthoc_fit_minus_reference_percent": 100 * (fit.fitted_a_angstrom - posthoc["value"]) / posthoc["value"],
            "reference_role": "posthoc_RRUFF_refinement_estimate_only",
        })
    improved = sum(r["fit"]["score_rmse"] < r["fit"]["initial_score_rmse"] for r in results)
    min_fraction = float(gate["minimum_fraction_of_development_profiles_with_rmse_improvement"])
    required = int(np.ceil(len(ids) * min_fraction))
    peak_required = float(gate["minimum_predicted_reflection_match_fraction"])
    peak_pass_count = sum(r["peak_alignment"]["match_fraction"] >= peak_required for r in results)
    real_pass = (not errors and len(results) == len(ids) and improved >= required and peak_pass_count >= required)
    payload["real_development"] = {
        "status": "GO_GATE_PASS" if real_pass else "NO_GO_GATE_FAIL",
        "population": "predeclared non-frozen Grossular development IDs only",
        "candidate_sample_count": len(ids),
        "loaded_sample_count": len(samples),
        "failed_sample_loads": errors,
        "rmse_improved_count": improved,
        "rmse_improved_required_count": required,
        "peak_alignment_pass_count": peak_pass_count,
        "peak_alignment_required_count": required,
        "predeclared_gate": gate,
        "samples": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"synthetic_gate": synthetic["status"],
                      "real_gate": payload["real_development"]["status"],
                      "real_samples": len(results), "failed_samples": len(errors),
                      "rmse_improved": improved, "rmse_required": required,
                      "peak_alignment_pass": peak_pass_count}, ensure_ascii=False))
    return 0 if real_pass else 1


if __name__ == "__main__":
    sys.exit(main())
