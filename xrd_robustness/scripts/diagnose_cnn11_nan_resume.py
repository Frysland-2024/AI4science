#!/usr/bin/env python
"""Replay CNN11 V10 from its saved step-18,480 checkpoint to locate the first NaN."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_simxrd_architecture_pilot import (  # noqa: E402
    PROTOCOL_PATH,
    V10_SIM_PATH,
    _assert_finite_named,
    _autocast,
    _check_gradients,
    _check_parameters_and_optimizer,
    _configure_runtime,
    _load_config,
    _make_model,
    _verify_data_bindings,
)
from xrd_robustness.online_views import TrainingMode  # noqa: E402
from xrd_robustness.parent_budget_efficiency import (  # noqa: E402
    CyclicParentSampler,
    load_split_rows,
    validate_parent_split,
)
from xrd_robustness.physics import PhysicsParameterSampler  # noqa: E402
from xrd_robustness.structure_data import CRYSTAL_SYSTEMS  # noqa: E402
from xrd_robustness.training.objectives import (  # noqa: E402
    TrainingStepConfig,
    run_training_step,
)
from xrd_robustness.training_prefetch import DynamicBatchPrefetcher  # noqa: E402
from xrd_robustness.view_manifest import build_parameter_batch  # noqa: E402


DEFAULT_CHECKPOINT = (
    PROJECT_ROOT
    / "outputs"
    / "simxrd_architecture_pilot_20261103"
    / "cnn11_v10"
    / "seed_20260711"
    / "best.ckpt"
)
DEFAULT_DATA_ROOT = PROJECT_ROOT / "data" / "formal_14060"
DEFAULT_TRACE = (
    PROJECT_ROOT
    / "reports"
    / "cnn11_v10_repair_20261103_diagnostic_v1"
    / "resume_trace_from_18480.jsonl"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _emit(handle: Any, event: str, **payload: Any) -> dict[str, Any]:
    row = {"event": event, **payload}
    encoded = json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False)
    handle.write(encoded + "\n")
    handle.flush()
    print(encoded, flush=True)
    return row


def _loss_summary(result: dict[str, torch.Tensor]) -> dict[str, float]:
    return {
        name: float(result[name].detach().float().cpu())
        for name in (
            "classification",
            "consistency",
            "total",
            "logits_first",
            "logits_second",
        )
        if name in {"classification", "consistency", "total"}
    }


def run_replay(
    *,
    checkpoint_path: Path,
    data_root: Path,
    trace_path: Path,
    through_step: int,
    device: torch.device,
    validation_cache_root: Path | None = None,
    snapshot_path: Path | None = None,
) -> dict[str, Any]:
    if trace_path.exists():
        raise FileExistsError(f"refusing to overwrite existing diagnostic trace: {trace_path}")
    summary_path = trace_path.with_suffix(".summary.json")
    if summary_path.exists():
        raise FileExistsError(f"refusing to overwrite existing diagnostic summary: {summary_path}")
    if not checkpoint_path.is_file():
        raise FileNotFoundError(checkpoint_path)
    if device.type != "cuda":
        raise ValueError("this exact checkpoint replay requires CUDA")

    protocol, _, sim_config = _load_config()
    data_bindings = _verify_data_bindings(data_root, protocol)
    checkpoint_sha = _sha256(checkpoint_path)
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    start_step = int(checkpoint["global_step"])
    seed = int(checkpoint["seed"])
    if through_step <= start_step:
        raise ValueError("through_step must be after the checkpoint step")
    if checkpoint.get("provenance", {}).get("configuration_id") != "cnn11_v10":
        raise ValueError("checkpoint is not the selected CNN11 + V10 run")
    if checkpoint.get("provenance", {}).get("simulator_version") != "v10_pseudo_voigt_caglioti":
        raise ValueError("checkpoint simulator does not match V10")
    optimizer_states = checkpoint.get("optimizers")
    if not isinstance(optimizer_states, list) or len(optimizer_states) != 1:
        raise ValueError("checkpoint does not contain exactly one AdamW state")

    runtime = _configure_runtime(device)
    expected = protocol["training"]
    model, model_config = _make_model("cnn11")
    saved_config = checkpoint["config"]
    if json.dumps(saved_config, sort_keys=True) != json.dumps(
        model_config.__dict__, sort_keys=True
    ):
        raise ValueError("CNN11 model config differs from the saved checkpoint")
    model.to(device)
    model.enable_numerical_checks(True)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(expected["learning_rate"]),
        weight_decay=float(expected["weight_decay"]),
        fused=bool(runtime["fused_adamw"]),
    )
    model.load_state_dict(checkpoint["model"], strict=True)
    optimizer.load_state_dict(optimizer_states[0])

    split_rows = load_split_rows(data_root)
    train_rows = validate_parent_split(split_rows)["train"]
    batch_size = int(expected["batch_size_parents"])
    parent_sampler = CyclicParentSampler(train_rows, seed=seed)
    for _ in range(start_step):
        parent_sampler.next_batch(batch_size)
    sampler = PhysicsParameterSampler.from_mapping({**sim_config, "run_seed": seed})

    prefetch_batches = 8
    prefetcher = DynamicBatchPrefetcher(
        worker_count=8,
        worker_native_threads=1,
        prefetch_batches=prefetch_batches,
        start_method="spawn",
        data_root=data_root,
        peak_cache_name="peak_tables_v7_reflection",
        sampler_config={**sim_config, "run_seed": seed},
        quality_gate=False,
        quality_gate_config=sim_config.get("quality_gates", {}),
        simulation_config_hash=_sha256(V10_SIM_PATH),
        simulator_version="v10_pseudo_voigt_caglioti",
        line_profile_config=sim_config["line_profile"],
        profile="train",
    )

    pending: dict[int, list[dict[str, Any]]] = {}

    def submit(step: int) -> None:
        batch = parent_sampler.next_batch(batch_size)
        pending[step] = batch
        ids = [str(row["material_id"]) for row in batch]
        parameter_rows = build_parameter_batch(
            ids,
            sampler,
            profile="train",
            epoch=0,
            global_step=step,
            split="train",
        )
        prefetcher.submit(step, ids, parameter_rows)

    trace_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    recent: list[dict[str, Any]] = []
    failure: dict[str, Any] | None = None
    completed = start_step
    try:
        with trace_path.open("x", encoding="utf-8") as handle:
            _emit(
                handle,
                "replay_started",
                checkpoint_path=str(checkpoint_path),
                checkpoint_sha256=checkpoint_sha,
                checkpoint_step=start_step,
                through_step=through_step,
                training_seed=seed,
                optimizer_step=int(
                    float(next(iter(optimizer.state.values()))["step"].detach().cpu())
                ),
                runtime=runtime,
                data_bindings=data_bindings,
                resume_method="restore_model_adamw_cpu_cuda_rng_and_replay_cyclic_parent_sampler",
            )

            for step in range(start_step, min(start_step + prefetch_batches, through_step)):
                submit(step)

            # Worker startup and manifest construction must not perturb the restored dropout RNG.
            torch.set_rng_state(checkpoint["torch_rng_state"])
            torch.cuda.set_rng_state_all(checkpoint["cuda_rng_state"])
            model.train()

            for step in range(start_step, through_step):
                rendered = prefetcher.get(step)
                batch = pending.pop(step)
                expected_ids = tuple(str(row["material_id"]) for row in batch)
                if rendered.material_ids != expected_ids:
                    raise RuntimeError("replay changed the frozen parent sampler order")
                next_step = step + prefetch_batches
                if next_step < through_step:
                    submit(next_step)

                x1 = torch.from_numpy(np.asarray(rendered.first, dtype=np.float32))
                x2 = torch.from_numpy(np.asarray(rendered.second, dtype=np.float32))
                target = torch.tensor(
                    [CRYSTAL_SYSTEMS.index(str(row["crystal_system"])) for row in batch],
                    dtype=torch.long,
                )
                x1 = x1.pin_memory().to(device, non_blocking=True)
                x2 = x2.pin_memory().to(device, non_blocking=True)
                target = target.to(device, non_blocking=True)
                optimizer.zero_grad(set_to_none=True)
                global_step = step + 1
                try:
                    with _autocast(device, runtime):
                        result = run_training_step(
                            TrainingStepConfig(
                                TrainingMode.DYNAMIC_JS,
                                lambda_js=float(expected["lambda_js"]),
                            ),
                            model,
                            x1=x1,
                            x2=x2,
                            target=target,
                        )
                except FloatingPointError as exc:
                    failure = {
                        "step": global_step,
                        "stage": "cnn11_forward_activation",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                    _emit(handle, "first_nonfinite", **failure)
                    break

                try:
                    _assert_finite_named(
                        [("input.first", x1), ("input.second", x2)],
                        context=f"simulated spectra before step {global_step}",
                    )
                    _assert_finite_named(
                        [
                            (name, result[name])
                            for name in (
                                "logits_first",
                                "logits_second",
                                "classification",
                                "consistency",
                                "total",
                            )
                        ],
                        context=f"model outputs/loss before step {global_step}",
                    )
                    result["total"].backward()
                    gradient_norm = _check_gradients(model, step=global_step)
                    optimizer.step()
                    _check_parameters_and_optimizer(model, optimizer, step=global_step)
                except FloatingPointError as exc:
                    failure = {
                        "step": global_step,
                        "stage": "loss_gradient_or_optimizer",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "losses": _loss_summary(result),
                    }
                    _emit(handle, "first_nonfinite", **failure)
                    break

                completed = global_step
                if global_step % 50 == 0 or global_step == start_step + 1:
                    row = {
                        "step": global_step,
                        "losses": _loss_summary(result),
                        "gradient_l2_norm": gradient_norm,
                        "elapsed_seconds": time.monotonic() - started,
                    }
                    recent.append(row)
                    recent = recent[-12:]
                    _emit(handle, "finite_step", **row)
            if failure is None:
                _emit(
                    handle,
                    "replay_reached_target_without_nonfinite",
                    last_step=completed,
                    elapsed_seconds=time.monotonic() - started,
                )
    finally:
        prefetcher.close()

    validation_summary = None
    if failure is None and validation_cache_root is not None:
        # This is the original, already-rendered VALIDATION panel only. No new
        # simulation and no RRUFF/Test access is permitted by this diagnostic.
        from run_simxrd_architecture_pilot import _evaluate_one_panel, TRAIN_PROFILES
        validation_seed = int(expected["validation_evaluation_seed"])
        cache_dir = (
            validation_cache_root / "evaluation_cache"
            / f"validation_v10_pseudo_voigt_caglioti_seed_{validation_seed}"
        )
        index_path = cache_dir / "panel_index.json"
        if not index_path.is_file():
            raise FileNotFoundError(f"frozen Validation panel index missing: {index_path}")
        index = json.loads(index_path.read_text(encoding="utf-8"))
        binding = index["bindings"]
        if (binding["split"] != "validation"
            or binding["simulator_version"] != "v10_pseudo_voigt_caglioti"
            or int(binding["seed"]) != validation_seed
            or binding["split_manifest_sha256"] != data_bindings["split_manifest_sha256"]):
            raise ValueError("Validation cache provenance mismatch")
        val_rows = sorted(
            [row for row in split_rows if str(row["split"]) == "validation"],
            key=lambda row: str(row["material_id"]),
        )
        labels = np.asarray(
            [CRYSTAL_SYSTEMS.index(str(row["crystal_system"])) for row in val_rows],
            dtype=np.int64,
        )
        per_profile = {}
        for profile in (*TRAIN_PROFILES, "in_range"):
            entry = index["entries"].get(profile)
            if entry is None:
                raise ValueError(f"missing frozen Validation profile {profile}")
            path = cache_dir / entry["path"]
            if _sha256(path) != entry["sha256"]:
                raise ValueError(f"Validation panel checksum mismatch: {path}")
            spectra = np.load(path, mmap_mode="r", allow_pickle=False)
            if spectra.shape != (len(labels), 3501):
                raise ValueError(f"Validation panel shape mismatch: {profile}")
            measures = _evaluate_one_panel(
                model, spectra, labels, device=device, batch_size=256,
            )
            per_profile[profile] = {
                key: float(measures[key])
                for key in ("accuracy", "macro_f1", "ece")
            }
        validation_summary = {
            "seed": validation_seed,
            "panel_index_sha256": _sha256(index_path),
            "mean_six_ood_macro_f1": float(
                np.mean([per_profile[p]["macro_f1"] for p in TRAIN_PROFILES])
            ),
            "in_range_macro_f1": per_profile["in_range"]["macro_f1"],
            "per_profile": per_profile,
            "selection_rule": "same 6-profile frozen Validation OOD mean, never RRUFF/Test",
        }

    snapshot_sha256 = None
    if failure is None and snapshot_path is not None:
        if snapshot_path.exists():
            raise FileExistsError(f"refusing to overwrite snapshot: {snapshot_path}")
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "schema_version": "cnn11-bounded-replay-inference-snapshot-v1",
                "source_checkpoint_sha256": checkpoint_sha,
                "global_step": completed,
                "model": {k: v.detach().cpu() for k, v in model.state_dict().items()},
                "model_config": model_config.__dict__,
                "validation": validation_summary,
                "training_method": "replayed-from-saved-state",
            }, snapshot_path,
        )
        snapshot_sha256 = _sha256(snapshot_path)

    summary = {
        "schema_version": "cnn11-first-nonfinite-resume-diagnostic-v1",
        "status": "reproduced_nonfinite" if failure else "finite_through_target",
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_sha,
        "checkpoint_step": start_step,
        "through_step": through_step,
        "last_finite_step": completed,
        "first_nonfinite": failure,
        "recent_finite_steps": recent,
        "training_seed": seed,
        "validation": validation_summary,
        "snapshot_path": str(snapshot_path) if snapshot_sha256 else None,
        "snapshot_sha256": snapshot_sha256,
        "resume_method": "restored model, AdamW and CPU/CUDA RNG; replayed deterministic cyclic parent sampler from frozen seed",
        "simulator_version": "v10_pseudo_voigt_caglioti",
        "amp_dtype": runtime["amp_dtype"],
        "optimizer": "AdamW fused=" + str(runtime["fused_adamw"]),
        "learning_rate": float(expected["learning_rate"]),
        "lambda_js": float(expected["lambda_js"]),
        "elapsed_seconds": time.monotonic() - started,
        "trace_path": str(trace_path),
        "data_bindings": data_bindings,
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False), flush=True)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--trace", type=Path, default=DEFAULT_TRACE)
    parser.add_argument("--through-step", type=int, default=20000)
    parser.add_argument("--validation-cache-root", type=Path)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args(argv)
    device = torch.device(args.device)
    run_replay(
        checkpoint_path=args.checkpoint.resolve(),
        data_root=args.data_root.resolve(),
        trace_path=args.trace.resolve(),
        through_step=int(args.through_step),
        device=device,
        validation_cache_root=(args.validation_cache_root.resolve() if args.validation_cache_root else None),
        snapshot_path=(args.snapshot.resolve() if args.snapshot else None),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
