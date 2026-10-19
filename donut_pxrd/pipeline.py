#!/usr/bin/env python3
"""Stdlib-only, fail-closed serial controller for the DONUT-PXRD study."""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid


SCHEMA = "donut_pxrd_serial_pipeline_state_v1"
SEEDS = [20261061, 20261062, 20261063]
EXPECTED_CONFIG_SHA256 = "0b0c5a3ec4c4a8ba8515c4bb6b32f4493f0ca64fe7abd0811dabf498c0996fb4"


class PipelineError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(value, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_name, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temp_name)


def within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def safe_path(root: Path, raw: str, external_roots: list[Path] | None = None) -> Path:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    if within(candidate, root.resolve()):
        return candidate
    if external_roots and any(within(candidate, allowed.resolve()) for allowed in external_roots):
        return candidate
    raise PipelineError(f"path escapes selected repo root and approved artifact roots: {raw}")


def load_config(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    try:
        cfg = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PipelineError(f"invalid pipeline JSON: {exc}") from exc
    if cfg.get("schema") != "donut_pxrd_serial_pipeline_v1":
        raise PipelineError("unsupported pipeline config schema")
    policy = cfg.get("policy", {})
    if (cfg.get("study_config_sha256") != EXPECTED_CONFIG_SHA256 or cfg.get("seeds") != SEEDS or
            policy.get("q_parent_count") != 512 or policy.get("frozen_split_counts") != {"train": 358, "validation": 77, "test": 77} or
            policy.get("max_epochs") != 30 or policy.get("test_tuning") is not False):
        raise PipelineError("pipeline config violates immutable study config, seed, split, epoch, or test policy")
    stages = cfg.get("stages")
    if not isinstance(stages, list) or not stages:
        raise PipelineError("config must contain ordered stages")
    ids = [s.get("id") for s in stages]
    if len(ids) != len(set(ids)) or any(not isinstance(i, str) or not i for i in ids):
        raise PipelineError("stage IDs must be unique non-empty strings")
    seen: set[str] = set()
    for stage in stages:
        deps = stage.get("depends_on", [])
        if any(dep not in seen for dep in deps):
            raise PipelineError(f"stage {stage['id']} has missing or forward precedence")
        seen.add(stage["id"])
        if int(stage.get("timeout_seconds", 0)) <= 0:
            raise PipelineError(f"stage {stage['id']} needs a positive timeout")
        if stage.get("command") is not None and not isinstance(stage["command"], list):
            raise PipelineError(f"stage {stage['id']} command must be an argument vector")
    return cfg, hashlib.sha256(raw).hexdigest()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


class FileLock:
    def __init__(self, path: Path):
        self.path = path
        self.fd: int | None = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise PipelineError(f"pipeline lock already exists: {self.path}") from exc
        os.write(self.fd, json.dumps({"pid": os.getpid(), "created_utc": now()}).encode())
        return self

    def __exit__(self, *_exc):
        if self.fd is not None:
            os.close(self.fd)
        with contextlib.suppress(FileNotFoundError):
            self.path.unlink()


def stage_outputs(stage: dict, root: Path, external_roots: list[Path]) -> list[Path]:
    return [safe_path(root, value, external_roots) for value in stage.get("required_outputs", [])]


def protected_outputs(stage: dict, root: Path, external_roots: list[Path]) -> list[Path]:
    return [safe_path(root, str(value).format(seed=seed), external_roots)
            for value in stage.get("protected_artifacts", [])
            for seed in stage.get("protected_seeds", [None])]


def input_manifest(stage: dict, root: Path, external_roots: list[Path]) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in stage.get("inputs", []):
        path = safe_path(root, raw, external_roots)
        if not path.is_file():
            raise PipelineError(f"required input is missing: {path}")
        result[str(path)] = sha256(path)
    return result


def stage_fingerprint(stage: dict, config_sha: str, upstream: dict, inputs: dict) -> str:
    payload = {"config_sha256": config_sha, "stage": stage, "upstream": upstream, "inputs": inputs}
    return hashlib.sha256(canonical_json(payload)).hexdigest()


def _json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"cannot validate JSON output {path}: {exc}") from exc


