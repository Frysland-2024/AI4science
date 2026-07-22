"""Post-hoc mechanism diagnostics from frozen feature arrays; no model inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from xrd_robustness.evaluation.metrics import representation_diagnostics, residual_diagnostics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features-npz", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = Path(args.features_npz).resolve()
    arrays = np.load(source, allow_pickle=False)
    required = {"first_features", "second_features", "labels"}
    if not required.issubset(arrays.files):
        raise ValueError(f"feature archive is missing arrays: {sorted(required - set(arrays.files))}")
    first = arrays["first_features"]
    second = arrays["second_features"]
    labels = arrays["labels"]
    if first.shape != second.shape or first.shape[0] != labels.shape[0]:
        raise ValueError("paired feature arrays and labels have inconsistent shapes")
    norm_first = first / np.clip(np.linalg.norm(first, axis=1, keepdims=True), 1e-8, None)
    norm_second = second / np.clip(np.linalg.norm(second, axis=1, keepdims=True), 1e-8, None)
    residual = np.abs(norm_first - norm_second)
    probe_logits = arrays["probe_logits"] if "probe_logits" in arrays.files else None
    report = {
        "schema_version": "v9-mechanism-diagnostics-v1",
        "scope": "posthoc_frozen_features_only",
        "selection_use_forbidden": True,
        "first_features": representation_diagnostics(first, labels=labels, prefix="feature"),
        "second_features": representation_diagnostics(second, labels=labels, prefix="feature"),
        "residual": residual_diagnostics(residual, probe_logits=probe_logits, labels=labels),
        "residual_swap_contract": "absolute normalized residual is invariant to view order",
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
