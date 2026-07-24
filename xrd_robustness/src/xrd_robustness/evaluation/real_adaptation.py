"""Fail-closed contract audit and planning for V9 real-domain adaptation.

This module never imports a model implementation and never loads spectrum arrays.
It validates only JSON/CSV contracts and produces immutable run plans.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROLE_REQUIRED_COLUMNS = (
    "sample_id",
    "crystal_system",
    "real_domain_role",
    "adaptation_train_rank_within_class",
    "spectrum_sha256",
)

EPISODE_REQUIRED_COLUMNS = (
    "shot_budget",
    "episode_id",
    "sample_id",
    "crystal_system",
    "role",
    "spectrum_sha256",
)

EXPECTED_ROLES = {
    "adaptation_train": 21,
    "adaptation_validation": 14,
    "final_real_test": 35,
}
EXPECTED_PER_CLASS = {
    "adaptation_train": 3,
    "adaptation_validation": 2,
    "final_real_test": 5,
}
EXPECTED_SUPPORT_COUNTS = {
    ("1shot", "E1"): 7,
    ("1shot", "E2"): 7,
    ("1shot", "E3"): 7,
    ("2shot", "E1"): 14,
    ("2shot", "E2"): 14,
    ("2shot", "E3"): 14,
    ("3shot", "E1"): 21,
}


class ContractAuditError(ValueError):
    """Raised when the frozen real-adaptation contract is inconsistent."""


def sha256_file(path: str | Path) -> str:
    source = Path(path)
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _read_csv(path: Path, required_columns: Iterable[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = tuple(reader.fieldnames or ())
        missing = [column for column in required_columns if column not in fieldnames]
        if missing:
            raise ContractAuditError(f"{path.name} missing columns: {missing}")
        return list(reader)


def _resolve(project_root: Path, registered_path: str) -> Path:
    path = Path(registered_path)
    return path.resolve() if path.is_absolute() else (project_root / path).resolve()


def _normalize_rank(value: str) -> int:
    try:
        rank = int(value)
    except (TypeError, ValueError) as exc:
        raise ContractAuditError(f"invalid adaptation train rank: {value!r}") from exc
    if rank not in {1, 2, 3}:
        raise ContractAuditError(f"adaptation train rank must be 1, 2 or 3, got {rank}")
    return rank


def _validate_role_manifest(rows: list[dict[str, str]], contract: dict[str, Any]) -> dict[str, Any]:
    if len(rows) != 70:
        raise ContractAuditError(f"role manifest must contain 70 rows, got {len(rows)}")

    sample_ids = [row["sample_id"] for row in rows]
    if len(set(sample_ids)) != len(sample_ids):
        raise ContractAuditError("role manifest contains duplicate sample_id values")

    roles = Counter(row["real_domain_role"] for row in rows)
    if roles != Counter(EXPECTED_ROLES):
        raise ContractAuditError(f"role counts mismatch: {dict(roles)}")

    classes = sorted({row["crystal_system"] for row in rows})
    if len(classes) != 7:
        raise ContractAuditError(f"expected 7 crystal systems, got {classes}")

    per_class: dict[str, Counter[str]] = defaultdict(Counter)
    train_ranks: dict[str, set[int]] = defaultdict(set)
    for row in rows:
        crystal_system = row["crystal_system"]
        role = row["real_domain_role"]
        per_class[crystal_system][role] += 1
        if role == "adaptation_train":
            train_ranks[crystal_system].add(_normalize_rank(row["adaptation_train_rank_within_class"]))
        elif row["adaptation_train_rank_within_class"].strip():
            raise ContractAuditError(
                f"non-training row {row['sample_id']} unexpectedly has a train rank"
            )

    for crystal_system in classes:
        if per_class[crystal_system] != Counter(EXPECTED_PER_CLASS):
            raise ContractAuditError(
                f"per-class role counts mismatch for {crystal_system}: "
                f"{dict(per_class[crystal_system])}"
            )
        if train_ranks[crystal_system] != {1, 2, 3}:
            raise ContractAuditError(
                f"training ranks for {crystal_system} must be {{1,2,3}}, "
                f"got {train_ranks[crystal_system]}"
            )

    registered = contract["role_assignment"]
    if registered["counts"] != EXPECTED_ROLES:
        raise ContractAuditError("contract role counts differ from the frozen 21/14/35 design")
    if registered["per_crystal_system"] != EXPECTED_PER_CLASS:
        raise ContractAuditError("contract per-class counts differ from the frozen 3/2/5 design")

    return {
        "sample_count": len(rows),
        "crystal_systems": classes,
        "role_counts": dict(roles),
        "per_class_role_counts": {
            key: dict(value) for key, value in sorted(per_class.items())
        },
    }


def _validate_episode_manifest(
    rows: list[dict[str, str]],
    role_rows: list[dict[str, str]],
) -> dict[str, Any]:
    role_by_sample = {row["sample_id"]: row for row in role_rows}
    support_groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    validation_groups: dict[tuple[str, str], set[str]] = defaultdict(set)
    test_groups: dict[tuple[str, str], set[str]] = defaultdict(set)

    for row in rows:
        key = (row["shot_budget"], row["episode_id"])
        sample_id = row["sample_id"]
        if sample_id not in role_by_sample:
            raise ContractAuditError(f"episode manifest contains unknown sample_id: {sample_id}")
        source = role_by_sample[sample_id]
        if row["crystal_system"] != source["crystal_system"]:
            raise ContractAuditError(f"crystal-system mismatch for {sample_id}")
        if row["spectrum_sha256"].upper() != source["spectrum_sha256"].upper():
            raise ContractAuditError(f"spectrum hash mismatch for {sample_id}")

        role = row["role"]
        if role == "support_train":
            if source["real_domain_role"] != "adaptation_train":
                raise ContractAuditError(f"non-training sample used as support: {sample_id}")
            support_groups[key].append(row)
        elif role == "adaptation_validation":
            if source["real_domain_role"] != "adaptation_validation":
                raise ContractAuditError(f"wrong validation membership for {sample_id}")
            validation_groups[key].add(sample_id)
        elif role == "final_real_test":
            if source["real_domain_role"] != "final_real_test":
                raise ContractAuditError(f"wrong final-test membership for {sample_id}")
            test_groups[key].add(sample_id)
        else:
            raise ContractAuditError(f"unexpected episode role: {role}")

    expected_validation = {
        row["sample_id"]
        for row in role_rows
        if row["real_domain_role"] == "adaptation_validation"
    }
    expected_test = {
        row["sample_id"]
        for row in role_rows
        if row["real_domain_role"] == "final_real_test"
    }

    if set(support_groups) != set(EXPECTED_SUPPORT_COUNTS):
        raise ContractAuditError(
            f"support episode keys mismatch: {sorted(support_groups)}"
        )

    for key, expected_count in EXPECTED_SUPPORT_COUNTS.items():
        support = support_groups[key]
        if len(support) != expected_count:
            raise ContractAuditError(
                f"support count mismatch for {key}: expected {expected_count}, got {len(support)}"
            )
        per_class = Counter(row["crystal_system"] for row in support)
        expected_per_class = 1 if key[0] == "1shot" else 2 if key[0] == "2shot" else 3
        if set(per_class.values()) != {expected_per_class} or len(per_class) != 7:
            raise ContractAuditError(f"support class balance mismatch for {key}: {dict(per_class)}")
        if validation_groups[key] != expected_validation:
            raise ContractAuditError(f"validation set mismatch for {key}")
        if test_groups[key] != expected_test:
            raise ContractAuditError(f"final-test set mismatch for {key}")

    return {
        "episode_count": len(support_groups),
        "support_counts": {
            f"{budget}:{episode}": len(rows_)
            for (budget, episode), rows_ in sorted(support_groups.items())
        },
        "validation_count_per_episode": len(expected_validation),
        "final_test_count_per_episode": len(expected_test),
    }


def audit_real_adaptation_contract(
    contract_path: str | Path,
    *,
    project_root: str | Path | None = None,
    require_local_data: bool = False,
) -> dict[str, Any]:
    """Audit the frozen contract without importing a model or loading spectra."""

    contract_source = Path(contract_path).resolve()
    root = Path(project_root).resolve() if project_root is not None else contract_source.parents[1]
    errors: list[str] = []

    try:
        contract = json.loads(contract_source.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive boundary
        return {
            "schema_version": "v9-real-adaptation-audit-v1",
            "status": "fail",
            "contract_path": str(contract_source),
            "model_loaded": False,
            "spectra_loaded": False,
            "errors": [f"contract load failed: {exc}"],
        }

    checks = {
        "execution_disabled": contract.get("execution_enabled") is False,
        "final_real_test_locked": (
            contract.get("final_real_test", {}).get("enabled") is False
            and contract.get("final_real_test", {}).get("locked") is True
        ),
        "three_core_methods_registered": len(contract.get("core_methods", [])) == 3,
        "primary_adaptation_is_head_only_ce": (
            contract.get("primary_adaptation", {}).get("encoder_trainable") is False
            and contract.get("primary_adaptation", {}).get("classifier_trainable") is True
            and contract.get("primary_adaptation", {}).get("objective") == "cross_entropy_only"
            and contract.get("primary_adaptation", {}).get("js_loss_enabled") is False
            and contract.get("primary_adaptation", {}).get("residual_loss_enabled") is False
        ),
        "source_count_is_70": contract.get("source_dataset", {}).get("sample_count") == 70,
        "final_test_count_is_35": contract.get("final_real_test", {}).get("sample_count") == 35,
    }
    for name, passed in checks.items():
        if not passed:
            errors.append(f"contract check failed: {name}")

    role_path = _resolve(root, contract["role_assignment"]["split_manifest_path"])
    episode_path = _resolve(root, contract["fewshot_episodes"]["manifest_path"])
    missing = [str(path) for path in (role_path, episode_path) if not path.is_file()]

    role_report: dict[str, Any] | str = "not_run_local_manifest_missing"
    episode_report: dict[str, Any] | str = "not_run_local_manifest_missing"

    if not missing:
        try:
            role_actual_hash = sha256_file(role_path)
            role_expected_hash = contract["role_assignment"]["split_manifest_sha256"].upper()
            if role_actual_hash != role_expected_hash:
                raise ContractAuditError(
                    f"role manifest hash mismatch: expected {role_expected_hash}, got {role_actual_hash}"
                )
            episode_actual_hash = sha256_file(episode_path)
            episode_expected_hash = contract["fewshot_episodes"]["manifest_sha256"].upper()
            if episode_actual_hash != episode_expected_hash:
                raise ContractAuditError(
                    f"episode manifest hash mismatch: expected {episode_expected_hash}, got {episode_actual_hash}"
                )
            role_rows = _read_csv(role_path, ROLE_REQUIRED_COLUMNS)
            episode_rows = _read_csv(episode_path, EPISODE_REQUIRED_COLUMNS)
            role_report = _validate_role_manifest(role_rows, contract)
            episode_report = _validate_episode_manifest(episode_rows, role_rows)
        except Exception as exc:
            errors.append(str(exc))
    elif require_local_data:
        errors.append(f"required local manifests are missing: {missing}")

    if errors:
        status = "fail"
    elif missing:
        status = "locked_design_ready_local_data_missing"
    else:
        status = "locked_contract_and_manifests_pass"

    return {
        "schema_version": "v9-real-adaptation-audit-v1",
        "status": status,
        "contract_path": str(contract_source),
        "contract_sha256": sha256_file(contract_source),
        "project_root": str(root),
        "model_loaded": False,
        "spectra_loaded": False,
        "final_test_used": False,
        "checks": checks,
        "missing_local_files": missing,
        "role_manifest_audit": role_report,
        "episode_manifest_audit": episode_report,
        "errors": errors,
    }


def build_real_adaptation_plan(
    contract_path: str | Path,
    *,
    include_secondary: bool = False,
) -> dict[str, Any]:
    """Create a deterministic plan without loading data, spectra, or models."""

    contract_source = Path(contract_path).resolve()
    contract = json.loads(contract_source.read_text(encoding="utf-8"))
    methods = list(contract["core_methods"])
    seeds = list(contract.get("pretraining_seeds", [20260711, 20260712, 20260713]))

    episode_keys: list[tuple[str, str]] = []
    for shot_budget, payload in contract["fewshot_episodes"]["budgets"].items():
        if shot_budget == "0shot":
            continue
        episode_keys.extend((shot_budget, episode_id) for episode_id in payload["episodes"])

    mode_ids = ["primary_adaptation"]
    if include_secondary:
        mode_ids.append("secondary_adaptation")

    candidate_runs: list[dict[str, Any]] = []
    selected_checkpoint_groups: list[dict[str, Any]] = []
    for mode_key in mode_ids:
        mode = contract[mode_key]
        for method in methods:
            for seed in seeds:
                for shot_budget, episode_id in episode_keys:
                    group_id = f"{mode['id']}__{method}__s{seed}__{shot_budget}__{episode_id}"
                    selected_checkpoint_groups.append(
                        {
                            "group_id": group_id,
                            "mode_id": mode["id"],
                            "method_id": method,
                            "pretraining_seed": seed,
                            "shot_budget": shot_budget,
                            "episode_id": episode_id,
                            "selection_metric": mode["checkpoint_metric"],
                            "status": "planned_not_started",
                        }
                    )
                    for learning_rate in mode["learning_rate_candidates"]:
                        candidate_runs.append(
                            {
                                "run_id": f"{group_id}__lr{learning_rate:.0e}",
                                "group_id": group_id,
                                "mode_id": mode["id"],
                                "method_id": method,
                                "pretraining_seed": seed,
                                "shot_budget": shot_budget,
                                "episode_id": episode_id,
                                "learning_rate": learning_rate,
                                "status": "planned_not_started",
                            }
                        )

    zero_shot = [
        {
            "method_id": method,
            "pretraining_seed": seed,
            "status": "planned_final_stage_only",
        }
        for method in methods
        for seed in seeds
    ]

    return {
        "schema_version": "v9-real-adaptation-plan-v1",
        "status": "planned_not_started_execution_disabled",
        "contract_path": str(contract_source),
        "contract_sha256": sha256_file(contract_source),
        "model_loaded": False,
        "spectra_loaded": False,
        "include_secondary": include_secondary,
        "candidate_training_run_count": len(candidate_runs),
        "selected_checkpoint_group_count": len(selected_checkpoint_groups),
        "zero_shot_evaluation_count": len(zero_shot),
        "candidate_training_runs": candidate_runs,
        "selected_checkpoint_groups": selected_checkpoint_groups,
        "zero_shot_evaluations": zero_shot,
    }
