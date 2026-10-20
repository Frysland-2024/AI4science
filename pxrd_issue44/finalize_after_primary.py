"""One-time continuation from fully persisted primary rows; never reruns primary scoring."""
from __future__ import annotations

import hashlib
import json
import os
import socket
import time
from pathlib import Path

from pxrd_issue44 import benchmark as b


def load_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_complete_primary(run, config):
    run = Path(run)
    marker = b.read_json(run / "test_opened.json")
    if marker.get("status") != "OPENED_ONCE" or "already-opened PR43" not in marker.get("relationship", ""):
        raise RuntimeError("primary marker is absent or does not identify the preregistered opened PR43 set")

    complete = b.read_json(run / "training_complete.json")
    expected_models = {(m, a, int(s)) for m in config["materials"]
                       for a in config["architectures"] for s in config["training"]["seeds"]}
    observed_models = {(r["material"], r["architecture"], int(r["seed"])) for r in complete["models"]}
    if complete.get("model_run_count") != len(expected_models) or observed_models != expected_models:
        raise RuntimeError("the frozen 42-model training matrix is incomplete")

    selection_hashes = {k.replace("\\", "/"): v for k, v in complete["selection_sha256"].items()}
    marker_hashes = {r["path"].replace("\\", "/"): r["sha256"] for r in marker.get("selection_files", [])}
    if len(marker_hashes) != len(expected_models) or marker_hashes != selection_hashes:
        raise RuntimeError("primary marker does not match all frozen model selections")
    selected = []
    for material, architecture, seed in sorted(expected_models):
        selection_path = run / "models" / material / architecture / f"selection_{seed}.json"
        checkpoint = run / "models" / material / architecture / "private" / f"best_{seed}.pt"
        key = str(selection_path.relative_to(b.ROOT)).replace("\\", "/")
        if not selection_path.is_file() or b.sha(selection_path) != selection_hashes.get(key):
            raise RuntimeError(f"selection hash mismatch: {material}/{architecture}/{seed}")
        selection = b.read_json(selection_path)
        if (selection.get("material"), selection.get("architecture"), int(selection.get("seed", -1))) != (
                material, architecture, seed):
            raise RuntimeError(f"selection identity mismatch: {material}/{architecture}/{seed}")
        if not checkpoint.is_file() or b.sha(checkpoint) != selection.get("checkpoint_sha256"):
            raise RuntimeError(f"checkpoint hash mismatch: {material}/{architecture}/{seed}")
        selected.append({"material": material, "architecture": architecture, "seed": seed,
                         "selection_sha256": b.sha(selection_path), "checkpoint_sha256": b.sha(checkpoint)})

    split = b.splits({"data": {"parents": 512, "train": 358, "validation": 77, "test": 77,
                               "split_seed": 2026101902}})
    expected_parents = set(int(x) for x in split["test"])
    expected_methods = {("P0", 0), ("P3", 0), ("P5", 0)}
    for architecture in config["architectures"]:
        for seed in config["training"]["seeds"]:
            expected_methods.add((f"{architecture}-direct", int(seed)))
            expected_methods.add((f"{architecture}+A", int(seed)))
    expected_keys = {(parent, method, seed) for parent in expected_parents for method, seed in expected_methods}
    material_audit = {}
    all_rows = []
    for material in config["materials"]:
        folder = run / "primary" / material
        path = folder / "per_sample.jsonl"
        rows = load_rows(path)
        observed = [(int(r["parent"]), r["method"], int(r["seed"])) for r in rows]
        if len(rows) != len(expected_keys) or set(observed) != expected_keys or len(set(observed)) != len(observed):
            raise RuntimeError(f"primary rows are incomplete or duplicated: {material} ({len(rows)} records)")
        dimensions = {len(r["q_true_posthoc"]) for r in rows}
        if len(dimensions) != 1 or any(len(r["lattice_abs_error_angstrom"]) not in dimensions for r in rows):
            raise RuntimeError(f"inconsistent DOF vectors in saved primary rows: {material}")
        metrics = b.read_json(folder / "metrics.json")
        observed_summaries = {(r["method"], int(r["seed"])) for r in metrics}
        if observed_summaries != expected_methods:
            raise RuntimeError(f"per-material primary summaries are incomplete: {material}")
        all_rows.extend(rows)
        material_audit[material] = {"rows": len(rows), "parents": len(expected_parents),
                                    "dof_count": next(iter(dimensions)),
                                    "per_sample_sha256": b.sha(path), "metrics_sha256": b.sha(folder / "metrics.json")}
    return {"status": "PASS", "training_models": len(selected), "training_selections": selected,
            "primary_rows": len(all_rows), "primary_rows_by_material": material_audit,
            "primary_records_sha256": hashlib.sha256("".join(
                b.sha(run / "primary" / m / "per_sample.jsonl") for m in config["materials"]).encode()).hexdigest()}, all_rows


