"""Read-only V11 status summary; never launches, resumes, or modifies research runs.

Run on the *same host/filesystem* as V11. GitHub alone cannot verify a local
process; checking for an existing lock is not equivalent to probing that lock.
"""
from __future__ import annotations

import argparse
import errno
import json
import os
from pathlib import Path

STUDY_RELATIVE = Path("server_runs/v11_a0_js_optuna")


def _load(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"unreadable JSON: {path.name}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"JSON object expected: {path.name}")
    return data


def _lock_held(path: Path) -> bool | None:
    """True: another process holds the lock; False: confirmed free; None: unknown.

    Never create the lock: merely testing the existence of .study.lock would
    produce false positives after a process has exited.
    """
    if not path.is_file():
        return False
    try:
        with path.open("r+b") as stream:
            if os.name == "nt":
                import msvcrt
                stream.seek(0)
                try:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError as exc:
                    return True if exc.errno in (errno.EACCES, errno.EAGAIN) else None
                else:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                    return False
            import fcntl
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                return True if exc.errno in (errno.EACCES, errno.EAGAIN) else None
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
                return False
    except OSError:
        return None


def summarize(study: Path) -> dict:
    """No Test/RRUFF, GPU, Optuna import, network, or write operations."""
    output = {
        "schema": "ai4science-v11-human-handoff-v1",
        "study": str(study),
        "status": "NEEDS_DECISION",
        "stage": "CUIFA_STAGE0",
        "completed_hpo_trials": 0,
        "expected_hpo_trials": None,
        "confirmation_results": 0,
        "live_runner_lock": "NOT_OBSERVED",
        "next_action": "Verify cuifa Stage 0 and approve HPO budget before launching training.",
        "boundary": "Local read-only summary; never certifies scientific results or Test/RRUFF execution.",
    }
    try:
        contract = _load(study / "contract.json")
        count = None
        if contract is not None:
            count = contract.get("max_new_trials")
            if not isinstance(count, int) or isinstance(count, bool) or count < 1:
                raise ValueError("invalid HPO trial budget")
            output["expected_hpo_trials"] = count
        trials = study / "trials"
        if trials.is_dir():
            for path in sorted(trials.glob("hpo_*/result.json")):
                row = _load(path)
                if row.get("status") != "completed":
                    raise ValueError(f"incomplete HPO result: {path.parent.name}")
                output["completed_hpo_trials"] += 1
            for path in sorted(trials.glob("confirm_*/result.json")):
                row = _load(path)
                if row.get("status") != "completed":
                    raise ValueError(f"incomplete confirmation: {path.parent.name}")
                output["confirmation_results"] += 1
        if contract and output["completed_hpo_trials"] > count:
            raise ValueError("more HPO results than frozen contract permits")
        recommendation = _load(study / "final_recommendation.json")
        final = _load(study / "final_training_summary.json")
        if contract is None and (output["completed_hpo_trials"] or output["confirmation_results"]
                                 or recommendation is not None or final is not None):
            raise ValueError("result artifacts exist without frozen study contract")
        if final is not None:
            seeds = final.get("runs")
            if (final.get("status") != "final_three_seed_training_completed"
                    or not isinstance(seeds, list) or len(seeds) != 3
                    or len({r.get("seed") for r in seeds if isinstance(r, dict)}) != 3):
                raise ValueError("final summary missing valid three-seed completion evidence")
            if recommendation is None or recommendation.get("status") != "hpo_and_confirmation_completed":
                raise ValueError("final summary exists without completed HPO recommendation")
            if (recommendation.get("hpo_trial_count") != count
                    or output["completed_hpo_trials"] != count
                    or output["confirmation_results"] != 2):
                raise ValueError("final summary exists without complete HPO and confirmation evidence")
            output.update(status="COMPLETED", stage="FINAL_TRAINING_EVIDENCE",
                          next_action="Review checkpoint hashes and authorize independent Test/RRUFF only if appropriate; not run by this tool.")
        elif recommendation is not None:
            if (recommendation.get("status") != "hpo_and_confirmation_completed"
                    or recommendation.get("hpo_trial_count") != count
                    or output["completed_hpo_trials"] != count
                    or output["confirmation_results"] != 2):
                raise ValueError("HPO recommendation is inconsistent with local completion evidence")
            output.update(status="NEEDS_DECISION", stage="HPO_CONFIRMED",
                          next_action="Review frozen HPO results and independently approve final training; never auto-advance.")
        elif contract is not None:
            output.update(stage="HPO_NOT_CONFIRMED",
                          next_action="Check host process and logs; incomplete study must not auto-resume or open Test/RRUFF.")
        lock = _lock_held(study / ".study.lock")
        output["live_runner_lock"] = "HELD" if lock is True else "FREE" if lock is False else "UNKNOWN"
        if lock is True and output["status"] != "COMPLETED":
            output.update(status="RUNNING", next_action="Active V11 runner lock detected on this host; check logs only at the next review window.")
        elif lock is None and contract is not None and output["status"] != "COMPLETED":
            output.update(status="NEEDS_DECISION", next_action="Runner lock could not be probed: check host, do not assume RUNNING.")
    except (OSError, ValueError, TypeError) as exc:
        output.update(status="BLOCKED", stage="EVIDENCE_INCONSISTENT",
                      next_action=f"Inspect locally before any continuation: {exc}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-dir", type=Path, default=Path(__file__).resolve().parents[1] / STUDY_RELATIVE)
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    args = parser.parse_args()
    result = summarize(args.study_dir)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"AI4science V11 | {result['status']} | {result['stage']}")
        print(f"HPO: {result['completed_hpo_trials']}/{result['expected_hpo_trials'] or '?'} completed; "
              f"confirmations: {result['confirmation_results']}/2; live lock: {result['live_runner_lock']}")
        print(f"Next: {result['next_action']}")
        print(result["boundary"])


if __name__ == "__main__":
    main()
