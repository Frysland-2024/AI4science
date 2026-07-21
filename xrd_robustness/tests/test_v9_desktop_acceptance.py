from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]

from scripts.audit_v9_desktop_acceleration import compare_cases
from scripts.audit_v9_desktop_readiness import build_readiness
from xrd_robustness.method_transfer import (
    audit_contract_assets,
    build_tuning_plan,
    canonical_hash,
    load_contract,
)


CONTRACT_PATH = PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"


class DesktopAccelerationComparisonTests(unittest.TestCase):
    def test_compare_cases_checks_logits_loss_and_gradients(self) -> None:
        reference = {
            "logits": torch.tensor([[1.0, -1.0]]),
            "loss": 0.5,
            "gradients": {"model.weight": torch.tensor([1.0, 2.0])},
        }
        thresholds = {
            "logits_atol": 0.01,
            "logits_rtol": 0.01,
            "loss_atol": 0.01,
            "loss_rtol": 0.01,
            "gradient_cosine_min": 0.99,
            "gradient_relative_l2_max": 0.05,
        }
        self.assertTrue(compare_cases(reference, reference, thresholds)["passed"])
        changed = {
            "logits": torch.tensor([[2.0, -1.0]]),
            "loss": 0.8,
            "gradients": {"model.weight": torch.tensor([-1.0, 2.0])},
        }
        self.assertFalse(compare_cases(reference, changed, thresholds)["passed"])


class DesktopReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract(CONTRACT_PATH)
        self.asset_audit = audit_contract_assets(self.contract, PROJECT_ROOT)
        self.plan = build_tuning_plan(self.contract, PROJECT_ROOT)
        contract_sha256 = hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest().upper()
        exact_prefetch = {
            "status": "passed",
            "equivalence": {
                "exact_material_order": True,
                "exact_accepted_manifest_rows": True,
                "exact_parameters": True,
                "exact_spectrum_arrays": True,
                "quality_gate_counts_match": True,
                "sequential_parameter_pair_hash": "A" * 64,
                "prefetch_parameter_pair_hash": "A" * 64,
            },
        }
        runtime_checks = {
            name: True
            for name in (
                "python_version",
                "torch_version",
                "cuda_runtime",
                "cuda_available",
                "gpu_name",
                "gpu_memory",
                "bf16_supported",
                "pip_check",
                "msvc_toolchain_discoverable",
            )
        }
        self.reports = {
            "environment": {"status": "pass", "checks": runtime_checks},
            "migration": {"status": "pass"},
            "preflight": {
                "status": "passed",
                "hashes": self.asset_audit["hashes"],
                "runtime": {"ready_for_development_tuning": True},
            },
            "hardware": {
                "status": "target_detected_ready_for_no_training_benchmarks",
                "contract": {"sha256": contract_sha256},
            },
            "prefetch_8x8": exact_prefetch,
            "prefetch_4x8": exact_prefetch,
            "prefetch_matrix": {"status": "pass"},
            "cuda_transfer": {"status": "pass"},
            "evaluation_batch": {"status": "pass"},
            "acceleration": {
                "status": "pass",
                "contract": {"sha256": contract_sha256},
            },
        }

    def _build(self, **overrides: object) -> dict[str, object]:
        arguments = {
            "contract": self.contract,
            "contract_path": CONTRACT_PATH,
            "asset_audit": self.asset_audit,
            "expected_plan": self.plan,
            "plan": self.plan,
            "reports": self.reports,
            "process_probe_supported": True,
            "training_processes": [],
            "registry_present": True,
            "registry_runs": [],
            "checkpoint_count": 0,
            "result_count": 0,
        }
        arguments.update(overrides)
        return build_readiness(**arguments)

    def test_complete_evidence_is_ready_but_does_not_authorize_training(self) -> None:
        report = self._build()
        self.assertEqual(report["status"], "ready_for_explicit_tuning_authorization")
        self.assertFalse(
            report["execution_state"]["explicit_tuning_authorization_recorded"]
        )
        self.assertFalse(report["execution_state"]["training_started"])

    def test_missing_registry_or_compile_failure_blocks_readiness(self) -> None:
        self.reports["acceleration"] = {
            **self.reports["acceleration"],
            "status": "fail",
        }
        report = self._build(registry_present=False)
        self.assertEqual(report["status"], "blocked")
        self.assertIn("run_registry_present", report["failed_checks"])
        self.assertIn("acceleration_gate_pass", report["failed_checks"])

    def test_first_boot_contains_only_engineering_audits(self) -> None:
        source = (PROJECT_ROOT / "scripts" / "desktop_first_boot_v9.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn('formal_training_commands=0', source)
        self.assertNotIn('"train_v7.py"', source)
        self.assertNotIn('"tune-run"', source)
        for required in (
            "verify_v9_desktop_migration.py",
            "audit_v9_runtime_environment.py",
            "audit_v9_dynamic_prefetch.py",
            "audit_v9_prefetch_matrix.py",
            "audit_v9_cuda_transfer.py",
            "audit_v9_evaluation_batch.py",
            "audit_v9_desktop_acceleration.py",
            "audit_v9_desktop_readiness.py",
        ):
            self.assertIn(required, source)


if __name__ == "__main__":
    unittest.main()
