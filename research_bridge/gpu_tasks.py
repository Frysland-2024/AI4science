"""Approved GPU lane with manual stop and safe public result publication."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from . import worker as w

LABEL = "bridge-gpu-approved"
PREFIX = "[Bridge GPU] "
PRESETS = {
    "forward_ab": {
        "entry": "pxrd_autolab/run.py",
        "config": "pxrd_autolab/configs/forward_ab_pilot.json",
    },
    "forward_speed_benchmark": {
        "entry": "pxrd_autolab/benchmark_gpu.py",
        "config": "pxrd_autolab/configs/forward_speed_benchmark.json",
    },
}
FIELDS = {"preset", "approved_sha", "config", "config_sha256", "run_id"}
RESULT_FILES = ("run_manifest.json", "gate_report.json", "metrics.json",
                "TECHNICAL_REPORT.md", "test_summary.json")
REQUIRED_RESULT_FILES = RESULT_FILES[:4]
MAX_RESULT_FILE_BYTES = 256 * 1024
MAX_RESULT_TOTAL_BYTES = 768 * 1024
STOP_POLL_SECONDS = 5
HEARTBEAT_SECONDS = 30


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def parse(issue):
    try:
        d = json.loads(issue["body"], object_pairs_hook=_unique_object)
    except (KeyError, ValueError, TypeError) as exc:
        raise w.BridgeError("GPU task body must contain valid JSON") from exc
    if not isinstance(d, dict) or set(d) != FIELDS:
        raise w.BridgeError("GPU task fields mismatch; max_minutes and extra fields are forbidden")
    if any(not isinstance(d[key], str) for key in FIELDS):
        raise w.BridgeError("GPU task fields must be strings")
    if d["preset"] not in PRESETS:
        raise w.BridgeError("GPU preset is not registered")
    if not re.fullmatch(r"[0-9a-f]{40}", d["approved_sha"]):
        raise w.BridgeError("Invalid approved source commit")
    if not re.fullmatch(r"[0-9a-f]{64}", d["config_sha256"]):
        raise w.BridgeError("Invalid config digest")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,39}", d["run_id"]):
        raise w.BridgeError("Invalid run identifier")
    if d["config"] != PRESETS[d["preset"]]["config"] or not w.safe_relpath(d["config"]):
        raise w.BridgeError("Config path does not match the registered preset")
    return d


def eligible(issue):
    labels = {x.get("name") for x in issue.get("labels", [])}
    if issue.get("state") != "open" or "pull_request" in issue:
        return False
    if issue.get("user", {}).get("login", "").lower() != w.OWNER.lower():
        return False
    if not issue.get("title", "").startswith(PREFIX):
        return False
    if not {w.READY, LABEL}.issubset(labels):
        return False
    if {w.APPROVED, "bridge-code-approved", w.RUNNING, w.REVIEW, w.FAILED}.intersection(labels):
        return False
    try:
        parse(issue)
        return True
    except w.BridgeError:
        return False


def pending():
    raw = w.gh(["api", "repos/" + w.REPO + "/issues?state=open&labels=" + w.READY
                + "%2C" + LABEL + "&per_page=50"])
    return sorted((i for i in json.loads(raw) if eligible(i)), key=lambda i: i["number"])


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def _utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _run_python():
    """Resolve a local administrator-selected Python; Issues cannot select executables."""
    configured = os.environ.get("AI4SCIENCE_GPU_PYTHON")
    default = Path(r"E:\AI4science\.venvs\xrd_test\Scripts\python.exe")
    candidate = Path(configured).expanduser() if configured else default
    if configured and not candidate.is_file():
        raise w.BridgeError("AI4SCIENCE_GPU_PYTHON does not name an existing file")
    if not candidate.is_file():
        candidate = Path(sys.executable)
    if not candidate.is_file():
        raise w.BridgeError("No approved Python interpreter is available")
    return str(candidate.resolve())


def _gpu_env():
    env = w.codex_env()
    secret_name = re.compile(r"(?:TOKEN|SECRET|PASSWORD|CREDENTIAL|API_KEY|ACCESS_KEY|AUTH)", re.I)
    cloud_name = re.compile(r"^(?:AWS_|AZURE_|GOOGLE_|CLOUDSDK_|KUBECONFIG$|NETRC$)", re.I)
    for key in list(env):
        if secret_name.search(key) or cloud_name.search(key):
            env.pop(key, None)
    env["PYTHONUNBUFFERED"] = "1"
    return env


class _WindowsProcessJob:
    """Kill descendants together with the runner when the owning handle closes."""
    def __init__(self, kernel32, handle):
        self.kernel32 = kernel32
        self.handle = handle

    def terminate(self):
        return bool(self.kernel32.TerminateJobObject(self.handle, 1))

    def close(self):
        if self.handle:
            self.kernel32.CloseHandle(self.handle)
            self.handle = None


def _attach_windows_job(proc):
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class BasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class ExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimitInformation),
            ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = (
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    kernel32.TerminateJobObject.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL

    handle = kernel32.CreateJobObjectW(None, None)
    if not handle:
        raise w.BridgeError("Could not create a Windows process job")
    job = _WindowsProcessJob(kernel32, handle)
    limits = ExtendedLimitInformation()
    limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel32.SetInformationJobObject(
            handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
        job.close()
        raise w.BridgeError("Could not configure Windows process-tree cleanup")
    if not kernel32.AssignProcessToJobObject(handle, wintypes.HANDLE(proc._handle)):
        job.terminate()
        job.close()
        raise w.BridgeError("Could not attach runner to Windows process-tree cleanup")
    return job


def _terminate_tree(pid, job=None):
    if job is not None and job.terminate():
        return
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(pid, signal.SIGTERM)
            time.sleep(0.2)
            os.killpg(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def _run_process(cmd, *, cwd, out, stop_path, env, poll_interval=STOP_POLL_SECONDS):
    """Stream logs to disk and monitor STOP without imposing a wall-clock timeout."""
    stdout_path, stderr_path = out / "stdout.log", out / "stderr.log"
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    popen_options = {"cwd": cwd, "env": env, "stdout": None, "stderr": None,
                     "stdin": subprocess.DEVNULL, "shell": False,
                     "creationflags": creationflags}
    if os.name != "nt":
        popen_options["start_new_session"] = True
    started = time.monotonic()
    last_heartbeat = 0.0
    with stdout_path.open("ab") as stdout_log, stderr_path.open("ab") as stderr_log:
        popen_options["stdout"], popen_options["stderr"] = stdout_log, stderr_log
        proc = subprocess.Popen(cmd, **popen_options)
        job = None
        try:
            job = _attach_windows_job(proc)
        except Exception:
            _terminate_tree(proc.pid)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            raise
        try:
            while proc.poll() is None:
                elapsed = time.monotonic() - started
                if stop_path.exists():
                    _terminate_tree(proc.pid, job=job)
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    _write_json(out / "heartbeat.json", {
                        "status": "STOPPED", "updated_utc": _utc_now(),
                        "elapsed_seconds": round(elapsed, 1),
                    })
                    return proc.returncode, True
                if elapsed - last_heartbeat >= HEARTBEAT_SECONDS:
                    _write_json(out / "heartbeat.json", {
                        "status": "RUNNING", "updated_utc": _utc_now(),
                        "elapsed_seconds": round(elapsed, 1),
                        "stdout_bytes": stdout_log.tell(), "stderr_bytes": stderr_log.tell(),
                    })
                    last_heartbeat = elapsed
                time.sleep(poll_interval)
            code = proc.returncode
            if code != 0:
                _terminate_tree(proc.pid, job=job)
            _write_json(out / "heartbeat.json", {
                "status": "EXITED", "updated_utc": _utc_now(),
                "elapsed_seconds": round(time.monotonic() - started, 1),
                "return_code": code,
            })
        finally:
            if job is not None:
                job.close()
    return code, False


def _read_gate_status(out):
    try:
        data = json.loads((out / "gate_report.json").read_text(encoding="utf-8"))
        return str(data.get("status", "")).upper()
    except (OSError, ValueError, TypeError):
        return ""


def _ensure_artifacts(out, *, run_status, detail):
    for name in ("stdout.log", "stderr.log"):
        (out / name).touch(exist_ok=True)
    if not (out / "gate_report.json").exists():
        _write_json(out / "gate_report.json", {
            "schema_version": 1, "status": run_status,
            "summary": detail, "gates": [],
        })
    if not (out / "metrics.json").exists():
        _write_json(out / "metrics.json", {
            "schema_version": 1, "status": run_status, "metrics": {},
        })
    if not (out / "TECHNICAL_REPORT.md").exists():
        (out / "TECHNICAL_REPORT.md").write_text(
            "# GPU bridge run report\n\n"
            f"Status: **{run_status}**\n\n{detail}\n\n"
            "No scientific performance claim is made by this bridge record.\n",
            encoding="utf-8")


def _classify_result(return_code, stopped, out):
    if stopped:
        return "STOPPED"
    try:
        metrics_status = str(json.loads((out / "metrics.json").read_text(encoding="utf-8")).get("status", "")).upper()
        if metrics_status.startswith("BLOCKED"):
            return metrics_status
    except (OSError, ValueError, TypeError):
        pass
    gate_status = _read_gate_status(out)
    if gate_status.startswith("BLOCKED") or return_code == 3:
        return gate_status if gate_status.startswith("BLOCKED") else "BLOCKED"
    if return_code == 0:
        return "SUCCESS"
    return "FAILED"


def _redact_public_text(text):
    patterns = [
        (r"(?i)\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|glpat-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}|sk-[A-Za-z0-9_-]{20,})\b", "[REDACTED_TOKEN]"),
        (r"(?i)\b(?:AKIA|ASIA)[A-Z0-9]{16}\b", "[REDACTED_AWS_KEY]"),
        (r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/-]+=*", r"\1 [REDACTED]"),
        (r"(?i)\b(?:authorization|proxy-authorization|x-api-key)\s*[:=]\s*[^\r\n]+", "[REDACTED_AUTH]"),
        (r"(?i)((?:api[-_]?key|access[-_]?token|refresh[-_]?token|token|password|passwd|secret|credential|client[-_]?secret)\s*[:=]\s*)([\"']?)[^\s\"',;]+", r"\1[REDACTED]"),
        (r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", "[REDACTED_PRIVATE_KEY]"),
        (r"(?<![\w])(?:[A-Za-z]:[\\/]|\\\\[^\s\\]+\\[^\s\\]+\\)[^\r\n\t\"<>|]+", "[LOCAL_PATH]"),
        (r"(?<![:/\w])/(?:Users|home|tmp|var|mnt|private|Volumes|root|workspace|workspaces|runner|opt|data|app|etc|dev|proc|sys|build|agent|agents|work|repo|repositories|scratch|cluster|local|media|run|storage|srv|jobs|project|projects|source|src)(?:/[^\s\"'<>|]*)?", "[LOCAL_PATH]"),
    ]
    value = text
    for pattern, replacement in patterns:
        value = re.sub(pattern, replacement, value)
    return value


def _sanitize_json(value):
    if isinstance(value, dict):
        cleaned = {}
        secret_key = re.compile(
            r"(?:auth|token|secret|password|passwd|credential|api[-_]?key|access[-_]?key|private[-_]?key|ssh[-_]?key|signing[-_]?key)", re.I)
        for key, item in value.items():
            safe_key = _redact_public_text(str(key))
            cleaned[safe_key] = ("[REDACTED]" if secret_key.search(str(key))
                                 else _sanitize_json(item))
        return cleaned
    if isinstance(value, list):
        return [_sanitize_json(item) for item in value]
    if isinstance(value, str):
        return _redact_public_text(value)
    return value


def _public_artifacts(out):
    files = {}
    total = 0
    for name in RESULT_FILES:
        path = out / name
        if path.is_symlink():
            raise w.BridgeError("Public result artifact must not be a symlink: " + name)
        if not path.exists():
            if name in REQUIRED_RESULT_FILES:
                raise w.BridgeError("Required public result artifact is missing: " + name)
            continue
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise w.BridgeError("Public result artifact must be a regular non-symlink file: " + name)
        if info.st_size > MAX_RESULT_FILE_BYTES:
            raise w.BridgeError("Public result artifact exceeds size cap: " + name)
        data = path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise w.BridgeError("Public result artifacts must be UTF-8 text: " + name) from exc
        if name.endswith(".json"):
            try:
                decoded = json.loads(text)
            except ValueError as exc:
                raise w.BridgeError("Public JSON artifact is invalid: " + name) from exc
            sanitized = (json.dumps(_sanitize_json(decoded), indent=2, sort_keys=True,
                                    ensure_ascii=False) + "\n").encode("utf-8")
        else:
            sanitized = _redact_public_text(text).encode("utf-8")
        if len(sanitized) > MAX_RESULT_FILE_BYTES:
            raise w.BridgeError("Sanitized public result artifact exceeds size cap: " + name)
        total += len(sanitized)
        files[name] = sanitized
    if total > MAX_RESULT_TOTAL_BYTES:
        raise w.BridgeError("Public result bundle exceeds total size cap")
    return files


def _git(args, cwd):
    try:
        proc = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True,
                              encoding="utf-8", errors="replace", timeout=180)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise w.BridgeError("Git publication command could not complete") from exc
    if proc.returncode:
        raise w.BridgeError("Git publication failed: " + _redact_public_text(proc.stderr[-500:]))
    return proc.stdout.strip()


def publish_results(root, out, *, run_id, source_commit, run_status):
    """Commit only allowlisted, bounded text artifacts on a source-based branch."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,39}", run_id):
        raise w.BridgeError("Unsafe result branch identifier")
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise w.BridgeError("Invalid source commit for result publication")
    files = _public_artifacts(out)
    origin = w.command(["git", "remote", "get-url", "origin"], cwd=root).strip()
    expected = "https://github.com/" + w.REPO + ".git"
    if origin.rstrip("/").removesuffix(".git").lower() != expected.removesuffix(".git").lower():
        raise w.BridgeError("Unexpected origin; refusing public result publication")
    branch = "bridge-results/" + run_id
    result_path = Path("bridge_results") / run_id
    with tempfile.TemporaryDirectory(prefix="ai4science-public-results-") as temp:
        clone = Path(temp) / "repo"
        _git(["clone", "--no-checkout", "--filter=blob:none", origin, str(clone)], cwd=temp)
        _git(["fetch", "--no-tags", "origin", source_commit], cwd=clone)
        _git(["checkout", "--detach", source_commit], cwd=clone)
        _git(["switch", "-c", branch], cwd=clone)
        destination = clone / result_path
        destination.mkdir(parents=True, exist_ok=False)
        for name, data in files.items():
            (destination / name).write_bytes(data)
        _git(["config", "user.name", "AI4science Research Bridge"], cwd=clone)
        _git(["config", "user.email", "research-bridge@users.noreply.github.com"], cwd=clone)
        _git(["add", "--", result_path.as_posix()], cwd=clone)
        _git(["commit", "-m", "Publish GPU run results " + run_id], cwd=clone)
        commit = _git(["rev-parse", "HEAD"], cwd=clone)
        _git(["push", "origin", "HEAD:refs/heads/" + branch], cwd=clone)
        result = {"status": "PUSHED", "branch": branch, "commit": commit,
                  "pull_request": None, "files": sorted(files)}
        with tempfile.TemporaryDirectory(prefix="ai4science-pr-body-") as body_dir:
            body_path = Path(body_dir) / "body.md"
            body_path.write_text(
                f"Automated public result bundle for run `{run_id}`.\n\n"
                f"Run status: `{run_status}`. Source commit: `{source_commit}`.\n\n"
                "This draft PR contains only the bridge allowlist of sanitized, bounded text artifacts. "
                "It does not certify scientific validity and is not auto-merged.\n",
                encoding="utf-8")
            try:
                result["pull_request"] = w.gh([
                    "pr", "create", "--repo", w.REPO, "--draft", "--base", "main",
                    "--head", branch, "--title", "[GPU results] " + run_id,
                    "--body-file", str(body_path),
                ]).strip()
                result["status"] = "PUSHED_DRAFT_PR"
            except Exception as exc:
                result["status"] = "PUSHED_PR_FAILED"
                result["pr_error"] = _redact_public_text(str(exc))[:500]
        return result


