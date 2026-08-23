#!/usr/bin/env python3
"""Evaluate the public ResNet Dynamic ERM/JS checkpoints on simulated Test."""

from __future__ import annotations

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Sequence

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xrd_robustness.evaluation.metrics import classification_metrics  # noqa: E402
from xrd_robustness.experiment import assert_model_fingerprint, load_checkpoint  # noqa: E402
from xrd_robustness.models import ML4PXRDResNet1D, ML4PXRDResNet1DConfig  # noqa: E402
from xrd_robustness.online_views import OnlineViewFactory  # noqa: E402
from xrd_robustness.peak_cache import (  # noqa: E402
    load_peak_table,
    validate_peak_cache_manifest,
)
from xrd_robustness.physics import PhysicsParameterSampler  # noqa: E402
from xrd_robustness.structure_data import CRYSTAL_SYSTEMS  # noqa: E402
from xrd_robustness.view_manifest import (  # noqa: E402
    ViewManifestRow,
    build_offline_view_manifest,
)


EXPERIMENT_PATH = ROOT / "configs/experiment.v9.public.json"
DATA_ROOT = ROOT / "data/formal_14060"
OUTPUT_ROOT = ROOT / "outputs/v9_public_simulated_test"
CHECKPOINT_ROOT = ROOT / "outputs/v9_resnet_js_simulated_test_checkpoints/checkpoints"
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
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def renderer_source_hashes() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in RENDERER_SOURCE_PATHS
    }


def flatten_profiles(contract: dict[str, Any]) -> tuple[str, ...]:
    raw = contract.get("evaluation_profiles")
    if not isinstance(raw, dict) or not raw:
        raise ValueError("public experiment requires evaluation_profiles")
    profiles: list[str] = []
    for group, values in raw.items():
        if not isinstance(values, list) or not values:
            raise ValueError(f"evaluation profile group must be a non-empty list: {group}")
        for value in values:
            profile = str(value)
            if not profile or profile in profiles:
                raise ValueError(f"evaluation profile is empty or duplicated: {profile!r}")
            profiles.append(profile)
    return tuple(profiles)


def run_specs(contract: dict[str, Any]) -> list[dict[str, Any]]:
    runs = contract.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("public experiment requires paired runs")
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pair_index, pair in enumerate(runs, start=1):
        if not isinstance(pair, dict):
            raise ValueError("each public run pair must be a mapping")
        seed = int(pair["training_seed"])
        for method, key in (
            ("dynamic_erm", "dynamic_erm_run_id"),
            ("dynamic_js", "js_run_id"),
        ):
            run_id = str(pair.get(key, "")).strip()
            if not run_id or run_id in seen:
                raise ValueError(f"missing or duplicate public run id: {run_id!r}")
            output.append(
                {
                    "pair_index": pair_index,
                    "training_seed": seed,
                    "method": method,
                    "run_id": run_id,
                }
            )
            seen.add(run_id)
    return output


def load_public_contract(
    experiment_path: Path = EXPERIMENT_PATH,
) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    contract = read_json(experiment_path)
    if contract.get("schema_version") != "v9-public-experiment-v1":
        raise ValueError("unsupported public experiment schema")
    if contract.get("model", {}).get("architecture") != "ResNet-18-GN":
        raise ValueError("public simulated Test supports only ResNet-18-GN")
    profiles = flatten_profiles(contract)
    specs = run_specs(contract)
    if len(specs) != 10:
        raise ValueError("public simulated Test requires five paired runs")
    evaluation_seeds = contract.get("evaluation_seeds")
    if (
        not isinstance(evaluation_seeds, list)
        or len(evaluation_seeds) != 3
        or len({int(seed) for seed in evaluation_seeds}) != 3
    ):
        raise ValueError("public simulated Test requires three evaluation seeds")
    relative_simulation = contract.get("config_paths", {}).get("simulation")
    if not isinstance(relative_simulation, str) or not relative_simulation:
        raise ValueError("public experiment does not declare its simulation config")
    simulation_path = (ROOT / relative_simulation).resolve()
    simulation = read_json(simulation_path)
    available = simulation.get("profiles", {})
    missing = [profile for profile in profiles if profile not in available]
    if missing:
        raise ValueError(f"simulation config is missing profiles: {missing}")
    return contract, simulation_path, simulation