def verify_preflight(stage: dict, root: Path, ext: list[Path], cfg: dict) -> dict:
    checks = {}
    for raw in stage.get("inputs", []):
        p = safe_path(root, raw, ext)
        if not p.is_file():
            raise PipelineError(f"preflight input file missing: {p}")
        checks[str(p)] = sha256(p)
    for raw in stage.get("required_outputs", []):
        p = safe_path(root, raw, ext)
        if not p.is_file():
            raise PipelineError(f"preflight source file missing: {p}")
        checks[raw] = sha256(p)
    config_path = safe_path(root, "donut_pxrd/configs/study_v1.json", ext)
    prereg_path = safe_path(root, "donut_pxrd/configs/preregistration_manifest.json", ext)
    study = _json(config_path)
    prereg = _json(prereg_path)
    actual_config_sha = sha256(config_path)
    if actual_config_sha != cfg["study_config_sha256"] or actual_config_sha != EXPECTED_CONFIG_SHA256:
        raise PipelineError(f"frozen study config SHA mismatch: {actual_config_sha}")
    if prereg.get("config_sha256") != actual_config_sha:
        raise PipelineError("pre-registration config SHA does not match frozen config")
    data = study.get("data", {})
    if data.get("q_count") != 512 or study.get("seeds") != SEEDS or study.get("donut", {}).get("epochs_max") != 30:
        raise PipelineError("frozen sample count, seed set, or epoch cap changed")
    if prereg.get("split_policy") != "fixed q parent split before nuisance/noise generation; 358/77/77":
        raise PipelineError("frozen split policy changed")
    if "no hyperparameter tuning" not in prereg.get("test_policy", ""):
        raise PipelineError("test leakage policy is absent or changed")
    checks[str(config_path)] = actual_config_sha
    checks[str(prereg_path)] = sha256(prereg_path)
    return {"checks": checks, "scientific_status": "preflight_verified", "study_config_sha256": actual_config_sha}


def verify_exp(stage: dict, root: Path, ext: list[Path], seeds: list[int]) -> dict:
    exp = stage["experiment"]
    run_dir = safe_path(root, f"donut_pxrd/results/study_v1/{exp}", ext)
    expected = ["data_arrays.npz", "data_manifest.json", "training_curves.json", "test_per_seed.json", "test_per_sample.csv"]
    for name in expected:
        if not (run_dir / name).is_file():
            raise PipelineError(f"{exp} missing required artifact {name}")
    dm = _json(run_dir / "data_manifest.json")
    arrays = run_dir / "data_arrays.npz"
    if dm.get("npz_sha256") != sha256(arrays):
        raise PipelineError(f"{exp} data archive SHA does not match data manifest")
    hashes = {str(arrays): sha256(arrays), str(run_dir / "data_manifest.json"): sha256(run_dir / "data_manifest.json")}
    records = _json(run_dir / "test_per_seed.json")
    if not isinstance(records, list) or sorted(r.get("seed") for r in records) != sorted(seeds):
        raise PipelineError(f"{exp} must contain exactly all frozen seed records")
    index_sets = [r.get("test_indices") for r in records]
    if not index_sets[0] or any(x != index_sets[0] for x in index_sets):
        raise PipelineError(f"{exp} seed records do not use one common non-empty test split")
    if len(index_sets[0]) != 77 or len(set(index_sets[0])) != 77:
        raise PipelineError(f"{exp} test split does not contain 77 unique parents")
    checkpoint_hashes = {}
    for rec in records:
        ckpt = safe_path(root, rec.get("checkpoint", ""), ext)
        if not ckpt.is_file() or sha256(ckpt) != rec.get("checkpoint_sha256"):
            raise PipelineError(f"{exp} checkpoint missing or SHA mismatch for seed {rec.get('seed')}")
        checkpoint_hashes[str(ckpt)] = sha256(ckpt)
    for item in expected:
        p = run_dir / item
        hashes[str(p)] = sha256(p)
    return {"artifact_sha256": hashes, "checkpoint_sha256": checkpoint_hashes,
            "seeds_verified": sorted(r["seed"] for r in records), "test_parent_count": 77,
            "scientific_status": "artifacts_verified; metrics retained as reported"}


