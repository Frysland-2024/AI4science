#!/usr/bin/env python3
"""Replay the pairing ablation with a 100-epoch ceiling and the same early stopping.

Why replay instead of resume from the completed 60-epoch pilot?
---------------------------------------------------------------
The quick pilot saved only the *best* model checkpoint (``best.pt``), not the
last epoch-60 model together with AdamW state.  For same-parent JS the best
checkpoint is epoch 40, while same-class JS peaks at epoch 60.  Loading those
checkpoints and continuing would therefore give the two arms different training
histories and would not be a clean continuation.

The scientifically clean option is a deterministic replay from epoch 1 with the
same seed, batches, views, optimizer, lambda, Validation panels and restored
prefetch pipeline, but with the maximum horizon raised from 60 to 100 epochs.
The original early-stopping rule is kept unchanged:

- Validation every 10 epochs
- minimum epoch = 40
- patience = 2 Validation checks
- min_delta = 0.002 in mean six-single-OOD Macro-F1

This script is only a thin locked launcher around ``run_pairing_ablation.py``;
it does not introduce a new training implementation and never accesses the
frozen simulated Test split.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

import run_pairing_ablation as pairing  # noqa: E402


DEFAULT_REFERENCE = ROOT / "outputs/pairing_ablation_quick"
DEFAULT_OUTPUT = ROOT / "outputs/pairing_ablation_extend100"
SEED = 20260711


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--reference-root", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--prefetch-workers", type=int, default=16)
    parser.add_argument("--prefetch-batches", type=int, default=6)
    parser.add_argument("--prefetch-worker-native-threads", type=int, default=1)
    return parser.parse_args()


def validate_reference(root: Path) -> dict[str, object]:
    summary_path = root / "summary.json"
    if not summary_path.is_file():
        raise SystemExit(
            f"reference quick summary is missing: {summary_path}\n"
            "Keep the completed 60-epoch pilot in place before launching the 100-epoch replay."
        )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    comparisons = summary.get("comparisons")
    if not isinstance(comparisons, list) or len(comparisons) != 1:
        raise SystemExit("reference quick summary is not the expected one-seed pairing pilot")
    comparison = comparisons[0]
    if int(comparison.get("seed", -1)) != SEED:
        raise SystemExit("reference quick summary seed does not match 20260711")
    return summary


def main() -> int:
    args = parse_args()
    reference_root = args.reference_root.resolve()
    output_root = args.output_root.resolve()
    reference = validate_reference(reference_root)

    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(
            f"refusing to overwrite non-empty output: {output_root}\n"
            "Choose a new --output-root or archive/delete the incomplete extension output first."
        )

    context = {
        "mode": "deterministic_replay_extension",
        "reason_not_true_resume": (
            "the 60-epoch pilot saved best.pt only and did not save the epoch-60 "
            "model plus AdamW optimizer state; replay keeps both arms scientifically matched"
        ),
        "reference_root": str(reference_root),
        "reference_summary": reference,
        "seed": SEED,
        "max_epochs": 100,
        "early_stopping": {
            "validation_every": 10,
            "min_epochs": 40,
            "patience": 2,
            "min_delta": 0.002,
            "metric": "Validation mean six-single-OOD Macro-F1",
        },
        "test_access": False,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "extension_context.json").write_text(
        json.dumps(context, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    argv = [
        "--output-root",
        str(output_root),
        "--seeds",
        str(SEED),
        "--epochs",
        "100",
        "--min-epochs",
        "40",
        "--patience",
        "2",
        "--validation-every",
        "10",
        "--min-delta",
        "0.002",
        "--device",
        str(args.device),
        "--prefetch-workers",
        str(args.prefetch_workers),
        "--prefetch-batches",
        str(args.prefetch_batches),
        "--prefetch-worker-native-threads",
        str(args.prefetch_worker_native_threads),
    ]

    print(
        "Launching deterministic 100-epoch replay extension for both arms. "
        "The old quick result is read-only and remains untouched.",
        flush=True,
    )
    return pairing.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
