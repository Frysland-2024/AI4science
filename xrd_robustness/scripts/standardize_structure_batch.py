#!/usr/bin/env python3
"""Standardize a JSON batch using a known-compatible pymatgen environment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--symprec", type=float, default=1e-3)
    parser.add_argument("--angle-tolerance", type=float, default=5.0)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = [payload]
    output = []
    for item in payload:
        material_id = str(item["material_id"])
        try:
            original = Structure.from_dict(item["original_structure"])
            if not original.is_ordered:
                raise ValueError("disordered or partially occupied structure")
            analyzer = SpacegroupAnalyzer(
                original,
                symprec=args.symprec,
                angle_tolerance=args.angle_tolerance,
            )
            standardized = analyzer.get_conventional_standard_structure()
            recomputed = int(
                SpacegroupAnalyzer(
                    standardized,
                    symprec=args.symprec,
                    angle_tolerance=args.angle_tolerance,
                ).get_space_group_number()
            )
            output.append(
                {
                    "material_id": material_id,
                    "standardized_structure": standardized.as_dict(),
                    "space_group_recomputed": recomputed,
                }
            )
        except Exception as error:
            output.append(
                {
                    "material_id": material_id,
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
            )
    Path(args.output).write_text(
        json.dumps(output, separators=(",", ":")), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
