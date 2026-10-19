"""P0 BaTiO3 structure, axis, Bragg and clean-profile parity audit."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch
from pymatgen.analysis.diffraction.xrd import XRDCalculator
from pymatgen.core import Lattice, Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / "xrd_inversion" / "src"),
    str(ROOT / "xrd_robustness" / "src"),
    str(ROOT / "xrd_forward_loss" / "src"),
]
from xrd_inversion.gpu_forward import CachedTetragonalGPUForward  # noqa: E402
from xrd_robustness.physics import PhysicsParameters  # noqa: E402
from xrd_robustness.simulator import (  # noqa: E402
    SimulationGrid,
    ideal_peak_table,
    simulate_from_peak_table,
)


def q_structure(reference: Structure, q: tuple[float, float], config: dict) -> Structure:
    parameterization = config["parameterization"]
    u0 = (2 * math.log(reference.lattice.a) + math.log(reference.lattice.c)) / 3
    v0 = math.log(reference.lattice.c / reference.lattice.a)
    u = u0 + q[0] * parameterization["du_half_range"]
    v = v0 + q[1] * parameterization["dv_half_range"]
    a, c = math.exp(u - v / 3), math.exp(u + 2 * v / 3)
    return Structure(
        lattice=Lattice.tetragonal(a, c),
        species=[site.species for site in reference],
        coords=reference.frac_coords,
        coords_are_cartesian=False,
        site_properties=reference.site_properties,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"output directory already exists: {args.output}")
    args.output.mkdir(parents=True)

    cif_path = ROOT / "xrd_forward_loss/data/public_cif/BaTiO3_COD_9014273_P4mm.cif"
    cfg_path = ROOT / "xrd_inversion/configs/week1_formal_gate.json"
    config = json.loads(cfg_path.read_text(encoding="utf-8"))
    structure = Structure.from_file(cif_path)
    grid_config = config["grid"]
    grid = SimulationGrid(
        two_theta_min=float(grid_config["two_theta_min"]),
        two_theta_max=float(grid_config["two_theta_max"]),
        step=float(grid_config["step"]),
        wavelength=float(grid_config["wavelength_angstrom"]),
    )
    padding = float(grid_config["peak_calculation_padding_deg"])
    padded_grid = SimulationGrid(
        two_theta_min=grid.two_theta_min - padding,
        two_theta_max=grid.two_theta_max + padding,
        step=grid.step,
        wavelength=grid.wavelength,
    )

    symmetry_analyzer = SpacegroupAnalyzer(structure, symprec=0.01)
    symmetry = symmetry_analyzer.get_space_group_symbol()
    symmetry_number = symmetry_analyzer.get_space_group_number()
    nominal_pattern = XRDCalculator(wavelength=grid.wavelength).get_pattern(
        structure, two_theta_range=(grid.two_theta_min, grid.two_theta_max)
    )
    bragg_errors = []
    for two_theta, families in zip(nominal_pattern.x, nominal_pattern.hkls, strict=True):
        for family in families:
            d_hkl = structure.lattice.d_hkl(family["hkl"])
            bragg = math.degrees(2 * math.asin(grid.wavelength / (2 * d_hkl)))
            bragg_errors.append(abs(float(two_theta) - bragg))

    device = "cuda"
    forward = CachedTetragonalGPUForward(
        structure,
        grid_config=grid_config,
        parameter_config=config["parameterization"],
        device=device,
        dtype=torch.float64,
    )
    clean_params = PhysicsParameters(
        delta_2theta_deg=0.0,
        fwhm_deg=0.08,
        background_to_peak_ratio=0.0,
        noise_std_ratio=0.0,
        background_type="flat",
        severity_level=0,
        zero_shift_active=False,
        broadening_active=False,
        background_active=False,
        noise_active=False,
        preferred_orientation_active=False,
    )
    probes = [
        (0.0, 0.0),
        (0.6, 0.0),
        (-0.6, 0.0),
        (0.0, 0.6),
        (0.0, -0.6),
        (0.6, -0.6),
        (-0.6, 0.6),
    ]
    rows = []
    for q in probes:
        q_tensor = torch.tensor([q[0], q[1], 0.0, -1.0], device=device, dtype=torch.float64)
        with torch.no_grad():
            torch_profile = forward.render(q_tensor, compatibility=True).cpu().numpy().astype(np.float64)
        varied = q_structure(structure, q, config)
        peaks = ideal_peak_table(varied, padded_grid)
        v9_profile = simulate_from_peak_table(
            peaks.positions,
            peaks.intensities,
            clean_params,
            rng_seed=0,
            grid=grid,
            normalize=True,
            reflection_table=peaks,
        ).astype(np.float64)
        delta = torch_profile - v9_profile
        torch_l2 = float(np.linalg.norm(torch_profile))
        v9_l2 = float(np.linalg.norm(v9_profile))
        rows.append(
            {
                "q": list(q),
                "max_abs_error": float(np.max(np.abs(delta))),
                "rmse": float(np.sqrt(np.mean(delta**2))),
                "relative_l2_error": float(np.linalg.norm(delta) / max(v9_l2, 1e-15)),
                "torch_peak_index": int(np.argmax(torch_profile)),
                "v9_peak_index": int(np.argmax(v9_profile)),
                "torch_area": float(np.trapezoid(torch_profile, grid.values)),
                "v9_area": float(np.trapezoid(v9_profile, grid.values)),
                "peak_count": int(len(peaks.positions)),
            }
        )
    max_error = max(row["max_abs_error"] for row in rows)
    max_rmse = max(row["rmse"] for row in rows)
    report = {
        "stage": "P0",
        "gate_thresholds": {"max_abs_error": 2e-6, "rmse": 2e-7, "bragg_error_deg": 1.1e-5},
        "structure": {
            "cif": str(cif_path.relative_to(ROOT)),
            "cif_sha256": hashlib.sha256(cif_path.read_bytes()).hexdigest(),
            "formula": structure.composition.reduced_formula,
            "sites": len(structure),
            "a_angstrom": float(structure.lattice.a),
            "b_angstrom": float(structure.lattice.b),
            "c_angstrom": float(structure.lattice.c),
            "space_group": symmetry,
            "space_group_number": symmetry_number,
            "pymatgen_nominal_peak_count": len(nominal_pattern.x),
            "bragg_law_max_abs_error_deg": max(bragg_errors),
        },
        "axis": {
            "two_theta_min_deg": grid.two_theta_min,
            "two_theta_max_deg": grid.two_theta_max,
            "step_deg": grid.step,
            "point_count": len(grid.values),
            "wavelength_angstrom": grid.wavelength,
            "wavelength_name": grid_config["wavelength_name"],
            "peak_calculation_padding_deg": padding,
        },
        "torch_forward": forward.provenance().__dict__,
        "pymatgen_version": importlib.metadata.version("pymatgen"),
        "clean_profile_parity": {
            "reference": "Pymatgen XRDCalculator peak table + independent V9 Gaussian renderer",
            "max_abs_error": max_error,
            "max_probe_rmse": max_rmse,
            "probes": rows,
            "passed": max_error <= 2e-6 and max_rmse <= 2e-7,
        },
    }
    report["passed"] = bool(
        structure.composition.reduced_formula == "BaTiO3"
        and symmetry_number == 99
        and abs(structure.lattice.a - 3.986) < 0.002
        and abs(structure.lattice.c - 4.026) < 0.002
        and max(bragg_errors) <= 1.1e-5
        and len(grid.values) == 3501
        and report["clean_profile_parity"]["passed"]
    )
    (args.output / "p0_reference.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"passed": report["passed"], "p0": report}, indent=2))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
