"""Audit the disabled V9 real-XRD preprocessing contract without inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from xrd_robustness.evaluation.real_xrd import audit_real_xrd_contract, audit_real_xrd_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=str(PROJECT_ROOT / "configs" / "real_test.v9.method_transfer.template.json"))
    parser.add_argument("--manifest")
    parser.add_argument("--output", default=str(PROJECT_ROOT / "reports" / "v9_real_test_preprocessing_readiness.json"))
    args = parser.parse_args()
    report = audit_real_xrd_contract(args.contract)
    if args.manifest:
        report["manifest_audit"] = audit_real_xrd_manifest(args.manifest)
    else:
        report["manifest_audit"] = "not_run_manifest_intentionally_absent"
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(output)}, indent=2))
    return 0 if report["status"] != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
