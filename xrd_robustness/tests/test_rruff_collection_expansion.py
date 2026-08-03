import csv
import importlib.util
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "audit_rruff_collection_expansion.py"
)
SPEC = importlib.util.spec_from_file_location("audit_rruff_collection_expansion", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


FIELDS = (
    "rruff_id",
    "mineral_name",
    "crystal_system",
    "dataset_role",
    "spectrum_sha256",
    "raw_member_sha256",
    "dif_member_sha256",
)


def write_manifest(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def row(rruff_id, crystal_system, role, mineral="Mineral"):
    return {
        "rruff_id": rruff_id,
        "mineral_name": mineral,
        "crystal_system": crystal_system,
        "dataset_role": role,
        "spectrum_sha256": f"spectrum-{rruff_id}",
        "raw_member_sha256": f"raw-{rruff_id}",
        "dif_member_sha256": f"dif-{rruff_id}",
    }


def test_expansion_audit_accepts_balanced_hash_preserving_superset(tmp_path):
    parent = tmp_path / "parent.csv"
    expanded = tmp_path / "expanded.csv"
    parent_rows = []
    expanded_rows = []
    for class_index, crystal_system in enumerate(MODULE.CLASS_ORDER):
        for sample_index in range(10):
            item = row(
                f"R{class_index}{sample_index:05d}",
                crystal_system,
                "legacy_rruff70",
                mineral=f"Legacy {class_index} {sample_index}",
            )
            parent_rows.append(item)
            expanded_rows.append(item.copy())
        expanded_rows.append(
            row(
                f"N{class_index}00000",
                crystal_system,
                "rruff77_extension",
                mineral=f"New {class_index}",
            )
        )
    write_manifest(parent, parent_rows)
    write_manifest(expanded, expanded_rows)

    report = MODULE.build_report(parent, expanded, expected_added_per_class=1)

    assert report["status"] == "pass"
    assert report["inheritance"]["all_parent_hashes_preserved"] is True
    assert report["addition"]["sample_count"] == 7
    assert set(report["addition"]["class_counts"].values()) == {1}


def test_expansion_audit_detects_changed_parent_hash(tmp_path):
    parent = tmp_path / "parent.csv"
    expanded = tmp_path / "expanded.csv"
    parent_rows = []
    expanded_rows = []
    for class_index, crystal_system in enumerate(MODULE.CLASS_ORDER):
        for sample_index in range(10):
            item = row(
                f"R{class_index}{sample_index:05d}",
                crystal_system,
                "legacy_rruff70",
                mineral=f"Legacy {class_index} {sample_index}",
            )
            parent_rows.append(item)
            expanded_rows.append(item.copy())
        expanded_rows.append(
            row(f"N{class_index}00000", crystal_system, "rruff77_extension")
        )
    expanded_rows[0]["spectrum_sha256"] = "changed"
    write_manifest(parent, parent_rows)
    write_manifest(expanded, expanded_rows)

    report = MODULE.build_report(parent, expanded, expected_added_per_class=1)

    assert report["status"] == "fail"
    assert report["inheritance"]["all_parent_hashes_preserved"] is False
    assert report["inheritance"]["hash_mismatches"]["spectrum_sha256"] == [
        "R000000"
    ]
