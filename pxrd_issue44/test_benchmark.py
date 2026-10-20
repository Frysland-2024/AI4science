"""Manager integrity checks that never generate or read held-out profiles."""
import json
from types import SimpleNamespace

import pytest

from pxrd_issue44 import benchmark


def test_report_builder_writes_all_frozen_cells_and_bootstrap(tmp_path):
    config = benchmark.read_json(benchmark.HERE / "frozen_config.json")
    run = tmp_path
    primary_dir = run / "primary"
    stress_dir = run / "stress"
    primary_dir.mkdir()
    stress_dir.mkdir()
    summaries = []
    mlp = []
    training = []
    for material in config["materials"]:
        cell_dims = 1 if material in {"mgo", "ceo2", "silicon"} else 2
        cell_errors = [0.01] * cell_dims
        for method, seed, q_mae, seconds in (("P0", 0, 0.3, 2.0), ("P3", 0, 0.2, 1.0), ("P5", 0, 0.15, 2.5)):
            summaries.append({"material": material, "method": method, "seed": seed, "q_mae": q_mae,
                "q_mae_per_dof": [q_mae] * cell_dims, "lattice_mae_angstrom": cell_errors,
                "convergence_rate": 0.99, "mean_seconds_end_to_end": seconds, "mean_nfev": 50})
        for seed in config["training"]["seeds"]:
            mlp.append({"material": material, "method": "N+A", "seed": seed, "q_mae": 0.22,
                "q_mae_per_dof": [0.22] * cell_dims, "lattice_mae_angstrom": cell_errors,
                "convergence_rate": 0.98, "mean_seconds_end_to_end": 1.1, "mean_nfev": 60})
        raw = []
        for parent in (4, 9):
            truth = [0.0] * cell_dims
            raw.append({"material": material, "method": "P3", "seed": 0, "parent": parent,
                "success": True, "q_true_posthoc": truth, "q_fit": [0.10] * cell_dims,
                "lattice_abs_error_angstrom": cell_errors})
            for architecture in config["architectures"]:
                for seed in config["training"]["seeds"]:
                    raw.append({"material": material, "method": f"{architecture}+A", "seed": seed,
                        "parent": parent, "success": True, "q_true_posthoc": truth, "q_fit": [0.05] * cell_dims,
                        "lattice_abs_error_angstrom": [0.005] * cell_dims})
                    for suffix, q_mae, seconds in (("direct", 0.07, 0.1), ("+A", 0.08, 0.5)):
                        method = f"{architecture}-direct" if suffix == "direct" else f"{architecture}+A"
                        summaries.append({"material": material, "method": method, "seed": seed, "q_mae": q_mae,
                            "q_mae_per_dof": [q_mae] * cell_dims, "lattice_mae_angstrom": [0.005] * cell_dims,
                            "convergence_rate": 0.99, "mean_seconds_end_to_end": seconds, "mean_nfev": 25})
                    training.append({"material": material, "architecture": architecture, "seed": seed,
                        "training_seconds": 1.0, "best_epoch": 2})
        (primary_dir / material).mkdir()
        (primary_dir / material / "per_sample.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in raw), encoding="utf-8")
    (primary_dir / "metrics.json").write_text(json.dumps(summaries), encoding="utf-8")
    (primary_dir / "mlp_pr43_primary_reference.json").write_text(json.dumps(mlp), encoding="utf-8")
    (stress_dir / "metrics.json").write_text("[]", encoding="utf-8")
    (stress_dir / "status.json").write_text(json.dumps({"status": "BLOCKED_NOT_RUN",
        "reason": "pre-existing process gate"}), encoding="utf-8")
    (run / "training_complete.json").write_text(json.dumps({"models": training}), encoding="utf-8")
    (run / "budget.json").write_text(json.dumps({"gpu_training_seconds": 100.0}), encoding="utf-8")
    for item in training:
        folder = run / "models" / item["material"] / item["architecture"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"selection_{item['seed']}.json").write_text(json.dumps(item), encoding="utf-8")

    comparison = benchmark.build_report(run, config)
    assert len(comparison["paired_parent_bootstrap_vs_p3"]) == 42
    assert comparison["criteria"]["all_42_architecture_seed_material_cells_pass_accuracy_vs_p3"] is True
    assert comparison["criteria"]["pass_counts"]["q_accuracy_vs_p3"] == 42
    assert comparison["stress_status"]["status"] == "BLOCKED_NOT_RUN"
    assert (run / "FINAL_REPORT.md").is_file()
    report = (run / "FINAL_REPORT.md").read_text(encoding="utf-8")
    assert "BLOCKED_NOT_RUN" in report
    assert "Overall status: **PARTIAL**" in report
    assert "42/42" in report


def test_failed_physics_start_keeps_actual_wall_time(monkeypatch):
    class BrokenModel:
        def fit(self, *args, **kwargs):
            raise RuntimeError("synthetic optimizer failure")

    ticks = iter((1.0, 1.5))
    monkeypatch.setattr(benchmark.time, "perf_counter", lambda: next(ticks))
    result = benchmark.fit_attempt(BrokenModel(), [0.0], [0.25], {"physics": {"maxiter_per_start": 100,
        "maxfun_per_start": 1000}})
    assert result["success"] is False
    assert result["failed"] is True
    assert result["message"] == "RuntimeError('synthetic optimizer failure')"
    assert result["seconds"] == pytest.approx(0.5)


def test_wddm_graphics_contexts_do_not_block_and_unknown_gpu_processes_do(monkeypatch):
    commands = []

    def fake_run(args, **kwargs):
        commands.append(args[0])
        if args[0] == "nvidia-smi":
            return SimpleNamespace(stdout="123, [Insufficient Permissions], [N/A]\n456, [N/A], [N/A]\n")
        if commands.count("nvidia-smi") == 1:
            return SimpleNamespace(stdout='[{"Id":123,"ProcessName":"chrome"},'
                                          '{"Id":456,"ProcessName":"WorkBuddy"}]')
        return SimpleNamespace(stdout='[{"Id":123,"ProcessName":"python"},'
                                      '{"Id":456,"ProcessName":"WorkBuddy"}]')

    monkeypatch.setattr(benchmark.subprocess, "run", fake_run)
    monkeypatch.setattr(benchmark.os, "getpid", lambda: 999)
    assert benchmark.gpu_compute_processes() == []
    assert benchmark.gpu_compute_processes() == ["python.exe"]
    assert commands == ["nvidia-smi", "powershell.exe", "nvidia-smi", "powershell.exe"]


def test_full_matrix_requires_complete_smoke_before_test(tmp_path):
    with pytest.raises(RuntimeError, match="operational smoke must pass"):
        benchmark.require_completed_smoke(tmp_path, {})

    config = benchmark.read_json(benchmark.HERE / "frozen_config.json")
    records = [{"material": material, "architecture": architecture, "seed": config["smoke"]["seed"]}
               for material in config["smoke"]["materials"] for architecture in config["smoke"]["architectures"]]
    hashes = {"frozen-source": "sha256"}
    (tmp_path / "smoke").mkdir()
    (tmp_path / "smoke" / "SMOKE.json").write_text(json.dumps({"status": "PASS", "records": records,
        "model_runs": len(records), "test_observations_generated": 0, "test_opened": False}), encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps({"stage": "SMOKE_COMPLETE_BEFORE_TEST", "hashes": hashes}),
        encoding="utf-8")
    result = benchmark.require_completed_smoke(tmp_path, hashes)
    assert result["model_runs"] == 6

    (tmp_path / "test_opened.json").write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="test-open marker exists"):
        benchmark.require_completed_smoke(tmp_path, hashes)


