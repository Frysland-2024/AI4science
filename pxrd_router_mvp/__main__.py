"""Headless measured-spectrum routing CLI."""

from __future__ import annotations

import argparse
import json

from .classifier_adapter import load_optional_prior
from .io import read_spectrum_file
from .router import route


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Route a spectrum against the bundled fixed-CIF candidate set")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="CSV, TSV, XY, or whitespace text spectrum")
    source.add_argument("--rruff-id", choices=("R050045", "R060745"), help="opt-in local adaptation_pool RRUFF sample")
    parser.add_argument("--rruff-root", help="local RRUFF-371 root; required with --rruff-id")
    parser.add_argument("--wavelength", type=float, help="X-ray wavelength in Angstrom; required with --input")
    parser.add_argument("--x-column", default="0", help="zero-based index or CSV header for 2theta")
    parser.add_argument("--y-column", default="1", help="zero-based index or CSV header for intensity")
    parser.add_argument("--range", nargs=2, type=float, metavar=("MIN", "MAX"))
    parser.add_argument("--use-classifier-prior", action="store_true", help="apply available frozen seven-system output as a weak optional ranking prior")
    parser.add_argument("--output", help="optional JSON output path")
    args = parser.parse_args(argv)
    if args.rruff_id:
        if not args.rruff_root:
            parser.error("--rruff-root is required with --rruff-id")
        from .rruff_local import route_local_example
        payload = route_local_example(args.rruff_root, args.rruff_id,
                                      use_classifier_prior=args.use_classifier_prior)
        text = json.dumps(payload, indent=2)
        if args.output:
            from pathlib import Path
            target = Path(args.output).resolve()
            try:
                target.relative_to(Path(__file__).resolve().parents[1])
            except ValueError as exc:
                raise SystemExit("output must stay inside this worktree under E:\\AI4science\\_local") from exc
            target.write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    if args.wavelength is None:
        parser.error("--wavelength is required with --input")
    def column(value):
        try:
            return int(value)
        except ValueError:
            return value
    spectrum = read_spectrum_file(args.input, wavelength_angstrom=args.wavelength,
                                  x_column=column(args.x_column), y_column=column(args.y_column),
                                  axis_range=tuple(args.range) if args.range else None)
    status = load_optional_prior(two_theta=spectrum.two_theta, intensity=spectrum.intensity,
                                 wavelength_angstrom=spectrum.wavelength_angstrom)
    result = route(spectrum.two_theta, spectrum.intensity, spectrum.wavelength_angstrom,
                   crystal_system_prior=status.prior if args.use_classifier_prior else None)
    payload = {
        "input_label": spectrum.source_label,
        "input_wavelength_angstrom": spectrum.wavelength_angstrom,
        "classifier": {"available": status.available, "message": status.message},
        "evaluated_candidate_ids": list(result.evaluated_candidate_ids),
        "ranking": [fit.summary() for fit in result.results[:3]],
        "warning": result.warning,
        "interpretation": "Candidate-limited single-phase matching and fixed-prototype lattice fitting; inspect before use.",
        "real_spectrum_accuracy_claim": False,
    }
    text = json.dumps(payload, indent=2)
    if args.output:
        from pathlib import Path
        target = Path(args.output).resolve()
        try:
            target.relative_to(Path(__file__).resolve().parents[1])
        except ValueError as exc:
            raise SystemExit("output must stay inside this worktree under E:\\AI4science\\_local") from exc
        target.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
