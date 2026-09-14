"""Fail-closed audit and planning utilities for a retrospective RRUFF-301 replay.

The available artifacts do not establish that the historical RRUFF-301 run was
authorized before execution.  This module therefore has two deliberately narrow
jobs:

* audit the internal consistency and recorded hashes of the existing artifacts;
* generate a new deterministic support plan labelled as retrospective replay.

It does not import a model implementation, load spectrum arrays, train, or run
inference.  The execution entry point is intentionally fail-closed.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from xrd_robustness.evaluation.metrics import classification_metrics


SCHEMA_VERSION = "rruff301-retrospective-replay-v1"
EVIDENCE_ROLE = "reproducibility_replay_not_confirmatory"
LOCKED_STATUS = "RETROSPECTIVE_REPLAY_NOT_AUTHORIZED"
KNOWN_INVALID_V1_SPLIT_SHA256 = (
    "15B7E2CA94AD78E796B4FB8DF9B1EDA90A661AAB8D142BFF5C4ECCA454D72E1D"
)
CLASS_ORDER = (
    "triclinic",
    "monoclinic",
    "orthorhombic",
    "tetragonal",
    "trigonal",
    "hexagonal",
    "cubic",
)
K_VALUES = (1, 2, 5)
EPISODE_SEEDS = (42, 123, 456, 789, 1024)
TRAIN_SEEDS = ("20260711", "20260712", "20260713", "20260714", "20260715")
METHODS = ("dynamic_erm", "js_lambda_60")
MODULE_PATH = Path(__file__).resolve()

SPLIT_REQUIRED_COLUMNS = ("rruff_id", "crystal_system", "split", "rank")
MASTER_REQUIRED_COLUMNS = (
    "rruff_id",
    "crystal_system",
    "dataset_role",
    "spectrum_path",
    "spectrum_sha256",
)


class ReplayContractError(ValueError):
    """Raised when retrospective-replay inputs violate the frozen contract."""


def sha256_file(path: str | Path) -> str:
    """Return an uppercase SHA-256 digest without interpreting file contents."""

    source = Path(path)
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def canonical_json_sha256(payload: Any) -> str:
    """Hash JSON content independently of indentation and dictionary insertion order."""

    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ReplayContractError(f"could not read JSON {path}: {exc}") from exc


def _read_csv(path: Path, required_columns: Iterable[str]) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = tuple(reader.fieldnames or ())
            missing = [column for column in required_columns if column not in columns]
            if missing:
                raise ReplayContractError(f"{path.name} missing columns: {missing}")
            return list(reader)
    except ReplayContractError:
        raise
    except Exception as exc:
        raise ReplayContractError(f"could not read CSV {path}: {exc}") from exc


def _resolve_registered_path(project_root: Path, registered_path: str) -> Path:
    source = Path(registered_path)
    resolved = source.resolve() if source.is_absolute() else (project_root / source).resolve()
    if resolved != project_root and project_root not in resolved.parents:
        raise ReplayContractError(
            f"registered path escapes project root: {registered_path!r}"
        )
    return resolved


def _display_path(path: Path, project_root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def _load_contract(
    contract_path: str | Path,
    *,
    project_root: str | Path | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    source = Path(contract_path).resolve()
    root = Path(project_root).resolve() if project_root is not None else source.parents[1]
    contract = _read_json(source)
    if not isinstance(contract, dict):
        raise ReplayContractError("replay contract must be a JSON object")
    _validate_contract_semantics(contract)
    return source, root, contract


def _validate_contract_semantics(contract: Mapping[str, Any]) -> None:
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    require(contract.get("schema_version") == "rruff301-retrospective-replay-contract-v1", "unexpected schema_version")
    require(contract.get("status") == LOCKED_STATUS, "contract status must remain not authorized")
    require(contract.get("evidence_role") == EVIDENCE_ROLE, "evidence_role must be retrospective and non-confirmatory")
    require(contract.get("historical_execution_claim") is False, "historical_execution_claim must be false")

    authorization = contract.get("authorization", {})
    require(authorization.get("execution_enabled") is False, "execution_enabled must remain false")
    require(authorization.get("independent_authorization_required") is True, "independent authorization must be required")

    split = contract.get("dataset", {}).get("canonical_split", {})
    roles = split.get("roles", {})
    require(split.get("total") == 301, "canonical split total must be 301")
    require(roles.get("adaptation_pool") == {"per_class": 10, "total": 70}, "adaptation split must be 10 per class and 70 total")
    require(roles.get("locked_test") == {"per_class": 33, "total": 231}, "locked test must be 33 per class and 231 total")
    require(split.get("sha256", "").upper() != KNOWN_INVALID_V1_SPLIT_SHA256, "canonical split is bound to the known-invalid v1 hash")
    forbidden_hashes = {
        str(item.get("sha256", "")).upper()
        for item in contract.get("dataset", {}).get("forbidden_inputs", [])
    }
    require(KNOWN_INVALID_V1_SPLIT_SHA256 in forbidden_hashes, "known-invalid v1 split hash is not explicitly forbidden")

    episode_plan = contract.get("episode_plan", {})
    require(episode_plan.get("historical_plan_claim") is False, "episode plan must not claim to be the historical plan")
    require(tuple(episode_plan.get("class_order", ())) == CLASS_ORDER, "class_order differs from the replay contract")
    require(tuple(episode_plan.get("K_values", ())) == K_VALUES, "K values differ from the replay contract")
    require(tuple(episode_plan.get("episode_seeds", ())) == EPISODE_SEEDS, "episode seeds differ from the replay contract")
    require(episode_plan.get("selection_algorithm") == "rruff70_compatible_python_random_v1", "unexpected episode selection algorithm")

    protocol = contract.get("protocol", {})
    require(tuple(protocol.get("train_seeds", ())) == TRAIN_SEEDS, "training seeds differ from the replay contract")
    require(tuple(protocol.get("methods", ())) == METHODS, "methods differ from the replay contract")
    require(protocol.get("trainable_modules") == ["embedding", "head"], "trainable modules must be embedding and head only")
    require(protocol.get("trainable_parameter_count") == 1_837_063, "unexpected trainable parameter count")
    require(protocol.get("primary_metric") == "macro_f1", "primary metric must be macro_f1")
    early_stop = protocol.get("training", {}).get("early_stopping", {})
    require(early_stop.get("implementation") == "post_update_support_ce_v1", "early stopping must bind the corrected post-update implementation")
    require(early_stop.get("query_access_forbidden") is True, "query access must be forbidden during adaptation")

    checkpoints = contract.get("checkpoints", {})
    checkpoint_items = checkpoints.get("items", [])
    checkpoint_keys = {
        (str(item.get("train_seed")), item.get("method"))
        for item in checkpoint_items
    }
    expected_checkpoint_keys = {(seed, method) for seed in TRAIN_SEEDS for method in METHODS}
    require(checkpoints.get("count") == 10, "checkpoint count must be 10")
    require(len(checkpoint_items) == 10, "checkpoint manifest must contain 10 items")
    require(checkpoint_keys == expected_checkpoint_keys, "checkpoint run keys are incomplete or duplicated")
    for item in checkpoint_items:
        require(_looks_like_sha256(str(item.get("sha256", ""))), f"invalid checkpoint hash for {item.get('train_seed')} {item.get('method')}")

    artifact_counts = {
        name: item.get("record_count")
        for name, item in contract.get("existing_artifacts", {}).get("items", {}).items()
    }
    require(
        artifact_counts
        == {"fewshot_runs": 150, "predictions": 34650, "fixed200": 100, "zero_shot": 10},
        "existing artifact record counts differ from the observed frozen files",
    )

    if errors:
        raise ReplayContractError("; ".join(errors))


def _looks_like_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdefABCDEF" for character in value)


def _verify_file_hash(path: Path, expected_sha256: str, *, label: str) -> str:
    if not path.is_file():
        raise ReplayContractError(f"missing {label}: {path}")
    actual = sha256_file(path)
    expected = expected_sha256.upper()
    if actual != expected:
        raise ReplayContractError(
            f"{label} hash mismatch: expected {expected}, got {actual}"
        )
    return actual


def _parse_positive_rank(row: Mapping[str, str]) -> int:
    try:
        rank = int(row["rank"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ReplayContractError(
            f"invalid rank for {row.get('rruff_id', '<unknown>')}: {row.get('rank')!r}"
        ) from exc
    if rank < 1:
        raise ReplayContractError(f"rank must be positive for {row['rruff_id']}")
    return rank


def _validate_dataset_rows(
    contract: Mapping[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    dataset = contract["dataset"]
    split_spec = dataset["canonical_split"]
    master_spec = dataset["master_manifest"]
    split_path = _resolve_registered_path(project_root, split_spec["path"])
    master_path = _resolve_registered_path(project_root, master_spec["path"])

    split_actual_hash = _verify_file_hash(
        split_path,
        split_spec["sha256"],
        label="canonical RRUFF-301 split",
    )
    if split_actual_hash == KNOWN_INVALID_V1_SPLIT_SHA256:
        raise ReplayContractError("refusing the known-invalid RRUFF-301 v1 split")
    master_actual_hash = _verify_file_hash(
        master_path,
        master_spec["sha256"],
        label="RRUFF-371 master manifest",
    )

    split_rows = _read_csv(split_path, SPLIT_REQUIRED_COLUMNS)
    master_rows = _read_csv(master_path, MASTER_REQUIRED_COLUMNS)
    if len(split_rows) != 301:
        raise ReplayContractError(f"canonical split must contain 301 rows, got {len(split_rows)}")

    split_ids = [row["rruff_id"].strip() for row in split_rows]
    if any(not sample_id for sample_id in split_ids):
        raise ReplayContractError("canonical split contains an empty rruff_id")
    if len(set(split_ids)) != len(split_ids):
        raise ReplayContractError("canonical split contains duplicate rruff_id values")

    rows_by_role_class: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    permitted_roles = {"adaptation_pool", "locked_test"}
    for source_row in split_rows:
        row = {key: value.strip() for key, value in source_row.items()}
        role = row["split"]
        crystal_system = row["crystal_system"].lower()
        if role not in permitted_roles:
            raise ReplayContractError(f"unexpected split role {role!r} for {row['rruff_id']}")
        if crystal_system not in CLASS_ORDER:
            raise ReplayContractError(f"unexpected crystal system {crystal_system!r} for {row['rruff_id']}")
        row["crystal_system"] = crystal_system
        row["rank"] = _parse_positive_rank(row)
        rows_by_role_class[(role, crystal_system)].append(row)

    expected_per_class = {"adaptation_pool": 10, "locked_test": 33}
    for role, per_class_count in expected_per_class.items():
        for crystal_system in CLASS_ORDER:
            rows = rows_by_role_class[(role, crystal_system)]
            if len(rows) != per_class_count:
                raise ReplayContractError(
                    f"{role} count mismatch for {crystal_system}: expected {per_class_count}, got {len(rows)}"
                )
            ranks = sorted(int(row["rank"]) for row in rows)
            if ranks != list(range(1, per_class_count + 1)):
                raise ReplayContractError(
                    f"{role} ranks for {crystal_system} must be 1..{per_class_count}, got {ranks}"
                )

    master_by_id: dict[str, dict[str, str]] = {}
    for source_row in master_rows:
        row = {key: value.strip() for key, value in source_row.items()}
        sample_id = row["rruff_id"]
        if sample_id in master_by_id:
            raise ReplayContractError(f"master manifest contains duplicate rruff_id: {sample_id}")
        master_by_id[sample_id] = row

    enriched_by_role_class: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    required_dataset_role = master_spec["required_dataset_role"]
    for (role, crystal_system), rows in rows_by_role_class.items():
        for row in rows:
            sample_id = row["rruff_id"]
            master = master_by_id.get(sample_id)
            if master is None:
                raise ReplayContractError(f"split sample is absent from master manifest: {sample_id}")
            if master["crystal_system"].lower() != crystal_system:
                raise ReplayContractError(f"crystal-system mismatch for {sample_id}")
            if master["dataset_role"] != required_dataset_role:
                raise ReplayContractError(
                    f"dataset_role mismatch for {sample_id}: {master['dataset_role']!r}"
                )
            spectrum_path = master["spectrum_path"]
            relative_spectrum = Path(spectrum_path)
            if not spectrum_path or relative_spectrum.is_absolute() or ".." in relative_spectrum.parts:
                raise ReplayContractError(f"unsafe or empty spectrum path for {sample_id}")
            spectrum_hash = master["spectrum_sha256"].upper()
            if not _looks_like_sha256(spectrum_hash):
                raise ReplayContractError(f"invalid spectrum SHA-256 for {sample_id}")
            enriched_by_role_class[(role, crystal_system)].append(
                {
                    "rruff_id": sample_id,
                    "crystal_system": crystal_system,
                    "source_split_rank": int(row["rank"]),
                    "spectrum_path": spectrum_path,
                    "spectrum_sha256": spectrum_hash,
                }
            )

    for rows in enriched_by_role_class.values():
        rows.sort(key=lambda row: row["source_split_rank"])

    return {
        "split_path": split_path,
        "split_sha256": split_actual_hash,
        "master_path": master_path,
        "master_sha256": master_actual_hash,
        "rows_by_role_class": enriched_by_role_class,
    }


def _plan_sample(row: Mapping[str, Any], *, class_index: int) -> dict[str, Any]:
    return {
        "rruff_id": row["rruff_id"],
        "crystal_system": row["crystal_system"],
        "class_index": class_index,
        "source_split_rank": int(row["source_split_rank"]),
        "spectrum_path": row["spectrum_path"],
        "spectrum_sha256": row["spectrum_sha256"],
    }


def build_retrospective_episode_plan(
    contract_path: str | Path,
    *,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    """Build a deterministic *new* replay plan without loading spectra or models.

    The selection sequence mirrors the observable RRUFF-70 script: the RNG is
    reset for every ``(K, episode_seed)`` and then reused while classes are
    shuffled in ``CLASS_ORDER``.  Because the original RRUFF-301 runner and plan
    are absent, equivalence to historical support membership is intentionally
    not claimed.
    """

    contract_source, root, contract = _load_contract(
        contract_path,
        project_root=project_root,
    )
    validated = _validate_dataset_rows(contract, root)
    rows_by_role_class = validated["rows_by_role_class"]

    locked_test: list[dict[str, Any]] = []
    for class_index, crystal_system in enumerate(CLASS_ORDER):
        for row in rows_by_role_class[("locked_test", crystal_system)]:
            locked_test.append(_plan_sample(row, class_index=class_index))

    locked_test_sha256 = canonical_json_sha256(
        [{"rruff_id": row["rruff_id"], "spectrum_sha256": row["spectrum_sha256"]} for row in locked_test]
    )
    episodes: list[dict[str, Any]] = []
    supports_by_key: dict[tuple[int, int, str], set[str]] = {}

    for K in K_VALUES:
        for episode_seed in EPISODE_SEEDS:
            rng = random.Random(episode_seed)
            support: list[dict[str, Any]] = []
            for class_index, crystal_system in enumerate(CLASS_ORDER):
                pool = list(rows_by_role_class[("adaptation_pool", crystal_system)])
                rng.shuffle(pool)
                selected = pool[:K]
                supports_by_key[(K, episode_seed, crystal_system)] = {
                    row["rruff_id"] for row in selected
                }
                for support_rank, row in enumerate(selected, start=1):
                    item = _plan_sample(row, class_index=class_index)
                    item.update(
                        {
                            "role": "support",
                            "support_rank": support_rank,
                        }
                    )
                    support.append(item)

            support_sha256 = canonical_json_sha256(
                [{"rruff_id": row["rruff_id"], "spectrum_sha256": row["spectrum_sha256"]} for row in support]
            )
            episodes.append(
                {
                    "episode_id": f"K{K}_seed{episode_seed}",
                    "K": K,
                    "episode_seed": episode_seed,
                    "support_count": len(support),
                    "support_set_sha256": support_sha256,
                    "locked_test_set_sha256": locked_test_sha256,
                    "support": support,
                }
            )

    for episode_seed in EPISODE_SEEDS:
        for crystal_system in CLASS_ORDER:
            one = supports_by_key[(1, episode_seed, crystal_system)]
            two = supports_by_key[(2, episode_seed, crystal_system)]
            five = supports_by_key[(5, episode_seed, crystal_system)]
            if not one < two or not two < five:
                raise ReplayContractError(
                    f"support sets are not strictly nested for seed={episode_seed}, class={crystal_system}"
                )

    hashed_content = {
        "schema_version": SCHEMA_VERSION,
        "evidence_role": EVIDENCE_ROLE,
        "historical_plan_claim": False,
        "selection_algorithm": contract["episode_plan"]["selection_algorithm"],
        "source_split_sha256": validated["split_sha256"],
        "source_master_manifest_sha256": validated["master_sha256"],
        "locked_test": locked_test,
        "episodes": episodes,
    }
    return {
        **hashed_content,
        "status": "retrospective_replay_plan_generated_not_authorized",
        "contract_path": _display_path(contract_source, root),
        "contract_sha256": sha256_file(contract_source),
        "planner_module_path": _display_path(MODULE_PATH, root),
        "planner_module_sha256": sha256_file(MODULE_PATH),
        "plan_content_sha256": canonical_json_sha256(hashed_content),
        "model_loaded": False,
        "spectra_loaded": False,
        "locked_test_count": len(locked_test),
        "episode_count": len(episodes),
        "support_assignment_count": sum(item["support_count"] for item in episodes),
    }


def _registered_hash_specs(contract: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any], bool]]:
    dataset = contract["dataset"]
    lineage = contract["historical_lineage"]
    return [
        # The superseded preregistration is retained in Git history rather than
        # the lean working tree. Its recorded hash remains auditable, but its
        # absence must not block the retrospective consistency audit.
        ("original_preregistration", lineage["original_preregistration"], False),
        ("canonical_split", dataset["canonical_split"], True),
        ("split_manifest", dataset["split_manifest"], True),
        ("master_manifest", dataset["master_manifest"], True),
        (
            "preprocessing_contract",
            {
                "path": contract["preprocessing"]["contract_path"],
                "sha256": contract["preprocessing"]["contract_sha256"],
            },
            True,
        ),
        *[
            (f"forbidden_input_{index}", item, False)
            for index, item in enumerate(dataset.get("forbidden_inputs", []), start=1)
        ],
    ]


def _audit_registered_file(
    root: Path,
    label: str,
    spec: Mapping[str, Any],
) -> dict[str, Any]:
    path = _resolve_registered_path(root, str(spec["path"]))
    expected = str(spec["sha256"]).upper()
    if not path.is_file():
        return {
            "status": "missing",
            "path": _display_path(path, root),
            "expected_sha256": expected,
        }
    actual = sha256_file(path)
    return {
        "status": "pass" if actual == expected else "hash_mismatch",
        "path": _display_path(path, root),
        "expected_sha256": expected,
        "actual_sha256": actual,
        "label": label,
    }


def _run_key(record: Mapping[str, Any]) -> tuple[int, int, str, str]:
    try:
        return (
            int(record["K"]),
            int(record["episode_seed"]),
            str(record["train_seed"]),
            str(record["method"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ReplayContractError(f"invalid run key record: {record}") from exc


def _require_unique_complete_keys(
    records: list[Mapping[str, Any]],
    expected: set[tuple[Any, ...]],
    key_function: Any,
    *,
    label: str,
) -> dict[tuple[Any, ...], Mapping[str, Any]]:
    keyed: dict[tuple[Any, ...], Mapping[str, Any]] = {}
    for record in records:
        key = key_function(record)
        if key in keyed:
            raise ReplayContractError(f"duplicate {label} key: {key}")
        keyed[key] = record
    actual = set(keyed)
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise ReplayContractError(
            f"{label} grid mismatch: missing={missing[:5]}, unexpected={unexpected[:5]}"
        )
    return keyed


def _close(left: Any, right: Any, *, tolerance: float = 1e-12) -> bool:
    try:
        return math.isclose(float(left), float(right), rel_tol=tolerance, abs_tol=tolerance)
    except (TypeError, ValueError):
        return False


def _metric_in_unit_interval(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and 0.0 <= number <= 1.0


def _audit_result_payloads(
    paths: Mapping[str, Path],
    locked_test: list[dict[str, Any]],
) -> dict[str, Any]:
    fewshot_payload = _read_json(paths["fewshot_runs"])
    predictions_payload = _read_json(paths["predictions"])
    fixed_payload = _read_json(paths["fixed200"])
    zero_payload = _read_json(paths["zero_shot"])

    fewshot = fewshot_payload.get("results") if isinstance(fewshot_payload, dict) else None
    predictions = predictions_payload.get("predictions") if isinstance(predictions_payload, dict) else None
    fixed = fixed_payload.get("results") if isinstance(fixed_payload, dict) else None
    zero = zero_payload.get("results") if isinstance(zero_payload, dict) else None
    if not all(isinstance(records, list) for records in (fewshot, predictions, fixed, zero)):
        raise ReplayContractError("one or more result artifacts has an invalid top-level schema")

    expected_run_keys = {
        (K, episode_seed, train_seed, method)
        for K in K_VALUES
        for episode_seed in EPISODE_SEEDS
        for train_seed in TRAIN_SEEDS
        for method in METHODS
    }
    fewshot_by_key = _require_unique_complete_keys(
        fewshot,
        expected_run_keys,
        _run_key,
        label="few-shot run",
    )

    if len(predictions) != len(expected_run_keys) * 231:
        raise ReplayContractError(
            f"prediction count mismatch: expected {len(expected_run_keys) * 231}, got {len(predictions)}"
        )
    predictions_by_key: dict[tuple[int, int, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for record in predictions:
        predictions_by_key[_run_key(record)].append(record)
    if set(predictions_by_key) != expected_run_keys:
        raise ReplayContractError("prediction run grid differs from the complete few-shot grid")

    expected_test_by_id = {row["rruff_id"]: row for row in locked_test}
    expected_test_ids = set(expected_test_by_id)
    class_to_index = {name: index for index, name in enumerate(CLASS_ORDER)}
    recomputed_runs = 0
    for key, rows in predictions_by_key.items():
        if len(rows) != 231:
            raise ReplayContractError(f"prediction count for {key} must be 231, got {len(rows)}")
        sample_ids = [str(row.get("sample_id", "")) for row in rows]
        if len(set(sample_ids)) != len(sample_ids):
            raise ReplayContractError(f"duplicate prediction sample_id values for {key}")
        if set(sample_ids) != expected_test_ids:
            raise ReplayContractError(f"locked-test membership mismatch for {key}")

        labels: list[int] = []
        predicted: list[int] = []
        for row in rows:
            sample_id = str(row["sample_id"])
            expected_class = expected_test_by_id[sample_id]["crystal_system"]
            true_class = str(row.get("true_class", ""))
            try:
                true_index = int(row["true_idx"])
                pred_index = int(row["pred_idx"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ReplayContractError(f"invalid prediction indices for {key}, sample {sample_id}") from exc
            if true_class != expected_class or true_index != class_to_index[expected_class]:
                raise ReplayContractError(f"prediction truth metadata mismatch for {key}, sample {sample_id}")
            if not 0 <= pred_index < len(CLASS_ORDER):
                raise ReplayContractError(f"pred_idx outside class range for {key}, sample {sample_id}")
            if "pred_class" in row and row["pred_class"] != CLASS_ORDER[pred_index]:
                raise ReplayContractError(f"pred_class does not match pred_idx for {key}, sample {sample_id}")
            if "correct" in row and int(row["correct"]) != int(true_index == pred_index):
                raise ReplayContractError(f"correct flag mismatch for {key}, sample {sample_id}")
            labels.append(true_index)
            predicted.append(pred_index)

        metrics = classification_metrics(labels, predicted, num_classes=len(CLASS_ORDER))
        recorded = fewshot_by_key[key]
        if not _close(recorded.get("accuracy"), metrics["accuracy"]):
            raise ReplayContractError(f"accuracy mismatch for {key}")
        if not _close(recorded.get("macro_f1"), metrics["macro_f1"]):
            raise ReplayContractError(f"macro_f1 mismatch for {key}")
        recorded_per_class = recorded.get("per_class_f1")
        if not isinstance(recorded_per_class, dict):
            raise ReplayContractError(f"missing per_class_f1 for {key}")
        for class_index, crystal_system in enumerate(CLASS_ORDER):
            if not _close(recorded_per_class.get(crystal_system), metrics["per_class_f1"][class_index]):
                raise ReplayContractError(f"per-class F1 mismatch for {key}, class {crystal_system}")
        recomputed_runs += 1

    expected_fixed_keys = {
        (K, episode_seed, train_seed, method)
        for K in (1, 5)
        for episode_seed in EPISODE_SEEDS
        for train_seed in TRAIN_SEEDS
        for method in METHODS
    }
    _require_unique_complete_keys(
        fixed,
        expected_fixed_keys,
        _run_key,
        label="fixed-200 run",
    )
    for record in fixed:
        if int(record.get("optimizer_steps", -1)) != 200:
            raise ReplayContractError(f"fixed-200 run has wrong optimizer_steps: {_run_key(record)}")
        if not _metric_in_unit_interval(record.get("accuracy")) or not _metric_in_unit_interval(
            record.get("macro_f1")
        ):
            raise ReplayContractError(f"fixed-200 run has invalid recorded metrics: {_run_key(record)}")

    expected_zero_keys = {(seed, method) for seed in TRAIN_SEEDS for method in METHODS}

    def zero_key(record: Mapping[str, Any]) -> tuple[str, str]:
        try:
            return str(record["seed"]), str(record["method"])
        except KeyError as exc:
            raise ReplayContractError(f"invalid zero-shot record: {record}") from exc

    _require_unique_complete_keys(zero, expected_zero_keys, zero_key, label="zero-shot run")
    zero_shot_macro_checks = 0
    for record in zero:
        key = zero_key(record)
        if not _metric_in_unit_interval(record.get("accuracy")) or not _metric_in_unit_interval(
            record.get("macro_f1")
        ):
            raise ReplayContractError(f"zero-shot run has invalid recorded metrics: {key}")
        per_class = record.get("per_class_f1")
        if not isinstance(per_class, dict) or set(per_class) != set(CLASS_ORDER):
            raise ReplayContractError(f"zero-shot run has invalid per_class_f1: {key}")
        values = [per_class[crystal_system] for crystal_system in CLASS_ORDER]
        if not all(_metric_in_unit_interval(value) for value in values):
            raise ReplayContractError(f"zero-shot run has out-of-range per_class_f1: {key}")
        if not _close(record.get("macro_f1"), sum(float(value) for value in values) / len(values)):
            raise ReplayContractError(f"zero-shot macro_f1 is inconsistent with per_class_f1: {key}")
        zero_shot_macro_checks += 1

    return {
        "fewshot_run_count": len(fewshot),
        "prediction_count": len(predictions),
        "fixed200_run_count": len(fixed),
        "zero_shot_run_count": len(zero),
        "metrics_recomputed_from_predictions": recomputed_runs,
        "locked_test_count_per_run": 231,
        "locked_test_membership_fixed": True,
        "artifact_verification": {
            "fewshot_runs": {
                "level": "metrics_recomputed_from_prediction_rows",
                "record_count": len(fewshot),
                "accuracy_macro_f1_and_per_class_f1_recomputed": recomputed_runs,
            },
            "predictions": {
                "level": "run_grid_truth_metadata_and_locked_test_membership_verified",
                "record_count": len(predictions),
                "used_to_recompute_fewshot_metrics": True,
            },
            "fixed200": {
                "level": "hash_schema_grid_steps_and_metric_ranges_only",
                "record_count": len(fixed),
                "metrics_recomputed_from_predictions": False,
                "reason": "fixed-200 prediction rows are not present in the available artifacts",
            },
            "zero_shot": {
                "level": "hash_schema_grid_metric_ranges_and_macro_from_per_class_only",
                "record_count": len(zero),
                "macro_from_per_class_checks": zero_shot_macro_checks,
                "accuracy_recomputed_from_predictions": False,
                "reason": "zero-shot prediction rows are not present in the available artifacts",
            },
        },
    }


def audit_existing_artifacts(
    contract_path: str | Path,
    *,
    project_root: str | Path | None = None,
    require_local_artifacts: bool = True,
    verify_checkpoints: bool = False,
) -> dict[str, Any]:
    """Audit hashes and internal consistency without model or spectrum access."""

    source = Path(contract_path).resolve()
    root = Path(project_root).resolve() if project_root is not None else source.parents[1]
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "fail",
        "evidence_role": EVIDENCE_ROLE,
        "historical_execution_claim": False,
        "confirmatory_claim_supported": False,
        "model_loaded": False,
        "spectra_loaded": False,
        "query_predictions_generated": False,
        "contract_path": _display_path(source, root),
        "project_root": ".",
        "auditor_module_path": _display_path(MODULE_PATH, root),
        "auditor_module_sha256": sha256_file(MODULE_PATH),
        "file_audits": {},
        "errors": [],
    }

    try:
        contract_source, root, contract = _load_contract(source, project_root=root)
        report["contract_sha256"] = sha256_file(contract_source)
    except Exception as exc:
        report["errors"].append(str(exc))
        report["internal_artifact_consistency"] = "not_run_invalid_contract"
        report["original_execution_reproducibility"] = "incomplete"
        return report

    missing_required: list[str] = []
    for label, spec, required in _registered_hash_specs(contract):
        try:
            item_report = _audit_registered_file(root, label, spec)
        except Exception as exc:
            report["errors"].append(str(exc))
            continue
        report["file_audits"][label] = item_report
        if item_report["status"] == "hash_mismatch":
            report["errors"].append(f"{label} hash mismatch")
        elif item_report["status"] == "missing" and required:
            missing_required.append(label)

    artifact_paths: dict[str, Path] = {}
    for name, spec in contract["existing_artifacts"]["items"].items():
        try:
            item_report = _audit_registered_file(root, f"existing_artifact_{name}", spec)
            artifact_paths[name] = _resolve_registered_path(root, spec["path"])
        except Exception as exc:
            report["errors"].append(str(exc))
            continue
        report["file_audits"][f"existing_artifact_{name}"] = item_report
        if item_report["status"] == "hash_mismatch":
            report["errors"].append(f"existing artifact {name} hash mismatch")
        elif item_report["status"] == "missing":
            missing_required.append(f"existing_artifact_{name}")

    checkpoint_reports: list[dict[str, Any]] = []
    if verify_checkpoints:
        for item in contract["checkpoints"]["items"]:
            label = f"checkpoint_{item['train_seed']}_{item['method']}"
            try:
                item_report = _audit_registered_file(root, label, item)
            except Exception as exc:
                report["errors"].append(str(exc))
                continue
            checkpoint_reports.append(item_report)
            if item_report["status"] == "hash_mismatch":
                report["errors"].append(f"{label} hash mismatch")
            elif item_report["status"] == "missing":
                missing_required.append(label)
        report["checkpoint_hash_audit"] = (
            "pass" if checkpoint_reports and all(item["status"] == "pass" for item in checkpoint_reports) else "incomplete"
        )
    else:
        report["checkpoint_hash_audit"] = "not_requested"
    report["checkpoint_file_audits"] = checkpoint_reports

    result_audit: dict[str, Any] | str = "not_run_local_artifacts_missing"
    if not report["errors"] and not missing_required:
        try:
            validated = _validate_dataset_rows(contract, root)
            locked_test = [
                row
                for crystal_system in CLASS_ORDER
                for row in validated["rows_by_role_class"][("locked_test", crystal_system)]
            ]
            result_audit = _audit_result_payloads(artifact_paths, locked_test)
        except Exception as exc:
            report["errors"].append(str(exc))
            result_audit = "fail"

    report["result_artifact_audit"] = result_audit
    report["missing_required_local_files"] = sorted(set(missing_required))
    report["original_execution_reproducibility"] = "incomplete"
    report["historical_governance_reconstruction"] = "not_possible_from_available_artifacts"

    if report["errors"]:
        report["status"] = "fail"
        report["internal_artifact_consistency"] = "fail"
    elif missing_required:
        report["status"] = (
            "fail" if require_local_artifacts else "local_artifacts_missing_provenance_incomplete"
        )
        report["internal_artifact_consistency"] = "not_run_local_artifacts_missing"
        if require_local_artifacts:
            report["errors"].append(
                "required local artifacts are missing: " + ", ".join(sorted(set(missing_required)))
            )
    else:
        report["status"] = (
            "existing_artifacts_verified_at_declared_levels_provenance_incomplete"
        )
        report["internal_artifact_consistency"] = "pass_with_per_artifact_verification_levels"
    return report


def build_run_replay_refusal(
    contract_path: str | Path,
    *,
    project_root: str | Path | None = None,
    authorization_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return a refusal before any model or spectrum access.

    This v1 repair intentionally contains no trainer.  Supplying an arbitrary
    authorization path cannot enable execution: a future implementation needs a
    separately reviewed contract and authorization validator.
    """

    source = Path(contract_path).resolve()
    try:
        contract_source, _, contract = _load_contract(source, project_root=project_root)
        contract_hash = sha256_file(contract_source)
        contract_status = contract["status"]
    except Exception as exc:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "refused_invalid_contract",
            "evidence_role": EVIDENCE_ROLE,
            "reason": str(exc),
            "model_loaded": False,
            "spectra_loaded": False,
            "training_started": False,
            "inference_started": False,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "refused_execution_not_authorized",
        "evidence_role": EVIDENCE_ROLE,
        "historical_execution_claim": False,
        "reason": (
            "This contract is explicitly not authorized and this runner implements audit and planning only. "
            "A supplied path is not itself authorization."
        ),
        "contract_status": contract_status,
        "contract_sha256": contract_hash,
        "refusal_module_sha256": sha256_file(MODULE_PATH),
        "authorization_supplied": authorization_path is not None,
        "authorization_validated": False,
        "model_loaded": False,
        "spectra_loaded": False,
        "training_started": False,
        "inference_started": False,
    }
