"""Run provenance, configuration hashes, and resumable checkpoint helpers."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import torch


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def config_hash(config: Any) -> str:
    return hashlib.sha256(canonical_json(config).encode("utf-8")).hexdigest()


def file_hash(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def model_fingerprint(model: torch.nn.Module, config: Any) -> dict[str, Any]:
    return {
        "backbone_class_name": model.__class__.__name__,
        "model_config_hash": config_hash(config),
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
    }


def assert_model_fingerprint(
    model: torch.nn.Module,
    config: Any,
    expected: Mapping[str, Any],
) -> dict[str, Any]:
    actual = model_fingerprint(model, config)
    for key in ("backbone_class_name", "model_config_hash", "parameter_count"):
        if str(actual[key]) != str(expected.get(key)):
            raise ValueError(f"backbone fingerprint mismatch for {key}: {actual[key]} != {expected.get(key)}")
    return actual


def assert_checkpoint_provenance(
    payload: Mapping[str, Any],
    *,
    data_manifest_hash: str,
    view_manifest_hash: str,
    provenance: Mapping[str, Any],
) -> None:
    """Fail closed when a resume checkpoint belongs to different run inputs."""

    if str(payload.get("data_manifest_hash")) != str(data_manifest_hash):
        raise ValueError("checkpoint data manifest hash mismatch")
    if str(payload.get("view_manifest_hash")) != str(view_manifest_hash):
        raise ValueError("checkpoint view manifest hash mismatch")
    if dict(payload.get("provenance", {})) != dict(provenance):
        raise ValueError("checkpoint subset, cache, or simulation provenance mismatch")


def save_checkpoint(
    path: str | Path,
    *,
    model: torch.nn.Module,
    optimizers: Sequence[torch.optim.Optimizer],
    schedulers: Sequence[Any] = (),
    epoch: int,
    global_step: int,
    config: Any,
    data_manifest_hash: str,
    view_manifest_hash: str,
    seed: int,
    extra_modules: Mapping[str, torch.nn.Module] | None = None,
    provenance: Mapping[str, Any] | None = None,
    extra_state: Mapping[str, Any] | None = None,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": model.state_dict(),
        "extra_modules": {
            name: module.state_dict() for name, module in (extra_modules or {}).items()
        },
        "optimizers": [optimizer.state_dict() for optimizer in optimizers],
        "schedulers": [scheduler.state_dict() for scheduler in schedulers],
        "epoch": int(epoch),
        "global_step": int(global_step),
        "config": _jsonable(config),
        "model_fingerprint": model_fingerprint(model, config),
        "data_manifest_hash": str(data_manifest_hash),
        "view_manifest_hash": str(view_manifest_hash),
        "seed": int(seed),
        "provenance": _jsonable(provenance or {}),
        "extra_state": _jsonable(extra_state or {}),
        "torch_rng_state": torch.get_rng_state(),
    }
    if torch.cuda.is_available():
        payload["cuda_rng_state"] = torch.cuda.get_rng_state_all()
    torch.save(payload, path)


def load_checkpoint(
    path: str | Path,
    *,
    model: torch.nn.Module,
    optimizers: Sequence[torch.optim.Optimizer] = (),
    schedulers: Sequence[Any] = (),
    extra_modules: Mapping[str, torch.nn.Module] | None = None,
    map_location: str | torch.device = "cpu",
) -> dict[str, Any]:
    payload = torch.load(Path(path), map_location=map_location, weights_only=False)
    model.load_state_dict(payload["model"])
    for name, module in (extra_modules or {}).items():
        if name not in payload.get("extra_modules", {}):
            raise ValueError(f"checkpoint is missing extra module state: {name}")
        module.load_state_dict(payload["extra_modules"][name])
    optimizer_states = payload.get("optimizers", [])
    if optimizers and len(optimizer_states) != len(optimizers):
        raise ValueError(
            f"checkpoint optimizer count mismatch: {len(optimizer_states)} != {len(optimizers)}"
        )
    scheduler_states = payload.get("schedulers", [])
    if schedulers and len(scheduler_states) != len(schedulers):
        raise ValueError(
            f"checkpoint scheduler count mismatch: {len(scheduler_states)} != {len(schedulers)}"
        )
    for optimizer, state in zip(optimizers, optimizer_states, strict=False):
        optimizer.load_state_dict(state)
    for scheduler, state in zip(schedulers, scheduler_states, strict=False):
        scheduler.load_state_dict(state)
    if "torch_rng_state" in payload:
        # ``map_location='cuda'`` also moves serialized CPU RNG tensors.  The
        # default CPU generator requires a CPU ByteTensor, so normalize it
        # explicitly instead of making CUDA resume depend on map-location side
        # effects.
        torch.set_rng_state(payload["torch_rng_state"].detach().cpu())
    if torch.cuda.is_available() and "cuda_rng_state" in payload:
        torch.cuda.set_rng_state_all(
            [state.detach().cpu() for state in payload["cuda_rng_state"]]
        )
    return payload
