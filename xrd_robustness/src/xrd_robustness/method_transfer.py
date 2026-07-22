"""Auditable planning and unified-Validation comparison for the V9-T study.

This module deliberately has no Torch dependency.  It validates the frozen study
contract, builds matched training commands, and evaluates completed run artifacts.
Training itself remains in ``scripts/train_v7.py`` so the established model and
simulation implementation are reused rather than forked.
"""

from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
from statistics import mean
from typing import Any, Mapping, Sequence

from .evaluation.statistics import hierarchical_paired_bootstrap, validate_prediction_rows

from .training_prefetch import (
    PREFETCH_RESULT_ORDER,
    PREFETCH_SHARDING_ALGORITHM,
    PREFETCH_WORKER_THREAD_POLICY,
    PREFETCH_WORKER_PEAK_CACHE,
)


METHOD_MODES = {
    "clean_erm",
    "offline_erm",
    "dynamic_erm",
    "dynamic_js",
    "dynamic_residual",
}
CORE_ROLES = {"baseline", "candidate"}


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def _project_path(project_root: Path, value: str) -> Path:
    root = project_root.resolve()
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError(f"contract path escapes project root: {value}") from error
    return path


def load_contract(path: str | Path) -> dict[str, Any]:
    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def validate_contract(contract: Mapping[str, Any]) -> None:
    if contract.get("schema_version") != "v9.1-method-transfer":
        raise ValueError("unsupported method-transfer schema_version")
    if contract.get("study_kind") != "cross_domain_method_transfer":
        raise ValueError("study_kind must be cross_domain_method_transfer")

    data = contract.get("data")
    simulation = contract.get("simulation")
    runtime = contract.get("runtime")
    experiment = contract.get("experiment")
    evaluation = contract.get("evaluation")
    tuning = contract.get("development_tuning")
    formal_hyperparameters = contract.get("formal_hyperparameters")
    metrics_and_logging = contract.get("metrics_and_logging")
    validation_comparison = contract.get("validation_comparison")
    execution = contract.get("execution_policy")
    trainer = contract.get("trainer")
    hardware_profile = contract.get("hardware_profile")
    for name, value in (
        ("data", data),
        ("simulation", simulation),
        ("runtime", runtime),
        ("experiment", experiment),
        ("evaluation", evaluation),
        ("development_tuning", tuning),
        ("formal_hyperparameters", formal_hyperparameters),
        ("metrics_and_logging", metrics_and_logging),
        ("validation_comparison", validation_comparison),
        ("execution_policy", execution),
        ("trainer", trainer),
        ("hardware_profile", hardware_profile),
    ):
        if not isinstance(value, Mapping):
            raise ValueError(f"{name} must be an object")

    if trainer.get("supporting_paths") != [
        "src/xrd_robustness/training_prefetch.py"
    ]:
        raise ValueError("trainer supporting_paths must freeze the dynamic prefetch implementation")
    if not str(hardware_profile.get("path", "")).strip() or len(
        str(hardware_profile.get("sha256", ""))
    ) != 64:
        raise ValueError("desktop hardware profile path and SHA256 must be frozen")

    if data.get("selection_split") != "validation":
        raise ValueError("method selection must use validation structures")
    if data.get("simulated_test_locked") is not True or data.get("real_test_locked") is not True:
        raise ValueError("simulated and real test sets must remain locked")
    expected_counts = data.get("expected_split_counts")
    if expected_counts != {"train": 9842, "validation": 2109, "test": 2109}:
        raise ValueError("V9-T split counts must remain 9842/2109/2109")
    if int(data.get("development_validation_count", 0)) != 2109:
        raise ValueError("unified Validation must contain all 2,109 validation structures")
    profiles = simulation.get("development_ood_profiles")
    if not isinstance(profiles, list) or not profiles or len(set(profiles)) != len(profiles):
        raise ValueError("development_ood_profiles must be a non-empty unique list")
    if simulation.get("real_xrd_used_for_selection") is not False:
        raise ValueError("real XRD cannot be used for method selection")
    if simulation.get("scientific_range_status") != "frozen":
        raise ValueError("method-transfer perturbation ranges must be frozen")
    if not simulation.get("freeze_evidence") or not simulation.get("freeze_evidence_sha256"):
        raise ValueError("frozen perturbation ranges require hashed freeze evidence")

    if experiment.get("device") != "cuda":
        raise ValueError("the formal method-transfer experiment must use CUDA")
    for key in (
        "python_executable",
        "python_version",
        "torch_version",
        "cuda_runtime",
        "gpu_name",
    ):
        if not str(runtime.get(key, "")).strip():
            raise ValueError(f"runtime.{key} must be frozen")
    if int(runtime.get("minimum_gpu_memory_mb", 0)) <= 0:
        raise ValueError("runtime.minimum_gpu_memory_mb must be positive")
    if runtime.get("pip_check_required") is not True:
        raise ValueError("the frozen runtime requires pip check")

    seeds = experiment.get("seeds")
    methods = experiment.get("methods")
    if not isinstance(seeds, list) or len(seeds) < 3 or len(set(seeds)) != len(seeds):
        raise ValueError("the controlled experiment requires at least three unique seeds")
    if not isinstance(methods, list) or len(methods) != 5:
        raise ValueError("method-transfer experiment requires two references, one baseline, and two candidates")
    method_ids = [item.get("id") for item in methods if isinstance(item, Mapping)]
    modes = [item.get("mode") for item in methods if isinstance(item, Mapping)]
    if len(method_ids) != 5 or len(set(method_ids)) != 5 or set(modes) != METHOD_MODES:
        raise ValueError("methods must contain clean, offline, dynamic, JS, and residual modes")
    baselines = [item for item in methods if item.get("role") == "baseline"]
    if len(baselines) != 1 or baselines[0].get("mode") != "dynamic_erm":
        raise ValueError(
            "dynamic_erm must be the sole strongest matched augmentation-only baseline"
        )
    references = [item for item in methods if item.get("role") == "reference"]
    candidates = [item for item in methods if item.get("role") == "candidate"]
    if {item.get("mode") for item in references} != {"clean_erm", "offline_erm"}:
        raise ValueError("clean_erm and offline_erm must be reference baselines")
    if {item.get("mode") for item in candidates} != {"dynamic_js", "dynamic_residual"}:
        raise ValueError("dynamic_js and dynamic_residual must be the two candidates")

    for key in ("batch_size", "evaluation_batch_size", "epochs", "max_optimizer_steps"):
        if int(experiment.get(key, 0)) <= 0:
            raise ValueError(f"experiment.{key} must be positive")
    if int(experiment.get("validation_interval_steps", -1)) <= 0:
        raise ValueError("validation_interval_steps must be positive")
    if experiment.get("development_only") is not True:
        raise ValueError("method-transfer experiment must keep test splits locked")
    dynamic_prefetch = experiment.get("dynamic_view_prefetch")
    if not isinstance(dynamic_prefetch, Mapping):
        raise ValueError("experiment.dynamic_view_prefetch must be an object")
    if dynamic_prefetch.get("enabled") is not True:
        raise ValueError("dynamic-view prefetch must remain enabled")
    if dynamic_prefetch.get("applies_to_modes") != [
        "clean_erm",
        "offline_erm",
        "dynamic_erm",
        "dynamic_js",
        "dynamic_residual",
    ]:
        raise ValueError("training prefetch must cover all five method modes")
    worker_processes = int(dynamic_prefetch.get("worker_processes", 0))
    if worker_processes <= 0 or worker_processes > int(experiment["batch_size"]):
        raise ValueError("dynamic-view prefetch worker_processes must be in [1, batch_size]")
    if int(dynamic_prefetch.get("prefetch_batches", 0)) <= 0:
        raise ValueError("dynamic-view prefetch prefetch_batches must be positive")
    if int(dynamic_prefetch.get("worker_native_threads", 0)) <= 0:
        raise ValueError("dynamic-view prefetch worker_native_threads must be positive")
    if dynamic_prefetch.get("worker_thread_policy") != PREFETCH_WORKER_THREAD_POLICY:
        raise ValueError("unexpected dynamic-view worker thread policy")
    if dynamic_prefetch.get("multiprocessing_start_method") != "spawn":
        raise ValueError("dynamic-view prefetch start method must be spawn")
    if dynamic_prefetch.get("sharding_algorithm") != PREFETCH_SHARDING_ALGORITHM:
        raise ValueError("unexpected dynamic-view prefetch sharding algorithm")
    if dynamic_prefetch.get("result_order") != PREFETCH_RESULT_ORDER:
        raise ValueError("unexpected dynamic-view prefetch result order")
    if dynamic_prefetch.get("worker_peak_cache") != PREFETCH_WORKER_PEAK_CACHE:
        raise ValueError("unexpected dynamic-view worker peak-cache policy")
    if (
        dynamic_prefetch.get("fixed_view_generation")
        != "frozen-manifest-process-prefetch-v1"
    ):
        raise ValueError("fixed Clean/Offline views must use process prefetch")
    if (
        dynamic_prefetch.get("clean_duplicate_policy")
        != "render-once-reuse-x1-as-x2"
    ):
        raise ValueError("Clean ERM must render once and reuse x1 as x2")
    if (
        dynamic_prefetch.get("main_process_training_peak_cache")
        != "disabled-when-prefetch-enabled"
    ):
        raise ValueError("main process must not duplicate the worker training peak cache")
    if dynamic_prefetch.get("pin_memory") is not True:
        raise ValueError("dynamic-view CUDA transfer must use pinned host memory")
    if dynamic_prefetch.get("non_blocking_h2d") is not True:
        raise ValueError("dynamic-view CUDA transfer must be non-blocking")

    tuning_candidates = tuning.get("candidates")
    if not isinstance(tuning_candidates, list) or len(tuning_candidates) != 2:
        raise ValueError("development tuning requires JS and residual candidate grids")
    expected_grids = {
        "lambda_js": [0.1, 0.3, 1.0],
        "lambda_res": [0.01, 0.1, 1.0],
    }
    observed_grids = {
        str(item.get("parameter")): list(item.get("values", []))
        for item in tuning_candidates
        if isinstance(item, Mapping)
    }
    if observed_grids != expected_grids:
        raise ValueError(f"unexpected development tuning grids: {observed_grids}")
    for key in ("epochs", "max_optimizer_steps", "validation_interval_steps"):
        if int(tuning.get(key, 0)) != int(experiment[key]):
            raise ValueError(f"development tuning must use the full formal {key} budget")
    if not isinstance(tuning.get("execution_enabled"), bool):
        raise ValueError("development tuning execution switch must be boolean")
    if bool(tuning["execution_enabled"]) != bool(
        execution.get("development_tuning_execution_enabled")
    ):
        raise ValueError("development tuning execution switches disagree")
    formal_values = formal_hyperparameters.get("values", {})
    if set(formal_values) != {"lambda_js", "lambda_res"}:
        raise ValueError("formal hyperparameters must contain lambda_js and lambda_res")
    if formal_hyperparameters.get("frozen") is False and any(
        value is not None for value in formal_values.values()
    ):
        raise ValueError("unfrozen formal hyperparameters must not contain selected values")
    if formal_hyperparameters.get("frozen") is True and any(
        value is None for value in formal_values.values()
    ):
        raise ValueError("frozen formal hyperparameters require two selected values")

    required_metrics = metrics_and_logging.get("required_metrics")
    for name in (
        "accuracy",
        "balanced_accuracy",
        "macro_f1",
        "per_class_recall",
        "confusion_matrix",
        "ece",
    ):
        if name not in required_metrics:
            raise ValueError(f"metrics contract is missing {name}")

    primary_profiles = validation_comparison.get("primary_ood_profiles")
    if not isinstance(primary_profiles, list) or not primary_profiles:
        raise ValueError("validation_comparison.primary_ood_profiles must be non-empty")
    if not set(primary_profiles).issubset(set(profiles)):
        raise ValueError("primary OOD profiles must be included in the development panel")
    combination_profiles = validation_comparison.get("secondary_combination_profiles")
    if not isinstance(combination_profiles, list) or len(combination_profiles) != 3:
        raise ValueError("Validation comparison requires three unseen-combination profiles")
    if not set(combination_profiles).issubset(set(profiles)):
        raise ValueError("combination OOD profiles must be included in the development panel")
    if int(validation_comparison.get("seed_count", 0)) != len(seeds):
        raise ValueError("Validation comparison seed count must match the formal experiment")
    bootstrap = validation_comparison.get("paired_bootstrap_contract", {})
    expected_bootstrap = {
        "independent_unit": "mother_structure_family",
        "pairing": "within_seed_same_family",
        "aggregation": "mean_paired_contrast_across_all_registered_seeds",
        "seed_only_bootstrap_forbidden": True,
        "replicates": 10000,
        "random_seed": 20260716,
        "prediction_row_schema": "configs/v9_prediction_rows.schema.json",
    }
    if bootstrap != expected_bootstrap:
        raise ValueError("Validation comparison must use the frozen family-level bootstrap contract")
    if validation_comparison.get("pass_fail_decision_forbidden") is not True:
        raise ValueError("Validation comparison must not reintroduce a pass/fail Gate")
    selectable = list(map(str, validation_comparison.get("selectable_method_ids", [])))
    expected_selectable = [
        "ordinary_dynamic_augmentation",
        "js_consistency_transfer",
        "residual_decorrelation_transfer",
    ]
    if selectable != expected_selectable:
        raise ValueError("unexpected selectable methods for unified Validation")
    narrative = contract.get("narrative_policy", {})
    if narrative.get("program_id") != "V9-T":
        raise ValueError("the active algorithm-transfer paper must use program ID V9-T")
    if narrative.get("current_program_priority") != "complete_algorithm_transfer_paper_first":
        raise ValueError("the current program priority must remain the algorithm-transfer paper")
    if narrative.get("paper_scope") != "algorithm_transfer_only":
        raise ValueError("the active paper scope must contain algorithm transfer only")
    if narrative.get("challenged_paradigm") != "augmentation_only_supervised_learning":
        raise ValueError("V9-T must challenge the augmentation-only paradigm, not dynamic augmentation itself")
    expected_augmentation_implementations = [
        "offline_pregenerated_physical_augmentation",
        "online_dynamic_physical_augmentation",
        "broader_perturbation_type_and_strength_coverage",
        "higher_physical_simulation_fidelity",
    ]
    if narrative.get("augmentation_implementations_in_scope") != expected_augmentation_implementations:
        raise ValueError("the augmentation-only paradigm must include all four registered implementations")
    expected_progression = [
        "augmentation_only_supervised_learning",
        "cross_view_prediction_consistency",
        "difference_aware_residual_class_decorrelation",
    ]
    if narrative.get("registered_method_progression") != expected_progression:
        raise ValueError("the registered paper progression has drifted")
    if narrative.get("dynamic_perturbation_role") != (
        "strong_matched_augmentation_only_baseline_and_paired_view_infrastructure"
    ):
        raise ValueError("dynamic augmentation must remain a strong matched baseline and infrastructure")
    if narrative.get("deferred_research") != "simulator_label_supervised_residual":
        raise ValueError("the simulator-supervised study must remain explicitly deferred")
    if narrative.get("deferred_program_id") != "V10":
        raise ValueError("the deferred simulator-supervised study must use program ID V10")
    if narrative.get("deferred_research_reentry_requires_explicit_user_decision") is not True:
        raise ValueError("deferred research cannot silently re-enter the active paper")
    if not isinstance(narrative.get("evidence_chain"), list) or len(
        narrative["evidence_chain"]
    ) != 4:
        raise ValueError("the paper evidence chain must contain four registered stages")
    if narrative.get("simulator_label_supervision_in_scope") is not False:
        raise ValueError("simulator-label supervision is outside the algorithm-transfer contract")
    if narrative.get("dynamic_perturbation_claimed_as_innovation") is not False:
        raise ValueError("dynamic perturbation is infrastructure, not a V9-T innovation claim")
    if narrative.get("structured_perturbation_in_scope") is not False:
        raise ValueError("structured perturbation must remain outside V9-T")
    expected_outcomes = {
        "residual_stably_beats_dynamic_and_js",
        "residual_effective_js_comparison_inconclusive",
        "js_effective_residual_no_extra_gain",
        "both_effective_no_clear_difference",
        "neither_effective",
    }
    if set(narrative.get("paper_outcome_branches", {})) != expected_outcomes:
        raise ValueError("V9-T paper outcome branches are incomplete")
    if execution.get("real_test_enabled") is not False:
        raise ValueError("real test must be disabled during method selection")
    if execution.get("simulated_test_enabled") is not False:
        raise ValueError("simulated test must be disabled during method selection")


