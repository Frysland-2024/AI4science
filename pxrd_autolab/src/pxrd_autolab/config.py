"""Strict configuration parsing for report-only AutoLab P0 runs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when a protocol is incomplete or asks P0 to do unsupported work."""


class BudgetError(ConfigError):
    """Raised when a configuration asks for work outside its declared budget."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def config_hash(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def read_config(path: Path) -> tuple[dict[str, Any], str, str]:
    raw = path.read_bytes()
    raw_hash = sha256_bytes(raw)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"configuration is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigError("configuration root must be a JSON object")
    return value, raw_hash, config_hash(value)


def validate_config(value: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "run_name",
        "mode",
        "data_role",
        "claim_scope",
        "budget",
        "execution",
    }
    missing = sorted(required - value.keys())
    if missing:
        raise ConfigError(f"missing required configuration fields: {', '.join(missing)}")
    if value["schema_version"] != "pxrd-autolab-p0-v1":
        raise ConfigError("unsupported schema_version")
    if value["mode"] not in {"recorded_report", "fixture_smoke"}:
        raise ConfigError(
            "P0 supports only recorded_report and fixture_smoke; training is not implemented"
        )
    if not isinstance(value["run_name"], str) or not value["run_name"].strip():
        raise ConfigError("run_name must be a non-empty string")
    for field in ("data_role", "claim_scope"):
        if not isinstance(value[field], str) or not value[field].strip():
            raise ConfigError(f"{field} must be a non-empty string")

    budget = value["budget"]
    execution = value["execution"]
    if not isinstance(budget, dict) or not isinstance(execution, dict):
        raise ConfigError("budget and execution must be JSON objects")
    max_steps = _nonnegative_integer(budget.get("max_steps"), "budget.max_steps")
    max_seconds = _positive_number(budget.get("max_seconds"), "budget.max_seconds")
    planned_steps = _nonnegative_integer(
        execution.get("planned_steps"), "execution.planned_steps"
    )
    if planned_steps > max_steps:
        raise BudgetError(
            f"planned_steps ({planned_steps}) exceeds max_steps ({max_steps})"
        )
    if planned_steps != 0:
        raise BudgetError("P0 report-only runs must use planned_steps=0; no training is allowed")

    if value["mode"] == "recorded_report":
        inputs = value.get("inputs")
        if not isinstance(inputs, dict):
            raise ConfigError("recorded_report requires an inputs object")
        for key in (
            "results_json",
            "forward_gate_json",
            "lambda_selection_json",
            "training_histories_json",
            "pilot_manifest_json",
        ):
            if not isinstance(inputs.get(key), str) or not inputs[key].strip():
                raise ConfigError(f"recorded_report requires inputs.{key}")
    else:
        fixture = value.get("fixture")
        if not isinstance(fixture, dict):
            raise ConfigError("fixture_smoke requires an explicit fixture object")
        if fixture.get("kind") != "synthetic_pipeline_fixture":
            raise ConfigError("fixture_smoke must declare kind=synthetic_pipeline_fixture")
        if fixture.get("gate_passed") is not True:
            raise ConfigError("fixture_smoke requires gate_passed=true")


def _nonnegative_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ConfigError(f"{name} must be a nonnegative number")
    return float(value)


def _nonnegative_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ConfigError(f"{name} must be a nonnegative integer")
    return value


def _positive_number(value: Any, name: str) -> float:
    number = _nonnegative_number(value, name)
    if number <= 0:
        raise ConfigError(f"{name} must be greater than zero")
    return number
