#!/usr/bin/env python3
"""Build the frozen CNRS318 zero-shot model inputs.

Reads the CNRS-318 eval manifest, maps each representative spectrum to Cu K-alpha via
Bragg's law, resamples to the fixed 10-80 deg / 0.02 deg grid (3501 points), applies
max normalization, and writes a float32 npz plus a preprocessing manifest and report.

No background subtraction, smoothing, peak detection, or sqrt/log intensity scaling is
applied; no CNRS-specific preprocessing is added.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/real.cnrs318.zero_shot.frozen.json"
EVAL_MANIFEST = ROOT / "manifests/cnrs318_eval_manifest.csv"
PARENT_MANIFEST = ROOT / "manifests/cnrs_318_parent_manifest_v2.csv"
SOURCE_ROOT = ROOT.parent / "01_literature/data_resources/opxrd_zenodo_14254270/CNRS"
OUTPUT_ROOT = ROOT / "outputs/cnrs318_zero_shot"


def parse_json_like(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return None
    return None


def numeric_sequence(value: Any) -> list[float]:
    if not isinstance(value, list):
        raise TypeError("spectrum array is not a list")
    return [float(item) for item in value]


def bragg_map(
    two_theta: list[float],
    source_wavelength: float,
    target_wavelength: float = 1.5406,
) -> tuple[list[float], list[int]]:
    """Pointwise Bragg mapping to the target wavelength.

    Returns (mapped_angles_deg, kept_source_indices).  Points whose argument
    exceeds one in magnitude are dropped, never clipped to 180 degrees.
    """
    if source_wavelength <= 0 or target_wavelength <= 0:
        raise ValueError("wavelengths must be positive")
    ratio = target_wavelength / source_wavelength
    angles: list[float] = []
    kept: list[int] = []
    for index, value in enumerate(two_theta):
        argument = ratio * math.sin(math.radians(value / 2.0))
        if -1.0 <= argument <= 1.0:
            angles.append(math.degrees(2.0 * math.asin(argument)))
            kept.append(index)
    return angles, kept


def read_spectrum(path: Path) -> tuple[list[float], list[float], float | None]:
    record = json.loads(path.read_text(encoding="utf-8"))
    two_theta = numeric_sequence(record.get("two_theta_values"))
    intensities = numeric_sequence(
        record.get("intensities", record.get("intensity_values"))
    )
    if len(two_theta) != len(intensities) or len(two_theta) < 2:
        raise ValueError(f"invalid spectrum arrays in {path.name}")
    label = parse_json_like(record.get("label"))
    wavelength: float | None = None
    if isinstance(label, dict):
        xray_info = parse_json_like(label.get("xray_info"))
        if isinstance(xray_info, dict) and xray_info.get("primary_wavelength") not in (None, ""):
            try:
                wavelength = float(xray_info["primary_wavelength"])
            except (TypeError, ValueError):
                wavelength = None
    if wavelength is None or wavelength <= 0:
        raise ValueError(f"missing source wavelength in {path.name}")
    return two_theta, intensities, wavelength


def resample(
    two_theta: list[float],
    intensities: list[float],
    source_wavelength: float,
    *,
    target_wavelength: float,
    two_theta_min: float,
    two_theta_max: float,
    step: float,
) -> np.ndarray:
    angles, kept = bragg_map(two_theta, source_wavelength, target_wavelength)
    mapped_intensity = [intensities[i] for i in kept]
    pairs = sorted(zip(angles, mapped_intensity))
    # merge duplicate angles by averaging intensities
    merged_angle: list[float] = []
    merged_intensity: list[float] = []
    for angle, value in pairs:
        if merged_angle and math.isclose(angle, merged_angle[-1], rel_tol=1e-12, abs_tol=1e-12):
            merged_intensity[-1] = 0.5 * (merged_intensity[-1] + value)
        else:
            merged_angle.append(angle)
            merged_intensity.append(value)
    count = int(round((two_theta_max - two_theta_min) / step)) + 1
    grid = np.linspace(two_theta_min, two_theta_max, count)
    interp = np.interp(grid, merged_angle, merged_intensity)
    peak = float(np.max(interp))
    if peak <= 0.0 or not math.isfinite(peak):
        raise ValueError("spectrum has non-positive maximum after resampling")
    interp = interp / peak
    return interp.astype(np.float32)


def build_inputs(
    *,
    config_path: Path = CONFIG_PATH,
    eval_manifest: Path = EVAL_MANIFEST,
    parent_manifest: Path = PARENT_MANIFEST,
    source_root: Path = SOURCE_ROOT,
    output_root: Path = OUTPUT_ROOT,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    class_order = list(config["class_order"])
    class_counts = {k: int(v) for k, v in config["class_counts"].items()}
    target_wavelength = float(config["target_wavelength_angstrom"])
    two_theta_min = float(config["two_theta_min"])
    two_theta_max = float(config["two_theta_max"])
    step = float(config["step_deg"])
    input_length = int(config["input_length"])

    eval_rows = list(csv.DictReader(eval_manifest.open(encoding="utf-8-sig")))
    expected_n = sum(class_counts.values())
    if len(eval_rows) != expected_n:
        raise ValueError(f"eval manifest has {len(eval_rows)} rows, expected {expected_n}")

    parent_rows = {
        row["parent_id"]: row
        for row in csv.DictReader(parent_manifest.open(encoding="utf-8-sig"))
    }
    if len(parent_rows) != expected_n:
        raise ValueError(f"parent manifest has {len(parent_rows)} rows, expected {expected_n}")
    for row in parent_rows.values():
        if str(row.get("formal_14060_overlap", "")).strip().lower() != "false":
            raise ValueError("a surviving parent still carries a formal_14060 overlap")

    matrix = np.zeros((expected_n, input_length), dtype=np.float32)
    manifest_rows: list[dict[str, Any]] = []
    seen_parents: set[str] = set()
    for position, row in enumerate(eval_rows):
        parent_id = row["parent_id"]
        if parent_id in seen_parents:
            raise ValueError(f"duplicate parent_id in eval manifest: {parent_id}")
        seen_parents.add(parent_id)
        scan_id = row["representative_scan_id"]
        path = source_root / f"{scan_id}.json"
        if not path.is_file():
            raise ValueError(f"missing source spectrum: {path}")
        two_theta, intensities, wavelength = read_spectrum(path)
        spectrum = resample(
            two_theta,
            intensities,
            wavelength,
            target_wavelength=target_wavelength,
            two_theta_min=two_theta_min,
            two_theta_max=two_theta_max,
            step=step,
        )
        matrix[position] = spectrum
        manifest_rows.append(
            {
                "position": position,
                "parent_id": parent_id,
                "scan_id": scan_id,
                "crystal_system": row["crystal_system"],
                "label_index": row["label_index"],
                "source_wavelength": wavelength,
                "mapped_point_count": int(
                    np.sum(
                        [
                            abs((target_wavelength / wavelength)
                                * math.sin(math.radians(v / 2.0))) <= 1.0
                            for v in two_theta
                        ]
                    )
                ),
                "resampled_max": float(np.max(spectrum)),
            }
        )

    # frozen assertions
    assert matrix.shape == (expected_n, input_length), matrix.shape
    assert np.isfinite(matrix).all(), "matrix contains NaN or Inf"
    assert np.allclose(matrix.max(axis=1), 1.0), "not every row is max-normalized"
    observed_counts: dict[str, int] = {}
    for row in manifest_rows:
        observed_counts[row["crystal_system"]] = observed_counts.get(row["crystal_system"], 0) + 1
    if observed_counts != class_counts:
        raise ValueError(f"class counts differ from frozen config: {observed_counts} != {class_counts}")

    output_root.mkdir(parents=True, exist_ok=True)
    np.savez(output_root / "cnrs318_inputs.npz", spectra=matrix)
    with (output_root / "cnrs318_preprocessing_manifest.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest_rows[0].keys()))
        writer.writeheader()
        writer.writerows(manifest_rows)

    report = {
        "schema_version": "cnrs318-preprocessing-report-v1",
        "status": "completed",
        "dataset_id": config["dataset_id"],
        "n_parents": expected_n,
        "shape": list(matrix.shape),
        "dtype": str(matrix.dtype),
        "nan_or_inf": bool(np.isnan(matrix).any() or np.isinf(matrix).any()),
        "all_rows_max_normalized": bool(np.allclose(matrix.max(axis=1), 1.0)),
        "unique_parents": len(seen_parents),
        "class_counts": observed_counts,
        "class_order": class_order,
        "eval_manifest_sha256": hashlib.sha256(eval_manifest.read_bytes()).hexdigest().upper(),
        "parent_manifest_sha256": hashlib.sha256(parent_manifest.read_bytes()).hexdigest().upper(),
        "inputs_sha256": hashlib.sha256(
            (output_root / "cnrs318_inputs.npz").read_bytes()
        ).hexdigest().upper(),
    }
    (output_root / "cnrs318_preprocessing_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build frozen CNRS318 zero-shot inputs")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--eval-manifest", type=Path, default=EVAL_MANIFEST)
    parser.add_argument("--parent-manifest", type=Path, default=PARENT_MANIFEST)
    parser.add_argument("--source-root", type=Path, default=SOURCE_ROOT)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_inputs(
        config_path=args.config.resolve(),
        eval_manifest=args.eval_manifest.resolve(),
        parent_manifest=args.parent_manifest.resolve(),
        source_root=args.source_root.resolve(),
        output_root=args.output_root.resolve(),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
