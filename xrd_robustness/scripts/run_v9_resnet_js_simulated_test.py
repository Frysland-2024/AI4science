#!/usr/bin/env python3
"""Fail-closed one-shot V9 ResNet-JS simulated-Test evaluator.

This runner implements the already frozen ten-checkpoint Test contract.  It
never trains, selects a checkpoint, reads real-XRD data, or changes the panel.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xrd_robustness.evaluation.metrics import classification_metrics
from xrd_robustness.experiment import assert_model_fingerprint, load_checkpoint
from xrd_robustness.models.ml4pxrd_resnet1d import (
    ML4PXRDResNet1D,
    ML4PXRDResNet1DConfig,
)
from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.peak_cache import load_peak_table, validate_peak_cache_manifest
from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.structure_data import CRYSTAL_SYSTEMS
from xrd_robustness.view_manifest import build_offline_view_manifest, save_manifest

CONTRACT_PATH = ROOT / "configs/v9_resnet_js_simulated_test.preregistered.json"
AUTH_PATH = ROOT / "configs/v9_resnet_js_simulated_test.authorization.json"
SIM_PATH = ROOT / "configs/simulation.v9.method_transfer.frozen.json"
SPLIT_PATH = ROOT / "data/formal_14060/manifests/split_manifest.json"
DATA_ROOT = ROOT / "data/formal_14060"
OUTPUT_ROOT = ROOT / "outputs/v9_resnet_js_simulated_test_v1"
CHECKPOINT_ROOT = ROOT / "outputs/v9_resnet_js_simulated_test_checkpoints/checkpoints"
PREFLIGHT_PATH = ROOT / "reports/v9_resnet_js_simulated_test_preflight.json"
SUMMARY_PATH = ROOT / "reports/v9_resnet_js_simulated_test_summary.json"
AUDIT_PATH = ROOT / "reports/v9_resnet_js_simulated_test_audit.json"
RETRY_AUTH_PATH = ROOT / "configs/v9_resnet_js_simulated_test.retry_authorization.json"
PANEL_CACHE_ROOT = ROOT / "outputs/v9_resnet_js_simulated_test_panel_cache_v1"
PANEL_CACHE_INDEX = PANEL_CACHE_ROOT / "index.json"
RUN_STATE_PATH = OUTPUT_ROOT / "run_state.json"
LAUNCHER_LOG_NAMES = {"runner.stdout.log", "runner.stderr.log"}
PROFILES = (
    "level0",
    "in_range",
    "ood_shift_negative",
    "ood_shift_positive",
    "ood_broadening",
    "ood_noise",
    "ood_background",
    "ood_texture",
    "ood_combo_shift_broadening",
    "ood_combo_background_noise",
    "ood_combo_texture_shift",
    "ood_all",
)
RENDERER_SOURCE_PATHS = (
    ROOT / "src/xrd_robustness/measurement_models.py",
    ROOT / "src/xrd_robustness/online_views.py",
    ROOT / "src/xrd_robustness/peak_cache.py",
    ROOT / "src/xrd_robustness/perturbation_strategy.py",
    ROOT / "src/xrd_robustness/physics.py",
    ROOT / "src/xrd_robustness/preferred_orientation.py",
    ROOT / "src/xrd_robustness/simulation_interfaces.py",
    ROOT / "src/xrd_robustness/simulator.py",
    ROOT / "src/xrd_robustness/view_manifest.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def renderer_source_hashes() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in RENDERER_SOURCE_PATHS
    }


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def output_root_has_test_artifacts() -> bool:
    """Launcher logs are not Test artifacts; every other entry is fail-closed."""
    return OUTPUT_ROOT.exists() and any(
        entry.name not in LAUNCHER_LOG_NAMES for entry in OUTPUT_ROOT.iterdir()
    )


def load_records() -> dict[str, dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in (DATA_ROOT / "mp_processed/structure_records.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    split = read_json(SPLIT_PATH)["records"]
    by_split = {str(row["material_id"]): row for row in split}
    records = {str(row["material_id"]): dict(row) for row in rows}
    if len(records) != 14060 or set(records) != set(by_split):
        raise RuntimeError("formal_14060 records and split manifest do not match")
    for material_id, row in records.items():
        item = by_split[material_id]
        if item["parent_structure_id"] != row["structure_fingerprint"]:
            raise RuntimeError(f"parent-structure mismatch: {material_id}")
        row["split"] = item["split"]
        row["parent_structure_id"] = item["parent_structure_id"]
    return records


def manifest_path(seed: int) -> Path:
    return DATA_ROOT / f"manifests/v9_method_transfer_test_seed_{seed}.csv"


def write_manifest(
    seed: int, test_ids: list[str], simulation: dict[str, Any]
) -> dict[str, Any]:
    sampler_payload = dict(simulation)
    sampler_payload["run_seed"] = seed
    sampler = PhysicsParameterSampler.from_mapping(sampler_payload)
    output = manifest_path(seed)
    rows_written = 0
    digest = hashlib.sha256()
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "profile",
                "material_id",
                "view_manifest_id",
                "simulation_seed",
                "parameters_json",
            ],
        )
        writer.writeheader()
        for profile in PROFILES:
            for row in build_offline_view_manifest(
                test_ids, sampler, profile=profile, views_per_material=1, split="test"
            ):
                value = {
                    "profile": profile,
                    "material_id": row.material_id,
                    "view_manifest_id": row.manifest_id,
                    "simulation_seed": row.simulation_seed,
                    "parameters_json": json.dumps(
                        row.parameters, sort_keys=True, separators=(",", ":")
                    ),
                }
                line = json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
                digest.update(line.encode("utf-8"))
                writer.writerow(value)
                rows_written += 1
    return {
        "path": str(output.relative_to(ROOT)),
        "sha256": sha256(output),
        "canonical_rows_sha256": digest.hexdigest().upper(),
        "rows": rows_written,
    }


def validate_contract(contract: dict[str, Any], authorization: dict[str, Any]) -> None:
    if contract.get("status") != "preregistered_locked_not_authorized":
        raise RuntimeError("preregistration status changed")
    if authorization.get("status") != "authorized_for_one_shot_simulated_test":
        raise RuntimeError("separate simulated-Test authorization is absent")
    if (
        authorization.get("preregistered_contract", {}).get("expected_status")
        != contract["status"]
    ):
        raise RuntimeError("authorization does not match contract status")
    if (
        contract["boundaries"].get("real_xrd_enabled") is not False
        or contract["selection_is_closed"].get("retraining_allowed") is not False
    ):
        raise RuntimeError("real-XRD or retraining boundary is not locked")


def preflight() -> dict[str, Any]:
    contract, authorization, simulation = (
        read_json(CONTRACT_PATH),
        read_json(AUTH_PATH),
        read_json(SIM_PATH),
    )
    validate_contract(contract, authorization)
    records = load_records()
    splits = {
        name: {r["parent_structure_id"] for r in records.values() if r["split"] == name}
        for name in ("train", "validation", "test")
    }
    if (
        len(splits["test"]) != 2109
        or splits["train"] & splits["validation"]
        or splits["train"] & splits["test"]
        or splits["validation"] & splits["test"]
    ):
        raise RuntimeError("parent-structure Test split gate failed")
    test_ids = sorted(
        material_id for material_id, row in records.items() if row["split"] == "test"
    )
    manifests = [
        write_manifest(seed, test_ids, simulation)
        for seed in contract["simulated_test_panel"]["evaluation_seeds"]
    ]
    if output_root_has_test_artifacts():
        raise RuntimeError(
            "Test output root is not empty; refusing a second Test attempt"
        )
    expected_runs = {row["run_id"]: row for row in contract["checkpoint_rule"]["runs"]}
    checkpoints = []
    for run_id, row in expected_runs.items():
        path = CHECKPOINT_ROOT / run_id / "best.ckpt"
        if not path.is_file():
            raise RuntimeError(f"missing frozen checkpoint: {path}")
        payload = torch.load(path, map_location="cpu", weights_only=False)
        if int(payload.get("epoch", -1)) != int(row["best_epoch"]) or int(
            payload.get("global_step", -1)
        ) != int(row["best_global_step"]):
            raise RuntimeError(f"checkpoint epoch/step mismatch: {run_id}")
        checkpoints.append(
            {
                "run_id": run_id,
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path),
                "epoch": payload["epoch"],
                "global_step": payload["global_step"],
            }
        )
    cache = validate_peak_cache_manifest(
        DATA_ROOT, "peak_tables_v7_reflection", records
    )
    report = {
        "schema_version": "v9-resnet-js-simulated-test-preflight-v2",
        "status": "pass",
        "contract_sha256": sha256(CONTRACT_PATH),
        "authorization_sha256": sha256(AUTH_PATH),
        "retry_authorization_sha256": sha256(RETRY_AUTH_PATH),
        "source_sha256": sha256(Path(__file__)),
        "renderer_source_sha256": renderer_source_hashes(),
        "simulation_sha256": sha256(SIM_PATH),
        "split_sha256": sha256(SPLIT_PATH),
        "peak_cache_manifest_sha256": cache["manifest_sha256"],
        "test_parent_structure_count": len(splits["test"]),
        "split_intersections_empty": True,
        "manifests": manifests,
        "checkpoints": checkpoints,
        "real_xrd_accessed": False,
        "test_inference_started": True,
        "test_inference_completed": False,
        "prior_attempt_status": "aborted_before_any_checkpoint_result",
        "authorized_identical_retry_started": False,
    }
    PREFLIGHT_PATH.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def manifest_rows(seed: int) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    with manifest_path(seed).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            result.setdefault(row["profile"], {})[row["material_id"]] = {
                "seed": int(row["simulation_seed"]),
                "parameters": json.loads(row["parameters_json"]),
            }
    return result


def cache_bindings(gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_sha256": gate["contract_sha256"],
        "simulation_sha256": gate["simulation_sha256"],
        "split_sha256": gate["split_sha256"],
        "peak_cache_manifest_sha256": gate["peak_cache_manifest_sha256"],
        "runner_source_sha256": gate["source_sha256"],
        "renderer_source_sha256": gate["renderer_source_sha256"],
        "manifests": {str(row["path"]): row["sha256"] for row in gate["manifests"]},
    }


def valid_cache_entry(entry: dict[str, Any]) -> bool:
    path = ROOT / entry["path"]
    if not path.is_file() or sha256(path) != entry.get("sha256"):
        return False
    array = np.load(path, mmap_mode="r", allow_pickle=False)
    return list(array.shape) == entry.get("shape") and str(array.dtype) == "float32"


def build_panel_cache(
    records: dict[str, dict[str, Any]],
    gate: dict[str, Any],
) -> dict[str, Any]:
    """Render each frozen Test spectrum exactly once, with file-level resume."""
    bindings = cache_bindings(gate)
    existing = read_json(PANEL_CACHE_INDEX) if PANEL_CACHE_INDEX.is_file() else {}
    if existing.get("bindings") != bindings:
        existing = {}
    test_ids = sorted(mid for mid, row in records.items() if row["split"] == "test")
    labels = [CRYSTAL_SYSTEMS.index(records[mid]["crystal_system"]) for mid in test_ids]
    index: dict[str, Any] = {
        "schema_version": "v9-resnet-js-simulated-test-panel-cache-v1",
        "bindings": bindings,
        "material_ids": test_ids,
        "labels": labels,
        "entries": dict(existing.get("entries", {})),
    }
    peaks = {
        mid: load_peak_table(
            DATA_ROOT / "mp_processed/peak_tables_v7_reflection" / f"{mid}.npz"
        )
        for mid in test_ids
    }
    factory = OnlineViewFactory(
        PhysicsParameterSampler.from_mapping({**read_json(SIM_PATH), "run_seed": 0})
    )
    from xrd_robustness.view_manifest import ViewManifestRow

    for seed in read_json(CONTRACT_PATH)["simulated_test_panel"]["evaluation_seeds"]:
        by_profile = manifest_rows(seed)
        for profile in PROFILES:
            key = f"{seed}:{profile}"
            cached = index["entries"].get(key)
            if cached and valid_cache_entry(cached):
                continue
            output = PANEL_CACHE_ROOT / f"seed_{seed}" / f"{profile}.npy"
            output.parent.mkdir(parents=True, exist_ok=True)
            partial = output.with_suffix(".partial.npy")
            if partial.exists():
                partial.unlink()
            matrix = np.lib.format.open_memmap(
                partial,
                mode="w+",
                dtype=np.float32,
                shape=(len(test_ids), ML4PXRDResNet1DConfig().input_length),
            )
            for position, material_id in enumerate(test_ids):
                value = by_profile[profile][material_id]
                row = ViewManifestRow(
                    split="test",
                    epoch=0,
                    global_step=0,
                    material_id=material_id,
                    view_id=1,
                    simulation_seed=value["seed"],
                    parameters=value["parameters"],
                )
                matrix[position] = factory.make_view_from_manifest(
                    peaks[material_id], row
                ).xrd
            matrix.flush()
            del matrix
            partial.replace(output)
            entry = {
                "path": output.relative_to(ROOT).as_posix(),
                "sha256": sha256(output),
                "shape": [len(test_ids), ML4PXRDResNet1DConfig().input_length],
                "dtype": "float32",
            }
            index["entries"][key] = entry
            write_json_atomic(PANEL_CACHE_INDEX, index)
    return index


def evaluate_cached(
    model: torch.nn.Module,
    records: dict[str, dict[str, Any]],
    cache: dict[str, Any],
    seed: int,
    *,
    batch_size: int,
    device: torch.device,
) -> dict[str, Any]:
    profiles: dict[str, Any] = {}
    model.eval()
    ids = list(cache["material_ids"])
    labels = np.asarray(cache["labels"], dtype=np.int64)
    for profile in PROFILES:
        entry = cache["entries"][f"{seed}:{profile}"]
        spectra_path = ROOT / entry["path"]
        if not spectra_path.is_file():
            raise RuntimeError(f"missing frozen panel cache entry: {seed}/{profile}")
        spectra = np.load(spectra_path, mmap_mode="r", allow_pickle=False)
        probabilities = np.empty((len(ids), len(CRYSTAL_SYSTEMS)), dtype=np.float32)
        for start in range(0, len(ids), batch_size):
            stop = min(start + batch_size, len(ids))
            host = torch.empty(
                (stop - start, spectra.shape[1]), dtype=torch.float32, pin_memory=True
            )
            host.numpy()[:] = spectra[start:stop]
            with torch.inference_mode(), torch.autocast(
                device_type="cuda", dtype=torch.float16
            ):
                logits = model(host.to(device, non_blocking=True))["logits"]
                probability = torch.softmax(logits, dim=-1).float().cpu().numpy()
            probabilities[start:stop] = probability
        predictions = probabilities.argmax(axis=1)
        metrics = classification_metrics(
            labels, predictions, probabilities=probabilities, num_classes=7
        )
        by_system = {}
        for system in CRYSTAL_SYSTEMS:
            mask = np.asarray([records[mid]["crystal_system"] == system for mid in ids])
            by_system[system] = classification_metrics(
                labels[mask], predictions[mask], num_classes=7
            )["macro_f1"]
        metrics["per_crystal_system_f1"] = by_system
        metrics["worst_class_f1"] = metrics["worst_group_f1"]
        profiles[profile] = metrics
    return profiles


def validate_execution_gate(gate: dict[str, Any]) -> None:
    if gate.get("status") != "pass" or gate.get("authorized_identical_retry_started"):
        raise RuntimeError("missing valid unused identical-retry preflight")
    if gate.get("source_sha256") != sha256(Path(__file__)):
        raise RuntimeError("runner changed after preflight; rerun preflight")
    if gate.get("renderer_source_sha256") != renderer_source_hashes():
        raise RuntimeError("renderer source changed after preflight; rerun preflight")
    retry = read_json(RETRY_AUTH_PATH)
    if retry.get("status") != "authorized_identical_retry_after_infrastructure_abort":
        raise RuntimeError("identical infrastructure-retry authorization is absent")
    if retry.get("contract_sha256") != gate["contract_sha256"]:
        raise RuntimeError("retry authorization does not match the frozen contract")
    if gate.get("prior_attempt_status") != "aborted_before_any_checkpoint_result":
        raise RuntimeError("prior aborted attempt is not represented in preflight")


def initialize_or_resume_run(gate: dict[str, Any], batch_size: int) -> dict[str, Any]:
    bindings = cache_bindings(gate)
    if RUN_STATE_PATH.is_file():
        state = read_json(RUN_STATE_PATH)
        if state.get("status") != "in_progress" or state.get("bindings") != bindings:
            raise RuntimeError("existing Test state cannot be resumed by this runner")
        if int(state.get("batch_size", -1)) != batch_size:
            raise RuntimeError(
                "resume batch size differs from the frozen in-progress attempt"
            )
        return state
    if output_root_has_test_artifacts():
        raise RuntimeError("Test output root contains an unrelated artifact")
    state = {
        "schema_version": "v9-resnet-js-simulated-test-run-state-v1",
        "status": "in_progress",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "batch_size": batch_size,
        "bindings": bindings,
        "completed_runs": [],
        "completed_run_sha256": {},
    }
    write_json_atomic(RUN_STATE_PATH, state)
    return state


def execute(batch_size: int) -> None:
    gate = read_json(PREFLIGHT_PATH)
    validate_execution_gate(gate)
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    state = initialize_or_resume_run(gate, batch_size)
    records = load_records()
    cache = build_panel_cache(records, gate)
    contract = read_json(CONTRACT_PATH)
    device = torch.device("cuda")
    raw_path = OUTPUT_ROOT / "raw_results.json"
    raw: dict[str, Any] = {
        "schema_version": "v9-resnet-js-simulated-test-output-v1",
        "runs": {},
    }
    for completed_run in state["completed_runs"]:
        completed_path = OUTPUT_ROOT / f"{completed_run}.json"
        expected_sha256 = state.get("completed_run_sha256", {}).get(completed_run)
        if not completed_path.is_file() or sha256(completed_path) != expected_sha256:
            raise RuntimeError(
                f"completed run artifact failed resume gate: {completed_run}"
            )
        raw["runs"][completed_run] = read_json(completed_path)
    for item in contract["checkpoint_rule"]["runs"]:
        run_id = item["run_id"]
        if run_id in raw["runs"]:
            continue
        model = ML4PXRDResNet1D(ML4PXRDResNet1DConfig()).to(device)
        payload = load_checkpoint(
            CHECKPOINT_ROOT / run_id / "best.ckpt", model=model, map_location="cpu"
        )
        assert_model_fingerprint(
            model, ML4PXRDResNet1DConfig(), payload["model_fingerprint"]
        )
        model.to(device)
        per_seed = {
            str(seed): evaluate_cached(
                model, records, cache, seed, batch_size=batch_size, device=device
            )
            for seed in contract["simulated_test_panel"]["evaluation_seeds"]
        }
        raw["runs"][run_id] = {
            "method": item["method"],
            "training_seed": item["training_seed"],
            "profiles_by_evaluation_seed": per_seed,
        }
        run_path = OUTPUT_ROOT / f"{run_id}.json"
        write_json_atomic(run_path, raw["runs"][run_id])
        write_json_atomic(raw_path, raw)
        state["completed_runs"] = list(raw["runs"])
        state["completed_run_sha256"][run_id] = sha256(run_path)
        write_json_atomic(RUN_STATE_PATH, state)
        del model
        torch.cuda.empty_cache()
    write_json_atomic(raw_path, raw)
    summaries = {}
    for run_id, value in raw["runs"].items():
        per_seed = value["profiles_by_evaluation_seed"]

        def avg(profile: str, field: str = "macro_f1") -> float:
            return float(
                np.mean(
                    [
                        per_seed[str(seed)][profile][field]
                        for seed in contract["simulated_test_panel"]["evaluation_seeds"]
                    ]
                )
            )

        summaries[run_id] = {
            "mean_single_factor_ood_macro_f1": float(
                np.mean(
                    [
                        avg(p)
                        for p in contract["simulated_test_panel"]["profiles"][
                            "single_factor_ood"
                        ]
                    ]
                )
            ),
            "in_range_macro_f1": avg("in_range"),
            "level0_macro_f1": avg("level0"),
            "worst_class_f1": float(
                np.mean(
                    [
                        avg(p, "worst_class_f1")
                        for p in contract["simulated_test_panel"]["profiles"][
                            "single_factor_ood"
                        ]
                    ]
                )
            ),
        }
    paired = []
    for pair in range(1, 6):
        erm, js = (
            f"seed_202607{10 + pair}_dynamic_erm",
            f"seed_202607{10 + pair}_js_lambda_60",
        )
        paired.append(
            {
                "pair_id": pair,
                **{
                    key: summaries[js][key] - summaries[erm][key]
                    for key in summaries[js]
                },
            }
        )
    values = np.asarray([row["mean_single_factor_ood_macro_f1"] for row in paired])
    rng = np.random.default_rng(20260801)
    boot = rng.choice(values, size=(20000, 5), replace=True).mean(axis=1)
    summary = {
        "schema_version": "v9-resnet-js-simulated-test-summary-v1",
        "status": "completed",
        "per_run": summaries,
        "paired_deltas": paired,
        "primary": {
            "mean_paired_delta": float(values.mean()),
            "sample_sd": float(values.std(ddof=1)),
            "bootstrap_95_percent_interval": [
                float(np.quantile(boot, 0.025)),
                float(np.quantile(boot, 0.975)),
            ],
        },
        "simulated_test_used": True,
        "real_xrd_used": False,
    }
    write_json_atomic(SUMMARY_PATH, summary)
    write_json_atomic(
        AUDIT_PATH,
        {
            "status": "completed",
            "preflight_sha256": sha256(PREFLIGHT_PATH),
            "summary_sha256": sha256(SUMMARY_PATH),
            "panel_cache_index_sha256": sha256(PANEL_CACHE_INDEX),
            "checkpoint_count": 10,
            "serial_checkpoint_evaluation": True,
            "spectra_rendered_once_and_reused": True,
            "real_xrd_accessed": False,
        },
    )
    state["status"] = "completed"
    state["completed_at"] = datetime.now(timezone.utc).isoformat()
    write_json_atomic(RUN_STATE_PATH, state)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preflight", "run"))
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()
    if args.command == "preflight":
        print(json.dumps(preflight(), indent=2, sort_keys=True))
    else:
        execute(args.batch_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
