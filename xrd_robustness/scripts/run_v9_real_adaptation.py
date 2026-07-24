"""Fail-closed planning entrypoint for V9 real-domain adaptation.

No training or inference command is implemented. The `run` command always refuses
execution until the frozen contract is integrated with an approved trainer.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from xrd_robustness.evaluation.real_adaptation import (
    audit_real_adaptation_contract,
    build_real_adaptation_plan,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = PROJECT_ROOT / "configs" / "real_adaptation.v9.method_transfer.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preflight", "plan", "run"))
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--include-secondary", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.command == "preflight":
        payload = audit_real_adaptation_contract(
            args.contract,
            project_root=args.project_root,
            require_local_data=False,
        )
        default_output = PROJECT_ROOT / "reports" / "v9_real_adaptation_preflight.json"
    elif args.command == "plan":
        audit = audit_real_adaptation_contract(
            args.contract,
            project_root=args.project_root,
            require_local_data=False,
        )
        if audit["status"] == "fail":
            payload = audit
        else:
            payload = build_real_adaptation_plan(
                args.contract,
                include_secondary=args.include_secondary,
            )
            payload["preflight_status"] = audit["status"]
        default_output = PROJECT_ROOT / "reports" / "v9_real_adaptation_plan.json"
    else:
        payload = {
            "schema_version": "v9-real-adaptation-execution-refusal-v1",
            "status": "refused_execution_disabled",
            "reason": (
                "real-adaptation training and final real-test inference are not implemented "
                "or authorized; only preflight and plan are allowed"
            ),
            "model_loaded": False,
            "spectra_loaded": False,
        }
        default_output = PROJECT_ROOT / "reports" / "v9_real_adaptation_execution_refusal.json"

    output = Path(args.output).resolve() if args.output else default_output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "output": str(output)}, indent=2))
    return 1 if payload["status"] in {"fail", "refused_execution_disabled"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