def verify_texture(stage: dict, root: Path, ext: list[Path]) -> dict:
    base = safe_path(root, "donut_pxrd/results/study_v1", ext)
    npz, metrics = base / "exp3_texture_ood.npz", base / "exp3_texture_ood_metrics.json"
    if not npz.is_file() or not metrics.is_file():
        raise PipelineError("texture OOD archive or metrics are missing")
    m = _json(metrics)
    if m.get("status") != "COMPLETE" or len(m.get("metrics_by_seed", [])) != 3:
        raise PipelineError("texture OOD verifier status or seed records are invalid")
    return {"artifact_sha256": {str(npz): sha256(npz), str(metrics): sha256(metrics)},
            "scientific_status": "generator-side texture OOD outputs verified"}


def verify_exp4(stage: dict, root: Path, ext: list[Path]) -> dict:
    run = safe_path(root, "donut_pxrd/results/study_v1/exp4", ext)
    raw, summary_path = run / "raw_paired_results.json", run / "summary.json"
    if not raw.is_file() or not summary_path.is_file():
        raise PipelineError("experiment 4 raw paired results or summary are missing")
    summary = _json(summary_path)
    if summary.get("status") != "COMPLETE" or summary.get("test_parent_count") != 77:
        raise PipelineError("experiment 4 summary is not terminal or does not cover all frozen test parents")
    methods = summary.get("methods", [])
    if set(methods) != set("ABCDE"):
        raise PipelineError("experiment 4 summary does not contain methods A/B/C/D/E")
    records = _json(raw)
    counts: dict[str, list[int]] = {}
    for record in records if isinstance(records, list) else []:
        method = record.get("method")
        if method in set("ABCDE"):
            counts.setdefault(method, []).append(record.get("q_parent_index"))
    if any(len(counts.get(m, [])) != 231 for m in "ABCD") or len(counts.get("E", [])) != 77:
        raise PipelineError("experiment 4 raw paired records are incomplete")
    if any(len(set(counts[m])) != 77 for m in "ABCDE"):
        raise PipelineError("experiment 4 does not cover the same 77 test parents per method")
    data_path = safe_path(root, "donut_pxrd/results/study_v1/exp3c/data_arrays.npz", ext)
    if summary.get("dataset_sha256") != sha256(data_path):
        raise PipelineError("experiment 4 summary dataset SHA differs from the frozen exp3c archive")
    checkpoint_hashes = {}
    abc_records = summary.get("abc_training_records", [])
    expected_pairs = {(m, seed) for m in "ABC" for seed in SEEDS}
    if {(r.get("method"), r.get("seed")) for r in abc_records} != expected_pairs:
        raise PipelineError("experiment 4 A/B/C checkpoint records do not cover all three seeds")
    for rec in abc_records:
        ckpt = safe_path(root, rec.get("checkpoint", ""), ext)
        if not ckpt.is_file() or ckpt.stat().st_size == 0 or sha256(ckpt) != rec.get("checkpoint_sha256"):
            raise PipelineError(f"experiment 4 checkpoint missing or SHA mismatch: {rec.get('method')}/{rec.get('seed')}")
        checkpoint_hashes[str(ckpt)] = sha256(ckpt)
    return {"artifact_sha256": {str(raw): sha256(raw), str(summary_path): sha256(summary_path)},
            "checkpoint_sha256": checkpoint_hashes, "methods": methods, "test_parent_count": 77,
            "scientific_status": "experiment 4 raw and summary outputs verified; performance interpretation remains in report"}


def verify(stage: dict, root: Path, ext: list[Path], cfg: dict) -> dict:
    kind = stage.get("verifier")
    if kind == "preflight":
        return verify_preflight(stage, root, ext, cfg)
    if kind == "experiment":
        return verify_exp(stage, root, ext, cfg.get("seeds", SEEDS))
    if kind == "texture":
        return verify_texture(stage, root, ext)
    if kind == "experiment4":
        return verify_exp4(stage, root, ext)
    if kind == "files":
        outputs = stage_outputs(stage, root, ext)
        missing = [str(p) for p in outputs if not p.is_file()]
        if missing:
            raise PipelineError("missing required outputs: " + ", ".join(missing))
        return {"artifact_sha256": {str(p): sha256(p) for p in outputs}, "scientific_status": "required files verified"}
    if kind == "report":
        return {"scientific_status": "all upstream scientific artifacts verified; no metric threshold inferred"}
    raise PipelineError(f"unknown verifier hook: {kind}")


