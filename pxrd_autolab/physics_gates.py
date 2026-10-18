"""Runtime evidence contract for the measurement-aware PXRD forward gates.

No passing gate evidence exists in this source revision. This module deliberately
blocks rather than accepting booleans or paths supplied by a GitHub Issue.
"""
from __future__ import annotations

import datetime as dt

REQUIRED_GATES = (
    "structure_and_reference_provenance",
    "independent_full_spectrum_parity",
    "measurement_aware_expected_profile",
    "autograd_vs_finite_difference",
    "q_eta_identifiability",
    "non_oracle_nuisance_estimation",
    "split_and_leakage_audit",
)


def run_required_gates(*, source_commit: str) -> dict:
    """Return a machine-readable block until real, reviewed tests are present.

    A future PASS must be produced by executable scientific tests in the
    approved tree and carry their measured values and provenance. Config or
    Issue fields are never consulted as evidence.
    """
    return {
        "schema_version": 1,
        "producer": "pxrd_autolab.physics_gates",
        "producer_status": "MISSING_REVIEWED_TEST_IMPLEMENTATION",
        "source_commit": source_commit,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "BLOCKED_MISSING_EVIDENCE",
        "summary": "No runtime scientific gate suite with independent measurement-aware evidence is registered.",
        "gates": [
            {
                "id": gate,
                "status": "BLOCKED_MISSING_EVIDENCE",
                "evidence": None,
                "reason": "A real test result with measured evidence and approved-source provenance is required.",
            }
            for gate in REQUIRED_GATES
        ],
    }
