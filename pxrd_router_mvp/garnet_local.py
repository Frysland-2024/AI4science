"""Local-only real-spectrum Garnet pilot with post-fit reference isolation.

The input path reads only the selected numeric XY_RAW profile. It never reads
the cell parameters embedded in that file's header. Same-sample refinement
output is opened only by :func:`load_posthoc_reference`, after physical fitting.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import least_squares
from scipy.signal import find_peaks


WAVELENGTH_ANGSTROM = 1.541838
WAVELENGTH_SOURCE = (
    "RRUFF Cu K-alpha wavelength #1; fixed pilot protocol, 1.541838 A. "
    "The target sample's refinement output is not read before fitting."
)
COD_RECORD = "9001871"
COD_FORMULA = "Ca3Al2Si3O12"
COD_SPACE_GROUP = "Ia-3d"
COD_SPACE_GROUP_NUMBER = 230
COD_CIF_SHA256 = "EBDD9ABB0BB717A8154EE25B00E26E4AA69F9261EAAFA56B02FE77E30E3AFFD6"
START_OFFSETS = (-0.04, -0.02, 0.0, 0.02, 0.04)
LATTICE_TOLERANCE = 0.05
MAX_FIT_RMSE = 0.05
MAX_POSTHOC_A_ERROR_FRACTION = 0.01
MAX_MULTISTART_SPREAD_ANGSTROM = 0.02
STRONG_PEAK_PROMINENCE = 0.05
STRONG_PEAK_MATCH_TOLERANCE_DEG = 0.20
MIN_STRONG_PEAK_MATCH_FRACTION = 0.80


@dataclass(frozen=True)
class GarnetSampleProfile:
    sample_id: str
    mineral_name: str
    measured_chemistry: str
    locality: str
    source_note: str
    sample_description: str
    crystal_system: str
    space_group: str
    raw_archive_member: str
    raw_member_sha256: str
    refinement_output_member: str
    refinement_output_sha256: str


# These are independent powder records, chosen by subgroup, chemistry,
# locality/source, data quality, and frozen-split exclusion. No sample cell is
# present in this registry. The CIF candidate is an independent COD entry.
_SAMPLES = (
    GarnetSampleProfile(
        sample_id="R040066-1",
        mineral_name="Grossular",
        measured_chemistry="(Ca2.90 Fe2+0.08 Mn0.02)(Al1.87 Fe3+0.13)(Si1.00O4)3",
        locality="Redding, Connecticut, USA",
        source_note="RRUFF ODR specimen; compact registry does not copy private provider fields",
        sample_description="Powder; RRUFF records X-ray diffraction and chemical identification",
        crystal_system="cubic",
        space_group="Ia-3d",
        raw_archive_member="Grossular__R040066-1__Powder__Xray_Data_XY_RAW__5cc9a78577f6344e48b8730a3e66.txt",
        raw_member_sha256="BB2EA60ED728A8FD73009A9630FC83FAC494E5F36DD19DBB73EA8F035C8D1F37",
        refinement_output_member="Grossular__R040066-1__Powder__Cell_Refinement_Output_Data__0fdb4473862cc7ec6026631808ce.txt",
        refinement_output_sha256="CF45E2CD24B26B3D1BD86A6D33530E0B67395D8E963ADD16D64E019EA6F677B0",
    ),
    GarnetSampleProfile(
        sample_id="R050036-1",
        mineral_name="Grossular",
        measured_chemistry="(Ca2.95 Mg0.05)(Al1.70 Fe3+0.30)(Si1.00O4)3; trace P",
        locality="Wah Wah Mountains, Utah, USA",
        source_note="RRUFF ODR specimen; source attribution is retained in the local archive",
        sample_description="Powder; RRUFF records X-ray diffraction and chemical identification",
        crystal_system="cubic",
        space_group="Ia-3d",
        raw_archive_member="Grossular__R050036-1__Powder__Xray_Data_XY_RAW__5194ec6a21eb17289fffa6227faa.txt",
        raw_member_sha256="B496606B4676CCAD80281C7DD2923610C59DA3C9206D7335660C316CAD776327",
        refinement_output_member="Grossular__R050036-1__Powder__Cell_Refinement_Output_Data__a2dd9bc78f4fa81e97e1f2ad275f.txt",
        refinement_output_sha256="0825466B9572D656493B0E95B565022ED593F230947D467B5B4B5982CE294263",
    ),
    GarnetSampleProfile(
        sample_id="R060382-1",
        mineral_name="Grossular",
        measured_chemistry="(Ca2.95 Mg0.03 Mn0.02)Al2.00((Si0.99 Ti0.01)O4)3; trace Fe",
        locality="Lalatema near Kilimanjaro, Tanzania",
        source_note="RRUFF ODR specimen; source attribution is retained in the local archive",
        sample_description="Powder; independent base ID and locality",
        crystal_system="cubic",
        space_group="Ia-3d (mineral record; no paired DIF SG value in the audit row)",
        raw_archive_member="Grossular__R060382-1__Powder__Xray_Data_XY_RAW__f92c1182e83923eb07e666fc59ff.txt",
        raw_member_sha256="C868C700DC822A93377E0173B9D68CCA3736F6EB5E2F0B82E76CC90386B2A164",
        refinement_output_member="Grossular__R060382-1__Powder__Cell_Refinement_Output_Data__f95f484ffecb14051ec06ed30aa8.txt",
        refinement_output_sha256="E8B75F188DF78086414A7C89830A8C49A752A0835FD91B29746048CF989D5FCC",
    ),
)
SAMPLES_BY_ID = {sample.sample_id.removesuffix("-1"): sample for sample in _SAMPLES}
SAMPLES_BY_EXACT_ID = {sample.sample_id: sample for sample in _SAMPLES}


@dataclass(frozen=True)
class GarnetSpectrum:
    sample_id: str
    two_theta: np.ndarray
    intensity: np.ndarray
    wavelength_angstrom: float
    source: str


@dataclass(frozen=True)
class FitAttempt:
    label: str
    initial_a_angstrom: float
    a_angstrom: float
    zero_shift_deg: float
    fwhm_deg: float
    scale: float
    background: float
    background_slope: float
    rmse: float
    weighted_rmse: float
    success: bool
    solver_status: int
    solver_message: str
    iterations: int
    at_lattice_bound: bool
    predicted: np.ndarray
    residual: np.ndarray

    def summary(self) -> dict[str, Any]:
        row = asdict(self)
        row.pop("predicted")
        row.pop("residual")
        return row


@dataclass(frozen=True)
class GarnetFit:
    sample_id: str
    cif_path: str
    cif_sha256: str
    cif_formula: str
    cif_space_group: str
    cif_cell_a_angstrom: float
    initial_cell_fit: FitAttempt
    multi_start_attempts: tuple[FitAttempt, ...]

    @property
    def best(self) -> FitAttempt:
        return min(self.multi_start_attempts, key=lambda attempt: attempt.weighted_rmse)

    def summary(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "cif_path": self.cif_path,
            "cif_sha256": self.cif_sha256,
            "cif_formula": self.cif_formula,
            "cif_space_group": self.cif_space_group,
            "cif_cell_a_angstrom": self.cif_cell_a_angstrom,
            "initial_cell_fit": self.initial_cell_fit.summary(),
            "multi_start_attempts": [attempt.summary() for attempt in self.multi_start_attempts],
            "best": self.best.summary(),
        }


@dataclass(frozen=True)
class PosthocReference:
    sample_id: str
    a_angstrom: float
    a_esd_angstrom: float | None
    refinement_rmse: float | None
    wavelength_triplet_angstrom: tuple[float, ...]
    source_member: str
    source_sha256: str
    role: str = "posthoc_evaluation_only"


@dataclass(frozen=True)
class PilotEvaluation:
    sample_id: str
    fitted_a_angstrom: float
    reference_a_angstrom: float
    a_error_angstrom: float
    a_error_percent: float
    peak_match_fraction: float
    observed_strong_peak_count: int
    matched_strong_peak_count: int
    multi_start_spread_angstrom: float
    criteria: dict[str, bool]
    status: str


def available_garnet_samples() -> tuple[GarnetSampleProfile, ...]:
    return _SAMPLES


def sample_profile(sample_id: str) -> GarnetSampleProfile:
    key = sample_id.strip()
    if key.endswith("-1"):
        sample = SAMPLES_BY_EXACT_ID.get(key)
    else:
        sample = SAMPLES_BY_ID.get(key)
    if sample is None:
        raise ValueError(f"only the three curated Grossular development samples are available: {key}")
    return sample


def find_archive_root(explicit_root: str | Path | None = None) -> Path:
    candidate = explicit_root or os.environ.get("PXRD_RRUFF_ARCHIVE_ROOT")
    if candidate:
        root = Path(candidate).expanduser().resolve()
        if not (root / "XY_RAW.zip").is_file():
            raise FileNotFoundError(f"RRUFF archive root must contain XY_RAW.zip: {root}")
        return root
    for parent in Path(__file__).resolve().parents:
        root = parent / "RRUFF"
        if (root / "XY_RAW.zip").is_file():
            return root
    raise FileNotFoundError("RRUFF archive not found; set PXRD_RRUFF_ARCHIVE_ROOT to the local archive directory")


def _verified_member(root: Path, archive_name: str, member_name: str, expected_sha256: str) -> bytes:
    archive_path = root / archive_name
    if not archive_path.is_file():
        raise FileNotFoundError(f"local RRUFF archive is missing: {archive_path}")
    with zipfile.ZipFile(archive_path) as archive:
        try:
            payload = archive.read(member_name)
        except KeyError as exc:
            raise FileNotFoundError(f"member {member_name} not found in local {archive_name}") from exc
    actual = hashlib.sha256(payload).hexdigest().upper()
    if actual != expected_sha256.upper():
        raise ValueError(f"SHA-256 mismatch for local RRUFF member {member_name}: {actual}")
    return payload


def parse_xy_raw_numeric_rows(payload: bytes) -> tuple[np.ndarray, np.ndarray]:
    """Parse only numeric angle/intensity rows; discard every header field."""
    text = payload.decode("utf-8-sig", errors="replace")
    x_values: list[float] = []
    y_values: list[float] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = re.split(r"[\s,;\t]+", stripped)
        if len(fields) < 2:
            continue
        try:
            x_value, y_value = float(fields[0]), float(fields[1])
        except ValueError:
            continue
        if math.isfinite(x_value) and math.isfinite(y_value):
            x_values.append(x_value)
            y_values.append(y_value)
    x = np.asarray(x_values, dtype=np.float64)
    y = np.asarray(y_values, dtype=np.float64)
    if len(x) < 100 or x.shape != y.shape or not np.all(np.diff(x) > 0):
        raise ValueError("RRUFF XY_RAW member has too few numeric rows or a non-increasing 2theta axis")
    if np.any(y < 0):
        raise ValueError("RRUFF XY_RAW member contains negative intensities")
    return x, y


def load_garnet_spectrum(sample_id: str, archive_root: str | Path | None = None) -> GarnetSpectrum:
    """Load a curated XY_RAW profile without parsing header metadata or cells."""
    sample = sample_profile(sample_id)
    root = find_archive_root(archive_root)
    payload = _verified_member(root, "XY_RAW.zip", sample.raw_archive_member, sample.raw_member_sha256)
    x, y = parse_xy_raw_numeric_rows(payload)
    return GarnetSpectrum(
        sample_id=sample.sample_id,
        two_theta=x,
        intensity=y,
        wavelength_angstrom=WAVELENGTH_ANGSTROM,
        source=f"RRUFF official local XY_RAW.zip member {sample.raw_archive_member}",
    )


def _parse_refinement_value(text: str, patterns: tuple[str, ...]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            try:
                value = float(match.group(1))
            except ValueError:
                continue
            if math.isfinite(value):
                return value
    return None


def load_posthoc_reference(sample_id: str, archive_root: str | Path | None = None) -> PosthocReference:
    """Read same-sample refinement results for evaluation after all fitting."""
    sample = sample_profile(sample_id)
    root = find_archive_root(archive_root)
    payload = _verified_member(
        root, "Refinement_Output_Data.zip", sample.refinement_output_member, sample.refinement_output_sha256
    )
    text = payload.decode("utf-8-sig", errors="replace")
    a_value = _parse_refinement_value(
        text,
        (
            r"^\s*(?:a|cell\s+length\s+a)\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)",
            r"^\s*a\s+([0-9]+(?:\.[0-9]+)?)\s*(?:\+/-|±)",
        ),
    )
    if a_value is None or not 1.0 < a_value < 30.0:
        raise ValueError(f"could not extract a posthoc refined cubic cell parameter for {sample.sample_id}")
    esd = _parse_refinement_value(text, (r"^\s*(?:esd\s*\(?a\)?|a\s+esd|siga)\s*[:=]\s*([0-9.eE+-]+)",))
    refinement_rmse = _parse_refinement_value(text, (r"^\s*(?:rmse|rms\s+error)\s*[:=]\s*([0-9.eE+-]+)",))
    wavelengths: list[float] = []
    for match in re.finditer(r"(?i)wavelength\s*#?\s*\d\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)", text):
        value = float(match.group(1))
        if 0.35 <= value <= 3.0:
            wavelengths.append(value)
    return PosthocReference(
        sample_id=sample.sample_id,
        a_angstrom=a_value,
        a_esd_angstrom=esd,
        refinement_rmse=refinement_rmse,
        wavelength_triplet_angstrom=tuple(wavelengths),
        source_member=sample.refinement_output_member,
        source_sha256=sample.refinement_output_sha256,
    )


def _load_grossular_cif(cif_path: str | Path):
    try:
        from pymatgen.analysis.diffraction.xrd import XRDCalculator
        from pymatgen.core import Lattice, Structure
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    except ImportError as exc:
        raise RuntimeError("Garnet physical fitting requires pymatgen; install with pip install -e '.[garnet]'") from exc
    path = Path(cif_path).resolve()
    content = path.read_bytes()
    raw_sha = hashlib.sha256(content).hexdigest().upper()
    normalized_sha = hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest().upper()
    actual_sha = raw_sha if raw_sha == COD_CIF_SHA256 else normalized_sha
    if actual_sha != COD_CIF_SHA256:
        raise ValueError(f"Grossular COD CIF SHA-256 mismatch: {actual_sha}")
    structure = Structure.from_file(path)
    composition = structure.composition.get_el_amt_dict()
    scale = composition.get("O", 0.0) / 12.0
    expected = {"Ca": 3.0, "Al": 2.0, "Si": 3.0, "O": 12.0}
    if scale <= 0 or any(abs(composition.get(element, 0.0) / scale - amount) > 0.02 for element, amount in expected.items()):
        raise ValueError(f"Grossular CIF formula mismatch: {structure.composition.reduced_formula}")
    spacegroup = SpacegroupAnalyzer(structure, symprec=1e-2).get_space_group_number()
    if spacegroup != COD_SPACE_GROUP_NUMBER:
        raise ValueError(f"Grossular CIF must be Ia-3d (230), got space group {spacegroup}")
    lengths = np.asarray(structure.lattice.abc, dtype=np.float64)
    if np.max(lengths) - np.min(lengths) > 0.02 or np.max(np.abs(np.asarray(structure.lattice.angles) - 90.0)) > 0.02:
        raise ValueError("Grossular pilot requires a cubic reference CIF")
    return structure, XRDCalculator(wavelength=WAVELENGTH_ANGSTROM), actual_sha, path


def _profile_for_a(reference_centers: np.ndarray, reference_amplitudes: np.ndarray,
                   x: np.ndarray, a0: float, a: float,
                   zero_shift: float, fwhm: float) -> np.ndarray:
    # XRDCalculator supplies the independently sourced structure factors and
    # powder multiplicities once. Cubic d-spacings then scale exactly as a/a0;
    # Lorentz-polarization is updated at each trial angle. This avoids rebuilding
    # the full symmetry/reflection table inside every optimizer evaluation.
    theta0 = np.radians(reference_centers / 2.0)
    sin_theta = np.sin(theta0) * (a0 / a)
    valid = (sin_theta > 0.0) & (sin_theta < 1.0)
    physical_centers = np.degrees(2.0 * np.arcsin(np.clip(sin_theta[valid], 0.0, 1.0)))
    centers = physical_centers + zero_shift
    theta = np.radians(physical_centers / 2.0)
    lp = (1.0 + np.cos(2.0 * theta) ** 2) / np.maximum(np.sin(theta) ** 2 * np.cos(theta), 1e-10)
    theta_reference = np.radians(reference_centers[valid] / 2.0)
    lp_reference = (1.0 + np.cos(2.0 * theta_reference) ** 2) / np.maximum(
        np.sin(theta_reference) ** 2 * np.cos(theta_reference), 1e-10
    )
    amplitudes = reference_amplitudes[valid] * lp / lp_reference
    sigma = fwhm / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    profile = np.zeros_like(x, dtype=np.float64)
    for center, amplitude in zip(centers, amplitudes, strict=True):
        if center < x[0] - 5 * sigma or center > x[-1] + 5 * sigma or amplitude <= 0:
            continue
        lo = max(0, int(np.searchsorted(x, center - 5 * sigma)))
        hi = min(len(x), int(np.searchsorted(x, center + 5 * sigma, side="right")))
        if lo < hi:
            z = (x[lo:hi] - center) / sigma
            profile[lo:hi] += amplitude * np.exp(-0.5 * z * z)
    maximum = float(profile.max(initial=0.0))
    return profile / maximum if maximum > 0 else profile


def fit_grossular_spectrum(spectrum: GarnetSpectrum, cif_path: str | Path) -> GarnetFit:
    """Compare fixed independent CIF cell against physical multi-start fits."""
    structure, calculator, cif_sha, path = _load_grossular_cif(cif_path)
    x = np.asarray(spectrum.two_theta, dtype=np.float64)
    y = np.asarray(spectrum.intensity, dtype=np.float64)
    if x.ndim != 1 or y.shape != x.shape or len(x) < 100 or not np.all(np.diff(x) > 0):
        raise ValueError("fit input must be a valid two-column increasing real spectrum")
    if abs(spectrum.wavelength_angstrom - WAVELENGTH_ANGSTROM) > 1e-7:
        raise ValueError("pilot wavelength differs from the fixed independent RRUFF protocol")
    y_norm = y / float(np.max(y))
    if np.max(y_norm) <= 0:
        raise ValueError("input spectrum has no positive intensity")
    a0 = float(structure.lattice.a)
    reflection_pattern = calculator.get_pattern(
        structure,
        two_theta_range=(max(0.1, float(x[0]) - 8.0), min(178.0, float(x[-1]) + 8.0)),
        scaled=True,
    )
    reference_centers = np.asarray(reflection_pattern.x, dtype=np.float64)
    reference_amplitudes = np.asarray(reflection_pattern.y, dtype=np.float64)
    lower_a, upper_a = a0 * (1.0 - LATTICE_TOLERANCE), a0 * (1.0 + LATTICE_TOLERANCE)
    xnorm = (x - float(np.mean(x))) / max(float(np.ptp(x)) / 2, 1.0)
    # Frozen peak-emphasis weights: strong measured features guide the fit while
    # retaining every input point and reporting the unweighted RMSE separately.
    weights = 1.0 + 2.0 * np.sqrt(np.clip(y_norm, 0.0, 1.0))

    def model(a: float, zero: float, width: float, scale: float, bg: float, slope: float) -> np.ndarray:
        physical = _profile_for_a(reference_centers, reference_amplitudes, x, a0, a, zero, width)
        return scale * physical + bg + slope * xnorm

    def solve(label: str, start_a: float | None) -> FitAttempt:
        if start_a is None:
            x0 = np.asarray([0.0, 0.16, 0.9, 0.05, 0.0], dtype=np.float64)
            lower = np.asarray([-0.30, 0.04, 0.0, -0.20, -0.20])
            upper = np.asarray([0.30, 0.60, 3.0, 0.60, 0.20])

            def render(parameters: np.ndarray) -> np.ndarray:
                zero, width, scale, bg, slope = parameters
                return model(a0, zero, width, scale, bg, slope)

            def residual(parameters: np.ndarray) -> np.ndarray:
                return (render(parameters) - y_norm) * weights

            solution = least_squares(residual, x0, bounds=(lower, upper), max_nfev=120,
                                     ftol=1e-7, xtol=1e-7, gtol=1e-7)
            zero, width, scale, bg, slope = solution.x
            a_fit = a0
            initial_a = a0
            at_bound = False
        else:
            x0 = np.asarray([start_a, 0.0, 0.16, 0.9, 0.05, 0.0], dtype=np.float64)
            lower = np.asarray([lower_a, -0.30, 0.04, 0.0, -0.20, -0.20])
            upper = np.asarray([upper_a, 0.30, 0.60, 3.0, 0.60, 0.20])

            def render(parameters: np.ndarray) -> np.ndarray:
                a, zero, width, scale, bg, slope = parameters
                return model(a, zero, width, scale, bg, slope)

            def residual(parameters: np.ndarray) -> np.ndarray:
                return (render(parameters) - y_norm) * weights

            solution = least_squares(residual, x0, bounds=(lower, upper), max_nfev=120,
                                     ftol=1e-7, xtol=1e-7, gtol=1e-7)
            a_fit, zero, width, scale, bg, slope = solution.x
            initial_a = start_a
            bound_eps = 1e-5 * (upper_a - lower_a)
            at_bound = bool(a_fit - lower_a < bound_eps or upper_a - a_fit < bound_eps)
        predicted = render(solution.x)
        error = y_norm - predicted
        return FitAttempt(
            label=label,
            initial_a_angstrom=float(initial_a),
            a_angstrom=float(a_fit),
            zero_shift_deg=float(zero),
            fwhm_deg=float(width),
            scale=float(scale),
            background=float(bg),
            background_slope=float(slope),
            rmse=float(np.sqrt(np.mean(error**2))),
            weighted_rmse=float(np.sqrt(np.mean((error * weights) ** 2))),
            success=bool(solution.success),
            solver_status=int(solution.status),
            solver_message=str(solution.message),
            iterations=int(solution.nfev),
            at_lattice_bound=at_bound,
            predicted=predicted,
            residual=error,
        )

    fixed = solve("independent_CIF_a_fixed_nuisance_fit", None)
    starts = tuple(solve(f"multistart_{offset:+.0%}", a0 * (1.0 + offset)) for offset in START_OFFSETS)
    formula = structure.composition.reduced_formula
    return GarnetFit(
        sample_id=spectrum.sample_id,
        cif_path=str(path),
        cif_sha256=cif_sha,
        cif_formula=formula,
        cif_space_group=COD_SPACE_GROUP,
        cif_cell_a_angstrom=a0,
        initial_cell_fit=fixed,
        multi_start_attempts=starts,
    )


def _peak_match_metrics(spectrum: GarnetSpectrum, fit: GarnetFit) -> tuple[float, int, int]:
    observed = np.asarray(spectrum.intensity, dtype=np.float64)
    observed = observed / float(np.max(observed))
    predicted = fit.best.predicted
    obs_peaks, _ = find_peaks(observed, prominence=STRONG_PEAK_PROMINENCE, distance=8)
    mod_peaks, _ = find_peaks(predicted, prominence=STRONG_PEAK_PROMINENCE, distance=8)
    obs_angles = spectrum.two_theta[obs_peaks]
    mod_angles = spectrum.two_theta[mod_peaks]
    if len(obs_angles) == 0:
        return 0.0, 0, 0
    matches = sum(
        1 for peak in obs_angles
        if len(mod_angles) and float(np.min(np.abs(mod_angles - peak))) <= STRONG_PEAK_MATCH_TOLERANCE_DEG
    )
    return matches / len(obs_angles), len(obs_angles), matches


def evaluate_posthoc(fit: GarnetFit, reference: PosthocReference,
                     spectrum: GarnetSpectrum) -> PilotEvaluation:
    """Apply the predeclared physical readiness checks after fitting only."""
    if fit.sample_id != reference.sample_id or fit.sample_id != spectrum.sample_id:
        raise ValueError("fit, posthoc reference, and input spectrum sample IDs must match")
    spread = max(attempt.a_angstrom for attempt in fit.multi_start_attempts) - min(
        attempt.a_angstrom for attempt in fit.multi_start_attempts
    )
    best = fit.best
    peak_fraction, n_peaks, n_matched = _peak_match_metrics(spectrum, fit)
    err = best.a_angstrom - reference.a_angstrom
    criteria = {
        "all_multistarts_converged": all(attempt.success for attempt in fit.multi_start_attempts),
        "multistarts_agree_within_0.02A": spread <= MAX_MULTISTART_SPREAD_ANGSTROM,
        "best_not_at_lattice_bound": not best.at_lattice_bound,
        "normalized_profile_rmse_at_most_0.05": best.rmse <= MAX_FIT_RMSE,
        "posthoc_a_error_at_most_1_percent": abs(err / reference.a_angstrom) <= MAX_POSTHOC_A_ERROR_FRACTION,
        "at_least_80_percent_strong_peaks_matched": peak_fraction >= MIN_STRONG_PEAK_MATCH_FRACTION,
    }
    return PilotEvaluation(
        sample_id=fit.sample_id,
        fitted_a_angstrom=best.a_angstrom,
        reference_a_angstrom=reference.a_angstrom,
        a_error_angstrom=err,
        a_error_percent=100.0 * err / reference.a_angstrom,
        peak_match_fraction=peak_fraction,
        observed_strong_peak_count=n_peaks,
        matched_strong_peak_count=n_matched,
        multi_start_spread_angstrom=spread,
        criteria=criteria,
        status="PHYSICS_MODEL_READY" if all(criteria.values()) else "PHYSICS_MODEL_NOT_READY",
    )


def run_garnet_pilot(sample_id: str, archive_root: str | Path, cif_path: str | Path,
                     output_root: str | Path) -> tuple[GarnetFit, PosthocReference, PilotEvaluation, Path]:
    """Fit first; only then load and evaluate against the held reference."""
    sample = sample_profile(sample_id)
    root = find_archive_root(archive_root)
    spectrum = load_garnet_spectrum(sample.sample_id, root)
    fit = fit_grossular_spectrum(spectrum, cif_path)
    # Explicit phase boundary: no same-sample refinement member is opened above.
    reference = load_posthoc_reference(sample.sample_id, root)
    evaluation = evaluate_posthoc(fit, reference, spectrum)
    output = Path(output_root).expanduser().resolve() / sample.sample_id.replace("-", "_")
    output.mkdir(parents=True, exist_ok=True)
    _save_diagnostics(output, sample, spectrum, fit, reference, evaluation)
    return fit, reference, evaluation, output


def run_garnet_development_suite(archive_root: str | Path, cif_path: str | Path,
                                 output_root: str | Path) -> dict[str, tuple[GarnetFit, PosthocReference, PilotEvaluation, Path]]:
    """Fit the complete curated development set before opening any references."""
    root = find_archive_root(archive_root)
    spectra = {sample.sample_id: load_garnet_spectrum(sample.sample_id, root) for sample in _SAMPLES}
    fits = {sample_id: fit_grossular_spectrum(spectrum, cif_path)
            for sample_id, spectrum in spectra.items()}
    # All candidate physical fits above finish before this posthoc-only phase.
    references = {sample_id: load_posthoc_reference(sample_id, root) for sample_id in spectra}
    evaluations = {sample_id: evaluate_posthoc(fits[sample_id], references[sample_id], spectra[sample_id])
                   for sample_id in spectra}
    output: dict[str, tuple[GarnetFit, PosthocReference, PilotEvaluation, Path]] = {}
    for sample in _SAMPLES:
        sample_id = sample.sample_id
        folder = Path(output_root).expanduser().resolve() / sample_id.replace("-", "_")
        folder.mkdir(parents=True, exist_ok=True)
        _save_diagnostics(folder, sample, spectra[sample_id], fits[sample_id],
                          references[sample_id], evaluations[sample_id])
        output[sample_id] = (fits[sample_id], references[sample_id], evaluations[sample_id], folder)
    return output


def _save_diagnostics(output: Path, sample: GarnetSampleProfile, spectrum: GarnetSpectrum,
                      fit: GarnetFit, reference: PosthocReference, evaluation: PilotEvaluation) -> None:
    # Full measured data and generated profiles are deliberately local-only.
    import csv

    with (output / "profile_fit_residual.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["two_theta_deg", "measured_intensity", "normalized_measured", "fixed_CIF_a_fit",
                         "optimized_fit", "optimized_residual"])
        y_norm = spectrum.intensity / float(np.max(spectrum.intensity))
        for values in zip(spectrum.two_theta, spectrum.intensity, y_norm, fit.initial_cell_fit.predicted,
                          fit.best.predicted, fit.best.residual, strict=True):
            writer.writerow([float(value) for value in values])
    payload = {
        "material_profile": asdict(sample),
        "wavelength_angstrom": spectrum.wavelength_angstrom,
        "wavelength_source": WAVELENGTH_SOURCE,
        "spectrum_quality": {
            "raw_archive_member": sample.raw_archive_member,
            "raw_member_sha256": sample.raw_member_sha256,
            "raw_member_sha256_verified": True,
            "numeric_row_count": int(len(spectrum.two_theta)),
            "two_theta_range_deg": [float(spectrum.two_theta[0]), float(spectrum.two_theta[-1])],
            "axis_strictly_increasing": bool(np.all(np.diff(spectrum.two_theta) > 0)),
            "intensities_nonnegative": bool(np.all(spectrum.intensity >= 0)),
            "quality_note": "Only the verified numeric XY_RAW trace is fitted; header metadata is discarded.",
        },
        "structure_template": {
            "cod_record": COD_RECORD,
            "formula": COD_FORMULA,
            "space_group": COD_SPACE_GROUP,
            "space_group_number": COD_SPACE_GROUP_NUMBER,
            "cif_path": fit.cif_path,
            "cif_sha256": fit.cif_sha256,
            "independence": "COD literature structure; not the RRUFF target specimen and not selected by target-cell distance",
        },
        "fit": fit.summary(),
        "posthoc_reference": asdict(reference),
        "evaluation": asdict(evaluation),
        "readiness_thresholds": {
            "lattice_search_fraction": LATTICE_TOLERANCE,
            "max_profile_rmse": MAX_FIT_RMSE,
            "max_posthoc_a_error_fraction": MAX_POSTHOC_A_ERROR_FRACTION,
            "max_multistart_spread_angstrom": MAX_MULTISTART_SPREAD_ANGSTROM,
            "strong_peak_prominence": STRONG_PEAK_PROMINENCE,
            "strong_peak_match_tolerance_deg": STRONG_PEAK_MATCH_TOLERANCE_DEG,
            "min_strong_peak_match_fraction": MIN_STRONG_PEAK_MATCH_FRACTION,
        },
    }
    (output / "diagnostic.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("saving the local Garnet diagnostic plot requires matplotlib") from exc
    y_norm = spectrum.intensity / float(np.max(spectrum.intensity))
    fig, (ax, resid) = plt.subplots(2, 1, figsize=(12, 7), sharex=True,
                                    gridspec_kw={"height_ratios": [3, 1]})
    ax.plot(spectrum.two_theta, y_norm, color="#222222", lw=0.8, label="RRUFF measured profile")
    ax.plot(spectrum.two_theta, fit.initial_cell_fit.predicted, color="#e09f3e", lw=1.0,
            label=f"COD a0 fixed ({fit.cif_cell_a_angstrom:.4f} Å; nuisance fit)")
    ax.plot(spectrum.two_theta, fit.best.predicted, color="#d1495b", lw=1.0,
            label=f"physical multi-start fit (a={fit.best.a_angstrom:.4f} Å)")
    ax.set_ylabel("Normalized intensity")
    ax.legend(loc="upper right")
    resid.axhline(0.0, color="gray", lw=0.7)
    resid.plot(spectrum.two_theta, fit.best.residual, color="#00798c", lw=0.8)
    resid.set_xlabel("2θ (degrees)")
    resid.set_ylabel("Residual")
    fig.suptitle(f"{sample.sample_id} Grossular — {evaluation.status}")
    fig.tight_layout()
    fig.savefig(output / "profile_fit_residual.png", dpi=160)
    plt.close(fig)
