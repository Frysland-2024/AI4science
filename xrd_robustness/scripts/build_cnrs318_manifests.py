#!/usr/bin/env python3
"""Build or verify the two frozen, lightweight CNRS-318 manifests.

The default mode is read-only and checks that the tracked manifests still match the
authoritative local audit output. Pass ``--write`` only when intentionally rebuilding
the manifests before a new freeze; never use it to edit the evaluation set after
inspecting model predictions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
AUDIT_CANDIDATES = (
    ROOT / "data/real_xrd/opxrd_cnrs7cs/cnrs_7cs_final_parent_candidates.csv"
)
PARENT_MANIFEST = ROOT / "manifests/cnrs_318_parent_manifest_v2.csv"
EVAL_MANIFEST = ROOT / "manifests/cnrs318_eval_manifest.csv"
EVAL_SHA256 = ROOT / "manifests/cnrs318_eval_manifest.sha256"

CLASS_ORDER = [
    "triclinic",
    "monoclinic",
    "orthorhombic",
    "tetragonal",
    "trigonal",
    "hexagonal",
    "cubic",
]
CLASS_INDEX = {name: index for index, name in enumerate(CLASS_ORDER)}
EXPECTED_CLASS_COUNTS = {
    "triclinic": 21,
    "monoclinic": 87,
    "orthorhombic": 77,
    "tetragonal": 41,
    "trigonal": 33,
    "hexagonal": 12,
    "cubic": 47,
}
PARENT_FIELDS = [
    "parent_id",
    "representative_scan_id",
    "crystal_system",
    "space_group_consensus",
    "label_source",
    "symmetry_stable",
    "formal_14060_overlap",
    "manual_review_status",
    "exclusion_reason",
    "formula_reduced",
    "parent_group_size",
]
EVAL_FIELDS = [
    "parent_id",
    "representative_scan_id",
    "crystal_system",
    "label_index",
    "label_source",
    "excluded",
]


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def consensus(row: dict[str, str]) -> str:
    value = (row.get("recomputed_crystal_system") or "").strip()
    return value.split(";")[0] if value else ""


def scan_number(scan_id: str) -> int:
    return int(scan_id.rsplit("_", 1)[-1])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read_csv(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(encoding="utf-8-sig")))


def expected_parent_rows(source: Path) -> list[dict[str, str]]:
    source_rows = read_csv(source)
    eligible = [
        row
        for row in source_rows
        if as_bool(row.get("mapped_cu_ka_10_80_broad_parent_independent_eligible"))
    ]
    if len(eligible) != 318:
        raise ValueError(f"authoritative audit has {len(eligible)} final parents, expected 318")
    rows = [
        {
            "parent_id": row["structural_parent_group"],
            "representative_scan_id": row["scan_id"],
            "crystal_system": consensus(row),
            "space_group_consensus": row.get("recomputed_space_group_consensus", ""),
            "label_source": "structure_recomputed_stable_system",
            "symmetry_stable": "True"
            if as_bool(row.get("crystal_system_stable"))
            and as_bool(row.get("space_group_stable"))
            else "False",
            "formal_14060_overlap": str(
                row.get("structural_parent_formal_14060_overlap", "")
            ).strip(),
            "manual_review_status": "NOT_RUN",
            "exclusion_reason": "",
            "formula_reduced": row.get("formula_reduced", ""),
            "parent_group_size": row.get("structural_parent_group_size", ""),
        }
        for row in eligible
    ]
    rank = {name: index for index, name in enumerate(CLASS_ORDER)}
    rows.sort(
        key=lambda row: (
            rank.get(row["crystal_system"], 99),
            scan_number(row["representative_scan_id"]),
        )
    )
    counts = Counter(row["crystal_system"] for row in rows)
    if dict(counts) != EXPECTED_CLASS_COUNTS:
        raise ValueError(f"unexpected class counts: {dict(counts)}")
    if any(row["symmetry_stable"] != "True" for row in rows):
        raise ValueError("a final parent has an unstable structure-derived label")
    if any(row["formal_14060_overlap"].lower() != "false" for row in rows):
        raise ValueError("a final parent overlaps formal_14060")
    return rows


def expected_eval_rows(parent_rows: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "parent_id": row["parent_id"],
            "representative_scan_id": row["representative_scan_id"],
            "crystal_system": row["crystal_system"],
            "label_index": str(CLASS_INDEX[row["crystal_system"]]),
            "label_source": row["label_source"],
            "excluded": "False",
        }
        for row in parent_rows
    ]


def write_csv(path: Path, fields: Sequence[str], rows: Sequence[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields))
        writer.writeheader()
        writer.writerows(rows)


def execute(
    *,
    audit_candidates: Path,
    parent_manifest: Path,
    eval_manifest: Path,
    eval_sha256: Path,
    write: bool,
) -> dict[str, Any]:
    if not audit_candidates.is_file():
        raise FileNotFoundError(f"missing authoritative local audit output: {audit_candidates}")
    parent_rows = expected_parent_rows(audit_candidates)
    eval_rows = expected_eval_rows(parent_rows)
    if write:
        write_csv(parent_manifest, PARENT_FIELDS, parent_rows)
        write_csv(eval_manifest, EVAL_FIELDS, eval_rows)
        eval_sha256.write_text(sha256(eval_manifest) + "\n", encoding="ascii")
    else:
        if read_csv(parent_manifest) != parent_rows:
            raise ValueError("tracked parent manifest differs from the authoritative audit")
        if read_csv(eval_manifest) != eval_rows:
            raise ValueError("tracked eval manifest differs from the parent manifest projection")
        expected_hash = eval_sha256.read_text(encoding="ascii").strip().upper()
        if sha256(eval_manifest) != expected_hash:
            raise ValueError("eval manifest SHA sidecar is stale")
    return {
        "status": "written" if write else "verified",
        "n_parents": len(parent_rows),
        "class_counts": EXPECTED_CLASS_COUNTS,
        "audit_candidates_sha256": sha256(audit_candidates),
        "parent_manifest_sha256": sha256(parent_manifest),
        "eval_manifest_sha256": sha256(eval_manifest),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-candidates", type=Path, default=AUDIT_CANDIDATES)
    parser.add_argument("--parent-manifest", type=Path, default=PARENT_MANIFEST)
    parser.add_argument("--eval-manifest", type=Path, default=EVAL_MANIFEST)
    parser.add_argument("--eval-sha256", type=Path, default=EVAL_SHA256)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Intentionally rewrite the manifests. Default mode only verifies them.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = execute(
        audit_candidates=args.audit_candidates.resolve(),
        parent_manifest=args.parent_manifest.resolve(),
        eval_manifest=args.eval_manifest.resolve(),
        eval_sha256=args.eval_sha256.resolve(),
        write=args.write,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
