#!/usr/bin/env python3
"""Build the 21-structure V7 perturbation atlas and quality audit."""

from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path
import sys
from typing import Iterable

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.peak_cache import load_peak_table
from xrd_robustness.simulation_quality import inspect_perturbed_view
from xrd_robustness.simulator import SimulationGrid, simulate_from_peak_table
from xrd_robustness.structure_data import CRYSTAL_SYSTEMS, select_nested_structure_records
from xrd_robustness.physics import PhysicsParameters


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "configs" / "simulation.v7.candidate.json"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "reports" / "perturbation_atlas"),
    )
    parser.add_argument("--seed", type=int, default=20260712)
    parser.add_argument(
        "--shift-ood-abs",
        type=float,
        default=0.5,
        help="Absolute OOD shift magnitude used for the symmetric shift audit",
    )
    return parser.parse_args()


def _load_selected_records() -> list[dict]:
    records_path = PROJECT_ROOT / "data" / "mp_processed" / "structure_records.jsonl"
    all_records = [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected = select_nested_structure_records(all_records, dataset_size=140)
    by_system = {system: [] for system in CRYSTAL_SYSTEMS}
    for record in selected:
        by_system[record["crystal_system"]].append(record)
    return [record for system in CRYSTAL_SYSTEMS for record in sorted(by_system[system], key=lambda row: row["material_id"])[:3]]


def _parameters(condition: str, case: str, sign: float, *, shift_ood_abs: float) -> PhysicsParameters:
    values = {
        "shift": {"light": (0.05, 0.08, 0.0, 0.0), "medium": (0.10, 0.08, 0.0, 0.0), "train_upper": (0.20, 0.08, 0.0, 0.0), "ood": (0.35, 0.08, 0.0, 0.0)},
        "broadening": {"light": (0.0, 0.12, 0.0, 0.0), "medium": (0.0, 0.15, 0.0, 0.0), "train_upper": (0.0, 0.20, 0.0, 0.0), "ood": (0.0, 0.275, 0.0, 0.0)},
        "noise": {"light": (0.0, 0.08, 0.005, 0.0), "medium": (0.0, 0.08, 0.01, 0.0), "train_upper": (0.0, 0.08, 0.02, 0.0), "ood": (0.0, 0.08, 0.035, 0.0)},
        "background": {"light": (0.0, 0.08, 0.0, 0.005), "medium": (0.0, 0.08, 0.0, 0.01), "train_upper": (0.0, 0.08, 0.0, 0.02), "ood": (0.0, 0.08, 0.0, 0.035)},
        "combined": {"light": (0.05, 0.12, 0.005, 0.005), "medium": (0.10, 0.15, 0.01, 0.01), "train_upper": (0.20, 0.20, 0.01, 0.01), "ood": (0.35, 0.275, 0.035, 0.035)},
    }
    shift, fwhm, noise, background = values[condition][case]
    if case == "ood" and condition in {"shift", "combined"}:
        shift = shift_ood_abs
    if condition == "shift" or condition == "combined":
        shift *= sign
    return PhysicsParameters(
        delta_2theta_deg=shift,
        fwhm_deg=fwhm,
        background_to_peak_ratio=background,
        noise_std_ratio=noise,
        background_type="polynomial" if background else "flat",
        severity_level=0 if case == "level0" else (4 if case == "ood" else 1),
    )


def _svg(profile: np.ndarray, *, width: int = 520, height: int = 120) -> str:
    values = np.asarray(profile, dtype=np.float64)
    stride = max(1, int(np.ceil(values.size / 500)))
    values = values[::stride]
    maximum = max(float(values.max()), 1e-8)
    points = []
    for index, value in enumerate(values):
        x = index / max(1, values.size - 1) * width
        y = height - (float(value) / maximum) * (height - 4) - 2
        points.append(f"{x:.2f},{y:.2f}")
    return f'<svg viewBox="0 0 {width} {height}" role="img"><polyline points="{" ".join(points)}" fill="none" stroke="#1f4e79" stroke-width="1.2"/></svg>'


def _cases() -> list[tuple[str, str]]:
    return [("level0", "level0"), *((condition, case) for condition in ("shift", "broadening", "noise", "background", "combined") for case in ("light", "medium", "train_upper", "ood"))]


def main() -> int:
    args = parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    grid = SimulationGrid()
    quality_gates = config.get("quality_gates", {})
    recall_threshold = float(quality_gates.get("top20_peak_recall_min", 0.80))
    retained_threshold = float(quality_gates.get("retained_integrated_intensity_min", 0.95))
    clipping_fraction_max = float(quality_gates.get("clipped_fraction_max", 0.55))
    records = _load_selected_records()
    base_parameters = PhysicsParameters(0.0, 0.08, 0.0, 0.0, "flat", 0)
    atlas: dict[str, dict[str, dict]] = {}
    rejected: list[dict] = []
    summary: list[dict] = []
    for record_index, record in enumerate(records):
        material_id = record["material_id"]
        peaks = load_peak_table(PROJECT_ROOT / "data" / "mp_processed" / "peak_tables_v7_reflection" / f"{material_id}.npz")
        base_raw = simulate_from_peak_table(
            peaks.positions,
            peaks.intensities,
            base_parameters,
            rng_seed=args.seed + record_index,
            grid=grid,
            normalize=False,
        )
        base = base_raw / max(float(np.max(base_raw)), 1e-8)
        atlas.setdefault(record["crystal_system"], {})[material_id] = {"level0": base}
        for condition in ("shift", "broadening", "noise", "background", "combined"):
            for case in ("light", "medium", "train_upper", "ood"):
                sign = -1.0 if record_index % 2 else 1.0
                parameters = _parameters(condition, case, sign, shift_ood_abs=args.shift_ood_abs)
                profile_raw, simulation_diagnostics = simulate_from_peak_table(
                    peaks.positions,
                    peaks.intensities,
                    parameters,
                    rng_seed=args.seed + 1000 + record_index,
                    grid=grid,
                    normalize=False,
                    return_diagnostics=True,
                )
                quality = inspect_perturbed_view(
                    base_raw,
                    profile_raw,
                    peak_positions=peaks.positions,
                    peak_intensities=peaks.intensities,
                    grid=grid.values,
                    parameters=parameters,
                    recall_threshold=recall_threshold,
                    retained_threshold=retained_threshold,
                    clipping_fraction_max=clipping_fraction_max,
                    simulation_diagnostics=simulation_diagnostics,
                )
                key = f"{condition}:{case}"
                profile = profile_raw / max(float(np.max(profile_raw)), 1e-8)
                atlas[record["crystal_system"]][material_id][key] = {
                    "profile": profile,
                    "quality": quality,
                    "parameters": parameters.to_dict(),
                }
                summary.append({
                    "condition": condition,
                    "case": case,
                    "material_id": material_id,
                    "crystal_system": record["crystal_system"],
                    **{key: value for key, value in quality.items() if key != "reasons"},
                    "reasons": ";".join(quality["reasons"]),
                })
                if not quality["passed"]:
                    rejected.append({
                        "condition": condition,
                        "case": case,
                        "material_id": material_id,
                        "crystal_system": record["crystal_system"],
                        "parameters": json.dumps(parameters.to_dict(), sort_keys=True),
                        "reasons": ";".join(quality["reasons"]),
                        "top20_peak_recall": quality["top20_peak_recall"],
                        "window_intensity_retained": quality["window_intensity_retained"],
                        "clipped_fraction": quality["clipped_fraction"],
                    })

    with (output_dir / "rejected_parameter_cases.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["condition", "case", "material_id", "crystal_system", "parameters", "reasons", "top20_peak_recall", "window_intensity_retained", "clipped_fraction"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rejected)
    with (output_dir / "quality_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = sorted({key for row in summary for key in row})
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summary)

    document = [
        "<!doctype html><html><head><meta charset='utf-8'><title>V7 Perturbation Atlas</title>",
        "<style>body{font-family:Arial,sans-serif;margin:24px;color:#222} table{border-collapse:collapse;margin-bottom:32px} th,td{border:1px solid #bbb;padding:5px;vertical-align:top} th{background:#eef3f8} td svg{width:260px;height:70px;background:#fff} .fail{background:#fff0f0} .pass{background:#f2fff2} small{color:#555}</style></head><body>",
        "<h1>V7 Candidate Perturbation Atlas</h1>",
        f"<p>Candidate config: <code>{html.escape(str(Path(args.config)))}</code>. This is a quality-screening report, not a final physical validation.</p>",
        f"<p>Structures: {len(records)} (3 per crystal system). Rejected cases: {len(rejected)}.</p>",
    ]
    for condition in ("shift", "broadening", "noise", "background", "combined"):
        document.append(f"<h2>{condition}</h2><table><tr><th>Structure</th><th>Level 0</th><th>Light</th><th>Medium</th><th>Train upper</th><th>OOD</th></tr>")
        for record in records:
            material_id = record["material_id"]
            entries = atlas[record["crystal_system"]][material_id]
            cells = [
                f"<td><small>{html.escape(material_id)}<br>{html.escape(record['crystal_system'])}</small></td>",
                f"<td>{_svg(entries['level0'])}</td>",
            ]
            for case in ("light", "medium", "train_upper", "ood"):
                entry = entries[f"{condition}:{case}"]
                quality = entry["quality"]
                css = "pass" if quality["passed"] else "fail"
                cells.append(f"<td class='{css}'>{_svg(entry['profile'])}<br><small>recall={quality['top20_peak_recall']:.2f}, retained={quality['window_intensity_retained']:.2f}, clipped={quality['clipped_fraction']:.2f}<br>{html.escape(';'.join(quality['reasons']))}</small></td>")
            document.append("<tr>" + "".join(cells) + "</tr>")
        document.append("</table>")
    document.append("</body></html>")
    (output_dir / "perturbation_atlas_report.html").write_text("\n".join(document), encoding="utf-8")
    print(json.dumps({"structures": len(records), "rejected": len(rejected), "report": str(output_dir / 'perturbation_atlas_report.html')}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