def audit_contract_assets(contract: Mapping[str, Any], project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    data = contract["data"]
    simulation = contract["simulation"]
    data_root = _project_path(root, str(data["root"]))
    split_manifest = _project_path(root, str(data["split_manifest"]))
    data_config = _project_path(root, str(data["data_config"]))
    split_audit = _project_path(root, str(data["split_audit"]))
    simulation_path = _project_path(root, str(simulation["path"]))
    freeze_evidence = _project_path(root, str(simulation["freeze_evidence"]))
    peak_manifest = _project_path(root, str(data["peak_cache_manifest"]))
    trainer = _project_path(root, str(contract["trainer"]["path"]))
    trainer_supporting_paths = [
        _project_path(root, str(value))
        for value in contract["trainer"]["supporting_paths"]
    ]
    validation_manifest = _project_path(
        root, str(data["development_validation_manifest"])
    )
    parameter_table = _project_path(root, str(simulation["parameter_table"]))
    evaluation_contract = _project_path(root, str(contract["evaluation"]["path"]))
    hardware_profile_path = _project_path(root, str(contract["hardware_profile"]["path"]))

    required = [
        data_root,
        split_manifest,
        data_config,
        split_audit,
        simulation_path,
        freeze_evidence,
        peak_manifest,
        trainer,
        *trainer_supporting_paths,
        validation_manifest,
        parameter_table,
        evaluation_contract,
        hardware_profile_path,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise ValueError(f"missing method-transfer assets: {missing}")

    hashes = {
        "split_manifest": sha256_file(split_manifest),
        "data_config": sha256_file(data_config),
        "split_audit": sha256_file(split_audit),
        "simulation_config": sha256_file(simulation_path),
        "freeze_evidence": sha256_file(freeze_evidence),
        "peak_cache_manifest": sha256_file(peak_manifest),
        "trainer": sha256_file(trainer),
        "trainer_supporting_paths": {
            str(path.relative_to(root)).replace("\\", "/"): sha256_file(path)
            for path in trainer_supporting_paths
        },
        "development_validation_manifest": sha256_file(validation_manifest),
        "parameter_table": sha256_file(parameter_table),
        "evaluation_contract": sha256_file(evaluation_contract),
        "hardware_profile": sha256_file(hardware_profile_path),
    }
    expected_hashes = {
        "split_manifest": str(data["split_manifest_sha256"]).upper(),
        "data_config": str(data["data_config_sha256"]).upper(),
        "split_audit": str(data["split_audit_sha256"]).upper(),
        "simulation_config": str(simulation["sha256"]).upper(),
        "freeze_evidence": str(simulation["freeze_evidence_sha256"]).upper(),
        "peak_cache_manifest": str(data["peak_cache_manifest_sha256"]).upper(),
        "development_validation_manifest": str(
            data["development_validation_manifest_sha256"]
        ).upper(),
        "parameter_table": str(simulation["parameter_table_sha256"]).upper(),
        "evaluation_contract": str(contract["evaluation"]["sha256"]).upper(),
        "hardware_profile": str(contract["hardware_profile"]["sha256"]).upper(),
    }
    mismatches = {
        key: {"expected": expected, "actual": hashes[key]}
        for key, expected in expected_hashes.items()
        if hashes[key] != expected
    }
    if mismatches:
        raise ValueError(f"method-transfer asset hash mismatch: {mismatches}")

    hardware_payload = json.loads(hardware_profile_path.read_text(encoding="utf-8"))
    if hardware_payload.get("schema_version") != "v9-desktop-hardware-profile-v1":
        raise ValueError("unsupported desktop hardware profile")
    target = hardware_payload.get("target", {})
    applied = hardware_payload.get("applied", {})
    prefetch_profile = applied.get("dynamic_prefetch", {})
    main_process = applied.get("main_process", {})
    cuda_math = applied.get("cuda_math", {})
    optimizer_profile = applied.get("optimizer", {})
    amp_profile = applied.get("automatic_mixed_precision", {})
    compile_profile = applied.get("torch_compile", {})
    parallel_scheduler = applied.get("parallel_run_scheduler", {})
    measurement_gate = hardware_payload.get("desktop_measurement_gate", {})
    measurement_implementation = measurement_gate.get("implementation", {})
    expected_measurement_implementation = {
        "environment_bootstrap",
        "runtime_environment_audit",
        "first_boot_orchestrator",
        "hardware_audit",
        "prefetch_matrix_audit",
        "evaluation_batch_audit",
        "acceleration_audit",
        "readiness_audit",
    }
    if set(measurement_implementation) != expected_measurement_implementation:
        raise ValueError("desktop measurement implementation paths must be complete")
    missing_measurement_implementation = [
        str(_project_path(root, str(path)))
        for path in measurement_implementation.values()
        if not _project_path(root, str(path)).is_file()
    ]
    if missing_measurement_implementation:
        raise ValueError(
            "missing desktop measurement implementations: "
            f"{missing_measurement_implementation}"
        )
    if "torch_compile_graph_executed" not in measurement_gate.get(
        "required_checks", []
    ):
        raise ValueError("desktop measurement gate must prove an actual compiled graph")
    if target.get("physical_cores") != 6 or target.get("logical_threads") != 12:
        raise ValueError("desktop CPU profile must freeze the Ryzen 5 9600X 6C/12T layout")
    if target.get("gpu") != contract["runtime"]["gpu_name"]:
        raise ValueError("desktop hardware profile GPU does not match the frozen runtime")
    if int(applied.get("evaluation_batch_size", 0)) != int(
        contract["experiment"]["evaluation_batch_size"]
    ):
        raise ValueError("hardware profile evaluation batch size does not match experiment")
    expected_prefetch = contract["experiment"]["dynamic_view_prefetch"]
    for key in (
        "worker_processes",
        "worker_native_threads",
        "prefetch_batches",
        "multiprocessing_start_method",
        "applies_to_modes",
        "fixed_view_generation",
        "clean_duplicate_policy",
        "main_process_training_peak_cache",
        "pin_memory",
        "non_blocking_h2d",
    ):
        if prefetch_profile.get(key) != expected_prefetch.get(key):
            raise ValueError(f"hardware profile dynamic prefetch mismatch: {key}")
    if int(main_process.get("intraop_threads", 0)) <= 0 or int(
        main_process.get("interop_threads", 0)
    ) <= 0:
        raise ValueError("hardware profile main-process thread counts must be positive")
    if cuda_math.get("float32_matmul_precision") not in {"highest", "high", "medium"}:
        raise ValueError("hardware profile float32 matmul precision is invalid")
    if optimizer_profile.get("name") != "AdamW" or optimizer_profile.get("fused") is not True:
        raise ValueError("desktop hardware profile must use fused AdamW")
    if amp_profile != {
        "enabled": True,
        "dtype": "bfloat16",
        "gradient_scaler": False,
        "fallback_to_float32": True,
    }:
        raise ValueError("desktop hardware profile must register BF16 AMP with FP32 fallback")
    if compile_profile.get("enabled") is not True:
        raise ValueError("desktop hardware profile must enable torch.compile")
    if compile_profile.get("backend") != "inductor":
        raise ValueError("desktop hardware profile must use the Inductor compile backend")
    if compile_profile.get("mode") not in {"default", "reduce-overhead", "max-autotune"}:
        raise ValueError("desktop hardware profile torch.compile mode is invalid")
    if compile_profile.get("fallback_to_eager") is not True:
        raise ValueError("desktop hardware profile must keep the eager fallback enabled")
    if int(applied.get("run_concurrency", 0)) != 2:
        raise ValueError("desktop hardware profile must register two concurrent runs")
    if parallel_scheduler != {
        "strategy": "bounded-pairs-v1",
        "concurrent_run_prefetch_workers": 4,
        "serial_tail_prefetch_workers": 8,
        "failure_policy": "finish-active-pair-then-stop",
        "registry_write_policy": "parent-process-only",
    }:
        raise ValueError("desktop parallel-run scheduler does not match the registered policy")
    if (
        int(parallel_scheduler["concurrent_run_prefetch_workers"])
        * int(applied["run_concurrency"])
        != int(prefetch_profile["worker_processes"])
    ):
        raise ValueError("parallel-run worker budget must equal the registered eight-worker budget")

    counts: Counter[str] = Counter()
    material_ids: set[str] = set()
    fingerprints: set[str] = set()
    family_splits: dict[str, set[str]] = {}
    with split_manifest.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            material_id = str(row["material_id"])
            fingerprint = str(row["structure_fingerprint"])
            family_id = str(row.get("family_id", "")).strip()
            if material_id in material_ids:
                raise ValueError(f"duplicate material_id in split manifest: {material_id}")
            if fingerprint in fingerprints:
                raise ValueError(f"duplicate structure fingerprint in split manifest: {fingerprint}")
            material_ids.add(material_id)
            fingerprints.add(fingerprint)
            split = str(row["split"])
            if not family_id:
                raise ValueError("family-aware split manifest is missing family_id")
            family_splits.setdefault(family_id, set()).add(split)
            counts[split] += 1
    actual_counts = dict(counts)
    if actual_counts != dict(data["expected_split_counts"]):
        raise ValueError(
            f"split count mismatch: {actual_counts} != {data['expected_split_counts']}"
        )
    crossing_families = sorted(
        family_id for family_id, splits in family_splits.items() if len(splits) > 1
    )
    if crossing_families:
        raise ValueError(f"structure families cross splits: {crossing_families[:3]}")

    def read_validation(path: Path) -> tuple[set[str], set[str]]:
        subset_ids: set[str] = set()
        subset_systems: set[str] = set()
        with path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                material_id = str(row["material_id"])
                if material_id in subset_ids:
                    raise ValueError("duplicate material ID in unified Validation manifest")
                if row.get("source_split") != "validation":
                    raise ValueError("unified Validation manifest contains a non-validation row")
                if row.get("development_role") != "unified_validation":
                    raise ValueError("unified Validation manifest role mismatch")
                subset_ids.add(material_id)
                subset_systems.add(str(row["crystal_system"]))
        if len(subset_systems) != 7:
            raise ValueError("unified Validation manifest does not cover seven crystal systems")
        return subset_ids, subset_systems

    validation_manifest_ids, _ = read_validation(validation_manifest)
    with split_manifest.open("r", encoding="utf-8", newline="") as handle:
        validation_ids = {
            row["material_id"]
            for row in csv.DictReader(handle)
            if row["split"] == "validation"
        }
    if validation_manifest_ids != validation_ids:
        raise ValueError("unified Validation manifest does not equal the validation split")
    if len(validation_manifest_ids) != int(data["development_validation_count"]):
        raise ValueError("unified Validation count mismatch")

    simulation_config = json.loads(simulation_path.read_text(encoding="utf-8"))
    freeze_report = json.loads(freeze_evidence.read_text(encoding="utf-8"))
    if simulation_config.get("status") != "formal_frozen":
        raise ValueError("simulation config is not marked formal_frozen")
    if freeze_report.get("status") != "passed":
        raise ValueError("perturbation freeze evidence did not pass")
    if str(freeze_report.get("config", {}).get("sha256", "")).upper() != hashes[
        "simulation_config"
    ]:
        raise ValueError("freeze evidence does not match the simulation config")
    available_profiles = set(simulation_config.get("profiles", {}))
    required_profiles = {
        str(simulation["train_profile"]),
        str(simulation["in_range_profile"]),
        *map(str, simulation["development_ood_profiles"]),
    }
    missing_profiles = sorted(required_profiles - available_profiles)
    if missing_profiles:
        raise ValueError(f"simulation config is missing profiles: {missing_profiles}")
    if "--development-only" not in trainer.read_text(encoding="utf-8"):
        raise ValueError("training entry point does not implement the simulated-test lock")

    evaluation_payload = json.loads(evaluation_contract.read_text(encoding="utf-8"))
    if evaluation_payload.get("status") != "frozen_engineering_contract":
        raise ValueError("evaluation contract is not frozen")
    if evaluation_payload["simulation"]["sha256"].upper() != hashes["simulation_config"]:
        raise ValueError("evaluation contract points to a different simulation config")
    if evaluation_payload["source_split"]["sha256"].upper() != hashes["split_manifest"]:
        raise ValueError("evaluation contract points to a different family-aware split")
    unified_validation = evaluation_payload["development"]["unified_validation"]
    if unified_validation["sha256"].upper() != hashes["development_validation_manifest"]:
        raise ValueError("evaluation contract points to a different unified Validation manifest")
    if evaluation_payload["simulated_test"]["enabled"] is not False:
        raise ValueError("simulated test is not locked in the evaluation contract")
    if evaluation_payload["real_test"]["enabled"] is not False:
        raise ValueError("real test is not locked in the evaluation contract")

    return {
        "status": "passed",
        "contract_status": contract["status"],
        "hashes": hashes,
        "split_counts": actual_counts,
        "unique_material_ids": len(material_ids),
        "unique_structure_fingerprints": len(fingerprints),
        "unique_structure_families": len(family_splits),
        "cross_split_family_count": len(crossing_families),
        "development_profiles": sorted(required_profiles),
        "scientific_range_status": "frozen",
        "freeze_evidence_status": "passed",
        "simulated_test_locked": True,
        "real_test_locked": True,
        "formal_development_run_count": len(contract["experiment"]["methods"])
        * len(contract["experiment"]["seeds"]),
        "core_comparison_run_count": 3 * len(contract["experiment"]["seeds"]),
        "development_tuning_run_count": 1
        + sum(len(item["values"]) for item in contract["development_tuning"]["candidates"]),
        "development_validation_count": len(validation_manifest_ids),
        "experiment_execution_enabled": bool(
            contract["execution_policy"]["experiment_execution_enabled"]
        ),
    }


CLI_HYPERPARAMETER_FLAGS = {
    "lambda_js": "--lambda-js",
    "lambda_res": "--lambda-res",
    "residual_head_depth": "--residual-head-depth",
    "warmup_epochs": "--warmup-epochs",
    "ramp_epochs": "--ramp-epochs",
    "offline_views": "--offline-views",
    "clean_profile": "--clean-profile",
}


def _append_method_arguments(args: list[str], hyperparameters: Mapping[str, Any]) -> None:
    for key, flag in CLI_HYPERPARAMETER_FLAGS.items():
        if key in hyperparameters:
            args.extend([flag, str(hyperparameters[key])])
    if hyperparameters.get("paired_offline_views") is True:
        args.append("--paired-offline-views")


def _training_argv(
    contract: Mapping[str, Any],
    *,
    hardware_profile: Mapping[str, Any],
    method: Mapping[str, Any],
    seed: int,
    evaluation_seed: int,
    subset_manifest: str,
    epochs: int,
    max_optimizer_steps: int,
    validation_interval_steps: int,
    output_dir: str,
    run_id: str,
    hyperparameters: Mapping[str, Any],
) -> list[str]:
    experiment = contract["experiment"]
    simulation = contract["simulation"]
    data = contract["data"]
    applied_hardware = hardware_profile["applied"]
    main_process = applied_hardware["main_process"]
    cuda_math = applied_hardware["cuda_math"]
    optimizer_profile = applied_hardware["optimizer"]
    amp_profile = applied_hardware["automatic_mixed_precision"]
    compile_profile = applied_hardware["torch_compile"]
    args = [
        str(contract["trainer"]["path"]),
        "--mode",
        str(method["mode"]),
        "--simulation-config",
        str(simulation["path"]),
        "--train-profile",
        str(method.get("train_profile", simulation["train_profile"])),
        "--in-range-profile",
        str(simulation["in_range_profile"]),
        "--ood-profiles",
        ",".join(map(str, simulation["development_ood_profiles"])),
        "--variant",
        str(contract["model"]["variant"]),
        "--dataset-size",
        str(data["dataset_size"]),
        "--data-root",
        str(data["root"]),
        "--split-manifest",
        str(data["split_manifest"]),
        "--peak-cache-name",
        str(data["peak_cache_name"]),
        "--epochs",
        str(epochs),
        "--max-optimizer-steps",
        str(max_optimizer_steps),
        "--validation-interval-steps",
        str(validation_interval_steps),
        "--batch-size",
        str(experiment["batch_size"]),
        "--evaluation-batch-size",
        str(experiment["evaluation_batch_size"]),
        "--dynamic-prefetch-workers",
        str(experiment["dynamic_view_prefetch"]["worker_processes"]),
        "--dynamic-prefetch-batches",
        str(experiment["dynamic_view_prefetch"]["prefetch_batches"]),
        "--dynamic-prefetch-worker-native-threads",
        str(experiment["dynamic_view_prefetch"]["worker_native_threads"]),
        "--dynamic-prefetch-start-method",
        str(experiment["dynamic_view_prefetch"]["multiprocessing_start_method"]),
        "--pin-memory",
        "--non-blocking-h2d",
        "--main-process-intraop-threads",
        str(main_process["intraop_threads"]),
        "--main-process-interop-threads",
        str(main_process["interop_threads"]),
        "--float32-matmul-precision",
        str(cuda_math["float32_matmul_precision"]),
        "--seed",
        str(seed),
        "--evaluation-seed",
        str(evaluation_seed),
        "--development-subset-manifest",
        subset_manifest,
        "--study-contract",
        "configs/algorithm.v9.method_transfer.json",
        "--evaluation-contract",
        str(contract["evaluation"]["path"]),
        "--run-id",
        run_id,
        "--device",
        str(experiment["device"]),
        "--output-dir",
        output_dir,
        "--run-dir-exact",
        "--development-only",
    ]
    if cuda_math.get("allow_tf32_matmul") is True and cuda_math.get(
        "allow_tf32_cudnn"
    ) is True:
        args.append("--allow-tf32")
    if cuda_math.get("cudnn_benchmark") is True:
        args.append("--cudnn-benchmark")
    if cuda_math.get("cudnn_deterministic") is True:
        args.append("--cudnn-deterministic")
    if optimizer_profile.get("fused") is True:
        args.append("--fused-adamw")
    if amp_profile.get("enabled") is True:
        args.extend(["--amp", "--amp-dtype", str(amp_profile["dtype"])])
        if amp_profile.get("fallback_to_float32") is True:
            args.append("--amp-fallback-to-float32")
    if compile_profile.get("enabled") is True:
        args.extend(
            [
                "--torch-compile",
                "--torch-compile-backend",
                str(compile_profile["backend"]),
                "--torch-compile-mode",
                str(compile_profile["mode"]),
            ]
        )
        if compile_profile.get("fullgraph") is True:
            args.append("--torch-compile-fullgraph")
        if compile_profile.get("dynamic") is True:
            args.append("--torch-compile-dynamic")
        if compile_profile.get("fallback_to_eager") is True:
            args.append("--torch-compile-fallback-to-eager")
    _append_method_arguments(args, hyperparameters)
    return args


def build_tuning_plan(contract: Mapping[str, Any], project_root: str | Path) -> dict[str, Any]:
    """Build the seven full-budget validation-only tuning runs without executing them."""

    validate_contract(contract)
    audit = audit_contract_assets(contract, project_root)
    tuning = contract["development_tuning"]
    hardware_profile = json.loads(
        _project_path(
            Path(project_root), str(contract["hardware_profile"]["path"])
        ).read_text(encoding="utf-8")
    )
    methods = {str(item["id"]): item for item in contract["experiment"]["methods"]}
    baseline_id = str(tuning["baseline_method_id"])
    if baseline_id not in methods or methods[baseline_id]["role"] != "baseline":
        raise ValueError("development tuning baseline does not identify the ordinary baseline")
    seed = int(tuning["seed"])
    evaluation_seed = int(contract["evaluation"]["development_evaluation_seed"])
    subset_manifest = str(contract["data"]["development_validation_manifest"])
    output_root = str(tuning["output_root"])
    runs: list[dict[str, Any]] = []

    def add_run(method: Mapping[str, Any], run_id: str, hyperparameters: Mapping[str, Any]) -> None:
        output_dir = f"{output_root}/{run_id}"
        runs.append(
            {
                "run_id": run_id,
                "method_id": str(method["id"]),
                "mode": str(method["mode"]),
                "role": str(method["role"]),
                "seed": seed,
                "evaluation_seed": evaluation_seed,
                "hyperparameters": dict(hyperparameters),
                "development_subset_manifest": subset_manifest,
                "development_subset_manifest_hash": contract["data"][
                    "development_validation_manifest_sha256"
                ],
                "output_dir": output_dir,
                "argv": _training_argv(
                    contract,
                    hardware_profile=hardware_profile,
                    method=method,
                    seed=seed,
                    evaluation_seed=evaluation_seed,
                    subset_manifest=subset_manifest,
                    epochs=int(tuning["epochs"]),
                    max_optimizer_steps=int(tuning["max_optimizer_steps"]),
                    validation_interval_steps=int(tuning["validation_interval_steps"]),
                    output_dir=output_dir,
                    run_id=run_id,
                    hyperparameters=hyperparameters,
                ),
                "status": "planned_not_started",
                "simulated_test_locked": True,
                "real_test_locked": True,
            }
        )

    add_run(methods[baseline_id], f"{baseline_id}__tuning_seed_{seed}", {})
    for candidate in tuning["candidates"]:
        method = methods[str(candidate["method_id"])]
        parameter = str(candidate["parameter"])
        fixed = dict(method.get("hyperparameters", {}))
        for value in candidate["values"]:
            label = str(value).replace(".", "p")
            run_id = f"{method['id']}__{parameter}_{label}__tuning_seed_{seed}"
            add_run(method, run_id, {**fixed, parameter: value})

    return {
        "schema_version": "v9.1-method-transfer-tuning-plan",
        "plan_kind": "validation_only_development_tuning",
        "contract_hash": canonical_hash(contract),
        "execution_enabled": bool(tuning["execution_enabled"]),
        "asset_audit": audit,
        "run_count": len(runs),
        "runs": runs,
    }


def _frozen_hyperparameters(
    contract: Mapping[str, Any], project_root: str | Path
) -> dict[str, float]:
    formal = contract["formal_hyperparameters"]
    if formal.get("frozen") is not True:
        raise ValueError(
            "formal plan is locked: Validation-only tuning selection has not been frozen"
        )
    selection_path = _project_path(Path(project_root), str(formal["selection_artifact"]))
    if not selection_path.is_file():
        raise ValueError("formal plan is locked: tuning selection artifact is missing")
    expected_hash = str(formal.get("selection_artifact_sha256") or "").upper()
    if not expected_hash or sha256_file(selection_path) != expected_hash:
        raise ValueError("formal plan is locked: tuning selection artifact hash mismatch")
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    if selection.get("status") != "selected":
        raise ValueError("formal plan is locked: tuning selection did not complete")
    if selection.get("simulated_test_used") is not False or selection.get("real_test_used") is not False:
        raise ValueError("formal plan is locked: tuning selection used a locked test set")
    values = {key: float(value) for key, value in formal.get("values", {}).items()}
    if values != {key: float(value) for key, value in selection.get("selected_values", {}).items()}:
        raise ValueError("formal hyperparameters do not match the tuning selection artifact")
    grids = {
        str(item["parameter"]): {float(value) for value in item["values"]}
        for item in contract["development_tuning"]["candidates"]
    }
    for key, value in values.items():
        if key not in grids or value not in grids[key]:
            raise ValueError(f"selected {key}={value} is outside the registered grid")
    return values


def build_run_plan(contract: Mapping[str, Any], project_root: str | Path) -> dict[str, Any]:
    """Build the fifteen formal development runs after tuning values are frozen."""

    validate_contract(contract)
    audit = audit_contract_assets(contract, project_root)
    selected_values = _frozen_hyperparameters(contract, project_root)
    experiment = contract["experiment"]
    hardware_profile = json.loads(
        _project_path(
            Path(project_root), str(contract["hardware_profile"]["path"])
        ).read_text(encoding="utf-8")
    )
    subset_manifest = str(contract["data"]["development_validation_manifest"])
    evaluation_seed = int(contract["evaluation"]["development_evaluation_seed"])
    runs: list[dict[str, Any]] = []
    for seed in experiment["seeds"]:
        for method in experiment["methods"]:
            run_id = f"{method['id']}__seed_{seed}"
            output_dir = f"{experiment['output_root']}/{method['id']}/seed_{seed}"
            hyperparameters = dict(method.get("hyperparameters", {}))
            tuned_parameter = method.get("tuned_parameter")
            if tuned_parameter:
                hyperparameters[str(tuned_parameter)] = selected_values[str(tuned_parameter)]
            runs.append(
                {
                    "run_id": run_id,
                    "method_id": method["id"],
                    "mode": method["mode"],
                    "role": method["role"],
                    "seed": int(seed),
                    "evaluation_seed": evaluation_seed,
                    "hyperparameters": hyperparameters,
                    "development_subset_manifest": subset_manifest,
                    "development_subset_manifest_hash": contract["data"][
                        "development_validation_manifest_sha256"
                    ],
                    "output_dir": output_dir,
                    "argv": _training_argv(
                        contract,
                        hardware_profile=hardware_profile,
                        method=method,
                        seed=int(seed),
                        evaluation_seed=evaluation_seed,
                        subset_manifest=subset_manifest,
                        epochs=int(experiment["epochs"]),
                        max_optimizer_steps=int(experiment["max_optimizer_steps"]),
                        validation_interval_steps=int(experiment["validation_interval_steps"]),
                        output_dir=output_dir,
                        run_id=run_id,
                        hyperparameters=hyperparameters,
                    ),
                    "status": "planned_not_started",
                    "simulated_test_locked": True,
                    "real_test_locked": True,
                }
            )

    return {
        "schema_version": "v9.1-method-transfer-run-plan",
        "plan_kind": "formal_unified_validation_comparison",
        "contract_hash": canonical_hash(contract),
        "contract_status": contract["status"],
        "execution_policy": dict(contract["execution_policy"]),
        "selected_hyperparameters": selected_values,
        "asset_audit": audit,
        "run_count": len(runs),
        "runs": runs,
    }


def _final_evaluation(result: Mapping[str, Any]) -> Mapping[str, Any]:
    for item in reversed(result.get("history", [])):
        if "in_range" in item and "ood" in item:
            return item
    raise ValueError("results.json has no completed development evaluation")


def _is_sha256(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(character in "0123456789abcdefABCDEF" for character in text)


def _load_audited_result(
    contract: Mapping[str, Any],
    result_path: Path,
    *,
    method: Mapping[str, Any],
    seed: int,
    run_id: str,
    subset_hash: str,
    expected_optimizer_steps: int,
    project_root: Path,
) -> dict[str, Any]:
    if not result_path.is_file():
        raise ValueError(f"missing results artifact: {result_path}")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("run_id") != run_id:
        raise ValueError(f"run ID mismatch: {result_path}")
    if result.get("mode") != method["mode"] or int(result.get("seed", -1)) != int(seed):
        raise ValueError(f"run identity mismatch: {result_path}")
    if int(result.get("evaluation_seed", -1)) != int(
        contract["evaluation"]["development_evaluation_seed"]
    ):
        raise ValueError(f"evaluation seed mismatch: {result_path}")
    scope = result.get("evaluation_scope", {})
    if (
        scope.get("development_only") is not True
        or scope.get("selection_split") != "validation"
        or scope.get("simulated_test_locked") is not True
        or scope.get("real_test_locked") is not True
    ):
        raise ValueError(f"test lock violated: {result_path}")
    if int(result.get("unique_train_structures", -1)) != int(
        contract["data"]["expected_split_counts"]["train"]
    ):
        raise ValueError(f"unexpected training structure count: {result_path}")

    expected_hashes = {
        "study_contract_hash": sha256_file(
            project_root / "configs" / "algorithm.v9.method_transfer.json"
        ),
        "evaluation_contract_hash": str(contract["evaluation"]["sha256"]).upper(),
        "data_manifest_hash": str(contract["data"]["split_manifest_sha256"]).upper(),
        "development_subset_manifest_hash": str(subset_hash).upper(),
        "simulation_config_hash": str(contract["simulation"]["sha256"]).upper(),
        "peak_cache_manifest_hash": str(
            contract["data"]["peak_cache_manifest_sha256"]
        ).upper(),
    }
    for key, expected in expected_hashes.items():
        if str(result.get(key, "")).upper() != expected:
            raise ValueError(f"{key} mismatch: {result_path}")
    for key in (
        "resolved_config_hash",
        "source_tree_hash",
        "training_sampler_contract_hash",
        "training_stream_audit_hash",
        "view_manifest_hash",
        "evaluation_manifest_hash",
        "checkpoint_hash",
    ):
        if not _is_sha256(result.get(key)):
            raise ValueError(f"missing or malformed {key}: {result_path}")
    if method["mode"] in {"clean_erm", "offline_erm"} and not _is_sha256(
        result.get("offline_manifest_hash")
    ):
        raise ValueError(f"fixed-view reference is missing its offline manifest hash: {result_path}")

    runtime = result.get("runtime_provenance", {})
    expected_runtime = contract["runtime"]
    runtime_expectations = {
        "python_version": expected_runtime["python_version"],
        "torch_version": expected_runtime["torch_version"],
        "cuda_runtime": expected_runtime["cuda_runtime"],
        "gpu_name": expected_runtime["gpu_name"],
    }
    for key, expected in runtime_expectations.items():
        if runtime.get(key) != expected:
            raise ValueError(f"runtime provenance mismatch for {key}: {result_path}")
    if not str(runtime.get("device", "")).startswith("cuda"):
        raise ValueError(f"formal result was not produced on CUDA: {result_path}")

    compute = result.get("compute_summary", {})
    expected_forward_views = expected_optimizer_steps * 2
    expected_structure_exposures = expected_optimizer_steps * int(
        contract["experiment"]["batch_size"]
    )
    expected_view_exposures = expected_forward_views * int(contract["experiment"]["batch_size"])
    expected_compute = {
        "optimizer_steps": expected_optimizer_steps,
        "training_backbone_forward_views": expected_forward_views,
        "training_structure_exposures": expected_structure_exposures,
        "training_view_exposures": expected_view_exposures,
    }
    for key, expected in expected_compute.items():
        if int(compute.get(key, -1)) != expected:
            raise ValueError(f"compute budget mismatch for {key}: {result_path}")
    for key in ("wall_clock_seconds", "gpu_hours", "peak_gpu_memory_mb"):
        value = compute.get(key)
        if value is None or float(value) < 0:
            raise ValueError(f"missing compute provenance {key}: {result_path}")

    stream_audit = result.get("training_stream_audit", {})
    if not isinstance(stream_audit, Mapping):
        raise ValueError(f"missing training stream audit: {result_path}")
    if str(stream_audit.get("sampler_contract_hash", "")).upper() != str(
        result["training_sampler_contract_hash"]
    ).upper():
        raise ValueError(f"training sampler contract mismatch: {result_path}")
    for key in ("sampler_hash", "pair_schedule_hash", "parameter_pair_hash"):
        if not _is_sha256(stream_audit.get(key)):
            raise ValueError(f"missing or malformed training stream {key}: {result_path}")
    expected_audit_counts = {
        "optimizer_steps": expected_optimizer_steps,
        "structure_exposures": expected_structure_exposures,
        "spectrum_exposures": expected_view_exposures,
    }
    for key, expected in expected_audit_counts.items():
        if int(stream_audit.get(key, -1)) != expected:
            raise ValueError(f"training stream exposure mismatch for {key}: {result_path}")

    final = _final_evaluation(result)
    required_metrics = set(map(str, contract["metrics_and_logging"]["required_metrics"]))
    evaluation_profiles = ["in_range", *map(str, contract["simulation"]["development_ood_profiles"])]
    metric_payloads = {"in_range": final.get("in_range", {})}
    metric_payloads.update(final.get("ood", {}))
    for profile in evaluation_profiles:
        metrics = metric_payloads.get(profile)
        if not isinstance(metrics, Mapping):
            raise ValueError(f"missing evaluation profile {profile}: {result_path}")
        missing_metrics = sorted(required_metrics - set(metrics))
        if missing_metrics:
            raise ValueError(
                f"{result_path} profile {profile} is missing metrics: {missing_metrics}"
            )
    prediction_metadata = result.get("prediction_rows", {})
    if not isinstance(prediction_metadata, Mapping):
        raise ValueError(f"missing prediction-row metadata: {result_path}")
    prediction_path = (result_path.parent / str(prediction_metadata.get("path", ""))).resolve()
    try:
        prediction_path.relative_to(result_path.parent.resolve())
    except ValueError as error:
        raise ValueError(f"prediction-row path escapes run directory: {result_path}") from error
    if not prediction_path.is_file():
        raise ValueError(f"missing prediction-row artifact: {prediction_path}")
    if sha256_file(prediction_path) != str(prediction_metadata.get("sha256", "")).upper():
        raise ValueError(f"prediction-row hash mismatch: {prediction_path}")
    prediction_rows = validate_prediction_rows(
        json.loads(line)
        for line in prediction_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    if len(prediction_rows) != int(prediction_metadata.get("row_count", -1)):
        raise ValueError(f"prediction-row count mismatch: {prediction_path}")
    if any(row["seed"] != seed or row["method_id"] != str(method["id"]) for row in prediction_rows):
        raise ValueError(f"prediction-row run identity mismatch: {prediction_path}")
    observed_profiles = {row["profile"] for row in prediction_rows}
    expected_profiles = {str(contract["simulation"]["in_range_profile"]), *map(str, contract["simulation"]["development_ood_profiles"])}
    if observed_profiles != expected_profiles:
        raise ValueError(f"prediction-row profile coverage mismatch: {prediction_path}")
    return {
        "result": result,
        "final": final,
        "result_path": str(result_path),
        "view_manifest_hash": str(result["view_manifest_hash"]).upper(),
        "evaluation_manifest_hash": str(result["evaluation_manifest_hash"]).upper(),
        "data_manifest_hash": str(result["data_manifest_hash"]).upper(),
        "simulation_config_hash": str(result["simulation_config_hash"]).upper(),
        "peak_cache_manifest_hash": str(result["peak_cache_manifest_hash"]).upper(),
        "training_sampler_contract_hash": str(
            result["training_sampler_contract_hash"]
        ).upper(),
        "training_sampler_hash": str(stream_audit["sampler_hash"]).upper(),
        "pair_schedule_hash": str(stream_audit["pair_schedule_hash"]).upper(),
        "parameter_pair_hash": str(stream_audit["parameter_pair_hash"]).upper(),
        "compute": {key: compute[key] for key in expected_compute},
        "id_macro_f1": float(final["in_range"]["macro_f1"]),
        "profile_macro_f1": {
            name: float(final["ood"][name]["macro_f1"])
            for name in contract["simulation"]["development_ood_profiles"]
        },
        "prediction_rows": prediction_rows,
    }


def evaluate_tuning_selection(
    contract: Mapping[str, Any],
    results_root: str | Path,
    project_root: str | Path,
) -> dict[str, Any]:
    """Select one registered lambda per candidate using only the tuning subset."""

    validate_contract(contract)
    plan = build_tuning_plan(contract, project_root)
    root = Path(results_root)
    methods = {str(item["id"]): item for item in contract["experiment"]["methods"]}
    tuning = contract["development_tuning"]
    seed = int(tuning["seed"])
    subset_hash = str(contract["data"]["development_validation_manifest_sha256"])
    audited: dict[str, dict[str, Any]] = {}
    for run in plan["runs"]:
        result_path = root / str(run["run_id"]) / "results.json"
        audited[str(run["run_id"])] = _load_audited_result(
            contract,
            result_path,
            method=methods[str(run["method_id"])],
            seed=seed,
            run_id=str(run["run_id"]),
            subset_hash=subset_hash,
            expected_optimizer_steps=int(tuning["max_optimizer_steps"]),
            project_root=Path(project_root).resolve(),
        )

    evaluation_hashes = {item["evaluation_manifest_hash"] for item in audited.values()}
    core_view_hashes = {item["view_manifest_hash"] for item in audited.values()}
    sampler_hashes = {item["training_sampler_hash"] for item in audited.values()}
    pair_schedule_hashes = {item["pair_schedule_hash"] for item in audited.values()}
    parameter_pair_hashes = {item["parameter_pair_hash"] for item in audited.values()}
    compute_budgets = {canonical_hash(item["compute"]) for item in audited.values()}
    if (
        len(evaluation_hashes) != 1
        or len(core_view_hashes) != 1
        or len(sampler_hashes) != 1
        or len(pair_schedule_hashes) != 1
        or len(parameter_pair_hashes) != 1
        or len(compute_budgets) != 1
    ):
        raise ValueError(
            "development tuning runs do not share matched sampler, pairs, views, evaluation, and compute"
        )

    baseline_run = next(run for run in plan["runs"] if run["role"] == "baseline")
    baseline = audited[str(baseline_run["run_id"])]
    primary_profiles = list(
        map(str, contract["validation_comparison"]["primary_ood_profiles"])
    )
    baseline_score = mean(baseline["profile_macro_f1"][name] for name in primary_profiles)
    selected_values: dict[str, float] = {}
    candidate_reports: dict[str, Any] = {}
    for candidate in tuning["candidates"]:
        method_id = str(candidate["method_id"])
        parameter = str(candidate["parameter"])
        rows = []
        for run in plan["runs"]:
            if run["method_id"] != method_id:
                continue
            value = float(run["hyperparameters"][parameter])
            result = audited[str(run["run_id"])]
            score = mean(result["profile_macro_f1"][name] for name in primary_profiles)
            id_delta = result["id_macro_f1"] - baseline["id_macro_f1"]
            rows.append(
                {
                    "value": value,
                    "eligible": id_delta
                    >= -float(tuning["selection"]["maximum_id_drop_vs_baseline"]),
                    "mean_single_factor_ood_macro_f1": score,
                    "gain_vs_baseline": score - baseline_score,
                    "id_delta_vs_baseline": id_delta,
                    "run_id": run["run_id"],
                }
            )
        eligible = [row for row in rows if row["eligible"]]
        if not eligible:
            raise ValueError(f"no {parameter} value passes the tuning ID guardrail")
        selected = max(
            eligible,
            key=lambda row: (row["mean_single_factor_ood_macro_f1"], -row["value"]),
        )
        selected_values[parameter] = float(selected["value"])
        candidate_reports[method_id] = {
            "parameter": parameter,
            "registered_values": list(candidate["values"]),
            "source": candidate["source"],
            "evaluations": rows,
            "selected_value": selected["value"],
        }

    return {
        "schema_version": "v9.1-method-transfer-tuning-selection",
        "status": "selected",
        "selection_scope": "unified_validation_only",
        "study_contract_hash": sha256_file(
            Path(project_root).resolve() / "configs" / "algorithm.v9.method_transfer.json"
        ),
        "evaluation_contract_hash": str(contract["evaluation"]["sha256"]).upper(),
        "validation_manifest_hash": subset_hash,
        "simulated_test_used": False,
        "real_test_used": False,
        "run_count": len(plan["runs"]),
        "baseline_method": baseline_run["method_id"],
        "baseline_mean_single_factor_ood_macro_f1": baseline_score,
        "selected_values": selected_values,
        "candidate_reports": candidate_reports,
        "result_artifact_hashes": {
            run_id: sha256_file(item["result_path"])
            for run_id, item in sorted(audited.items())
        },
        "formal_freeze_required_next": True,
    }


def evaluate_validation_comparison(
    contract: Mapping[str, Any],
    results_root: str | Path,
    project_root: str | Path | None = None,
) -> dict[str, Any]:
    """Compare and select methods on unified Validation without a pass/fail Gate."""

    validate_contract(contract)
    if contract["formal_hyperparameters"].get("frozen") is not True:
        raise ValueError(
            "Validation comparison is locked until Validation-only tuning values are frozen"
        )
    project = (
        Path(project_root).resolve()
        if project_root is not None
        else Path(__file__).resolve().parents[2]
    )
    root = Path(results_root)
    experiment = contract["experiment"]
    comparison = contract["validation_comparison"]
    bootstrap_contract = comparison["paired_bootstrap_contract"]
    methods = {str(item["id"]): item for item in experiment["methods"]}
    baseline_id = next(key for key, item in methods.items() if item["role"] == "baseline")
    primary_profiles = list(map(str, comparison["primary_ood_profiles"]))
    combination_profiles = list(map(str, comparison["secondary_combination_profiles"]))
    run_metrics: dict[tuple[str, int], dict[str, Any]] = {}

    for method_id, method in methods.items():
        for seed in experiment["seeds"]:
            result_path = root / method_id / f"seed_{seed}" / "results.json"
            run_id = f"{method_id}__seed_{seed}"
            run_metrics[(method_id, int(seed))] = _load_audited_result(
                contract,
                result_path,
                method=method,
                seed=int(seed),
                run_id=run_id,
                subset_hash=str(
                    contract["data"]["development_validation_manifest_sha256"]
                ),
                expected_optimizer_steps=int(experiment["max_optimizer_steps"]),
                project_root=project,
            )
            profile_values = run_metrics[(method_id, int(seed))]["profile_macro_f1"]
            run_metrics[(method_id, int(seed))]["mean_ood_macro_f1"] = mean(
                profile_values[name] for name in primary_profiles
            )

    fairness_errors: list[str] = []
    shared_evaluation_hashes = {
        metrics["evaluation_manifest_hash"] for metrics in run_metrics.values()
    }
    if len(shared_evaluation_hashes) != 1:
        fairness_errors.append("all methods and seeds must share one fixed evaluation manifest")
    for seed in experiment["seeds"]:
        baseline = run_metrics[(baseline_id, int(seed))]
        for method_id, method in methods.items():
            candidate = run_metrics[(method_id, int(seed))]
            comparison_keys = [
                "data_manifest_hash",
                "simulation_config_hash",
                "peak_cache_manifest_hash",
                "evaluation_manifest_hash",
                "training_sampler_contract_hash",
                "training_sampler_hash",
                "pair_schedule_hash",
                "compute",
            ]
            if method["role"] in CORE_ROLES:
                comparison_keys.extend(["view_manifest_hash", "parameter_pair_hash"])
            for key in comparison_keys:
                if candidate[key] != baseline[key]:
                    fairness_errors.append(f"seed {seed}: {method_id} mismatched {key}")
    if fairness_errors:
        raise ValueError(f"matched-budget audit failed: {fairness_errors}")

    method_summaries: dict[str, Any] = {}
    for method_id, method in methods.items():
        method_summaries[method_id] = {
            "role": method["role"],
            "mean_id_macro_f1": mean(
                run_metrics[(method_id, int(seed))]["id_macro_f1"]
                for seed in experiment["seeds"]
            ),
            "mean_single_factor_ood_macro_f1": mean(
                run_metrics[(method_id, int(seed))]["mean_ood_macro_f1"]
                for seed in experiment["seeds"]
            ),
            "per_seed_single_factor_ood_macro_f1": [
                run_metrics[(method_id, int(seed))]["mean_ood_macro_f1"]
                for seed in experiment["seeds"]
            ],
        }

    selectable = list(map(str, comparison["selectable_method_ids"]))
    selected = max(
        selectable,
        key=lambda method_id: (
            method_summaries[method_id]["mean_single_factor_ood_macro_f1"],
            -int(methods[method_id].get("complexity_rank", 999)),
        ),
    )

    def paired_contrast(focus_id: str, comparator_id: str) -> dict[str, Any]:
        family_contrast = hierarchical_paired_bootstrap(
            [
                row
                for (method_id, _seed), metrics in run_metrics.items()
                if method_id in {focus_id, comparator_id}
                for row in metrics["prediction_rows"]
            ],
            focus_method_id=focus_id,
            comparator_method_id=comparator_id,
            profiles=primary_profiles,
            replicates=int(bootstrap_contract["replicates"]),
            random_seed=int(bootstrap_contract["random_seed"]),
        )
        deltas = [
            float(family_contrast["paired_seed_deltas"][str(int(seed))])
            for seed in experiment["seeds"]
        ]
        ci_low, ci_high = family_contrast["hierarchical_bootstrap_95_ci"]
        return {
            "focus_method_id": focus_id,
            "comparator_method_id": comparator_id,
            "metric": "mean_single_factor_ood_macro_f1",
            "paired_seed_deltas": deltas,
            "mean_delta": mean(deltas),
            "paired_bootstrap_95_ci": [ci_low, ci_high],
            "hierarchical_bootstrap": family_contrast,
            "all_seed_deltas_positive": all(value > 0.0 for value in deltas),
            "mean_id_delta": mean(
                run_metrics[(focus_id, int(seed))]["id_macro_f1"]
                - run_metrics[(comparator_id, int(seed))]["id_macro_f1"]
                for seed in experiment["seeds"]
            ),
            "mean_profile_deltas": {
                name: mean(
                    run_metrics[(focus_id, int(seed))]["profile_macro_f1"][name]
                    - run_metrics[(comparator_id, int(seed))]["profile_macro_f1"][name]
                    for seed in experiment["seeds"]
                )
                for name in [*primary_profiles, *combination_profiles]
            },
        }

    js_id = "js_consistency_transfer"
    residual_id = "residual_decorrelation_transfer"
    residual_vs_js = paired_contrast(residual_id, js_id)
    residual_vs_dynamic = paired_contrast(residual_id, baseline_id)
    js_vs_dynamic = paired_contrast(js_id, baseline_id)

    def stable_positive(contrast: Mapping[str, Any]) -> bool:
        return bool(
            contrast["mean_delta"] > 0.0
            and contrast["paired_bootstrap_95_ci"][0] > 0.0
            and contrast["all_seed_deltas_positive"]
        )

    residual_stably_beats_js = stable_positive(residual_vs_js)
    js_stably_beats_residual = bool(
        residual_vs_js["mean_delta"] < 0.0
        and residual_vs_js["paired_bootstrap_95_ci"][1] < 0.0
        and all(value < 0.0 for value in residual_vs_js["paired_seed_deltas"])
    )
    residual_effective = stable_positive(residual_vs_dynamic)
    js_effective = stable_positive(js_vs_dynamic)
    if selected == residual_id and residual_effective and residual_stably_beats_js:
        narrative_outcome = "residual_stably_beats_dynamic_and_js"
    elif selected == js_id and js_effective and (not residual_effective or js_stably_beats_residual):
        narrative_outcome = "js_effective_residual_no_extra_gain"
    elif residual_effective and js_effective:
        narrative_outcome = "both_effective_no_clear_difference"
    elif residual_effective:
        narrative_outcome = "residual_effective_js_comparison_inconclusive"
    else:
        narrative_outcome = "neither_effective"
    return {
        "schema_version": "v9.2-method-transfer-unified-validation-comparison",
        "status": "selected",
        "baseline": baseline_id,
        "selected_method": selected,
        "selection_scope": "unified_validation_only",
        "pass_fail_decision_used": False,
        "simulated_test_used": False,
        "real_test_used": False,
        "matched_budget_audit": "passed",
        "formal_run_count": len(run_metrics),
        "method_summaries": method_summaries,
        "paired_comparisons": {
            "js_minus_dynamic": js_vs_dynamic,
            "residual_minus_dynamic": residual_vs_dynamic,
            "residual_minus_js": residual_vs_js,
        },
        "paper_narrative_outcome": narrative_outcome,
        "paper_narrative_text": contract["narrative_policy"]["paper_outcome_branches"][
            narrative_outcome
        ],
        "negative_result_diagnostic_order": (
            [
                "simulator_domain_shift_validity",
                "ood_design_validity",
                "backbone_and_split_correctness",
                "real_xrd_preprocessing_consistency",
            ]
            if narrative_outcome == "neither_effective"
            else []
        ),
    }


def audit_final_evaluation_locks(
    contract: Mapping[str, Any], project_root: str | Path
) -> dict[str, Any]:
    """Audit final-test contracts without unlocking or evaluating either test set."""

    validate_contract(contract)
    root = Path(project_root).resolve()
    evaluation_path = _project_path(root, str(contract["evaluation"]["path"]))
    real_path = _project_path(root, str(contract["final_evaluation"]["real_test_contract"]))
    if not evaluation_path.is_file() or not real_path.is_file():
        raise ValueError("a final evaluation contract is missing")
    if sha256_file(evaluation_path) != str(contract["evaluation"]["sha256"]).upper():
        raise ValueError("evaluation contract hash mismatch")
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    real = json.loads(real_path.read_text(encoding="utf-8"))
    expected_real_hash = str(evaluation["real_test"]["contract_sha256"]).upper()
    if sha256_file(real_path) != expected_real_hash:
        raise ValueError("real-test template hash mismatch")
    if evaluation["simulated_test"]["enabled"] is not False:
        raise ValueError("simulated test was unexpectedly unlocked")
    if evaluation["real_test"]["enabled"] is not False or real["enabled"] is not False:
        raise ValueError("real test was unexpectedly unlocked")
    blockers = []
    if contract["formal_hyperparameters"].get("frozen") is not True:
        blockers.append("Validation-only lambda selection is not frozen")
    blockers.append("15 formal development runs and unified Validation comparison are incomplete")
    blockers.append("simulated-test execution requires separate explicit authorization")
    blockers.append("real-test data manifest is not frozen and requires separate explicit authorization")
    return {
        "schema_version": "v9.1-method-transfer-final-evaluation-lock-audit",
        "status": "locked_as_required",
        "evaluation_contract_hash": sha256_file(evaluation_path),
        "real_test_template_hash": sha256_file(real_path),
        "simulated_test_locked": True,
        "real_test_locked": True,
        "simulated_test_used": False,
        "real_test_used": False,
        "unlock_ready": False,
        "blockers": blockers,
    }