def _resolve_public_path(relative_path: str) -> Path:
    path = (ROOT / relative_path).resolve()
    if ROOT.resolve() not in path.parents:
        raise ValueError(f"public contract path leaves the project root: {relative_path}")
    return path


def load_data_contract(
    contract: dict[str, Any], *, verify_files: bool = True
) -> tuple[Path, dict[str, Any]]:
    relative_path = contract.get("config_paths", {}).get("data")
    if not isinstance(relative_path, str) or not relative_path:
        raise ValueError("public experiment does not declare its data config")
    data_path = _resolve_public_path(relative_path)
    data = read_json(data_path)
    if data.get("schema_version") != "v9t-parent-structure-data-split-v1":
        raise ValueError("unsupported public data schema")
    dataset_root = data.get("dataset_root")
    if not isinstance(dataset_root, str) or _resolve_public_path(dataset_root) != DATA_ROOT:
        raise ValueError("public data config does not resolve to the frozen data root")
    if verify_files:
        for section in ("source_records", "peak_cache", "split"):
            entry = data.get(section)
            if not isinstance(entry, dict):
                raise ValueError(f"public data config is missing {section}")
            raw_path = entry.get("path")
            expected_hash = entry.get("sha256")
            if not isinstance(raw_path, str) or not isinstance(expected_hash, str):
                raise ValueError(f"public data config has an invalid {section} binding")
            bound_path = _resolve_public_path(raw_path)
            if not bound_path.is_file() or sha256(bound_path) != expected_hash.upper():
                raise RuntimeError(f"public data binding changed: {section}")
    return data_path, data


