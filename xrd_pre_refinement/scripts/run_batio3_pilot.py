#!/usr/bin/env python
"""Reproducible small simulated engineering pilot; no training is performed."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(REPO / "xrd_robustness" / "src"))

from xrd_pre_refinement.baseline import rank_single_phase_templates
from xrd_pre_refinement.parameter_fit import fit_candidate_parameters
from xrd_pre_refinement.registry import load_registry
from xrd_pre_refinement.reporting import build_report
from xrd_pre_refinement.simulation import simulate_cif


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _format_json(value, level: int = 0) -> str:
    """Pretty-print objects while wrapping long scalar arrays in compact rows."""
    indent = "  " * level
    if isinstance(value, dict):
        if not value:
            return "{}"
        rows = [
            f'{"  " * (level + 1)}{json.dumps(str(key), ensure_ascii=False)}: {_format_json(item, level + 1)}'
            for key, item in value.items()
        ]
        return "{\n" + ",\n".join(rows) + f"\n{indent}}}"
    if isinstance(value, list):
        if not value:
            return "[]"
        if all(not isinstance(item, (dict, list)) for item in value):
            chunks: list[str] = []
            current = ""
            for item in value:
                rendered = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
                if current and len(current) + len(rendered) + 2 > 100:
                    chunks.append(current)
                    current = rendered
                else:
                    current = rendered if not current else f"{current}, {rendered}"
            chunks.append(current)
            rows = ["  " * (level + 1) + chunk for chunk in chunks]
            return "[\n" + ",\n".join(rows) + f"\n{indent}]"
        rows = ["  " * (level + 1) + _format_json(item, level + 1) for item in value]
        return "[\n" + ",\n".join(rows) + f"\n{indent}]"
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def write_json(path: Path, value) -> None:
    path.write_text(_format_json(value) + "\n", encoding="utf-8")


def representative_peaks(structure, wavelength: float) -> dict[str, object]:
    """Summarize simulated Bragg features around two diagnostic windows."""
    from pymatgen.analysis.diffraction.xrd import XRDCalculator

    pattern = XRDCalculator(wavelength=wavelength).get_pattern(
        structure, two_theta_range=(40.0, 68.0), scaled=True
    )
    windows = {"around_45_deg": (44.0, 46.0), "around_66_deg": (65.0, 67.0)}
    summary: dict[str, object] = {}
    for label, (lower, upper) in windows.items():
        rows = []
        for position, intensity, families in zip(pattern.x, pattern.y, pattern.hkls, strict=True):
            if lower <= position <= upper:
                rows.append({
                    "two_theta_deg": round(float(position), 5),
                    "relative_intensity": round(float(intensity), 5),
                    "hkl_families": [list(map(int, family["hkl"])) for family in families],
                })
        summary[label] = rows
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "reports" / "pilot_run")
    parser.add_argument("--registry", type=Path, default=ROOT / "configs" / "registry.json")
    args = parser.parse_args()
    registry_path = args.registry.resolve()
    router, config_dir = load_registry(registry_path)
    family = router.families["batio3_pilot"]
    route = router.route("batio3_pilot", "BaTiO3")
    if route.status != "ROUTED":
        raise RuntimeError(f"pilot metadata route failed: {route}")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    instrument = family["instrument"]
    template_measurement = family["template_measurement"]
    measurement = family["pilot_measurement"]
    profiles: dict[str, np.ndarray] = {}
    axis: np.ndarray | None = None
    manifest_candidates = []
    for index, candidate in enumerate(family["candidates"]):
        cif = (config_dir / candidate["cif_path"]).resolve()
        expected_symbol = candidate["space_group"]["symbol"]
        expected_number = candidate["space_group"]["number"]
        candidate_instrument = dict(instrument)
        candidate_instrument["_expected_space_group"] = {
            "symbol": expected_symbol,
            "number": expected_number,
        }
        template = simulate_cif(
            cif, candidate_instrument, template_measurement, seed=100 + index,
            robustness_source=REPO / "xrd_robustness" / "src",
        )
        if template.space_group_symbol != expected_symbol or template.space_group_number != expected_number:
            raise RuntimeError(f"space group check failed for {candidate['candidate_id']}")
        profiles[candidate["candidate_id"]] = template.intensity
        axis = template.two_theta_deg
        manifest_candidates.append({
            "candidate_id": candidate["candidate_id"],
            "cif_sha256": sha256(cif),
            "space_group_from_cif": {"symbol": template.space_group_symbol, "number": template.space_group_number},
            "sites": len(template.structure),
            "reduced_formula": template.structure.composition.reduced_formula,
            "cif_source": candidate["cif_source"],
            "representative_ideal_bragg_peaks": representative_peaks(
                template.structure, float(instrument["wavelength_angstrom"])
            ),
        })
    assert axis is not None
    # Use a separately seeded repeat of the tetragonal candidate as the
    # illustrative input. It is simulated data, not an experimental prediction.
    target_candidate_id = family["pilot_observation_candidate"]
    target_candidate = next(
        candidate for candidate in family["candidates"]
        if candidate["candidate_id"] == target_candidate_id
    )
    target_cif = (config_dir / target_candidate["cif_path"]).resolve()
    target_instrument = dict(instrument)
    target_instrument["_expected_space_group"] = target_candidate["space_group"]
    observed = simulate_cif(
        target_cif, target_instrument, measurement, seed=812,
        robustness_source=REPO / "xrd_robustness" / "src",
    ).intensity
    ranked = rank_single_phase_templates(
        observed, profiles, family["candidates"], top_k=len(family["candidates"])
    )
    fits_by_candidate = {}
    for candidate in family["candidates"]:
        candidate_cif = (config_dir / candidate["cif_path"]).resolve()
        fits_by_candidate[candidate["candidate_id"]] = fit_candidate_parameters(
            candidate_cif,
            observed,
            instrument,
            measurement,
            expected_space_group=candidate["space_group"],
            robustness_source=REPO / "xrd_robustness" / "src",
        )
    for row in ranked:
        row["limited_forward_fit"] = fits_by_candidate[row["candidate_id"]]
    report = build_report(
        sample_id="batio3_tetragonal_simulated_engineering_example",
        route=route.__dict__,
        ranked_candidates=ranked,
        observed_profile=observed.astype(float).tolist(),
        two_theta_deg=axis.astype(float).tolist(),
        model_id="template-normalized-rmse-plus-limited-forward-fit-demo-v1",
    )
    write_json(out / "pre_refinement_report.json", report)

    # An explicitly synthetic intensity-weight mixture is only a safety test.
    mix_ids = family["mixture_stress_candidates"]
    mix_coefficients = family["mixture_stress_coefficients"]
    if len(mix_ids) != len(mix_coefficients) or not mix_ids:
        raise ValueError("mixture stress candidate ids and coefficients must have matching non-empty lengths")
    if any(candidate_id not in profiles for candidate_id in mix_ids):
        raise ValueError("mixture stress configuration refers to an unknown candidate")
    mixture = sum(
        float(weight) * profiles[candidate_id]
        for candidate_id, weight in zip(mix_ids, mix_coefficients, strict=True)
    )
    mixture /= max(float(mixture.max()), 1e-12)
    mixture_ranked = rank_single_phase_templates(
        mixture, profiles, family["candidates"], top_k=len(family["candidates"])
    )
    mixture_report = build_report(
        sample_id="batio3_synthetic_intensity_mix_stress_example",
        route=route.__dict__,
        ranked_candidates=mixture_ranked,
        observed_profile=mixture.astype(float).tolist(),
        two_theta_deg=axis.astype(float).tolist(),
        model_id="template-normalized-rmse-v1",
        mixture_stress_case=True,
    )
    mixture_report["coexistence_hypothesis"]["simulated_intensity_weights"] = {
        candidate_id: float(weight)
        for candidate_id, weight in zip(mix_ids, mix_coefficients, strict=True)
    }
    mixture_report["coexistence_hypothesis"]["weight_basis"] = "arbitrary normalized profile-intensity mixing coefficients; not wt%"
    write_json(out / "synthetic_mix_stress_report.json", mixture_report)
    np.savetxt(out / "simulated_example.csv", np.column_stack((axis, observed)), delimiter=",", header="two_theta_deg,intensity", comments="")

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(axis, observed, color="#222222", lw=1.3, label="simulated tetragonal observation")
        for candidate in family["candidates"]:
            ax.plot(axis, profiles[candidate["candidate_id"]], lw=1.0, alpha=0.85, label=f"template: {candidate['phase_id']}")
            fit_profile = np.asarray(
                fits_by_candidate[candidate["candidate_id"]]["fitted_forward_profile"],
                dtype=np.float64,
            )
            ax.plot(
                axis,
                fit_profile,
                lw=1.0,
                ls="--",
                label=f"bounded forward fit: {candidate['phase_id']}",
            )
        ax.set(xlabel=r"2$\theta$ (degrees)", ylabel="normalized intensity", title="BaTiO3 pilot: candidate templates and bounded forward fits")
        ax.legend(frameon=False)
        fig.tight_layout()
        fig.savefig(out / "batio3_template_comparison.png", dpi=180)
        plt.close(fig)
    except ImportError:
        pass

    try:
        git_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        git_commit = None
    try:
        working_tree_dirty = bool(subprocess.run(
            ["git", "status", "--porcelain"], cwd=REPO, check=True,
            capture_output=True, text=True,
        ).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        working_tree_dirty = None
    source_files = sorted(
        [*ROOT.joinpath("src").rglob("*.py"), *ROOT.joinpath("scripts").glob("*.py")]
    )
    def position_for_hkl(candidate_id: str, hkl: list[int]) -> float:
        candidate_summary = next(row for row in manifest_candidates if row["candidate_id"] == candidate_id)
        for rows in candidate_summary["representative_ideal_bragg_peaks"].values():
            for peak in rows:
                if hkl in peak["hkl_families"]:
                    return float(peak["two_theta_deg"])
        raise ValueError(f"diagnostic hkl {hkl} was not found for {candidate_id}")

    cubic_id = next(
        candidate["candidate_id"] for candidate in family["candidates"]
        if candidate["space_group"]["symbol"] == "Pm-3m"
    )
    tetragonal_id = next(
        candidate["candidate_id"] for candidate in family["candidates"]
        if candidate["space_group"]["symbol"] == "P4mm"
    )
    cubic_200 = position_for_hkl(cubic_id, [2, 0, 0])
    tetragonal_002 = position_for_hkl(tetragonal_id, [0, 0, 2])
    tetragonal_200 = position_for_hkl(tetragonal_id, [2, 0, 0])
    nominal_split = abs(tetragonal_200 - tetragonal_002)
    manifest = {
        "run_kind": "simulated_engineering_demo_not_scientific_result",
        "date": date.today().isoformat(),
        "git_commit": git_commit,
        "working_tree_dirty_at_run": working_tree_dirty,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "command": "python xrd_pre_refinement/scripts/run_batio3_pilot.py",
        "registry_sha256": sha256(registry_path),
        "family_config_sha256": sha256(config_dir / "families" / "batio3_pilot.json"),
        "instrument": instrument,
        "template_measurement": template_measurement,
        "measurement": measurement,
        "noise_seed_observation": 812,
        "observation_candidate_id": target_candidate_id,
        "limited_forward_fit": {
            "candidate_count": len(fits_by_candidate),
            "fitted_candidate_ids": list(fits_by_candidate),
            "parameter_intervals": "NOT_ESTIMATED",
            "bound_interpretation": "engineering demo search limits only; not validated priors",
            "per_candidate": {
                candidate_id: {
                    "fit_success": result["fit_success"],
                    "normalized_rmse_before": result["normalized_rmse_before"],
                    "normalized_rmse_after": result["normalized_rmse_after"],
                    "fitted_values": result["fitted_values"],
                    "search_bounds": result["search_bounds"],
                    "function_evaluations": result["function_evaluations"],
                }
                for candidate_id, result in fits_by_candidate.items()
            },
        },
        "source_context": family["source_context"],
        "discriminability_notes": family["discriminability_notes"],
        "representative_feature_comparison": {
            "wavelength_angstrom": float(instrument["wavelength_angstrom"]),
            "cubic_200_two_theta_deg": cubic_200,
            "tetragonal_002_two_theta_deg": tetragonal_002,
            "tetragonal_200_two_theta_deg": tetragonal_200,
            "tetragonal_002_200_split_deg": nominal_split,
            "observation_fwhm_deg": float(measurement["fwhm_deg"]),
            "split_to_observation_fwhm_ratio": nominal_split / float(measurement["fwhm_deg"]),
            "interpretation": "Ideal structure-derived powder calculation at the explicit simulation wavelength; this ratio is not an experimental resolution guarantee.",
        },
        "source_code_sha256": {
            path.relative_to(ROOT).as_posix(): sha256(path) for path in source_files
        },
        "candidates": manifest_candidates,
        "model_training": "NOT_RUN",
        "probability_calibration": "NOT_FITTED",
        "phase_fraction_estimation": "NOT_IMPLEMENTED",
        "mix_recipe": {
            "candidate_ids": mix_ids,
            "coefficients": [float(value) for value in mix_coefficients],
            "interpretation": "arbitrary normalized profile-intensity mixing coefficients only; not phase fractions",
        },
    }
    write_json(out / "run_manifest.json", manifest)
    print(json.dumps({
        "status": "SIMULATED_ENGINEERING_DEMO_COMPLETE",
        "out": str(out),
        "top_ranked_candidate": ranked[0]["candidate_id"],
        "ranking_scores_are_probabilities": False,
        "limited_fit_summary": {
            candidate_id: {
                "fit_success": result["fit_success"],
                "normalized_rmse_before": result["normalized_rmse_before"],
                "normalized_rmse_after": result["normalized_rmse_after"],
                "fitted_values": result["fitted_values"],
            }
            for candidate_id, result in fits_by_candidate.items()
        },
        "review_required": report["review"]["required"],
        "mixture_review_required": mixture_report["review"]["required"],
        "figure": str(out / "batio3_template_comparison.png"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
