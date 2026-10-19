"""Pinned Grossular material project and a one-free-parameter physics fit.

The fit consumes only the two numeric profile columns. Reference cell values
are carried separately by the local data loader and are not passed to it.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
from scipy.optimize import minimize_scalar

from .candidates import Candidate
from .crystal import render
from .garnet_audit import _frozen_roles, exact_id, parse_refinement_output


ROOT = Path(__file__).resolve().parent
PROJECT_DIR = ROOT / "projects" / "grossular"
PROFILE_PATH = PROJECT_DIR / "project.json"
PROFILE = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
TEMPLATE_PATH = PROJECT_DIR / PROFILE["structure_template"]["relative_path"]
GROSSULAR_CANDIDATE = Candidate(
    id="grossular_garnet_cod9001868",
    name="Grossular garnet (Ia-3d)",
    formula="Ca3Al2Si3O12",
    crystal_system="cubic",
    cif=TEMPLATE_PATH,
    source_url=PROFILE["structure_template"]["source_url"],
    source_record=PROFILE["structure_template"]["source_record"],
    source_license=PROFILE["structure_template"]["source_license"],
    lattice_tolerance=float(PROFILE["structure_constraints"]["initial_parameter_bound_fraction"]),
    expected_sha256=PROFILE["structure_template"]["sha256"],
)


@dataclass(frozen=True)
class FitResult:
    candidate_id: str
    initial_a_angstrom: float
    fitted_a_angstrom: float
    score_rmse: float
    initial_score_rmse: float
    improvement_rmse: float
    wavelength_angstrom: float
    zero_shift_deg_fixed: float
    fwhm_deg_fixed: float
    scale_linear_fit: float
    background_linear_fit: float
    lower_a_angstrom: float
    upper_a_angstrom: float
    success: bool
    optimizer: str
    evaluations: int
    elapsed_seconds: float
    residual: np.ndarray
    predicted: np.ndarray

    def summary(self) -> dict[str, Any]:
        result = asdict(self)
        result.pop("residual")
        result.pop("predicted")
        result["free_structural_parameters"] = ["a_angstrom"]
        return result


@dataclass(frozen=True)
class DevelopmentSample:
    sample_id: str
    mineral_name: str
    measured_chemistry: str
    sample_description: str
    exact_raw_member: str
    raw_member_sha256: str
    point_count: int
    two_theta_min_deg: float
    two_theta_max_deg: float
    wavelength_proxy_from_refinement_angstrom: float
    cell_reference_for_posthoc_only: dict[str, Any]
    two_theta: np.ndarray
    intensity: np.ndarray


def load_candidate() -> Any:
    """Hash-check and parse the independent COD template."""
    return GROSSULAR_CANDIDATE.load()


def _parse_xy_without_headers(text: str) -> tuple[np.ndarray, np.ndarray]:
    xs: list[float] = []
    ys: list[float] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.replace(",", " ").split()
        if len(parts) < 2:
            continue
        try:
            x, y = float(parts[0]), float(parts[1])
        except ValueError:
            continue
        if math.isfinite(x) and math.isfinite(y):
            xs.append(x)
            ys.append(y)
    return np.asarray(xs, dtype=np.float64), np.asarray(ys, dtype=np.float64)


def _parse_header(text: str) -> dict[str, str]:
    values = {}
    for line in text.splitlines():
        if line.startswith("##") and "=" in line:
            k, v = line[2:].split("=", 1)
            values[k.strip().upper()] = v.strip()
    return values


def load_development_sample(sample_id: str, archive_root: Path, *,
                            frozen_manifest: Path,
                            frozen_split: Path) -> DevelopmentSample:
    """Load only a non-frozen, exact-ID Grossular raw profile.

    The raw XY header is parsed solely to guard sample identity and chemistry;
    its `CELL PARAMETERS` field is never returned. The cell reference comes
    from the separate exact-ID refinement output and is retained posthoc.
    """
    roles = _frozen_roles(frozen_manifest, frozen_split)
    if not (frozen_manifest.is_file() and frozen_split.is_file()):
        raise FileNotFoundError("both frozen RRUFF boundary files are required")
    role = roles.get(sample_id.split("-", 1)[0])
    if role is not None:
        raise ValueError(f"{sample_id} is not eligible for new development; frozen/previous role={role}")
    archive_root = Path(archive_root)
    with zipfile.ZipFile(archive_root / "XY_RAW.zip") as zf:
        hits = [n for n in zf.namelist() if exact_id(n) == sample_id]
        if len(hits) != 1:
            raise ValueError(f"expected one exact-ID raw member for {sample_id}, found {len(hits)}")
        raw_bytes = zf.read(hits[0])
    raw_text = raw_bytes.decode("latin-1", errors="replace")
    header = _parse_header(raw_text)
    if header.get("NAMES", "").casefold() != "grossular":
        raise ValueError(f"{sample_id} is not labeled Grossular")
    description = header.get("DIFFRACTION SAMPLE DESCRIPTION", "")
    if not description.casefold().startswith("powder") or any(t in description.casefold() for t in ("mixture", "contamination", "two phase", "two-phase")):
        raise ValueError(f"{sample_id} is not a clean, single-phase powder development profile: {description}")
    x, y = _parse_xy_without_headers(raw_text)
    if len(x) < 100 or len(x) != len(y) or not np.all(np.diff(x) > 0) or np.ptp(y) <= 0:
        raise ValueError(f"{sample_id} has an invalid XY numeric profile")
    # No cell-header value is read. Cell reference is pulled from the distinct
    # refinement-output artifact and is used only after fitting is complete.
    with zipfile.ZipFile(archive_root / "Refinement_Output_Data.zip") as zf:
        out_hits = [n for n in zf.namelist() if exact_id(n) == sample_id]
        if len(out_hits) != 1:
            raise ValueError(f"expected one exact-ID refinement output for {sample_id}, found {len(out_hits)}")
        out_text = zf.read(out_hits[0]).decode("latin-1", errors="replace")
    ref = parse_refinement_output(out_text)
    waves = ref["wavelengths"]
    if len(waves) < 2 or not ref["complete_six"]:
        raise ValueError(f"{sample_id} lacks complete cell reference or wavelength #2")
    return DevelopmentSample(
        sample_id=sample_id,
        mineral_name=header.get("NAMES", ""),
        measured_chemistry=header.get("MEASURED CHEMISTRY", ""),
        sample_description=description,
        exact_raw_member=hits[0],
        raw_member_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        point_count=len(x),
        two_theta_min_deg=float(x[0]),
        two_theta_max_deg=float(x[-1]),
        wavelength_proxy_from_refinement_angstrom=float(waves[1]),
        cell_reference_for_posthoc_only=ref["cell"],
        two_theta=x,
        intensity=y,
    )


def _fit_scale_background(profile: np.ndarray, observed: np.ndarray) -> tuple[float, float, np.ndarray]:
    p = np.asarray(profile, dtype=np.float64)
    y = np.asarray(observed, dtype=np.float64)
    matrix = np.column_stack((p, np.ones_like(p)))
    scale, background = np.linalg.lstsq(matrix, y, rcond=None)[0]
    scale = max(float(scale), 0.0)
    background = max(float(background), 0.0)
    predicted = scale * p + background
    return scale, background, predicted


def fit_single_a(two_theta: np.ndarray, intensity: np.ndarray, wavelength_angstrom: float, *,
                 fwhm_deg: float = 0.14, zero_shift_deg: float = 0.0,
                 candidate: Candidate = GROSSULAR_CANDIDATE) -> FitResult:
    """Refine cubic `a` only; wavelength, shift and width remain fixed.

    Intensity scale and constant background are re-estimated by linear least
    squares at each `a`, avoiding additional nonlinear fit parameters.
    """
    crystal = candidate.load()
    x = np.asarray(two_theta, dtype=np.float64)
    y = np.asarray(intensity, dtype=np.float64)
    if x.ndim != 1 or y.shape != x.shape or len(x) < 100 or not np.all(np.diff(x) > 0):
        raise ValueError("fit input requires matching increasing 2theta/intensity vectors")
    if not np.all(np.isfinite(y)) or np.max(y) <= 0 or np.min(y) < 0:
        raise ValueError("fit intensity must be finite, nonnegative, and nonzero")
    yn = y / float(np.max(y))
    if len(x) > 2500:
        fit_x = np.linspace(float(x[0]), float(x[-1]), 2500)
        fit_y = np.interp(fit_x, x, yn)
    else:
        fit_x, fit_y = x, yn

    def evaluate(a_value: float) -> tuple[float, float, float, np.ndarray]:
        profile = render(crystal, fit_x, wavelength_angstrom, a=a_value, c=a_value,
                         zero_shift=zero_shift_deg, fwhm=fwhm_deg)
        scale, background, predicted = _fit_scale_background(profile, fit_y)
        score = float(np.sqrt(np.mean(np.square(fit_y - predicted))))
        return score, scale, background, predicted

    fraction = candidate.lattice_tolerance
    low, high = crystal.a * (1.0 - fraction), crystal.a * (1.0 + fraction)
    initial_profile_full = render(crystal, x, wavelength_angstrom, a=crystal.a, c=crystal.a,
                                  zero_shift=zero_shift_deg, fwhm=fwhm_deg)
    _, _, initial_predicted_full = _fit_scale_background(initial_profile_full, yn)
    initial_score = float(np.sqrt(np.mean(np.square(yn - initial_predicted_full))))
    start = perf_counter()
    solution = minimize_scalar(lambda a: evaluate(float(a))[0], bounds=(low, high), method="bounded",
                               options={"xatol": 1e-5, "maxiter": 80})
    elapsed = perf_counter() - start
    fitted = float(solution.x)
    # Report full-grid overlay / residual even when the optimizer used a coarse mesh.
    full_profile = render(crystal, x, wavelength_angstrom, a=fitted, c=fitted,
                          zero_shift=zero_shift_deg, fwhm=fwhm_deg)
    scale, background, predicted = _fit_scale_background(full_profile, yn)
    residual = yn - predicted
    full_rmse = float(np.sqrt(np.mean(np.square(residual))))
    return FitResult(candidate.id, crystal.a, fitted, full_rmse, initial_score,
                     initial_score - full_rmse, float(wavelength_angstrom), float(zero_shift_deg),
                     float(fwhm_deg), scale, background, low, high, bool(solution.success),
                     "scipy.optimize.minimize_scalar(method=bounded), one free structural parameter",
                     int(solution.nfev), elapsed, residual, predicted)


def fit_multistart_a(two_theta: np.ndarray, intensity: np.ndarray, wavelength_angstrom: float, *,
                     starts: tuple[float, ...] = (0.975, 0.99, 1.0, 1.01, 1.025),
                     fwhm_deg: float = 0.14, zero_shift_deg: float = 0.0,
                     candidate: Candidate = GROSSULAR_CANDIDATE) -> dict[str, Any]:
    """Multistart L-BFGS-B baseline over the fixed, predeclared cubic-a bounds."""
    from scipy.optimize import minimize

    crystal = candidate.load()
    x = np.asarray(two_theta, dtype=np.float64)
    y = np.asarray(intensity, dtype=np.float64)
    if x.ndim != 1 or y.shape != x.shape or len(x) < 100 or not np.all(np.diff(x) > 0):
        raise ValueError("fit input requires matching increasing 2theta/intensity vectors")
    yn = y / float(np.max(y))
    fit_x = np.linspace(float(x[0]), float(x[-1]), min(2500, len(x))) if len(x) > 2500 else x
    fit_y = np.interp(fit_x, x, yn) if len(x) > 2500 else yn
    fraction = candidate.lattice_tolerance
    bounds = [(crystal.a * (1 - fraction), crystal.a * (1 + fraction))]
    evaluations = 0

    def objective(vector):
        nonlocal evaluations
        evaluations += 1
        a_value = float(vector[0])
        profile = render(crystal, fit_x, wavelength_angstrom, a=a_value, c=a_value,
                         zero_shift=zero_shift_deg, fwhm=fwhm_deg)
        _, _, predicted = _fit_scale_background(profile, fit_y)
        return float(np.mean(np.square(fit_y - predicted)))

    t0 = perf_counter()
    attempts = []
    for fraction_start in starts:
        x0 = min(bounds[0][1], max(bounds[0][0], crystal.a * fraction_start))
        result = minimize(objective, np.asarray([x0]), method="L-BFGS-B", bounds=bounds,
                          options={"maxiter": 60, "ftol": 1e-10, "maxls": 20})
        attempts.append({"start_a_angstrom": float(x0), "fitted_a_angstrom": float(result.x[0]),
                         "score_rmse_coarse": float(math.sqrt(max(float(result.fun), 0.0))),
                         "success": bool(result.success), "message": str(result.message),
                         "iterations": int(result.nit)})
    elapsed = perf_counter() - t0
    best = min(attempts, key=lambda r: r["score_rmse_coarse"])
    a = best["fitted_a_angstrom"]
    p = render(crystal, x, wavelength_angstrom, a=a, c=a, zero_shift=zero_shift_deg, fwhm=fwhm_deg)
    scale, background, pred = _fit_scale_background(p, yn)
    residual = yn - pred
    return {
        "candidate_id": candidate.id,
        "best_a_angstrom": a,
        "score_rmse": float(np.sqrt(np.mean(np.square(residual)))),
        "scale_linear_fit": scale,
        "background_linear_fit": background,
        "wavelength_angstrom": float(wavelength_angstrom),
        "zero_shift_deg_fixed": float(zero_shift_deg),
        "fwhm_deg_fixed": float(fwhm_deg),
        "bounds_angstrom": bounds[0],
        "starts_fraction_of_cif_a": starts,
        "attempts": attempts,
        "evaluations": evaluations,
        "elapsed_seconds": elapsed,
        "free_structural_parameters": ["a_angstrom"],
        "residual": residual,
        "predicted": pred,
        "success": any(r["success"] for r in attempts),
    }


def real_sample_result(sample: DevelopmentSample, *, fwhm_deg: float = 0.14,
                       wavelength_angstrom: float | None = None) -> dict[str, Any]:
    """Fit the profile first; compare with the RRUFF cell only posthoc."""
    wavelength = wavelength_angstrom or sample.wavelength_proxy_from_refinement_angstrom
    fit = fit_single_a(sample.two_theta, sample.intensity, wavelength, fwhm_deg=fwhm_deg)
    reference = sample.cell_reference_for_posthoc_only["a"]["value"]
    return {
        "sample_id": sample.sample_id,
        "mineral_name": sample.mineral_name,
        "measured_chemistry": sample.measured_chemistry,
        "description": sample.sample_description,
        "raw_member_sha256": sample.raw_member_sha256,
        "point_count": sample.point_count,
        "two_theta_min_deg": sample.two_theta_min_deg,
        "two_theta_max_deg": sample.two_theta_max_deg,
        "wavelength_proxy_angstrom": wavelength,
        "posthoc_refinement_reference_a_angstrom": reference,
        "posthoc_reference_esd_a_angstrom": sample.cell_reference_for_posthoc_only["a"]["esd"],
        "posthoc_fit_error_a_angstrom": fit.fitted_a_angstrom - reference,
        "posthoc_fit_error_a_percent": 100.0 * (fit.fitted_a_angstrom - reference) / reference,
        "fit": fit.summary(),
        "initial_residual_rmse": fit.initial_score_rmse,
        "fitted_residual_rmse": fit.score_rmse,
        "rmse_improvement": fit.initial_score_rmse - fit.score_rmse,
        "interpretation": "development-only profile fit; refinement cell is a posthoc RRUFF reference estimate, not exact ground truth",
    }


def save_real_results(results: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
