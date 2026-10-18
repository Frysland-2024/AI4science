#!/usr/bin/env python
"""Execute the frozen parent-budget matrix in seed-major, budget-minor order."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from run_parent_budget_pair import _run_pair  # noqa: E402


SEEDS = (20260711, 20260712, 20260713, 20260714, 20260715)
BUDGETS = ("10", "25", "50", "100")


def _complete_pair(output_root: Path, seed: int, budget: str) -> bool:
    result_path = output_root / f"seed_{seed}" / f"parents_{ {'10':984,'25':2460,'50':4921,'100':9842}[budget] }" / "result.json"
    if not result_path.is_file():
        return False
    return json.loads(result_path.read_text(encoding="utf-8")).get("status") == "completed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, choices=SEEDS, required=True)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--protocol-config", type=Path, default=PROJECT_ROOT / "configs" / "parent_budget_efficiency.v1.json")
    parser.add_argument("--subset-manifest", type=Path, default=PROJECT_ROOT / "manifests" / "parent_budget_efficiency" / "parent_subsets.v1.json")
    parser.add_argument("--ranked-parents", type=Path, default=PROJECT_ROOT / "manifests" / "parent_budget_efficiency" / "ranked_train_parents.v1.csv")
    parser.add_argument("--simulation-config", type=Path, default=PROJECT_ROOT / "configs" / "simulation.method_transfer.frozen.json")
    args = parser.parse_args()
    requested = tuple(args.seeds)
    if requested != tuple(seed for seed in SEEDS if seed in set(requested)):
        raise ValueError("seeds must follow the frozen order 20260711 through 20260715")
    output_root = args.output_root.resolve()
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")

    first_requested = SEEDS.index(requested[0])
    for prior_seed in SEEDS[:first_requested]:
        for budget in BUDGETS:
            if not _complete_pair(output_root, prior_seed, budget):
                raise RuntimeError(
                    f"seed-major order requires all budgets for prior seed {prior_seed}; "
                    f"missing parents={budget} pair"
                )
    matrix_path = output_root / "matrix_status.json"
    progress = {
        "schema_version": "parent-budget-matrix-status-v1",
        "planned_seeds": list(SEEDS),
        "planned_budgets_percent": [int(value) for value in BUDGETS],
        "planned_pairs": len(SEEDS) * len(BUDGETS),
        "completed_pairs": [],
        "started_unix_time": time.time(),
    }
    if matrix_path.exists():
        existing = json.loads(matrix_path.read_text(encoding="utf-8"))
        progress["completed_pairs"] = list(existing.get("completed_pairs", []))
        progress["started_unix_time"] = existing.get("started_unix_time", progress["started_unix_time"])
    matrix_path.parent.mkdir(parents=True, exist_ok=True)

    for seed in requested:
        for budget in BUDGETS:
            key = f"seed_{seed}:parents_{ {'10':984,'25':2460,'50':4921,'100':9842}[budget] }"
            if _complete_pair(output_root, seed, budget):
                if key not in progress["completed_pairs"]:
                    progress["completed_pairs"].append(key)
                continue
            pair_dir = output_root / f"seed_{seed}" / f"parents_{ {'10':984,'25':2460,'50':4921,'100':9842}[budget] }"
            if pair_dir.exists() and any(pair_dir.iterdir()):
                raise FileExistsError(
                    f"incomplete pair output exists and will not be overwritten: {pair_dir}"
                )
            result = _run_pair(
                data_root=args.data_root.resolve(),
                config_path=args.protocol_config.resolve(),
                subset_manifest_path=args.subset_manifest.resolve(),
                ranked_path=args.ranked_parents.resolve(),
                simulation_path=args.simulation_config.resolve(),
                output_root=output_root,
                budget_key=budget,
                seed=seed,
                device=device,
            )
            if result.get("status") != "completed":
                raise RuntimeError(f"pair did not complete: {key}")
            if key not in progress["completed_pairs"]:
                progress["completed_pairs"].append(key)
            progress["completed_pairs"].sort(
                key=lambda value: (
                    SEEDS.index(int(value.split(":")[0].removeprefix("seed_"))),
                    BUDGETS.index(next(k for k, v in {"10":984,"25":2460,"50":4921,"100":9842}.items() if value.endswith(f"parents_{v}"))),
                )
            )
            progress["updated_unix_time"] = time.time()
            temporary = matrix_path.with_suffix(".partial")
            temporary.write_text(json.dumps(progress, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            temporary.replace(matrix_path)
    progress["status"] = "completed" if len(progress["completed_pairs"]) == progress["planned_pairs"] else "partial"
    progress["updated_unix_time"] = time.time()
    temporary = matrix_path.with_suffix(".partial")
    temporary.write_text(json.dumps(progress, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(matrix_path)
    print(json.dumps(progress, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
