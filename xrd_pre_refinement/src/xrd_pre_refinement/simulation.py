"""Adapters to the repository's existing CIF-to-PXRD simulator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class SimulatedPattern:
    two_theta_deg: np.ndarray
    intensity: np.ndarray
    structure: Any
    space_group_symbol: str
    space_group_number: int


def simulate_cif(
    cif_path: str | Path,
    instrument: dict[str, Any],
    measurement: dict[str, float],
    *,
    seed: int,
    robustness_source: str | Path | None = None,
) -> SimulatedPattern:
    """Load a CIF, verify its symmetry, then render it with the shared PXRD code.

    ``robustness_source`` is the repository ``xrd_robustness/src`` directory.
    Imports are lazy so registry and schema use does not require pymatgen.
    """
    try:
        from pymatgen.core import Structure
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("install xrd-pre-refinement[science] to run the CIF demo") from exc

    if robustness_source is not None:
        import sys

        source = str(Path(robustness_source).resolve())
        if source not in sys.path:
            sys.path.insert(0, source)
    try:
        from xrd_robustness.physics import PhysicsParameters
        from xrd_robustness.simulator import (
            SimulationGrid,
            ideal_peak_table,
            simulate_from_peak_table,
        )
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "could not import the repository xrd_robustness simulator; pass its src directory"
        ) from exc

    structure = Structure.from_file(str(cif_path))
    analyzer = SpacegroupAnalyzer(structure, symprec=0.01, angle_tolerance=5)
    symbol = analyzer.get_space_group_symbol()
    number = int(analyzer.get_space_group_number())
    expected = instrument.get("_expected_space_group")
    if expected and (symbol != expected["symbol"] or number != int(expected["number"])):
        raise ValueError(
            f"CIF symmetry mismatch: expected {expected['symbol']} ({expected['number']}), "
            f"found {symbol} ({number})"
        )

    grid = SimulationGrid(
        two_theta_min=float(instrument["two_theta_min_deg"]),
        two_theta_max=float(instrument["two_theta_max_deg"]),
        step=float(instrument["step_deg"]),
        wavelength=float(instrument["wavelength_angstrom"]),
    )
    # ``ideal_peak_table`` uses the same explicit wavelength and supplies the
    # reflection metadata consumed by the existing renderer.
    peak_table = ideal_peak_table(structure, grid)
    if peak_table.positions.size == 0 or not np.isfinite(peak_table.intensities).all():
        raise ValueError(f"CIF produced no usable Bragg peaks in configured range: {cif_path}")
    params = PhysicsParameters(
        delta_2theta_deg=float(measurement["delta_2theta_deg"]),
        fwhm_deg=float(measurement["fwhm_deg"]),
        background_to_peak_ratio=float(measurement["background_to_peak_ratio"]),
        noise_std_ratio=float(measurement["noise_std_ratio"]),
        background_type="polynomial",
        severity_level=0,
        zero_shift_active=True,
        broadening_active=True,
        background_active=True,
        noise_active=True,
    )
    intensity = simulate_from_peak_table(
        peak_table.positions,
        peak_table.intensities,
        params,
        rng_seed=int(seed),
        grid=grid,
        reflection_table=peak_table,
    )
    intensity = np.asarray(intensity, dtype=np.float64)
    axis = grid.values
    if intensity.shape != axis.shape or not np.isfinite(intensity).all():
        raise RuntimeError("simulated profile failed axis/finite-value checks")
    return SimulatedPattern(axis, intensity, structure, symbol, number)
