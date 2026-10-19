"""Opt-in, read-only bridge to two RRUFF adaptation-pool examples.

RRUFF spectra and refinement records are licensed for local research here only;
this module reads the user's local tree and never copies those records.
"""

from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from .io import Spectrum, read_spectrum_file
from .classifier_adapter import load_optional_prior

ALLOWED_IDS = {"R050045", "R060745"}
SPLIT_FILE = Path("splits/rruff301_adaptation_test_split.csv")
MANIFEST_FILE = Path("manifests/rruff371_master_manifest.csv")


@dataclass(frozen=True)
class RruffLocalExample:
    rruff_id: str
    mineral: str
    ideal_chemistry: str
    crystal_system: str
    space_group: str
    spectrum: Spectrum
    wavelength_triplet: tuple[float, float, float]
    selected_wavelength_angstrom: float
    refinement_reference_wavelength_angstrom: float
    machine_error_deg: float
    refined_cell_angstrom: tuple[float, float, float]
    provenance: str
    refinement_role: str = "posthoc_reference_only; excluded from initialization and routing"


def _under(root: Path, relative: str) -> Path:
    base = root.resolve()
    path = (base / relative).resolve()
    if base not in path.parents:
        raise ValueError("RRUFF manifest path escapes the selected data root")
    return path


def _csv_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return {str(row.get("rruff_id", "")).strip(): row for row in reader}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _metadata(root: Path, rruff_id: str) -> tuple[dict[str, str], dict[str, str]]:
    if rruff_id not in ALLOWED_IDS:
        raise ValueError(f"only the adaptation examples {sorted(ALLOWED_IDS)} are enabled")
    split_rows = _csv_rows(_under(root, str(SPLIT_FILE)))
    split = split_rows.get(rruff_id)
    if split is None or split.get("split") != "adaptation_pool":
        raise ValueError(f"{rruff_id} is not an allowed adaptation_pool sample")
    manifest_rows = _csv_rows(_under(root, str(MANIFEST_FILE)))
    record = manifest_rows.get(rruff_id)
    if record is None:
        raise ValueError(f"{rruff_id} is missing from the RRUFF manifest")
    return split, record


def load_local_example(base_path: str | Path, rruff_id: str) -> RruffLocalExample:
    """Load a single permitted adaptation sample without writing to its tree."""
    root = Path(base_path).resolve()
    _, row = _metadata(root, rruff_id)
    spectrum_path = _under(root, row["spectrum_path"])
    if _sha256(spectrum_path) != row["spectrum_sha256"].upper():
        raise ValueError(f"{rruff_id} spectrum SHA-256 differs from its manifest")
    refinement_path = _under(root, row["refinement_path"])
    text = refinement_path.read_text(encoding="utf-8-sig", errors="strict")
    wave_matches = re.findall(r"Wavelength\s+#([123])\s*=\s*([0-9.]+)", text, flags=re.I)
    waves = {int(index): float(value) for index, value in wave_matches}
    if set(waves) != {1, 2, 3}:
        raise ValueError(f"{rruff_id} refinement must record wavelength entries #1, #2 and #3")
    error_match = re.search(r"MACHINE\s+ERROR:\s*([-+0-9.]+)", text, flags=re.I)
    if not error_match:
        raise ValueError(f"{rruff_id} refinement is missing the machine-error record")
    cell: dict[str, float] = {}
    for axis in "ABC":
        match = re.search(rf"\b{axis}\s*=\s*([0-9]+(?:\.[0-9]+)?)", text, flags=re.I)
        if not match:
            raise ValueError(f"{rruff_id} refinement is missing cell axis {axis}")
        cell[axis] = float(match.group(1))
    spectrum = read_spectrum_file(
        spectrum_path,
        wavelength_angstrom=waves[1],  # RRUFF DIF records source-profile Cu Kalpha as wavelength #1
        x_column="two_theta",
        y_column="intensity",
    )
    return RruffLocalExample(
        rruff_id=rruff_id,
        mineral=row["mineral_name"],
        ideal_chemistry=row["ideal_chemistry"],
        crystal_system=row["crystal_system"],
        space_group=row["space_group"],
        spectrum=spectrum,
        wavelength_triplet=(waves[1], waves[2], waves[3]),
        selected_wavelength_angstrom=waves[1],
        refinement_reference_wavelength_angstrom=waves[2],
        machine_error_deg=float(error_match.group(1)),
        refined_cell_angstrom=(cell["A"], cell["B"], cell["C"]),
        provenance=(
            f"RRUFF-371 local measured/resampled spectrum {rruff_id}; "
            "adaptation_pool; 10-80 deg at 0.02 deg; manifest SHA-256 verified"
        ),
    )


def route_local_example(base_path: str | Path, rruff_id: str, *, use_classifier_prior: bool = False) -> dict:
    """Run the regular all-candidate router and attach held posthoc comparison."""
    from .router import route

    example = load_local_example(base_path, rruff_id)
    classifier = load_optional_prior(
        two_theta=example.spectrum.two_theta, intensity=example.spectrum.intensity,
        wavelength_angstrom=example.selected_wavelength_angstrom,
    )
    result = route(example.spectrum.two_theta, example.spectrum.intensity,
                   example.selected_wavelength_angstrom,
                   crystal_system_prior=classifier.prior if use_classifier_prior else None)
    best = result.results[0]
    a_ref, b_ref, c_ref = example.refined_cell_angstrom
    fitted_c = best.c_angstrom if best.c_angstrom is not None else best.a_angstrom
    errors = {
        "a_percent": 100.0 * (best.a_angstrom - a_ref) / a_ref,
        "c_percent": 100.0 * (fitted_c - c_ref) / c_ref,
    }
    return {
        "rruff_id": example.rruff_id,
        "mineral": example.mineral,
        "ideal_chemistry": example.ideal_chemistry,
        "crystal_system": example.crystal_system,
        "space_group": example.space_group,
        "provenance": example.provenance,
        "wavelength_triplet_angstrom": list(example.wavelength_triplet),
        "selected_wavelength_angstrom": example.selected_wavelength_angstrom,
        "refinement_reference_wavelength_angstrom": example.refinement_reference_wavelength_angstrom,
        "machine_error_deg_recorded": example.machine_error_deg,
        "posthoc_refined_cell_angstrom": {"a": a_ref, "b": b_ref, "c": c_ref},
        "posthoc_reference_role": example.refinement_role,
        "best_candidate_fit": best.summary(),
        "posthoc_lattice_difference_percent": errors,
        "ranking": [fit.summary() for fit in result.results[:3]],
        "warning": result.warning,
        "real_demo_status": "real_demo_requires_better_forward",
        "real_demo_warning": (
            f"The candidate library does not contain {example.ideal_chemistry} {example.mineral}; "
            "the best listed candidate is only a profile comparison and cannot identify this sample."
        ),
        "evaluated_candidate_ids": list(result.evaluated_candidate_ids),
        "frozen_locked_test_used": False,
        "classifier": {
            "available": classifier.available,
            "message": classifier.message,
            "checkpoint": classifier.checkpoint,
            "checkpoint_sha256": classifier.checkpoint_sha256,
            "probabilities": classifier.prior,
        },
        "classifier_prior_applied": bool(use_classifier_prior and classifier.available),
        "interpretation": "Exploratory local measured-spectrum demonstration; posthoc RRUFF refinement is not independent ground truth.",
    }