def test_paired_parent_bootstrap_is_deterministic_and_reports_dofs():
    rows = []
    for parent, base_error, model_error in ((2, 0.20, 0.10), (4, 0.10, 0.12), (8, 0.30, 0.15)):
        for method, error in (("P3", base_error), ("resnet1d+A", model_error)):
            rows.append({"material": "batio3", "method": method, "seed": 0 if method == "P3" else 7,
                "parent": parent, "success": True, "q_true_posthoc": [0.0, 0.0], "q_fit": [error, error],
                "lattice_abs_error_angstrom": [error / 10, error / 20]})
    first = benchmark.paired_parent_bootstrap(rows, "batio3", "resnet1d", 7, resamples=250)
    second = benchmark.paired_parent_bootstrap(rows, "batio3", "resnet1d", 7, resamples=250)
    assert first == second
    assert first["q_mae"]["n_parents"] == 3
    assert first["q_mae"]["mean_delta"] == pytest.approx((-0.10 + 0.02 - 0.15) / 3)
    assert len(first["cell_mae_angstrom_per_dof"]) == 2
    assert first["interpretation"].startswith("descriptive paired-parent bootstrap")


def test_summary_keeps_materials_and_distinct_dofs_separate():
    rows = [
        {"material": "cubic", "method": "P3", "seed": 0, "success": True,
         "q_fit": [0.2], "q_true_posthoc": [0.0], "lattice_abs_error_angstrom": [0.01],
         "rmse": 0.1, "seconds": 1.0, "nfev": 3, "boundary_hit": False},
        {"material": "tetragonal", "method": "P3", "seed": 0, "success": True,
         "q_fit": [0.2, -0.4], "q_true_posthoc": [0.0, 0.0],
         "lattice_abs_error_angstrom": [0.01, 0.02], "rmse": 0.1, "seconds": 1.0,
         "nfev": 3, "boundary_hit": False},
    ]

    result = benchmark.summarize_issue44(rows)

    assert [(row["material"], row["q_mae_per_dof"]) for row in result] == [
        ("cubic", [pytest.approx(0.2)]), ("tetragonal", [pytest.approx(0.2), pytest.approx(0.4)])]
    assert [row["lattice_mae_angstrom"] for row in result] == [[pytest.approx(0.01)],
                                                               [pytest.approx(0.01), pytest.approx(0.02)]]