def _write_manifest(out, *, issue_number, info, source_commit, entry_blob, status,
                    return_code, stopped, publication=None, error=None):
    manifest = {
        "schema_version": 1,
        "status": status,
        "issue_number": issue_number,
        "run_id": info["run_id"],
        "preset": info["preset"],
        "source_commit": source_commit,
        "code_sha": {"path": PRESETS[info["preset"]]["entry"], "git_blob": entry_blob},
        "config": info["config"],
        "config_sha256": info["config_sha256"],
        "sources": [PRESETS[info["preset"]]["entry"], info["config"]],
        "return_code": return_code,
        "stopped_by_marker": stopped,
        "started_utc": _read_started(out),
        "finished_utc": _utc_now(),
        "publication_target": "bridge-results/" + info["run_id"],
        "scientific_certification": False,
    }
    if error:
        manifest["error"] = _redact_public_text(error)[:500]
    if publication:
        manifest["publication"] = {
            "status": publication.get("status"),
            "branch": publication.get("branch"),
            "draft_pr": publication.get("pull_request"),
        }
    _write_json(out / "run_manifest.json", manifest)


def _read_started(out):
    try:
        return json.loads((out / "run_started.json").read_text(encoding="utf-8"))["started_utc"]
    except (OSError, ValueError, KeyError, TypeError):
        return _utc_now()


