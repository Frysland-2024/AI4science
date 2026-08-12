"""Audit or plan an explicitly retrospective, non-confirmatory RRUFF-301 replay.

``run-replay`` is intentionally a fail-closed refusal in this repair.  No command
in this script imports a model, loads spectrum arrays, trains, or runs inference.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Sequence

from xrd_robustness.evaluation.rruff301_replay import (
    audit_existing_artifacts,
    build_retrospective_episode_plan,
    build_run_replay_refusal,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = PROJECT_ROOT / "configs" / "rruff301_retrospective_replay.v1.json"


def _atomic_write_new_json(path: Path, payload: object) -> None:
    """Write a new report atomically and refuse to replace an existing artifact."""

    path = path.resolve()
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    if temporary.exists():
        raise FileExistsError(f"temporary output already exists: {temporary}")
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fail-closed RRUFF-301 retrospective replay audit and planning"
    )
    parser.add_argument(
        "command",
        choices=("audit-existing", "plan-replay", "run-replay"),
    )
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--output")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Compute and validate the requested audit or plan without writing a report.",
    )
    parser.add_argument(
        "--allow-missing-local-artifacts",
        action="store_true",
        help=(
            "Inventory mode only: permit a provenance-incomplete report when registered "
            "local artifacts are absent. Missing artifacts fail by default."
        ),
    )
    parser.add_argument(
        "--verify-checkpoints",
        action="store_true",
        help="Hash all ten local checkpoints during audit-existing.",
    )
    parser.add_argument(
        "--authorization",
        help="Recorded only by run-replay; it cannot enable this disabled v1 runner.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.command == "audit-existing":
        payload = audit_existing_artifacts(
            args.contract,
            project_root=args.project_root,
            require_local_artifacts=not args.allow_missing_local_artifacts,
            verify_checkpoints=args.verify_checkpoints,
        )
        default_output = PROJECT_ROOT / "reports" / "rruff301_existing_artifact_lineage_audit.json"
        exit_code = 1 if payload["status"] == "fail" else 0
    elif args.command == "plan-replay":
        try:
            payload = build_retrospective_episode_plan(
                args.contract,
                project_root=args.project_root,
            )
            exit_code = 0
        except Exception as exc:
            payload = {
                "schema_version": "rruff301-retrospective-replay-v1",
                "status": "fail",
                "evidence_role": "reproducibility_replay_not_confirmatory",
                "historical_plan_claim": False,
                "model_loaded": False,
                "spectra_loaded": False,
                "errors": [str(exc)],
            }
            exit_code = 1
        default_output = PROJECT_ROOT / "reports" / "rruff301_retrospective_replay_episode_plan.json"
    else:
        payload = build_run_replay_refusal(
            args.contract,
            project_root=args.project_root,
            authorization_path=args.authorization,
        )
        default_output = PROJECT_ROOT / "reports" / "rruff301_retrospective_replay_execution_refusal.json"
        exit_code = 2

    output = Path(args.output).resolve() if args.output else default_output.resolve()
    if not args.check_only:
        try:
            _atomic_write_new_json(output, payload)
        except FileExistsError as exc:
            print(
                json.dumps(
                    {"status": "refused_output_exists", "reason": str(exc)},
                    indent=2,
                )
            )
            return 2

    print(
        json.dumps(
            {
                "status": payload["status"],
                "output": None if args.check_only else str(output),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
