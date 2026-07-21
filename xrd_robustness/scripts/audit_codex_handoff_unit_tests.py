#!/usr/bin/env python3
"""Run the complete source unit-test suite and persist compact handoff evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import time
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "codex_account_handoff_unittest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def _failure_rows(rows: list[tuple[unittest.case.TestCase, str]]) -> list[dict[str, str]]:
    return [{"test": str(test), "traceback": traceback} for test, traceback in rows]


def main() -> int:
    args = parse_args()
    sys.path.insert(0, str(PROJECT_ROOT))
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(PROJECT_ROOT / "tests"),
        pattern="test*.py",
    )
    stream = io.StringIO()
    started = time.monotonic()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    duration_seconds = time.monotonic() - started
    report = {
        "schema_version": "codex-account-handoff-unittest-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if result.wasSuccessful() else "fail",
        "purpose": "full source unit-test evidence; no training",
        "python": sys.executable,
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "expected_failures": len(result.expectedFailures),
        "unexpected_successes": len(result.unexpectedSuccesses),
        "duration_seconds": round(duration_seconds, 6),
        "failure_details": _failure_rows(result.failures),
        "error_details": _failure_rows(result.errors),
    }
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "tests_run": report["tests_run"],
                "failures": report["failures"],
                "errors": report["errors"],
                "output": str(output_path),
            },
            ensure_ascii=False,
        )
    )
    if not result.wasSuccessful():
        print(stream.getvalue(), file=sys.stderr)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
