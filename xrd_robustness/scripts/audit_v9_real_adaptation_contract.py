"""Audit the frozen V9 real-adaptation contract without model or spectrum access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from xrd_robustness.evaluation.real_adaptation import audit_real_adaptation_contract


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--contract",
        default=str(PROJECT_ROOT / "configs" / "real_adaptation.v9.method_transfer.json"),
    )
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--require-local-data", action="store_true")
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "reports" / "v9_real_adaptation_contract_audit.json"),
    )
    args = parser.parse_args()

    report = audit_real_adaptation_contract(
        args.contract,
        project_root=args.project_root,
        require_local_data=args.require_local_data,
    )
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(output)}, indent=2))
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
