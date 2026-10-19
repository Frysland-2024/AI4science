"""Reproducible synthetic-only command line demonstration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .candidates import available_candidates, candidate_by_id
from .classifier_adapter import load_optional_prior
from .crystal import render
from .router import route


def run_demo(candidate_id: str = "batio3_p4mm_cod9014273", seed: int = 271828) -> dict:
    candidate = candidate_by_id(candidate_id)
    crystal = candidate.load()
    wavelength = 1.5406
    axis = np.arange(10.0, 80.0001, 0.04)
    true_a = crystal.a * 1.004
    true_c = (crystal.c * 0.997) if crystal.crystal_system == "tetragonal" else true_a
    clean = render(crystal, axis, wavelength, a=true_a, c=true_c, zero_shift=0.025, fwhm=0.16)
    rng = np.random.default_rng(seed)
    simulated = np.clip(0.025 + 0.96 * clean + rng.normal(0.0, 0.003, clean.size), 0.0, None)
    prior_status = load_optional_prior()
    routed = route(axis, simulated, wavelength)
    return {
        "data_label": "SIMULATED synthetic profile; generated from the selected fixed CIF",
        "seed": seed,
        "wavelength_angstrom": wavelength,
        "candidate_set": [c.id for c in available_candidates()],
        "source_candidate": candidate.id,
        "true_parameters_for_demo_only": {"a_angstrom": true_a, "c_angstrom": true_c, "zero_shift_deg": 0.025},
        "classifier": {"available": prior_status.available, "message": prior_status.message},
        "evaluated_candidate_ids": list(routed.evaluated_candidate_ids),
        "ranking": [fit.summary() for fit in routed.results[:3]],
        "warning": routed.warning,
        "limitations": ["synthetic self-consistency only", "not real measured data", "not phase-ID accuracy evidence",
                        "restricted three-CIF single-phase hypotheses", "approximate neutral-atom scattering factors"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a deterministic synthetic PXRD phase-router demo")
    parser.add_argument("--candidate", default="batio3_p4mm_cod9014273", choices=[c.id for c in available_candidates()])
    parser.add_argument("--seed", type=int, default=271828)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = run_demo(args.candidate, args.seed)
    rendered = json.dumps(result, indent=2)
    if args.output:
        target = args.output.resolve()
        try:
            target.relative_to(Path(__file__).resolve().parents[1])
        except ValueError as exc:
            raise SystemExit("demo output must stay inside this worktree under E:\\AI4science\\_local") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
