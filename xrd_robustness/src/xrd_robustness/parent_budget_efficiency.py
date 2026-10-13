"""Frozen parent-budget subset and stream helpers for the supplementary PXRD study.

The module intentionally depends only on the official split manifest and the
public source records. It never reads validation or test scores when selecting
training parents.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

import numpy as np

from .structure_data import CRYSTAL_SYSTEMS


PROTOCOL_VERSION = "parent-structure-efficiency-v1"
SELECTION_SEED = 20261013
BUDGETS = {"10": 984, "25": 2460, "50": 4921, "100": 9842}


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def identity_hash(ids: Iterable[str]) -> str:
    """Hash a set-like identity list independent of filesystem line endings."""
    return sha256_bytes(canonical_json_bytes(sorted(str(value) for value in ids)))


def _hamilton_quotas(
    total: int, class_counts: Mapping[str, int]
) -> dict[str, int]:
    denominator = sum(class_counts.values())
    raw = {name: total * class_counts[name] / denominator for name in CRYSTAL_SYSTEMS}
    quotas = {name: int(np.floor(raw[name])) for name in CRYSTAL_SYSTEMS}
    remainder = total - sum(quotas.values())
    order_index = {name: index for index, name in enumerate(CRYSTAL_SYSTEMS)}
    ranked = sorted(
        CRYSTAL_SYSTEMS,
        key=lambda name: (-(raw[name] - quotas[name]), order_index[name]),
    )
    for name in ranked[:remainder]:
        quotas[name] += 1
    if sum(quotas.values()) != total:
        raise AssertionError("Hamilton apportionment failed to preserve the budget")
    return quotas


def _selection_rank(seed: int, crystal_system: str, parent_id: str) -> str:
    payload = f"{PROTOCOL_VERSION}\0{int(seed)}\0{crystal_system}\0{parent_id}".encode()
    return hashlib.sha256(payload).hexdigest()


def build_nested_parent_order(
    split_rows: Sequence[Mapping[str, Any]], *, selection_seed: int = SELECTION_SEED
) -> tuple[list[dict[str, Any]], dict[str, dict[str, int]]]:
    """Return one deterministic stratified ordering whose prefixes are nested.

    For each target size, class quotas use Hamilton largest-remainder rounding,
    with ``CRYSTAL_SYSTEMS`` as the exact tie order. The source protocol's four
    quota vectors are checked for monotonicity before taking per-class prefixes.
    """
    train_rows = [row for row in split_rows if str(row["split"]) == "train"]
    counts = Counter(str(row["crystal_system"]) for row in train_rows)
    if set(counts) != set(CRYSTAL_SYSTEMS):
        raise ValueError("official Train split must contain all seven crystal systems")
    if sum(counts.values()) != BUDGETS["100"]:
        raise ValueError("official Train count does not match the frozen 9,842-parent budget")
    ranked_by_class: dict[str, list[dict[str, Any]]] = {}
    for name in CRYSTAL_SYSTEMS:
        rows = [dict(row) for row in train_rows if str(row["crystal_system"]) == name]
        rows.sort(
            key=lambda row: (
                _selection_rank(selection_seed, name, str(row["parent_structure_id"])),
                str(row["parent_structure_id"]),
            )
        )
        for rank, row in enumerate(rows, start=1):
            row["selection_rank"] = _selection_rank(
                selection_seed, name, str(row["parent_structure_id"])
            )
            row["class_rank"] = rank
        ranked_by_class[name] = rows

    quotas = {
        key: _hamilton_quotas(total, counts)
        for key, total in BUDGETS.items()
    }
    for name in CRYSTAL_SYSTEMS:
        previous = 0
        for key in ("10", "25", "50", "100"):
            quota = quotas[key][name]
            if quota < previous:
                raise ValueError(
                    f"frozen Hamilton quotas are not nested for {name} at {key}%"
                )
            previous = quota

    full_order: list[dict[str, Any]] = []
    for name in CRYSTAL_SYSTEMS:
        full_order.extend(ranked_by_class[name])
    return full_order, quotas


def validate_parent_split(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Validate unique parent/material identities and return split-indexed rows."""
    result = {name: [] for name in ("train", "validation", "test")}
    seen_materials: dict[str, str] = {}
    seen_parents: dict[str, str] = {}
    for raw in rows:
        row = dict(raw)
        split = str(row["split"])
        if split not in result:
            raise ValueError(f"unknown split {split!r}")
        material_id = str(row["material_id"])
        parent_id = str(row["parent_structure_id"])
        crystal_system = str(row["crystal_system"])
        if crystal_system not in CRYSTAL_SYSTEMS:
            raise ValueError(f"unknown crystal system {crystal_system!r}")
        if material_id in seen_materials:
            raise ValueError(f"duplicate material id {material_id}")
        if parent_id in seen_parents:
            raise ValueError(
                f"duplicate physical parent fingerprint {parent_id} in "
                f"{seen_parents[parent_id]} and {material_id}"
            )
        seen_materials[material_id] = parent_id
        seen_parents[parent_id] = material_id
        result[split].append(row)
    expected = {"train": 9842, "validation": 2109, "test": 2109}
    counts = {name: len(value) for name, value in result.items()}
    if counts != expected:
        raise ValueError(f"official formal split counts differ: {counts}")
    return result


