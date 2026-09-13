#!/usr/bin/env python3
"""Torch-free preflight for the same-parent vs same-class pairing ablation.

This script intentionally uses only the Python standard library. It validates
that the frozen train/validation split and local V7 peak cache are present, then
constructs example same-class/different-parent pairs without importing torch.
It does not train, render spectra, or access the simulated Test split.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import random


ROOT = Path(__file__).resolve().parents[1]
DATA_CONFIG = ROOT / "configs/data.method_transfer.structure_split.json"
OUTPUT = ROOT / "outputs/pairing_ablation_preflight.json"


def resolve_project_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    if ROOT.resolve() not in path.parents and path != ROOT.resolve():
        raise ValueError(f"path leaves xrd_robustness root: {value}")
    return path


def main() -> int:
    data = json.loads(DATA_CONFIG.read_text(encoding="utf-8"))
    split_path = resolve_project_path(str(data["split"]["path"]))
    peak_manifest_path = resolve_project_path(str(data["peak_cache"]["path"]))

    split_payload = json.loads(split_path.read_text(encoding="utf-8"))
    split_rows = split_payload.get("records")
    if not isinstance(split_rows, list):
        raise SystemExit("split manifest does not contain records")

    with peak_manifest_path.open("r", encoding="utf-8", newline="") as handle:
        peak_rows = list(csv.DictReader(handle))
    peak_by_id = {str(row["material_id"]): row for row in peak_rows}

    train_rows = [row for row in split_rows if row.get("split") == "train"]
    val_rows = [row for row in split_rows if row.get("split") == "validation"]
    expected = data["split"]["counts"]
    if len(train_rows) != int(expected["train"]):
        raise SystemExit(f"train count mismatch: {len(train_rows)} != {expected['train']}")
    if len(val_rows) != int(expected["validation"]):
        raise SystemExit(f"validation count mismatch: {len(val_rows)} != {expected['validation']}")

    missing = [
        str(row["material_id"])
        for row in train_rows + val_rows
        if str(row["material_id"]) not in peak_by_id
    ]
    if missing:
        raise SystemExit(f"peak cache missing IDs, first: {missing[:5]}")

    groups: dict[str, list[dict[str, object]]] = {}
    for row in train_rows:
        groups.setdefault(str(row["crystal_system"]), []).append(row)

    rng = random.Random(20260711)
    example_pairs = []
    per_class_counts = {}
    for crystal_system in sorted(groups):
        group = list(groups[crystal_system])
        rng.shuffle(group)
        per_class_counts[crystal_system] = len(group)
        for i in range(0, min(len(group) - 1, 4), 2):
            a = group[i]
            b = group[i + 1]
            if a["material_id"] == b["material_id"]:
                raise SystemExit("same-parent pair encountered")
            if a["crystal_system"] != b["crystal_system"]:
                raise SystemExit("different-class pair encountered")
            example_pairs.append(
                {
                    "class": crystal_system,
                    "a": a["material_id"],
                    "b": b["material_id"],
                    "different_parent": True,
                }
            )

    payload = {
        "status": "pass",
        "torch_imported": False,
        "test_access": False,
        "train_count": len(train_rows),
        "validation_count": len(val_rows),
        "train_per_class": per_class_counts,
        "peak_manifest_rows": len(peak_rows),
        "example_same_class_different_parent_pairs": example_pairs,
        "next_step": (
            "Once a working torch environment is available, run "
            "scripts/run_pairing_ablation.py --quick --device cuda"
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