def _notify(number, message, *, label_add, label_remove):
    errors = []
    try:
        w.comment(number, message)
    except Exception as exc:
        errors.append("comment: " + _redact_public_text(str(exc))[:300])
    try:
        w.label(number, label_add, label_remove)
    except Exception as exc:
        errors.append("label: " + _redact_public_text(str(exc))[:300])
    return errors


def run(root, issue, dry_run=False):
    info = parse(issue)
    number = issue["number"]
    if w.journal(root, number).exists():
        return
    if dry_run:
        print("DRY RUN GPU", number, info["preset"], "unbounded runtime; manual STOP marker")
        return

    base = w.revision(root)
    if base != info["approved_sha"]:
        raise w.BridgeError("Main changed; GPU run requires fresh approval")
    if not w.claim(root, number, "GPU_PREPARING", commit=base, run_id=info["run_id"]):
        return
    git_common = w.git_common_dir(root)
    out = git_common / "research_bridge" / "gpu_runs" / info["run_id"]
    if out.exists():
        w.record(root, number, "GPU_PRECHECK_FAILED", commit=base, run_id=info["run_id"],
                 error="Run ID already exists; no overwrite")
        raise w.BridgeError("Run ID already exists; no overwrite")
    try:
        out.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        w.record(root, number, "GPU_PRECHECK_FAILED", commit=base, run_id=info["run_id"],
                 error="Could not reserve run directory: " + str(exc)[:300])
        raise
    stop_path = out / "STOP"

    return_code, stopped, entry_blob, error = None, False, None, None
    started = _utc_now()
    _write_json(out / "run_started.json", {"started_utc": started})
    try:
        w.label(number, w.RUNNING, w.READY)
        w.record(root, number, "GPU_RUNNING", commit=base, run_id=info["run_id"],
                 output_dir=".git/research_bridge/gpu_runs/" + info["run_id"])
        preset = PRESETS[info["preset"]]
        with tempfile.TemporaryDirectory(prefix="research-bridge-gpu-") as tmp:
            workspace = Path(tmp) / "source"
            w.snapshot(root, workspace, base)
            cfg = workspace / info["config"]
            exe = workspace / preset["entry"]
            if cfg.is_symlink() or exe.is_symlink() or not cfg.is_file() or not exe.is_file():
                raise w.BridgeError("Approved runner or config is missing or symlinked")
            if hashlib.sha256(cfg.read_bytes()).hexdigest() != info["config_sha256"]:
                raise w.BridgeError("Config fingerprint mismatch")
            entry_blob = w.command(["git", "rev-parse", base + ":" + preset["entry"]], cwd=root).strip()
            cmd = [_run_python(), str(exe), "--config", str(cfg), "--output-dir", str(out),
                   "--source-commit", base]
            return_code, stopped = _run_process(cmd, cwd=workspace, out=out,
                                                stop_path=stop_path, env=_gpu_env())
    except Exception as exc:
        error = str(exc)
        if return_code is None:
            return_code = 1
    if not entry_blob:
        try:
            entry_blob = w.command(["git", "rev-parse", base + ":" + PRESETS[info["preset"]]["entry"]], cwd=root).strip()
        except Exception:
            entry_blob = None

    gate_status = _read_gate_status(out)
    provisional = _classify_result(return_code, stopped, out)
    if error and provisional == "SUCCESS":
        provisional = "FAILED"
    detail = error or ("Stopped by local STOP marker." if stopped else
                       "Runner returned code " + str(return_code) + ".")
    _ensure_artifacts(out, run_status=provisional, detail=detail)
    _write_manifest(out, issue_number=number, info=info, source_commit=base,
                    entry_blob=entry_blob, status=provisional, return_code=return_code,
                    stopped=stopped, error=error)

    publication = None
    publication_error = None
    try:
        publication = publish_results(root, out, run_id=info["run_id"],
                                      source_commit=base, run_status=provisional)
    except Exception as exc:
        publication_error = _redact_public_text(str(exc))[:500]
        _write_json(out / "publication.json", {
            "status": "FAILED", "updated_utc": _utc_now(), "error": publication_error,
            "target_branch": "bridge-results/" + info["run_id"],
        })

    result = {"run_status": provisional, "return_code": return_code,
              "publication": publication, "publication_error": publication_error,
              "logs": ["stdout.log", "stderr.log"]}
    if publication:
        _write_json(out / "publication.json", publication)
    status = ("GPU_PUBLICATION_FAILED" if publication_error or
              (publication and publication.get("status") == "PUSHED_PR_FAILED") else
              "GPU_" + provisional)
    w.record(root, number, status, commit=base, run_id=info["run_id"], **result)

    if publication_error or (publication and publication.get("status") == "PUSHED_PR_FAILED"):
        message = ("GPU run status: " + provisional + ". Automatic GitHub result publication did not fully complete. "
                   "The local error trail is in .git/research_bridge/gpu_runs/" + info["run_id"] +
                   "; inspect the worker journal before retrying. " +
                   (publication_error or publication.get("pr_error", "Draft PR creation failed.")))
        errors = _notify(number, message, label_add=w.FAILED, label_remove=w.RUNNING)
    elif provisional in ("FAILED", "STOPPED"):
        publication_ref = publication.get("pull_request") or publication.get("branch")
        errors = _notify(number, "GPU run status: " + provisional + ". Results: " +
                         str(publication_ref) + ". Inspect the dedicated results PR; no auto-merge occurred.",
                         label_add=w.FAILED, label_remove=w.RUNNING)
    else:
        publication_ref = publication.get("pull_request") or publication.get("branch")
        errors = _notify(number, "GPU run status: " + provisional + ". Public result bundle: " +
                         str(publication_ref) + ". This is a draft result record, not scientific certification.",
                         label_add=w.REVIEW, label_remove=w.RUNNING)
    if errors:
        result["notification_errors"] = errors
        w.record(root, number, status, commit=base, run_id=info["run_id"], **result)
    return result