def load_records(
    contract: dict[str, Any], data_contract: dict[str, Any] | None = None
) -> dict[str, dict[str, Any]]:
    if data_contract is None:
        _, data_contract = load_data_contract(contract)
    records_path = _resolve_public_path(str(data_contract["source_records"]["path"]))
    split_path = _resolve_public_path(str(data_contract["split"]["path"]))
    rows = [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    split_rows = read_json(split_path).get("records")
    if not isinstance(split_rows, list):
        raise RuntimeError("split manifest does not contain records")
    split_by_id = {str(row["material_id"]): row for row in split_rows}
    records = {str(row["material_id"]): dict(row) for row in rows}
    if set(records) != set(split_by_id):
        raise RuntimeError("structure records and split manifest do not match")
    observed_counts = {name: 0 for name in ("train", "validation", "test")}
    parent_sets = {name: set() for name in observed_counts}
    for material_id, record in records.items():
        split = split_by_id[material_id]
        if split["parent_structure_id"] != record["structure_fingerprint"]:
            raise RuntimeError(f"parent-structure mismatch: {material_id}")
        split_name = str(split["split"])
        record["split"] = split_name
        record["parent_structure_id"] = split["parent_structure_id"]
        observed_counts[split_name] += 1
        parent_sets[split_name].add(split["parent_structure_id"])
    expected_counts = {
        key: int(value) for key, value in contract.get("split_counts", {}).items()
        if key in observed_counts
    }
    if expected_counts != observed_counts:
        raise RuntimeError(
            f"public split counts differ: {observed_counts} != {expected_counts}"
        )
    if (
        parent_sets["train"] & parent_sets["validation"]
        or parent_sets["train"] & parent_sets["test"]
        or parent_sets["validation"] & parent_sets["test"]
    ):
        raise RuntimeError("parent structures overlap across public splits")
    return records


def preflight(
    *,
    experiment_path: Path = EXPERIMENT_PATH,
    output_root: Path = OUTPUT_ROOT,
    checkpoint_root: Path = CHECKPOINT_ROOT,
    evaluation_seeds: Sequence[int] | None = None,
) -> dict[str, Any]:
    contract, simulation_path, _ = load_public_contract(experiment_path)
    frozen_evaluation_seeds = tuple(int(seed) for seed in contract["evaluation_seeds"])
    if evaluation_seeds is not None and tuple(evaluation_seeds) != frozen_evaluation_seeds:
        raise ValueError("evaluation seeds differ from the public experiment")
    data_path, data_contract = load_data_contract(contract)
    records = load_records(contract, data_contract)
    cache = validate_peak_cache_manifest(
        DATA_ROOT,
        "peak_tables_v7_reflection",
        records,
    )
    checkpoints: list[dict[str, Any]] = []
    for spec in run_specs(contract):
        path = checkpoint_root / spec["run_id"] / "best.ckpt"
        if not path.is_file():
            raise RuntimeError(f"missing public checkpoint: {path}")
        payload = torch.load(path, map_location="cpu", weights_only=False)
        if "model" not in payload or "model_fingerprint" not in payload:
            raise RuntimeError(f"malformed public checkpoint: {path}")
        checkpoints.append(
            {
                **spec,
                "path": str(path.resolve()),
                "sha256": sha256(path),
                "epoch": int(payload.get("epoch", -1)),
                "global_step": int(payload.get("global_step", -1)),
            }
        )
    gate = {
        "schema_version": "v9-public-simulated-test-preflight-v1",
        "status": "pass",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "experiment_path": str(experiment_path.resolve()),
        "experiment_sha256": sha256(experiment_path),
        "data_config_path": str(data_path),
        "data_config_sha256": sha256(data_path),
        "source_records_sha256": sha256(
            _resolve_public_path(str(data_contract["source_records"]["path"]))
        ),
        "simulation_path": str(simulation_path),
        "simulation_sha256": sha256(simulation_path),
        "split_sha256": sha256(
            _resolve_public_path(str(data_contract["split"]["path"]))
        ),
        "peak_cache_manifest_sha256": cache["manifest_sha256"],
        "checkpoint_root": str(checkpoint_root.resolve()),
        "runner_source_sha256": sha256(Path(__file__)),
        "renderer_source_sha256": renderer_source_hashes(),
        "profiles": list(flatten_profiles(contract)),
        "evaluation_seeds": list(frozen_evaluation_seeds),
        "test_structure_count": int(contract["split_counts"]["test"]),
        "checkpoints": checkpoints,
    }
    write_json_atomic(output_root / "preflight.json", gate)
    return gate


def cache_bindings(gate: dict[str, Any]) -> dict[str, Any]:
    bindings = {
        key: gate[key]
        for key in (
            "experiment_sha256",
            "data_config_sha256",
            "source_records_sha256",
            "simulation_sha256",
            "split_sha256",
            "peak_cache_manifest_sha256",
            "runner_source_sha256",
            "renderer_source_sha256",
            "profiles",
            "evaluation_seeds",
        )
    }
    checkpoints = gate.get("checkpoints")
    if not isinstance(checkpoints, list):
        raise ValueError("simulated-Test gate is missing checkpoint bindings")
    bindings["checkpoint_sha256"] = {
        str(item["run_id"]): str(item["sha256"])
        for item in checkpoints
    }
    return bindings


def verify_checkpoint_bindings(
    gate: dict[str, Any],
    contract: dict[str, Any],
    checkpoint_root: Path,
) -> dict[str, Path]:
    if str(checkpoint_root.resolve()) != str(gate.get("checkpoint_root", "")):
        raise RuntimeError("checkpoint root differs from simulated-Test preflight")
    raw = gate.get("checkpoints")
    if not isinstance(raw, list) or len(raw) != len(run_specs(contract)):
        raise RuntimeError("simulated-Test checkpoint bindings are incomplete")
    declared = {str(item["run_id"]): item for item in raw}
    output: dict[str, Path] = {}
    for spec in run_specs(contract):
        run_id = spec["run_id"]
        item = declared.get(run_id)
        path = (checkpoint_root / run_id / "best.ckpt").resolve()
        declared_path = Path(str(item.get("path", ""))).resolve() if item else None
        if item is None or path != declared_path:
            raise RuntimeError(f"checkpoint path changed after preflight: {run_id}")
        if not path.is_file() or sha256(path) != str(item.get("sha256", "")):
            raise RuntimeError(f"checkpoint changed after preflight: {run_id}")
        output[run_id] = path
    return output


def valid_cache_entry(entry: dict[str, Any], output_root: Path = OUTPUT_ROOT) -> bool:
    path = output_root / str(entry.get("path", ""))
    if not path.is_file() or sha256(path) != entry.get("sha256"):
        return False
    array = np.load(path, mmap_mode="r", allow_pickle=False)
    return list(array.shape) == entry.get("shape") and str(array.dtype) == "float32"


def add_named_crystal_system_f1(metrics: dict[str, Any]) -> dict[str, Any]:
    values = metrics.get("per_class_f1")
    if not isinstance(values, (list, tuple)) or len(values) != len(CRYSTAL_SYSTEMS):
        raise ValueError("per_class_f1 must contain one value for every crystal system")
    return {
        **metrics,
        "per_crystal_system_f1": {
            system: float(value)
            for system, value in zip(CRYSTAL_SYSTEMS, values, strict=True)
        },
    }


def build_panel_cache(
    records: dict[str, dict[str, Any]],
    simulation: dict[str, Any],
    gate: dict[str, Any],
    *,
    output_root: Path,
) -> dict[str, Any]:
    index_path = output_root / "panel_cache/index.json"
    bindings = cache_bindings(gate)
    existing = read_json(index_path) if index_path.is_file() else {}
    if existing.get("bindings") != bindings:
        existing = {}
    test_ids = sorted(mid for mid, row in records.items() if row["split"] == "test")
    index: dict[str, Any] = {
        "schema_version": "v9-public-panel-cache-v1",
        "bindings": bindings,
        "material_ids": test_ids,
        "labels": [CRYSTAL_SYSTEMS.index(records[mid]["crystal_system"]) for mid in test_ids],
        "entries": dict(existing.get("entries", {})),
    }
    peaks = {
        material_id: load_peak_table(
            DATA_ROOT
            / "mp_processed/peak_tables_v7_reflection"
            / f"{material_id}.npz"
        )
        for material_id in test_ids
    }
    for seed in gate["evaluation_seeds"]:
        sampler = PhysicsParameterSampler.from_mapping({**simulation, "run_seed": seed})
        factory = OnlineViewFactory(sampler)
        for profile in gate["profiles"]:
            key = f"{seed}:{profile}"
            entry = index["entries"].get(key)
            if isinstance(entry, dict) and valid_cache_entry(entry, output_root):
                continue
            rows = build_offline_view_manifest(
                test_ids,
                sampler,
                profile=profile,
                views_per_material=1,
                split="test",
            )
            by_id = {row.material_id: row for row in rows}
            output = output_root / "panel_cache" / f"seed_{seed}" / f"{profile}.npy"
            output.parent.mkdir(parents=True, exist_ok=True)
            temporary = output.with_suffix(".partial.npy")
            matrix = np.lib.format.open_memmap(
                temporary,
                mode="w+",
                dtype=np.float32,
                shape=(len(test_ids), ML4PXRDResNet1DConfig().input_length),
            )
            for position, material_id in enumerate(test_ids):
                matrix[position] = factory.make_view_from_manifest(
                    peaks[material_id], by_id[material_id]
                ).xrd
            matrix.flush()
            del matrix
            temporary.replace(output)
            index["entries"][key] = {
                "path": output.relative_to(output_root).as_posix(),
                "sha256": sha256(output),
                "shape": [len(test_ids), ML4PXRDResNet1DConfig().input_length],
                "dtype": "float32",
            }
            write_json_atomic(index_path, index)
    return index


def evaluate_cached(
    model: torch.nn.Module,
    cache: dict[str, Any],
    seed: int,
    *,
    profiles: Iterable[str],
    output_root: Path,
    batch_size: int,
    device: torch.device,
) -> dict[str, Any]:
    labels = np.asarray(cache["labels"], dtype=np.int64)
    output: dict[str, Any] = {}
    model.eval()
    for profile in profiles:
        entry = cache["entries"][f"{seed}:{profile}"]
        spectra = np.load(output_root / entry["path"], mmap_mode="r", allow_pickle=False)
        probabilities = np.empty((len(labels), len(CRYSTAL_SYSTEMS)), dtype=np.float32)
        for start in range(0, len(labels), batch_size):
            stop = min(start + batch_size, len(labels))
            host = torch.from_numpy(np.array(spectra[start:stop], copy=True))
            context = (
                torch.autocast(device_type="cuda", dtype=torch.float16)
                if device.type == "cuda"
                else nullcontext()
            )
            with torch.inference_mode(), context:
                logits = model(host.to(device))["logits"]
                probabilities[start:stop] = (
                    torch.softmax(logits, dim=-1).float().cpu().numpy()
                )
        metrics = add_named_crystal_system_f1(
            classification_metrics(
                labels,
                probabilities.argmax(axis=1),
                probabilities=probabilities,
                num_classes=len(CRYSTAL_SYSTEMS),
            )
        )
        metrics["worst_class_f1"] = metrics["worst_group_f1"]
        output[str(profile)] = metrics
    return output


def initialize_or_resume_run(
    gate: dict[str, Any],
    batch_size: int,
    *,
    output_root: Path = OUTPUT_ROOT,
    device: str = "cpu",
) -> dict[str, Any]:
    state_path = output_root / "run_state.json"
    bindings = cache_bindings(gate)
    if state_path.is_file():
        state = read_json(state_path)
        if state.get("status") != "in_progress" or state.get("bindings") != bindings:
            raise RuntimeError("existing simulated-Test state cannot be resumed")
        if int(state.get("batch_size", -1)) != batch_size:
            raise RuntimeError("resume batch size differs from the in-progress run")
        if str(state.get("device")) != device:
            raise RuntimeError("resume device differs from the in-progress run")
        return state
    state = {
        "schema_version": "v9-public-simulated-test-state-v1",
        "status": "in_progress",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "batch_size": int(batch_size),
        "device": device,
        "bindings": bindings,
        "completed_runs": [],
        "completed_run_sha256": {},
    }
    write_json_atomic(state_path, state)
    return state


def _device(value: str) -> torch.device:
    if value == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(value)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    return device


def _aggregate_summary(
    raw: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    profiles = contract["evaluation_profiles"]
    evaluation_seeds = next(iter(raw["runs"].values()))["evaluation_seeds"]

    def average(run: dict[str, Any], profile_names: Sequence[str], field: str) -> float:
        return float(
            np.mean(
                [
                    run["profiles_by_evaluation_seed"][str(seed)][profile][field]
                    for seed in evaluation_seeds
                    for profile in profile_names
                ]
            )
        )

    per_run: dict[str, Any] = {}
    for run_id, run in raw["runs"].items():
        per_run[run_id] = {
            "method": run["method"],
            "training_seed": run["training_seed"],
            "level0_macro_f1": average(run, profiles["level0"], "macro_f1"),
            "in_range_macro_f1": average(run, profiles["in_range"], "macro_f1"),
            "mean_single_factor_ood_macro_f1": average(
                run, profiles["single_factor_ood"], "macro_f1"
            ),
            "worst_class_f1": average(
                run, profiles["single_factor_ood"], "worst_class_f1"
            ),
        }
    paired: list[dict[str, Any]] = []
    for pair in contract["runs"]:
        erm = per_run[pair["dynamic_erm_run_id"]]
        js = per_run[pair["js_run_id"]]
        paired.append(
            {
                "training_seed": int(pair["training_seed"]),
                **{
                    key: float(js[key] - erm[key])
                    for key in (
                        "level0_macro_f1",
                        "in_range_macro_f1",
                        "mean_single_factor_ood_macro_f1",
                        "worst_class_f1",
                    )
                },
            }
        )
    primary = np.asarray(
        [row["mean_single_factor_ood_macro_f1"] for row in paired],
        dtype=np.float64,
    )
    rng = np.random.default_rng(20260801)
    bootstrap = rng.choice(primary, size=(20_000, len(primary)), replace=True).mean(axis=1)
    return {
        "schema_version": "v9-public-simulated-test-output-v1",
        "status": "completed",
        "per_run": per_run,
        "paired_deltas": paired,
        "primary": {
            "mean_paired_delta": float(primary.mean()),
            "sample_sd": float(primary.std(ddof=1)),
            "bootstrap_95_percent_interval": [
                float(np.quantile(bootstrap, 0.025)),
                float(np.quantile(bootstrap, 0.975)),
            ],
        },
    }


def execute(
    *,
    experiment_path: Path = EXPERIMENT_PATH,
    output_root: Path = OUTPUT_ROOT,
    checkpoint_root: Path = CHECKPOINT_ROOT,
    batch_size: int = 128,
    device_name: str = "auto",
) -> dict[str, Any]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    gate_path = output_root / "preflight.json"
    if not gate_path.is_file():
        raise RuntimeError("run preflight before simulated-Test inference")
    gate = read_json(gate_path)
    contract, simulation_path, simulation = load_public_contract(experiment_path)
    data_path, data_contract = load_data_contract(contract)
    if gate.get("status") != "pass":
        raise RuntimeError("simulated-Test preflight did not pass")
    if gate.get("experiment_sha256") != sha256(experiment_path):
        raise RuntimeError("public experiment changed after preflight")
    if gate.get("data_config_sha256") != sha256(data_path):
        raise RuntimeError("public data config changed after preflight")
    records_path = _resolve_public_path(str(data_contract["source_records"]["path"]))
    split_path = _resolve_public_path(str(data_contract["split"]["path"]))
    if gate.get("source_records_sha256") != sha256(records_path):
        raise RuntimeError("source records changed after preflight")
    if gate.get("split_sha256") != sha256(split_path):
        raise RuntimeError("public split changed after preflight")
    if gate.get("simulation_sha256") != sha256(simulation_path):
        raise RuntimeError("simulation config changed after preflight")
    if gate.get("runner_source_sha256") != sha256(Path(__file__)):
        raise RuntimeError("runner changed after preflight")
    if gate.get("renderer_source_sha256") != renderer_source_hashes():
        raise RuntimeError("renderer changed after preflight")
    checkpoint_paths = verify_checkpoint_bindings(gate, contract, checkpoint_root)
    device = _device(device_name)
    records = load_records(contract, data_contract)
    cache_validation = validate_peak_cache_manifest(
        DATA_ROOT,
        "peak_tables_v7_reflection",
        records,
    )
    if gate.get("peak_cache_manifest_sha256") != cache_validation["manifest_sha256"]:
        raise RuntimeError("public peak-cache manifest changed after preflight")
    cache = build_panel_cache(records, simulation, gate, output_root=output_root)
    state = initialize_or_resume_run(
        gate,
        batch_size,
        output_root=output_root,
        device=str(device),
    )
    raw_path = output_root / "raw_results.json"
    raw: dict[str, Any] = {
        "schema_version": "v9-public-simulated-test-raw-v1",
        "runs": {},
    }
    for run_id in state["completed_runs"]:
        path = output_root / "runs" / f"{run_id}.json"
        if sha256(path) != state["completed_run_sha256"].get(run_id):
            raise RuntimeError(f"completed run failed resume hash gate: {run_id}")
        raw["runs"][run_id] = read_json(path)
    for spec in run_specs(contract):
        run_id = spec["run_id"]
        if run_id in raw["runs"]:
            continue
        model_config = ML4PXRDResNet1DConfig(model_id="18")
        model = ML4PXRDResNet1D(model_config)
        payload = load_checkpoint(
            checkpoint_paths[run_id],
            model=model,
            map_location="cpu",
        )
        assert_model_fingerprint(model, model_config, payload["model_fingerprint"])
        model.to(device)
        value = {
            **spec,
            "evaluation_seeds": list(gate["evaluation_seeds"]),
            "profiles_by_evaluation_seed": {
                str(seed): evaluate_cached(
                    model,
                    cache,
                    int(seed),
                    profiles=gate["profiles"],
                    output_root=output_root,
                    batch_size=batch_size,
                    device=device,
                )
                for seed in gate["evaluation_seeds"]
            },
        }
        raw["runs"][run_id] = value
        run_path = output_root / "runs" / f"{run_id}.json"
        write_json_atomic(run_path, value)
        write_json_atomic(raw_path, raw)
        state["completed_runs"] = list(raw["runs"])
        state["completed_run_sha256"][run_id] = sha256(run_path)
        write_json_atomic(output_root / "run_state.json", state)
        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()
    summary = _aggregate_summary(raw, contract)
    write_json_atomic(raw_path, raw)
    write_json_atomic(output_root / "summary.json", summary)
    state["status"] = "completed"
    state["completed_at"] = datetime.now(timezone.utc).isoformat()
    write_json_atomic(output_root / "run_state.json", state)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Public ResNet Dynamic ERM/JS simulated-Test runner"
    )
    parser.add_argument("command", choices=("preflight", "run"))
    parser.add_argument("--experiment-config", type=Path, default=EXPERIMENT_PATH)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--checkpoint-root", type=Path, default=CHECKPOINT_ROOT)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--device", default="auto")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "preflight":
        value = preflight(
            experiment_path=args.experiment_config.resolve(),
            output_root=args.output_root.resolve(),
            checkpoint_root=args.checkpoint_root.resolve(),
        )
    else:
        value = execute(
            experiment_path=args.experiment_config.resolve(),
            output_root=args.output_root.resolve(),
            checkpoint_root=args.checkpoint_root.resolve(),
            batch_size=args.batch_size,
            device_name=args.device,
        )
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