def write_primary_summaries(run, config, rows, prior):
    primary = run / "primary"
    b.atomic(primary / "metrics.json", b.summarize_issue44(rows))
    mlp = [r for material in config["materials"] for r in prior[material]["rows_data"] if r["method"] == "N+A"]
    b.atomic(primary / "mlp_pr43_primary_reference.json", b.summarize_issue44(mlp))
    (primary / "test_reuse_notice.md").write_text(
        "Primary rows were scored exactly once before the post-test aggregation error. This continuation summarizes the persisted JSONL only; it does not regenerate observations, rerun fits, or select models. The reused PR43 split is exploratory, not independent confirmation. Historical MLP N+A rows are read-only; MLP-only predictions were unavailable and were not reconstructed.\n",
        encoding="utf-8")


def finalize_saved_primary(run, stress_gate):
    run = Path(run).resolve()
    lock = run / "post_primary_continuation.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(json.dumps({"pid": os.getpid(), "host": socket.gethostname(), "started": time.time()}))
    try:
        config = b.read_json(b.HERE / "frozen_config.json")
        primary_audit, primary_rows = validate_complete_primary(run, config)
        stress_root = run / "stress"
        if any(stress_root.glob("*/per_sample.jsonl")) or (stress_root / "metrics.json").exists():
            raise RuntimeError("stress outputs already exist; no retry is permitted")
        if stress_gate.get("status") != "BLOCKED_NOT_RUN" or not stress_gate.get("reason"):
            raise RuntimeError("this finalizer only supports an explicit blocked/not-run stress record")
        real_gate = b.read_json(b.HERE / "REAL_RRUFF_GATE.json")
        if real_gate.get("status") != "BLOCKED" or real_gate.get("allowed_real_cases") != 0:
            raise RuntimeError("real-domain gate changed; continuation is refused")
        frozen_hashes = b.read_json(run / "manifest.json").get("hashes", {})
        sidecar = b.read_json(run / "posttraining_manager_continuation.json")
        before_functions = sidecar["function_hashes_after"]
        current_functions = b._top_level_function_hashes()
        changed_functions = sorted(name for name in set(before_functions) & set(current_functions)
                                   if before_functions[name] != current_functions[name])
        added_functions = sorted(set(current_functions) - set(before_functions))
        removed_functions = sorted(set(before_functions) - set(current_functions))
        if changed_functions != ["build_report", "summarize_issue44"] or added_functions or removed_functions:
            raise RuntimeError("post-test source changes exceed the summary grouping and blocked-stress reporting fix")
        if current_functions.get("train_one") != before_functions.get("train_one") or \
                current_functions.get("evaluate_primary") != before_functions.get("evaluate_primary") or \
                current_functions.get("evaluate_stress") != before_functions.get("evaluate_stress"):
            raise RuntimeError("training or evaluation code changed; post-primary continuation is refused")

        current_hashes = {k.replace("\\", "/"): v for k, v in b.hash_inputs().items()}
        frozen_normalized = {k.replace("\\", "/"): v for k, v in frozen_hashes.items()}
        source_drift = sorted(k for k in set(current_hashes) | set(frozen_normalized)
                              if current_hashes.get(k) != frozen_normalized.get(k))
        if source_drift != ["pxrd_issue44/benchmark.py", "pxrd_issue44/test_benchmark.py"]:
            raise RuntimeError(f"post-test input hash changes are broader than reporting/test coverage: {source_drift}")

        now = time.time()
        budget = b.read_json(run / "budget.json")
        elapsed = now - float(budget["started"])
        limits = config["compute_limits"]
        size_before = sum(p.stat().st_size for p in run.rglob("*") if p.is_file())
        if elapsed >= limits["wall_seconds"] or size_before >= limits["disk_bytes"]:
            raise RuntimeError("PARTIAL: wall or output budget was reached before post-primary continuation")
        prior = b.verify_pr43()
        write_primary_summaries(run, config, primary_rows, prior)
        stress_root.mkdir(exist_ok=True)
        b.atomic(stress_root / "status.json", stress_gate)
        b.atomic(stress_root / "metrics.json", [])
        (stress_root / "not_run_notice.md").write_text(
            "New-architecture stress scoring was not run because an unidentified active Python process was using CPU and its command line could not be inspected. Per the no-disruption rule, this stage remains blocked/not run; the PR43 historical stress baseline is unchanged.\n",
            encoding="utf-8")
        recovery = {"status": "PRIMARY_COMPLETE_STRESS_BLOCKED_NOT_RUN", "time": now,
                    "primary_scoring_rerun": False, "primary_rows_verified": primary_audit["primary_rows"],
                    "primary_audit": primary_audit, "stress_status": stress_gate,
                    "frozen_manifest_hashes_sha256": hashlib.sha256(json.dumps(frozen_hashes, sort_keys=True).encode()).hexdigest(),
                    "current_source_hashes": current_hashes,
                    "benchmark_sha256_after_report_fix": b.sha(b.HERE / "benchmark.py"),
                    "finalizer_script_sha256": b.sha(Path(__file__)),
                    "function_changes_after_test_open": changed_functions,
                    "training_and_primary_evaluation_functions_unchanged": True,
                    "prior_failure_sha256": b.sha(run / "failure.json"),
                    "budget_elapsed_seconds_before_stress": elapsed, "output_bytes_before_stress": size_before}
        b.atomic(run / "post_primary_recovery.json", recovery)
        recovery.update({"status": "COMPLETE_WITH_STRESS_BLOCKED_NOT_RUN",
                         "stress_scoring_started": False, "stress_marker_created": False})
        b.build_report(run, config)
        b.budget_check(run, float(budget["started"]), float(budget["gpu_training_seconds"]))
        size_after = sum(p.stat().st_size for p in run.rglob("*") if p.is_file())
        if size_after > limits["disk_bytes"]:
            raise RuntimeError("PARTIAL: output budget exceeded after stress evaluation")
        recovery.update({"finished": time.time(), "primary_scoring_rerun": False,
                         "stress_summary_rows": 0, "output_bytes_after": size_after,
                         "elapsed_seconds_after": time.time() - float(budget["started"]),
                         "report_sha256": b.sha(run / "FINAL_REPORT.md"),
                         "comparison_sha256": b.sha(run / "comparison.json")})
        b.atomic(run / "post_primary_recovery.json", recovery)
        manifest = b.read_json(run / "manifest.json")
        manifest["stage"] = "SYNTHETIC_PRIMARY_COMPLETE_STRESS_NOT_RUN_REAL_RRUFF_BLOCKED"
        manifest["post_primary_recovery_sha256"] = b.sha(run / "post_primary_recovery.json")
        b.atomic(run / "manifest.json", manifest)
        b.atomic(run / "status.json", {"status": "PARTIAL", "synthetic_status": "COMPLETE",
            "stage": "SYNTHETIC_PRIMARY_COMPLETE_STRESS_NOT_RUN_REAL_RRUFF_BLOCKED",
            "finished": recovery["finished"], "elapsed_seconds": recovery["elapsed_seconds_after"],
            "model_runs": 42, "primary_rows_including_baselines_and_neural": primary_audit["primary_rows"],
            "stress_status": "BLOCKED_NOT_RUN", "stress_summary_rows": 0, "materials": config["materials"],
            "real_rruff": "BLOCKED", "publication": "PENDING", "report": "FINAL_REPORT.md",
            "comparison": "comparison.json", "primary_scoring_rerun": False,
            "historical_finalizer_failure": "preserved in failure.json; aggregation recovered from complete saved rows"})
        b.append_jsonl(run / "events.jsonl", {"event": "post_primary_aggregation_recovered",
            "time": recovery["finished"], "primary_rows_verified": primary_audit["primary_rows"],
            "primary_scoring_rerun": False, "stress_summary_rows": 0,
            "stress_status": "BLOCKED_NOT_RUN",
            "real_rruff": "BLOCKED"})
        return recovery
    except Exception as exc:
        status = {"status": "PARTIAL", "stage": "post_primary_continuation_stopped",
                  "time": time.time(), "error": repr(exc), "primary_scoring_rerun": False}
        b.atomic(run / "post_primary_failure.json", status)
        b.atomic(run / "status.json", status)
        raise
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--stress-gate-file", required=True, type=Path,
                         help="JSON record explaining why stress scoring is blocked/not run")
    arguments = parser.parse_args()
    finalize_saved_primary(arguments.run, b.read_json(arguments.stress_gate_file))
