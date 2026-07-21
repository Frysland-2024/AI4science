#!/usr/bin/env python3
"""Export the active V7 candidate parameter profiles to a reviewable CSV."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.physics import parameter_registry_rows


FIELDS = (
    "profile",
    "role",
    "severity_level",
    "background_type",
    "background_order",
    "background_variation",
    "background_anchor_count",
    "background_gp_length_scale",
    "background_floor_fraction",
    "noise_model",
    "noise_stage",
    "poisson_count_scale",
    "electronic_noise_std_ratio",
    "electronic_noise_std_counts",
    "parameter",
    "unit",
    "distribution",
    "min_value",
    "max_value",
    "apply_probability",
    "literature_source",
    "code_source",
    "physics_basis",
    "status",
    "run_seed",
    "source_config",
    "config_sha256",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "configs" / "simulation.v7.candidate.json"),
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "reports" / "v7_active_parameter_table.csv"),
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config_sha256 = hashlib.sha256(config_path.read_bytes()).hexdigest().upper()
    try:
        source_config = str(config_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        source_config = str(config_path)
    rows = parameter_registry_rows(
        config,
        source_config=source_config,
        config_sha256=config_sha256,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(
        json.dumps(
            {
                "output": str(output_path),
                "rows": len(rows),
                "profiles": len(config["profiles"]),
                "config_sha256": config_sha256,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
