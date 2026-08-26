#!/usr/bin/env python3
"""Compute ideal peak tables in a known-compatible pymatgen environment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pymatgen.core import Structure

from xrd_robustness.simulator import SimulationGrid, ideal_peak_table


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows = []
    for item in payload:
        try:
            structure = Structure.from_dict(item["standardized_structure"])
            table = ideal_peak_table(structure, SimulationGrid())
            if table.positions.size == 0:
                raise ValueError("empty peak table")
            rows.append(
                {
                    "material_id": item["material_id"],
                    "positions": table.positions.tolist(),
                    "intensities": table.intensities.tolist(),
                    "hkls": table.hkls.tolist(),
                    "multiplicities": table.multiplicities.tolist(),
                    "reciprocal_vectors": table.reciprocal_vectors.tolist(),
                    "reflection_peak_indices": table.reflection_peak_indices.tolist(),
                }
            )
        except Exception as error:
            rows.append(
                {
                    "material_id": item["material_id"],
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
            )
    Path(args.output).write_text(
        json.dumps(rows, separators=(",", ":")), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