def inspect(cfg: dict, cfg_sha: str, root: Path, outdir: Path) -> dict:
    ext = [Path(p) for p in cfg.get("allowed_external_roots", [])]
    report = {"schema": "donut_pxrd_serial_inspect_v1", "created_utc": now(), "repo_root": str(root.resolve()),
              "pipeline_config_sha256": cfg_sha, "mode": "inspect", "read_only_target": True, "stages": []}
    for stage in cfg["stages"]:
        entry = {"id": stage["id"], "status": "NOT_RUN", "missing": [], "verified": False}
        if stage.get("verifier") in ("experiment", "texture", "experiment4"):
            try:
                evidence = verify(stage, root, ext, cfg)
                entry.update(status="COMPLETE", verified=True, evidence=evidence)
            except (PipelineError, OSError) as exc:
                # Inspect is an inventory; partial outputs are not classified as failures.
                entry.update(status="NOT_RUN", reason=str(exc))
                exp = stage.get("experiment")
                expected = []
                if exp:
                    expected = [f"donut_pxrd/results/study_v1/{exp}/{n}" for n in
                                ("data_arrays.npz", "data_manifest.json", "training_curves.json", "test_per_seed.json", "test_per_sample.csv")]
                elif stage.get("verifier") == "texture":
                    expected = ["donut_pxrd/results/study_v1/exp3_texture_ood.npz", "donut_pxrd/results/study_v1/exp3_texture_ood_metrics.json"]
                elif stage.get("verifier") == "experiment4":
                    expected = ["donut_pxrd/results/study_v1/exp4/raw_paired_results.json", "donut_pxrd/results/study_v1/exp4/summary.json"]
                else:
                    expected = stage.get("required_outputs", [])
                for raw in expected:
                    p = safe_path(root, raw, ext)
                    if not p.is_file():
                        entry["missing"].append(str(p))
        elif stage["id"] == "preflight":
            try:
                entry.update(status="COMPLETE", verified=True, evidence=verify(stage, root, ext, cfg))
            except (PipelineError, OSError) as exc:
                entry.update(status="BLOCKED", reason=str(exc))
        report["stages"].append(entry)
    outdir.mkdir(parents=True, exist_ok=True)
    atomic_json(outdir / "inspect_report.json", report)
    lines = [f"read_only_target=true", f"repo_root={root.resolve()}", f"created_utc={report['created_utc']}"]
    lines.extend(f"{s['id']}={s['status']} verified={s['verified']} missing={len(s['missing'])}" for s in report["stages"])
    (outdir / "inspect.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def _artifact_hashes(stage: dict, root: Path, ext: list[Path]) -> dict[str, str]:
    paths = stage_outputs(stage, root, ext)
    found = {}
    for p in paths:
        if p.is_file():
            found[str(p)] = sha256(p)
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file():
                    found[str(f)] = sha256(f)
    # Include checkpoint files discovered by the scientific verifier.
    return found


def _command(stage: dict, root: Path) -> list[str] | None:
    vector = stage.get("command")
    if vector is None:
        return None
    result = []
    for value in vector:
        s = str(value).replace("{python}", sys.executable).replace("{repo_root}", str(root))
        result.append(s)
    if result and not Path(result[0]).is_absolute() and result[0] == "python":
        result[0] = sys.executable
    return result


def external_worker_active(root: Path) -> bool:
    """Best-effort read-only guard for an independently launched study worker."""
    needles = ("run_donut_stages.py", "run_experiment4.py")
    if os.name == "nt":
        encoded = __import__("base64").b64encode(str(root.resolve()).encode("utf-8")).decode("ascii")
        script = ("$r=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('" + encoded + "')); "
                  "$p=Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and "
                  "$_.CommandLine.Contains($r) -and ($_.CommandLine -match 'run_donut_stages\\.py|run_experiment4\\.py') }; "
                  "if ($p) { 'ACTIVE' } else { 'IDLE' }")
        try:
            result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                                    capture_output=True, text=True, timeout=15, shell=False, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PipelineError(f"cannot verify external experiment process lock: {exc}") from exc
        if result.returncode != 0:
            raise PipelineError("cannot verify external experiment process lock; refusing Experiment 4")
        return "ACTIVE" in result.stdout
    try:
        result = subprocess.run(["ps", "-eo", "args="], capture_output=True, text=True, timeout=10,
                                shell=False, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise PipelineError(f"cannot verify external experiment process lock: {exc}") from exc
    command_text = result.stdout.casefold()
    return str(root.resolve()).casefold() in command_text and any(n in command_text for n in needles)


def _stage_run(stage: dict, root: Path, ext: list[Path], cfg: dict, state: dict, state_path: Path,
               log_dir: Path, config_sha: str, resume: bool, dry_run: bool = False) -> tuple[dict, str]:
    sid = stage["id"]
    inputs = input_manifest(stage, root, ext)
    upstream = {d: state["stages"].get(d, {}).get("artifact_sha256", {}) for d in stage.get("depends_on", [])}
    fingerprint = stage_fingerprint(stage, config_sha, upstream, inputs)
    prior = state["stages"].get(sid)
    outputs = stage_outputs(stage, root, ext)
    protected = protected_outputs(stage, root, ext)
    any_output = any(p.exists() for p in outputs)
    any_protected = any(p.exists() for p in protected)
    any_output = any_output or any_protected
    if stage.get("artifact_gate") and any_output and not (prior and prior.get("status") == "COMPLETE"):
        try:
            evidence = verify(stage, root, ext, cfg)
            record = {"status": "COMPLETE", "imported_verified": True, "fingerprint": fingerprint,
                      "artifact_sha256": evidence.get("artifact_sha256", _artifact_hashes(stage, root, ext)),
                      "evidence": evidence, "scientific_status": evidence.get("scientific_status"),
                      "verified_utc": now(), "attempts": list(prior.get("attempts", [])) if prior else []}
            state["stages"][sid] = record
            atomic_json(state_path, state)
            return record, "artifact-gate"
        except (PipelineError, OSError) as exc:
            record = {"status": "BLOCKED", "error": f"artifact gate did not verify: {exc}", "attempts": []}
            state["stages"][sid] = record
            atomic_json(state_path, state)
            return record, "blocked"
    if prior and prior.get("status") == "COMPLETE":
        try:
            evidence = verify(stage, root, ext, cfg)
            current_artifacts = evidence.get("artifact_sha256", {})
            unchanged = (prior.get("fingerprint") == fingerprint and
                         prior.get("artifact_sha256", {}) == current_artifacts)
            if unchanged:
                prior["resume_action"] = "SKIPPED_VERIFIED"
                prior["scientific_status"] = evidence.get("scientific_status")
                return prior, "skip"
            if resume:
                prior.update(status="BLOCKED", error="completed stage fingerprints or artifact hashes changed; manual repair required")
                atomic_json(state_path, state)
                return prior, "blocked"
        except (PipelineError, OSError):
            if resume:
                prior.update(status="BLOCKED", error="previously complete outputs no longer pass verifier; manual repair required")
                atomic_json(state_path, state)
                return prior, "blocked"
    if resume and not prior and any_output:
        try:
            evidence = verify(stage, root, ext, cfg)
            record = {"status": "COMPLETE", "imported_verified": True, "fingerprint": fingerprint,
                      "artifact_sha256": evidence.get("artifact_sha256", _artifact_hashes(stage, root, ext)),
                      "scientific_status": evidence.get("scientific_status"), "verified_utc": now(), "attempts": []}
            state["stages"][sid] = record
            atomic_json(state_path, state)
            return record, "imported"
        except (PipelineError, OSError) as exc:
            record = {"status": "BLOCKED", "error": f"partial/unverified existing outputs require manual repair: {exc}", "attempts": []}
            state["stages"][sid] = record
            atomic_json(state_path, state)
            return record, "blocked"
    if resume and prior and prior.get("status") not in ("COMPLETE", "RUNNING", "BLOCKED") and any_output:
        try:
            evidence = verify(stage, root, ext, cfg)
            record = {"status": "COMPLETE", "imported_verified": True, "fingerprint": fingerprint,
                      "artifact_sha256": evidence.get("artifact_sha256", _artifact_hashes(stage, root, ext)),
                      "evidence": evidence, "scientific_status": evidence.get("scientific_status"),
                      "verified_utc": now(), "attempts": list(prior.get("attempts", []))}
            state["stages"][sid] = record
            atomic_json(state_path, state)
            return record, "recovered-verified"
        except (PipelineError, OSError) as exc:
            prior.update(status="BLOCKED", error=f"failed attempt left partial/unverified outputs; manual repair required: {exc}")
            atomic_json(state_path, state)
            return prior, "blocked"
    if prior and prior.get("status") in ("RUNNING", "BLOCKED") and any_output:
        prior.update(status="BLOCKED", error="partial stage outputs require manual cleanup or repair")
        atomic_json(state_path, state)
        return prior, "blocked"
    if any_output and not resume:
        record = {"status": "BLOCKED", "error": "refusing to overwrite existing training/output artifacts"}
        state["stages"][sid] = record
        atomic_json(state_path, state)
        return record, "blocked"

    vector = _command(stage, root)
    if dry_run:
        return {"status": "NOT_RUN", "command": vector, "fingerprint": fingerprint}, "dry"
    attempts = list(prior.get("attempts", [])) if prior else []
    log_path = log_dir / f"{state['run_id']}_{sid}_attempt{len(attempts)+1}.log"
    record = {"status": "RUNNING", "fingerprint": fingerprint, "log_path": str(log_path), "attempts": attempts}
    state["stages"][sid] = record
    atomic_json(state_path, state)
    started = time.monotonic()
    exit_code: int | None = None
    error = None
    with log_path.open("x", encoding="utf-8", newline="\n") as log:
        if vector is None:
            log.write("BUILTIN verification stage; no subprocess command\n")
            exit_code = 0
        else:
            log.write("argv=" + json.dumps(vector, ensure_ascii=False) + "\n")
            log.flush()
            try:
                proc = subprocess.run(vector, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                                      timeout=int(stage["timeout_seconds"]), check=False, shell=False)
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                exit_code = 124
                error = "stage timed out"
            except OSError as exc:
                exit_code = 127
                error = str(exc)
    duration = time.monotonic() - started
    attempt = {"log_path": str(log_path), "exit_code": exit_code, "duration_seconds": round(duration, 6), "finished_utc": now()}
    if error:
        attempt["error"] = error
    attempts.append(attempt)
    record["attempts"] = attempts
    record["exit_code"] = exit_code
    record["duration_seconds"] = round(duration, 6)
    if exit_code != 0:
        record.update(status="FAILED", error=error or f"subprocess exit code {exit_code}", finished_utc=now())
        state["stages"][sid] = record
        atomic_json(state_path, state)
        return record, "failed"
    try:
        evidence = verify(stage, root, ext, cfg)
        artifacts = evidence.get("artifact_sha256") or _artifact_hashes(stage, root, ext)
        record.update(status="COMPLETE", artifact_sha256=artifacts, evidence=evidence,
                      scientific_status=evidence.get("scientific_status"), finished_utc=now())
        state["stages"][sid] = record
        atomic_json(state_path, state)
        return record, "complete"
    except (PipelineError, OSError) as exc:
        record.update(status="FAILED", error=f"command succeeded but output verification failed: {exc}", finished_utc=now())
        state["stages"][sid] = record
        atomic_json(state_path, state)
        return record, "failed"


def run_pipeline(cfg: dict, config_sha: str, root: Path, outdir: Path, mode: str,
                 execute: bool = False, dry_run: bool = False) -> int:
    ext = [Path(p) for p in cfg.get("allowed_external_roots", [])]
    state_path = outdir / "state.json"
    outdir.mkdir(parents=True, exist_ok=True)
    if mode == "run" and dry_run:
        for stage in cfg["stages"]:
            inputs = input_manifest(stage, root, ext)
            print(json.dumps({"stage": stage["id"], "argv": _command(stage, root), "input_sha256": inputs}, ensure_ascii=False))
        return 0
    # One lock per selected study tree prevents two controller instances from
    # racing even when their state/log output directories differ.
    lock_path = root / ".donut_pxrd_serial_pipeline.lock"
    with FileLock(lock_path):
        if mode == "run" and not execute and not dry_run:
            raise PipelineError("real run requires --execute; use --dry-run to preview")
        if mode == "resume" and not state_path.is_file():
            state = {"schema": SCHEMA, "run_id": "resume-" + uuid.uuid4().hex, "created_utc": now(), "config_sha256": config_sha,
                     "repo_root": str(root.resolve()), "stages": {}}
            atomic_json(state_path, state)
        elif state_path.exists():
            state = _json(state_path)
            if state.get("schema") != SCHEMA or state.get("config_sha256") != config_sha or state.get("repo_root") != str(root.resolve()):
                raise PipelineError("state belongs to a different config or selected repository")
        else:
            state = {"schema": SCHEMA, "run_id": uuid.uuid4().hex, "created_utc": now(), "config_sha256": config_sha,
                     "repo_root": str(root.resolve()), "stages": {}}
            atomic_json(state_path, state)
        log_dir = outdir / "logs"
        log_dir.mkdir(exist_ok=True)
        stopped = False
        for stage in cfg["stages"]:
            sid = stage["id"]
            if stopped:
                state["stages"].setdefault(sid, {"status": "BLOCKED", "error": "upstream stage did not complete"})
                atomic_json(state_path, state)
                continue
            if any(state["stages"].get(dep, {}).get("status") != "COMPLETE" for dep in stage.get("depends_on", [])):
                state["stages"][sid] = {"status": "BLOCKED", "error": "precedence gate not complete"}
                atomic_json(state_path, state)
                stopped = True
                continue
            if stage["id"] == "exp4" and not dry_run and external_worker_active(root):
                state["stages"][sid] = {"status": "BLOCKED", "error": "another DONUT study worker process is active; GPU stage not launched"}
                atomic_json(state_path, state)
                stopped = True
                continue
            record, result = _stage_run(stage, root, ext, cfg, state, state_path, log_dir, config_sha,
                                        resume=(mode == "resume"), dry_run=dry_run)
            print(f"{sid}: {record['status']} ({result})")
            if result in ("failed", "blocked"):
                stopped = True
        state["updated_utc"] = now()
        state["pipeline_status"] = "COMPLETE" if all(state["stages"].get(s["id"], {}).get("status") == "COMPLETE" for s in cfg["stages"]) else "INCOMPLETE"
        atomic_json(state_path, state)
        return 0 if state["pipeline_status"] == "COMPLETE" else 2


def _mock_worker(args: argparse.Namespace) -> int:
    output = Path(args.mock_output)
    if args.mock_behavior == "fail-once":
        marker = Path(args.mock_marker)
        try:
            fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        except FileExistsError:
            pass
        else:
            print("intentional smoke failure", file=sys.stderr)
            return 23
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(args.mock_payload + "\n", encoding="utf-8")
    print(f"wrote {output}")
    return 0


def smoke(outdir: Path) -> int:
    """Run four tiny subprocesses: two pass, one fails once, recovery resumes."""
    outdir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="donut-pipeline-smoke-") as temp:
        root = Path(temp)
        (root / "mock.py").write_text("# subprocess target is the stdlib controller\n", encoding="utf-8")
        script = str(Path(__file__).resolve())
        marker = root / "fail-once.marker"
        stages = []
        for sid in ("mock_preflight", "mock_exp1", "mock_exp2"):
            out = f"mock_outputs/{sid}.json"
            stages.append({"id": sid, "depends_on": [stages[-1]["id"]] if stages else [], "timeout_seconds": 30,
                           "command": [sys.executable, script, "--mock-worker", "--mock-output", out, "--mock-payload", sid],
                           "required_outputs": [out], "inputs": [], "verifier": "files"})
        out = "mock_outputs/mock_exp3.json"
        stages.append({"id": "mock_exp3", "depends_on": ["mock_exp2"], "timeout_seconds": 30,
                       "command": [sys.executable, script, "--mock-worker", "--mock-behavior", "fail-once", "--mock-marker", str(marker),
                                   "--mock-output", out, "--mock-payload", "mock_exp3"],
                       "required_outputs": [out], "inputs": [], "verifier": "files"})
        cfg = {"schema": "donut_pxrd_serial_pipeline_v1", "study_config_sha256": EXPECTED_CONFIG_SHA256,
               "seeds": SEEDS, "policy": {"q_parent_count": 512,
               "frozen_split_counts": {"train": 358, "validation": 77, "test": 77}, "max_epochs": 30, "test_tuning": False},
               "allowed_external_roots": [], "stages": stages}
        config_path = root / "smoke.json"
        atomic_json(config_path, cfg)
        loaded, digest = load_config(config_path)
        first = run_pipeline(loaded, digest, root, root / "state", "run", execute=True)
        state1 = _json(root / "state/state.json")
        if first != 2 or state1["stages"]["mock_exp3"]["status"] != "FAILED":
            raise PipelineError("smoke did not stop on the intentional subprocess failure")
        second = run_pipeline(loaded, digest, root, root / "state", "resume")
        state2 = _json(root / "state/state.json")
        if second != 0 or any(state2["stages"][s]["status"] != "COMPLETE" for s in ("mock_preflight", "mock_exp1", "mock_exp2", "mock_exp3")):
            raise PipelineError("smoke resume did not recover to all mock stages complete")
        if any(state2["stages"][s].get("resume_action") != "SKIPPED_VERIFIED" for s in ("mock_preflight", "mock_exp1", "mock_exp2")):
            raise PipelineError("smoke resume did not skip previously verified complete stages")
        summary = {"status": "PASS", "first_exit_code": first, "resume_exit_code": second,
                   "intentional_failure_exit_code": state1["stages"]["mock_exp3"]["exit_code"],
                   "stage_order": [s["id"] for s in stages], "resume_skips": ["mock_preflight", "mock_exp1", "mock_exp2"],
                   "scientific_training_launched": False}
        atomic_json(outdir / "smoke_report.json", summary)
        print(json.dumps(summary, indent=2))
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("donut_pxrd/configs/serial_pipeline_v1.json"))
    parser.add_argument("--repo-root", type=Path, help="explicit study repository root")
    parser.add_argument("--mode", choices=("inspect", "smoke", "run", "resume"), default="inspect")
    parser.add_argument("--output-dir", type=Path, help="state/log output; for inspect keep outside repo-root")
    parser.add_argument("--execute", action="store_true", help="explicit authorization to launch real stage commands")
    parser.add_argument("--dry-run", action="store_true", help="print the real command plan without launching stages")
    parser.add_argument("--mock-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--mock-output", help=argparse.SUPPRESS)
    parser.add_argument("--mock-payload", default="ok", help=argparse.SUPPRESS)
    parser.add_argument("--mock-behavior", choices=("success", "fail-once"), default="success", help=argparse.SUPPRESS)
    parser.add_argument("--mock-marker", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.mock_worker:
        if not args.mock_output:
            parser.error("--mock-output is required")
        if args.mock_behavior == "fail-once" and not args.mock_marker:
            parser.error("--mock-marker is required for fail-once")
        return _mock_worker(args)
    try:
        if args.repo_root is None or args.output_dir is None:
            parser.error("--repo-root and --output-dir are required")
        root = args.repo_root.resolve()
        outdir = args.output_dir.resolve()
        if args.mode == "smoke":
            return smoke(outdir)
        cfg_path = args.config.resolve()
        cfg, config_sha = load_config(cfg_path)
        if args.mode == "inspect":
            if within(outdir, root):
                raise PipelineError("inspect output-dir must be outside the inspected repo-root")
            report = inspect(cfg, config_sha, root, outdir)
            print(json.dumps({"report": str(outdir / "inspect_report.json"),
                              "stages": [{"id": s["id"], "status": s["status"], "verified": s["verified"]} for s in report["stages"]]}, indent=2))
            return 0
        if not root.is_dir():
            raise PipelineError(f"repo-root does not exist: {root}")
        return run_pipeline(cfg, config_sha, root, outdir, args.mode, execute=args.execute, dry_run=args.dry_run)
    except (PipelineError, OSError, ValueError) as exc:
        print(f"pipeline error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
