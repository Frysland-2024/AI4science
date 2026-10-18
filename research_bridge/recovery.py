"""Fail-closed resume eligibility checks; never launches work."""
from __future__ import annotations
import hashlib
import re
from pathlib import Path

NEEDED = ("source_sha", "config_sha256", "split_sha256", "checkpoint_sha256",
          "optimizer_sha256", "rng_sha256", "completed_step", "total_steps",
          "approved_budget_steps", "seed", "attempt")

def assess_resume(record: dict, checkpoint: Path) -> dict:
    missing = [key for key in NEEDED if key not in record]
    if missing:
        return {"resume_allowed": False, "reason": "MISSING_CONTRACT",
                "missing": missing}
    if not checkpoint.is_file() or checkpoint.is_symlink():
        return {"resume_allowed": False, "reason": "CHECKPOINT_MISSING"}
    if any(not re.fullmatch(r"[0-9a-f]{64}", record.get(key, ""))
           for key in ("config_sha256", "split_sha256", "checkpoint_sha256",
                       "optimizer_sha256", "rng_sha256")):
        return {"resume_allowed": False, "reason": "INVALID_HASH"}
    if not re.fullmatch(r"[0-9a-f]{40}", str(record.get("source_sha", ""))):
        return {"resume_allowed": False, "reason": "INVALID_SOURCE_SHA"}
    step, target, budget = (record["completed_step"], record["total_steps"],
                            record["approved_budget_steps"])
    if any(type(v) is not int for v in (step, target, budget)):
        return {"resume_allowed": False, "reason": "INVALID_STEP"}
    if not (0 <= step < target <= budget):
        return {"resume_allowed": False, "reason": "BUDGET_OR_STEP_INVALID"}
    digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    if digest != record["checkpoint_sha256"]:
        return {"resume_allowed": False, "reason": "CHECKPOINT_HASH_MISMATCH"}
    return {"resume_allowed": False, "reason": "MANUAL_APPROVAL_REQUIRED",
            "validated_checkpoint": True,
            "note": "Supervisor never starts/resumes training automatically"}
