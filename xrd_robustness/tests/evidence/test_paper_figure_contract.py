from __future__ import annotations

import json
import statistics
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATHS = (
    PROJECT_ROOT / "reports" / "validation_results.json",
    PROJECT_ROOT / "reports" / "simulated_test_results.json",
)
METRICS = (
    "level0_macro_f1",
    "in_range_macro_f1",
    "mean_single_factor_ood_macro_f1",
    "worst_class_f1",
)
METHODS = ("dynamic_erm", "js_consistency")


def _load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


@pytest.mark.parametrize("report_path", REPORT_PATHS)
def test_paired_figure_rows_reproduce_public_aggregates(report_path: Path) -> None:
    report = _load_json(report_path)
    pairs = report["paired_runs"]
    assert isinstance(pairs, list)
    assert len(pairs) == report["paired_seed_count"]

    contract = _load_json(PROJECT_ROOT / "configs" / "experiment.public.json")
    assert [pair["training_seed"] for pair in pairs] == contract["training_seeds"]

    for metric in METRICS:
        values_by_method = {
            method: [float(pair[method][metric]) for pair in pairs]
            for method in METHODS
        }
        for method, values in values_by_method.items():
            aggregate = report["methods"][method][metric]
            assert statistics.fmean(values) == pytest.approx(
                aggregate["mean"], abs=1e-12
            )
            assert statistics.stdev(values) == pytest.approx(
                aggregate["sample_sd"], abs=1e-12
            )

        deltas = [
            js_value - erm_value
            for erm_value, js_value in zip(
                values_by_method["dynamic_erm"],
                values_by_method["js_consistency"],
                strict=True,
            )
        ]
        improvement = report["paired_improvements"][metric]
        assert statistics.fmean(deltas) == pytest.approx(
            improvement["mean"], abs=1e-12
        )
        if "sample_sd" in improvement:
            assert statistics.stdev(deltas) == pytest.approx(
                improvement["sample_sd"], abs=1e-12
            )
        if "positive_pairs" in improvement:
            assert sum(delta > 0.0 for delta in deltas) == improvement[
                "positive_pairs"
            ]


def test_all_four_paper_figure_scaffolds_generate(tmp_path: Path) -> None:
    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "generate_paper_figures.py"),
        "--output-dir",
        str(tmp_path),
        "--formats",
        "svg",
    ]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True, capture_output=True, text=True)

    expected = {
        "figure_1_method_overview.svg",
        "figure_2_validation_paired_ood.svg",
        "figure_3_simulated_test_paired_ood.svg",
        "figure_4_metric_overview.svg",
    }
    generated = {path.name for path in tmp_path.iterdir() if path.is_file()}
    assert generated == expected
    for filename in expected:
        content = (tmp_path / filename).read_text(encoding="utf-8")
        assert "<svg" in content
        assert len(content) > 1_000