class CyclicParentSampler:
    """Deterministic shuffled cycles that always yield complete fixed batches."""

    def __init__(self, rows: Sequence[Mapping[str, Any]], *, seed: int):
        if not rows:
            raise ValueError("sampler requires at least one parent")
        self.rows = list(rows)
        self.seed = int(seed)
        self.cycle = -1
        self.cursor = 0
        self.order = np.empty(0, dtype=np.int64)
        self.occurrences = 0
        self._new_cycle()

    def _new_cycle(self) -> None:
        self.cycle += 1
        self.order = np.random.default_rng(
            np.random.SeedSequence([self.seed, self.cycle, 20261013])
        ).permutation(len(self.rows))
        self.cursor = 0

    def next_batch(self, batch_size: int) -> list[dict[str, Any]]:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        indices: list[int] = []
        while len(indices) < batch_size:
            remaining = batch_size - len(indices)
            available = len(self.order) - self.cursor
            take = min(remaining, available)
            indices.extend(int(value) for value in self.order[self.cursor : self.cursor + take])
            self.cursor += take
            if self.cursor == len(self.order):
                self._new_cycle()
        self.occurrences += batch_size
        return [self.rows[index] for index in indices]


def load_split_rows(data_root: str | Path) -> list[dict[str, Any]]:
    path = Path(data_root) / "manifests" / "split_manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("records")
    if not isinstance(rows, list):
        raise ValueError("split_manifest.json must contain a records list")
    return [dict(row) for row in rows]


def load_source_record_index(data_root: str | Path) -> dict[str, dict[str, Any]]:
    path = Path(data_root) / "mp_processed" / "structure_records.jsonl"
    indexed: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            material_id = str(row["material_id"])
            if material_id in indexed:
                raise ValueError(f"duplicate source material {material_id} at line {line_number}")
            indexed[material_id] = {
                "crystal_system": str(row["crystal_system"]),
                "structure_fingerprint": str(row["structure_fingerprint"]),
                "split": str(row["split"]),
            }
    return indexed


def verify_source_against_split(
    split_rows: Sequence[Mapping[str, Any]], source_index: Mapping[str, Mapping[str, Any]]
) -> dict[str, int]:
    if len(source_index) != len(split_rows):
        raise ValueError("source record and official split manifest counts differ")
    source_split_disagreements = 0
    for row in split_rows:
        material_id = str(row["material_id"])
        source = source_index.get(material_id)
        if source is None:
            raise ValueError(f"official split material missing from source records: {material_id}")
        checks = {
            "crystal_system": str(row["crystal_system"]),
            "structure_fingerprint": str(row["parent_structure_id"]),
        }
        if any(str(source[key]) != expected for key, expected in checks.items()):
            raise ValueError(f"source record disagrees with split manifest for {material_id}")
        # The source record split field predates the later frozen split manifest.
        # It is audited, but the hash-bound official split manifest is authoritative.
        source_split_disagreements += int(str(source["split"]) != str(row["split"] ))
    return {"source_split_field_disagreements": source_split_disagreements}


def write_ranked_csv(path: str | Path, rows: Sequence[Mapping[str, Any]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fields = (
        "class_rank",
        "crystal_system",
        "material_id",
        "parent_structure_id",
        "selection_rank",
    )
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in fields})


def read_ranked_csv(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return [
            {
                **row,
                "class_rank": int(row["class_rank"]),
            }
            for row in csv.DictReader(handle)
        ]


def budget_prefixes(
    ranked_rows: Sequence[Mapping[str, Any]], quotas: Mapping[str, Mapping[str, int]]
) -> dict[str, list[dict[str, Any]]]:
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in ranked_rows:
        by_class[str(row["crystal_system"])].append(dict(row))
    output: dict[str, list[dict[str, Any]]] = {}
    previous: set[str] = set()
    for key in ("10", "25", "50", "100"):
        chosen: list[dict[str, Any]] = []
        for name in CRYSTAL_SYSTEMS:
            chosen.extend(by_class[name][: int(quotas[key][name])])
        ids = {str(row["parent_structure_id"]) for row in chosen}
        if not previous.issubset(ids):
            raise ValueError(f"{key}% subset is not nested in its predecessor")
        if len(ids) != BUDGETS[key]:
            raise ValueError(f"{key}% subset has {len(ids)}, expected {BUDGETS[key]}")
        output[key] = chosen
        previous = ids
    return output


def expected_exposure(steps: int, batch_size: int) -> dict[str, int]:
    if steps <= 0 or batch_size <= 0:
        raise ValueError("steps and batch_size must be positive")
    occurrences = int(steps) * int(batch_size)
    return {
        "optimizer_steps": int(steps),
        "parent_occurrences": occurrences,
        "views": occurrences * 2,
    }
